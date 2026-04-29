from flask import Flask, request
import pandas as pd
import json
from ticker_config import (
    TICKER_LIST,
    ticker_dict,
    TOP1_PRESETS,
    STRATEGY_PARAM_MAP,
    STRATEGY_LABELS,
    get_preset,
    get_preset_query,
    optimizer_compare_rows,
)

app = Flask(__name__)

INITIAL_CASH = 100_000_000



def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def load_ticker_data(ticker):
    """티커별 일봉/주봉 데이터를 로드한다.
    우선순위:
    1) {ticker}_daily_data.csv
    2) {ticker}_daily_with_mode.csv

    주봉 파일이 없으면 일봉에서 자동 생성한다.
    daily에 WeeklyRSI가 없으면 weekly RSI를 붙인다.
    """
    ticker = ticker.upper()

    daily_file_candidates = [
        f"{ticker}_daily_data.csv",
        f"{ticker}_daily_with_mode.csv",
    ]
    weekly_file_candidates = [
        f"{ticker}_weekly_mode.csv",
    ]

    daily_df = None
    weekly_df = None
    daily_file_used = None
    weekly_file_used = None

    for file in daily_file_candidates:
        try:
            daily_df = pd.read_csv(file)
            daily_file_used = file
            break
        except Exception:
            continue

    if daily_df is None:
        return None, None

    # yfinance 등에서 MultiIndex 컬럼이 CSV로 저장된 경우 대비
    if "Date" not in daily_df.columns:
        first_col = daily_df.columns[0]
        daily_df = daily_df.rename(columns={first_col: "Date"})

    daily_df["Date"] = pd.to_datetime(daily_df["Date"], errors="coerce")
    daily_df = daily_df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

    if "Close" not in daily_df.columns:
        return None, None

    daily_df["Close"] = pd.to_numeric(daily_df["Close"], errors="coerce")
    daily_df = daily_df.dropna(subset=["Close"]).reset_index(drop=True)

    for file in weekly_file_candidates:
        try:
            weekly_df = pd.read_csv(file)
            weekly_file_used = file
            break
        except Exception:
            continue

    # weekly 파일이 없으면 일봉에서 자동 생성
    if weekly_df is None:
        weekly_df = daily_df.set_index("Date").resample("W-FRI").last().dropna(subset=["Close"]).reset_index()

    if "Date" not in weekly_df.columns:
        first_col = weekly_df.columns[0]
        weekly_df = weekly_df.rename(columns={first_col: "Date"})

    weekly_df["Date"] = pd.to_datetime(weekly_df["Date"], errors="coerce")
    weekly_df = weekly_df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

    if "Close" in weekly_df.columns:
        weekly_df["Close"] = pd.to_numeric(weekly_df["Close"], errors="coerce")

    # weekly RSI 없으면 계산
    if "RSI" not in weekly_df.columns and "WeeklyRSI" not in weekly_df.columns:
        if "Close" in weekly_df.columns:
            weekly_df["RSI"] = calc_rsi(weekly_df["Close"])
        else:
            weekly_df["RSI"] = 50

    # daily에 WeeklyRSI 없으면 weekly에서 붙이기
    if "WeeklyRSI" not in daily_df.columns:
        rsi_col = "WeeklyRSI" if "WeeklyRSI" in weekly_df.columns else "RSI"
        weekly_rsi = weekly_df[["Date", rsi_col]].copy().rename(columns={rsi_col: "WeeklyRSI"})
        daily_df = pd.merge_asof(
            daily_df.sort_values("Date"),
            weekly_rsi.sort_values("Date"),
            on="Date",
            direction="backward"
        )

    daily_df["WeeklyRSI"] = pd.to_numeric(daily_df.get("WeeklyRSI", 50), errors="coerce").fillna(50)
    daily_df["RSI"] = pd.to_numeric(daily_df.get("RSI", daily_df["WeeklyRSI"]), errors="coerce").fillna(daily_df["WeeklyRSI"])

    daily_df["MA5"] = daily_df["Close"].rolling(5).mean()
    daily_df["MA20"] = daily_df["Close"].rolling(20).mean()
    daily_df["MA200"] = daily_df["Close"].rolling(200).mean()

    # 디버그용 속성
    daily_df.attrs["daily_file_used"] = daily_file_used
    daily_df.attrs["weekly_file_used"] = weekly_file_used or "auto_generated_from_daily"

    return daily_df, weekly_df

# 현재 선택 티커 데이터는 home()에서 로드됨
daily = None
weekly = None



# =========================
# 공통 함수

# =========================
def make_mode(rsi, sell_rsi):
    if rsi >= sell_rsi:
        return "과열"
    elif rsi >= 50:
        return "상승"
    elif rsi >= 30:
        return "중립"
    elif rsi >= 20:
        return "침체"
    else:
        return "극침체"


def add_metrics(result_df):
    result_df["Peak"] = result_df["TotalAsset"].cummax()
    result_df["Drawdown"] = (result_df["TotalAsset"] - result_df["Peak"]) / result_df["Peak"]
    result_df["DailyReturn"] = result_df["TotalAsset"].pct_change().fillna(0) * 100
    return result_df


def calc_cagr(bt):
    if bt.empty:
        return 0

    start_date = bt["Date"].min()
    end_date = bt["Date"].max()
    years = max((end_date - start_date).days / 365.25, 0.01)

    start_asset = bt.iloc[0]["TotalAsset"]
    end_asset = bt.iloc[-1]["TotalAsset"]

    if start_asset <= 0:
        return 0

    return ((end_asset / start_asset) ** (1 / years) - 1) * 100


def calc_buyhold_stats(bt):
    """선택 기간 기준 QQQ 단순보유 성과 계산"""
    if bt.empty or len(bt) < 2:
        return 0, 0, 0, INITIAL_CASH

    start_close = float(bt.iloc[0]["Close"])
    if start_close <= 0:
        return 0, 0, 0, INITIAL_CASH

    bh_asset = INITIAL_CASH * (bt["Close"] / start_close)
    bh_final_asset = float(bh_asset.iloc[-1])
    bh_return = (bh_final_asset / INITIAL_CASH - 1) * 100

    peak = bh_asset.cummax()
    dd = (bh_asset - peak) / peak
    bh_mdd = float(dd.min() * 100)

    start_date = bt["Date"].min()
    end_date = bt["Date"].max()
    years = max((end_date - start_date).days / 365.25, 0.01)
    bh_cagr = ((bh_final_asset / INITIAL_CASH) ** (1 / years) - 1) * 100

    return bh_return, bh_cagr, bh_mdd, bh_final_asset


def cls_delta(value):
    return "positive" if value >= 0 else "negative"


def cls_positive_negative(value):
    return "positive" if value >= 0 else "negative"


def cls_mdd(value):
    if value <= -20:
        return "danger"
    elif value <= -10:
        return "warning"
    return "positive"


def cls_open_position(open_position):
    return "warning" if open_position == "있음" else "positive"


def make_strategy_verdict(return_delta, mdd_improvement):
    if return_delta >= 0 and mdd_improvement >= 0:
        return "전략 우세", "positive", "단순보유보다 수익률과 방어력이 모두 우수합니다."
    if return_delta >= 0 and mdd_improvement < 0:
        return "수익 우세 / 리스크 확인", "warning", "단순보유보다 수익률은 높지만 MDD는 더 큽니다."
    if return_delta < 0 and mdd_improvement >= 0:
        return "방어 우세", "warning", "수익률은 단순보유보다 낮지만 MDD 방어는 더 좋습니다."
    return "단순보유 우세", "negative", "현재 조건에서는 단순보유 대비 수익률과 방어력이 모두 아쉽습니다."


def calc_yearly_stats(bt):
    """선택 기간 기준 연도별 전략/QQQ 성과 계산"""
    if bt.empty:
        return pd.DataFrame()

    yearly_rows = []
    temp = bt.copy()
    temp["Year"] = temp["Date"].dt.year

    for year, group in temp.groupby("Year"):
        group = group.sort_values("Date").copy()
        if len(group) < 2:
            continue

        strategy_start = float(group.iloc[0]["TotalAsset"])
        strategy_end = float(group.iloc[-1]["TotalAsset"])
        qqq_start = float(group.iloc[0]["Close"])
        qqq_end = float(group.iloc[-1]["Close"])

        strategy_return = (strategy_end / strategy_start - 1) * 100 if strategy_start > 0 else 0
        qqq_return = (qqq_end / qqq_start - 1) * 100 if qqq_start > 0 else 0
        excess_return = strategy_return - qqq_return

        peak = group["TotalAsset"].cummax()
        dd = (group["TotalAsset"] - peak) / peak
        year_mdd = float(dd.min() * 100) if not dd.empty else 0

        qqq_asset = INITIAL_CASH * (group["Close"] / qqq_start) if qqq_start > 0 else pd.Series([INITIAL_CASH] * len(group))
        qqq_peak = qqq_asset.cummax()
        qqq_dd = (qqq_asset - qqq_peak) / qqq_peak
        qqq_mdd = float(qqq_dd.min() * 100) if not qqq_dd.empty else 0

        yearly_rows.append({
            "Year": int(year),
            "StrategyReturn": strategy_return,
            "QQQReturn": qqq_return,
            "ExcessReturn": excess_return,
            "StrategyMDD": year_mdd,
            "QQQMDD": qqq_mdd,
        })

    return pd.DataFrame(yearly_rows)


def pick_first_existing_col(df, candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None


def to_number_safe(value, default=0):
    try:
        if pd.isna(value):
            return default
        if isinstance(value, str):
            value = value.replace("%", "").replace(",", "").strip()
        return float(value)
    except Exception:
        return default


def classify_strategy_type(cagr, mdd, win_rate=0):
    """딥마이닝 결과를 공격형/균형형/방어형으로 간단 분류"""
    abs_mdd = abs(mdd)
    if cagr >= 8 and abs_mdd >= 18:
        return "공격형"
    if abs_mdd <= 12 and win_rate >= 60:
        return "방어형"
    return "균형형"


def summarize_period(bt_period):
    """Step18A: 기간별 요약"""
    if bt_period.empty or len(bt_period) < 2:
        return {
            "start": "-",
            "end": "-",
            "return": 0,
            "cagr": 0,
            "mdd": 0,
            "final_asset": INITIAL_CASH,
            "class": "warning",
        }

    start_asset = float(bt_period.iloc[0]["TotalAsset"])
    end_asset = float(bt_period.iloc[-1]["TotalAsset"])
    period_return = (end_asset / start_asset - 1) * 100 if start_asset > 0 else 0

    peak = bt_period["TotalAsset"].cummax()
    dd = (bt_period["TotalAsset"] - peak) / peak
    period_mdd = float(dd.min() * 100) if not dd.empty else 0

    period_cagr = calc_cagr(bt_period)

    return {
        "start": bt_period.iloc[0]["Date"].strftime("%Y-%m-%d"),
        "end": bt_period.iloc[-1]["Date"].strftime("%Y-%m-%d"),
        "return": period_return,
        "cagr": period_cagr,
        "mdd": period_mdd,
        "final_asset": end_asset,
        "class": cls_positive_negative(period_return),
    }


def make_walkforward_summary(bt):
    """Step18A: 인샘플 / 아웃샘플 검증"""
    train = bt[(bt["Date"] >= pd.Timestamp("2010-01-01")) & (bt["Date"] <= pd.Timestamp("2018-12-31"))].copy()
    test = bt[bt["Date"] >= pd.Timestamp("2019-01-01")].copy()

    train_summary = summarize_period(train)
    test_summary = summarize_period(test)

    cagr_drop = train_summary["cagr"] - test_summary["cagr"]
    mdd_worse = abs(test_summary["mdd"]) - abs(train_summary["mdd"])

    if test.empty or train.empty:
        verdict = "검증 데이터 부족"
        verdict_class = "warning"
        detail = "선택 기간이 너무 짧아 인샘플/아웃샘플을 나누기 어렵습니다."
    elif cagr_drop >= 5 and mdd_worse >= 5:
        verdict = "과최적화 의심"
        verdict_class = "danger"
        detail = "검증 구간 CAGR이 크게 낮고 MDD도 악화되었습니다."
    elif cagr_drop >= 5:
        verdict = "수익성 둔화"
        verdict_class = "warning"
        detail = "검증 구간 수익성이 학습 구간보다 낮아졌습니다."
    elif mdd_worse >= 5:
        verdict = "리스크 확대"
        verdict_class = "warning"
        detail = "검증 구간 MDD가 학습 구간보다 악화되었습니다."
    else:
        verdict = "검증 양호"
        verdict_class = "positive"
        detail = "학습 구간과 검증 구간의 성과 차이가 과도하지 않습니다."

    return train_summary, test_summary, cagr_drop, mdd_worse, verdict, verdict_class, detail


def calc_stability_score(train_summary, test_summary, mdd_worse):
    """과최적화 방지용 간단 안정성 점수(0~100).
    - OOS CAGR이 IS CAGR에 가까울수록 높음
    - OOS MDD가 IS보다 크게 나빠지면 감점
    """
    is_cagr = abs(train_summary.get("cagr", 0))
    oos_cagr = test_summary.get("cagr", 0)

    if is_cagr <= 0.01:
        base = 50 if oos_cagr >= 0 else 20
    else:
        base = max(0, min(100, (oos_cagr / is_cagr) * 100))

    penalty = max(0, mdd_worse) * 2
    score = max(0, min(100, base - penalty))

    if score >= 75:
        risk = "낮음"
        risk_class = "positive"
    elif score >= 50:
        risk = "보통"
        risk_class = "warning"
    else:
        risk = "높음"
        risk_class = "danger"

    return score, risk, risk_class


# =========================
# 거래 요약

# =========================
def make_trade_summary(trade_df, bt):
    if trade_df.empty:
        return {
            "trade_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate": 0,
            "avg_hold_days": 0,
            "max_hold_days": 0,
            "trades_per_year": 0,
            "open_position": "없음",
            "max_split": 0,
        }

    trade_count = len(trade_df)
    win_count = len(trade_df[trade_df["Profit"] > 0])
    loss_count = len(trade_df[trade_df["Profit"] <= 0])
    win_rate = (win_count / trade_count) * 100 if trade_count > 0 else 0

    avg_hold_days = trade_df["HoldDays"].mean() if "HoldDays" in trade_df.columns else 0
    max_hold_days = trade_df["HoldDays"].max() if "HoldDays" in trade_df.columns else 0

    years = max((bt["Date"].max() - bt["Date"].min()).days / 365.25, 1)
    trades_per_year = trade_count / years if years > 0 else 0

    open_position = "있음" if bt.iloc[-1]["Shares"] > 0 else "없음"
    max_split = bt["CurrentSplit"].max() if "CurrentSplit" in bt.columns else 0

    return {
        "trade_count": int(trade_count),
        "win_count": int(win_count),
        "loss_count": int(loss_count),
        "win_rate": round(win_rate, 2),
        "avg_hold_days": round(avg_hold_days, 1),
        "max_hold_days": int(max_hold_days) if pd.notna(max_hold_days) else 0,
        "trades_per_year": round(trades_per_year, 2),
        "open_position": open_position,
        "max_split": round(max_split, 1),
    }



# =========================
# 전략 1: RSI 커스텀

# =========================
def run_backtest(
    split_count=10,
    extreme_split=4,
    recession_split=3,
    neutral_split=1,
    boom_split=1,
    sell_rsi=70,
    fee_rate_pct=0.25,
):
    cash = INITIAL_CASH
    shares = 0
    avg_price = 0
    current_split = 0

    results = []
    trade_logs = []

    entry_date = None
    entry_amount = 0

    split_map = {
        "극침체": extreme_split,
        "침체": recession_split,
        "중립": neutral_split,
        "상승": boom_split,
        "과열": 0,
    }

    fee_rate = fee_rate_pct / 100

    for _, row in daily.iterrows():
        date = row["Date"]
        price = row["Close"]

        if "WeeklyRSI" in row:
            rsi = row["WeeklyRSI"]
        elif "RSI" in row:
            rsi = row["RSI"]
        else:
            rsi = 50

        mode = make_mode(rsi, sell_rsi)
        action = "관망"

        # 매도 조건
        if shares > 0 and rsi >= sell_rsi:
            sell_amount = shares * price
            sell_fee = sell_amount * fee_rate
            net_sell = sell_amount - sell_fee

            profit = net_sell - entry_amount
            return_pct = (profit / entry_amount) * 100 if entry_amount > 0 else 0

            hold_days = (date - entry_date).days if entry_date else 0

            trade_logs.append({
                "BuyDate": entry_date,
                "SellDate": date,
                "HoldDays": hold_days,
                "BuyAmount": entry_amount,
                "SellAmount": net_sell,
                "Profit": profit,
                "ReturnPct": return_pct,
                "Reason": "과열 RSI 전략매도",
            })

            cash += net_sell
            shares = 0
            avg_price = 0
            current_split = 0
            entry_date = None
            entry_amount = 0
            action = "매도"

        else:
            buy_splits_today = split_map.get(mode, 0)

            if buy_splits_today > 0 and current_split < split_count:
                remain_split = split_count - current_split
                actual_split = min(buy_splits_today, remain_split)

                split_amount = cash / remain_split if remain_split > 0 else 0
                buy_amount = split_amount * actual_split

                if buy_amount > 0:
                    buy_fee = buy_amount * fee_rate
                    total_buy_cost = buy_amount + buy_fee

                    if total_buy_cost > cash:
                        buy_amount = cash / (1 + fee_rate)
                        buy_fee = buy_amount * fee_rate
                        total_buy_cost = buy_amount + buy_fee

                    buy_shares = buy_amount / price if price > 0 else 0

                    total_cost_before = shares * avg_price
                    shares += buy_shares
                    total_cost_after = total_cost_before + buy_amount

                    avg_price = total_cost_after / shares if shares > 0 else 0

                    cash -= total_buy_cost

                    if entry_date is None:
                        entry_date = date
                        entry_amount = total_buy_cost
                    else:
                        entry_amount += total_buy_cost

                    current_split += actual_split
                    action = "매수"

        stock_value = shares * price
        total_asset = cash + stock_value

        results.append({
            "Date": date,
            "Close": price,
            "RSI": rsi,
            "Mode": mode,
            "Action": action,
            "Cash": cash,
            "Shares": shares,
            "StockValue": stock_value,
            "TotalAsset": total_asset,
            "CurrentSplit": current_split,
        })

    result_df = pd.DataFrame(results)
    result_df = add_metrics(result_df)

    trade_df = pd.DataFrame(trade_logs)

    if not trade_df.empty:
        # MAE / MFE
        maes = []
        mfes = []

        for _, trade in trade_df.iterrows():
            period = daily[
                (daily["Date"] >= trade["BuyDate"]) &
                (daily["Date"] <= trade["SellDate"])
            ].copy()

            if period.empty:
                maes.append(0)
                mfes.append(0)
                continue

            entry_price = period.iloc[0]["Close"]

            min_price = period["Close"].min()
            max_price = period["Close"].max()

            mae = ((min_price / entry_price) - 1) * 100
            mfe = ((max_price / entry_price) - 1) * 100

            maes.append(mae)
            mfes.append(mfe)

        trade_df["MAE"] = maes
        trade_df["MFE"] = mfes

    return result_df, trade_df


# =========================
# 전략 2: 오리지널 무한매수법

# =========================
def run_original_backtest(
    split_count=10,
    profit_target=10.0,
    fee_rate_pct=0.25,
):
    cash = INITIAL_CASH
    shares = 0
    avg_price = 0
    current_split = 0

    results = []
    trade_logs = []

    entry_date = None
    entry_amount = 0

    split_amount_base = INITIAL_CASH / split_count
    fee_rate = fee_rate_pct / 100

    for _, row in daily.iterrows():
        date = row["Date"]
        price = row["Close"]

        action = "관망"

        # 목표수익률 도달 시 전량매도
        if shares > 0:
            current_return = ((price / avg_price) - 1) * 100 if avg_price > 0 else 0

            if current_return >= profit_target:
                gross_sell = shares * price
                sell_fee = gross_sell * fee_rate
                net_sell = gross_sell - sell_fee

                profit = net_sell - entry_amount
                return_pct = (profit / entry_amount) * 100 if entry_amount > 0 else 0
                hold_days = (date - entry_date).days if entry_date else 0

                trade_logs.append({
                    "BuyDate": entry_date,
                    "SellDate": date,
                    "HoldDays": hold_days,
                    "BuyAmount": entry_amount,
                    "SellAmount": net_sell,
                    "Profit": profit,
                    "ReturnPct": return_pct,
                    "Reason": f"목표수익률 {profit_target:.1f}% 도달",
                })

                cash += net_sell
                shares = 0
                avg_price = 0
                current_split = 0
                entry_date = None
                entry_amount = 0
                action = "매도"

        # 분할매수
        elif current_split < split_count:
            remain_split = split_count - current_split
            buy_amount = min(split_amount_base, cash)

            if buy_amount > 0:
                buy_fee = buy_amount * fee_rate
                total_buy_cost = buy_amount + buy_fee

                if total_buy_cost > cash:
                    buy_amount = cash / (1 + fee_rate)
                    buy_fee = buy_amount * fee_rate
                    total_buy_cost = buy_amount + buy_fee

                buy_shares = buy_amount / price if price > 0 else 0

                total_cost_before = shares * avg_price
                shares += buy_shares
                total_cost_after = total_cost_before + buy_amount

                avg_price = total_cost_after / shares if shares > 0 else 0

                cash -= total_buy_cost

                if entry_date is None:
                    entry_date = date
                    entry_amount = total_buy_cost
                else:
                    entry_amount += total_buy_cost

                current_split += 1
                action = "매수"

        stock_value = shares * price
        total_asset = cash + stock_value

        results.append({
            "Date": date,
            "Close": price,
            "Action": action,
            "Cash": cash,
            "Shares": shares,
            "StockValue": stock_value,
            "TotalAsset": total_asset,
            "CurrentSplit": current_split,
        })

    result_df = pd.DataFrame(results)
    result_df = add_metrics(result_df)

    trade_df = pd.DataFrame(trade_logs)

    if not trade_df.empty:
        maes = []
        mfes = []

        for _, trade in trade_df.iterrows():
            period = daily[
                (daily["Date"] >= trade["BuyDate"]) &
                (daily["Date"] <= trade["SellDate"])
            ].copy()

            if period.empty:
                maes.append(0)
                mfes.append(0)
                continue

            entry_price = period.iloc[0]["Close"]

            min_price = period["Close"].min()
            max_price = period["Close"].max()

            mae = ((min_price / entry_price) - 1) * 100
            mfe = ((max_price / entry_price) - 1) * 100

            maes.append(mae)
            mfes.append(mfe)

        trade_df["MAE"] = maes
        trade_df["MFE"] = mfes

    return result_df, trade_df



# =========================
# 전략 3: 오리지널 2.0 (MA5 / MA20)

# =========================
def run_original_upgrade_backtest(
    split_count=30,
    profit_target=10.0,
    ma5_factor=3,
    ma20_factor=5,
    fee_rate_pct=0.25,
):
    cash = INITIAL_CASH
    shares = 0
    avg_price = 0
    current_split = 0

    results = []
    trade_logs = []

    entry_date = None
    entry_amount = 0

    split_amount_base = INITIAL_CASH / split_count
    fee_rate = fee_rate_pct / 100

    for _, row in daily.iterrows():
        date = row["Date"]
        price = row["Close"]
        ma5 = row["MA5"]
        ma20 = row["MA20"]

        action = "관망"

        # 매도
        if shares > 0:
            current_return = ((price / avg_price) - 1) * 100 if avg_price > 0 else 0

            if current_return >= profit_target:
                gross_sell = shares * price
                sell_fee = gross_sell * fee_rate
                net_sell = gross_sell - sell_fee

                profit = net_sell - entry_amount
                return_pct = (profit / entry_amount) * 100 if entry_amount > 0 else 0
                hold_days = (date - entry_date).days if entry_date else 0

                trade_logs.append({
                    "BuyDate": entry_date,
                    "SellDate": date,
                    "HoldDays": hold_days,
                    "BuyAmount": entry_amount,
                    "SellAmount": net_sell,
                    "Profit": profit,
                    "ReturnPct": return_pct,
                    "Reason": f"목표수익률 {profit_target:.1f}% 도달",
                })

                cash += net_sell
                shares = 0
                avg_price = 0
                current_split = 0
                entry_date = None
                entry_amount = 0
                action = "매도"

        # 매수
        elif current_split < split_count:
            buy_factor = 1

            if pd.notna(ma20) and price < ma20:
                buy_factor = ma20_factor
            elif pd.notna(ma5) and price < ma5:
                buy_factor = ma5_factor

            remain_split = split_count - current_split
            actual_split = min(buy_factor, remain_split)

            buy_amount = min(split_amount_base * actual_split, cash)

            if buy_amount > 0:
                buy_fee = buy_amount * fee_rate
                total_buy_cost = buy_amount + buy_fee

                if total_buy_cost > cash:
                    buy_amount = cash / (1 + fee_rate)
                    buy_fee = buy_amount * fee_rate
                    total_buy_cost = buy_amount + buy_fee

                buy_shares = buy_amount / price if price > 0 else 0

                total_cost_before = shares * avg_price
                shares += buy_shares
                total_cost_after = total_cost_before + buy_amount

                avg_price = total_cost_after / shares if shares > 0 else 0

                cash -= total_buy_cost

                if entry_date is None:
                    entry_date = date
                    entry_amount = total_buy_cost
                else:
                    entry_amount += total_buy_cost

                current_split += actual_split
                action = f"{actual_split}분할 매수"

        stock_value = shares * price
        total_asset = cash + stock_value

        results.append({
            "Date": date,
            "Close": price,
            "Action": action,
            "Cash": cash,
            "Shares": shares,
            "StockValue": stock_value,
            "TotalAsset": total_asset,
            "CurrentSplit": current_split,
        })

    result_df = pd.DataFrame(results)
    result_df = add_metrics(result_df)

    trade_df = pd.DataFrame(trade_logs)

    if not trade_df.empty:
        maes = []
        mfes = []

        for _, trade in trade_df.iterrows():
            period = daily[
                (daily["Date"] >= trade["BuyDate"]) &
                (daily["Date"] <= trade["SellDate"])
            ].copy()

            if period.empty:
                maes.append(0)
                mfes.append(0)
                continue

            entry_price = period.iloc[0]["Close"]

            min_price = period["Close"].min()
            max_price = period["Close"].max()

            mae = ((min_price / entry_price) - 1) * 100
            mfe = ((max_price / entry_price) - 1) * 100

            maes.append(mae)
            mfes.append(mfe)

        trade_df["MAE"] = maes
        trade_df["MFE"] = mfes

    return result_df, trade_df

# =========================
# Step22B-1: 무한매수 4.0 v0
# =========================
def run_infinite4_v0_backtest(
    split_count=20,
    target_profit=7.0,
    quarter_sell_ratio=25.0,
    fee_rate_pct=0.25,
):
    """무한매수법 4.0 v0 단순 엔진.

    - 분할수 20/30/40만 실험
    - T = INITIAL_CASH / split_count
    - 미보유 상태: 1T 최초 진입
    - 보유 중: 현재가가 평단 이하이고 남은 분할이 있으면 1T 추가매수
    - 목표수익률 도달: 보유 수량의 quarter_sell_ratio 만큼 부분매도

    v1 이후: 별점/전반전·후반전/소진모드/LOC·지정가 세부 로직 연결
    """
    split_count = int(split_count)
    if split_count not in [20, 30, 40]:
        split_count = 20 if split_count < 25 else 30 if split_count < 35 else 40

    cash = INITIAL_CASH
    shares = 0.0
    avg_price = 0.0
    current_split = 0.0

    unit_cash = INITIAL_CASH / split_count
    fee_rate = fee_rate_pct / 100
    sell_ratio = max(0.01, min(float(quarter_sell_ratio) / 100, 1.0))

    results = []
    trade_logs = []

    entry_date = None
    entry_amount = 0.0

    for _, row in daily.iterrows():
        date = row["Date"]
        price = float(row["Close"])
        action = "관망"
        mode = "소진모드" if current_split >= split_count else "일반모드"

        if shares > 0 and avg_price > 0:
            current_return = ((price / avg_price) - 1) * 100

            if current_return >= target_profit:
                if current_split <= 1.01 or sell_ratio >= 0.999:
                    sell_fraction = 1.0
                    sell_reason = f"목표수익률 {target_profit:.1f}% 도달 전량매도"
                else:
                    sell_fraction = sell_ratio
                    sell_reason = f"목표수익률 {target_profit:.1f}% 도달 쿼터매도({quarter_sell_ratio:.1f}%)"

                sell_shares = shares * sell_fraction
                gross_sell = sell_shares * price
                sell_fee = gross_sell * fee_rate
                net_sell = gross_sell - sell_fee

                cost_basis_sold = entry_amount * sell_fraction if entry_amount > 0 else avg_price * sell_shares
                profit = net_sell - cost_basis_sold
                return_pct = (profit / cost_basis_sold) * 100 if cost_basis_sold > 0 else 0
                hold_days = (date - entry_date).days if entry_date is not None else 0

                trade_logs.append({
                    "BuyDate": entry_date,
                    "SellDate": date,
                    "HoldDays": hold_days,
                    "BuyAmount": cost_basis_sold,
                    "SellAmount": net_sell,
                    "Profit": profit,
                    "ReturnPct": return_pct,
                    "Reason": sell_reason,
                })

                cash += net_sell
                shares -= sell_shares
                entry_amount -= cost_basis_sold
                current_split = max(0.0, current_split * (1 - sell_fraction))

                if shares <= 1e-9 or current_split <= 0.01:
                    shares = 0.0
                    avg_price = 0.0
                    current_split = 0.0
                    entry_date = None
                    entry_amount = 0.0

                action = "쿼터매도" if sell_fraction < 1.0 else "전량매도"

        if action == "관망":
            should_enter = shares <= 0
            should_add = shares > 0 and price <= avg_price and current_split < split_count

            if should_enter or should_add:
                buy_amount = min(unit_cash, cash / (1 + fee_rate))

                if buy_amount > 0:
                    buy_fee = buy_amount * fee_rate
                    total_buy_cost = buy_amount + buy_fee
                    buy_shares = buy_amount / price if price > 0 else 0

                    total_cost_before = shares * avg_price
                    shares += buy_shares
                    total_cost_after = total_cost_before + buy_amount
                    avg_price = total_cost_after / shares if shares > 0 else 0

                    cash -= total_buy_cost
                    current_split = min(split_count, current_split + 1)

                    if entry_date is None:
                        entry_date = date
                        entry_amount = total_buy_cost
                    else:
                        entry_amount += total_buy_cost

                    action = "최초매수" if should_enter else "평단이하 추가매수"

        stock_value = shares * price
        total_asset = cash + stock_value
        mode = "소진모드" if current_split >= split_count else "일반모드"

        results.append({
            "Date": date,
            "Close": price,
            "RSI": row.get("WeeklyRSI", row.get("RSI", 50)),
            "Mode": mode,
            "Action": action,
            "Cash": cash,
            "Shares": shares,
            "StockValue": stock_value,
            "TotalAsset": total_asset,
            "CurrentSplit": current_split,
        })

    result_df = pd.DataFrame(results)
    result_df = add_metrics(result_df)
    trade_df = pd.DataFrame(trade_logs)

    if not trade_df.empty:
        maes = []
        mfes = []
        for _, trade in trade_df.iterrows():
            if pd.isna(trade.get("BuyDate")) or pd.isna(trade.get("SellDate")):
                maes.append(0)
                mfes.append(0)
                continue

            period = daily[(daily["Date"] >= trade["BuyDate"]) & (daily["Date"] <= trade["SellDate"])].copy()
            if period.empty:
                maes.append(0)
                mfes.append(0)
                continue

            entry_price = float(period.iloc[0]["Close"])
            min_price = float(period["Close"].min())
            max_price = float(period["Close"].max())
            maes.append(((min_price / entry_price) - 1) * 100 if entry_price > 0 else 0)
            mfes.append(((max_price / entry_price) - 1) * 100 if entry_price > 0 else 0)

        trade_df["MAE"] = maes
        trade_df["MFE"] = mfes

    return result_df, trade_df






# =========================
# Step17 딥마이닝 TOP50 필터

# =========================
def load_deepmine_data(strategy, ticker="QQQ"):
    ticker = ticker.upper()
    file_map = {
        "rsi": [f"{ticker}_ultra_score_top10.csv", "QQQ_ultra_score_top10.csv"],
        "original": [f"{ticker}_original_score_top10.csv", "QQQ_original_score_top10.csv"],
        "original_upgrade": [f"{ticker}_original_return_top10.csv", "QQQ_original_return_top10.csv"],
    }

    for file_path in file_map.get(strategy, []):
        try:
            return pd.read_csv(file_path)
        except Exception:
            continue

    return pd.DataFrame()


def build_deepmine_table(
    strategy,
    ticker="QQQ",
    min_cagr=0,
    max_mdd=100,
    min_win=0,
    min_pf=0
):
    df = load_deepmine_data(strategy, ticker)

    if df.empty:
        return "", None

    cagr_col = pick_first_existing_col(df, ["CAGR", "cagr"])
    mdd_col = pick_first_existing_col(df, ["MDD", "mdd"])
    win_col = pick_first_existing_col(df, ["승률", "WinRate", "win_rate"])
    pf_col = pick_first_existing_col(df, ["ProfitFactor", "profit_factor", "PF"])

    if cagr_col:
        df = df[df[cagr_col].apply(lambda x: to_number_safe(x)) >= min_cagr]

    if mdd_col:
        df = df[df[mdd_col].apply(lambda x: abs(to_number_safe(x))) <= max_mdd]

    if win_col:
        df = df[df[win_col].apply(lambda x: to_number_safe(x)) >= min_win]

    if pf_col:
        df = df[df[pf_col].apply(lambda x: to_number_safe(x)) >= min_pf]

    if df.empty:
        return "<p>조건에 맞는 전략이 없습니다.</p>", None

    # 추천 전략 선정
    best_row = df.iloc[0]

    best_cagr = to_number_safe(best_row[cagr_col]) if cagr_col else 0
    best_mdd = to_number_safe(best_row[mdd_col]) if mdd_col else 0
    best_win = to_number_safe(best_row[win_col]) if win_col else 0

    strategy_type = classify_strategy_type(best_cagr, best_mdd, best_win)

    recommend_card = {
        "type": strategy_type,
        "cagr": best_cagr,
        "mdd": best_mdd,
        "win": best_win,
        "row": best_row,
    }

    display_df = df.head(50).copy()

    # 전략유형 추가
    display_types = []

    for _, row in display_df.iterrows():
        row_cagr = to_number_safe(row[cagr_col]) if cagr_col else 0
        row_mdd = to_number_safe(row[mdd_col]) if mdd_col else 0
        row_win = to_number_safe(row[win_col]) if win_col else 0

        display_types.append(
            classify_strategy_type(row_cagr, row_mdd, row_win)
        )

    display_df["전략유형"] = display_types

    headers = "".join([f"<th>{col}</th>" for col in display_df.columns])

    rows_html = ""

    for _, row in display_df.iterrows():
        row_html = "<tr>"

        for col in display_df.columns:
            row_html += f"<td>{row[col]}</td>"

        row_html += "</tr>"
        rows_html += row_html

    html = f"""
    <div class="card">
        <h2>딥마이닝 TOP50 (필터 적용)</h2>

        <div class="table-wrap">
            <table border="1" cellpadding="6" cellspacing="0">
                <tr>{headers}</tr>
                {rows_html}
            </table>
        </div>
    </div>
    """

    return html, recommend_card



# =========================
# Step19 오늘의 판단실

# =========================
def make_today_decision(
    latest_mode,
    split_count,
    current_split,
    final_cash,
    latest_price,
    fee_percent
):
    remain_split = max(split_count - current_split, 0)

    if remain_split <= 0:
        return {
            "action": "분할 완료 / 대기",
            "class": "warning",
            "recommended_split": 0,
            "amount": 0,
            "detail": "이미 최대 분할 상태입니다.",
        }

    split_cash = final_cash / remain_split if remain_split > 0 else 0

    if latest_mode == "과열":
        return {
            "action": "매도 검토",
            "class": "negative",
            "recommended_split": 0,
            "amount": 0,
            "detail": "과열 구간으로 신규 매수보다 차익실현 우선 구간입니다.",
        }

    if latest_mode == "상승":
        recommended_split = min(1, remain_split)

    elif latest_mode == "중립":
        recommended_split = min(1, remain_split)

    elif latest_mode == "침체":
        recommended_split = min(2, remain_split)

    else:  # 극침체
        recommended_split = min(4, remain_split)

    invest_amount = split_cash * recommended_split

    estimated_fee = invest_amount * (fee_percent / 100)

    return {
        "action": f"{recommended_split}분할 매수",
        "class": "positive" if recommended_split > 0 else "warning",
        "recommended_split": recommended_split,
        "amount": invest_amount,
        "detail": f"예상 투입금 {invest_amount:,.0f}원 / 예상 매수수수료 {estimated_fee:,.0f}원",
    }



# =========================
# Step18A + 19 카드 HTML

# =========================
def build_walkforward_and_today_cards(
    bt,
    latest_mode,
    split_count,
    current_split,
    final_cash,
    latest_price,
    fee_percent
):
    train_summary, test_summary, cagr_drop, mdd_worse, wf_verdict, wf_class, wf_detail = make_walkforward_summary(bt)
    stability_score, overfit_risk, overfit_class = calc_stability_score(train_summary, test_summary, mdd_worse)

    today_decision = make_today_decision(
        latest_mode,
        split_count,
        current_split,
        final_cash,
        latest_price,
        fee_percent
    )

    html = f"""
    <div class="grid">

        <div class="metric {wf_class}">
            <h3>워크포워드 판정</h3>
            <p>{wf_verdict}</p>
        </div>

        <div class="metric {overfit_class}">
            <h3>Overfit Risk</h3>
            <p>{overfit_risk}</p>
        </div>

        <div class="metric {overfit_class}">
            <h3>Stability Score</h3>
            <p>{stability_score:.1f}</p>
        </div>

        <div class="metric">
            <h3>인샘플 CAGR</h3>
            <p>{train_summary['cagr']:.2f}%</p>
        </div>

        <div class="metric">
            <h3>아웃샘플 CAGR</h3>
            <p>{test_summary['cagr']:.2f}%</p>
        </div>

        <div class="metric {cls_delta(-cagr_drop)}">
            <h3>CAGR 변화</h3>
            <p>{-cagr_drop:.2f}%</p>
        </div>

        <div class="metric {today_decision['class']}">
            <h3>오늘의 추천행동</h3>
            <p>{today_decision['action']}</p>
        </div>

        <div class="metric">
            <h3>추천 투입금</h3>
            <p>{today_decision['amount']:,.0f}원</p>
        </div>

    </div>

    <div class="card">
        <h2>Step18A 워크포워드 분석</h2>
        <p>{wf_detail}</p>
        <p>인샘플: {train_summary['start']} ~ {train_summary['end']}</p>
        <p>아웃샘플: {test_summary['start']} ~ {test_summary['end']}</p>
        <p>아웃샘플 MDD 변화: {mdd_worse:.2f}%p</p>
        <p>Stability Score: <b>{stability_score:.1f}</b> / Overfit Risk: <b>{overfit_risk}</b></p>
    </div>

    <div class="card">
        <h2>Step19 오늘의 판단실</h2>
        <p>현재 모드: <b>{latest_mode}</b></p>
        <p>{today_decision['detail']}</p>
    </div>
    """

    return html


# =========================



# =========================
# Step20+21: 프리셋 / 전략 파라미터 맵 / 최적화 비교 UI
# =========================
def metric_class_from_mdd(mdd_value):
    try:
        v = float(mdd_value)
    except Exception:
        return "warning"
    if v <= -80:
        return "danger"
    if v <= -55:
        return "warning"
    return "positive"


def practical_grade(cagr, mdd, stability):
    try:
        cagr = float(cagr)
        mdd = float(mdd)
        stability = float(stability)
    except Exception:
        return "검토"

    if cagr >= 30 and mdd >= -80 and stability >= 55:
        return "S 균형형"
    if cagr >= 35 and mdd < -80:
        return "A 공격형"
    if stability >= 70 and mdd >= -65:
        return "B 방어형"
    return "C 연구용"


def build_preset_buttons_html(ticker, strategy, start_date, end_date, fee_percent):
    """티커별 추천 프리셋 버튼. 현재는 RSI 최적화 결과를 중심으로 구성."""
    ticker = ticker.upper()

    buttons = []
    for preset_type in ["balanced", "aggressive", "defensive"]:
        preset = get_preset(ticker, "rsi", preset_type)
        if not preset:
            continue

        query = get_preset_query(
            ticker=ticker,
            strategy="rsi",
            preset_type=preset_type,
            start_date=start_date,
            end_date=end_date,
            fee_percent=fee_percent,
        )
        label = preset.get("label", preset_type)
        desc = preset.get("desc", "")

        buttons.append(f"""
        <a class="preset-btn" href="/?{query}">
            <b>{label}</b><br>
            <span>{desc}</span>
        </a>
        """)

    if not buttons:
        return ""

    return f"""
    <div class="preset-box">
        <p><b>Step20 추천 프리셋</b> <span class="small-note">Optimizer 결과 기반 자동입력</span></p>
        <div class="preset-buttons">
            {''.join(buttons)}
        </div>
    </div>
    """


def build_strategy_param_map_html():
    """Step21: 전략별 파라미터 맵. 실제 엔진 이식 전에도 구조를 먼저 고정."""
    sections = []

    for strategy_key, config in STRATEGY_PARAM_MAP.items():
        label = config.get("label", strategy_key)
        status = config.get("status", "준비중")
        params = config.get("params", [])
        note = config.get("note", "")

        li = "".join([f"<li>{p}</li>" for p in params])
        sections.append(f"""
        <div class="map-card">
            <h3>{label}</h3>
            <p class="small-note">상태: <b>{status}</b></p>
            <ul>{li}</ul>
            <p class="small-note">{note}</p>
        </div>
        """)

    return f"""
    <div class="card">
        <h2>Step21 전략별 파라미터 맵</h2>
        <p class="small-note">무한매수 / 떨사오팔 / 종사종팔 엔진을 나중에 연결하기 위한 공통 설계도입니다.</p>
        <div class="map-grid">
            {''.join(sections)}
        </div>
    </div>
    """


def build_optimizer_compare_html(strategy="rsi"):
    """생성된 *_optimizer_top100.csv 파일을 읽어 티커별 1순위만 비교."""
    rows = optimizer_compare_rows(strategy)
    if not rows:
        return f"""
        <div class="card">
            <h2>Step20 티커별 최적화 비교</h2>
            <p>아직 비교할 Optimizer 결과가 없습니다.</p>
            <pre>python optimizer_lab.py TQQQ {strategy}
python optimizer_lab.py SOXL {strategy}
python optimizer_lab.py SOXX {strategy}</pre>
        </div>
        """

    card_rows = ""
    table_rows = ""

    for r in rows:
        ticker = r.get("Ticker", "-")
        score = r.get("Score", 0)
        cagr = r.get("CAGR", 0)
        mdd = r.get("MDD", 0)
        stability = r.get("StabilityScore", 0)
        grade = practical_grade(cagr, mdd, stability)
        mdd_cls = metric_class_from_mdd(mdd)

        card_rows += f"""
        <div class="metric {mdd_cls}">
            <h3>{ticker} / {grade}</h3>
            <p>{score}</p>
            <span class="small-note">CAGR {cagr}% / MDD {mdd}% / Stability {stability}</span>
        </div>
        """

        table_rows += f"""
        <tr>
            <td>{ticker}</td>
            <td>{score}</td>
            <td>{cagr}%</td>
            <td>{mdd}%</td>
            <td>{stability}</td>
            <td>{r.get("OverfitRisk", "-")}</td>
            <td>{grade}</td>
            <td>{r.get("split_count", "-")}</td>
            <td>{r.get("sell_rsi", "-")}</td>
            <td>{r.get("extreme_split", "-")}</td>
            <td>{r.get("recession_split", "-")}</td>
            <td>{r.get("neutral_split", "-")}</td>
            <td>{r.get("boom_split", "-")}</td>
        </tr>
        """

    return f"""
    <div class="card hero">
        <h2>Step20 티커별 Optimizer 1위 비교</h2>
        <div class="grid">
            {card_rows}
        </div>
        <div class="table-wrap">
            <table border="1" cellpadding="6" cellspacing="0">
                <tr>
                    <th>티커</th>
                    <th>Score</th>
                    <th>CAGR</th>
                    <th>MDD</th>
                    <th>Stability</th>
                    <th>Overfit</th>
                    <th>실전등급</th>
                    <th>분할수</th>
                    <th>매도RSI</th>
                    <th>극침체</th>
                    <th>침체</th>
                    <th>중립</th>
                    <th>상승</th>
                </tr>
                {table_rows}
            </table>
        </div>
    </div>
    """

# =========================
# Step22 Optimizer Lab 결과 표시

# =========================
def load_optimizer_result(ticker, strategy):
    ticker = ticker.upper()
    candidates = [
        f"{ticker}_{strategy}_optimizer_top100.csv",
        f"{ticker}_optimizer_top100.csv",
    ]
    for file in candidates:
        try:
            return pd.read_csv(file), file
        except Exception:
            continue
    return pd.DataFrame(), None


def build_optimizer_result_html(ticker, strategy):
    df, file_used = load_optimizer_result(ticker, strategy)
    if df.empty:
        return f'''
        <div class="card hero">
            <h2>Optimizer Lab</h2>
            <p><b>{ticker}</b> / <b>{strategy}</b> 최적화 결과 파일이 아직 없습니다.</p>
            <p>먼저 터미널에서 아래 명령을 실행하세요.</p>
            <pre>python optimizer_lab.py {ticker} {strategy}</pre>
            <p class="small-note">생성 예상 파일: {ticker}_{strategy}_optimizer_top100.csv</p>
        </div>
        '''

    display_df = df.head(100).copy()
    headers = ''.join([f'<th>{col}</th>' for col in display_df.columns])
    rows = ''
    for _, row in display_df.iterrows():
        rows += '<tr>' + ''.join([f'<td>{row[col]}</td>' for col in display_df.columns]) + '</tr>'

    best = display_df.iloc[0]
    best_score = best.get('Score', '-')
    best_cagr = best.get('CAGR', '-')
    best_mdd = best.get('MDD', '-')
    best_stability = best.get('StabilityScore', '-')

    return f'''
    <div class="card hero">
        <h2>Optimizer Lab 추천 1순위</h2>
        <div class="grid">
            <div class="metric positive"><h3>Score</h3><p>{best_score}</p></div>
            <div class="metric positive"><h3>CAGR</h3><p>{best_cagr}</p></div>
            <div class="metric warning"><h3>MDD</h3><p>{best_mdd}</p></div>
            <div class="metric positive"><h3>Stability</h3><p>{best_stability}</p></div>
        </div>
        <p class="small-note">파일: {file_used}</p>
    </div>

    <div class="card">
        <h2>{ticker} Optimizer TOP100</h2>
        <div class="table-wrap">
            <table border="1" cellpadding="6" cellspacing="0">
                <tr>{headers}</tr>
                {rows}
            </table>
        </div>
    </div>
    '''

# Flask 메인 라우트

# =========================
@app.route("/")
def home():
    global daily, weekly

    ticker = request.args.get("ticker", default="QQQ").upper()

    if ticker not in TICKER_LIST:
        ticker = "QQQ"

    daily, weekly = load_ticker_data(ticker)

    if daily is None or weekly is None:
        available = ", ".join(TICKER_LIST)
        return f"""
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: Arial; padding: 40px;">
            <h2>{ticker} 데이터 파일을 찾을 수 없습니다.</h2>
            <p>필요 파일:</p>
            <pre>{ticker}_daily_data.csv 또는 {ticker}_daily_with_mode.csv
{ticker}_weekly_mode.csv</pre>
            <p>지원 티커: {available}</p>
            <a href="/?ticker=QQQ">QQQ로 돌아가기</a>
        </body>
        </html>
        """

    strategy = request.args.get("strategy", default="rsi")
    action_mode = request.args.get("action_mode", default="backtest")

    start_date = request.args.get("start_date", default=daily["Date"].min().strftime("%Y-%m-%d"))
    end_date = request.args.get("end_date", default=daily["Date"].max().strftime("%Y-%m-%d"))
    
    split_count = request.args.get("split_count", default=10, type=int)
    sell_rsi = request.args.get("sell_rsi", default=70, type=int)

    extreme_split = request.args.get("extreme_split", default=4, type=int)
    recession_split = request.args.get("recession_split", default=3, type=int)
    neutral_split = request.args.get("neutral_split", default=1, type=int)
    boom_split = request.args.get("boom_split", default=1, type=int)

    profit_target = request.args.get("profit_target", default=10.0, type=float)
    ma5_factor = request.args.get("ma5_factor", default=3, type=int)
    ma20_factor = request.args.get("ma20_factor", default=5, type=int)

    # Step22B 무한매수 4.0 v0 입력값
    infinite_split_count = request.args.get("infinite_split_count", default=20, type=int)
    infinite_target_profit = request.args.get("infinite_target_profit", default=7.0, type=float)
    quarter_sell_ratio = request.args.get("quarter_sell_ratio", default=25.0, type=float)

    fee_percent = request.args.get("fee_percent", default=0.25, type=float)
    ticker_options = ""
    for tk, name in ticker_dict().items():
        selected = "selected" if ticker == tk else ""
        ticker_options += f'<option value="{tk}" {selected}>{name}</option>'

    min_cagr = request.args.get("min_cagr", default=0, type=float)
    max_mdd = request.args.get("max_mdd", default=100, type=float)
    min_win = request.args.get("min_win", default=0, type=float)
    min_pf = request.args.get("min_pf", default=0, type=float)

    preset_buttons_html = build_preset_buttons_html(
        ticker=ticker,
        strategy=strategy,
        start_date=start_date,
        end_date=end_date,
        fee_percent=fee_percent,
    )
    strategy_param_map_html = build_strategy_param_map_html()
    optimizer_compare_html = build_optimizer_compare_html(strategy="rsi")


    # =========================
    # 전략 실행

    # =========================
    if strategy == "rsi":
        bt, trade_df = run_backtest(
            split_count=split_count,
            extreme_split=extreme_split,
            recession_split=recession_split,
            neutral_split=neutral_split,
            boom_split=boom_split,
            sell_rsi=sell_rsi,
            fee_rate_pct=fee_percent,
        )
        strategy_name = "RSI 커스텀"

        strategy_inputs = f"""
        <div class="input-row">
            <label>분할수 <input type="number" name="split_count" value="{split_count}"></label>
            <label>매도 RSI <input type="number" name="sell_rsi" value="{sell_rsi}"></label>
        </div>

        <div class="input-row">
            <label>극침체 <input type="number" name="extreme_split" value="{extreme_split}"></label>
            <label>침체 <input type="number" name="recession_split" value="{recession_split}"></label>
            <label>중립 <input type="number" name="neutral_split" value="{neutral_split}"></label>
            <label>상승 <input type="number" name="boom_split" value="{boom_split}"></label>
        </div>
        """

    elif strategy == "original":
        bt, trade_df = run_original_backtest(
            split_count=split_count,
            profit_target=profit_target,
            fee_rate_pct=fee_percent,
        )
        strategy_name = "오리지널"

        strategy_inputs = f"""
        <div class="input-row">
            <label>분할수 <input type="number" name="split_count" value="{split_count}"></label>
            <label>목표수익률(%) <input type="number" step="0.1" name="profit_target" value="{profit_target}"></label>
        </div>
        """

    elif strategy == "original_upgrade":
        bt, trade_df = run_original_upgrade_backtest(
            split_count=split_count,
            profit_target=profit_target,
            ma5_factor=ma5_factor,
            ma20_factor=ma20_factor,
            fee_rate_pct=fee_percent,
        )
        strategy_name = "오리지널 2.0"

        strategy_inputs = f"""
        <div class="input-row">
            <label>분할수 <input type="number" name="split_count" value="{split_count}"></label>
            <label>목표수익률(%) <input type="number" step="0.1" name="profit_target" value="{profit_target}"></label>
        </div>

        <div class="input-row">
            <label>MA5 매수배수 <input type="number" name="ma5_factor" value="{ma5_factor}"></label>
            <label>MA20 매수배수 <input type="number" name="ma20_factor" value="{ma20_factor}"></label>
        </div>
        """

    elif strategy == "infinite4":
        if infinite_split_count not in [20, 30, 40]:
            infinite_split_count = 20

        split_count = infinite_split_count
        bt, trade_df = run_infinite4_v0_backtest(
            split_count=infinite_split_count,
            target_profit=infinite_target_profit,
            quarter_sell_ratio=quarter_sell_ratio,
            fee_rate_pct=fee_percent,
        )
        strategy_name = "무한매수 4.0 v0"

        strategy_inputs = f"""
        <div class="input-row">
            <label>분할횟수
                <select name="infinite_split_count">
                    <option value="20" {"selected" if infinite_split_count == 20 else ""}>20</option>
                    <option value="30" {"selected" if infinite_split_count == 30 else ""}>30</option>
                    <option value="40" {"selected" if infinite_split_count == 40 else ""}>40</option>
                </select>
            </label>
            <label>목표수익률(%) <input type="number" step="0.1" name="infinite_target_profit" value="{infinite_target_profit}"></label>
            <label>쿼터매도비율(%) <input type="number" step="1" name="quarter_sell_ratio" value="{quarter_sell_ratio}"></label>
        </div>
        <p class="small-note">
            v0 단순엔진: T=원금/분할횟수, 미보유 1T 진입, 평단 이하 1T 추가매수, 목표수익률 도달 시 쿼터매도.<br>
            별점/전반전·후반전/소진모드/LOC·지정가 세부 로직은 v1 이후에 붙입니다.
        </p>
        """

    else:
        return "지원하지 않는 전략입니다."


    # =========================
    # 기간 필터링

    # =========================
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)

    bt = bt[(bt["Date"] >= start_dt) & (bt["Date"] <= end_dt)].copy()

    if bt.empty:
        return "선택한 기간에 백테스트 데이터가 없습니다. 시작일/종료일을 확인해주세요."

    if not trade_df.empty:
        trade_df["SellDate_dt"] = pd.to_datetime(trade_df["SellDate"])
        trade_df = trade_df[
            (trade_df["SellDate_dt"] >= start_dt) &
            (trade_df["SellDate_dt"] <= end_dt)
        ].copy()


    # =========================
    # 기본 성과 계산

    # =========================
    final = bt.tail(1).iloc[0]

    latest_date = final["Date"].strftime("%Y-%m-%d")
    latest_close = round(final["Close"], 2)

    if "RSI" in final.index:
        latest_rsi = round(final["RSI"], 2)
    elif "WeeklyRSI" in final.index:
        latest_rsi = round(final["WeeklyRSI"], 2)
    else:
        latest_rsi = 0

    latest_mode = make_mode(latest_rsi, sell_rsi)

    if pd.to_datetime(end_date) > daily["Date"].max():
        data_notice = "※ 선택 종료일이 데이터 범위를 초과해 마지막 데이터 기준으로 표시됩니다."
    else:
        data_notice = ""

    final_asset = round(final["TotalAsset"])
    cash = round(final["Cash"])
    stock_value = round(final["StockValue"])
    current_split = final["CurrentSplit"]

    return_rate = (final_asset / INITIAL_CASH - 1) * 100
    mdd = bt["Drawdown"].min() * 100
    cagr = calc_cagr(bt)

    trade_summary = make_trade_summary(trade_df, bt)

    avg_hold_days = trade_summary["avg_hold_days"]
    trades_per_year = trade_summary["trades_per_year"]
    open_position = trade_summary["open_position"]
    max_split = trade_summary["max_split"]


    # =========================
    # 수수료 / Profit Factor

    # =========================
    if trade_df.empty:
        buy_fee = 0
        sell_fee = 0
        estimated_fee = 0
        profit_factor = 0
    else:
        buy_fee = trade_df["BuyAmount"].fillna(0).sum() * (fee_percent / 100)
        sell_fee = trade_df["SellAmount"].fillna(0).sum() * (fee_percent / 100)
        estimated_fee = buy_fee + sell_fee

        gross_profit = trade_df[trade_df["Profit"] > 0]["Profit"].sum()
        gross_loss = abs(trade_df[trade_df["Profit"] < 0]["Profit"].sum())

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        else:
            profit_factor = gross_profit if gross_profit > 0 else 0


    # =========================
    # Buy & Hold 비교

    # =========================
    bh_return, bh_cagr, bh_mdd, bh_final_asset = calc_buyhold_stats(bt)

    return_delta = return_rate - bh_return
    cagr_delta = cagr - bh_cagr
    mdd_improvement = abs(bh_mdd) - abs(mdd)

    verdict, verdict_class, verdict_detail = make_strategy_verdict(
        return_delta,
        mdd_improvement
    )


    # =========================
    # 연도별 성과

    # =========================
    yearly_df = calc_yearly_stats(bt)

    if yearly_df.empty:
        best_year = "-"
        worst_year = "-"
        worst_mdd_year = "-"
    else:
        best_year = int(yearly_df.loc[yearly_df["StrategyReturn"].idxmax(), "Year"])
        worst_year = int(yearly_df.loc[yearly_df["StrategyReturn"].idxmin(), "Year"])
        worst_mdd_year = int(yearly_df.loc[yearly_df["StrategyMDD"].idxmin(), "Year"])

    yearly_labels = yearly_df["Year"].astype(str).tolist() if not yearly_df.empty else []
    yearly_strategy_returns = yearly_df["StrategyReturn"].round(2).tolist() if not yearly_df.empty else []
    yearly_qqq_returns = yearly_df["QQQReturn"].round(2).tolist() if not yearly_df.empty else []

    yearly_rows = ""
    if not yearly_df.empty:
        for _, row in yearly_df.iterrows():
            yearly_rows += f"""
            <tr>
                <td>{int(row["Year"])}</td>
                <td>{row["StrategyReturn"]:.2f}%</td>
                <td>{row["QQQReturn"]:.2f}%</td>
                <td>{row["ExcessReturn"]:.2f}%</td>
                <td>{row["StrategyMDD"]:.2f}%</td>
                <td>{row["QQQMDD"]:.2f}%</td>
            </tr>
            """

    yearly_html = f"""
    <div class="grid">
        <div class="metric positive"><h3>최고 수익 연도</h3><p>{best_year}</p></div>
        <div class="metric warning"><h3>최악 수익 연도</h3><p>{worst_year}</p></div>
        <div class="metric danger"><h3>최대 MDD 연도</h3><p>{worst_mdd_year}</p></div>
    </div>

    <div class="card">
        <h2>연도별 성과 분석</h2>
        <div class="table-wrap">
            <table border="1" cellpadding="6" cellspacing="0">
                <tr>
                    <th>연도</th>
                    <th>전략 수익률</th>
                    <th>{ticker} 수익률</th>
                    <th>초과수익</th>
                    <th>전략 MDD</th>
                    <th>{ticker} MDD</th>
                </tr>
                {yearly_rows}
            </table>
        </div>
    </div>

    <div class="card">
        <h2>연도별 수익률 비교</h2>
        <div class="chart-box">
            <canvas id="yearlyChart"></canvas>
        </div>
    </div>
    """


    # =========================
    # Step18A + Step19

    # =========================
    walkforward_today_html = build_walkforward_and_today_cards(
        bt=bt,
        latest_mode=latest_mode,
        split_count=split_count,
        current_split=current_split,
        final_cash=cash,
        latest_price=latest_close,
        fee_percent=fee_percent
    )


    # =========================
    # 딥마이닝 TOP50

    # =========================
    deepmine_html = ""
    optimizer_html = ""
    recommend_card_html = ""

    if action_mode == "deepmine":
        deepmine_table_html, recommend_card = build_deepmine_table(
            strategy=strategy,
            ticker=ticker,
            min_cagr=min_cagr,
            max_mdd=max_mdd,
            min_win=min_win,
            min_pf=min_pf,
        )

        deepmine_html = f"""
        <div class="card">
            <h2>딥마이닝 2.0 필터</h2>
            <form method="get">
                <input type="hidden" name="ticker" value="{ticker}">
                <input type="hidden" name="strategy" value="{strategy}">
                <input type="hidden" name="action_mode" value="deepmine">
                <input type="hidden" name="start_date" value="{start_date}">
                <input type="hidden" name="end_date" value="{end_date}">
                <input type="hidden" name="fee_percent" value="{fee_percent}">

                <div class="input-row">
                    <label>최소 CAGR <input type="number" step="0.1" name="min_cagr" value="{min_cagr}"></label>
                    <label>최대 MDD <input type="number" step="0.1" name="max_mdd" value="{max_mdd}"></label>
                    <label>최소 승률 <input type="number" step="0.1" name="min_win" value="{min_win}"></label>
                    <label>최소 PF <input type="number" step="0.1" name="min_pf" value="{min_pf}"></label>
                </div>

                <button type="submit">필터 적용</button>
            </form>
        </div>
        {deepmine_table_html}
        """

        if recommend_card:
            recommend_card_html = f"""
            <div class="card hero">
                <h2>추천 후보 1순위</h2>
                <p>전략 유형: <b>{recommend_card["type"]}</b></p>
                <p>CAGR: <b>{recommend_card["cagr"]:.2f}%</b></p>
                <p>MDD: <b>{recommend_card["mdd"]:.2f}%</b></p>
                <p>승률: <b>{recommend_card["win"]:.2f}%</b></p>
            </div>
            """


    # =========================
    if action_mode == "optimizer":
        optimizer_html = build_optimizer_result_html(ticker, strategy)

    # 매매로그

    # =========================
    trade_rows = ""
    if not trade_df.empty:
        for _, row in trade_df.tail(20).sort_values("SellDate", ascending=False).iterrows():
            trade_rows += f"""
            <tr>
                <td>{row.get("BuyDate", "")}</td>
                <td>{row.get("SellDate", "")}</td>
                <td>{row.get("HoldDays", 0)}</td>
                <td>{row.get("BuyAmount", 0):,.0f}</td>
                <td>{row.get("SellAmount", 0):,.0f}</td>
                <td>{row.get("Profit", 0):,.0f}</td>
                <td>{row.get("ReturnPct", 0):.2f}%</td>
                <td>{row.get("MAE", 0):.2f}%</td>
                <td>{row.get("MFE", 0):.2f}%</td>
                <td>{row.get("Reason", "")}</td>
            </tr>
            """

    trade_log_html = f"""
    <div class="card">
        <h2>매매로그 / 승률 / 보유일 분석</h2>
        <div class="summary-grid">
            <p>총 거래수: <b>{trade_summary["trade_count"]}</b></p>
            <p>수익매도: <b>{trade_summary["win_count"]}</b></p>
            <p>손실매도: <b>{trade_summary["loss_count"]}</b></p>
            <p>승률: <b>{trade_summary["win_rate"]:.2f}%</b></p>
            <p>평균 보유일: <b>{trade_summary["avg_hold_days"]:.1f}일</b></p>
            <p>최대 보유일: <b>{trade_summary["max_hold_days"]}</b>일</p>
            <p>연평균 거래횟수: <b>{trade_summary["trades_per_year"]:.2f}회</b></p>
            <p>현재 미청산: <b>{trade_summary["open_position"]}</b></p>
            <p>최대 분할: <b>{trade_summary["max_split"]:.1f} / {split_count}</b></p>
        </div>

        <div class="table-wrap">
            <table border="1" cellpadding="6" cellspacing="0">
                <tr>
                    <th>매수일</th>
                    <th>매도일</th>
                    <th>보유일</th>
                    <th>매수금액</th>
                    <th>매도금액</th>
                    <th>손익</th>
                    <th>수익률</th>
                    <th>MAE</th>
                    <th>MFE</th>
                    <th>사유</th>
                </tr>
                {trade_rows}
            </table>
        </div>
    </div>
    """


    # =========================
    # 차트 데이터

    # =========================
    bt["TotalAsset"] = pd.to_numeric(bt["TotalAsset"], errors="coerce").fillna(0)
    bt["Close"] = pd.to_numeric(bt["Close"], errors="coerce").fillna(0)
    bt["Drawdown"] = pd.to_numeric(bt["Drawdown"], errors="coerce").fillna(0)

    monthly = bt.copy()
    monthly["Month"] = monthly["Date"].dt.to_period("M")
    monthly_return = monthly.groupby("Month")["DailyReturn"].sum().reset_index()

    buy_points = []
    sell_points = []

    for _, row in bt.iterrows():
        if "매수" in str(row["Action"]):
            buy_points.append(round(float(row["Close"]), 2))
            sell_points.append(None)
        elif "매도" in str(row["Action"]):
            buy_points.append(None)
            sell_points.append(round(float(row["Close"]), 2))
        else:
            buy_points.append(None)
            sell_points.append(None)

    chart_data = {
        "labels": bt["Date"].dt.strftime("%Y-%m-%d").tolist(),
        "assets": bt["TotalAsset"].round(0).tolist(),
        "prices": bt["Close"].round(2).tolist(),
        "drawdown": (bt["Drawdown"] * 100).round(2).tolist(),
        "month_labels": monthly_return["Month"].astype(str).tolist(),
        "month_return": monthly_return["DailyReturn"].fillna(0).round(2).tolist(),
        "buy_points": buy_points,
        "sell_points": sell_points,
        "yearly_labels": yearly_labels,
        "yearly_strategy_returns": yearly_strategy_returns,
        "yearly_qqq_returns": yearly_qqq_returns,
    }

    chart_json = json.dumps(chart_data, ensure_ascii=False)

    return_class = cls_positive_negative(return_rate)
    cagr_class = cls_positive_negative(cagr)
    mdd_class = cls_mdd(mdd)
    win_class = "positive" if trade_summary["win_rate"] >= 60 else "warning" if trade_summary["win_rate"] >= 40 else "negative"
    bh_class = cls_positive_negative(bh_return)
    open_class = cls_open_position(open_position)
    pf_class = "positive" if profit_factor >= 1.5 else "warning" if profit_factor >= 1 else "negative"

    html = f"""
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ticker} Strategy Lab</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #f5f7fa;
            padding: 40px;
            color: #111827;
        }}
        .card {{
            background: white;
            padding: 22px;
            border-radius: 14px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            overflow-x: auto;
        }}
        .hero {{
            border-left: 6px solid #2196f3;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 20px;
        }}
        .metric {{
            background: white;
            padding: 20px;
            border-radius: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            transition: transform 0.2s ease;
            border-top: 4px solid #d1d5db;
        }}
        .metric:hover {{
            transform: translateY(-3px);
        }}
        .metric h3 {{
            margin: 0;
            color: #666;
            font-size: 14px;
        }}
        .metric p {{
            margin: 8px 0 0 0;
            font-size: 24px;
            font-weight: bold;
        }}
        .metric.positive {{
            border-top-color: #16a34a;
        }}
        .metric.positive p {{
            color: #16a34a;
        }}
        .metric.negative {{
            border-top-color: #dc2626;
        }}
        .metric.negative p {{
            color: #dc2626;
        }}
        .metric.warning {{
            border-top-color: #f59e0b;
        }}
        .metric.warning p {{
            color: #d97706;
        }}
        .metric.danger {{
            border-top-color: #991b1b;
        }}
        .metric.danger p {{
            color: #991b1b;
        }}
        .mode {{
            font-size: 32px;
            color: blue;
            font-weight: bold;
        }}
        .input-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 12px;
            align-items: center;
        }}
        input, select, button {{
            padding: 7px;
            margin: 4px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
        }}
        button {{
            cursor: pointer;
            background: #111827;
            color: white;
        }}
        table {{
            border-collapse: collapse;
            background: white;
            white-space: nowrap;
            width: 100%;
        }}
        th {{
            background: #f0f0f0;
        }}
        th, td {{
            padding: 8px;
        }}
        .table-wrap {{
            overflow-x: auto;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 8px 16px;
        }}
        .chart-box {{
            position: relative;
            width: 100%;
            height: 420px;
        }}
        .small-note {{
            color: #6b7280;
            font-size: 13px;
        }}
        .preset-box {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 12px;
            margin: 10px 0 14px 0;
        }}
        .preset-buttons {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .preset-btn {{
            display: inline-block;
            text-decoration: none;
            color: #111827;
            background: white;
            border: 1px solid #d1d5db;
            border-left: 5px solid #2196f3;
            border-radius: 10px;
            padding: 10px 14px;
            min-width: 170px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        }}
        .preset-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 3px 8px rgba(0,0,0,0.08);
        }}
        .map-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 14px;
        }}
        .map-card {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 14px;
        }}
        .map-card h3 {{
            margin-top: 0;
        }}
        @media (max-width: 768px) {{
            body {{
                padding: 12px;
            }}
            .card {{
                padding: 16px;
            }}
            .grid {{
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
            }}
            .metric {{
                padding: 14px;
            }}
            .metric p {{
                font-size: 18px;
            }}
            .metric h3 {{
                font-size: 12px;
            }}
            .chart-box {{
                height: 320px;
            }}
            .mode {{
                font-size: 24px;
            }}
        }}
    </style>
</head>

<body>

<div class="card hero">
    <h1>{ticker} 전략 실험실</h1>

    <form method="get">
        <div class="input-row">
            <label>티커 선택
                <select name="ticker" onchange="this.form.submit()">
                    {ticker_options}
                </select>
            </label>
        </div>

        <div class="input-row">
            <label>시작일 <input type="date" name="start_date" value="{start_date}"></label>
            <label>종료일 <input type="date" name="end_date" value="{end_date}"></label>
            <label>수수료율(%) <input type="number" step="0.001" name="fee_percent" value="{fee_percent}"></label>
            <span class="small-note">예: 0.25 입력 = 매수 0.25% + 매도 0.25%</span>
        </div>

        <div class="input-row">
            <label>전략 선택
                <select name="strategy">
                    <option value="rsi" {"selected" if strategy == "rsi" else ""}>RSI 커스텀</option>
                    <option value="original" {"selected" if strategy == "original" else ""}>오리지널</option>
                    <option value="original_upgrade" {"selected" if strategy == "original_upgrade" else ""}>오리지널 2.0</option>
                    <option value="infinite4" {"selected" if strategy == "infinite4" else ""}>무한매수 4.0 v0</option>
                    <option value="tteolsa" disabled>떨사오팔 준비중</option>
                    <option value="jongsajongpal" disabled>종사종팔 준비중</option>
                </select>
            </label>
        </div>

        {strategy_inputs}

        {preset_buttons_html}

        <button type="submit" name="action_mode" value="backtest">백테스트</button>
        <button type="submit" name="action_mode" value="deepmine">딥마이닝 TOP50</button>
        <button type="submit" name="action_mode" value="optimizer">Optimizer TOP100</button>
    </form>

    <hr>

    <p>기준일: {latest_date}</p>
    <p style="color:#777;">데이터 마지막일: {daily["Date"].max().strftime("%Y-%m-%d")}</p>
    <p style="color:orange;">{data_notice}</p>
    <p>{ticker} 종가: ${latest_close}</p>
    <p>주간 RSI: {latest_rsi}</p>
    <div class="mode">현재 모드: {latest_mode}</div>
</div>

<div class="grid">
    <div class="metric {return_class}"><h3>최종자산</h3><p>{final_asset:,.0f}원</p></div>
    <div class="metric {return_class}"><h3>총수익률</h3><p>{return_rate:.2f}%</p></div>
    <div class="metric {cagr_class}"><h3>CAGR</h3><p>{cagr:.2f}%</p></div>
    <div class="metric {mdd_class}"><h3>MDD</h3><p>{mdd:.2f}%</p></div>

    <div class="metric {win_class}"><h3>승률</h3><p>{trade_summary["win_rate"]:.2f}%</p></div>
    <div class="metric"><h3>거래수</h3><p>{trade_summary["trade_count"]}</p></div>

    <div class="metric"><h3>평균보유일</h3><p>{avg_hold_days:.1f}일</p></div>
    <div class="metric"><h3>연평균거래</h3><p>{trades_per_year:.2f}회</p></div>

    <div class="metric {open_class}"><h3>현재 미청산</h3><p>{open_position}</p></div>
    <div class="metric"><h3>최대분할</h3><p>{max_split:.1f}</p></div>

    <div class="metric {bh_class}"><h3>Buy&Hold</h3><p>{bh_return:.2f}%</p></div>
    <div class="metric warning"><h3>예상수수료</h3><p>{estimated_fee:,.0f}원</p></div>

    <div class="metric"><h3>매수수수료</h3><p>{buy_fee:,.0f}원</p></div>
    <div class="metric"><h3>매도수수료</h3><p>{sell_fee:,.0f}원</p></div>
    <div class="metric {pf_class}"><h3>Profit Factor</h3><p>{profit_factor:.2f}</p></div>
</div>

<div class="card hero">
    <h2>전략 vs {ticker} Buy&Hold 비교</h2>
    <div class="grid">
        <div class="metric {verdict_class}"><h3>종합판정</h3><p>{verdict}</p></div>
        <div class="metric {cls_delta(return_delta)}"><h3>초과수익률</h3><p>{return_delta:.2f}%</p></div>
        <div class="metric {cls_delta(cagr_delta)}"><h3>CAGR 차이</h3><p>{cagr_delta:.2f}%</p></div>
        <div class="metric {cls_delta(mdd_improvement)}"><h3>MDD 개선폭</h3><p>{mdd_improvement:.2f}%p</p></div>
    </div>
    <p>{verdict_detail}</p>
</div>

{walkforward_today_html}

{optimizer_compare_html}

{strategy_param_map_html}

{yearly_html}

{deepmine_html}
{optimizer_html}
{recommend_card_html}

<div class="card">
    <h2>백테스트 결과</h2>
    <p>전략: {strategy_name}</p>
    <p>분할수: {split_count}</p>
    <p>현금: {cash:,.0f}원</p>
    <p>주식가치: {stock_value:,.0f}원</p>
    <p>현재 분할 상태: {current_split} / {split_count}</p>
    <p>수수료율: 매수 {fee_percent:.3f}% / 매도 {fee_percent:.3f}%</p>
</div>

{trade_log_html}

<div class="card">
    <h2>통합 차트: 총자산 + {ticker} 가격 + 매수/매도 포인트</h2>
    <div class="chart-box">
        <canvas id="assetChart"></canvas>
    </div>
</div>

<div class="card">
    <h2>Drawdown</h2>
    <div class="chart-box">
        <canvas id="ddChart"></canvas>
    </div>
</div>

<div class="card">
    <h2>월별 수익률</h2>
    <div class="chart-box">
        <canvas id="monthlyChart"></canvas>
    </div>
</div>

<script>
const chartData = {chart_json};

const labels = chartData.labels || [];
const assets = chartData.assets || [];
const prices = chartData.prices || [];
const drawdowns = chartData.drawdown || [];
const buyPoints = chartData.buy_points || [];
const sellPoints = chartData.sell_points || [];
const monthLabels = chartData.month_labels || [];
const monthReturns = chartData.month_return || [];
const yearlyLabels = chartData.yearly_labels || [];
const yearlyStrategyReturns = chartData.yearly_strategy_returns || [];
const yearlyQqqReturns = chartData.yearly_qqq_returns || [];

function won(value) {{
    return Number(value).toLocaleString() + "원";
}}

function pct(value) {{
    return Number(value).toFixed(2) + "%";
}}

new Chart(document.getElementById("assetChart"), {{
    type: "line",
    data: {{
        labels: labels,
        datasets: [
            {{
                label: "총자산",
                data: assets,
                borderColor: "#2196f3",
                backgroundColor: "#2196f3",
                borderWidth: 2,
                pointRadius: 0,
                yAxisID: "y"
            }},
            {{
                label: "{ticker} 가격",
                data: prices,
                borderColor: "#ff6b8a",
                backgroundColor: "#ff6b8a",
                borderWidth: 1,
                pointRadius: 0,
                yAxisID: "y1"
            }},
            {{
                label: "매수",
                data: buyPoints,
                borderColor: "green",
                backgroundColor: "green",
                borderWidth: 0,
                pointRadius: 6,
                pointHoverRadius: 8,
                pointStyle: "triangle",
                showLine: false,
                yAxisID: "y1"
            }},
            {{
                label: "매도",
                data: sellPoints,
                borderColor: "red",
                backgroundColor: "red",
                borderWidth: 0,
                pointRadius: 7,
                pointHoverRadius: 9,
                pointStyle: "rectRot",
                showLine: false,
                yAxisID: "y1"
            }}
        ]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{
            mode: "index",
            intersect: false
        }},
        plugins: {{
            tooltip: {{
                callbacks: {{
                    label: function(context) {{
                        if (context.dataset.label === "총자산") {{
                            return context.dataset.label + ": " + won(context.raw);
                        }}
                        if (context.dataset.label === "{ticker} 가격" || context.dataset.label === "매수" || context.dataset.label === "매도") {{
                            return context.dataset.label + ": $" + Number(context.raw).toFixed(2);
                        }}
                        return context.dataset.label + ": " + context.raw;
                    }}
                }}
            }}
        }},
        scales: {{
            x: {{
                ticks: {{
                    maxTicksLimit: 12,
                    maxRotation: 45,
                    minRotation: 45
                }}
            }},
            y: {{
                type: "linear",
                position: "left"
            }},
            y1: {{
                type: "linear",
                position: "right",
                grid: {{
                    drawOnChartArea: false
                }}
            }}
        }}
    }}
}});

new Chart(document.getElementById("ddChart"), {{
    type: "line",
    data: {{
        labels: labels,
        datasets: [{{
            label: "Drawdown (%)",
            data: drawdowns,
            borderColor: "#2563eb",
            backgroundColor: "#2563eb",
            borderWidth: 2,
            pointRadius: 0
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{
            mode: "index",
            intersect: false
        }},
        plugins: {{
            tooltip: {{
                callbacks: {{
                    label: function(context) {{
                        return "Drawdown: " + pct(context.raw);
                    }}
                }}
            }}
        }},
        scales: {{
            x: {{
                ticks: {{
                    maxTicksLimit: 12,
                    maxRotation: 45,
                    minRotation: 45
                }}
            }},
            y: {{
                ticks: {{
                    callback: function(value) {{
                        return value + "%";
                    }}
                }}
            }}
        }}
    }}
}});

new Chart(document.getElementById("monthlyChart"), {{
    type: "bar",
    data: {{
        labels: monthLabels,
        datasets: [{{
            label: "월별 수익률 (%)",
            data: monthReturns,
            backgroundColor: "#90caf9",
            borderColor: "#42a5f5",
            borderWidth: 1
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{
            mode: "index",
            intersect: false
        }},
        plugins: {{
            tooltip: {{
                callbacks: {{
                    label: function(context) {{
                        return "월 수익률: " + pct(context.raw);
                    }}
                }}
            }}
        }},
        scales: {{
            x: {{
                ticks: {{
                    maxTicksLimit: 12,
                    maxRotation: 45,
                    minRotation: 45
                }}
            }},
            y: {{
                ticks: {{
                    callback: function(value) {{
                        return value + "%";
                    }}
                }}
            }}
        }}
    }}
}});

new Chart(document.getElementById("yearlyChart"), {{
    type: "bar",
    data: {{
        labels: yearlyLabels,
        datasets: [
            {{
                label: "전략 수익률",
                data: yearlyStrategyReturns,
                backgroundColor: "#2196f3"
            }},
            {{
                label: "{ticker} 수익률",
                data: yearlyQqqReturns,
                backgroundColor: "#ff6b8a"
            }}
        ]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{
            mode: "index",
            intersect: false
        }},
        plugins: {{
            tooltip: {{
                callbacks: {{
                    label: function(context) {{
                        return context.dataset.label + ": " + pct(context.raw);
                    }}
                }}
            }}
        }},
        scales: {{
            x: {{
                ticks: {{
                    maxTicksLimit: 12,
                    maxRotation: 45,
                    minRotation: 45
                }}
            }},
            y: {{
                ticks: {{
                    callback: function(value) {{
                        return value + "%";
                    }}
                }}
            }}
        }}
    }}
}});
</script>

</body>
</html>
"""

    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
