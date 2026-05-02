"""
Step25D-2 - 라오어 무한매수법 V2.2 통합 원문기준 백테스트 엔진

기준 source:
- 사용자가 새로 제공한 사진/정리 순서 기준.
- 기존 zip 해석보다 새 이미지 기준을 우선한다.
- V2.2와 V4.0을 섞지 않는다.
- V2.2 기본형/수치변화는 사용자-facing 버전으로 나누지 않는다.
- 하나의 V2.2 전략 안에서 TQQQ/SOXL별 원문 공식만 자동 적용한다.

핵심 원칙:
- 별% LOC 지점은 매수/매도 공통 1개다.
- 실제 별LOC 매수가는 별가격 - 0.01, 별LOC 매도가는 별가격 그대로다.
- 전반전: 1회 매수분 1/2은 0% LOC, 1/2은 별% LOC.
- 후반전: 1회 매수분 전체를 별% LOC.
- 매도는 전후반 공통: 보유 1/4 별LOC, 보유 3/4 지정가.
- TQQQ 공식: 별%=10-T/2*(40/a), 지정가 10%.
- SOXL 공식: 별%=12-T*0.6*(40/a), 지정가 12%.
- 기본 체결가는 주문가격 체결로 둔다. LOC 신호는 일봉 종가 기준으로 판단한다.

주의:
- 첫매수의 세부 원문은 현재 사진 묶음에서 V4.0처럼 명확히 별도 설명되지 않았으므로,
  백테스트 시작용 첫매수는 전날종가 대비 first_loc_buffer_pct LOC로 체결보장형 진입한다.
  로그에 FirstBuyPolicy=bootstrap_prev_close_buffer 로 남긴다.
- 큰수매수는 주문거부/RPA 예외옵션이므로 기본 백테스트 로직에는 넣지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import pandas as pd

SUPPORTED_TICKERS = {"TQQQ", "SOXL"}
EPS = 1e-10


def _num(x, default=0.0):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def normalize_ticker(ticker: str) -> str:
    ticker = str(ticker or "").upper().strip()
    if ticker not in SUPPORTED_TICKERS:
        raise ValueError(f"V2.2 통합 원문엔진은 TQQQ/SOXL만 지원합니다. 입력={ticker}")
    return ticker


def calc_v22_star_pct(ticker: str, split_count: int, T: float) -> float:
    ticker = normalize_ticker(ticker)
    a = float(split_count)
    T = float(T)
    if a <= 0:
        raise ValueError("분할수는 0보다 커야 합니다.")
    if ticker == "TQQQ":
        return 10.0 - (T / 2.0) * (40.0 / a)
    return 12.0 - T * 0.6 * (40.0 / a)


def calc_v22_designated_pct(ticker: str) -> float:
    return 10.0 if normalize_ticker(ticker) == "TQQQ" else 12.0


def calc_v22_quarter_pct(ticker: str) -> float:
    return -10.0 if normalize_ticker(ticker) == "TQQQ" else -12.0


@dataclass
class V22State:
    cash: float
    unit_amount: float
    shares: float = 0.0
    cost_basis: float = 0.0
    cycle_id: int = 0
    cycle_start_date: pd.Timestamp | None = None
    last_buy_date: pd.Timestamp | None = None
    quarter_mode: bool = False
    quarter_round: int = 0
    quarter_unit_amount: float = 0.0

    @property
    def avg_price(self) -> float:
        return self.cost_basis / self.shares if self.shares > EPS else 0.0

    @property
    def T(self) -> float:
        # V2.2 백테스트에서는 현재 누적 매수원가 / 고정 1회매수금으로 진행률을 추적한다.
        return self.cost_basis / self.unit_amount if self.unit_amount > EPS else 0.0


def _phase_v22(T: float, split_count: int, quarter_mode: bool = False) -> str:
    if quarter_mode:
        return "쿼터손절"
    if T <= EPS:
        return "무포지션"
    if T < float(split_count) / 2.0:
        return "전반전"
    return "후반전"


def _buy(state: V22State, date, price: float, amount: float, fee_rate: float, logs: List[Dict] | None = None, reason: str = ""):
    """V2.2 원칙 매수 실행. Step25D-6-2는 계산은 유지하고 체결 이벤트 로그만 보강한다."""
    if price <= 0 or amount <= 0 or state.cash <= 0:
        return 0.0, 0.0, 0.0

    cash_before = state.cash
    shares_before = state.shares
    avg_before = state.avg_price
    t_before = state.T
    cycle_was_empty = state.cycle_start_date is None

    gross = min(float(amount), state.cash / (1.0 + fee_rate))
    if gross <= 0:
        return 0.0, 0.0, 0.0
    fee = gross * fee_rate
    qty = gross / price
    state.cash -= gross + fee
    state.shares += qty
    state.cost_basis += gross
    if state.cycle_start_date is None:
        state.cycle_id += 1
        state.cycle_start_date = date
    state.last_buy_date = date

    if logs is not None:
        cycle_start = state.cycle_start_date or date
        logs.append({
            "LogType": "TradeEvent", "EventSide": "BUY", "EventType": "BUY",
            "EventDate": date, "LastActionDate": date,
            "CycleId": state.cycle_id, "CycleStartDate": cycle_start,
            "BuyDate": date, "BuyEventDate": date, "LastBuyDate": date,
            "SellDate": pd.NaT, "SellEventDate": pd.NaT,
            "HoldDays": 0, "LastBuyHoldDays": 0, "CycleEndDate": pd.NaT,
            "BuyAmount": gross, "SellAmount": 0.0, "Profit": 0.0, "ReturnPct": 0.0,
            "Reason": reason or "V2.2 LOC매수", "BuyPrice": price, "SellPrice": 0.0,
            "SharesBought": qty, "SharesSold": 0.0,
            "BuyFraction": gross / state.unit_amount if state.unit_amount > EPS else 0.0,
            "SellFraction": 0.0, "OrderType": "BUY", "OrderPrice": price, "OrderQty": qty,
            "HoldingQtyBefore": shares_before, "HoldingQtyAfter": state.shares,
            "AvgPriceBefore": avg_before, "AvgPriceAfter": state.avg_price,
            "TBefore": t_before, "TAfter": state.T,
            "CashBefore": cash_before, "CashAfter": state.cash,
            "CycleStartedByThisEvent": bool(cycle_was_empty), "CycleCompleted": False,
        })
    return gross, fee, qty

def _sell(state: V22State, date, price: float, fraction: float, fee_rate: float, reason: str, logs: List[Dict]):
    if price <= 0 or fraction <= 0 or state.shares <= EPS:
        return 0.0, 0.0, 0.0
    fraction = min(1.0, max(0.0, float(fraction)))
    qty = state.shares * fraction
    gross = qty * price
    fee = gross * fee_rate
    net = gross - fee
    cost_sold = state.cost_basis * fraction
    profit = net - cost_sold
    ret = profit / cost_sold * 100.0 if cost_sold > EPS else 0.0
    full = fraction >= 0.999999 or state.shares - qty <= EPS
    cycle_start = state.cycle_start_date or date
    last_buy = state.last_buy_date or cycle_start
    hold_days = (pd.to_datetime(date) - pd.to_datetime(cycle_start)).days if cycle_start is not None else 0
    last_buy_hold_days = (pd.to_datetime(date) - pd.to_datetime(last_buy)).days if last_buy is not None else 0

    logs.append({
        "LogType": "TradeEvent",
        "EventSide": "SELL",
        "EventType": "SELL",
        "EventDate": date,
        "LastActionDate": date,
        "CycleId": state.cycle_id,
        "CycleStartDate": cycle_start,
        "BuyDate": cycle_start,
        "BuyEventDate": pd.NaT,
        "LastBuyDate": last_buy,
        "SellDate": date,
        "SellEventDate": date,
        "HoldDays": hold_days,
        "LastBuyHoldDays": last_buy_hold_days,
        "CycleEndDate": date if full else pd.NaT,
        "BuyAmount": cost_sold,
        "SellAmount": net,
        "Profit": profit,
        "ReturnPct": ret,
        "Reason": reason,
        "BuyPrice": 0.0,
        "SellPrice": price,
        "SharesBought": 0.0,
        "SharesSold": qty,
        "BuyFraction": 0.0,
        "SellFraction": fraction,
        "OrderType": "SELL",
        "OrderPrice": price,
        "OrderQty": qty,
        "HoldingQtyBefore": state.shares,
        "HoldingQtyAfter": state.shares - qty,
        "AvgPriceBefore": state.avg_price,
        "AvgPriceAfter": state.avg_price if not full else 0.0,
        "TBefore": state.T,
        "TAfter": max(0.0, state.T * (1.0 - fraction)),
        "CashBefore": state.cash,
        "CashAfter": state.cash + net,
        "CycleStartedByThisEvent": False,
        "CycleCompleted": bool(full),
    })
    state.cash += net
    state.shares -= qty
    state.cost_basis -= cost_sold
    if state.shares <= EPS or state.cost_basis <= 1e-6:
        state.shares = 0.0
        state.cost_basis = 0.0
        state.cycle_start_date = None
        state.last_buy_date = None
        state.quarter_mode = False
        state.quarter_round = 0
        state.quarter_unit_amount = 0.0
    return net, profit, qty


def _add_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df["Peak"] = df["TotalAsset"].cummax()
    df["Drawdown"] = (df["TotalAsset"] - df["Peak"]) / df["Peak"]
    df["DailyReturn"] = df["TotalAsset"].pct_change().fillna(0) * 100
    return df


def run_raor_v22_core(
    daily_df: pd.DataFrame,
    ticker: str = "TQQQ",
    split_count: int = 40,
    initial_cash: float = 100_000_000,
    fee_rate_pct: float = 0.1,
    first_loc_buffer_pct: float = 12.0,
    enable_quarter_loss: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    ticker = normalize_ticker(ticker)
    split_count = int(split_count)
    if split_count <= 0:
        raise ValueError("분할수는 1 이상이어야 합니다.")

    df = daily_df.copy()
    if "Date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "Date"})
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    if "Close" not in df.columns:
        raise ValueError("daily_df에 Close 컬럼이 필요합니다.")
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df = df.dropna(subset=["Close"]).reset_index(drop=True)
    for col in ["Open", "High", "Low"]:
        if col not in df.columns:
            df[col] = df["Close"]
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(df["Close"])

    fee_rate = float(fee_rate_pct) / 100.0
    unit_amount = float(initial_cash) / float(split_count)
    state = V22State(cash=float(initial_cash), unit_amount=unit_amount)
    rows: List[Dict] = []
    trades: List[Dict] = []
    designated_pct = calc_v22_designated_pct(ticker)
    quarter_pct = calc_v22_quarter_pct(ticker)

    for i, row in df.iterrows():
        date = row["Date"]
        close = float(row["Close"])
        high = float(row.get("High", close))
        prev_close = float(df.loc[i - 1, "Close"]) if i > 0 else close
        action: List[str] = []
        plan: List[str] = []
        debug: List[str] = []
        t_before = state.T
        avg_before = state.avg_price
        phase_before = _phase_v22(t_before, split_count, state.quarter_mode)
        star_pct_before = calc_v22_star_pct(ticker, split_count, t_before) if t_before > EPS else 0.0
        star_price_before = avg_before * (1.0 + star_pct_before / 100.0) if avg_before > 0 else 0.0
        buy_loc_before = star_price_before - 0.01 if star_price_before > 0 else 0.0
        designated_price_before = avg_before * (1.0 + designated_pct / 100.0) if avg_before > 0 else 0.0
        buy_signal = sell_signal = designated_signal = False
        buy_exec = sell_exec = designated_exec = False
        overlap = bool(buy_loc_before > 0 and star_price_before > 0 and buy_loc_before >= star_price_before)
        sold_today = False

        # 쿼터손절 발동: 40분할 기준 39<T<=40에 해당하는 일반화 조건. 최초 1/4 MOC 매도.
        if enable_quarter_loss and (not state.quarter_mode) and state.shares > EPS and t_before > (split_count - 1.0) and t_before <= split_count + 1e-6:
            _sell(state, date, close, 0.25, fee_rate, f"V2.2 쿼터손절 시작 MOC 25% / T={t_before:.4f}", trades)
            state.quarter_mode = True
            state.quarter_round = 0
            state.quarter_unit_amount = min(state.unit_amount, max(0.0, state.cash) / 10.0)
            action.append("쿼터손절시작MOC")
            sold_today = True
            debug.append(f"QuarterLossStart: T={t_before:.4f}, quarter_unit={state.quarter_unit_amount:,.0f}")

        # 매도 예약: 전후반 공통. 지정가 75%, 별LOC 25%.
        if state.shares > EPS and not sold_today:
            if state.quarter_mode:
                q_loc_price = state.avg_price * (1.0 + quarter_pct / 100.0)
                q_designated = state.avg_price * (1.0 + designated_pct / 100.0)
                designated_signal = high >= q_designated
                sell_signal = close >= q_loc_price
                if designated_signal:
                    _sell(state, date, q_designated, 0.75, fee_rate, f"V2.2 쿼터손절 지정가75 {designated_pct:.0f}%", trades)
                    action.append("쿼터지정가75매도")
                    designated_exec = True
                    sold_today = True
                if state.shares > EPS and sell_signal:
                    _sell(state, date, q_loc_price, 1.0 if designated_signal else 0.25, fee_rate, f"V2.2 쿼터손절 LOC매도 {quarter_pct:.0f}%", trades)
                    action.append("쿼터LOC매도")
                    sell_exec = True
                    sold_today = True
                    if state.shares > EPS:
                        state.quarter_mode = False
                        state.quarter_round = 0
                        action.append("후반전복귀")
                plan.append(f"쿼터매도예약: LOC {quarter_pct:.0f}% @{q_loc_price:.2f}, 지정가 {designated_pct:.0f}% @{q_designated:.2f}")
            else:
                designated_signal = designated_price_before > 0 and high >= designated_price_before
                sell_signal = star_price_before > 0 and close >= star_price_before
                if designated_signal:
                    _sell(state, date, designated_price_before, 0.75, fee_rate, f"V2.2 지정가75 {designated_pct:.0f}%", trades)
                    action.append("지정가75매도")
                    designated_exec = True
                    sold_today = True
                if state.shares > EPS and sell_signal:
                    _sell(state, date, star_price_before, 1.0 if designated_signal else 0.25, fee_rate, f"V2.2 별LOC매도 25% / 별% {star_pct_before:.4f}%", trades)
                    action.append("별LOC매도")
                    sell_exec = True
                    sold_today = True
                plan.append(f"매도예약: 별LOC25 @{star_price_before:.2f}, 지정가75 @{designated_price_before:.2f}")

        # 매수: 동일 일자 매도 후 매수는 일봉 선후관계 과최적화를 피하기 위해 기본 차단.
        if not sold_today:
            if state.shares <= EPS or state.T <= EPS:
                if i > 0:
                    first_loc = prev_close * (1.0 + float(first_loc_buffer_pct) / 100.0)
                    buy_signal = close <= first_loc
                    if buy_signal:
                        gross, fee, qty = _buy(state, date, first_loc, state.unit_amount, fee_rate, trades, "V2.2 첫매수 LOC / bootstrap_prev_close_buffer")
                        if gross > 0:
                            action.append("첫매수LOC")
                            buy_exec = True
                    plan.append(f"첫매수: 전날종가×{1+first_loc_buffer_pct/100:.3f} LOC @{first_loc:.2f} / FirstBuyPolicy=bootstrap_prev_close_buffer")
                else:
                    action.append("첫날대기")
            elif state.quarter_mode:
                q_buy_price = state.avg_price * (1.0 + quarter_pct / 100.0)
                amount = state.quarter_unit_amount if state.quarter_unit_amount > 0 else min(state.unit_amount, state.cash / 10.0)
                buy_signal = close <= q_buy_price
                if buy_signal and state.quarter_round < 10:
                    gross, fee, qty = _buy(state, date, q_buy_price, amount, fee_rate, trades, f"V2.2 쿼터손절 LOC매수 {quarter_pct:.0f}%")
                    if gross > 0:
                        state.quarter_round += 1
                        action.append(f"쿼터LOC매수{state.quarter_round}")
                        buy_exec = True
                plan.append(f"쿼터매수: LOC {quarter_pct:.0f}% @{q_buy_price:.2f}, round={state.quarter_round}/10")
                if state.quarter_round >= 10 and state.shares > EPS:
                    _sell(state, date, close, 0.25, fee_rate, "V2.2 쿼터손절 10회 소진 후 MOC 25%", trades)
                    action.append("쿼터10회후MOC")
                    state.quarter_round = 0
                    state.quarter_unit_amount = min(state.unit_amount, max(0.0, state.cash) / 10.0)
                    sold_today = True
            else:
                avg_now = state.avg_price
                T_now = state.T
                star_pct_now = calc_v22_star_pct(ticker, split_count, T_now)
                star_price_now = avg_now * (1.0 + star_pct_now / 100.0)
                star_buy = star_price_now - 0.01
                if T_now < split_count / 2.0:
                    # 전반전: 0% LOC 절반 + 별LOC 절반
                    half = state.unit_amount * 0.5
                    if close <= avg_now:
                        gross, fee, qty = _buy(state, date, avg_now, half, fee_rate, trades, "V2.2 전반전 0% LOC매수 0.5T")
                        if gross > 0:
                            action.append("전반전0%LOC")
                            buy_exec = True
                            buy_signal = True
                    if close <= star_buy:
                        gross, fee, qty = _buy(state, date, star_buy, half, fee_rate, trades, f"V2.2 전반전 별LOC매수 0.5T / 별% {star_pct_now:.4f}%")
                        if gross > 0:
                            action.append("전반전별LOC")
                            buy_exec = True
                            buy_signal = True
                    plan.append(f"전반전매수: 0%LOC @{avg_now:.2f} 0.5T + 별LOC @{star_buy:.2f} 0.5T")
                else:
                    # 후반전: 별LOC 1T
                    if close <= star_buy:
                        gross, fee, qty = _buy(state, date, star_buy, state.unit_amount, fee_rate, trades, f"V2.2 후반전 별LOC매수 1T / 별% {star_pct_now:.4f}%")
                        if gross > 0:
                            action.append("후반전별LOC")
                            buy_exec = True
                            buy_signal = True
                    plan.append(f"후반전매수: 별LOC @{star_buy:.2f} 1T")

        if not action:
            action.append("관망")

        t_after = state.T
        avg_after = state.avg_price
        phase_after = _phase_v22(t_after, split_count, state.quarter_mode)
        star_pct_after = calc_v22_star_pct(ticker, split_count, t_after) if t_after > EPS else 0.0
        star_price_after = avg_after * (1.0 + star_pct_after / 100.0) if avg_after > 0 else 0.0
        total_asset = state.cash + state.shares * close
        ambiguous = sum([bool(buy_signal), bool(sell_signal), bool(designated_signal)]) >= 2
        rows.append({
            "Date": date,
            "Close": close,
            "High": high,
            "Mode": phase_after,
            "PhaseBefore": phase_before,
            "PhaseAfter": phase_after,
            "Action": "+".join(action),
            "Cash": state.cash,
            "Shares": state.shares,
            "StockValue": state.shares * close,
            "TotalAsset": total_asset,
            "CurrentSplit": t_after,
            "T": t_after,
            "TBefore": t_before,
            "TAfter": t_after,
            "TDelta": t_after - t_before,
            "AvgPrice": avg_after,
            "StarPct": star_pct_after,
            "StarPrice": star_price_after,
            "BuyLOCPrice": star_price_after - 0.01 if star_price_after > 0 else 0.0,
            "SellLOCPrice": star_price_after,
            "DesignatedSellPct": designated_pct,
            "DesignatedSellPrice": avg_after * (1.0 + designated_pct / 100.0) if avg_after > 0 else 0.0,
            "OrderPlan": " || ".join(plan),
            "Reason": "+".join(action),
            "CycleId": state.cycle_id,
            "CycleStartDate": state.cycle_start_date,
            "CycleCompleted": False,
            "BuyLOCSignal": bool(buy_signal),
            "SellLOCSignal": bool(sell_signal),
            "DesignatedSellSignal": bool(designated_signal),
            "BuyLOCExecuted": bool(buy_exec),
            "SellLOCExecuted": bool(sell_exec),
            "DesignatedSellExecuted": bool(designated_exec),
            "BuySellPriceOverlap": bool(overlap),
            "DailyCandleOrderAmbiguous": bool(ambiguous),
            "QuarterMode": bool(state.quarter_mode),
            "QuarterRound": int(state.quarter_round),
            "RaorDebug": " | ".join(debug),
        })

    trade_events = pd.DataFrame(trades)
    if not trade_events.empty and "EventDate" in trade_events.columns:
        trade_events = trade_events.sort_values(["EventDate", "CycleId", "EventSide"]).reset_index(drop=True)
    return _add_metrics(pd.DataFrame(rows)), trade_events


run_raor_v22_backtest = run_raor_v22_core
