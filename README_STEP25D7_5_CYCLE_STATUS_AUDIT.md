# Step25D-7-5 — V2.2 CycleStatus / 종료사유 / 미청산 검증판

## 목적
Step25D-7-4에서 BUY/SELL 이벤트 집계와 쿼터손절 체결 카운터는 보정되었지만, 1000일 이상 지속되는 장기 주기가 실제 장기 보유인지, 종료 판정/화면 집계 오류인지 구분하기 어려웠다.

이번 버전은 V2.2 공식과 체결 규칙은 바꾸지 않고 다음 검증 컬럼과 화면을 추가한다.

## 추가 내용

### 1. Trade Event Log 보강
- CycleStatus
- CycleEndReason
- OpenQtyAfter
- OpenMarketValueAfter

### 2. bt 일별 로그 보강
- CycleStatus
- CycleEndReason
- OpenQty
- OpenMarketValue

### 3. 화면 추가
`검증/매매 로그` 탭에 다음 섹션을 추가했다.

- Step25D-7-5 CycleStatus / 종료사유 / 미청산 검증
- COMPLETED / OPEN / REVIEW 카운터
- 1000일 이상 주기 카운터
- 현재 미청산 수량
- 현재 미청산 평가액
- 주기별 상태표

## 판정 기준

- COMPLETED: `CycleCompleted=True`인 SELL 이벤트가 있는 주기
- OPEN: 백테스트 마지막 날 실제 보유수량이 남아 있는 현재 주기
- REVIEW: 이벤트는 있으나 완료/진행 상태를 확정할 수 없는 주기

## 주의
- 1000일 이상 주기는 오류 확정이 아니라 장기 주기 검토 표시다.
- 수익률 개선 목적이 아니라 주기 종료/미청산/장기보유 상태 검증 목적이다.
- V2.2 원문 공식, 쿼터손절 체결 조건, 수수료 계산은 Step25D-7-4와 동일하게 유지했다.
