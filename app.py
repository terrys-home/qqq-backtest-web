from flask import Flask, request
import pandas as pd

app = Flask(__name__)

INITIAL_CASH = 100_000_000

daily = pd.read_csv("QQQ_daily_with_mode.csv")
daily["Date"] = pd.to_datetime(daily["Date"])
daily = daily.sort_values("Date")

daily["MA5"] = daily["Close"].rolling(5).mean()
daily["MA20"] = daily["Close"].rolling(20).mean()
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


def add_metrics(result_df):
    result_df["Peak"] = result_df["TotalAsset"].cummax()
    result_df["Drawdown"] = (result_df["TotalAsset"] - result_df["Peak"]) / result_df["Peak"]
    result_df["DailyReturn"] = result_df["TotalAsset"].pct_change().fillna(0) * 100
    return result_df


def make_trade_summary(trade_df):
    if trade_df.empty:
        return {
            "trade_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate": 0,
        }

    trade_count = len(trade_df)
    win_count = len(trade_df[trade_df["Profit"] > 0])
    loss_count = len(trade_df[trade_df["Profit"] <= 0])
    win_rate = win_count / trade_count * 100 if trade_count > 0 else 0

    return {
        "trade_count": trade_count,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": win_rate,
    }


def run_rsi_engine(
    split_count=10,
    sell_rsi=70,
    geuk_chimche_strength=4,
    chimche_strength=3,
    jungrip_strength=1,
    sangseung_strength=1,
    weight_mode="equal"
):
    cash = INITIAL_CASH
    shares = 0
    current_split = 0
    split_unit = INITIAL_CASH / split_count

    invested_amount = 0
    first_buy_date = None
    trade_no = 0

    results = []
    trades = []

    strength_by_mode = {
        "극침체": geuk_chimche_strength,
        "침체": chimche_strength,
        "중립": jungrip_strength,
        "상승": sangseung_strength,
    }

    for _, row in daily.iterrows():
        date = row["Date"]
        price = row["Close"]
        rsi = row["WeeklyRSI"]
        mode = make_mode(rsi, sell_rsi)
        ma200 = row["MA200"]

        action = "관망"
        weight = 1.0

        if mode == "과열" and shares > 0:
            sell_amount = shares * price
            profit = sell_amount - invested_amount
            profit_rate = profit / invested_amount * 100 if invested_amount > 0 else 0
            trade_no += 1

            trades.append({
                "TradeNo": trade_no,
                "BuyDate": first_buy_date.strftime("%Y-%m-%d") if first_buy_date is not None else "",
                "SellDate": date.strftime("%Y-%m-%d"),
                "Strategy": "RSI 커스텀",
                "BuyAmount": round(invested_amount),
                "SellAmount": round(sell_amount),
                "Profit": round(profit),
                "ProfitRate": round(profit_rate, 2),
                "SellReason": "과열 RSI 전량매도",
                "Result": "수익매도" if profit > 0 else "손실매도",
            })

            cash += sell_amount
            shares = 0
            current_split = 0
            invested_amount = 0
            first_buy_date = None
            action = "과열 전량매도"

        elif mode in strength_by_mode:
            buy_strength = strength_by_mode[mode]

            if mode == "극침체":
                trend_multiplier = 1.0
            elif price > ma200:
                trend_multiplier = 1.0
            else:
                trend_multiplier = 0.0

            adjusted_strength = buy_strength * trend_multiplier

            if adjusted_strength > 0:
                target_split = min(current_split + adjusted_strength, split_count)
                buy_splits = max(target_split - current_split, 0)

                if buy_splits > 0:
                    if weight_mode == "back_weighted":
                        weight = 0.3 + (current_split / split_count) * 1.4

                    buy_amount = min(split_unit * buy_splits * weight, cash)

                    if buy_amount > 0:
                        buy_shares = buy_amount / price
                        shares += buy_shares
                        cash -= buy_amount
                        invested_amount += buy_amount
                        current_split += buy_splits

                        if first_buy_date is None:
                            first_buy_date = date

                        action = f"{buy_splits:.2f}분할 매수"

        stock_value = shares * price
        total_asset = cash + stock_value

        results.append({
            "Date": date,
            "Close": price,
            "Action": action,
            "CurrentSplit": current_split,
            "Cash": cash,
            "StockValue": stock_value,
            "TotalAsset": total_asset,
        })

    return add_metrics(pd.DataFrame(results)), pd.DataFrame(trades)


def run_backtest(
    split_count=10,
    sell_rsi=70,
    geuk_chimche_strength=4,
    chimche_strength=3,
    jungrip_strength=1,
    sangseung_strength=1,
    weight_mode="equal"
):
    bt, _ = run_rsi_engine(
        split_count=split_count,
        sell_rsi=sell_rsi,
        geuk_chimche_strength=geuk_chimche_strength,
        chimche_strength=chimche_strength,
        jungrip_strength=jungrip_strength,
        sangseung_strength=sangseung_strength,
        weight_mode=weight_mode
    )
    return bt


def run_original_engine(split_count=40, profit_target=0.10):
    cash = INITIAL_CASH
    shares = 0
    invested_amount = 0
    current_split = 0
    split_unit = INITIAL_CASH / split_count

    first_buy_date = None
    trade_no = 0

    results = []
    trades = []

    for _, row in daily.iterrows():
        date = row["Date"]
        price = row["Close"]

        action = "관망"

        avg_price = invested_amount / shares if shares > 0 else 0
        profit_rate_now = (price / avg_price - 1) if avg_price > 0 else 0

        if shares > 0 and profit_rate_now >= profit_target:
            sell_amount = shares * price
            profit = sell_amount - invested_amount
            profit_rate = profit / invested_amount * 100 if invested_amount > 0 else 0
            trade_no += 1

            trades.append({
                "TradeNo": trade_no,
                "BuyDate": first_buy_date.strftime("%Y-%m-%d") if first_buy_date is not None else "",
                "SellDate": date.strftime("%Y-%m-%d"),
                "Strategy": "오리지널",
                "BuyAmount": round(invested_amount),
                "SellAmount": round(sell_amount),
                "Profit": round(profit),
                "ProfitRate": round(profit_rate, 2),
                "SellReason": f"목표수익률 {profit_target * 100:.1f}% 도달",
                "Result": "수익매도" if profit > 0 else "손실매도",
            })

            cash += sell_amount
            shares = 0
            invested_amount = 0
            current_split = 0
            first_buy_date = None
            action = "목표수익 전량매도"

        elif current_split < split_count and cash > 0:
            buy_amount = min(split_unit, cash)
            buy_shares = buy_amount / price

            shares += buy_shares
            cash -= buy_amount
            invested_amount += buy_amount
            current_split += 1

            if first_buy_date is None:
                first_buy_date = date

            action = f"{current_split}차 매수"

        stock_value = shares * price
        total_asset = cash + stock_value

        results.append({
            "Date": date,
            "Close": price,
            "Action": action,
            "CurrentSplit": current_split,
            "Cash": cash,
            "StockValue": stock_value,
            "TotalAsset": total_asset,
        })

    return add_metrics(pd.DataFrame(results)), pd.DataFrame(trades)


def run_original_backtest(split_count=40, profit_target=0.10):
    bt, _ = run_original_engine(split_count=split_count, profit_target=profit_target)
    return bt


def run_original_upgrade_engine(
    split_count=30,
    profit_target=0.10,
    ma5_buy_split=3,
    ma20_buy_split=5
):
    cash = INITIAL_CASH
    shares = 0
    invested_amount = 0
    current_split = 0
    split_unit = INITIAL_CASH / split_count

    first_buy_date = None
    trade_no = 0

    results = []
    trades = []

    for _, row in daily.iterrows():
        date = row["Date"]
        price = row["Close"]
        ma5 = row["MA5"]
        ma20 = row["MA20"]

        action = "관망"

        avg_price = invested_amount / shares if shares > 0 else 0
        profit_rate_now = (price / avg_price - 1) if avg_price > 0 else 0

        if shares > 0 and profit_rate_now >= profit_target:
            sell_amount = shares * price
            profit = sell_amount - invested_amount
            profit_rate = profit / invested_amount * 100 if invested_amount > 0 else 0
            trade_no += 1

            trades.append({
                "TradeNo": trade_no,
                "BuyDate": first_buy_date.strftime("%Y-%m-%d") if first_buy_date is not None else "",
                "SellDate": date.strftime("%Y-%m-%d"),
                "Strategy": "오리지널 2.0",
                "BuyAmount": round(invested_amount),
                "SellAmount": round(sell_amount),
                "Profit": round(profit),
                "ProfitRate": round(profit_rate, 2),
                "SellReason": f"목표수익률 {profit_target * 100:.1f}% 도달",
                "Result": "수익매도" if profit > 0 else "손실매도",
            })

            cash += sell_amount
            shares = 0
            invested_amount = 0
            current_split = 0
            first_buy_date = None
            action = "목표수익 전량매도"

        elif current_split < split_count and cash > 0:
            buy_split = 1

            if pd.notna(ma20) and price < ma20:
                buy_split = ma20_buy_split
            elif pd.notna(ma5) and price < ma5:
                buy_split = ma5_buy_split

            actual_split = min(buy_split, split_count - current_split)
            buy_amount = min(split_unit * actual_split, cash)
            buy_shares = buy_amount / price

            shares += buy_shares
            cash -= buy_amount
            invested_amount += buy_amount
            current_split += actual_split

            if first_buy_date is None:
                first_buy_date = date

            action = f"{actual_split}분할 매수"

        stock_value = shares * price
        total_asset = cash + stock_value

        results.append({
            "Date": date,
            "Close": price,
            "Action": action,
            "CurrentSplit": current_split,
            "Cash": cash,
            "StockValue": stock_value,
            "TotalAsset": total_asset,
        })

    return add_metrics(pd.DataFrame(results)), pd.DataFrame(trades)


def run_original_upgrade_backtest(
    split_count=30,
    profit_target=0.10,
    ma5_buy_split=3,
    ma20_buy_split=5
):
    bt, _ = run_original_upgrade_engine(
        split_count=split_count,
        profit_target=profit_target,
        ma5_buy_split=ma5_buy_split,
        ma20_buy_split=ma20_buy_split
    )
    return bt


@app.route("/")
def home():
    strategy = request.args.get("strategy", default="rsi")
    action_mode = request.args.get("action_mode", default="backtest")

    start_date = request.args.get("start_date", default="2010-01-01")
    end_date = request.args.get("end_date", default=weekly["Date"].max().strftime("%Y-%m-%d"))

    split_count = request.args.get("split_count", default=10, type=int)
    sell_rsi = request.args.get("sell_rsi", default=70, type=int)

    geuk_chimche_strength = request.args.get("geuk_chimche_strength", default=4, type=int)
    chimche_strength = request.args.get("chimche_strength", default=3, type=int)
    jungrip_strength = request.args.get("jungrip_strength", default=1, type=int)
    sangseung_strength = request.args.get("sangseung_strength", default=1, type=int)
    weight_mode = request.args.get("weight_mode", default="equal")

    profit_target = request.args.get("profit_target", default=0.10, type=float)
    ma5_buy_split = request.args.get("ma5_buy_split", default=3, type=int)
    ma20_buy_split = request.args.get("ma20_buy_split", default=5, type=int)

    selected_rsi = "selected" if strategy == "rsi" else ""
    selected_original = "selected" if strategy == "original" else ""
    selected_original_upgrade = "selected" if strategy == "original_upgrade" else ""

    selected_equal = "selected" if weight_mode == "equal" else ""
    selected_back = "selected" if weight_mode == "back_weighted" else ""

    if strategy == "rsi":
        bt, trade_df = run_rsi_engine(
            split_count=split_count,
            sell_rsi=sell_rsi,
            geuk_chimche_strength=geuk_chimche_strength,
            chimche_strength=chimche_strength,
            jungrip_strength=jungrip_strength,
            sangseung_strength=sangseung_strength,
            weight_mode=weight_mode,
        )
        strategy_name = "RSI 커스텀"

        strategy_inputs = f"""
        분할수 <input type="number" name="split_count" value="{split_count}">
        매도 RSI <input type="number" name="sell_rsi" value="{sell_rsi}"><br><br>

        극침체 <input type="number" name="geuk_chimche_strength" value="{geuk_chimche_strength}">
        침체 <input type="number" name="chimche_strength" value="{chimche_strength}">
        중립 <input type="number" name="jungrip_strength" value="{jungrip_strength}">
        상승 <input type="number" name="sangseung_strength" value="{sangseung_strength}"><br><br>

        분할 비중
        <select name="weight_mode">
            <option value="equal" {selected_equal}>균등</option>
            <option value="back_weighted" {selected_back}>뒤로 갈수록 크게</option>
        </select><br><br>
        """

    elif strategy == "original":
        bt, trade_df = run_original_engine(
            split_count=split_count,
            profit_target=profit_target,
        )
        strategy_name = "오리지널"

        strategy_inputs = f"""
        분할수 <input type="number" name="split_count" value="{split_count}">
        목표수익률 <input type="number" step="0.01" name="profit_target" value="{profit_target}"><br><br>
        """

    else:
        bt, trade_df = run_original_upgrade_engine(
            split_count=split_count,
            profit_target=profit_target,
            ma5_buy_split=ma5_buy_split,
            ma20_buy_split=ma20_buy_split,
        )
        strategy_name = "오리지널 2.0"

        strategy_inputs = f"""
        분할수 <input type="number" name="split_count" value="{split_count}">
        목표수익률 <input type="number" step="0.01" name="profit_target" value="{profit_target}"><br><br>

        MA5 매수배수 <input type="number" name="ma5_buy_split" value="{ma5_buy_split}">
        MA20 매수배수 <input type="number" name="ma20_buy_split" value="{ma20_buy_split}"><br><br>
        """

    bt = bt[(bt["Date"] >= start_date) & (bt["Date"] <= end_date)].copy()

    latest = weekly.tail(1).iloc[0]
    latest_date = latest["Date"].strftime("%Y-%m-%d")
    latest_close = round(latest["Close"], 2)
    latest_rsi = round(latest["RSI"], 2)
    latest_mode = make_mode(latest_rsi, sell_rsi)

    final = bt.tail(1).iloc[0]

    final_asset = round(final["TotalAsset"])
    profit = final_asset - INITIAL_CASH
    return_rate = (final_asset / INITIAL_CASH - 1) * 100
    cash = round(final["Cash"])
    stock_value = round(final["StockValue"])
    current_split = final["CurrentSplit"]
    mdd = bt["Drawdown"].min() * 100

    trade_summary = make_trade_summary(trade_df)
    trade_count = trade_summary["trade_count"]
    win_count = trade_summary["win_count"]
    loss_count = trade_summary["loss_count"]
    win_rate = trade_summary["win_rate"]

    chart_labels = bt["Date"].dt.strftime("%Y-%m-%d").tolist()
    chart_assets = bt["TotalAsset"].round(0).tolist()
    chart_drawdown = (bt["Drawdown"] * 100).round(2).tolist()

    monthly = bt.copy()
    monthly["Month"] = monthly["Date"].dt.to_period("M")
    monthly_return = monthly.groupby("Month")["DailyReturn"].sum().reset_index()
    chart_month_labels = monthly_return["Month"].astype(str).tolist()
    chart_month_return = monthly_return["DailyReturn"].round(2).tolist()

    deepmine_html = ""
    if action_mode == "deepmine":
        if strategy == "rsi":
            top10 = pd.read_csv("QQQ_ultra_score_top10.csv")
        elif strategy == "original":
            top10 = pd.read_csv("QQQ_original_score_top10.csv")
        else:
            top10 = pd.read_csv("QQQ_original_return_top10.csv")

        table_rows = ""

        for _, row in top10.head(10).iterrows():
            row_html = "<tr>"

            for val in row:
                row_html += f"<td>{val}</td>"

            if strategy == "rsi":
                apply_button = f"""
                <form method="get">
                    <input type="hidden" name="strategy" value="rsi">
                    <input type="hidden" name="action_mode" value="backtest">
                    <input type="hidden" name="start_date" value="{start_date}">
                    <input type="hidden" name="end_date" value="{end_date}">
                    <input type="hidden" name="split_count" value="{row['split']}">
                    <input type="hidden" name="sell_rsi" value="{row['sell_rsi']}">
                    <input type="hidden" name="geuk_chimche_strength" value="{row['geuk']}">
                    <input type="hidden" name="chimche_strength" value="{row['chim']}">
                    <input type="hidden" name="jungrip_strength" value="{row['jung']}">
                    <input type="hidden" name="sangseung_strength" value="{row['sang']}">
                    <input type="hidden" name="weight_mode" value="{row['weight']}">
                    <button type="submit">적용</button>
                </form>
                """
            else:
                target_strategy = "original" if strategy == "original" else "original_upgrade"
                apply_button = f"""
                <form method="get">
                    <input type="hidden" name="strategy" value="{target_strategy}">
                    <input type="hidden" name="action_mode" value="backtest">
                    <input type="hidden" name="start_date" value="{start_date}">
                    <input type="hidden" name="end_date" value="{end_date}">
                    <input type="hidden" name="split_count" value="{row['split_count']}">
                    <input type="hidden" name="profit_target" value="{row['profit_target']}">
                    <input type="hidden" name="ma5_buy_split" value="{row.get('ma5_buy_split', 3)}">
                    <input type="hidden" name="ma20_buy_split" value="{row.get('ma20_buy_split', 5)}">
                    <button type="submit">적용</button>
                </form>
                """

            row_html += f"<td>{apply_button}</td>"
            row_html += "</tr>"
            table_rows += row_html

        headers = "".join([f"<th>{col}</th>" for col in top10.columns])
        headers += "<th>적용</th>"

        deepmine_html = f"""
        <div class="card">
            <h2>딥마이닝 TOP10</h2>
            <p>전략: {strategy_name}</p>

            <table border="1" cellpadding="6" cellspacing="0">
                <tr>{headers}</tr>
                {table_rows}
            </table>
        </div>
        """

    trade_rows = ""
    for _, row in trade_df.tail(20).sort_values("TradeNo", ascending=False).iterrows():
        trade_rows += f"""
        <tr>
            <td>{row['TradeNo']}</td>
            <td>{row['BuyDate']}</td>
            <td>{row['SellDate']}</td>
            <td>{row['BuyAmount']:,.0f}</td>
            <td>{row['SellAmount']:,.0f}</td>
            <td>{row['Profit']:,.0f}</td>
            <td>{row['ProfitRate']:.2f}%</td>
            <td>{row['SellReason']}</td>
            <td>{row['Result']}</td>
        </tr>
        """

    trade_log_html = f"""
    <div class="card">
        <h2>매매로그 / 승률</h2>
        <p>총 매도완료 거래수: {trade_count}</p>
        <p>수익매도: {win_count}</p>
        <p>손실매도: {loss_count}</p>
        <p>승률: {win_rate:.2f}%</p>

        <table border="1" cellpadding="6" cellspacing="0">
            <tr>
                <th>번호</th>
                <th>매수시작일</th>
                <th>매도일</th>
                <th>매수금액</th>
                <th>매도금액</th>
                <th>손익</th>
                <th>수익률</th>
                <th>매도사유</th>
                <th>결과</th>
            </tr>
            {trade_rows}
        </table>
    </div>
    """

    html = f"""
<html>
<head>
    <meta charset="utf-8">
    <title>QQQ Strategy Lab</title>
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
        input, select, button {{
            padding: 6px;
            margin: 4px;
        }}
        button {{
            cursor: pointer;
        }}
        table {{
            border-collapse: collapse;
            background: white;
        }}
        th {{
            background: #f0f0f0;
        }}
    </style>
</head>

<body>

<div class="card">
    <h1>QQQ 전략 실험실</h1>

    <form method="get">
        시작일 <input type="date" name="start_date" value="{start_date}">
        종료일 <input type="date" name="end_date" value="{end_date}"><br><br>

        전략 선택
        <select name="strategy">
            <option value="rsi" {"selected" if strategy == "rsi" else ""}>RSI 커스텀</option>
            <option value="original" {"selected" if strategy == "original" else ""}>오리지널</option>
            <option value="original_upgrade" {"selected" if strategy == "original_upgrade" else ""}>오리지널 2.0</option>
        </select><br><br>

        {strategy_inputs}

        <button type="submit" name="action_mode" value="backtest">백테스트</button>
        <button type="submit" name="action_mode" value="deepmine">딥마이닝 TOP10</button>
    </form>

    <hr>

    <p>기준일: {latest_date}</p>
    <p>QQQ 종가: ${latest_close}</p>
    <p>주간 RSI: {latest_rsi}</p>
    <div class="mode">현재 모드: {latest_mode}</div>
</div>

<div class="card">
    <h2>백테스트 결과</h2>
    <p>전략: {strategy_name}</p>
    <p>분할수: {split_count}</p>
    <p>최종자산: {final_asset:,.0f}원</p>
    <p>수익금: {profit:,.0f}원</p>
    <p>수익률: {return_rate:.2f}%</p>
    <p>MDD: {mdd:.2f}%</p>
    <p>현금: {cash:,.0f}원</p>
    <p>주식가치: {stock_value:,.0f}원</p>
    <p>현재 분할 상태: {current_split} / {split_count}</p>
</div>

{deepmine_html}

{trade_log_html}

<div class="card">
    <h2>자산곡선</h2>
    <canvas id="assetChart"></canvas>
</div>

<div class="card">
    <h2>Drawdown</h2>
    <canvas id="ddChart"></canvas>
</div>

<div class="card">
    <h2>월별 수익률</h2>
    <canvas id="monthlyChart"></canvas>
</div>

<script>
const labels = {chart_labels};
const assets = {chart_assets};
const drawdowns = {chart_drawdown};
const monthLabels = {chart_month_labels};
const monthReturns = {chart_month_return};

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

new Chart(document.getElementById("monthlyChart"), {{
    type: "bar",
    data: {{
        labels: monthLabels,
        datasets: [{{
            label: "월별 수익률 (%)",
            data: monthReturns
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