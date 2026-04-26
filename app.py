from flask import Flask, request
import pandas as pd

app = Flask(__name__)

@app.route("/")
def home():
    df = pd.read_csv("QQQ_weekly_mode.csv")

    bt = pd.read_csv("QQQ_split_backtest.csv")
    bt["Date"] = pd.to_datetime(bt["Date"])

    chart_labels = bt["Date"].dt.strftime("%Y-%m-%d").tolist()
    chart_assets = bt["TotalAsset"].round(0).tolist()

    final = bt.tail(1).iloc[0]

    final_asset = round(final["TotalAsset"])
    cash = round(final["Cash"])
    stock_value = round(final["StockValue"])
    current_split = final["CurrentSplit"]

    initial_cash = 100_000_000
    profit = final_asset - initial_cash
    return_rate = (final_asset / initial_cash - 1) * 100

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    min_date = df["Date"].min().strftime("%Y-%m-%d")
    max_date = df["Date"].max().strftime("%Y-%m-%d")

    if not start_date:
        start_date = df["Date"].tail(20).min().strftime("%Y-%m-%d")

    if not end_date:
        end_date = max_date

    filtered = df[
        (df["Date"] >= start_date) &
        (df["Date"] <= end_date)
    ]

    latest = filtered.tail(1).iloc[0]

    latest_date = latest["Date"].strftime("%Y-%m-%d")
    latest_close = round(latest["Close"], 2)
    latest_rsi = round(latest["RSI"], 2)
    latest_mode = latest["Mode"]

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
            }}
            button {{
                cursor: pointer;
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
            <p>최종자산: {final_asset:,.0f}원</p>
            <p>수익금: {profit:,.0f}원</p>
            <p>수익률: {return_rate:.2f}%</p>
            <p>현금: {cash:,.0f}원</p>
            <p>주식가치: {stock_value:,.0f}원</p>
            <p>현재 분할 상태: {current_split} / 7</p>
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
                    plugins: {{
                        legend: {{
                            display: true
                        }}
                    }},
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