# Step24B 라오어 무한매수4.0 원문기반 확장 엔진

이번 버전은 `Step24A`를 덮어쓴 것이 아니라, 별도 엔진 파일을 추가한 확장본입니다.

## 추가/수정 파일

- `muhan_raor_v4_step24b_engine.py` 신규 추가
- `app.py`에 Step24B 전략 선택/래퍼 추가
- `ticker_config.py`에 Step24B 전략 라벨/프리셋 추가
- `optimizer_lab.py`에 Step24B 최적화 진입점 추가

## 전략 선택명

웹 화면 전략 선택에서 아래 항목을 선택하세요.

```text
라오어 무한매수4.0 원문엔진 / Step24B
```

CLI 최적화:

```bash
python optimizer_lab.py TQQQ raor4_step24b
python optimizer_lab.py SOXL raor4_step24b
```

## Step24A 유지 규칙

- 시작 전 보유수량 0이면 `T=0`
- 첫매수는 `1회매수금`으로 전날종가보다 일반적으로 `10~15%` 큰 값으로 LOC 시도
- 기본 첫매수 LOC 여유율은 `12%`
- 일일매수시도액 = `잔금 / (분할수 - T)`
- TQQQ/SOXL 20/40분할 별% 공식만 사용
- 별%가격 = `평단 × (1 + 별%/100)`
- 매수점 = `별%가격 - 0.01`
- 매도점 = `별%가격`
- 전반전 매수 = 별지점/큰수 LOC 0.5T + 평단 LOC 0.5T
- 쿼터매도 = 보유수량 25% 매도 후 `T = 기존 T × 0.75`
- 지정가매도 기준 = TQQQ +15%, SOXL +20%

## Step24B 추가 반영

- `후반전`과 `소진모드`를 엔진 내부에서 명시적으로 분리
- 소진모드 조건을 `남은 T < 1` 기준으로 처리
- 후반전 매수는 별지점 LOC 기준, 1일 최대 1T 한도로 처리
- 소진모드 매수는 남은 T와 잔금 범위 안에서만 별지점 LOC 시도
- 쿼터매도는 별% 매도점 LOC 체결 조건으로 처리
- 후반전/소진모드에서는 LOC 쿼터매도와 지정가매도 후보를 분리 계산
- T 추적 로그 강화:
  - `PhaseBefore`
  - `PhaseAfter`
  - `TBefore`
  - `TAfter`
  - `TDelta`
  - `RemainingTBefore`
  - `RemainingTAfter`
  - `DailyAttemptBefore`
  - `OrderPlan`
  - `RaorDebug`

## 의도적으로 임의 구현하지 않은 부분

- 30분할 별% 공식은 원문 이미지에 명시된 공식이 없으므로 넣지 않았습니다.
- TQQQ/SOXL 외 티커는 원문 공식이 없으므로 지원하지 않습니다.
- 후반전의 세부 다중 사다리 수량표가 원문에 따로 있다면, 현재 버전은 임의 추정하지 않고 1일 1T 한도로 막아두었습니다.

## 실행

```bash
python app.py
```

브라우저:

```text
http://127.0.0.1:5000
```
