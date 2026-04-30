# Step24L - 라오어 무한매수4.0 원문엔진 체결검증 보강

## 핵심 수정

- Step24H에서 바로 Step24L로 확장했습니다.
- 별LOC 매수가는 `별지점 - 0.01`로 고정했습니다.
- 별LOC 매도가는 `별지점` 그대로 고정했습니다.
- 따라서 같은 별지점 기준에서 매수LOC와 매도LOC 가격이 겹치면 안 됩니다.
- `BuySellPriceOverlap` 컬럼을 추가했습니다. 정상이라면 `False`여야 합니다.
- 기존 `SameDayMultiSignal` 표현은 오해가 있어 제거하고 `DailyCandleOrderAmbiguous`로 변경했습니다.

## 로그 해석

- `BuyLOCPrice`: 별LOC 매수가, 별지점 - 0.01
- `SellLOCPrice`: 별LOC 매도가, 별지점 그대로
- `BuySellPriceOverlap`: 매수LOC 가격이 매도LOC 가격 이상인 오류 여부
- `DailyCandleOrderAmbiguous`: 가격 겹침이 아니라 일봉 OHLC만으로 장중 선후관계를 확정할 수 없는 구간
- `ExecutionPriorityNote`: 일봉 선후관계 불명 구간의 보수적 처리 설명

## 유지된 원문 구조

- 첫매수: 전날 종가 +10~15% LOC, 기본 12%
- 매수: 별LOC 매수는 별지점 - 0.01
- 매도: 보유수량 25%는 별지점 LOC 매도
- 매도: 보유수량 75%는 평단 대비 지정가 매도
- 지정가 기본: TQQQ 15%, SOXL 20%
- 지정가 %는 UI에서 커스텀 입력 가능

## 주의

- `DailyCandleOrderAmbiguous=True`는 가격 겹침 오류가 아닙니다.
- 일봉 데이터만으로 고가/저가/종가 발생 순서를 알 수 없다는 뜻입니다.
- 실제 자동주문/RPA에서는 매수예약과 매도예약을 매일 동시에 걸어두는 구조로 별도 처리해야 합니다.
