# Step25D-6 - V2.2 매매로그 날짜 보정 / 쿼터손절 검증판

Step25D-5의 V2.2 매매로그에서 한 주기가 2021년에 시작했는데 매수일이 2025/2026으로 보이는 현상을 보정했습니다.
이는 실제 주기가 점프한 것이 아니라, 하나의 V2.2 주기 안에서 추가 매수가 계속 발생하고 부분매도가 여러 번 발생하는데 로그의 BuyDate에 마지막 매수일을 넣어 생긴 표시 혼동입니다.

- BuyDate는 CycleStartDate와 동일하게 주기 시작일 기준으로 고정
- 실제 마지막 매수일은 LastBuyDate 컬럼으로 별도 보관
- HoldDays는 CycleStartDate부터 SellDate까지 계산
- LastBuyHoldDays는 마지막 매수일부터 SellDate까지 계산
- V2.2 공식은 변경 없음
