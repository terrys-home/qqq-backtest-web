import pandas as pd

# 1. 데이터 불러오기
df = pd.read_csv("QQQ_weekly_mode.csv")
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date")

# 2. 기본 설정
initial_cash = 100_000_000  # 초기자산 1억원
cash = initial_cash
shares = 0

# 3. 모드별 매수 금액
buy_amount_by_mode = {
    "침체": 2_000_000,
    "중립": 0,
    "상승": 1_000_000,
    "과열": 0,
}

results = []

# 4. 백테스트 반복
for _, row in df.iterrows():
    date = row["Date"]
    price = row["Close"]
    rsi = row["RSI"]
    mode = row["Mode"]

    action = "관망"
    buy_amount = 0
    sell_amount = 0

    # 과열이면 전량 매도
    if mode == "과열" and shares > 0:
        sell_amount = shares * price
        cash += sell_amount
        shares = 0
        action = "전량매도"

    # 침체/상승이면 매수
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
        "RSI": rsi,
        "Mode": mode,
        "Action": action,
        "BuyAmount": buy_amount,
        "SellAmount": sell_amount,
        "Shares": shares,
        "Cash": cash,
        "StockValue": stock_value,
        "TotalAsset": total_asset,
    })

# 5. 결과 저장
result_df = pd.DataFrame(results)
result_df.to_csv("QQQ_simple_backtest.csv", index=False, encoding="utf-8-sig")

# 6. 요약 출력
final_asset = result_df.iloc[-1]["TotalAsset"]
profit = final_asset - initial_cash
return_rate = (final_asset / initial_cash - 1) * 100

print(result_df.tail(20))
print("백테스트 완료: QQQ_simple_backtest.csv")
print(f"초기자산: {initial_cash:,.0f}원")
print(f"최종자산: {final_asset:,.0f}원")
print(f"수익금: {profit:,.0f}원")
print(f"수익률: {return_rate:.2f}%")