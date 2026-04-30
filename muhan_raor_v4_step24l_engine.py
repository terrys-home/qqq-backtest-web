"""
Step24L - 라오어 무한매수법 4.0 원문기반 매도예약 보강 엔진

기준
- Step24A 엔진을 수정하지 않고 별도 파일로 확장합니다.
- 기존 V4/V5 근사 엔진은 건드리지 않습니다.
- 자동주문/RPA가 아니라 백테스트/판단엔진입니다.

일봉 백테스트 체결 근사
- LOC 매수: 당일 종가 <= LOC 매수가이면 당일 종가 체결
- LOC 매도: 당일 종가 >= LOC 매도가이면 당일 종가 체결
- 지정가 매도: 당일 고가 >= 지정가이면 지정가 체결

Step24A 유지
1) 시작 전 보유수량 0이면 T=0
2) 첫매수: 1회매수금으로 전날종가보다 적당히 큰 값 LOC 매수 시도
   - 기본 +12%, 원문 일반 가이드 +10~15%
3) 일일매수시도액 = 잔금 / (분할수 - T)
4) 별% 공식
   - TQQQ 20분할: 15 - 1.5T
   - TQQQ 40분할: 15 - 0.75T
   - SOXL 20분할: 20 - 2T
   - SOXL 40분할: 20 - T
5) 별%가격 = 평단 * (1 + 별%/100)
6) 매수점 = 별%가격 - 0.01, 매도점 = 별%가격
7) 전반전: 별지점/큰수 LOC 0.5T + 평단 LOC 0.5T
8) 매도예약: 매일 보유수량 1/4은 별지점 LOC 매도, 나머지 3/4은 TQQQ +15% / SOXL +20% 지정가 매도
9) 지정가매도 기준가: TQQQ +15%, SOXL +20%

Step24L 추가
- 후반전/소진모드 분기를 명시적으로 분리
- 소진모드 시작 조건: 남은 T < 1 또는 일일매수시도액 계산이 불가능할 정도로 잔여 분할이 작을 때
- 후반전 매수: 원문에 명시된 별지점 LOC 기준을 유지하되, 임의 다중 사다리는 만들지 않고 1일 1T 한도로 제한
- 소진모드 매수: 잔금 범위 내에서 별지점 LOC만 시도, T는 실제 사용금액/1회매수시도액만큼 추적
- 매도는 전반전/후반전 구분 없이 공통 적용
- 매일 보유수량 1/4은 별지점 LOC 매도, 나머지 3/4은 지정가 매도 예약으로 계산
- 지정가 매도 기준: TQQQ +15%, SOXL +20%
- 별LOC 매수가는 별지점-0.01, 별LOC 매도가는 별지점으로 고정하여 가격 겹침을 방지
- DailyCandleOrderAmbiguous는 가격 겹침이 아니라 일봉 OHLC상 장중 선후관계를 확정할 수 없는 경우만 표시
- T 추적 로그 강화: TBefore/TAfter/TDelta/PhaseBefore/PhaseAfter/RemainingT/UsedAttemptRatio/OrderPlan
- 부분매도 로그의 매수일 고정 표시 방지: BuyDate는 마지막 체결 매수일, CycleStartDate는 무한매수 주기 시작일로 분리
- 기간 내 완료된 무한매수 주기 집계용 CycleId/CycleCompleted 컬럼 추가

주의
- 원문 이미지에 없는 30분할 별% 공식, TQQQ/SOXL 외 티커 공식은 넣지 않았습니다.
- 후반전의 세부 수량표가 별도로 존재하는 경우, 현재 코드는 임의 추정하지 않고 1일 1T 한도 LOC로 막아두었습니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import pandas as pd


SUPPORTED_TICKERS = {"TQQQ", "SOXL"}
SUPPORTED_SPLITS = {20, 40}
EPS = 1e-10


@dataclass
class PositionState:
    cash: float
    shares: float = 0.0
    cost_basis: float = 0.0
    T: float = 0.0
    entry_date: pd.Timestamp | None = None
    cycle_id: int = 0
    cycle_start_date: pd.Timestamp | None = None
    last_buy_date: pd.Timestamp | None = None

    @property
    def avg_price(self) -> float:
        return self.cost_basis / self.shares if self.shares > EPS else 0.0


def _num(x, default=0.0) -> float:
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def _get_col(row, candidates, default=0.0) -> float:
    for c in candidates:
        if c in row.index:
            return _num(row[c], default)
    return default


def normalize_ticker(ticker: str) -> str:
    ticker = str(ticker or "").upper().strip()
    if ticker not in SUPPORTED_TICKERS:
        raise ValueError(f"Step24L 원문엔진은 현재 TQQQ/SOXL만 지원합니다. 입력 티커={ticker}")
    return ticker


def normalize_split(split_count: int) -> int:
    split_count = int(split_count)
    if split_count not in SUPPORTED_SPLITS:
        raise ValueError(
            "Step24L 원문엔진은 현재 별% 공식이 명시된 20/40분할만 지원합니다. "
            f"입력 분할={split_count}"
        )
    return split_count


def calc_star_pct(ticker: str, split_count: int, T: float) -> float:
    ticker = normalize_ticker(ticker)
    split_count = normalize_split(split_count)
    T = float(T)
    if ticker == "TQQQ" and split_count == 20:
        return 15.0 - 1.5 * T
    if ticker == "TQQQ" and split_count == 40:
        return 15.0 - 0.75 * T
    if ticker == "SOXL" and split_count == 20:
        return 20.0 - 2.0 * T
    if ticker == "SOXL" and split_count == 40:
        return 20.0 - 1.0 * T
    raise ValueError(f"지원하지 않는 조합: {ticker} / {split_count}")


def calc_star_price(avg_price: float, star_pct: float) -> float:
    return avg_price * (1.0 + star_pct / 100.0) if avg_price > 0 else 0.0


def calc_designated_sell_pct(ticker: str) -> float:
    ticker = normalize_ticker(ticker)
    return 15.0 if ticker == "TQQQ" else 20.0


def current_phase(T: float, split_count: int, cash: float | None = None) -> str:
    T = float(T)
    split_count = int(split_count)
    remaining_t = split_count - T
    if T <= EPS:
        return "무포지션"
    if remaining_t < 1.0:
        return "소진모드"
    if T < split_count / 2:
        return "전반전"
    return "후반전"


def safe_daily_attempt(cash: float, split_count: int, T: float) -> float:
    remaining_t = float(split_count) - float(T)
    if remaining_t <= EPS:
        return 0.0
    return max(0.0, float(cash) / remaining_t)


def add_metrics(result_df: pd.DataFrame) -> pd.DataFrame:
    if result_df.empty:
        return result_df
    result_df["Peak"] = result_df["TotalAsset"].cummax()
    result_df["Drawdown"] = (result_df["TotalAsset"] - result_df["Peak"]) / result_df["Peak"]
    result_df["DailyReturn"] = result_df["TotalAsset"].pct_change().fillna(0) * 100
    return result_df


def execute_buy(
    state: PositionState,
    date: pd.Timestamp,
    close_price: float,
    target_amount: float,
    fee_rate: float,
) -> Tuple[float, float, float]:
    if target_amount <= 0 or close_price <= 0 or state.cash <= 0:
        return 0.0, 0.0, 0.0
    gross_buy = min(float(target_amount), state.cash / (1.0 + fee_rate))
    if gross_buy <= 0:
        return 0.0, 0.0, 0.0
    fee = gross_buy * fee_rate
    shares_bought = gross_buy / close_price
    state.cash -= gross_buy + fee
    state.shares += shares_bought
    state.cost_basis += gross_buy
    if state.entry_date is None:
        state.entry_date = date
        state.cycle_id += 1
        state.cycle_start_date = date
    state.last_buy_date = date
    return gross_buy, fee, shares_bought


def execute_sell(
    state: PositionState,
    date: pd.Timestamp,
    sell_price: float,
    sell_fraction: float,
    fee_rate: float,
    reason: str,
    trade_logs: List[Dict],
) -> Tuple[float, float, float]:
    if state.shares <= EPS or sell_price <= 0 or sell_fraction <= 0:
        return 0.0, 0.0, 0.0
    sell_fraction = max(0.0, min(1.0, float(sell_fraction)))
    shares_sold = state.shares * sell_fraction
    gross_sell = shares_sold * sell_price
    fee = gross_sell * fee_rate
    net_sell = gross_sell - fee
    cost_sold = state.cost_basis * sell_fraction
    profit = net_sell - cost_sold
    return_pct = (profit / cost_sold) * 100.0 if cost_sold > 0 else 0.0
    representative_buy_date = state.last_buy_date or state.entry_date
    hold_days = (date - representative_buy_date).days if representative_buy_date is not None else 0
    cycle_hold_days = (date - state.cycle_start_date).days if state.cycle_start_date is not None else hold_days
    full_cycle_sell = sell_fraction >= 0.999999 or (state.shares - shares_sold) <= EPS

    trade_logs.append({
        "CycleId": state.cycle_id,
        "CycleStartDate": state.cycle_start_date,
        "BuyDate": representative_buy_date,
        "SellDate": date,
        "CycleEndDate": date if full_cycle_sell else pd.NaT,
        "HoldDays": hold_days,
        "CycleHoldDays": cycle_hold_days,
        "BuyAmount": cost_sold,
        "SellAmount": net_sell,
        "Profit": profit,
        "ReturnPct": return_pct,
        "Reason": reason,
        "SellPrice": sell_price,
        "SharesSold": shares_sold,
        "SellFraction": sell_fraction,
        "OrderType": "SELL",
        "OrderPrice": sell_price,
        "OrderQty": shares_sold,
        "CashBefore": state.cash,
        "CashAfter": state.cash + net_sell,
        "HoldingQtyBefore": state.shares,
        "HoldingQtyAfter": state.shares - shares_sold,
        "AvgPriceBefore": state.avg_price,
        "AvgPriceAfter": state.avg_price,
        "QuarterSellQty": shares_sold if sell_fraction < 0.999999 else 0.0,
        "CycleCompleted": bool(full_cycle_sell),
    })

    state.cash += net_sell
    state.shares -= shares_sold
    state.cost_basis -= cost_sold

    if state.shares <= EPS or state.cost_basis <= 1e-6:
        state.shares = 0.0
        state.cost_basis = 0.0
        state.T = 0.0
        state.entry_date = None
        state.cycle_start_date = None
        state.last_buy_date = None
    return net_sell, profit, shares_sold


def _apply_t_increase_by_amount(old_T: float, gross_buy: float, unit_amount: float, planned_t: float, split_count: int) -> float:
    if gross_buy <= 0 or unit_amount <= 0 or planned_t <= 0:
        return old_T
    ratio = max(0.0, min(1.0, gross_buy / unit_amount))
    return min(float(split_count), float(old_T) + planned_t * ratio)


def _record_buy_order(order_notes: List[str], name: str, loc_price: float, planned_t: float, planned_amount: float, filled: bool, gross_buy: float):
    status = "체결" if filled else "미체결"
    order_notes.append(
        f"{name}: LOC={loc_price:.2f}, 계획={planned_t:.4f}T/{planned_amount:,.0f}, {status}, 매수금={gross_buy:,.0f}"
    )


def run_raor_infinite4_step24l_core(
    daily_df: pd.DataFrame,
    ticker: str = "TQQQ",
    split_count: int = 40,
    initial_cash: float = 100_000_000,
    fee_rate_pct: float = 0.1,
    first_loc_buffer_pct: float = 12.0,
    designated_sell_pct_override: float | None = None,
    enable_designated_sell: bool = True,
    enable_quarter_sell: bool = True,
    allow_same_day_sell_after_buy: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    ticker = normalize_ticker(ticker)
    split_count = normalize_split(split_count)

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
    state = PositionState(cash=float(initial_cash))
    results: List[Dict] = []
    trade_logs: List[Dict] = []
    # 원문 기본값: TQQQ +15%, SOXL +20%.
    # Step24L에서는 백테스트 비교를 위해 UI에서 지정가 전량매도 수익률을 선택할 수 있게 하되,
    # 기본값은 원문값을 유지한다.
    designated_sell_pct = (
        calc_designated_sell_pct(ticker)
        if designated_sell_pct_override is None
        else float(designated_sell_pct_override)
    )
    if designated_sell_pct <= 0:
        designated_sell_pct = calc_designated_sell_pct(ticker)

    for i, row in df.iterrows():
        date = row["Date"]
        close_price = float(row["Close"])
        high_price = float(row.get("High", close_price))
        prev_close = float(df.loc[i - 1, "Close"]) if i > 0 else close_price

        action_parts: List[str] = []
        debug_parts: List[str] = []
        order_notes: List[str] = []

        t_before_day = float(state.T)
        avg_before = state.avg_price
        phase_before = current_phase(state.T, split_count, state.cash)
        remaining_t_before = max(float(split_count) - state.T, 0.0)
        daily_attempt_before = safe_daily_attempt(state.cash, split_count, state.T)
        star_pct_before = calc_star_pct(ticker, split_count, state.T) if state.T > 0 else 0.0
        star_price_before = calc_star_price(avg_before, star_pct_before) if state.T > 0 else 0.0
        star_buy_before = max(0.0, star_price_before - 0.01) if star_price_before > 0 else 0.0
        designated_sell_price_before = avg_before * (1.0 + designated_sell_pct / 100.0) if avg_before > 0 else 0.0
        sold_today = False
        designated_hit = False
        star_loc_hit = False
        buy_loc_signal = False
        buy_loc_executed = False
        sell_loc_executed = False
        designated_sell_executed = False
        daily_candle_order_ambiguous = False
        buy_sell_price_overlap = False

        # 1) 매도: 원문 매도예약 구조 반영
        # - 전반전/후반전 상관없이 공통 적용
        # - 매일 보유수량의 1/4은 별지점 LOC 매도
        # - 나머지 보유수량 3/4은 TQQQ +15%, SOXL +20% 지정가 매도
        # - 백테스트 체결 근사:
        #   지정가 매도 = 당일 High >= 지정가이면 지정가 체결
        #   LOC 매도 = 당일 Close >= 별지점이면 종가 체결
        # - 같은 날 둘 다 충족되면 지정가 75%를 먼저 반영하고,
        #   남은 25%를 별LOC로 매도하여 과매도 없이 주기 완료 처리
        if state.shares > EPS:
            old_T_start_sell = float(state.T)
            designated_hit = (
                enable_designated_sell
                and designated_sell_price_before > 0
                and high_price >= designated_sell_price_before
            )
            star_loc_hit = (
                enable_quarter_sell
                and star_price_before > 0
                and close_price >= star_price_before
            )

            # Step24L 핵심 검증:
            # 별LOC 매수가는 별지점 - 0.01, 별LOC 매도가는 별지점 그대로다.
            # 따라서 같은 별지점 기준에서 매수/매도 LOC 가격이 겹치면 안 된다.
            buy_sell_price_overlap = bool(star_buy_before > 0 and star_price_before > 0 and star_buy_before >= star_price_before)
            if buy_sell_price_overlap:
                debug_parts.append(f"경고: LOC매수가({star_buy_before:.2f}) >= LOC매도가({star_price_before:.2f}) - 별지점 가격분리 오류")

            # 원문상 별% 매도점은 TQQQ 15%, SOXL 20%에서 T가 증가할수록 내려간다.
            # 따라서 별LOC 매도점이 지정가 매도점보다 높게 계산되면 공식/T 추적 오류 가능성이 크다.
            if star_price_before > 0 and designated_sell_price_before > 0 and star_price_before > designated_sell_price_before + 1e-8:
                debug_parts.append(f"경고: 별LOC매도가({star_price_before:.2f}) > 지정가({designated_sell_price_before:.2f}) - 별%/T 계산 재확인 필요")

            if designated_hit:
                old_T = state.T
                execute_sell(
                    state=state,
                    date=date,
                    sell_price=designated_sell_price_before,
                    sell_fraction=0.75,
                    fee_rate=fee_rate,
                    reason=f"Step24L 지정가매도(커스텀): 보유수량 75% {ticker} +{designated_sell_pct:.0f}% / 지정가 {designated_sell_price_before:.2f} / phase={phase_before}",
                    trade_logs=trade_logs,
                )
                if state.shares > EPS:
                    state.T = old_T * 0.25
                action_parts.append("지정가75매도")
                debug_parts.append(f"지정가75매도: T {old_T:.4f}→{state.T:.4f}, 지정가={designated_sell_price_before:.2f}")
                sold_today = True
                designated_sell_executed = True

            if state.shares > EPS and star_loc_hit:
                old_T = state.T
                # 지정가 75%가 이미 체결된 날에는 남은 25% 전량이 원래 보유수량의 쿼터에 해당
                # 지정가가 체결되지 않은 날에는 현재 보유수량의 25%만 LOC 매도
                sell_fraction = 1.0 if designated_hit else 0.25
                sell_label = "별LOC잔여전량" if designated_hit else "쿼터매도LOC"
                execute_sell(
                    state=state,
                    date=date,
                    sell_price=close_price,
                    sell_fraction=sell_fraction,
                    fee_rate=fee_rate,
                    reason=f"Step24L {sell_label}: 별% LOC 매도점 {star_price_before:.2f} / phase={phase_before}",
                    trade_logs=trade_logs,
                )
                if state.shares > EPS:
                    state.T = old_T * (1.0 - sell_fraction)
                action_parts.append(sell_label)
                debug_parts.append(f"{sell_label}: T {old_T:.4f}→{state.T:.4f}, 별매도점={star_price_before:.2f}")
                sold_today = True
                sell_loc_executed = True

            if designated_hit or star_loc_hit:
                order_notes.append(
                    f"매도예약: 별LOC 25% @ {star_price_before:.2f}, 지정가 75% @ {designated_sell_price_before:.2f}, "
                    f"지정가체결={'Y' if designated_hit else 'N'}, LOC체결={'Y' if star_loc_hit else 'N'}"
                )

        # 2) 매수: 같은 날 매도 후 매수는 기본 차단. 원문 일일 주문표 체결순서 과최적화 방지.
        may_buy_today = (not sold_today) or allow_same_day_sell_after_buy
        if may_buy_today:
            if state.T <= EPS or state.shares <= EPS:
                if i > 0:
                    daily_attempt = safe_daily_attempt(state.cash, split_count, 0.0)
                    first_loc_price = prev_close * (1.0 + float(first_loc_buffer_pct) / 100.0)
                    buy_loc_signal = close_price <= first_loc_price
                    if buy_loc_signal:
                        gross_buy, fee, _ = execute_buy(state, date, close_price, daily_attempt, fee_rate)
                        if gross_buy > 0:
                            old_T = state.T
                            state.T = _apply_t_increase_by_amount(old_T, gross_buy, daily_attempt, 1.0, split_count)
                            action_parts.append("첫매수LOC")
                            buy_loc_executed = True
                            _record_buy_order(order_notes, "첫매수", first_loc_price, 1.0, daily_attempt, True, gross_buy)
                            debug_parts.append(f"첫매수: 전날종가 {prev_close:.2f}×{1+first_loc_buffer_pct/100:.3f}, T {old_T:.4f}→{state.T:.4f}")
                    else:
                        action_parts.append("첫매수대기")
                        _record_buy_order(order_notes, "첫매수", first_loc_price, 1.0, daily_attempt, False, 0.0)
                else:
                    action_parts.append("첫날대기")
            else:
                phase_now = current_phase(state.T, split_count, state.cash)
                daily_attempt = safe_daily_attempt(state.cash, split_count, state.T)
                avg_now = state.avg_price
                star_pct_now = calc_star_pct(ticker, split_count, state.T)
                star_price_now = calc_star_price(avg_now, star_pct_now)
                star_buy_now = max(0.0, star_price_now - 0.01) if star_price_now > 0 else 0.0

                if phase_now == "전반전":
                    # Step24A 원문 반영 유지: 별지점/큰수 0.5T + 평단 0.5T
                    if star_buy_now > 0:
                        planned_amount = daily_attempt * 0.5
                        filled = close_price <= star_buy_now
                        buy_loc_signal = buy_loc_signal or filled
                        gross_buy = 0.0
                        if filled:
                            old_T = state.T
                            gross_buy, fee, _ = execute_buy(state, date, close_price, planned_amount, fee_rate)
                            state.T = _apply_t_increase_by_amount(old_T, gross_buy, planned_amount, 0.5, split_count)
                            if gross_buy > 0:
                                action_parts.append("전반전별LOC")
                                buy_loc_executed = True
                                debug_parts.append(f"전반전 별LOC: T {old_T:.4f}→{state.T:.4f}")
                        _record_buy_order(order_notes, "전반전 별/큰수", star_buy_now, 0.5, planned_amount, filled and gross_buy > 0, gross_buy)

                    if avg_now > 0:
                        planned_amount = daily_attempt * 0.5
                        filled = close_price <= avg_now
                        buy_loc_signal = buy_loc_signal or filled
                        gross_buy = 0.0
                        if filled:
                            old_T = state.T
                            gross_buy, fee, _ = execute_buy(state, date, close_price, planned_amount, fee_rate)
                            state.T = _apply_t_increase_by_amount(old_T, gross_buy, planned_amount, 0.5, split_count)
                            if gross_buy > 0:
                                action_parts.append("전반전평단LOC")
                                buy_loc_executed = True
                                debug_parts.append(f"전반전 평단LOC: T {old_T:.4f}→{state.T:.4f}")
                        _record_buy_order(order_notes, "전반전 평단", avg_now, 0.5, planned_amount, filled and gross_buy > 0, gross_buy)

                elif phase_now == "후반전":
                    # 후반전: 원문에 명시된 별지점 LOC 기준을 유지. 세부 사다리는 임의 생성하지 않음.
                    planned_t = min(1.0, max(float(split_count) - state.T, 0.0))
                    planned_amount = daily_attempt * planned_t
                    filled = star_buy_now > 0 and close_price <= star_buy_now
                    buy_loc_signal = buy_loc_signal or filled
                    gross_buy = 0.0
                    if filled:
                        old_T = state.T
                        gross_buy, fee, _ = execute_buy(state, date, close_price, planned_amount, fee_rate)
                        state.T = _apply_t_increase_by_amount(old_T, gross_buy, planned_amount, planned_t, split_count)
                        if gross_buy > 0:
                            action_parts.append("후반전별LOC")
                            buy_loc_executed = True
                            debug_parts.append(f"후반전 별LOC 1일 최대 {planned_t:.4f}T: T {old_T:.4f}→{state.T:.4f}")
                    _record_buy_order(order_notes, "후반전 별지점", star_buy_now, planned_t, planned_amount, filled and gross_buy > 0, gross_buy)

                elif phase_now == "소진모드":
                    # 소진모드: 남은 T가 1보다 작다. 남은 T와 잔금 범위 안에서만 별지점 LOC를 시도한다.
                    planned_t = max(0.0, min(1.0, float(split_count) - state.T))
                    planned_amount = state.cash / (1.0 + fee_rate) if planned_t <= EPS else daily_attempt * planned_t
                    filled = star_buy_now > 0 and close_price <= star_buy_now and planned_amount > 0
                    buy_loc_signal = buy_loc_signal or filled
                    gross_buy = 0.0
                    if filled:
                        old_T = state.T
                        gross_buy, fee, _ = execute_buy(state, date, close_price, planned_amount, fee_rate)
                        state.T = _apply_t_increase_by_amount(old_T, gross_buy, planned_amount, planned_t if planned_t > EPS else 0.0, split_count)
                        if gross_buy > 0:
                            action_parts.append("소진모드별LOC")
                            buy_loc_executed = True
                            debug_parts.append(f"소진모드 별LOC 잔여 {planned_t:.4f}T: T {old_T:.4f}→{state.T:.4f}")
                    _record_buy_order(order_notes, "소진모드 별지점", star_buy_now, planned_t, planned_amount, filled and gross_buy > 0, gross_buy)

        # 가격 겹침 오류와 일봉 선후관계 불명은 분리해서 기록한다.
        # LOC 매수/매도 가격은 별지점-0.01 / 별지점으로 분리되므로 BuySellPriceOverlap은 정상적으로 False여야 한다.
        signal_count = int(bool(designated_hit)) + int(bool(star_loc_hit)) + int(bool(buy_loc_signal))
        executed_count = int(bool(designated_sell_executed)) + int(bool(sell_loc_executed)) + int(bool(buy_loc_executed))
        daily_candle_order_ambiguous = signal_count >= 2 or executed_count >= 2
        if daily_candle_order_ambiguous:
            debug_parts.append(
                f"DailyCandleOrderAmbiguous: 지정가신호={'Y' if designated_hit else 'N'}, "
                f"별LOC매도신호={'Y' if star_loc_hit else 'N'}, 별LOC매수신호={'Y' if buy_loc_signal else 'N'}, "
                "가격 겹침이 아니라 일봉 OHLC만으로 장중 선후관계를 확정할 수 없다는 의미"
            )

        if not action_parts:
            action_parts.append("관망")

        stock_value = state.shares * close_price
        total_asset = state.cash + stock_value
        avg_after = state.avg_price
        phase_after = current_phase(state.T, split_count, state.cash)
        star_pct_after = calc_star_pct(ticker, split_count, state.T) if state.T > 0 else 0.0
        star_price_after = calc_star_price(avg_after, star_pct_after) if state.T > 0 else 0.0
        daily_attempt_after = safe_daily_attempt(state.cash, split_count, state.T)
        remaining_t_after = max(float(split_count) - state.T, 0.0)
        t_delta = float(state.T) - t_before_day
        used_attempt_ratio = (t_delta / max(1.0, min(1.0, remaining_t_before))) if t_delta > 0 else 0.0

        results.append({
            "Date": date,
            "Close": close_price,
            "High": high_price,
            "RSI": _get_col(row, ["WeeklyRSI", "RSI"], 50),
            "Mode": phase_after,
            "PhaseBefore": phase_before,
            "PhaseAfter": phase_after,
            "Action": "+".join(action_parts),
            "Cash": state.cash,
            "Shares": state.shares,
            "StockValue": stock_value,
            "TotalAsset": total_asset,
            "CurrentSplit": state.T,
            "T": state.T,
            "TBefore": t_before_day,
            "TAfter": state.T,
            "TDelta": t_delta,
            "RemainingTBefore": remaining_t_before,
            "RemainingTAfter": remaining_t_after,
            "AvgPrice": avg_after,
            "StarPct": star_pct_after,
            "StarPrice": star_price_after,
            "SellLOCPrice": star_price_after,
            "BuyStarPrice": max(0.0, star_price_after - 0.01) if star_price_after > 0 else 0.0,
            "BuyLOCPrice": max(0.0, star_price_after - 0.01) if star_price_after > 0 else 0.0,
            "DailyAttemptBefore": daily_attempt_before,
            "DailyAttempt": daily_attempt_after,
            "DesignatedSellPrice": avg_after * (1.0 + designated_sell_pct / 100.0) if avg_after > 0 else 0.0,
            "SellTargetPrice": avg_after * (1.0 + designated_sell_pct / 100.0) if avg_after > 0 else 0.0,
            "OrderType": "+".join(action_parts),
            "OrderPrice": close_price,
            "OrderQty": state.shares,
            "CashAfter": state.cash,
            "HoldingQtyAfter": state.shares,
            "AvgPriceAfter": avg_after,
            "QuarterSellQty": 0.0,
            "IsCycleCompleted": False,
            "CycleId": state.cycle_id,
            "CycleStartDate": state.cycle_start_date,
            "LastBuyDate": state.last_buy_date,
            "UsedAttemptRatio": used_attempt_ratio,
            "OrderPlan": " || ".join(order_notes),
            "DesignatedSellPct": designated_sell_pct,
            "DesignatedSellSignal": bool(designated_hit),
            "SellLOCSignal": bool(star_loc_hit),
            "BuyLOCSignal": bool(buy_loc_signal),
            "DesignatedSellExecuted": bool(designated_sell_executed),
            "SellLOCExecuted": bool(sell_loc_executed),
            "BuyLOCExecuted": bool(buy_loc_executed),
            "BuySellPriceOverlap": bool(buy_sell_price_overlap),
            "DailyCandleOrderAmbiguous": bool(daily_candle_order_ambiguous),
            "ExecutionPriorityNote": "일봉 OHLC 선후관계 불명: 매도예약 우선 기록, 같은 날 매수는 기본 차단" if daily_candle_order_ambiguous else "",
            "RaorDebug": " | ".join(debug_parts),
        })

    result_df = add_metrics(pd.DataFrame(results))
    trade_df = pd.DataFrame(trade_logs)
    if not trade_df.empty:
        maes, mfes = [], []
        for _, trade in trade_df.iterrows():
            if pd.isna(trade.get("BuyDate")) or pd.isna(trade.get("SellDate")):
                maes.append(0.0); mfes.append(0.0); continue
            period = df[(df["Date"] >= trade["BuyDate"]) & (df["Date"] <= trade["SellDate"])]
            if period.empty:
                maes.append(0.0); mfes.append(0.0); continue
            entry_price = float(period.iloc[0]["Close"])
            min_price = float(period["Close"].min())
            max_price = float(period["Close"].max())
            maes.append(((min_price / entry_price) - 1.0) * 100.0 if entry_price > 0 else 0.0)
            mfes.append(((max_price / entry_price) - 1.0) * 100.0 if entry_price > 0 else 0.0)
        trade_df["MAE"] = maes
        trade_df["MFE"] = mfes
    return result_df, trade_df


run_raor_infinite4_step24l_backtest = run_raor_infinite4_step24l_core
