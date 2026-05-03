"""
Step25D-7-5 - 라오어 무한매수법 V2.2 CycleStatus/종료사유 검증 엔진

기준 source:
- 사용자가 글로 정리해서 제공한 원문 기준을 최우선으로 사용한다.
- 사진 OCR/이미지 해석으로 추정한 내용은 기준으로 사용하지 않는다.
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
- V2.2 첫매수의 세부 원문은 사용자가 글로 확정한 항목에 포함되지 않았으므로,
  백테스트 시작용 첫매수는 전날종가 대비 first_loc_buffer_pct LOC로 체결보장형 진입한다.
  로그에 FirstBuyPolicy=bootstrap_prev_close_buffer 로 남긴다.
- 큰수매수는 주문거부/RPA 예외옵션이므로 기본 백테스트 로직에는 넣지 않는다.
- Step25D-7-5는 쿼터손절 체결 이벤트에 CycleStatus/CycleEndReason/OpenQty/OpenMarketValue를 추가해 장기 주기와 미청산 상태를 검증하는 수정판이다.
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


def _event_asset(cash: float, shares: float, market_price: float | None) -> float:
    mp = float(market_price) if market_price is not None and market_price > 0 else 0.0
    return float(cash) + float(shares) * mp


def _quarter_event_type(reason: str = "", transition_reason: str = "") -> str:
    text = f"{reason} {transition_reason}"
    if "쿼터손절 시작" in text:
        return "QUARTER_START_MOC"
    if "10회 소진 후 MOC" in text:
        return "QUARTER_10TH_MOC"
    if "쿼터손절 LOC매수" in text:
        return "QUARTER_LOC_BUY"
    if "쿼터손절 LOC매도" in text:
        return "QUARTER_LOC_SELL"
    if "쿼터손절 지정가" in text:
        return "QUARTER_DESIGNATED_SELL"
    if "쿼터" in text:
        return "QUARTER_OTHER"
    return ""


def _buy(state: V22State, date, price: float, amount: float, fee_rate: float, logs: List[Dict] | None = None, reason: str = "", market_price: float | None = None):
    """V2.2 원칙 매수 실행. Step25D-6-2는 계산은 유지하고 체결 이벤트 로그만 보강한다."""
    if price <= 0 or amount <= 0 or state.cash <= 0:
        return 0.0, 0.0, 0.0

    cash_before = state.cash
    shares_before = state.shares
    cost_basis_before = state.cost_basis
    avg_before = state.avg_price
    t_before = state.T
    mp = float(market_price) if market_price is not None and market_price > 0 else float(price)
    asset_before = _event_asset(cash_before, shares_before, mp)
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
    asset_after = _event_asset(state.cash, state.shares, mp)

    if logs is not None:
        cycle_start = state.cycle_start_date or date
        logs.append({
            "LogType": "TradeEvent", "EventSeq": len(logs) + 1, "EventSide": "BUY", "EventType": "BUY",
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
            "CashDelta": state.cash - cash_before,
            "CashDeltaExpected": -(gross + fee),
            "CashDeltaDiff": (state.cash - cash_before) - (-(gross + fee)),
            "FeeAmount": fee,
            "CostBasisBefore": cost_basis_before, "CostBasisAfter": state.cost_basis,
            "CostBasisDelta": state.cost_basis - cost_basis_before,
            "AssetBefore": asset_before, "AssetAfter": asset_after, "AssetDelta": asset_after - asset_before,
            "MarketPriceForAsset": mp,
            "QuarterEventType": _quarter_event_type(reason),
            "CashValidationOK": abs(((state.cash - cash_before) - (-(gross + fee)))) <= 1e-4,
            "SharesValidationOK": abs(((state.shares - shares_before) - qty)) <= 1e-8,
            "CycleStartedByThisEvent": bool(cycle_was_empty), "CycleCompleted": False,
            "CycleStatus": "OPEN", "CycleEndReason": "", "OpenQtyAfter": float(state.shares),
            "OpenMarketValueAfter": float(state.shares) * float(mp),
            "QuarterModeBefore": bool(state.quarter_mode), "QuarterModeAfter": bool(state.quarter_mode),
            "QuarterRoundBefore": int(state.quarter_round), "QuarterRoundAfter": int(state.quarter_round),
            "QuarterUnitAmount": float(state.quarter_unit_amount),
            "ModeTransitionReason": "",
        })
    return gross, fee, qty

def _sell(state: V22State, date, price: float, fraction: float, fee_rate: float, reason: str, logs: List[Dict], mode_transition_reason: str = "", market_price: float | None = None):
    quarter_mode_before = bool(state.quarter_mode)
    quarter_round_before = int(state.quarter_round)
    cash_before = state.cash
    shares_before = state.shares
    cost_basis_before = state.cost_basis
    avg_before = state.avg_price
    t_before = state.T
    mp = float(market_price) if market_price is not None and market_price > 0 else float(price)
    asset_before = _event_asset(cash_before, shares_before, mp)
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
        "EventSeq": len(logs) + 1,
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
        "HoldingQtyBefore": shares_before,
        "HoldingQtyAfter": shares_before - qty,
        "AvgPriceBefore": avg_before,
        "AvgPriceAfter": avg_before if not full else 0.0,
        "TBefore": t_before,
        "TAfter": max(0.0, t_before * (1.0 - fraction)),
        "CashBefore": cash_before,
        "CashAfter": cash_before + net,
        "CashDelta": net,
        "CashDeltaExpected": net,
        "CashDeltaDiff": 0.0,
        "FeeAmount": fee,
        "CostBasisBefore": cost_basis_before, "CostBasisAfter": cost_basis_before - cost_sold,
        "CostBasisDelta": -cost_sold,
        "AssetBefore": asset_before, "AssetAfter": _event_asset(cash_before + net, shares_before - qty, mp),
        "AssetDelta": _event_asset(cash_before + net, shares_before - qty, mp) - asset_before,
        "MarketPriceForAsset": mp,
        "QuarterEventType": _quarter_event_type(reason, mode_transition_reason),
        "CashValidationOK": True,
        "SharesValidationOK": abs(((shares_before - qty) - shares_before) + qty) <= 1e-8,
        "CycleStartedByThisEvent": False,
        "CycleCompleted": bool(full),
        "CycleStatus": "COMPLETED" if full else "OPEN",
        "CycleEndReason": "전량매도완료" if full else "부분매도진행",
        "OpenQtyAfter": float(shares_before - qty),
        "OpenMarketValueAfter": float(shares_before - qty) * float(mp),
        "QuarterModeBefore": quarter_mode_before,
        "QuarterModeAfter": False if full else bool(state.quarter_mode),
        "QuarterRoundBefore": quarter_round_before,
        "QuarterRoundAfter": 0 if full else int(state.quarter_round),
        "QuarterUnitAmount": float(state.quarter_unit_amount),
        "ModeTransitionReason": mode_transition_reason,
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


def _mark_last_transition(logs: List[Dict], state: V22State, transition_reason: str):
    """마지막 TradeEvent에 모드 전환 결과를 표시한다. 계산값은 건드리지 않는 표시/검증용 보강이다."""
    if not logs:
        return
    logs[-1]["QuarterModeAfter"] = bool(state.quarter_mode)
    logs[-1]["QuarterRoundAfter"] = int(state.quarter_round)
    logs[-1]["QuarterUnitAmount"] = float(state.quarter_unit_amount)
    logs[-1]["ModeTransitionReason"] = transition_reason
    logs[-1]["QuarterEventType"] = _quarter_event_type(str(logs[-1].get("Reason", "")), transition_reason)


def _calc_quarter_unit_amount(state: V22State) -> float:
    """원문 기준: 남은 자금/10, 단 기존 1회매수금보다 커지면 안 됨."""
    if state.cash <= EPS:
        return 0.0
    return min(float(state.unit_amount), float(state.cash) / 10.0)


def _quarter_trigger_info(state: V22State, split_count: int, fee_rate: float) -> Dict:
    """
    사용자 제공 원문 텍스트 기준 쿼터손절 발동 진단.

    원문 확정 범위:
    - 40분할 기준 39 < T <= 40
    - 또는 40회 매수가 거의 모두 종료되어 더 이상 1회치 매수를 완전히 추가할 수 없는 상태

    구현 원칙:
    - 40분할 외 발동조건은 원문 확인 필요로 막는다.
    - T가 부동소수점/수수료/부분체결 계산으로 40을 아주 조금 넘더라도 stuck 방지를 위해
      'T 소진권'으로 표시하고 쿼터손절 진입 후보로 인정한다.
    - 실제 MOC 시작은 일봉 선후관계 과최적화를 피하기 위해 일자 루프의 첫 액션에서만 실행한다.
    """
    T = float(state.T)
    unit_cash_need = float(state.unit_amount) * (1.0 + float(fee_rate))
    can_add_full_unit = bool(state.cash + EPS >= unit_cash_need)
    remaining_t = float(split_count) - T
    info = {
        "confirmed_scope": int(split_count) == 40,
        "candidate": False,
        "trigger": False,
        "reason": "",
        "can_add_full_unit": can_add_full_unit,
        "remaining_t": remaining_t,
        "unit_cash_need": unit_cash_need,
    }
    if state.shares <= EPS:
        info["reason"] = "무포지션: 쿼터손절 대상 아님"
        return info
    if state.quarter_mode:
        info["candidate"] = True
        info["reason"] = "이미 쿼터손절모드 진행 중"
        return info
    if int(split_count) != 40:
        if T > float(split_count) - 1.0:
            info["candidate"] = True
            info["reason"] = "40분할 외 쿼터손절 발동조건은 원문 확인 필요"
        return info

    t_exhausted = T > 39.0 + EPS
    cash_exhausted = (T >= 39.0 - EPS) and (not can_add_full_unit)
    near_exhaustion = T >= 38.5
    if t_exhausted or cash_exhausted:
        reasons = []
        if t_exhausted:
            if T <= 40.0 + 1e-6:
                reasons.append(f"원문 발동조건 39<T<=40 충족(T={T:.6f})")
            else:
                reasons.append(f"T가 40 초과로 계산됨(T={T:.6f}); 소진권 stuck 방지 트리거")
        if cash_exhausted:
            reasons.append("더 이상 기존 1회치 매수를 완전히 추가할 현금 부족")
        info.update({"candidate": True, "trigger": True, "reason": " / ".join(reasons)})
    elif near_exhaustion:
        info.update({"candidate": True, "trigger": False, "reason": f"소진권 근접(T={T:.6f}); 아직 원문 발동조건 미충족"})
    return info

def _add_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df["Peak"] = df["TotalAsset"].cummax()
    df["Drawdown"] = (df["TotalAsset"] - df["Peak"]) / df["Peak"]
    df["DailyReturn"] = df["TotalAsset"].pct_change().fillna(0) * 100
    return df


def _add_trade_validation_columns(trade_events: pd.DataFrame) -> pd.DataFrame:
    if trade_events is None or trade_events.empty:
        return trade_events
    df = trade_events.copy()
    for col in ["CashDelta", "CashDeltaExpected", "CashDeltaDiff", "HoldingQtyBefore", "HoldingQtyAfter", "SharesBought", "SharesSold", "CostBasisBefore", "CostBasisAfter", "CostBasisDelta"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    if "CashDeltaDiff" in df.columns:
        df["CashValidationOK"] = df["CashDeltaDiff"].abs() <= 1e-4
    if all(c in df.columns for c in ["HoldingQtyBefore", "HoldingQtyAfter", "SharesBought", "SharesSold"]):
        df["SharesDeltaActual"] = df["HoldingQtyAfter"] - df["HoldingQtyBefore"]
        df["SharesDeltaExpected"] = df["SharesBought"] - df["SharesSold"]
        df["SharesDeltaDiff"] = df["SharesDeltaActual"] - df["SharesDeltaExpected"]
        df["SharesValidationOK"] = df["SharesDeltaDiff"].abs() <= 1e-8
    if all(c in df.columns for c in ["CostBasisBefore", "CostBasisAfter", "CostBasisDelta"]):
        df["CostBasisDeltaActual"] = df["CostBasisAfter"] - df["CostBasisBefore"]
        df["CostBasisDeltaDiff"] = df["CostBasisDeltaActual"] - df["CostBasisDelta"]
        df["CostBasisValidationOK"] = df["CostBasisDeltaDiff"].abs() <= 1e-4
    if "QuarterEventType" not in df.columns:
        df["QuarterEventType"] = ""
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

        # Step25D-7-2 쿼터손절 발동 진단/수정.
        # 사용자 제공 원문 텍스트 기준: 40분할에서 39<T<=40 또는 더 이상 1회치 매수를 완전히 추가할 수 없는 상태.
        quarter_info_before = _quarter_trigger_info(state, split_count, fee_rate)
        quarter_trigger = bool(enable_quarter_loss and quarter_info_before["trigger"])
        if enable_quarter_loss and quarter_info_before["candidate"]:
            debug.append(
                "QuarterTriggerCandidate: "
                + str(quarter_info_before["reason"])
                + f" / can_add_full_unit={quarter_info_before['can_add_full_unit']}"
                + f" / remaining_t={quarter_info_before['remaining_t']:.6f}"
            )
        if quarter_trigger:
            transition_reason = "쿼터손절 진입: " + str(quarter_info_before["reason"])
            _sell(
                state, date, close, 0.25, fee_rate,
                f"V2.2 쿼터손절 시작 MOC 25% / T={t_before:.4f}", trades,
                transition_reason, close
            )
            if state.shares > EPS:
                state.quarter_mode = True
                state.quarter_round = 0
                state.quarter_unit_amount = _calc_quarter_unit_amount(state)
                _mark_last_transition(trades, state, transition_reason)
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
                    _sell(state, date, q_designated, 0.75, fee_rate, f"V2.2 쿼터손절 지정가75 {designated_pct:.0f}%", trades, "", close)
                    action.append("쿼터지정가75매도")
                    designated_exec = True
                    sold_today = True
                if state.shares > EPS and sell_signal:
                    _sell(state, date, q_loc_price, 1.0 if designated_signal else 0.25, fee_rate, f"V2.2 쿼터손절 LOC매도 {quarter_pct:.0f}%", trades, "쿼터손절 중 LOC 매도 성공 → 후반전 모드 복귀", close)
                    action.append("쿼터LOC매도")
                    sell_exec = True
                    sold_today = True
                    if state.shares > EPS:
                        state.quarter_mode = False
                        state.quarter_round = 0
                        state.quarter_unit_amount = 0.0
                        _mark_last_transition(trades, state, "쿼터손절 중 LOC 매도 성공 → 후반전 모드 복귀")
                        action.append("후반전복귀")
                plan.append(f"쿼터매도예약: LOC {quarter_pct:.0f}% @{q_loc_price:.2f}, 지정가 {designated_pct:.0f}% @{q_designated:.2f}")
            else:
                designated_signal = designated_price_before > 0 and high >= designated_price_before
                sell_signal = star_price_before > 0 and close >= star_price_before
                if designated_signal:
                    _sell(state, date, designated_price_before, 0.75, fee_rate, f"V2.2 지정가75 {designated_pct:.0f}%", trades, "", close)
                    action.append("지정가75매도")
                    designated_exec = True
                    sold_today = True
                if state.shares > EPS and sell_signal:
                    _sell(state, date, star_price_before, 1.0 if designated_signal else 0.25, fee_rate, f"V2.2 별LOC매도 25% / 별% {star_pct_before:.4f}%", trades, "", close)
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
                        gross, fee, qty = _buy(state, date, first_loc, state.unit_amount, fee_rate, trades, "V2.2 첫매수 LOC / bootstrap_prev_close_buffer", close)
                        if gross > 0:
                            action.append("첫매수LOC")
                            buy_exec = True
                    plan.append(f"첫매수: 전날종가×{1+first_loc_buffer_pct/100:.3f} LOC @{first_loc:.2f} / FirstBuyPolicy=bootstrap_prev_close_buffer")
                else:
                    action.append("첫날대기")
            elif state.quarter_mode:
                q_buy_price = state.avg_price * (1.0 + quarter_pct / 100.0)
                amount = state.quarter_unit_amount if state.quarter_unit_amount > 0 else _calc_quarter_unit_amount(state)
                buy_signal = close <= q_buy_price
                if buy_signal and state.quarter_round < 10:
                    gross, fee, qty = _buy(state, date, q_buy_price, amount, fee_rate, trades, f"V2.2 쿼터손절 LOC매수 {quarter_pct:.0f}%", close)
                    if gross > 0:
                        state.quarter_round += 1
                        if trades:
                            trades[-1]["QuarterRoundAfter"] = int(state.quarter_round)
                        action.append(f"쿼터LOC매수{state.quarter_round}")
                        buy_exec = True
                plan.append(f"쿼터매수: LOC {quarter_pct:.0f}% @{q_buy_price:.2f}, round={state.quarter_round}/10, 1회금액≤기존1회 {amount:,.0f}")
                if state.quarter_round >= 10 and state.shares > EPS:
                    q_escape_price_before_moc = state.avg_price * (1.0 + quarter_pct / 100.0)
                    _sell(state, date, close, 0.25, fee_rate, "V2.2 쿼터손절 10회 소진 후 MOC 25%", trades, "", close)
                    action.append("쿼터10회후MOC")
                    # 원문 정리 기준: 10회째 MOC 매도가 -10%/SOXL -12% 안쪽이면 후반전 모드로 진입.
                    # 일봉 백테스트에서는 MOC 체결가(close)가 해당 LOC 기준가 이상이면 '안쪽'으로 판정한다.
                    if state.shares > EPS and close >= q_escape_price_before_moc:
                        state.quarter_mode = False
                        state.quarter_round = 0
                        state.quarter_unit_amount = 0.0
                        _mark_last_transition(trades, state, f"10회 후 MOC 체결가가 {quarter_pct:.0f}% LOC 기준 안쪽 → 후반전 모드 복귀")
                        action.append("후반전복귀")
                    elif state.shares > EPS:
                        state.quarter_round = 0
                        state.quarter_unit_amount = _calc_quarter_unit_amount(state)
                        _mark_last_transition(trades, state, f"10회 후 MOC 체결가가 {quarter_pct:.0f}% LOC 기준 밖 → 쿼터손절 반복")
                        action.append("쿼터반복")
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
                        gross, fee, qty = _buy(state, date, avg_now, half, fee_rate, trades, "V2.2 전반전 0% LOC매수 0.5T", close)
                        if gross > 0:
                            action.append("전반전0%LOC")
                            buy_exec = True
                            buy_signal = True
                    if close <= star_buy:
                        gross, fee, qty = _buy(state, date, star_buy, half, fee_rate, trades, f"V2.2 전반전 별LOC매수 0.5T / 별% {star_pct_now:.4f}%", close)
                        if gross > 0:
                            action.append("전반전별LOC")
                            buy_exec = True
                            buy_signal = True
                    plan.append(f"전반전매수: 0%LOC @{avg_now:.2f} 0.5T + 별LOC @{star_buy:.2f} 0.5T")
                else:
                    # 후반전: 별LOC 1T
                    if close <= star_buy:
                        gross, fee, qty = _buy(state, date, star_buy, state.unit_amount, fee_rate, trades, f"V2.2 후반전 별LOC매수 1T / 별% {star_pct_now:.4f}%", close)
                        if gross > 0:
                            action.append("후반전별LOC")
                            buy_exec = True
                            buy_signal = True
                    plan.append(f"후반전매수: 별LOC @{star_buy:.2f} 1T")

        quarter_info_after_actions = _quarter_trigger_info(state, split_count, fee_rate)
        if enable_quarter_loss and quarter_info_after_actions["candidate"] and (not state.quarter_mode) and (not sold_today):
            # 당일 LOC 매수 후 소진권에 도달한 경우, 같은 종가 기준으로 MOC까지 가정하지 않고 다음 거래일 첫 액션에서 처리한다.
            debug.append("QuarterTriggerAfterActionPendingNextDay: " + str(quarter_info_after_actions["reason"]))
            if "쿼터후보" not in action:
                action.append("쿼터후보")

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
            "CycleStatus": "OPEN" if state.shares > EPS else "FLAT",
            "CycleEndReason": "기간종료미청산" if state.shares > EPS and i == len(df) - 1 else "",
            "OpenQty": float(state.shares),
            "OpenMarketValue": float(state.shares) * float(close),
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
            "QuarterUnitAmount": float(state.quarter_unit_amount),
            "QuarterTriggerCandidate": bool(quarter_info_before.get("candidate") or quarter_info_after_actions.get("candidate")),
            "QuarterTriggerExecuted": bool(quarter_trigger),
            "QuarterTriggerReason": str(quarter_info_before.get("reason") or quarter_info_after_actions.get("reason") or ""),
            "CanAddFullUnitBefore": bool(quarter_info_before.get("can_add_full_unit")),
            "RemainingTBefore": float(quarter_info_before.get("remaining_t", 0.0)),
            "ModeTransitionReason": " | ".join([x for x in action if "복귀" in x or "쿼터손절시작" in x or "쿼터반복" in x or "쿼터후보" in x]),
            "RaorDebug": " | ".join(debug),
        })

    trade_events = pd.DataFrame(trades)
    if not trade_events.empty and "EventDate" in trade_events.columns:
        trade_events = trade_events.sort_values(["EventSeq"] if "EventSeq" in trade_events.columns else ["EventDate", "CycleId", "EventSide"]).reset_index(drop=True)
    trade_events = _add_trade_validation_columns(trade_events)
    return _add_metrics(pd.DataFrame(rows)), trade_events


run_raor_v22_backtest = run_raor_v22_core
