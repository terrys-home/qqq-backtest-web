# Step25D-7-4 — V2.2 Trade Event Log / 완료주기 집계 보정판

## 목적
Step25D-7-3에서 쿼터손절 체결 이벤트는 생성됐지만, 화면 집계에서 다음 문제가 남아 있었다.

1. 기간 필터가 `SellDate` 기준이라 BUY 이벤트가 화면 집계에서 제거됨
2. `쿼터LOC매수` 카운터와 금액이 0으로 보일 수 있음
3. 승률/거래수/평균보유일이 부분 SELL 이벤트 기준으로 계산되어 무한매수 주기 성과와 섞임
4. 수수료 집계가 BUY 이벤트와 SELL 이벤트의 `BuyAmount` 의미를 혼용할 수 있음

## 수정 내용

### 1. EventDate 기준 필터링
- `filter_trade_df_by_period()` 추가
- `EventDate`가 있으면 `EventDate` 기준으로 필터링
- 구버전 로그만 `SellDate` 기준 fallback

### 2. BUY/SELL 이벤트 보존
- `get_buy_trade_df()` 추가
- `get_trade_event_counts()` 추가
- Trade Event Log에서 체결 이벤트 수, BUY/SELL 이벤트 수를 별도 표시

### 3. 완료주기 기준 승률/보유일 계산
- `make_trade_summary()` 보정
- Event 로그 스타일에서는 부분매도 SELL 이벤트가 아니라 완료 주기 단위로 집계
- 대시보드 문구도 `승률/거래수`에서 `주기승률/완료주기수`로 변경

### 4. 수수료 집계 보정
- `FeeAmount`가 있으면 BUY/SELL 이벤트별 실제 수수료 합산
- 구버전 로그는 기존 방식 유지

## 기대 확인 포인트
- 쿼터LOC매수 카운터가 0이 아니라 실제 BUY 이벤트 기준으로 표시되는지
- 쿼터LOC매수금이 실제 매수금액으로 표시되는지
- Trade Event Log에 BUY 이벤트가 유지되는지
- 승률/보유일이 부분매도 이벤트가 아니라 완료 주기 기준으로 표시되는지

## 주의
- 이번 버전은 원문 공식 변경판이 아니라 로그/집계 보정판이다.
- 쿼터손절 체결 규칙 자체는 Step25D-7-3 기준을 유지한다.
