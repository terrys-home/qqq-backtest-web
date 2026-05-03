# Step25D-7 - V2.2 쿼터손절모드 1차 구현/검증판

## 기준

- 사용자가 글로 정리해서 제공한 라오어 무한매수법 원문 기준만 사용한다.
- 사진 OCR/이미지 해석으로 추정한 내용은 기준으로 사용하지 않는다.
- V2.2와 V4.0은 분리한다.
- V2.2 기본형/수치변화는 나누지 않고 하나의 통합 전략으로 둔다.
- TQQQ/SOXL은 티커별 공식만 자동 적용한다.

## 이번 버전에서 구현한 것

### 1. V2.2 쿼터손절 발동

40분할 기준:

- `39 < T <= 40`
- 보유수량이 있고 일반모드일 때
- 최초 누적수량 1/4을 MOC 매도
- MOC는 해당일 종가 체결
- 이후 쿼터손절모드 진입

주의:

- 20/30분할의 쿼터손절 발동 조건은 사용자가 글로 확정한 원문 범위 밖이므로 자동 발동하지 않고 로그에 `원문 확인 필요` 취지로 남긴다.

### 2. 쿼터손절 재매수금

- 쿼터손절 시작 후 남은 현금 기준 `현금 / 10`
- 단, 기존 1회매수금보다 커지지 않도록 `min(기존1회매수금, 현금/10)`
- `QuarterUnitAmount`로 일별 로그에 표시

### 3. 티커별 쿼터손절 가격

TQQQ:

- LOC 매수/매도 기준: -10%
- 지정가 매도: +10%

SOXL:

- LOC 매수/매도 기준: -12%
- 지정가 매도: +12%

### 4. 쿼터손절 중 매도

- 누적수량 1/4: 쿼터 LOC 매도
- 나머지 3/4: 지정가 매도
- 쿼터 LOC 매도 성공 시 `후반전복귀` 처리
- `ModeTransitionReason`에 전환 사유 기록

### 5. 10회 소진 후 MOC

- 쿼터 LOC 매수 회차가 10회에 도달하면 누적수량 1/4 MOC 매도
- MOC 체결가가 쿼터 LOC 기준 안쪽이면 후반전모드 복귀
- 기준 밖이면 쿼터손절모드 반복
- 전환/반복 사유는 `ModeTransitionReason`에 기록

## 로그 보강

Trade Event Log에 추가/보강된 컬럼:

- `QuarterModeBefore`
- `QuarterModeAfter`
- `QuarterRoundBefore`
- `QuarterRoundAfter`
- `ModeTransitionReason`

Order Plan Log에 추가/보강된 컬럼:

- `QuarterRound`
- `QuarterUnitAmount`
- `ModeTransitionReason`

## 검증 결과

- `python -m py_compile app.py` 통과
- `python -m py_compile muhan_raor_v22_engine.py` 통과
- synthetic OHLC 데이터로 쿼터손절 시작, 쿼터 LOC 매수, 10회 후 MOC 반복 로그 생성 확인

## 아직 남은 것

- 실제 SOXL/TQQQ 장기 데이터에서 수익률/MDD 변화 확인
- 쿼터손절 탈출 조건의 원문 표현 중 “안쪽” 해석은 현재 일봉 기준 `MOC 체결가 >= 쿼터 LOC 기준가`로 구현함. 사용자가 원문상 더 정확한 판정식을 추가 제공하면 교체 필요
- V4.0 일반모드 재검증은 Step25E에서 진행
