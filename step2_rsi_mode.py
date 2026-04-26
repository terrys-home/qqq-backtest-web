import pandas as pd

# 1. CSV 불러오기
df = pd.read_csv("QQQ_daily_data.csv")

# 2. 날짜 컬럼 datetime 변환
df['Date'] = pd.to_datetime(df['Date'])
df.set_index('Date', inplace=True)

# 3. 주봉 데이터로 변환 (금요일 기준)
weekly_df = df.resample('W-FRI').last()

# 4. 종가만 사용
close = weekly_df['Close']

# 5. RSI 계산 함수
def calculate_rsi(series, period=14):
    delta = series.diff()

    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    return rsi

# 6. RSI 계산
weekly_df['RSI'] = calculate_rsi(close)

# 7. 모드 생성 함수
def get_mode(rsi):
    if rsi >= 70:
        return "과열"
    elif rsi >= 50:
        return "상승"
    elif rsi >= 30:
        return "중립"
    else:
        return "침체"

# 8. 모드 컬럼 추가
weekly_df['Mode'] = weekly_df['RSI'].apply(get_mode)

# 9. 결과 확인
print(weekly_df[['Close', 'RSI', 'Mode']].tail(20))

# 10. 저장
weekly_df.to_csv("QQQ_weekly_mode.csv", encoding="utf-8-sig")

print("주간 RSI + 모드 생성 완료")