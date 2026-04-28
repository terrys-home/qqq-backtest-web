from app import run_backtest
import pandas as pd

results = []

split_range = [10, 15, 20]
sell_range = [65, 70, 75]
geuk_range = [2, 3, 4]
chim_range = [1, 2, 3]
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
                            mdd = bt["Drawdown"].min() * 100
                            return_rate = (final_asset / 100000000 - 1) * 100

                            print(f"테스트중: split={split_count}, sell={sell_rsi}, geuk={geuk}, chim={chim}, jung={jung}, sang={sang}, weight={weight}")

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
                                "mdd": round(mdd, 2)
                            })

df = pd.DataFrame(results)

# 수익률 TOP10
df.sort_values("return_rate", ascending=False).head(10).to_csv("QQQ_optimization_top10.csv", index=False, encoding="utf-8-sig")

# MDD 방어 TOP10
df.sort_values("mdd", ascending=False).head(10).to_csv("QQQ_mdd_top10.csv", index=False, encoding="utf-8-sig")

print("완료: TOP10 저장")