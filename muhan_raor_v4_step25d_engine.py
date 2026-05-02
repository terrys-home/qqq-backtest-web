"""
Step25D - 라오어 무한매수법 4.0 원문 재검증판

- 매매 엔진은 Step24X/25C 계열의 V4.0 일반모드 로직을 그대로 사용한다.
- 이 파일은 V2.2와 V4.0 분리 작업을 위한 Step25D 명명/연결용 래퍼다.
- 리버스모드는 아직 기본 엔진에 넣지 않고, 일반모드 검증 후 별도 구현한다.
"""
from muhan_raor_v4_step24x_engine import run_raor_infinite4_step24p_core

def run_raor_infinite4_step25d_core(*args, **kwargs):
    return run_raor_infinite4_step24p_core(*args, **kwargs)
