import pandas as pd

DATA_FILE = "QQQ_daily_with_mode.csv"

INITIAL_CASH = 100_000_000
START_DATE = "2010-01-01"
END_DATE = "2026-04-24"

df = pd.read_csv(DATA_FILE)
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date")

df["MA5"] = df["Close"].rolling(5).mean()
df["MA20"] = df["Close"].rolling(20).mean()

df = df[
    (df["Date"] >= START_DATE) &
    (df["Date"] <= END_DATE)
].copy()


def run_original_upgrade(
    split_count=40,
    profit_target=0.10,
    ma5_buy_split=2,
    ma20_buy_split=3
):
    cash = INITIAL_CASH
    shares = 0
    invested_amount = 0
    current_split = 0
    split_unit = INITIAL_CASH / split_count

    results = []

    for _, row in df.iterrows():
        price = row["Close"]
        ma5 = row["MA5"]
        ma20 = row["MA20"]

        buy_amount = 0
        sell_amount = 0
        action = "관망"

        avg_price = invested_amount / shares if shares > 0 else 0
        profit_rate = (price / avg_price - 1) if avg_price > 0 else 0

        if shares > 0 and profit_rate >= profit_target:
            sell_amount = shares * price
            cash += sell_amount

            shares = 0
            invested_amount = 0
            current_split = 0
            action = "목표수익 전량매도"

        elif current_split < split_count and cash > 0:
            buy_split = 1

            if pd.notna(ma20) and price < ma20:
                buy_split = ma20_buy_split
            elif pd.notna(ma5) and price < ma5:
                buy_split = ma5_buy_split

            remain_split = split_count - current_split
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
            "TotalAsset": total_asset,
            "Cash": cash,
            "StockValue": stock_value,
            "CurrentSplit": current_split,
            "Action": action,
            "BuyAmount": buy_amount,
            "SellAmount": sell_amount,
        })

    result_df = pd.DataFrame(results)
    result_df["Peak"] = result_df["TotalAsset"].cummax()
    result_df["Drawdown"] = (
        result_df["TotalAsset"] - result_df["Peak"]
    ) / result_df["Peak"]

    final_asset = result_df.iloc[-1]["TotalAsset"]
    return_rate = (final_asset / INITIAL_CASH - 1) * 100
    mdd = result_df["Drawdown"].min() * 100

    return {
        "final_asset": round(final_asset),
        "return_rate": round(return_rate, 2),
        "mdd": round(mdd, 2),
    }


results = []

split_range = [30, 40, 50, 60]
profit_targets = [0.05, 0.07, 0.10, 0.12, 0.15]
ma5_splits = [1, 2, 3, 4]
ma20_splits = [2, 3, 4, 5, 6]

for split_count in split_range:
    for profit_target in profit_targets:
        for ma5_buy_split in ma5_splits:
            for ma20_buy_split in ma20_splits:
                if ma20_buy_split < ma5_buy_split:
                    continue

                r = run_original_upgrade(
                    split_count=split_count,
                    profit_target=profit_target,
                    ma5_buy_split=ma5_buy_split,
                    ma20_buy_split=ma20_buy_split
                )

                score = (r["return_rate"] * 0.6) + ((100 + r["mdd"]) * 0.4)

                results.append({
                    "split_count": split_count,
                    "profit_target": profit_target,
                    "ma5_buy_split": ma5_buy_split,
                    "ma20_buy_split": ma20_buy_split,
                    "final_asset": r["final_asset"],
                    "return_rate": r["return_rate"],
                    "mdd": r["mdd"],
                    "score": round(score, 2),
                })

                print(
                    f"테스트중 split={split_count}, "
                    f"target={profit_target}, "
                    f"ma5={ma5_buy_split}, "
                    f"ma20={ma20_buy_split}, "
                    f"return={r['return_rate']}, "
                    f"mdd={r['mdd']}"
                )

result_df = pd.DataFrame(results)

result_df.sort_values("return_rate", ascending=False).head(10).to_csv(
    "QQQ_original_return_top10.csv",
    index=False,
    encoding="utf-8-sig"
)

result_df[result_df["mdd"] >= -20].sort_values("score", ascending=False).head(10).to_csv(
    "QQQ_original_balance_top10.csv",
    index=False,
    encoding="utf-8-sig"
)

result_df.sort_values("score", ascending=False).head(10).to_csv(
    "QQQ_original_score_top10.csv",
    index=False,
    encoding="utf-8-sig"
)

print("완료: 오리지널 2.0 최적화 저장")
print("생성 파일:")
print("QQQ_original_return_top10.csv")
print("QQQ_original_balance_top10.csv")
print("QQQ_original_score_top10.csv")