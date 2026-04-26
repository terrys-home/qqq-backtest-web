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

buy_split_by_mode = {
    "침체": 2,
    "중립": 0,
    "상승": 1,
    "과열": 0,
}

results = []

for _, row in df.iterrows():
    date = row["Date"]
    price = row["Close"]
    rsi = row["WeeklyRSI"]
    mode = row["WeeklyMode"]

    action = "관망"
    buy_amount = 0
    sell_amount = 0
    buy_splits_today = 0

    # 과열이면 전량매도 후 분할 초기화
    if mode == "과열" and shares > 0:
        sell_amount = shares * price
        cash += sell_amount
        shares = 0
        current_split = 0
        action = "전량매도"

    # 침체/상승이면 분할매수
    elif mode in ["침체", "상승"]:
        target_buy_splits = buy_split_by_mode[mode]
        remain_splits = split_count - current_split
        buy_splits_today = min(target_buy_splits, remain_splits)

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