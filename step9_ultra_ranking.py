from app import run_backtest
import pandas as pd

results = []

split_range = [10, 15, 20]
sell_range = [65, 70, 75]
geuk_range = [1, 2, 3, 4]
chim_range = [0, 1, 2, 3]
jung_range = [0, 1]
sang_range = [0, 1]
weight_modes = ["equal", "back_weighted"]

for split_count in split_range:
    for sell_rsi in sell_range:
        for geuk in geuk_range:
            for chim in chim_range:
                for jung in jung_range:
                    for sang in sang_range:
                        for weight in weight_modes:
                            bt = run_backtest(
                                split_count=split_count,
                                sell_rsi=sell_rsi,
                                geuk_chimche_strength=geuk,
                                chimche_strength=chim,
                                jungrip_strength=jung,
                                sangseung_strength=sang,
                                weight_mode=weight
                            )

                            final = bt.tail(1).iloc[0]

                            final_asset = final["TotalAsset"]
                            return_rate = (final_asset / 100_000_000 - 1) * 100
                            mdd = bt["Drawdown"].min() * 100

                            # MDD가 너무 큰 전략은 감점
                            score = (return_rate * 0.6) + ((100 + mdd) * 0.4)

                            results.append({
                                "split": split_count,
                                "sell_rsi": sell_rsi,
                                "geuk": geuk,
                                "chim": chim,
                                "jung": jung,
                                "sang": sang,
                                "weight": weight,
                                "final_asset": round(final_asset),
                                "return_rate": round(return_rate, 2),
                                "mdd": round(mdd, 2),
                                "score": round(score, 2)
                            })

df = pd.DataFrame(results)

df_score = df.sort_values("score", ascending=False).head(10)
df_score.to_csv("QQQ_ultra_score_top10.csv", index=False, encoding="utf-8-sig")

df_balance = df[
    (df["return_rate"] >= 150) &
    (df["mdd"] >= -40)
].sort_values("score", ascending=False).head(10)

df_balance.to_csv("QQQ_balance_top10.csv", index=False, encoding="utf-8-sig")

print("완료: 울트라 랭킹 저장")
print("생성 파일:")
print("QQQ_ultra_score_top10.csv")
print("QQQ_balance_top10.csv")