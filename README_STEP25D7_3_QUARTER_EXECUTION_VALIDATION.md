# Step25D-7-3 — V2.2 쿼터손절 체결/자산반영 검증판

## 기준

- 사용자 작성 `라오어 무한매수법 원문` 텍스트 기준을 우선한다.
- 사진 OCR/이전 zip 해석으로 새 공식을 추가하지 않는다.
- V2.2와 V4.0은 분리한다.
- 이번 버전은 수익률 개선판이 아니라, Step25D-7-2에서 발동된 쿼터손절이 실제로 현금/수량/원가/T에 반영되는지 확인하는 검증판이다.

## 주요 변경

### 1. Trade Event 검증 컬럼 추가

`muhan_raor_v22_engine.py`의 BUY/SELL 이벤트 로그에 다음 컬럼을 추가했다.

- `QuarterEventType`
  - `QUARTER_START_MOC`
  - `QUARTER_LOC_BUY`
  - `QUARTER_10TH_MOC`
  - `QUARTER_LOC_SELL`
  - `QUARTER_DESIGNATED_SELL`
- `CashBefore`, `CashAfter`, `CashDelta`, `CashDeltaExpected`, `CashDeltaDiff`
- `FeeAmount`
- `HoldingQtyBefore`, `HoldingQtyAfter`, `SharesDeltaActual`, `SharesDeltaExpected`, `SharesDeltaDiff`
- `CostBasisBefore`, `CostBasisAfter`, `CostBasisDelta`, `CostBasisDeltaActual`, `CostBasisDeltaDiff`
- `AssetBefore`, `AssetAfter`, `AssetDelta`, `MarketPriceForAsset`
- `CashValidationOK`, `SharesValidationOK`, `CostBasisValidationOK`

### 2. 쿼터손절 집계 보강

`app.py`의 주기 상세 분석과 Trade Event Log에 다음 항목을 추가했다.

- 쿼터LOC매수금
- 쿼터MOC매도금
- 현금검증 실패 건수
- 수량검증 실패 건수
- 쿼터 이벤트 타입
- 이벤트별 현금 전/후
- 이벤트별 현금/수량 검증 결과

### 3. 카운터 집계 방식 보강

기존 문자열 검색 중심에서 `QuarterEventType` 기준 집계를 우선 사용하도록 바꿨다.
문자열 표시가 조금 달라도 쿼터 LOC 매수/MOC/복귀 카운터가 누락되지 않도록 보강했다.

## 확인 포인트

화면에서 먼저 볼 것:

1. `쿼터LOC매수`가 0이 아닌지
2. `쿼터MOC`가 실제 매도 이벤트로 찍히는지
3. `쿼터LOC매수금`, `쿼터MOC매도금`이 0이 아닌지
4. `현금검증 실패`, `수량검증 실패`가 0건인지
5. Trade Event Log에서 쿼터 이벤트의 `현금전 → 현금후`가 실제로 변하는지
6. `QuarterEventType`이 쿼터 이벤트별로 제대로 찍히는지

## 아직 판단 금지

이번 버전에서 CAGR/MDD가 좋아졌는지보다 먼저, 쿼터손절의 회계 반영이 맞는지 확인해야 한다.
자산 결과 개선은 다음 단계에서 원문 기준과 비교하면서 판단한다.
