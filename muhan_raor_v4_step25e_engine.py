"""
Step25E - 라오어 무한매수법 4.0 일반모드 원문 기준 재검증판

- 매매 엔진은 Step24X/25D 계열 V4.0 일반모드 로직을 그대로 사용한다.
- 이 파일은 V2.2 검증마감 이후 V4.0 일반모드를 별도 단계로 분리하기 위한 래퍼다.
- 리버스모드는 아직 포함하지 않는다.
- 원문에 없는 공식/수량/체결 규칙은 추가하지 않는다.
"""
from muhan_raor_v4_step25d_engine import run_raor_infinite4_step25d_core


def run_raor_infinite4_step25e_core(*args, **kwargs):
    return run_raor_infinite4_step25d_core(*args, **kwargs)
