# Infinite Lab Step23E / V5 업그레이드

## 목적
- V4의 `기본 별점(%)` 고정형 구조를 `초기 별점(%)` 기반 동적 구조로 개선했습니다.
- 화면에서 입력한 별점은 고정값이 아니라 시작 기준값입니다.
- 실제 별지점은 전반전/후반전/소진모드, 분할진행률, 평균단가 대비 현재가 위치에 따라 자동 가변됩니다.

## 포함 파일
- app.py
- optimizer_lab.py
- ticker_config.py
- muhan_v5_engine.py
- README_STEP23E_V5.md

## 적용 방법
압축을 풀면 `infinite_lab` 폴더가 있습니다. 폴더 자체를 넣지 말고, 안의 파일만 기존 `qqq-backtest-web` 루트에 복사하세요.

대상 위치 예:
```text
qqq-backtest-web/
 ┣ app.py
 ┣ optimizer_lab.py
 ┣ ticker_config.py
 ┣ muhan_v5_engine.py
 ┗ README_STEP23E_V5.md
```

## 실행
```bash
python app.py
```
브라우저:
```text
http://127.0.0.1:5000
```

## Optimizer
```bash
python optimizer_lab.py TQQQ infinite4_v5
python optimizer_lab.py SOXL infinite4_v5
```

## V5 핵심 변경
- 전략 선택 메뉴에 `무한매수 4.0 V5 / Step23E 동적별지점` 추가
- `기본 별점(%)` 문구를 `초기 별점(%)` 개념으로 변경
- 결과 데이터에 DynamicLayer / ProgressRate / DynamicFactor 추가
- 언이시트 LOC / 큰수 / 매도가 입력값은 계속 우선 적용
- 수동값이 없으면 동적 별점 레이어로 다음 LOC와 큰수 후보 산출

## 주의
- 자동주문/RPA 기능은 포함하지 않았습니다.
- 기존 V4 파일은 남겨둬도 되지만, V5 실행에는 `muhan_v5_engine.py`가 루트에 있어야 합니다.
