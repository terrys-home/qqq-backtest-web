# Infinite Lab Step24P - RAOR Original Engine

## 기준
- Step24P는 Step24O 엔진을 기준으로 확장한 화면/최적화 구조 버전입니다.
- 매매 공식 자체는 `muhan_raor_v4_step24o_engine.py`를 그대로 사용합니다.
- 원문에 없는 공식/규칙은 추가하지 않았습니다.

## Step24P 추가 내용
1. Step24P 전략 추가: `raor4_step24p`
2. 기본 티커를 TQQQ로 변경
3. Step24 전략에서 QQQ 등 미지원 티커가 들어오면 TQQQ로 자동 보정
4. 파라미터 세분화 입력
   - 탐색 분할수: 20,40
   - 첫매수 LOC 최소/최대/간격
   - 지정가 매도 최소/최대/간격
   - 표시 개수
   - 점수 기준: 균형형 / 수익률 우선 / MDD 방어 우선 / 회전율 우선
5. DeepMining/Optimizer 결과에 진행형 UI 컬럼 추가
   - 검증순서
   - 진행률
   - 판정: 강력 후보 / 유효 후보 / 방어 후보 / 회전 부족 / 관찰
6. 결과 CSV 캐시 저장 구조 추가
   - `step24_cache/` 폴더에 조건별 CSV 저장
   - 같은 조건이면 캐시 재사용
7. TOP 후보의 `적용` 링크 추가
   - 클릭하면 해당 분할수/첫매수LOC/지정가%가 현재 백테스트 설정에 반영됨

## Step24Q로 이어갈 후보
- 실시간 진행률 API 또는 SSE/WebSocket
- 계산 중 오버레이
- 현재 몇 번째 조합 계산 중인지 브라우저 표시
- 캐시 CSV 다운로드 버튼
- TOP1 값 JS 즉시 적용
- 조건별 캐시 관리 화면

## 보존 기준 버전
- Step24N / Step24M / Step24L / Step24H / Step24G / Step24F / Step24E 보존
- Step24A~D는 되살리지 않음
