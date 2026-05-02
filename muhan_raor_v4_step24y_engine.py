"""
Step24U - 라오어 무한매수법 4.0 원문기반 엔진

기준:
- 매매 엔진은 Step24O/P/Q/R/S/T 계열 원문 로직을 그대로 사용합니다.
- Step24U의 변경점은 app.py의 UI/polling 준비/무체결 공백 진단 강화입니다.
- 원문에 없는 매매 공식/규칙은 추가하지 않습니다.
"""

from muhan_raor_v4_step24o_engine import run_raor_infinite4_step24o_core


def run_raor_infinite4_step24p_core(*args, **kwargs):
    return run_raor_infinite4_step24o_core(*args, **kwargs)
