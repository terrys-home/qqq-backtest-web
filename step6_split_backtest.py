import pandas as pd

df = pd.read_csv("QQQ_daily_with_mode.csv")
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date")

initial_cash = 100_000_000
cash = initial_cash
shares = 0

split_count = 7
split_unit = initial_cash / split_count
current_split = 0

results = []

for i, row in df.iterrows():
    date = row["Date"]
    price = row["Close"]
    rsi = row["WeeklyRSI"]
    mode = row["WeeklyMode"]

    action = "관망"
    buy_amount = 0
    sell_amount = 0
    buy_splits_today = 0

    # 전날 분할 상태
    if len(results) == 0:
        prev_split = 0
    else:
        prev_split = results[-1]["CurrentSplit"]

    # 과열이면 전량매도 후 분할 초기화
    if mode == "과열" and shares > 0:
        sell_amount = shares * price
        cash += sell_amount
        shares = 0
        current_split = 0
        action = "전량매도"

    # 침체/상승이면 전날 분할 + 1 만큼 맞춰서 매수
    elif mode in ["침체", "상승"]:
        target_split_today = prev_split + 1

        # 최대 분할수 제한
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
        "WeeklyMode": mode,
        "PrevSplit": prev_split,
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

# 🔥 최고 자산 (Running Max)
result_df["Peak"] = result_df["TotalAsset"].cummax()

# 🔥 Drawdown 계산 (현재 자산이 최고점 대비 얼마나 떨어졌는지)
result_df["Drawdown"] = (result_df["TotalAsset"] - result_df["Peak"]) / result_df["Peak"]

# 🔥 MDD (최대 낙폭)
mdd = result_df["Drawdown"].min()
result_df.to_csv("QQQ_split_backtest.csv", index=False, encoding="utf-8-sig")

final_asset = result_df.iloc[-1]["TotalAsset"]
profit = final_asset - initial_cash
return_rate = (final_asset / initial_cash - 1) * 100

print(result_df.tail(30))
print("분할매수 백테스트 완료: QQQ_split_backtest.csv")
print(f"초기자산: {initial_cash:,.0f}원")
print(f"최종자산: {final_asset:,.0f}원")
print(f"수익금: {profit:,.0f}원")
print(f"수익률: {return_rate:.2f}%")
print(f"MDD: {mdd:.2%}")