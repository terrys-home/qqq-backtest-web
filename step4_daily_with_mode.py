import pandas as pd

# 1. 일봉 데이터 불러오기
daily = pd.read_csv("QQQ_daily_data.csv")
daily["Date"] = pd.to_datetime(daily["Date"])
daily = daily.sort_values("Date")

# 2. 주봉 모드 데이터 불러오기
weekly = pd.read_csv("QQQ_weekly_mode.csv")
weekly["Date"] = pd.to_datetime(weekly["Date"])
weekly = weekly.sort_values("Date")

# 3. 필요한 컬럼만 사용
weekly_mode = weekly[["Date", "RSI", "Mode"]].copy()
weekly_mode = weekly_mode.rename(columns={
    "Date": "WeekDate",
    "RSI": "WeeklyRSI",
    "Mode": "WeeklyMode"
})

# 4. 일봉 날짜에 가장 최근 주간 모드 붙이기
daily_with_mode = pd.merge_asof(
    daily,
    weekly_mode,
    left_on="Date",
    right_on="WeekDate",
    direction="backward"
)

# 5. 아직 RSI가 없는 초기 구간 제거
daily_with_mode = daily_with_mode.dropna(subset=["WeeklyRSI", "WeeklyMode"])

# 6. 저장
daily_with_mode.to_csv("QQQ_daily_with_mode.csv", index=False, encoding="utf-8-sig")

# 7. 확인 출력
print(daily_with_mode[["Date", "Close", "WeeklyRSI", "WeeklyMode"]].tail(30))
print("일봉 + 주간 모드 결합 완료: QQQ_daily_with_mode.csv")