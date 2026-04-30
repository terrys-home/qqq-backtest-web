# Infinite Lab Step23A/B/C V4 Upgrade

네가 보내준 기존 작업 흐름을 유지한 상태에서 Step23A/B/C를 추가한 업그레이드 묶음입니다.

## 포함 파일
- app.py
- optimizer_lab.py
- ticker_config.py
- muhan_v4_engine.py

## 핵심
- Step23A: 언이시트 LOC / 큰수 / 매도가 입력값 우선, 없으면 동적 별지점 자동 계산
- Step23B: 전반전 / 후반전 / 소진모드와 쿼터매도 세분화
- Step23C: max_gap_pct 기반 LOC 괴리 제한 강화

## 적용
1. 기존 프로젝트 폴더를 먼저 통째로 복사해서 백업
2. 이 압축의 4개 파일만 프로젝트 루트에 복사
3. 같은 이름 파일은 덮어쓰기
4. 실행: python app.py
5. Optimizer: python optimizer_lab.py TQQQ infinite4_v4

자동주문/RPA는 포함하지 않았습니다.
