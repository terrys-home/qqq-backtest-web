from flask import Flask, request
import pandas as pd

app = Flask(__name__)

daily = pd.read_csv("QQQ_daily_with_mode.csv")
daily["Date"] = pd.to_datetime(daily["Date"])
daily = daily.sort_values("Date")

if "MA120" not in daily.columns:
    daily["MA120"] = daily["Close"].rolling(120).mean()

if "MA200" not in daily.columns:
    daily["MA200"] = daily["Close"].rolling(200).mean()

weekly = pd.read_csv("QQQ_weekly_mode.csv")
weekly["Date"] = pd.to_datetime(weekly["Date"])
weekly = weekly.sort_values("Date")


def make_mode(rsi, sell_rsi):
    if rsi >= sell_rsi:
        return "과열"
    elif rsi >= 50:
        return "상승"
    elif rsi >= 30:
        return "중립"
    elif rsi >= 20:
        return "침체"
    else:
        return "극침체"


def run_backtest(
    split_count=10,
    sell_rsi=70,
    geuk_chimche_strength=3,
    chimche_strength=2,
    jungrip_strength=0,
    sangseung_strength=1,
    weight_mode="equal"
):
    initial_cash = 100_000_000
    cash = initial_cash
    shares = 0
    base_split_unit = initial_cash / split_count
    current_split = 0
    results = []

    strength_by_mode = {
        "침체": chimche_strength,
        "중립": jungrip_strength,
        "상승": sangseung_strength,
        "극침체": geuk_chimche_strength,
    }

    for _, row in daily.iterrows():
        date = row["Date"]
        price = row["Close"]
        rsi = row["WeeklyRSI"]
        mode = make_mode(rsi, sell_rsi)
        ma200 = row["MA200"]

        action = "관망"
        buy_amount = 0
        sell_amount = 0
        buy_splits_today = 0
        weight = 1.0

        if mode == "과열" and shares > 0:
            sell_amount = shares * price
            cash += sell_amount
            shares = 0
            current_split = 0
            action = "전량매도"

        elif mode in strength_by_mode:
            buy_strength = strength_by_mode[mode]

            if price > ma200:
                trend_multiplier = 1.0
            else:
                trend_multiplier = 0.2

            adjusted_strength = buy_strength * trend_multiplier

            if adjusted_strength > 0:
                target_split_today = min(current_split + adjusted_strength, split_count)
                buy_splits_today = max(target_split_today - current_split, 0)

                if buy_splits_today > 0:
                    if weight_mode == "back_weighted":
                        weight = 0.3 + (current_split / split_count) * 1.4
                    else:
                        weight = 1.0

                    buy_amount = min(base_split_unit * buy_splits_today * weight, cash)
                    buy_shares = buy_amount / price

                    shares += buy_shares
                    cash -= buy_amount
                    current_split += buy_splits_today
                    action = f"{buy_splits_today:.2f}분할 매수 / 가중치 {weight:.2f}"

        stock_value = shares * price
        total_asset = cash + stock_value

        results.append({
            "Date": date,
            "Close": price,
            "WeeklyRSI": rsi,
            "Mode": mode,
            "MA200": ma200,
            "Action": action,
            "BuySplitsToday": buy_splits_today,
            "Weight": weight,
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
    result_df["DailyReturn"] = result_df["TotalAsset"].pct_change().fillna(0) * 100
    result_df["DailyReturn"] = result_df["TotalAsset"].pct_change() * 100
    result_df["DailyReturn"] = result_df["DailyReturn"].fillna(0)

    return result_df


@app.route("/")
def home():
    split_count = request.args.get("split_count", default=10, type=int)
    sell_rsi = request.args.get("sell_rsi", default=70, type=int)

    geuk_chimche_strength = request.args.get("geuk_chimche_strength", default=3, type=int)
    chimche_strength = request.args.get("chimche_strength", default=2, type=int)
    jungrip_strength = request.args.get("jungrip_strength", default=0, type=int)
    sangseung_strength = request.args.get("sangseung_strength", default=1, type=int)
    weight_mode = request.args.get("weight_mode", default="equal")

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    min_date = weekly["Date"].min().strftime("%Y-%m-%d")
    max_date = weekly["Date"].max().strftime("%Y-%m-%d")

    if not start_date:
        start_date = weekly["Date"].tail(20).min().strftime("%Y-%m-%d")

    if not end_date:
        end_date = max_date

    filtered = weekly[
        (weekly["Date"] >= start_date) &
        (weekly["Date"] <= end_date)
    ].copy()

    filtered["Mode"] = filtered["RSI"].apply(lambda x: make_mode(x, sell_rsi))

    latest = filtered.tail(1).iloc[0]
    latest_date = latest["Date"].strftime("%Y-%m-%d")
    latest_close = round(latest["Close"], 2)
    latest_rsi = round(latest["RSI"], 2)
    latest_mode = latest["Mode"]

    bt = run_backtest(
        split_count=split_count,
        sell_rsi=sell_rsi,
        chimche_strength=chimche_strength,
        geuk_chimche_strength=geuk_chimche_strength,
        jungrip_strength=jungrip_strength,
        sangseung_strength=sangseung_strength,
        weight_mode=weight_mode
    )

    final = bt.tail(1).iloc[0]

    initial_cash = 100_000_000
    final_asset = round(final["TotalAsset"])
    profit = final_asset - initial_cash
    return_rate = (final_asset / initial_cash - 1) * 100
    cash = round(final["Cash"])
    stock_value = round(final["StockValue"])
    current_split = final["CurrentSplit"]
    mdd = bt["Drawdown"].min() * 100

    chart_labels = bt["Date"].dt.strftime("%Y-%m-%d").tolist()
    chart_assets = bt["TotalAsset"].round(0).tolist()
    chart_daily_return = bt["DailyReturn"].round(2).tolist()
    chart_drawdown = (bt["Drawdown"] * 100).round(2).tolist()
    chart_daily_return = bt["DailyReturn"].round(2).tolist()

    table_rows = ""
    for _, row in filtered.sort_values("Date", ascending=False).iterrows():
        table_rows += f"""
        <tr>
            <td>{row['Date'].strftime('%Y-%m-%d')}</td>
            <td>{round(row['Close'], 2)}</td>
            <td>{round(row['RSI'], 2)}</td>
            <td>{row['Mode']}</td>
        </tr>
        """

    selected_equal = "selected" if weight_mode == "equal" else ""
    selected_back = "selected" if weight_mode == "back_weighted" else ""

html = f"""
<html>
<head>
    <meta charset="utf-8">
    <title>QQQ RSI Mode</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        body {{
            font-family: Arial;
            background: #f5f7fa;
            padding: 40px;
        }}

        .card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
        }}

        .mode {{
            font-size: 32px;
            color: blue;
            font-weight: bold;
        }}
    </style>
</head>

<body>

<div class="card">
    <h1>QQQ 주간 RSI 모드</h1>

    <form method="get">
        시작일 <input type="date" name="start_date" value="{start_date}">
        종료일 <input type="date" name="end_date" value="{end_date}"><br><br>

        분할수 <input type="number" name="split_count" value="{split_count}">
        매도 RSI <input type="number" name="sell_rsi" value="{sell_rsi}"><br><br>

        극침체 <input type="number" name="geuk_chimche_strength" value="{geuk_chimche_strength}">
        침체 <input type="number" name="chimche_strength" value="{chimche_strength}">
        중립 <input type="number" name="jungrip_strength" value="{jungrip_strength}">
        상승 <input type="number" name="sangseung_strength" value="{sangseung_strength}"><br><br>

        분할 비중
        <select name="weight_mode">
            <option value="equal" {"selected" if weight_mode=="equal" else ""}>균등</option>
            <option value="back_weighted" {"selected" if weight_mode=="back_weighted" else ""}>뒤로 갈수록 크게</option>
        </select>

        <button type="submit">조회</button>
    </form>

    <hr>

    <p>기준일: {latest_date}</p>
    <p>QQQ 종가: ${latest_close}</p>
    <p>주간 RSI: {latest_rsi}</p>

    <div class="mode">현재 모드: {latest_mode}</div>
</div>

<div class="card">
    <h2>백테스트 결과</h2>

    <p>분할수: {split_count}</p>
    <p>매도 RSI: {sell_rsi}</p>
    <p>극침체: {geuk_chimche_strength}</p>
    <p>침체: {chimche_strength}</p>
    <p>중립: {jungrip_strength}</p>
    <p>상승: {sangseung_strength}</p>
    <p>분할 비중: {weight_mode}</p>

    <p>최종자산: {final_asset:,.0f}원</p>
    <p>수익금: {profit:,.0f}원</p>
    <p>수익률: {return_rate:.2f}%</p>
    <p>MDD: {mdd:.2f}%</p>
    <p>현금: {cash:,.0f}원</p>
    <p>주식가치: {stock_value:,.0f}원</p>
</div>

<div class="card">
    <h2>자산곡선</h2>
    <canvas id="assetChart"></canvas>
</div>

<div class="card">
    <h2>Drawdown</h2>
    <canvas id="ddChart"></canvas>
</div>

<div class="card">
    <h2>일별 수익률</h2>
    <canvas id="dailyChart"></canvas>
</div>

<script>
const labels = {chart_labels};
const assets = {chart_assets};
const drawdowns = {chart_drawdown};
const dailyReturns = {chart_daily_return};

// 자산곡선
new Chart(document.getElementById("assetChart"), {{
    type: "line",
    data: {{
        labels: labels,
        datasets: [{{
            label: "총자산",
            data: assets,
            borderWidth: 2,
            pointRadius: 0
        }}]
    }}
}});

// DD
new Chart(document.getElementById("ddChart"), {{
    type: "line",
    data: {{
        labels: labels,
        datasets: [{{
            label: "Drawdown (%)",
            data: drawdowns,
            borderWidth: 2,
            pointRadius: 0
        }}]
    }}
}});

// 일별 수익률
new Chart(document.getElementById("dailyChart"), {{
    type: "bar",
    data: {{
        labels: labels,
        datasets: [{{
            label: "일별 수익률 (%)",
            data: dailyReturns
        }}]
    }}
}});
</script>

</body>
</html>
"""

    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)