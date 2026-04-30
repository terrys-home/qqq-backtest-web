# Infinite Lab Step24D - RAOR Original Engine

Step24D는 Step24C 기반 보강판입니다.

## 변경점

1. 완료 주기 0 고정 문제 보정
   - 기존에는 trade_df의 CycleCompleted만 기준으로 완료 주기를 계산해 쿼터매도 로그만 누적되는 경우 완료 주기가 0으로 고정될 수 있었습니다.
   - Step24D는 bt의 CycleId 진행값을 함께 사용합니다.
   - 현재 미청산이 있으면 `max(CycleId)-1`까지 완료 주기로 계산합니다.
   - 현재 미청산이 없으면 `max(CycleId)`까지 완료 주기로 계산합니다.

2. 주기 상세 분석 추가
   - 완료 주기 수
   - 진행 중 주기
   - 평균/최장/최단 주기일수
   - 평균 주기수익률
   - 최대 소진 T
   - 후반전 진입 횟수
   - 소진모드 진입 횟수
   - 쿼터매도 횟수

3. 원문 규칙 검증 체크리스트 추가
   - 첫매수 LOC
   - T 증가 로그
   - 별% 공식
   - 전반전/후반전
   - 쿼터매도
   - 소진모드

4. 로그 컬럼 강화
   - OrderType
   - OrderPrice
   - OrderQty
   - CashBefore/CashAfter
   - HoldingQtyBefore/HoldingQtyAfter
   - AvgPriceBefore/AvgPriceAfter
   - QuarterSellQty

## 주의

- 원문에 없는 30분할 별% 공식은 추가하지 않았습니다.
- 후반전의 세부 사다리 수량표는 원문 확인 전까지 임의 확장하지 않았습니다.
- Step24A/B/C 파일은 유지하고 Step24D 파일을 새로 추가했습니다.


## Step24D Hotfix - 완료 주기 과소 계산 수정

- 기존 Step24D에서는 별% 매도점 도달 시 T 크기와 무관하게 항상 25% 쿼터매도만 실행했습니다.
- 이 경우 T가 1 이하까지 줄어도 포지션이 전량 청산되지 않아 한 주기가 비정상적으로 오래 유지되고, 완료 주기가 과소 집계될 수 있었습니다.
- 수정 후에는 T > 1이면 쿼터매도, T <= 1이면 잔여 수량 전량매도 후 CycleCompleted=True로 처리합니다.
