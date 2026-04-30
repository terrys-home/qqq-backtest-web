"""
Step24P - 라오어 무한매수법 4.0 원문기반 엔진

기준:
- 매매 엔진은 Step24O를 그대로 사용합니다.
- Step24P의 변경점은 app.py의 파라미터 세분화, DeepMining 진행형 UI, 후보판정, CSV 캐시 준비 구조입니다.
- 원문에 없는 매매 공식/규칙은 추가하지 않습니다.
"""

from muhan_raor_v4_step24o_engine import run_raor_infinite4_step24o_core


def run_raor_infinite4_step24p_core(*args, **kwargs):
    return run_raor_infinite4_step24o_core(*args, **kwargs)
