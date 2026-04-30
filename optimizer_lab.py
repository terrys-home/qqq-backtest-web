"""
Step22D Infinite Lab Core Optimizer
사용법:
python optimizer_lab.py TQQQ rsi
python optimizer_lab.py TQQQ infinite4_v3
python optimizer_lab.py TQQQ infinite4_v4
python optimizer_lab.py TQQQ infinite4_v5
python optimizer_lab.py TQQQ raor4_step24p
python optimizer_lab.py TQQQ raor4_step24o
python optimizer_lab.py TQQQ raor4_step24n
python optimizer_lab.py TQQQ raor4_step24m

주의:
- 자동주문/RPA 없음
- 백테스트/판단엔진 최적화 전용
"""

import itertools
import sys
from pathlib import Path
import pandas as pd
import app as lab
from ticker_config import TICKER_LIST


def profit_factor(trade_df):
    if trade_df.empty or "Profit" not in trade_df.columns:
        return 0.0
    gp = trade_df.loc[trade_df["Profit"] > 0, "Profit"].sum()
    gl = abs(trade_df.loc[trade_df["Profit"] < 0, "Profit"].sum())
    return float(gp / gl) if gl > 0 else (float(gp) if gp > 0 else 0.0)


def summarize(bt, trade_df):
    final_asset = float(bt.iloc[-1]["TotalAsset"])
    total_return = (final_asset / lab.INITIAL_CASH - 1) * 100
    cagr = lab.calc_cagr(bt)
    mdd = float(bt["Drawdown"].min() * 100)
    ts = lab.make_trade_summary(trade_df, bt)
    train, test, cagr_drop, mdd_worse, *_ = lab.make_walkforward_summary(bt)
    stability, overfit_risk, _ = lab.calc_stability_score(train, test, mdd_worse)
    pf = profit_factor(trade_df)
    risk_penalty = {"낮음": 0, "보통": 5, "높음": 15}.get(overfit_risk, 10)
    score = (cagr * 2.2) + (stability * 0.45) + (min(pf, 5) * 5) - (abs(mdd) * 0.45) - risk_penalty
    return {
        "FinalAsset": round(final_asset, 0),
        "Return": round(total_return, 2),
        "CAGR": round(cagr, 2),
        "MDD": round(mdd, 2),
        "WinRate": round(ts.get("win_rate", 0), 2),
        "Trades": ts.get("trade_count", 0),
        "AvgHoldDays": ts.get("avg_hold_days", 0),
        "MaxHoldDays_Actual": ts.get("max_hold_days", 0),
        "ProfitFactor": round(pf, 2),
        "IS_CAGR": round(train.get("cagr", 0), 2),
        "OOS_CAGR": round(test.get("cagr", 0), 2),
        "MDD_Worse": round(mdd_worse, 2),
        "StabilityScore": round(stability, 1),
        "OverfitRisk": overfit_risk,
        "Score": round(score, 2),
    }


def iter_params(strategy):
    if strategy == "rsi":
        for vals in itertools.product(
            [8, 10, 12, 15, 20],
            [60, 65, 70, 75, 80],
            [2, 3, 4, 5, 6],
            [1, 2, 3, 4],
            [1, 2],
            [0, 1],
        ):
            split_count, sell_rsi, extreme, recession, neutral, boom = vals
            if extreme < recession:
                continue
            yield {
                "split_count": split_count,
                "sell_rsi": sell_rsi,
                "extreme_split": extreme,
                "recession_split": recession,
                "neutral_split": neutral,
                "boom_split": boom,
            }

    elif strategy in ["raor4_step24m", "raor4_step24n", "raor4_step24o", "raor4_step24p"]:
        for vals in itertools.product(
            [20, 40],
            [10, 12, 15],
            [10, 12.5, 15, 17.5, 20, 22.5, 25],
        ):
            split_count, first_loc_buffer_pct, designated_sell_pct = vals
            yield {
                "split_count": split_count,
                "first_loc_buffer_pct": first_loc_buffer_pct,
                "designated_sell_pct_override": designated_sell_pct,
            }

    elif strategy in ["raor4_step24e", "raor4_step24f", "raor4_step24g", "raor4_step24h", "raor4_step24l"]:
        for vals in itertools.product(
            [20, 40],      # split_count: 원문 별% 공식이 명시된 값만
            [10, 12, 15],  # first_loc_buffer_pct: 원문 첫매수 +10~15%
        ):
            split_count, first_loc_buffer_pct = vals
            yield {
                "split_count": split_count,
                "first_loc_buffer_pct": first_loc_buffer_pct,
            }

    elif strategy in ["infinite4", "infinite4_v2", "infinite4_v3", "infinite4_v4", "infinite4_v5"]:
        for vals in itertools.product(
            [20, 30, 40],      # split_count
            [5, 7, 10],        # target_profit
            [25],              # quarter_sell_ratio
            [5, 7, 10],        # star_pct
            [15, 20],          # max_gap_pct
            [180, 365, 540],   # max_hold_days
        ):
            split_count, target_profit, quarter_sell_ratio, star_pct, max_gap_pct, max_hold_days = vals
            params = {
                "split_count": split_count,
                "target_profit": target_profit,
                "quarter_sell_ratio": quarter_sell_ratio,
                "star_pct": star_pct,
                "max_gap_pct": max_gap_pct,
                "max_hold_days": max_hold_days,
            }
            if strategy in ["infinite4", "infinite4_v2"]:
                params.pop("max_hold_days", None)
            yield params
    else:
        raise ValueError(strategy)


def run_one(strategy, params, fee_percent=0.25):
    if strategy == "rsi":
        return lab.run_backtest(fee_rate_pct=fee_percent, **params)
    if strategy == "infinite4":
        p = dict(params)
        p.pop("max_gap_pct", None)
        p.pop("max_hold_days", None)
        return lab.run_infinite4_v1_backtest(fee_rate_pct=fee_percent, **p)
    if strategy == "infinite4_v2":
        p = dict(params)
        p.pop("max_hold_days", None)
        return lab.run_infinite4_v2_backtest(fee_rate_pct=fee_percent, **p)
    if strategy == "infinite4_v3":
        return lab.run_infinite4_v3_backtest(fee_rate_pct=fee_percent, **params)
    if strategy == "infinite4_v4":
        return lab.run_infinite4_v4_backtest(fee_rate_pct=fee_percent, **params)
    if strategy == "infinite4_v5":
        return lab.run_infinite4_v5_backtest(fee_rate_pct=fee_percent, **params)
    if strategy == "raor4_step24e":
        return lab.run_raor_infinite4_step24e_backtest(ticker=lab.current_ticker if hasattr(lab, "current_ticker") else "TQQQ", fee_rate_pct=fee_percent, **params)
    if strategy == "raor4_step24f":
        return lab.run_raor_infinite4_step24f_backtest(ticker=lab.current_ticker if hasattr(lab, "current_ticker") else "TQQQ", fee_rate_pct=fee_percent, **params)
    if strategy == "raor4_step24p":
        return lab.run_raor_infinite4_step24p_backtest(ticker=lab.current_ticker if hasattr(lab, "current_ticker") else "TQQQ", fee_rate_pct=fee_percent, **params)
    if strategy == "raor4_step24o":
        return lab.run_raor_infinite4_step24o_backtest(ticker=lab.current_ticker if hasattr(lab, "current_ticker") else "TQQQ", fee_rate_pct=fee_percent, **params)
    if strategy == "raor4_step24n":
        return lab.run_raor_infinite4_step24n_backtest(ticker=lab.current_ticker if hasattr(lab, "current_ticker") else "TQQQ", fee_rate_pct=fee_percent, **params)
    if strategy == "raor4_step24m":
        return lab.run_raor_infinite4_step24m_backtest(ticker=lab.current_ticker if hasattr(lab, "current_ticker") else "TQQQ", fee_rate_pct=fee_percent, **params)
    if strategy == "raor4_step24l":
        return lab.run_raor_infinite4_step24l_backtest(ticker=lab.current_ticker if hasattr(lab, "current_ticker") else "TQQQ", fee_rate_pct=fee_percent, **params)

    if strategy == "raor4_step24h":
        return lab.run_raor_infinite4_step24h_backtest(ticker=lab.current_ticker if hasattr(lab, "current_ticker") else "TQQQ", fee_rate_pct=fee_percent, **params)
    if strategy == "raor4_step24g":
        return lab.run_raor_infinite4_step24g_backtest(ticker=lab.current_ticker if hasattr(lab, "current_ticker") else "TQQQ", fee_rate_pct=fee_percent, **params)
    raise ValueError(strategy)


def optimize(ticker, strategy, fee_percent=0.25):
    ticker = ticker.upper()
    if ticker not in TICKER_LIST:
        raise SystemExit(f"지원하지 않는 티커: {ticker}. ticker_config.py에 추가하세요.")

    daily, weekly = lab.load_ticker_data(ticker)
    if daily is None:
        raise SystemExit(f"{ticker} 데이터 없음. 먼저 python update_data.py {ticker}")

    lab.daily, lab.weekly = daily, weekly
    lab.current_ticker = ticker
    rows = []

    for i, params in enumerate(iter_params(strategy), 1):
        bt, trade_df = run_one(strategy, params, fee_percent)
        rows.append({"Ticker": ticker, "Strategy": strategy, **params, **summarize(bt, trade_df)})
        if i % 50 == 0:
            print(f"진행: {i}개 조합")

    df = pd.DataFrame(rows)
    return df.sort_values(["Score", "StabilityScore", "CAGR"], ascending=False).reset_index(drop=True)


def main():
    ticker = sys.argv[1].upper() if len(sys.argv) >= 2 else "QQQ"
    strategy = sys.argv[2] if len(sys.argv) >= 3 else "rsi"
    fee = float(sys.argv[3]) if len(sys.argv) >= 4 else 0.25

    df = optimize(ticker, strategy, fee)
    out = Path(f"{ticker}_{strategy}_optimizer_top100.csv")
    df.head(100).to_csv(out, index=False, encoding="utf-8-sig")
    print(f"완료: {out}")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
