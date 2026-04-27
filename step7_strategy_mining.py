import pandas as pd

df = pd.read_csv("QQQ_daily_with_mode.csv")
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date")


def make_mode(rsi, sell_rsi):
    if rsi >= sell_rsi:
        return "과열"
    elif rsi >= 50:
        return "상승"
    elif rsi >= 30:
        return "중립"
    else:
        return "침체"


def run_backtest(split_count=7, sell_rsi=70, buy_modes=["침체", "상승"]):
    initial_cash = 100_000_000
    cash = initial_cash
    shares = 0
    split_unit = initial_cash / split_count
    current_split = 0

    results = []

    for _, row in df.iterrows():
        date = row["Date"]
        price = row["Close"]
        rsi = row["WeeklyRSI"]

        mode = make_mode(rsi, sell_rsi)

        action = "관망"
        buy_amount = 0
        sell_amount = 0
        buy_splits_today = 0

        if len(results) == 0:
            prev_split = 0
        else:
            prev_split = results[-1]["CurrentSplit"]

        if mode == "과열" and shares > 0:
            sell_amount = shares * price
            cash += sell_amount
            shares = 0
            current_split = 0
            action = "전량매도"

        elif mode in buy_modes:
            target_split_today = prev_split + 1
            target_split_today = min(target_split_today, split_count)

            buy_splits_today = target_split_today - current_split
            buy_splits_today = max(buy_splits_today, 0)

            if buy_splits_today > 0:
                buy_amount = min(split_unit * buy_splits_today, cash)
                buy_shares = buy_amount / price

                shares += buy_shares
                cash -= buy_amount
                current_split += buy_splits_today
                action = f"{buy_splits_today}분할 매수"

        stock_value = shares * price
        total_asset = cash + stock_value

        results.append({
            "Date": date,
            "Close": price,
            "WeeklyRSI": rsi,
            "Mode": mode,
            "Action": action,
            "BuySplitsToday": buy_splits_today,
            "CurrentSplit": current_split,
            "BuyAmount": buy_amount,
            "SellAmount": sell_amount,
            "Shares": shares,
            "Cash": cash,
            "StockValue": stock_value,
            "TotalAsset": total_asset,
        })

    result_df = pd.DataFrame(results)

    result_df["Peak"] = result_df["TotalAsset"].cummax()
    result_df["Drawdown"] = (result_df["TotalAsset"] - result_df["Peak"]) / result_df["Peak"]

    final_asset = result_df.iloc[-1]["TotalAsset"]
    return_rate = (final_asset / initial_cash - 1) * 100
    mdd = result_df["Drawdown"].min() * 100

    return {
        "split_count": split_count,
        "sell_rsi": sell_rsi,
        "buy_modes": "+".join(buy_modes),
        "final_asset": final_asset,
        "return_rate": return_rate,
        "mdd": mdd,
        "result_df": result_df,
    }


split_counts = [5, 7, 10, 15, 20]
sell_rsi_list = [65, 70, 75]

buy_mode_sets = [
    ["침체"],
    ["침체", "상승"],
]

optimization_results = []

for split_count in split_counts:
    for sell_rsi in sell_rsi_list:
        for buy_modes in buy_mode_sets:
            result = run_backtest(
                split_count=split_count,
                sell_rsi=sell_rsi,
                buy_modes=buy_modes
            )

            # 수익률 대비 MDD 점수
            score = result["return_rate"] / abs(result["mdd"])

            optimization_results.append({
                "분할수": result["split_count"],
                "매도RSI": result["sell_rsi"],
                "매수모드": result["buy_modes"],
                "최종자산": round(result["final_asset"]),
                "수익률(%)": round(result["return_rate"], 2),
                "MDD(%)": round(result["mdd"], 2),
                "점수": round(score, 2),
            })

summary_df = pd.DataFrame(optimization_results)

# 점수 높은 순으로 정렬
summary_df = summary_df.sort_values("점수", ascending=False)

top10 = summary_df.head(10)

top10.to_csv("QQQ_optimization_top10.csv", index=False, encoding="utf-8-sig")
summary_df.to_csv("QQQ_optimization_all.csv", index=False, encoding="utf-8-sig")

print("자동 최적화 TOP 10")
print(top10)
print("저장 완료:")
print("QQQ_optimization_top10.csv")
print("QQQ_optimization_all.csv")