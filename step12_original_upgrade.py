import pandas as pd

# =========================
# 오리지널 무한매수법 2.0
# =========================

DATA_FILE = "QQQ_daily_with_mode.csv"

INITIAL_CASH = 100_000_000
SPLIT_COUNT = 40
PROFIT_TARGET = 0.10
START_DATE = "2010-01-01"
END_DATE = "2026-04-24"

df = pd.read_csv(DATA_FILE)
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date")

# 이동평균선
df["MA5"] = df["Close"].rolling(5).mean()
df["MA20"] = df["Close"].rolling(20).mean()

df = df[
    (df["Date"] >= START_DATE) &
    (df["Date"] <= END_DATE)
].copy()

cash = INITIAL_CASH
shares = 0
invested_amount = 0
current_split = 0
split_unit = INITIAL_CASH / SPLIT_COUNT

results = []

for _, row in df.iterrows():
    date = row["Date"]
    price = row["Close"]
    ma5 = row["MA5"]
    ma20 = row["MA20"]

    action = "관망"
    buy_amount = 0
    sell_amount = 0

    stock_value = shares * price
    total_asset = cash + stock_value

    avg_price = invested_amount / shares if shares > 0 else 0
    profit_rate = (price / avg_price - 1) if avg_price > 0 else 0

    # 목표수익률 도달 시 전량매도
    if shares > 0 and profit_rate >= PROFIT_TARGET:
        sell_amount = shares * price
        cash += sell_amount

        shares = 0
        invested_amount = 0
        current_split = 0

        action = "목표수익 전량매도"

    elif current_split < SPLIT_COUNT and cash > 0:

        # =====================
        # 매수 강도 결정
        # =====================
        buy_split = 1

        if pd.notna(ma20) and price < ma20:
            buy_split = 3
        elif pd.notna(ma5) and price < ma5:
            buy_split = 2

        remain_split = SPLIT_COUNT - current_split
        actual_split = min(buy_split, remain_split)

        buy_amount = min(split_unit * actual_split, cash)

        if buy_amount > 0:
            buy_shares = buy_amount / price

            shares += buy_shares
            cash -= buy_amount
            invested_amount += buy_amount
            current_split += actual_split

            action = f"{actual_split}분할 매수"

    stock_value = shares * price
    total_asset = cash + stock_value

    results.append({
        "Date": date,
        "Close": price,
        "MA5": ma5,
        "MA20": ma20,
        "Action": action,
        "CurrentSplit": current_split,
        "BuyAmount": buy_amount,
        "SellAmount": sell_amount,
        "Shares": shares,
        "AvgPrice": avg_price,
        "Cash": cash,
        "StockValue": stock_value,
        "TotalAsset": total_asset,
    })

result_df = pd.DataFrame(results)

# MDD
result_df["Peak"] = result_df["TotalAsset"].cummax()
result_df["Drawdown"] = (
    result_df["TotalAsset"] - result_df["Peak"]
) / result_df["Peak"]

final_asset = result_df.iloc[-1]["TotalAsset"]
profit = final_asset - INITIAL_CASH
return_rate = (final_asset / INITIAL_CASH - 1) * 100
mdd = result_df["Drawdown"].min() * 100

# 저장
result_df.to_csv(
    "QQQ_original_upgrade.csv",
    index=False,
    encoding="utf-8-sig"
)

print("오리지널 무한매수법 2.0 완료")
print("저장파일: QQQ_original_upgrade.csv")
print(f"초기자산: {INITIAL_CASH:,.0f}원")
print(f"최종자산: {final_asset:,.0f}원")
print(f"수익금: {profit:,.0f}원")
print(f"수익률: {return_rate:.2f}%")
print(f"MDD: {mdd:.2f}%")