"""
Step24A - 라오어 무한매수법 4.0 원문기반 새 엔진

중요 원칙
- 기존 V4/V5 근사 엔진을 수정한 것이 아니라, 라오어 방법론 문장 기준으로 새로 작성한 엔진입니다.
- 자동주문/RPA가 아니라 백테스트/판단엔진입니다.
- LOC는 일봉 백테스트에서 다음처럼 근사합니다.
  * LOC 매수: 당일 종가 <= LOC 매수가이면 당일 종가 체결로 간주
  * LOC 매도: 당일 종가 >= LOC 매도가이면 당일 종가 체결로 간주
  * 지정가 매도: 당일 고가 >= 지정가이면 지정가 체결로 간주

반영한 핵심 규칙
1) 시작 전 보유수량 0이면 T=0
2) 첫매수: 1회매수금으로 전날종가보다 적당히 큰 값(기본 +12%, 원문 일반 가이드 10~15%) LOC 매수 시도
3) 일일매수 시도액: 잔금 / (분할수 - T)
4) 별% 공식
   - TQQQ 20분할: 15 - 1.5T
   - TQQQ 40분할: 15 - 0.75T
   - SOXL 20분할: 20 - 2T
   - SOXL 40분할: 20 - T
5) 별%가격: 평단 * (1 + 별%/100)
6) 매수점: 별%가격 - 0.01, 매도점: 별%가격
7) 전반전: 1회매수액을 별지점/큰수 LOC 0.5 + 평단 LOC 0.5로 나눔
   - 하나만 체결되면 T + 0.5
   - 둘 다 체결되면 T + 1.0
   - 아래 LOC 사다리는 그 회차 1T를 채우기 위한 보조망이므로, 회차당 T 증가 한도는 1.0
8) 쿼터매도: 보유수량의 25% 매도, T = 기존 T * 0.75
9) 지정가매도: TQQQ +15%, SOXL +20% 목표가를 사용

아직 방법론 원문 추가 확인이 필요한 부분
- 후반전/소진모드의 세부 LOC 사다리 수량 배분표는 원문 추가 확인 전까지 보수적으로 1회매수액 LOC 묶음으로 처리합니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple
import math
import pandas as pd


SUPPORTED_TICKERS = {"TQQQ", "SOXL"}
SUPPORTED_SPLITS = {20, 40}


@dataclass
class PositionState:
    cash: float
    shares: float = 0.0
    cost_basis: float = 0.0  # 수수료 제외 매수원금
    T: float = 0.0
    entry_date: pd.Timestamp | None = None

    @property
    def avg_price(self) -> float:
        return self.cost_basis / self.shares if self.shares > 0 else 0.0


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


def add_metrics(result_df: pd.DataFrame) -> pd.DataFrame:
    if result_df.empty:
        return result_df
    result_df["Peak"] = result_df["TotalAsset"].cummax()
    result_df["Drawdown"] = (result_df["TotalAsset"] - result_df["Peak"]) / result_df["Peak"]
    result_df["DailyReturn"] = result_df["TotalAsset"].pct_change().fillna(0) * 100
    return result_df


def normalize_ticker(ticker: str) -> str:
    ticker = str(ticker or "").upper().strip()
    if ticker not in SUPPORTED_TICKERS:
        raise ValueError(
            f"라오어 4.0 원문공식 엔진은 현재 TQQQ/SOXL만 지원합니다. 입력 티커={ticker}"
        )
    return ticker


def normalize_split(split_count: int) -> int:
    split_count = int(split_count)
    if split_count not in SUPPORTED_SPLITS:
        raise ValueError(
            "라오어 4.0 원문공식 엔진은 현재 별% 공식이 명시된 20/40분할만 지원합니다. "
            f"입력 분할={split_count}"
        )
    return split_count


def calc_star_pct(ticker: str, split_count: int, T: float) -> float:
    """라오어 4.0 원문 별% 공식."""
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
    if avg_price <= 0:
        return 0.0
    return avg_price * (1.0 + star_pct / 100.0)


def calc_designated_sell_pct(ticker: str) -> float:
    ticker = normalize_ticker(ticker)
    return 15.0 if ticker == "TQQQ" else 20.0


def current_phase(T: float, split_count: int) -> str:
    if T <= 0:
        return "무포지션"
    if T >= split_count:
        return "소진모드"
    if T < split_count / 2:
        return "전반전"
    return "후반전"


def safe_daily_attempt(cash: float, split_count: int, T: float) -> float:
    remain = max(float(split_count) - float(T), 0.000001)
    return max(0.0, cash / remain)


def execute_buy(
    state: PositionState,
    date: pd.Timestamp,
    close_price: float,
    target_amount: float,
    fee_rate: float,
) -> Tuple[float, float, float]:
    """target_amount만큼 종가 체결 매수. 반환: gross_buy, fee, shares_bought"""
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
    """지정 비율 매도. 반환: net_sell, profit, shares_sold"""
    if state.shares <= 0 or sell_price <= 0 or sell_fraction <= 0:
        return 0.0, 0.0, 0.0

    sell_fraction = max(0.0, min(1.0, float(sell_fraction)))
    shares_sold = state.shares * sell_fraction
    gross_sell = shares_sold * sell_price
    fee = gross_sell * fee_rate
    net_sell = gross_sell - fee
    cost_sold = state.cost_basis * sell_fraction
    profit = net_sell - cost_sold
    return_pct = (profit / cost_sold) * 100.0 if cost_sold > 0 else 0.0
    hold_days = (date - state.entry_date).days if state.entry_date is not None else 0

    trade_logs.append({
        "BuyDate": state.entry_date,
        "SellDate": date,
        "HoldDays": hold_days,
        "BuyAmount": cost_sold,
        "SellAmount": net_sell,
        "Profit": profit,
        "ReturnPct": return_pct,
        "Reason": reason,
        "SellPrice": sell_price,
        "SharesSold": shares_sold,
    })

    state.cash += net_sell
    state.shares -= shares_sold
    state.cost_basis -= cost_sold

    if state.shares <= 1e-10 or state.cost_basis <= 1e-6:
        state.shares = 0.0
        state.cost_basis = 0.0
        state.T = 0.0
        state.entry_date = None

    return net_sell, profit, shares_sold


def run_raor_infinite4_core(
    daily_df: pd.DataFrame,
    ticker: str = "TQQQ",
    split_count: int = 40,
    initial_cash: float = 100_000_000,
    fee_rate_pct: float = 0.1,
    first_loc_buffer_pct: float = 12.0,
    enable_designated_sell: bool = True,
    enable_quarter_sell: bool = True,
    max_days_without_position: int | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """라오어 무한매수4.0 원문기반 백테스트.

    Parameters
    ----------
    first_loc_buffer_pct:
        첫매수 LOC를 전날종가보다 얼마나 높게 둘지. 원문 일반 가이드 10~15%, 기본 12%.
    """
    ticker = normalize_ticker(ticker)
    split_count = normalize_split(split_count)

    df = daily_df.copy()
    if "Date" not in df.columns:
        first_col = df.columns[0]
        df = df.rename(columns={first_col: "Date"})
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

    if "Close" not in df.columns:
        raise ValueError("daily_df에 Close 컬럼이 필요합니다.")
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df = df.dropna(subset=["Close"]).reset_index(drop=True)

    # Open/High/Low가 없으면 Close로 대체
    for col in ["Open", "High", "Low"]:
        if col not in df.columns:
            df[col] = df["Close"]
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(df["Close"])

    fee_rate = float(fee_rate_pct) / 100.0
    state = PositionState(cash=float(initial_cash))
    results: List[Dict] = []
    trade_logs: List[Dict] = []

    no_position_days = 0

    for i, row in df.iterrows():
        date = row["Date"]
        close_price = float(row["Close"])
        high_price = float(row.get("High", close_price))
        prev_close = float(df.loc[i - 1, "Close"]) if i > 0 else close_price

        action_parts: List[str] = []
        debug_parts: List[str] = []

        avg_before = state.avg_price
        phase_before = current_phase(state.T, split_count)
        star_pct_before = calc_star_pct(ticker, split_count, state.T) if state.T > 0 else 0.0
        star_price_before = calc_star_price(avg_before, star_pct_before) if state.T > 0 else 0.0
        buy_star_price = max(0.0, star_price_before - 0.01) if star_price_before > 0 else 0.0
        designated_sell_pct = calc_designated_sell_pct(ticker)
        designated_sell_price = avg_before * (1.0 + designated_sell_pct / 100.0) if avg_before > 0 else 0.0

        # 1) 매도: 지정가매도 먼저 확인. 같은 날 복수 주문의 체결순서가 불명확하므로 과매도 방지를 위해 지정가 전량청산을 우선 처리.
        if state.shares > 0 and enable_designated_sell and designated_sell_price > 0 and high_price >= designated_sell_price:
            execute_sell(
                state=state,
                date=date,
                sell_price=designated_sell_price,
                sell_fraction=1.0,
                fee_rate=fee_rate,
                reason=f"라오어 지정가매도 {ticker} +{designated_sell_pct:.0f}%",
                trade_logs=trade_logs,
            )
            action_parts.append("지정가매도")
            debug_parts.append(f"지정가 {designated_sell_price:.2f} 체결")

        # 2) 쿼터매도: 별%가격 LOC 매도, 보유수량 25%, T = 기존T * 0.75
        if state.shares > 0 and enable_quarter_sell:
            avg_now = state.avg_price
            star_pct_now = calc_star_pct(ticker, split_count, state.T)
            star_sell_price = calc_star_price(avg_now, star_pct_now)
            if star_sell_price > 0 and close_price >= star_sell_price:
                old_T = state.T
                execute_sell(
                    state=state,
                    date=date,
                    sell_price=close_price,
                    sell_fraction=0.25,
                    fee_rate=fee_rate,
                    reason=f"라오어 쿼터매도 LOC 별%가격 {star_sell_price:.2f}",
                    trade_logs=trade_logs,
                )
                if state.shares > 0:
                    state.T = old_T * 0.75
                action_parts.append("쿼터매도")
                debug_parts.append(f"T {old_T:.4f}→{state.T:.4f}")

        # 3) 매수
        if state.T <= 0 or state.shares <= 0:
            # 첫매수: 전날 종가보다 10~15% 정도 위값으로 1회매수 LOC 시도
            if i > 0:
                daily_attempt = safe_daily_attempt(state.cash, split_count, 0.0)
                first_loc_price = prev_close * (1.0 + float(first_loc_buffer_pct) / 100.0)
                if close_price <= first_loc_price:
                    gross_buy, fee, shares_bought = execute_buy(
                        state=state,
                        date=date,
                        close_price=close_price,
                        target_amount=daily_attempt,
                        fee_rate=fee_rate,
                    )
                    if gross_buy > 0:
                        state.T = 1.0
                        action_parts.append("첫매수LOC")
                        debug_parts.append(
                            f"첫매수 전날종가 {prev_close:.2f}×{1+first_loc_buffer_pct/100:.2f}={first_loc_price:.2f}, T=1"
                        )
                else:
                    action_parts.append("첫매수대기")
                    debug_parts.append(f"첫LOC {first_loc_price:.2f} 미체결")
            else:
                action_parts.append("첫날대기")
        else:
            if state.T < split_count:
                daily_attempt = safe_daily_attempt(state.cash, split_count, state.T)
                phase_now = current_phase(state.T, split_count)
                avg_now = state.avg_price
                star_pct_now = calc_star_pct(ticker, split_count, state.T)
                star_price_now = calc_star_price(avg_now, star_pct_now)
                star_buy_now = max(0.0, star_price_now - 0.01)

                if phase_now == "전반전":
                    filled_t = 0.0
                    # 별지점/큰수 LOC 0.5T
                    if star_buy_now > 0 and close_price <= star_buy_now:
                        gross_buy, fee, shares_bought = execute_buy(
                            state, date, close_price, daily_attempt * 0.5, fee_rate
                        )
                        if gross_buy > 0:
                            filled_t += 0.5
                            action_parts.append("전반전별LOC")
                    # 평단 LOC 0.5T
                    # 평단은 매수 전 평단 기준을 사용한다. 별LOC가 먼저 체결되어도 같은 날 주문표는 사전에 걸어둔 것으로 보기 때문.
                    if avg_now > 0 and close_price <= avg_now:
                        gross_buy, fee, shares_bought = execute_buy(
                            state, date, close_price, daily_attempt * 0.5, fee_rate
                        )
                        if gross_buy > 0:
                            filled_t += 0.5
                            action_parts.append("전반전평단LOC")

                    if filled_t > 0:
                        old_T = state.T
                        state.T = min(float(split_count), state.T + min(filled_t, 1.0))
                        debug_parts.append(
                            f"전반전 1회차 최대 1T, 체결 {filled_t:.1f}T, T {old_T:.4f}→{state.T:.4f}"
                        )

                else:
                    # 후반전/소진모드: 원문 세부 수량표는 추가 확인 대상.
                    # 임의 다중 T 증가는 금지하고, 1일 1회매수액 한도 내에서만 체결한다.
                    if star_buy_now > 0 and close_price <= star_buy_now:
                        gross_buy, fee, shares_bought = execute_buy(
                            state, date, close_price, daily_attempt, fee_rate
                        )
                        if gross_buy > 0:
                            old_T = state.T
                            state.T = min(float(split_count), state.T + 1.0)
                            action_parts.append("후반전LOC")
                            debug_parts.append(
                                f"후반전 LOC 1회매수액, T {old_T:.4f}→{state.T:.4f}"
                            )

        stock_value = state.shares * close_price
        total_asset = state.cash + stock_value
        avg_after = state.avg_price
        phase_after = current_phase(state.T, split_count)
        star_pct_after = calc_star_pct(ticker, split_count, state.T) if state.T > 0 else 0.0
        star_price_after = calc_star_price(avg_after, star_pct_after) if state.T > 0 else 0.0
        daily_attempt_after = safe_daily_attempt(state.cash, split_count, state.T) if state.T < split_count else 0.0

        if not action_parts:
            action_parts.append("관망")

        results.append({
            "Date": date,
            "Close": close_price,
            "RSI": _get_col(row, ["WeeklyRSI", "RSI"], 50),
            "Mode": phase_after,
            "Action": "+".join(action_parts),
            "Cash": state.cash,
            "Shares": state.shares,
            "StockValue": stock_value,
            "TotalAsset": total_asset,
            "CurrentSplit": state.T,
            "T": state.T,
            "AvgPrice": avg_after,
            "StarPct": star_pct_after,
            "StarPrice": star_price_after,
            "BuyStarPrice": max(0.0, star_price_after - 0.01) if star_price_after > 0 else 0.0,
            "DailyAttempt": daily_attempt_after,
            "DesignatedSellPrice": avg_after * (1.0 + designated_sell_pct / 100.0) if avg_after > 0 else 0.0,
            "RaorDebug": " | ".join(debug_parts),
        })

    result_df = add_metrics(pd.DataFrame(results))
    trade_df = pd.DataFrame(trade_logs)

    if not trade_df.empty:
        # MAE/MFE 계산
        maes = []
        mfes = []
        for _, trade in trade_df.iterrows():
            if pd.isna(trade.get("BuyDate")) or pd.isna(trade.get("SellDate")):
                maes.append(0.0)
                mfes.append(0.0)
                continue
            period = df[(df["Date"] >= trade["BuyDate"]) & (df["Date"] <= trade["SellDate"])]
            if period.empty:
                maes.append(0.0)
                mfes.append(0.0)
                continue
            entry_price = float(period.iloc[0]["Close"])
            min_price = float(period["Close"].min())
            max_price = float(period["Close"].max())
            maes.append(((min_price / entry_price) - 1.0) * 100.0 if entry_price > 0 else 0.0)
            mfes.append(((max_price / entry_price) - 1.0) * 100.0 if entry_price > 0 else 0.0)
        trade_df["MAE"] = maes
        trade_df["MFE"] = mfes

    return result_df, trade_df


# app.py/optimizer_lab.py에서 쓰기 좋은 별칭
run_raor_infinite4_backtest = run_raor_infinite4_core
