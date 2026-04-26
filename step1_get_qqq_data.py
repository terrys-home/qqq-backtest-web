import yfinance as yf

ticker = "QQQ"

df = yf.download(ticker, period="max", interval="1d")

# 컬럼이 여러 줄로 생기는 문제 방지
if isinstance(df.columns, type(df.columns)) and hasattr(df.columns, "levels"):
    df.columns = df.columns.get_level_values(0)

df = df.reset_index()

df.to_csv("QQQ_daily_data.csv", index=False, encoding="utf-8-sig")

print(df.head())
print(df.tail())
print("QQQ 데이터 저장 완료: QQQ_daily_data.csv")