# Infinite Lab Step23D V4 Audit

이번 버전은 Step23A/B/C V4에 **검증 컬럼**을 추가한 버전입니다.

## 핵심 변경
- `app.py`: V4 엔진 래퍼 추가
  - `muhan_v4_engine.run_infinite4_v4_core()`가 요구하는 `daily_df`를 자동 주입
  - Optimizer에서도 같은 함수 호출 가능
- `muhan_v4_engine.py`: 과대수익/분할 계산 검증용 컬럼 추가

## 추가된 주요 컬럼
- `TAmount`: 1T 금액
- `PositionPrincipal`: 현재 보유원금
- `EntryAmountWithFee`: 현재 포지션 투입금(수수료 포함)
- `PrincipalAfterSell`: 쿼터매도 후 남은 투입금
- `LastBuyUnits`, `LastBuyAmount`, `LastBuyQty`
- `LastSellFraction`, `LastSellQty`, `LastSellAmount`, `LastCostBasisSold`
- `CumulativeBuyAmount`, `CumulativeSellAmount`, `CumulativeFee`
- `RealizedProfit`, `MaxCashUsed`, `ExposurePct`
- `AuditFlag`: `정상`, `NEGATIVE_CASH`, `SPLIT_OVER` 등

## 적용 방법
기존 프로젝트 루트(`qqq-backtest-web`)에 아래 5개 파일만 덮어쓰기/추가하세요.

- `app.py`
- `optimizer_lab.py`
- `ticker_config.py`
- `muhan_v4_engine.py`
- `README_STEP23D_V4_AUDIT.md`

`templates`, `static` 폴더는 건드리지 않습니다.
