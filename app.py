from flask import Flask, request
import pandas as pd

app = Flask(__name__)

daily = pd.read_csv("QQQ_daily_with_mode.csv")
daily["Date"] = pd.to_datetime(daily["Date"])
daily = daily.sort_values("Date")

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
    else:
        return "침체"


def run_backtest(split_count=10, sell_rsi=70, buy_modes=["침체", "상승"]):
    initial_cash = 100_000_000
    cash = initial_cash
    shares = 0
    split_unit = initial_cash / split_count
    current_split = 0
    results = []

    for _, row in daily.iterrows():
        date = row["Date"]
        price = row["Close"]
        rsi = row["WeeklyRSI"]
        mode = make_mode(rsi, sell_rsi)

        action = "관망"
        buy_amount = 0
        sell_amount = 0
        buy_splits_today = 0

        prev_split = 0 if len(results) == 0 else results[-1]["CurrentSplit"]

        if mode == "과열" and shares > 0:
            sell_amount = shares * price
            cash += sell_amount
            shares = 0
            current_split = 0
            action = "전량매도"

        elif mode in buy_modes:
            target_split_today = min(prev_split + 1, split_count)
            buy_splits_today = max(target_split_today - current_split, 0)

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

    return result_df


@app.route("/")
def home():
    split_count = request.args.get("split_count", default=10, type=int)
    sell_rsi = request.args.get("sell_rsi", default=70, type=int)

    buy_modes = request.args.getlist("buy_modes")
    if not buy_modes:
        buy_modes = ["침체", "상승"]

    checked_chimche = "checked" if "침체" in buy_modes else ""
    checked_jungrip = "checked" if "중립" in buy_modes else ""
    checked_sangseung = "checked" if "상승" in buy_modes else ""

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
        buy_modes=buy_modes
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

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>QQQ RSI Mode</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f5f7fa;
                padding: 40px;
            }}
            .card {{
                background: white;
                padding: 24px;
                border-radius: 16px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                margin-bottom: 24px;
            }}
            .mode {{
                font-size: 36px;
                font-weight: bold;
                color: #2563eb;
            }}
            input, button {{
                padding: 10px;
                margin-right: 8px;
                margin-bottom: 10px;
            }}
            label {{
                margin-right: 10px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
            }}
            th, td {{
                padding: 12px;
                border-bottom: 1px solid #ddd;
                text-align: center;
            }}
            th {{
                background: #eef2ff;
            }}
        </style>
    </head>

    <body>
        <div class="card">
            <h1>QQQ 주간 RSI 모드</h1>

            <form method="get">
                <label>시작일</label>
                <input type="date" name="start_date" value="{start_date}" min="{min_date}" max="{max_date}">

                <label>종료일</label>
                <input type="date" name="end_date" value="{end_date}" min="{min_date}" max="{max_date}">

                <label>분할수</label>
                <input type="number" name="split_count" value="{split_count}" min="1" max="50">

                <label>매도 RSI</label>
                <input type="number" name="sell_rsi" value="{sell_rsi}" min="50" max="90">

                <br>

                <label>
                    <input type="checkbox" name="buy_modes" value="침체" {checked_chimche}>
                    침체 매수
                </label>

                <label>
                    <input type="checkbox" name="buy_modes" value="중립" {checked_jungrip}>
                    중립 매수
                </label>

                <label>
                    <input type="checkbox" name="buy_modes" value="상승" {checked_sangseung}>
                    상승 매수
                </label>

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
            <p>매수모드: {' + '.join(buy_modes)}</p>
            <p>최종자산: {final_asset:,.0f}원</p>
            <p>수익금: {profit:,.0f}원</p>
            <p>수익률: {return_rate:.2f}%</p>
            <p>MDD: {mdd:.2f}%</p>
            <p>현금: {cash:,.0f}원</p>
            <p>주식가치: {stock_value:,.0f}원</p>
            <p>현재 분할 상태: {current_split} / {split_count}</p>
        </div>

        <div class="card">
            <h2>자산곡선</h2>
            <canvas id="assetChart" height="100"></canvas>
        </div>

        <div class="card">
            <h2>선택 기간 모드 기록</h2>
            <table>
                <tr>
                    <th>날짜</th>
                    <th>종가</th>
                    <th>RSI</th>
                    <th>모드</th>
                </tr>
                {table_rows}
            </table>
        </div>

        <script>
            const labels = {chart_labels};
            const assets = {chart_assets};

            const ctx = document.getElementById('assetChart');

            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [{{
                        label: '총자산',
                        data: assets,
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.1
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        x: {{
                            ticks: {{
                                maxTicksLimit: 10
                            }}
                        }},
                        y: {{
                            ticks: {{
                                callback: function(value) {{
                                    return value.toLocaleString() + '원';
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """

    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)