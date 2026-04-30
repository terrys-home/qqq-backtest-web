# Step24H - 라오어 무한매수4.0 원문엔진 체결 검증판

## 기준
- Step24G 기반입니다.
- 매일 매도예약 구조는 유지합니다.
  - 보유수량 25%: 별지점 LOC 매도
  - 보유수량 75%: 평단 대비 지정가 매도
- 전량매도 지정가 수익률은 사용자가 직접 입력합니다.

## Step24H 추가
- 같은 날 지정가매도 / 별LOC매도 / LOC매수 신호가 겹치는 경우 `SameDayMultiSignal=True`로 표시합니다.
- 일봉 데이터는 장중 선후관계를 알 수 없으므로, 동시신호 구간은 원문 체결 흐름 검증 대상으로 봅니다.
- 결과 로그에 다음 컬럼을 추가했습니다.
  - DesignatedSellPct
  - DesignatedSellSignal
  - SellLOCSignal
  - BuyLOCSignal
  - DesignatedSellExecuted
  - SellLOCExecuted
  - BuyLOCExecuted
  - SameDayMultiSignal
  - ExecutionPriorityNote

## 딥마이닝/옵티마이저 버튼
- 라오어 Step24 계열은 기존 RSI/오리지널 최적화 CSV와 섞이지 않도록 막았습니다.
- Step24H 전용 CSV가 없으면 안내문만 표시합니다.
