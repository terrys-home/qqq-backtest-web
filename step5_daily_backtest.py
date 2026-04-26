import pandas as pd

df = pd.read_csv("QQQ_daily_with_mode.csv")
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date")

initial_cash = 100_000_000
cash = initial_cash
shares = 0

buy_amount_by_mode = {
    "침체": 400_000,
    "중립": 0,
    "상승": 200_000,
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

    if mode == "과열" and shares > 0:
        sell_amount = shares * price
        cash += sell_amount
        shares = 0
        action = "전량매도"

    elif mode in ["침체", "상승"]:
        buy_amount = min(buy_amount_by_mode[mode], cash)

        if buy_amount > 0:
            buy_shares = buy_amount / price
            shares += buy_shares
            cash -= buy_amount
            action = "매수"

    stock_value = shares * price
    total_asset = cash + stock_value

    results.append({
        "Date": date,
        "Close": price,
        "WeeklyRSI": rsi,
        "WeeklyMode": mode,
        "Action": action,
        "BuyAmount": buy_amount,
        "SellAmount": sell_amount,
        "Shares": shares,
        "Cash": cash,
        "StockValue": stock_value,
        "TotalAsset": total_asset,
    })

result_df = pd.DataFrame(results)
result_df.to_csv("QQQ_daily_backtest.csv", index=False, encoding="utf-8-sig")

final_asset = result_df.iloc[-1]["TotalAsset"]
profit = final_asset - initial_cash
return_rate = (final_asset / initial_cash - 1) * 100

print(result_df.tail(20))
print("일봉 백테스트 완료: QQQ_daily_backtest.csv")
print(f"초기자산: {initial_cash:,.0f}원")
print(f"최종자산: {final_asset:,.0f}원")
print(f"수익금: {profit:,.0f}원")
print(f"수익률: {return_rate:.2f}%")