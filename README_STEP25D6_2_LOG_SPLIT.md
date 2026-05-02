# Sunny's Test - Step25D-6-2 V2.2 Log Split Fix

기준 파일: Infinite_Lab_Step25D6_RAOR_Original_Engine_v22_log_fix.zip

## 목적
Step25D-6에서 매매로그가 `BuyDate=주기 시작일`, `SellDate=부분매도일` 구조로 섞이면서 2021년 주기가 2025/2026년으로 점프하는 것처럼 보이는 문제를 줄이기 위한 로그 표시/집계 보정판입니다.

## 변경 원칙
- V2.2 가격 공식/체결 공식은 변경하지 않았습니다.
- 쿼터손절모드 공식 검증/완성 구현은 Step25D-7 대상으로 남겨두었습니다.
- 이번 버전은 로그 구조와 UI 표시만 보정합니다.

## 변경 파일
- `muhan_raor_v22_engine.py`
  - BUY 체결 이벤트도 `trade_df`에 기록
  - SELL 체결 이벤트에 `EventDate`, `SellEventDate`, `LastActionDate` 추가
  - `CycleStartDate`, `BuyEventDate`, `SellEventDate`, `LastBuyDate`, `CycleEndDate` 분리
  - `EventSide=BUY/SELL`, `LogType=TradeEvent` 추가

- `app.py`
  - 성과 집계/승률/완료손익 계산은 SELL 이벤트만 사용하도록 `get_sell_trade_df()` 추가
  - Trade Event Log UI를 이벤트 단위로 표시
  - Order Plan Log UI 추가
  - Cycle Summary는 SELL 이벤트 기준으로 손익 집계

## 로그 해석
- `CycleStartDate`: 해당 무한매수 주기 시작일
- `EventDate`: 실제 BUY/SELL 체결 이벤트가 발생한 날
- `BuyEventDate`: 매수 체결 이벤트일
- `SellEventDate`: 매도 체결 이벤트일
- `LastBuyDate`: 해당 주기 안에서 가장 최근 매수일
- `CycleEndDate`: 전량 매도로 주기가 종료된 날

## 검증
- `python -m py_compile app.py`
- `python -m py_compile muhan_raor_v22_engine.py`
- `muhan_raor_v22_engine.py` 단독 synthetic dataframe 테스트 완료

주의: 현재 실행 환경에는 Flask가 설치되어 있지 않아 `import app` 실행 테스트는 하지 못했습니다. 문법 컴파일 검증은 완료했습니다.
