# Infinite Lab Step24M - RAOR Original Engine

Step24L 기반 검증/최적화 준비판입니다.

## 핵심 변경

- Step24M 전략 추가
- 별LOC 매수 = 별지점 - 0.01 유지
- 별LOC 매도 = 별지점 유지
- 전량매도 지정가 % 직접 입력 유지
- 체결 검증 카운터 추가
  - 가격겹침 오류
  - 일봉 선후관계 불명
  - 전량매도 완료누락
  - 보유수량 0 로그
- 최근 Cycle별 마지막 상태 요약 추가
- Step24M 전용 Optimizer 조합 준비
  - 분할수: 20, 40
  - 첫매수 LOC 여유율: 10, 12, 15
  - 전량매도 지정가: 10, 12.5, 15, 17.5, 20, 22.5, 25

## Optimizer 실행 예시

```bash
python optimizer_lab.py TQQQ raor4_step24m 0.1
python optimizer_lab.py SOXL raor4_step24m 0.1
```

생성 파일:

```text
TQQQ_raor4_step24m_optimizer_top100.csv
SOXL_raor4_step24m_optimizer_top100.csv
```

## 주의

일봉 데이터는 장중 체결 순서를 알 수 없으므로 `DailyCandleOrderAmbiguous`는 오류가 아니라 검증 경고입니다.
`BuySellPriceOverlap`은 0건이어야 정상입니다.
