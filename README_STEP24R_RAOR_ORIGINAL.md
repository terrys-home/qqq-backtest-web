# Infinite Lab Step24R - RAOR Original Engine UI Redesign

## 기준
- Step24R은 Step24Q 매매 엔진을 그대로 사용합니다.
- 라오어 무한매수4.0 원문 기준 매매 공식은 변경하지 않았습니다.
- 이번 버전은 UI 리디자인과 실시간 진행률 준비 구조 중심입니다.

## 추가 내용
1. 전략 선택 기본값: `raor4_step24r`
2. Step24R 전용 엔진 파일 추가: `muhan_raor_v4_step24r_engine.py`
3. Step24R 캐시 폴더 분리: `step24_cache/step24r/`
4. SEED 스타일 참고 UI 적용
   - 좌측 사이드바
   - 상단 요약바
   - 카드형 지표 정리
   - Optimizer/DeepMining 앵커 메뉴
5. 실시간 진행률 준비판
   - 클릭 즉시 진행 오버레이
   - 예상 조합수 / 캐시 재사용 안내
   - 24S에서 job_id + polling 방식으로 확장 가능하도록 프론트 구조 유지

## 보존 버전
- Step24E/F/G/H/L/M/N/O/P/Q 보존
- Step24A~D는 되살리지 않음

## 주의
- 현재 Step24R의 진행률은 24Q처럼 브라우저 대기형 오버레이입니다.
- 진짜 실시간 조합별 진행률은 24S에서 Flask job_id/polling 구조로 분리하는 것을 권장합니다.
