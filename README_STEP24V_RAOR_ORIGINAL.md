# Infinite Lab Step24V - RAOR Original Engine

## 목적
Step24V는 Step24U 매매 엔진을 그대로 유지하면서, Optimizer 결과를 실전 후보로 비교/선정하기 쉽게 만든 버전입니다.

## 유지 원칙
- 라오어 무한매수 4.0 원문 기준 매매공식은 변경하지 않습니다.
- 첫매수 LOC 여유율은 원문 가이드 범위인 10~15% 안에서만 탐색합니다.
- 20/40 외 분할은 원문 공식 미확인으로 탐색에서 제외합니다.
- 실전점수, 공백 페널티, 후보 판정은 매매공식이 아니라 후보 선택용 보조지표입니다.

## Step24V 추가 기능
1. `raor4_step24v` 전략 추가
2. 기본 전략을 Step24V로 변경
3. `muhan_raor_v4_step24v_engine.py` 추가
4. Step24V 전용 캐시 폴더 사용
   - `step24_cache/step24v/`
5. Optimizer 결과에서 대표 후보 자동 비교
   - 균형형 Score 1위
   - 수익률형 CAGR 1위
   - 방어형 MDD 1위
6. 후보별 비교 항목 추가
   - 분할수
   - 첫매수 LOC
   - 지정가 매도 %
   - CAGR
   - MDD
   - 완료주기
   - 최대 무체결 공백
   - 장기공백 횟수
   - 2022년 수익률
   - 실전점수
   - 판정
7. 웹화면 정리 후보 체크 카드 추가

## 정리 후보 판단
현재 웹사이트에서 바로 삭제하기보다 숨김/아카이브가 적절한 후보:
- V1~V5 / Step23 계열 드롭다운 항목
- Step24E~H 역사 버전
- Step20 추천 프리셋 카드
- Step18/19/20/21 연구 설명 카드
- 긴 매매로그 전체표는 최근 50개 기본 표시 + CSV 전체보기 구조 추천

삭제 금지:
- `app.py`
- `ticker_config.py`
- `optimizer_lab.py`
- 최신 Step24 엔진 파일
- 원본 CSV 데이터
- Step24N 이후 기준 백업

## 다음 후보 Step24W
- 실제 job_id 생성
- 서버 background job 상태 저장
- `/progress/<job_id>` polling
- 후보가 하나씩 표에 추가되는 진짜 실시간 진행률
- 중간 취소 버튼
