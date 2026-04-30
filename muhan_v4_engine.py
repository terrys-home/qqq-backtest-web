"""
muhan_v4_engine.py
Step23A/B/C/D 무한매수법 4.0 V4 판단엔진

자동주문/RPA가 아니라 백테스트/판단엔진 전용입니다.

Step23D 추가:
- T금액, 누적매수금, 누적매도금, 누적수수료, 실현손익
- 현재보유원금, 쿼터매도 후 남은원금, 매수/매도수량
- 현금잔고/총자산/분할상태 검증 컬럼
- 과대수익 여부를 보기 위한 AuditFlag
"""

from __future__ import annotations
import pandas as pd


def _clamp_split_count(split_count: int) -> int:
    split_count = int(split_count)
    if split_count in (20, 30, 40):
        return split_count
    return 20 if split_count < 25 else 30 if split_count < 35 else 40


def _safe_float(value, default=0.0):
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def calc_dynamic_star_point(
    avg_price: float,
    target_profit: float = 7.0,
    star_pct: float = 7.0,
    sheet_loc_price: float = 0.0,
    sheet_sell_price: float = 0.0,
):
    """언이시트 근접 별지점 계산.

    1) LOC 수동 입력이 있으면 그 가격을 별지점으로 우선 사용
    2) 매도가 수동 입력이 있으면 평균단가 대비 목표수익률을 역산해 별점률 보정
    3) 둘 다 없으면 avg_price * (1 - star_pct)로 자동 계산
    """
    avg_price = _safe_float(avg_price)
    target_profit = _safe_float(target_profit, 7.0)
    star_pct = _safe_float(star_pct, 7.0)
    sheet_loc_price = _safe_float(sheet_loc_price)
    sheet_sell_price = _safe_float(sheet_sell_price)

    if avg_price <= 0:
        return {
            "star_point": 0.0,
            "star_score": star_pct,
            "sell_price": 0.0,
            "sheet_override_used": False,
            "source": "no_position",
        }

    auto_sell_price = avg_price * (1 + target_profit / 100)
    sell_price = sheet_sell_price if sheet_sell_price > 0 else auto_sell_price

    if sheet_loc_price > 0:
        star_point = sheet_loc_price
        star_score = max(0.0, (1 - star_point / avg_price) * 100)
        return {
            "star_point": star_point,
            "star_score": star_score,
            "sell_price": sell_price,
            "sheet_override_used": True,
            "source": "sheet_loc",
        }

    if sheet_sell_price > 0:
        implied_target = max(0.0, (sheet_sell_price / avg_price - 1) * 100)
        adjusted_star_pct = max(1.0, min(25.0, (star_pct + implied_target) / 2))
        star_point = avg_price * (1 - adjusted_star_pct / 100)
        return {
            "star_point": star_point,
            "star_score": adjusted_star_pct,
            "sell_price": sell_price,
            "sheet_override_used": True,
            "source": "sheet_sell_reverse",
        }

    star_point = avg_price * (1 - star_pct / 100)
    return {
        "star_point": star_point,
        "star_score": star_pct,
        "sell_price": sell_price,
        "sheet_override_used": False,
        "source": "auto_star_pct",
    }


def _add_metrics(result_df: pd.DataFrame) -> pd.DataFrame:
    result_df["Peak"] = result_df["TotalAsset"].cummax()
    result_df["Drawdown"] = (result_df["TotalAsset"] - result_df["Peak"]) / result_df["Peak"]
    result_df["DailyReturn"] = result_df["TotalAsset"].pct_change().fillna(0) * 100
    return result_df


def _calc_mae_mfe(daily_df: pd.DataFrame, trade_df: pd.DataFrame):
    if trade_df.empty:
        return trade_df
    maes, mfes = [], []
    for _, trade in trade_df.iterrows():
        if pd.isna(trade.get("BuyDate")) or pd.isna(trade.get("SellDate")):
            maes.append(0.0)
            mfes.append(0.0)
            continue
        period = daily_df[(daily_df["Date"] >= trade["BuyDate"]) & (daily_df["Date"] <= trade["SellDate"])].copy()
        if period.empty:
            maes.append(0.0)
            mfes.append(0.0)
            continue
        entry_price = float(period.iloc[0]["Close"])
        min_price = float(period["Close"].min())
        max_price = float(period["Close"].max())
        maes.append(((min_price / entry_price) - 1) * 100 if entry_price > 0 else 0.0)
        mfes.append(((max_price / entry_price) - 1) * 100 if entry_price > 0 else 0.0)
    trade_df["MAE"] = maes
    trade_df["MFE"] = mfes
    return trade_df


def _audit_flag(cash, stock_value, total_asset, current_split, split_count, shares, avg_price):
    flags = []
    if abs((cash + stock_value) - total_asset) > 1:
        flags.append("ASSET_MISMATCH")
    if cash < -1:
        flags.append("NEGATIVE_CASH")
    if current_split > split_count + 1e-6:
        flags.append("SPLIT_OVER")
    if shares < -1e-9:
        flags.append("NEGATIVE_SHARES")
    if shares > 0 and avg_price <= 0:
        flags.append("AVG_PRICE_ZERO")
    return "정상" if not flags else ",".join(flags)


def run_infinite4_v4_core(
    daily_df: pd.DataFrame,
    initial_cash: float = 100_000_000,
    split_count: int = 30,
    target_profit: float = 7.0,
    quarter_sell_ratio: float = 25.0,
    star_pct: float = 7.0,
    max_gap_pct: float = 20.0,
    max_hold_days: int = 365,
    sheet_loc_price: float = 0.0,
    sheet_big_buy_price: float = 0.0,
    sheet_sell_price: float = 0.0,
    fee_rate_pct: float = 0.25,
):
    split_count = _clamp_split_count(split_count)
    target_profit = _safe_float(target_profit, 7.0)
    quarter_sell_ratio = _safe_float(quarter_sell_ratio, 25.0)
    star_pct = _safe_float(star_pct, 7.0)
    max_gap_pct = _safe_float(max_gap_pct, 20.0)
    max_hold_days = int(max_hold_days or 365)
    sheet_loc_price = _safe_float(sheet_loc_price)
    sheet_big_buy_price = _safe_float(sheet_big_buy_price)
    sheet_sell_price = _safe_float(sheet_sell_price)

    cash = float(initial_cash)
    shares = 0.0
    avg_price = 0.0
    current_split = 0.0
    entry_date = None
    entry_amount = 0.0

    unit_cash = float(initial_cash) / split_count
    fee_rate = fee_rate_pct / 100
    sell_ratio = max(0.01, min(quarter_sell_ratio / 100, 1.0))
    max_gap_rate = max(0.0, max_gap_pct / 100)

    cumulative_buy_amount = 0.0      # 수수료 제외 매수원금
    cumulative_sell_amount = 0.0     # 수수료 차감 후 매도금
    cumulative_fee = 0.0
    realized_profit = 0.0
    max_cash_used = 0.0

    results = []
    trade_logs = []

    daily_df = daily_df.copy()
    daily_df["Date"] = pd.to_datetime(daily_df["Date"])
    daily_df["Close"] = pd.to_numeric(daily_df["Close"], errors="coerce")
    daily_df = daily_df.dropna(subset=["Date", "Close"]).sort_values("Date").reset_index(drop=True)

    for _, row in daily_df.iterrows():
        date = row["Date"]
        price = float(row["Close"])
        rsi = row.get("WeeklyRSI", row.get("RSI", 50))
        action = "관망"
        reason = ""

        last_buy_units = 0.0
        last_buy_amount = 0.0
        last_buy_qty = 0.0
        last_sell_fraction = 0.0
        last_sell_qty = 0.0
        last_sell_amount = 0.0
        last_cost_basis_sold = 0.0
        principal_after_sell = entry_amount

        hold_days = (date - entry_date).days if entry_date is not None and shares > 0 else 0
        mode = "소진모드" if current_split >= split_count else "일반모드"
        half = "전반전" if current_split < (split_count / 2) else "후반전"

        star_info = calc_dynamic_star_point(avg_price, target_profit, star_pct, sheet_loc_price, sheet_sell_price)
        star_point = float(star_info["star_point"])
        star_score = float(star_info["star_score"])
        sell_price = float(star_info["sell_price"])
        sheet_override_used = bool(star_info["sheet_override_used"])

        auto_big_buy_price = avg_price * (1 - max(star_score * 1.5, star_score + 3) / 100) if avg_price > 0 else 0.0
        big_buy_price = sheet_big_buy_price if sheet_big_buy_price > 0 else auto_big_buy_price

        hit_target = shares > 0 and avg_price > 0 and sell_price > 0 and price >= sell_price
        hit_max_hold = shares > 0 and hold_days >= max_hold_days

        if hit_target or hit_max_hold:
            if hit_max_hold and not hit_target:
                sell_fraction = 1.0
                sell_reason = f"보유일 {hold_days}일 >= {max_hold_days}일 관리매도"
            elif mode == "소진모드":
                sell_fraction = min(0.5, max(sell_ratio, 0.25))
                sell_reason = f"소진모드 목표가 도달 부분매도({sell_fraction*100:.0f}%)"
            elif half == "전반전":
                sell_fraction = sell_ratio
                sell_reason = f"전반전 목표가 도달 쿼터매도({quarter_sell_ratio:.1f}%)"
            else:
                sell_fraction = min(0.5, max(sell_ratio, 0.25))
                sell_reason = f"후반전 목표가 도달 부분매도({sell_fraction*100:.0f}%)"

            if current_split <= 1.01:
                sell_fraction = 1.0
                sell_reason = "목표가 도달 전량매도"

            sell_shares = shares * sell_fraction
            gross_sell = sell_shares * price
            sell_fee = gross_sell * fee_rate
            net_sell = gross_sell - sell_fee
            cost_basis_sold = entry_amount * sell_fraction if entry_amount > 0 else avg_price * sell_shares
            profit = net_sell - cost_basis_sold
            return_pct = (profit / cost_basis_sold) * 100 if cost_basis_sold > 0 else 0.0

            cash += net_sell
            shares -= sell_shares
            entry_amount -= cost_basis_sold
            principal_after_sell = entry_amount
            current_split = max(0.0, current_split * (1 - sell_fraction))

            cumulative_sell_amount += net_sell
            cumulative_fee += sell_fee
            realized_profit += profit
            last_sell_fraction = sell_fraction
            last_sell_qty = sell_shares
            last_sell_amount = net_sell
            last_cost_basis_sold = cost_basis_sold

            trade_logs.append({
                "BuyDate": entry_date,
                "SellDate": date,
                "HoldDays": hold_days,
                "BuyAmount": cost_basis_sold,
                "SellAmount": net_sell,
                "Profit": profit,
                "ReturnPct": return_pct,
                "Reason": sell_reason,
                "Mode": mode,
                "Half": half,
                "StarPoint": star_point,
                "SellPrice": sell_price,
                "TAmount": unit_cash,
                "SellFraction": sell_fraction,
                "SellQty": sell_shares,
                "CostBasisSold": cost_basis_sold,
                "PrincipalAfterSell": principal_after_sell,
                "CumulativeBuyAmount": cumulative_buy_amount,
                "CumulativeSellAmount": cumulative_sell_amount,
                "CumulativeFee": cumulative_fee,
                "RealizedProfit": realized_profit,
            })

            action = "쿼터매도" if sell_fraction < 1.0 else "전량매도"
            reason = sell_reason

            if shares <= 1e-9 or current_split <= 0.01:
                shares = 0.0
                avg_price = 0.0
                current_split = 0.0
                entry_date = None
                entry_amount = 0.0
                principal_after_sell = 0.0

        if action == "관망":
            has_capacity = current_split < split_count
            should_enter = shares <= 0 and has_capacity
            should_add_loc = shares > 0 and has_capacity and star_point > 0 and price <= star_point
            should_big_buy = shares > 0 and has_capacity and big_buy_price > 0 and price <= big_buy_price

            buy_units = 0.0
            buy_tag = ""

            if should_enter:
                buy_units = 1.0
                buy_tag = "최초 1T LOC"
            elif should_big_buy:
                buy_units = 2.0 if half == "후반전" or mode == "소진모드" else 1.0
                buy_tag = "큰수매수"
            elif should_add_loc:
                buy_units = 1.0
                buy_tag = "동적 별지점 LOC"

            if buy_units > 0 and not should_enter:
                ref_price = big_buy_price if should_big_buy and big_buy_price > 0 else star_point
                loc_gap = abs(price - ref_price) / ref_price if ref_price > 0 else 0.0
                if loc_gap > max_gap_rate:
                    buy_units = 0.0
                    reason = f"LOC 괴리 초과로 매수 보류: gap {loc_gap*100:.2f}% > {max_gap_pct:.2f}%"

            if buy_units > 0:
                remain_split = max(split_count - current_split, 0.0)
                buy_units = min(buy_units, remain_split)
                buy_amount = min(unit_cash * buy_units, cash / (1 + fee_rate))
                if buy_amount > 0 and price > 0:
                    buy_fee = buy_amount * fee_rate
                    total_buy_cost = buy_amount + buy_fee
                    buy_shares = buy_amount / price

                    total_cost_before = shares * avg_price
                    shares += buy_shares
                    total_cost_after = total_cost_before + buy_amount
                    avg_price = total_cost_after / shares if shares > 0 else 0.0

                    cash -= total_buy_cost
                    current_split = min(float(split_count), current_split + buy_units)
                    if entry_date is None:
                        entry_date = date
                        entry_amount = total_buy_cost
                    else:
                        entry_amount += total_buy_cost

                    cumulative_buy_amount += buy_amount
                    cumulative_fee += buy_fee
                    max_cash_used = max(max_cash_used, initial_cash - cash)
                    last_buy_units = buy_units
                    last_buy_amount = buy_amount
                    last_buy_qty = buy_shares

                    action = buy_tag
                    reason = f"{buy_tag} / {buy_units:.1f}T / sheet_override={sheet_override_used}"

        stock_value = shares * price
        total_asset = cash + stock_value
        mode = "소진모드" if current_split >= split_count else "일반모드"
        half = "전반전" if current_split < (split_count / 2) else "후반전"
        star_info = calc_dynamic_star_point(avg_price, target_profit, star_pct, sheet_loc_price, sheet_sell_price)
        star_point = float(star_info["star_point"])
        star_score = float(star_info["star_score"])
        sell_price = float(star_info["sell_price"])
        big_buy_price = sheet_big_buy_price if sheet_big_buy_price > 0 else (avg_price * (1 - max(star_score * 1.5, star_score + 3) / 100) if avg_price > 0 else 0.0)
        quarter_sell_qty = shares * sell_ratio if shares > 0 else 0.0
        position_principal = shares * avg_price if shares > 0 else 0.0
        remaining_split = max(split_count - current_split, 0.0)
        exposure_pct = (stock_value / total_asset * 100) if total_asset > 0 else 0.0
        audit_flag = _audit_flag(cash, stock_value, total_asset, current_split, split_count, shares, avg_price)

        results.append({
            "Date": date,
            "Close": price,
            "RSI": rsi,
            "Mode": mode,
            "Half": half,
            "Action": action,
            "Reason": reason,
            "Cash": cash,
            "Shares": shares,
            "StockValue": stock_value,
            "TotalAsset": total_asset,
            "CurrentSplit": current_split,
            "RemainingSplit": remaining_split,
            "AvgPrice": avg_price,
            "StarPrice": star_point,
            "StarPoint": star_point,
            "StarScore": star_score,
            "NextLOCPrice": star_point,
            "BigBuyPrice": big_buy_price,
            "SellPrice": sell_price,
            "QuarterSellQty": quarter_sell_qty,
            "SheetOverrideUsed": star_info["sheet_override_used"],
            "StarSource": star_info["source"],

            # Step23D 검증 컬럼
            "TAmount": unit_cash,
            "PositionPrincipal": position_principal,
            "EntryAmountWithFee": entry_amount,
            "PrincipalAfterSell": principal_after_sell,
            "LastBuyUnits": last_buy_units,
            "LastBuyAmount": last_buy_amount,
            "LastBuyQty": last_buy_qty,
            "LastSellFraction": last_sell_fraction,
            "LastSellQty": last_sell_qty,
            "LastSellAmount": last_sell_amount,
            "LastCostBasisSold": last_cost_basis_sold,
            "CumulativeBuyAmount": cumulative_buy_amount,
            "CumulativeSellAmount": cumulative_sell_amount,
            "CumulativeFee": cumulative_fee,
            "RealizedProfit": realized_profit,
            "MaxCashUsed": max_cash_used,
            "ExposurePct": exposure_pct,
            "AuditFlag": audit_flag,
        })

    result_df = pd.DataFrame(results)
    result_df = _add_metrics(result_df)
    trade_df = pd.DataFrame(trade_logs)
    trade_df = _calc_mae_mfe(daily_df, trade_df)
    return result_df, trade_df
