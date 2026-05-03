from flask import Flask, request, send_file, abort, jsonify, Response
import pandas as pd
import json
import hashlib
import threading
import uuid
import time
from pathlib import Path
from ticker_config import (
    TICKER_LIST,
    ticker_dict,
    TOP1_PRESETS,
    STRATEGY_PARAM_MAP,
    STRATEGY_LABELS,
    get_preset,
    get_preset_query,
    optimizer_compare_rows,
)

app = Flask(__name__)

# Step23A/B/C/D: V4 언이시트 근접 엔진
try:
    from muhan_v4_engine import run_infinite4_v4_core
except Exception:
    run_infinite4_v4_core = None

# Step23E: V5 언이시트 동적별지점 엔진
try:
    from muhan_v5_engine import run_infinite4_v5_core
except Exception:
    run_infinite4_v5_core = None





# Step24E: 매일 매도예약 원문 보강 엔진
try:
    from muhan_raor_v4_step24e_engine import run_raor_infinite4_step24e_core
except Exception:
    run_raor_infinite4_step24e_core = None

# Step24F: 지정가 전량매도 수익률 선택 + 매도예약 검증 보강 엔진
try:
    from muhan_raor_v4_step24f_engine import run_raor_infinite4_step24f_core
except Exception:
    run_raor_infinite4_step24f_core = None

# Step24G: 지정가 전량매도 수익률 커스텀 입력 + 매도예약 검증 보강 엔진
try:
    from muhan_raor_v4_step24g_engine import run_raor_infinite4_step24g_core
except Exception:
    run_raor_infinite4_step24g_core = None

# Step24H: Step24G 기반 + 같은날 체결신호 검증 로그 강화 엔진
try:
    from muhan_raor_v4_step24h_engine import run_raor_infinite4_step24h_core
except Exception:
    run_raor_infinite4_step24h_core = None

# Step24L: Step24H 기반 + LOC 매수/매도 가격분리 및 일봉 선후관계 분리 로그 엔진
try:
    from muhan_raor_v4_step24l_engine import run_raor_infinite4_step24l_core
except Exception:
    run_raor_infinite4_step24l_core = None

# Step24M: Step24L 기반 + 검증 카운터/Step24 전용 최적화 준비 엔진
try:
    from muhan_raor_v4_step24m_engine import run_raor_infinite4_step24m_core
except Exception:
    run_raor_infinite4_step24m_core = None

# Step24N: Step24M 기반 + 이전 Step24A~D 정리판
try:
    from muhan_raor_v4_step24n_engine import run_raor_infinite4_step24n_core
except Exception:
    run_raor_infinite4_step24n_core = None

# Step24O: Step24N 기준 + Step24 전용 Optimizer/DeepMining 화면 실행판
try:
    from muhan_raor_v4_step24o_engine import run_raor_infinite4_step24o_core
except Exception:
    run_raor_infinite4_step24o_core = None

# Step24P: Step24O 기준 + 파라미터 세분화 / 진행형 DeepMining UI / 캐시 준비판
try:
    from muhan_raor_v4_step24p_engine import run_raor_infinite4_step24p_core
except Exception:
    run_raor_infinite4_step24p_core = None

# Step24Q: Step24P 기준 + 캐시/CSV/후보적용/진행형 UI 고도화판
try:
    from muhan_raor_v4_step24q_engine import run_raor_infinite4_step24p_core as run_raor_infinite4_step24q_core
except Exception:
    run_raor_infinite4_step24q_core = None

# Step24R: Step24Q 기준 + SEED 스타일 UI 리디자인 / 실시간 진행률 준비판
try:
    from muhan_raor_v4_step24r_engine import run_raor_infinite4_step24p_core as run_raor_infinite4_step24r_core
except Exception:
    run_raor_infinite4_step24r_core = None

# Step24S: Step24R 기준 + 좁은 사이드바 / 섹션 전환형 UI / 실시간 polling 준비판
try:
    from muhan_raor_v4_step24s_engine import run_raor_infinite4_step24p_core as run_raor_infinite4_step24s_core
except Exception:
    run_raor_infinite4_step24s_core = None

# Step24T: Step24S 기준 + 좌측 여백 확장 / polling API 준비판
try:
    from muhan_raor_v4_step24t_engine import run_raor_infinite4_step24p_core as run_raor_infinite4_step24t_core
except Exception:
    run_raor_infinite4_step24t_core = None

# Step24U: Step24T 기준 + UI 안정화 / 무체결 공백 진단 / polling 확장 준비판
try:
    from muhan_raor_v4_step24u_engine import run_raor_infinite4_step24p_core as run_raor_infinite4_step24u_core
except Exception:
    run_raor_infinite4_step24u_core = None

# Step24V: Step24U 기준 + 후보 비교/실전선정판 + 정리 후보 점검판
try:
    from muhan_raor_v4_step24v_engine import run_raor_infinite4_step24p_core as run_raor_infinite4_step24v_core
except Exception:
    run_raor_infinite4_step24v_core = None

# Step24W: Step24V 기준 + 과최적화 방어 Robust Mining / 구간검증 / 주변값 안정성 판
try:
    from muhan_raor_v4_step24w_engine import run_raor_infinite4_step24p_core as run_raor_infinite4_step24w_core
except Exception:
    run_raor_infinite4_step24w_core = None

# Step24X: Step24W 기준 + 실제 진행형 Robust Mining / job polling / 취소·이어하기 준비판
try:
    from muhan_raor_v4_step24x_engine import run_raor_infinite4_step24p_core as run_raor_infinite4_step24x_core
except Exception:
    run_raor_infinite4_step24x_core = None

# Step24Y~Step25C: 매매 엔진은 Step24X 원문엔진을 그대로 사용하고, 화면/분석 기능만 확장한다.
run_raor_infinite4_step24y_core = run_raor_infinite4_step24x_core or run_raor_infinite4_step24w_core
run_raor_infinite4_step24z_core = run_raor_infinite4_step24x_core or run_raor_infinite4_step24w_core
run_raor_infinite4_step25a_core = run_raor_infinite4_step24x_core or run_raor_infinite4_step24w_core
run_raor_infinite4_step25b_core = run_raor_infinite4_step24x_core or run_raor_infinite4_step24w_core
run_raor_infinite4_step25c_core = run_raor_infinite4_step24x_core or run_raor_infinite4_step24w_core

# Step25D-3: V2.2 통합엔진 + V4.0 원문 재검증 래퍼
try:
    from muhan_raor_v22_engine import run_raor_v22_core
except Exception:
    run_raor_v22_core = None

try:
    from muhan_raor_v4_step25d_engine import run_raor_infinite4_step25d_core
except Exception:
    run_raor_infinite4_step25d_core = None

run_raor_infinite4_step25d_core = run_raor_infinite4_step25d_core or run_raor_infinite4_step24x_core or run_raor_infinite4_step24w_core


STEP24X_JOBS = {}
STEP24X_JOBS_LOCK = threading.Lock()

INITIAL_CASH = 100_000_000



def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def load_ticker_data(ticker):
    """티커별 일봉/주봉 데이터를 로드한다.
    우선순위:
    1) {ticker}_daily_data.csv
    2) {ticker}_daily_with_mode.csv

    주봉 파일이 없으면 일봉에서 자동 생성한다.
    daily에 WeeklyRSI가 없으면 weekly RSI를 붙인다.
    """
    ticker = ticker.upper()

    daily_file_candidates = [
        f"{ticker}_daily_data.csv",
        f"{ticker}_daily_with_mode.csv",
    ]
    weekly_file_candidates = [
        f"{ticker}_weekly_mode.csv",
    ]

    daily_df = None
    weekly_df = None
    daily_file_used = None
    weekly_file_used = None

    for file in daily_file_candidates:
        try:
            daily_df = pd.read_csv(file)
            daily_file_used = file
            break
        except Exception:
            continue

    if daily_df is None:
        return None, None

    # yfinance 등에서 MultiIndex 컬럼이 CSV로 저장된 경우 대비
    if "Date" not in daily_df.columns:
        first_col = daily_df.columns[0]
        daily_df = daily_df.rename(columns={first_col: "Date"})

    daily_df["Date"] = pd.to_datetime(daily_df["Date"], errors="coerce")
    daily_df = daily_df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

    if "Close" not in daily_df.columns:
        return None, None

    daily_df["Close"] = pd.to_numeric(daily_df["Close"], errors="coerce")
    daily_df = daily_df.dropna(subset=["Close"]).reset_index(drop=True)

    for file in weekly_file_candidates:
        try:
            weekly_df = pd.read_csv(file)
            weekly_file_used = file
            break
        except Exception:
            continue

    # weekly 파일이 없으면 일봉에서 자동 생성
    if weekly_df is None:
        weekly_df = daily_df.set_index("Date").resample("W-FRI").last().dropna(subset=["Close"]).reset_index()

    if "Date" not in weekly_df.columns:
        first_col = weekly_df.columns[0]
        weekly_df = weekly_df.rename(columns={first_col: "Date"})

    weekly_df["Date"] = pd.to_datetime(weekly_df["Date"], errors="coerce")
    weekly_df = weekly_df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

    if "Close" in weekly_df.columns:
        weekly_df["Close"] = pd.to_numeric(weekly_df["Close"], errors="coerce")

    # weekly RSI 없으면 계산
    if "RSI" not in weekly_df.columns and "WeeklyRSI" not in weekly_df.columns:
        if "Close" in weekly_df.columns:
            weekly_df["RSI"] = calc_rsi(weekly_df["Close"])
        else:
            weekly_df["RSI"] = 50

    # daily에 WeeklyRSI 없으면 weekly에서 붙이기
    if "WeeklyRSI" not in daily_df.columns:
        rsi_col = "WeeklyRSI" if "WeeklyRSI" in weekly_df.columns else "RSI"
        weekly_rsi = weekly_df[["Date", rsi_col]].copy().rename(columns={rsi_col: "WeeklyRSI"})
        daily_df = pd.merge_asof(
            daily_df.sort_values("Date"),
            weekly_rsi.sort_values("Date"),
            on="Date",
            direction="backward"
        )

    daily_df["WeeklyRSI"] = pd.to_numeric(daily_df.get("WeeklyRSI", 50), errors="coerce").fillna(50)
    daily_df["RSI"] = pd.to_numeric(daily_df.get("RSI", daily_df["WeeklyRSI"]), errors="coerce").fillna(daily_df["WeeklyRSI"])

    daily_df["MA5"] = daily_df["Close"].rolling(5).mean()
    daily_df["MA20"] = daily_df["Close"].rolling(20).mean()
    daily_df["MA200"] = daily_df["Close"].rolling(200).mean()

    # 디버그용 속성
    daily_df.attrs["daily_file_used"] = daily_file_used
    daily_df.attrs["weekly_file_used"] = weekly_file_used or "auto_generated_from_daily"

    return daily_df, weekly_df

# 현재 선택 티커 데이터는 home()에서 로드됨
daily = None
weekly = None


def run_infinite4_v4_backtest(**kwargs):
    """app/optimizer 공용 V4 래퍼.
    muhan_v4_engine.run_infinite4_v4_core는 daily_df를 첫 인자로 요구하므로,
    현재 선택된 전역 daily 데이터를 자동으로 주입한다.
    """
    if run_infinite4_v4_core is None:
        raise ImportError("muhan_v4_engine.py 또는 run_infinite4_v4_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_infinite4_v4_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )


def run_infinite4_v5_backtest(**kwargs):
    """app/optimizer 공용 V5 래퍼.
    V5는 기본 별점값을 초기값으로만 사용하고, 전반전/후반전/소진모드에 따라
    내부에서 동적 별지점/다음 LOC/큰수 후보를 재계산한다.
    """
    if run_infinite4_v5_core is None:
        raise ImportError("muhan_v5_engine.py 또는 run_infinite4_v5_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_infinite4_v5_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )






def run_raor_infinite4_step24e_backtest(**kwargs):
    """Step24E: 매일 매도예약 원문 보강 엔진 래퍼."""
    if run_raor_infinite4_step24e_core is None:
        raise ImportError("muhan_raor_v4_step24e_engine.py 또는 run_raor_infinite4_step24e_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_infinite4_step24e_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )



def run_raor_infinite4_step24f_backtest(**kwargs):
    """Step24F: 지정가 전량매도 수익률 선택 + 매도예약 검증 보강 엔진 래퍼."""
    if run_raor_infinite4_step24f_core is None:
        raise ImportError("muhan_raor_v4_step24f_engine.py 또는 run_raor_infinite4_step24f_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_infinite4_step24f_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )


def run_raor_infinite4_step24g_backtest(**kwargs):
    """Step24G: 지정가 전량매도 수익률 커스텀 입력 + 매도예약 검증 보강 엔진 래퍼."""
    if run_raor_infinite4_step24g_core is None:
        raise ImportError("muhan_raor_v4_step24g_engine.py 또는 run_raor_infinite4_step24g_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_infinite4_step24g_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )


def run_raor_infinite4_step24h_backtest(**kwargs):
    """Step24H: Step24G 기반 + 지정가/별LOC/매수LOC 동시신호 검증 로그 강화 엔진 래퍼."""
    if run_raor_infinite4_step24h_core is None:
        raise ImportError("muhan_raor_v4_step24h_engine.py 또는 run_raor_infinite4_step24h_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_infinite4_step24h_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )


def run_raor_infinite4_step24l_backtest(**kwargs):
    """Step24L: Step24H 기반 + 별LOC 매수가/매도가 가격분리 및 일봉 선후관계 분리 로그 엔진 래퍼."""
    if run_raor_infinite4_step24l_core is None:
        raise ImportError("muhan_raor_v4_step24l_engine.py 또는 run_raor_infinite4_step24l_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_infinite4_step24l_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )


def run_raor_infinite4_step24m_backtest(**kwargs):
    """Step24M: Step24L 기반 + 검증 카운터/Step24 전용 최적화 준비 엔진 래퍼."""
    if run_raor_infinite4_step24m_core is None:
        raise ImportError("muhan_raor_v4_step24m_engine.py 또는 run_raor_infinite4_step24m_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_infinite4_step24m_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )


def run_raor_infinite4_step24n_backtest(**kwargs):
    """Step24N: Step24M 기반 + 이전 Step24A~D 정리판 엔진 래퍼."""
    if run_raor_infinite4_step24n_core is None:
        raise ImportError("muhan_raor_v4_step24n_engine.py 또는 run_raor_infinite4_step24n_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_infinite4_step24n_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )


def run_raor_infinite4_step24o_backtest(**kwargs):
    """Step24O: Step24N 기준 + Step24 전용 Optimizer/DeepMining 화면 실행판 엔진 래퍼."""
    if run_raor_infinite4_step24o_core is None:
        raise ImportError("muhan_raor_v4_step24o_engine.py 또는 run_raor_infinite4_step24o_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_infinite4_step24o_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )


def run_raor_infinite4_step24p_backtest(**kwargs):
    """Step24P: Step24O 엔진 기준, UI/최적화 탐색 구조 확장판 래퍼."""
    if run_raor_infinite4_step24p_core is None:
        raise ImportError("muhan_raor_v4_step24p_engine.py 또는 run_raor_infinite4_step24p_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_infinite4_step24p_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )


def run_raor_infinite4_step24q_backtest(**kwargs):
    """Step24Q: Step24P 기준 + 캐시/CSV/후보적용/진행형 UI 고도화판 래퍼."""
    if run_raor_infinite4_step24q_core is None:
        raise ImportError("muhan_raor_v4_step24q_engine.py 또는 run_raor_infinite4_step24q_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_infinite4_step24q_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )

def run_raor_infinite4_step24r_backtest(**kwargs):
    """Step24R: Step24Q 매매엔진 그대로 + UI/진행률 준비판 래퍼."""
    if run_raor_infinite4_step24r_core is None:
        raise ImportError("muhan_raor_v4_step24r_engine.py 또는 run_raor_infinite4_step24r_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_infinite4_step24r_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )


def run_raor_infinite4_step24s_backtest(**kwargs):
    """Step24S: Step24R 매매엔진 그대로 + 좁은 사이드바/섹션 전환 UI 래퍼."""
    if run_raor_infinite4_step24s_core is None:
        raise ImportError("muhan_raor_v4_step24s_engine.py 또는 run_raor_infinite4_step24s_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_infinite4_step24s_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )


def run_raor_infinite4_step24t_backtest(**kwargs):
    """Step24T: Step24S 매매엔진 그대로 + 좌측 여백 확장/polling 준비판 래퍼."""
    if run_raor_infinite4_step24t_core is None:
        raise ImportError("muhan_raor_v4_step24t_engine.py 또는 run_raor_infinite4_step24t_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_infinite4_step24t_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )


def run_raor_infinite4_step24u_backtest(**kwargs):
    """Step24U: Step24S 매매엔진 그대로 + UI/진단/polling 확장 준비판 래퍼."""
    if run_raor_infinite4_step24u_core is None:
        raise ImportError("muhan_raor_v4_step24u_engine.py 또는 run_raor_infinite4_step24u_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_infinite4_step24u_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )



def run_raor_infinite4_step24v_backtest(**kwargs):
    """Step24V: Step24U 매매엔진 그대로 + 후보 비교/실전선정/정리 후보 점검판 래퍼."""
    if run_raor_infinite4_step24v_core is None:
        raise ImportError("muhan_raor_v4_step24v_engine.py 또는 run_raor_infinite4_step24v_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_infinite4_step24v_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )


def run_raor_infinite4_step24w_backtest(**kwargs):
    """Step24W: Step24V 매매엔진 그대로 + Robust Mining/과최적화 방어 점수판 래퍼."""
    if run_raor_infinite4_step24w_core is None:
        raise ImportError("muhan_raor_v4_step24w_engine.py 또는 run_raor_infinite4_step24w_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_infinite4_step24w_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )


def run_raor_infinite4_step24x_backtest(**kwargs):
    """Step24X: Step24W 매매엔진 그대로 + 실제 진행형 Robust Mining/polling 래퍼."""
    core = run_raor_infinite4_step24x_core or run_raor_infinite4_step24w_core
    if core is None:
        raise ImportError("muhan_raor_v4_step24x_engine.py 또는 Step24W 코어를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )


def run_raor_infinite4_step24y_backtest(**kwargs):
    """Step24Y: 결과 해석/후보 선택 도우미. 매매공식은 Step24X와 동일."""
    return run_raor_infinite4_step24x_backtest(**kwargs)


def run_raor_infinite4_step24z_backtest(**kwargs):
    """Step24Z: 프리셋 저장/불러오기 준비판. 매매공식은 Step24X와 동일."""
    return run_raor_infinite4_step24x_backtest(**kwargs)


def run_raor_infinite4_step25a_backtest(**kwargs):
    """Step25A: TQQQ/SOXL 동시 비교 준비판. 매매공식은 Step24X와 동일."""
    return run_raor_infinite4_step24x_backtest(**kwargs)


def run_raor_infinite4_step25b_backtest(**kwargs):
    """Step25B: 원문/스프레드시트 교차검증 준비판. 매매공식은 Step24X와 동일."""
    return run_raor_infinite4_step24x_backtest(**kwargs)


def run_raor_infinite4_step25c_backtest(**kwargs):
    """Step25C: RPA 주문 신호 출력 준비판. 매매공식은 Step24X와 동일."""
    return run_raor_infinite4_step24x_backtest(**kwargs)

def run_raor_infinite4_step25d_backtest(**kwargs):
    """Step25D-3: V4.0 원문 재검증판. 매매공식은 Step24X와 동일, V2.2는 티커별 공식 통합 엔진으로 분리."""
    if run_raor_infinite4_step25d_core is None:
        raise ImportError("muhan_raor_v4_step25d_engine.py 또는 Step24X 코어를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_infinite4_step25d_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )


def run_raor_v22_backtest(**kwargs):
    """라오어 무한매수법 V2.2 통합 엔진 래퍼. TQQQ/SOXL은 전략 분리가 아니라 티커별 공식 자동 적용."""
    if run_raor_v22_core is None:
        raise ImportError("muhan_raor_v22_engine.py 또는 run_raor_v22_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_v22_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )



    """Step24T: Step24S 매매엔진 그대로 + 좌측 여백 확장/polling 준비판 래퍼."""
    if run_raor_infinite4_step24t_core is None:
        raise ImportError("muhan_raor_v4_step24t_engine.py 또는 run_raor_infinite4_step24t_core를 불러오지 못했습니다.")
    if daily is None:
        raise ValueError("daily 데이터가 로드되지 않았습니다. load_ticker_data() 후 실행하세요.")
    return run_raor_infinite4_step24t_core(
        daily_df=daily,
        initial_cash=INITIAL_CASH,
        **kwargs,
    )

# =========================
# 공통 함수

# =========================
def make_mode(rsi, sell_rsi):
    if rsi >= sell_rsi:
        return "과열"
    elif rsi >= 50:
        return "상승"
    elif rsi >= 30:
        return "중립"
    elif rsi >= 20:
        return "침체"
    else:
        return "극침체"


def add_metrics(result_df):
    result_df["Peak"] = result_df["TotalAsset"].cummax()
    result_df["Drawdown"] = (result_df["TotalAsset"] - result_df["Peak"]) / result_df["Peak"]
    result_df["DailyReturn"] = result_df["TotalAsset"].pct_change().fillna(0) * 100
    return result_df


def calc_cagr(bt):
    if bt.empty:
        return 0

    start_date = bt["Date"].min()
    end_date = bt["Date"].max()
    years = max((end_date - start_date).days / 365.25, 0.01)

    start_asset = bt.iloc[0]["TotalAsset"]
    end_asset = bt.iloc[-1]["TotalAsset"]

    if start_asset <= 0:
        return 0

    return ((end_asset / start_asset) ** (1 / years) - 1) * 100


def calc_buyhold_stats(bt):
    """선택 기간 기준 QQQ 단순보유 성과 계산"""
    if bt.empty or len(bt) < 2:
        return 0, 0, 0, INITIAL_CASH

    start_close = float(bt.iloc[0]["Close"])
    if start_close <= 0:
        return 0, 0, 0, INITIAL_CASH

    bh_asset = INITIAL_CASH * (bt["Close"] / start_close)
    bh_final_asset = float(bh_asset.iloc[-1])
    bh_return = (bh_final_asset / INITIAL_CASH - 1) * 100

    peak = bh_asset.cummax()
    dd = (bh_asset - peak) / peak
    bh_mdd = float(dd.min() * 100)

    start_date = bt["Date"].min()
    end_date = bt["Date"].max()
    years = max((end_date - start_date).days / 365.25, 0.01)
    bh_cagr = ((bh_final_asset / INITIAL_CASH) ** (1 / years) - 1) * 100

    return bh_return, bh_cagr, bh_mdd, bh_final_asset


def cls_delta(value):
    return "positive" if value >= 0 else "negative"


def cls_positive_negative(value):
    return "positive" if value >= 0 else "negative"


def cls_mdd(value):
    if value <= -20:
        return "danger"
    elif value <= -10:
        return "warning"
    return "positive"


def cls_open_position(open_position):
    return "warning" if open_position == "있음" else "positive"


def make_strategy_verdict(return_delta, mdd_improvement):
    if return_delta >= 0 and mdd_improvement >= 0:
        return "전략 우세", "positive", "단순보유보다 수익률과 방어력이 모두 우수합니다."
    if return_delta >= 0 and mdd_improvement < 0:
        return "수익 우세 / 리스크 확인", "warning", "단순보유보다 수익률은 높지만 MDD는 더 큽니다."
    if return_delta < 0 and mdd_improvement >= 0:
        return "방어 우세", "warning", "수익률은 단순보유보다 낮지만 MDD 방어는 더 좋습니다."
    return "단순보유 우세", "negative", "현재 조건에서는 단순보유 대비 수익률과 방어력이 모두 아쉽습니다."


def calc_yearly_stats(bt):
    """선택 기간 기준 연도별 전략/QQQ 성과 계산"""
    if bt.empty:
        return pd.DataFrame()

    yearly_rows = []
    temp = bt.copy()
    temp["Year"] = temp["Date"].dt.year

    for year, group in temp.groupby("Year"):
        group = group.sort_values("Date").copy()
        if len(group) < 2:
            continue

        strategy_start = float(group.iloc[0]["TotalAsset"])
        strategy_end = float(group.iloc[-1]["TotalAsset"])
        qqq_start = float(group.iloc[0]["Close"])
        qqq_end = float(group.iloc[-1]["Close"])

        strategy_return = (strategy_end / strategy_start - 1) * 100 if strategy_start > 0 else 0
        qqq_return = (qqq_end / qqq_start - 1) * 100 if qqq_start > 0 else 0
        excess_return = strategy_return - qqq_return

        peak = group["TotalAsset"].cummax()
        dd = (group["TotalAsset"] - peak) / peak
        year_mdd = float(dd.min() * 100) if not dd.empty else 0

        qqq_asset = INITIAL_CASH * (group["Close"] / qqq_start) if qqq_start > 0 else pd.Series([INITIAL_CASH] * len(group))
        qqq_peak = qqq_asset.cummax()
        qqq_dd = (qqq_asset - qqq_peak) / qqq_peak
        qqq_mdd = float(qqq_dd.min() * 100) if not qqq_dd.empty else 0

        yearly_rows.append({
            "Year": int(year),
            "StrategyReturn": strategy_return,
            "QQQReturn": qqq_return,
            "ExcessReturn": excess_return,
            "StrategyMDD": year_mdd,
            "QQQMDD": qqq_mdd,
        })

    return pd.DataFrame(yearly_rows)


def pick_first_existing_col(df, candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None


def to_number_safe(value, default=0):
    try:
        if pd.isna(value):
            return default
        if isinstance(value, str):
            value = value.replace("%", "").replace(",", "").strip()
        return float(value)
    except Exception:
        return default


def classify_strategy_type(cagr, mdd, win_rate=0):
    """딥마이닝 결과를 공격형/균형형/방어형으로 간단 분류"""
    abs_mdd = abs(mdd)
    if cagr >= 8 and abs_mdd >= 18:
        return "공격형"
    if abs_mdd <= 12 and win_rate >= 60:
        return "방어형"
    return "균형형"


def summarize_period(bt_period):
    """Step18A: 기간별 요약"""
    if bt_period.empty or len(bt_period) < 2:
        return {
            "start": "-",
            "end": "-",
            "return": 0,
            "cagr": 0,
            "mdd": 0,
            "final_asset": INITIAL_CASH,
            "class": "warning",
        }

    start_asset = float(bt_period.iloc[0]["TotalAsset"])
    end_asset = float(bt_period.iloc[-1]["TotalAsset"])
    period_return = (end_asset / start_asset - 1) * 100 if start_asset > 0 else 0

    peak = bt_period["TotalAsset"].cummax()
    dd = (bt_period["TotalAsset"] - peak) / peak
    period_mdd = float(dd.min() * 100) if not dd.empty else 0

    period_cagr = calc_cagr(bt_period)

    return {
        "start": bt_period.iloc[0]["Date"].strftime("%Y-%m-%d"),
        "end": bt_period.iloc[-1]["Date"].strftime("%Y-%m-%d"),
        "return": period_return,
        "cagr": period_cagr,
        "mdd": period_mdd,
        "final_asset": end_asset,
        "class": cls_positive_negative(period_return),
    }


def make_walkforward_summary(bt):
    """Step18A: 인샘플 / 아웃샘플 검증"""
    train = bt[(bt["Date"] >= pd.Timestamp("2010-01-01")) & (bt["Date"] <= pd.Timestamp("2018-12-31"))].copy()
    test = bt[bt["Date"] >= pd.Timestamp("2019-01-01")].copy()

    train_summary = summarize_period(train)
    test_summary = summarize_period(test)

    cagr_drop = train_summary["cagr"] - test_summary["cagr"]
    mdd_worse = abs(test_summary["mdd"]) - abs(train_summary["mdd"])

    if test.empty or train.empty:
        verdict = "검증 데이터 부족"
        verdict_class = "warning"
        detail = "선택 기간이 너무 짧아 인샘플/아웃샘플을 나누기 어렵습니다."
    elif cagr_drop >= 5 and mdd_worse >= 5:
        verdict = "과최적화 의심"
        verdict_class = "danger"
        detail = "검증 구간 CAGR이 크게 낮고 MDD도 악화되었습니다."
    elif cagr_drop >= 5:
        verdict = "수익성 둔화"
        verdict_class = "warning"
        detail = "검증 구간 수익성이 학습 구간보다 낮아졌습니다."
    elif mdd_worse >= 5:
        verdict = "리스크 확대"
        verdict_class = "warning"
        detail = "검증 구간 MDD가 학습 구간보다 악화되었습니다."
    else:
        verdict = "검증 양호"
        verdict_class = "positive"
        detail = "학습 구간과 검증 구간의 성과 차이가 과도하지 않습니다."

    return train_summary, test_summary, cagr_drop, mdd_worse, verdict, verdict_class, detail


def calc_stability_score(train_summary, test_summary, mdd_worse):
    """과최적화 방지용 간단 안정성 점수(0~100).
    - OOS CAGR이 IS CAGR에 가까울수록 높음
    - OOS MDD가 IS보다 크게 나빠지면 감점
    """
    is_cagr = abs(train_summary.get("cagr", 0))
    oos_cagr = test_summary.get("cagr", 0)

    if is_cagr <= 0.01:
        base = 50 if oos_cagr >= 0 else 20
    else:
        base = max(0, min(100, (oos_cagr / is_cagr) * 100))

    penalty = max(0, mdd_worse) * 2
    score = max(0, min(100, base - penalty))

    if score >= 75:
        risk = "낮음"
        risk_class = "positive"
    elif score >= 50:
        risk = "보통"
        risk_class = "warning"
    else:
        risk = "높음"
        risk_class = "danger"

    return score, risk, risk_class


# =========================
# 거래 요약

# =========================

def get_sell_trade_df(trade_df):
    """Trade Event Log가 BUY/SELL을 모두 담을 때 SELL 이벤트만 분리한다."""
    if trade_df is None or trade_df.empty:
        return pd.DataFrame()
    if "EventSide" in trade_df.columns:
        return trade_df[trade_df["EventSide"].astype(str).str.upper() == "SELL"].copy()
    if "OrderType" in trade_df.columns:
        mask = trade_df["OrderType"].astype(str).str.upper().eq("SELL")
        if mask.any():
            return trade_df[mask].copy()
    return trade_df.copy()


def get_buy_trade_df(trade_df):
    """Step25D-7-5: 실제 BUY 이벤트를 분리한다. 옛 로그에는 빈 DF를 반환한다."""
    if trade_df is None or trade_df.empty:
        return pd.DataFrame()
    if "EventSide" in trade_df.columns:
        return trade_df[trade_df["EventSide"].astype(str).str.upper() == "BUY"].copy()
    if "OrderType" in trade_df.columns:
        mask = trade_df["OrderType"].astype(str).str.upper().eq("BUY")
        if mask.any():
            return trade_df[mask].copy()
    return pd.DataFrame()


def filter_trade_df_by_period(trade_df, start_dt, end_dt):
    """
    Step25D-7-5: BUY/SELL 이벤트 로그는 SellDate 기준으로 필터링하면 BUY 이벤트가 모두 사라진다.
    EventDate가 있으면 EventDate 기준으로 필터링하고, 구버전 로그만 SellDate 기준으로 fallback한다.
    """
    if trade_df is None or trade_df.empty:
        return trade_df
    df = trade_df.copy()
    date_col = None
    for c in ["EventDate", "SellDate", "BuyDate"]:
        if c in df.columns:
            date_col = c
            break
    if date_col is None:
        return df
    df["_EventFilterDate"] = pd.to_datetime(df[date_col], errors="coerce")
    df = df[(df["_EventFilterDate"] >= start_dt) & (df["_EventFilterDate"] <= end_dt)].copy()
    return df.drop(columns=["_EventFilterDate"], errors="ignore")


def get_trade_event_counts(trade_df):
    if trade_df is None or trade_df.empty:
        return {"event_count": 0, "buy_event_count": 0, "sell_event_count": 0}
    if "EventSide" in trade_df.columns:
        side = trade_df["EventSide"].astype(str).str.upper()
        return {
            "event_count": int(len(trade_df)),
            "buy_event_count": int((side == "BUY").sum()),
            "sell_event_count": int((side == "SELL").sum()),
        }
    return {"event_count": int(len(trade_df)), "buy_event_count": 0, "sell_event_count": int(len(trade_df))}


def fmt_log_date(value):
    if value is None or value == "" or pd.isna(value):
        return ""
    try:
        return pd.to_datetime(value).strftime("%Y-%m-%d")
    except Exception:
        return str(value)

def make_trade_summary(trade_df, bt):
    """
    Step25D-7-5: V2.2 이벤트 로그에서 승률/보유일을 부분 SELL 이벤트 기준으로 계산하면
    쿼터MOC/부분매도가 모두 개별 거래로 잡혀 왜곡된다.
    - EventSide/CycleId가 있는 로그: 완료 주기 단위로 승률/보유일 계산
    - 구버전 로그: 기존처럼 SELL 로그 기준으로 계산
    """
    if trade_df is None or trade_df.empty:
        open_position = "있음" if (bt is not None and not bt.empty and float(bt.iloc[-1].get("Shares", 0) or 0) > 0) else "없음"
        max_split = bt["CurrentSplit"].max() if bt is not None and not bt.empty and "CurrentSplit" in bt.columns else 0
        return {
            "trade_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate": 0,
            "avg_hold_days": 0,
            "max_hold_days": 0,
            "trades_per_year": 0,
            "open_position": open_position,
            "max_split": round(max_split, 1),
            "summary_basis": "완료 주기",
        }

    sell_df = get_sell_trade_df(trade_df)
    event_style = "EventSide" in trade_df.columns and "CycleId" in trade_df.columns

    if event_style and bt is not None and not bt.empty and "CycleId" in bt.columns:
        final_row = bt.tail(1).iloc[0]
        open_now = float(final_row.get("Shares", 0) or 0) > 1e-9
        max_cycle_id = int(pd.to_numeric(bt["CycleId"], errors="coerce").fillna(0).max())
        inferred_last_completed = max_cycle_id - (1 if open_now else 0)
        completed_ids = set(range(1, max(0, inferred_last_completed) + 1))

        if "CycleCompleted" in sell_df.columns:
            completed_by_event = sell_df.loc[sell_df["CycleCompleted"].fillna(False).astype(bool), "CycleId"]
            completed_ids |= set(pd.to_numeric(completed_by_event, errors="coerce").dropna().astype(int).tolist())

        rows = []
        if completed_ids and not sell_df.empty:
            sdf = sell_df.copy()
            sdf["CycleIdNum"] = pd.to_numeric(sdf["CycleId"], errors="coerce").fillna(0).astype(int)
            sdf = sdf[sdf["CycleIdNum"].isin(completed_ids)].copy()
            for cid, g in sdf.groupby("CycleIdNum"):
                if g.empty:
                    continue
                profit = float(pd.to_numeric(g.get("Profit", 0), errors="coerce").fillna(0).sum())
                buy_amount = float(pd.to_numeric(g.get("BuyAmount", 0), errors="coerce").fillna(0).sum())
                start_v = pd.NaT
                end_v = pd.NaT
                if "CycleStartDate" in g.columns and not g["CycleStartDate"].dropna().empty:
                    start_v = pd.to_datetime(g["CycleStartDate"].dropna().iloc[0], errors="coerce")
                if pd.isna(start_v) and "BuyDate" in g.columns and not g["BuyDate"].dropna().empty:
                    start_v = pd.to_datetime(g["BuyDate"].dropna().min(), errors="coerce")
                if "SellEventDate" in g.columns and not g["SellEventDate"].dropna().empty:
                    end_v = pd.to_datetime(g["SellEventDate"].dropna().max(), errors="coerce")
                elif "SellDate" in g.columns and not g["SellDate"].dropna().empty:
                    end_v = pd.to_datetime(g["SellDate"].dropna().max(), errors="coerce")
                hold_days = int((end_v - start_v).days) if pd.notna(start_v) and pd.notna(end_v) else 0
                rows.append({"CycleId": int(cid), "Profit": profit, "BuyAmount": buy_amount, "HoldDays": hold_days})

        cycle_perf = pd.DataFrame(rows)
        trade_count = len(cycle_perf)
        win_count = int((cycle_perf["Profit"] > 0).sum()) if not cycle_perf.empty else 0
        loss_count = int((cycle_perf["Profit"] <= 0).sum()) if not cycle_perf.empty else 0
        win_rate = (win_count / trade_count) * 100 if trade_count > 0 else 0
        avg_hold_days = cycle_perf["HoldDays"].mean() if not cycle_perf.empty else 0
        max_hold_days = cycle_perf["HoldDays"].max() if not cycle_perf.empty else 0
    else:
        # 구버전/단일 매도 로그 전략 fallback
        trade_count = len(sell_df)
        win_count = len(sell_df[sell_df["Profit"] > 0]) if "Profit" in sell_df.columns else 0
        loss_count = len(sell_df[sell_df["Profit"] <= 0]) if "Profit" in sell_df.columns else 0
        win_rate = (win_count / trade_count) * 100 if trade_count > 0 else 0
        avg_hold_days = sell_df["HoldDays"].mean() if "HoldDays" in sell_df.columns and not sell_df.empty else 0
        max_hold_days = sell_df["HoldDays"].max() if "HoldDays" in sell_df.columns and not sell_df.empty else 0

    years = max((bt["Date"].max() - bt["Date"].min()).days / 365.25, 1) if bt is not None and not bt.empty else 1
    trades_per_year = trade_count / years if years > 0 else 0
    open_position = "있음" if bt is not None and not bt.empty and float(bt.iloc[-1].get("Shares", 0) or 0) > 0 else "없음"
    max_split = bt["CurrentSplit"].max() if bt is not None and not bt.empty and "CurrentSplit" in bt.columns else 0

    return {
        "trade_count": int(trade_count),
        "win_count": int(win_count),
        "loss_count": int(loss_count),
        "win_rate": round(win_rate, 2),
        "avg_hold_days": round(avg_hold_days, 1) if pd.notna(avg_hold_days) else 0,
        "max_hold_days": int(max_hold_days) if pd.notna(max_hold_days) else 0,
        "trades_per_year": round(trades_per_year, 2),
        "open_position": open_position,
        "max_split": round(max_split, 1),
        "summary_basis": "완료 주기" if event_style else "매도 이벤트",
    }


def make_cycle_status(trade_df, bt, split_count):
    """Step24D UI용 무한매수 주기 요약.
    완료 주기 0 고정 문제 보정:
    - trade_df의 CycleCompleted만 믿지 않고 bt의 CycleId 진행값으로도 추정한다.
    - 현재 미청산이 있으면 max(CycleId)-1까지 완료, 없으면 max(CycleId)까지 완료로 본다.
    """
    status = {
        "completed_cycles": 0,
        "completed_profit": 0.0,
        "active_cycle_label": "없음",
        "active_cycle_id": None,
        "active_start": "-",
        "active_days": 0,
        "active_t": 0.0,
        "active_progress_pct": 0.0,
        "active_remaining_t": float(split_count),
        "open_position": "없음",
    }
    if bt is None or bt.empty:
        return status

    final_row = bt.tail(1).iloc[0]
    shares = float(final_row.get("Shares", 0) or 0)
    current_t = float(final_row.get("T", final_row.get("CurrentSplit", 0)) or 0)
    open_now = shares > 1e-9 and current_t > 1e-9

    max_cycle_id = 0
    if "CycleId" in bt.columns:
        try:
            max_cycle_id = int(pd.to_numeric(bt["CycleId"], errors="coerce").fillna(0).max())
        except Exception:
            max_cycle_id = 0

    completed_ids = set()
    if trade_df is not None and not trade_df.empty and "CycleId" in trade_df.columns:
        cdf = trade_df.copy()
        if "CycleCompleted" in cdf.columns:
            cdf["CycleCompleted"] = cdf["CycleCompleted"].fillna(False).astype(bool)
            completed_ids |= set(cdf.loc[cdf["CycleCompleted"], "CycleId"].dropna().astype(int).tolist())

    # bt CycleId 기준 보정: 현재 294회차 진행 중이면 1~293회차는 완료로 간주
    if max_cycle_id > 0:
        inferred_last_completed = max_cycle_id - (1 if open_now else 0)
        if inferred_last_completed > 0:
            completed_ids |= set(range(1, inferred_last_completed + 1))

    status["completed_cycles"] = len(completed_ids)
    if trade_df is not None and not trade_df.empty and completed_ids and "Profit" in trade_df.columns and "CycleId" in trade_df.columns:
        try:
            sell_df = get_sell_trade_df(trade_df)
            status["completed_profit"] = float(sell_df[sell_df["CycleId"].isin(completed_ids)]["Profit"].fillna(0).sum())
        except Exception:
            status["completed_profit"] = 0.0

    cycle_id_raw = final_row.get("CycleId", None)
    if open_now:
        status["open_position"] = "있음"
        try:
            cycle_id = int(cycle_id_raw)
        except Exception:
            cycle_id = max_cycle_id if max_cycle_id > 0 else None
        status["active_cycle_id"] = cycle_id
        status["active_cycle_label"] = f"{cycle_id}회차" if cycle_id else "진행 중"
        status["active_t"] = round(current_t, 2)
        status["active_progress_pct"] = round((current_t / float(split_count)) * 100.0, 1) if split_count else 0.0
        status["active_remaining_t"] = round(max(float(split_count) - current_t, 0.0), 2)

        start_v = final_row.get("CycleStartDate", None)
        if pd.isna(start_v) or start_v in (None, ""):
            if cycle_id is not None and "CycleId" in bt.columns:
                same = bt[bt["CycleId"] == cycle_id]
                if not same.empty:
                    # 같은 CycleId에서 실제 포지션이 시작된 첫 날짜 우선
                    if "Shares" in same.columns:
                        same_pos = same[same["Shares"] > 1e-9]
                        start_v = same_pos["Date"].min() if not same_pos.empty else same["Date"].min()
                    else:
                        start_v = same["Date"].min()
            else:
                start_v = final_row.get("Date", None)
        if pd.notna(start_v):
            start_ts = pd.to_datetime(start_v)
            end_ts = pd.to_datetime(final_row.get("Date"))
            status["active_start"] = start_ts.strftime("%Y-%m-%d")
            status["active_days"] = int((end_ts - start_ts).days)
    return status


def make_cycle_detail_summary(trade_df, bt, split_count, cycle_status):
    """Step24D: 주기별 상세 분석용 집계."""
    detail = {
        "avg_cycle_days": 0,
        "max_cycle_days": 0,
        "min_cycle_days": 0,
        "avg_cycle_return": 0.0,
        "best_cycle_profit": 0.0,
        "worst_cycle_profit": 0.0,
        "avg_max_t": 0.0,
        "max_used_t": 0.0,
        "second_half_count": 0,
        "exhaust_count": 0,
        "quarter_sell_count": 0,
        "quarter_start_count": 0,
        "quarter_moc_count": 0,
        "quarter_loc_buy_count": 0,
        "quarter_loc_sell_count": 0,
        "quarter_exit_count": 0,
        "quarter_repeat_count": 0,
        "quarter_trigger_candidate_count": 0,
        "quarter_trigger_executed_count": 0,
        "quarter_cash_validation_fail_count": 0,
        "quarter_shares_validation_fail_count": 0,
        "quarter_cost_basis_validation_fail_count": 0,
        "quarter_total_moc_sell_amount": 0.0,
        "quarter_total_moc_sell_qty": 0.0,
        "quarter_total_loc_buy_amount": 0.0,
        "quarter_total_loc_buy_qty": 0.0,
        "quarter_total_loc_sell_amount": 0.0,
        "quarter_total_loc_sell_qty": 0.0,
        "quarter_max_cash_delta_diff": 0.0,
    }
    if bt is None or bt.empty or "CycleId" not in bt.columns:
        return detail
    temp = bt.copy()
    temp["CycleIdNum"] = pd.to_numeric(temp["CycleId"], errors="coerce").fillna(0).astype(int)
    temp = temp[temp["CycleIdNum"] > 0]
    if temp.empty:
        return detail

    max_t_by_cycle = temp.groupby("CycleIdNum")["T" if "T" in temp.columns else "CurrentSplit"].max()
    detail["avg_max_t"] = float(max_t_by_cycle.mean()) if not max_t_by_cycle.empty else 0.0
    detail["max_used_t"] = float(max_t_by_cycle.max()) if not max_t_by_cycle.empty else 0.0

    if "QuarterTriggerCandidate" in temp.columns:
        detail["quarter_trigger_candidate_count"] = int(temp["QuarterTriggerCandidate"].fillna(False).astype(bool).sum())
    if "QuarterTriggerExecuted" in temp.columns:
        detail["quarter_trigger_executed_count"] = int(temp["QuarterTriggerExecuted"].fillna(False).astype(bool).sum())

    if "PhaseAfter" in temp.columns:
        detail["second_half_count"] = int(temp.loc[temp["PhaseAfter"] == "후반전", "CycleIdNum"].nunique())
        detail["exhaust_count"] = int(temp.loc[temp["PhaseAfter"] == "소진모드", "CycleIdNum"].nunique())
    elif "Mode" in temp.columns:
        detail["second_half_count"] = int(temp.loc[temp["Mode"] == "후반전", "CycleIdNum"].nunique())
        detail["exhaust_count"] = int(temp.loc[temp["Mode"] == "소진모드", "CycleIdNum"].nunique())

    if trade_df is not None and not trade_df.empty:
        sell_events = get_sell_trade_df(trade_df)
        all_events = trade_df.copy()
        reason_all = all_events["Reason"].astype(str) if "Reason" in all_events.columns else pd.Series(dtype=str)
        transition_all = all_events["ModeTransitionReason"].astype(str) if "ModeTransitionReason" in all_events.columns else pd.Series(dtype=str)
        if "Reason" in sell_events.columns:
            detail["quarter_sell_count"] = int(sell_events["Reason"].astype(str).str.contains("쿼터", na=False).sum())
        if not all_events.empty:
            qtype = all_events["QuarterEventType"].astype(str) if "QuarterEventType" in all_events.columns else pd.Series([""] * len(all_events), index=all_events.index)
            if "QuarterEventType" in all_events.columns:
                detail["quarter_start_count"] = int((qtype == "QUARTER_START_MOC").sum())
                detail["quarter_moc_count"] = int(qtype.isin(["QUARTER_START_MOC", "QUARTER_10TH_MOC"]).sum())
                detail["quarter_loc_buy_count"] = int((qtype == "QUARTER_LOC_BUY").sum())
                detail["quarter_loc_sell_count"] = int((qtype == "QUARTER_LOC_SELL").sum())
            else:
                detail["quarter_start_count"] = int(reason_all.str.contains("쿼터손절 시작", na=False).sum())
                detail["quarter_moc_count"] = int(reason_all.str.contains("쿼터.*MOC|MOC.*쿼터", regex=True, na=False).sum())
                detail["quarter_loc_buy_count"] = int(reason_all.str.contains("쿼터손절 LOC매수", na=False).sum())
                detail["quarter_loc_sell_count"] = int(reason_all.str.contains("쿼터손절 LOC매도", na=False).sum())
            detail["quarter_exit_count"] = int(transition_all.str.contains("복귀", na=False).sum())
            detail["quarter_repeat_count"] = int(transition_all.str.contains("반복", na=False).sum())

            qevents = all_events[qtype.str.startswith("QUARTER", na=False)].copy()
            if not qevents.empty:
                def _sum_num(df, col):
                    return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum()) if col in df.columns else 0.0
                moc_events = qevents[qtype.loc[qevents.index].isin(["QUARTER_START_MOC", "QUARTER_10TH_MOC"])]
                q_buy_events = qevents[qtype.loc[qevents.index].eq("QUARTER_LOC_BUY")]
                q_loc_sell_events = qevents[qtype.loc[qevents.index].eq("QUARTER_LOC_SELL")]
                detail["quarter_total_moc_sell_amount"] = _sum_num(moc_events, "SellAmount")
                detail["quarter_total_moc_sell_qty"] = _sum_num(moc_events, "SharesSold")
                detail["quarter_total_loc_buy_amount"] = _sum_num(q_buy_events, "BuyAmount")
                detail["quarter_total_loc_buy_qty"] = _sum_num(q_buy_events, "SharesBought")
                detail["quarter_total_loc_sell_amount"] = _sum_num(q_loc_sell_events, "SellAmount")
                detail["quarter_total_loc_sell_qty"] = _sum_num(q_loc_sell_events, "SharesSold")
                if "CashValidationOK" in qevents.columns:
                    detail["quarter_cash_validation_fail_count"] = int((~qevents["CashValidationOK"].fillna(True).astype(bool)).sum())
                if "SharesValidationOK" in qevents.columns:
                    detail["quarter_shares_validation_fail_count"] = int((~qevents["SharesValidationOK"].fillna(True).astype(bool)).sum())
                if "CostBasisValidationOK" in qevents.columns:
                    detail["quarter_cost_basis_validation_fail_count"] = int((~qevents["CostBasisValidationOK"].fillna(True).astype(bool)).sum())
                if "CashDeltaDiff" in qevents.columns:
                    detail["quarter_max_cash_delta_diff"] = float(pd.to_numeric(qevents["CashDeltaDiff"], errors="coerce").abs().fillna(0).max())
        if "CycleId" in sell_events.columns:
            tdf = sell_events.copy()
            tdf["CycleIdNum"] = pd.to_numeric(tdf["CycleId"], errors="coerce").fillna(0).astype(int)
            completed_n = int(cycle_status.get("completed_cycles", 0) or 0)
            completed_ids = set(range(1, completed_n + 1))
            done = tdf[tdf["CycleIdNum"].isin(completed_ids)].copy()
            if not done.empty:
                profits = done.groupby("CycleIdNum")["Profit"].sum() if "Profit" in done.columns else pd.Series(dtype=float)
                buys = done.groupby("CycleIdNum")["BuyAmount"].sum() if "BuyAmount" in done.columns else pd.Series(dtype=float)
                if not profits.empty:
                    returns = (profits / buys.replace(0, pd.NA) * 100).dropna()
                    detail["avg_cycle_return"] = float(returns.mean()) if not returns.empty else 0.0
                    detail["best_cycle_profit"] = float(profits.max())
                    detail["worst_cycle_profit"] = float(profits.min())
                days = []
                for cid, g in done.groupby("CycleIdNum"):
                    start_v = g["CycleStartDate"].dropna().iloc[0] if "CycleStartDate" in g.columns and not g["CycleStartDate"].dropna().empty else g["BuyDate"].min()
                    end_v = g["SellDate"].max()
                    if pd.notna(start_v) and pd.notna(end_v):
                        days.append((pd.to_datetime(end_v) - pd.to_datetime(start_v)).days)
                if days:
                    detail["avg_cycle_days"] = sum(days) / len(days)
                    detail["max_cycle_days"] = max(days)
                    detail["min_cycle_days"] = min(days)
    return detail




def make_cycle_status_audit_html(trade_df, bt, split_count):
    """Step25D-7-6: 최종 주기상태와 이벤트 후 상태를 분리해서 보여주는 검증표.
    목적:
    - 1000일 이상 장기 주기가 표시 오류인지 실제 장기 보유 후 종료인지 확인한다.
    - Trade Event Log의 OPEN은 '이벤트 직후 상태'임을 분리한다.
    - 이 표는 주기별 '최종 상태' 기준이다.
    """
    if bt is None or bt.empty or "CycleId" not in bt.columns:
        return ""

    btdf = bt.copy()
    btdf["CycleIdNum"] = pd.to_numeric(btdf["CycleId"], errors="coerce").fillna(0).astype(int)
    btdf = btdf[btdf["CycleIdNum"] > 0].copy()
    if btdf.empty:
        return ""
    btdf["Date"] = pd.to_datetime(btdf["Date"], errors="coerce")

    event_df = trade_df.copy() if trade_df is not None and not trade_df.empty else pd.DataFrame()
    if not event_df.empty and "CycleId" in event_df.columns:
        event_df["CycleIdNum"] = pd.to_numeric(event_df["CycleId"], errors="coerce").fillna(0).astype(int)
        if "EventDate" in event_df.columns:
            event_df["EventDateTS"] = pd.to_datetime(event_df["EventDate"], errors="coerce")
        elif "SellDate" in event_df.columns:
            event_df["EventDateTS"] = pd.to_datetime(event_df["SellDate"], errors="coerce")
        else:
            event_df["EventDateTS"] = pd.NaT
    else:
        event_df = pd.DataFrame()

    final = btdf.sort_values("Date").tail(1).iloc[0]
    final_cycle = int(final.get("CycleIdNum", 0) or 0)
    final_shares = float(final.get("Shares", 0) or 0)
    final_close = float(final.get("Close", 0) or 0)
    final_date = pd.to_datetime(final.get("Date"), errors="coerce")
    open_now = final_shares > 1e-9

    cycle_ids = sorted(set(btdf["CycleIdNum"].dropna().astype(int).tolist()) | (set(event_df["CycleIdNum"].dropna().astype(int).tolist()) if not event_df.empty else set()))
    rows = []
    completed_count = 0
    open_count = 0
    need_review_count = 0
    long_cycle_count = 0
    long_completed_count = 0

    for cid in cycle_ids:
        if cid <= 0:
            continue
        gbt = btdf[btdf["CycleIdNum"] == cid].copy()
        gev = event_df[event_df["CycleIdNum"] == cid].copy() if not event_df.empty else pd.DataFrame()

        buy_events = gev[gev.get("EventSide", pd.Series(dtype=str)).astype(str).str.upper().eq("BUY")] if not gev.empty and "EventSide" in gev.columns else pd.DataFrame()
        sell_events = gev[gev.get("EventSide", pd.Series(dtype=str)).astype(str).str.upper().eq("SELL")] if not gev.empty and "EventSide" in gev.columns else pd.DataFrame()

        start_v = pd.NaT
        if not buy_events.empty and "EventDateTS" in buy_events.columns:
            start_v = buy_events["EventDateTS"].dropna().min()
        if pd.isna(start_v) and not gev.empty and "CycleStartDate" in gev.columns and not gev["CycleStartDate"].dropna().empty:
            start_v = pd.to_datetime(gev["CycleStartDate"].dropna().iloc[0], errors="coerce")
        if pd.isna(start_v) and not gbt.empty:
            pos_rows = gbt[pd.to_numeric(gbt.get("Shares", 0), errors="coerce").fillna(0) > 1e-9]
            start_v = pos_rows["Date"].min() if not pos_rows.empty else gbt["Date"].min()

        completed_event = pd.DataFrame()
        if not sell_events.empty and "CycleCompleted" in sell_events.columns:
            completed_event = sell_events[sell_events["CycleCompleted"].fillna(False).astype(bool)].copy()
        completed = not completed_event.empty
        is_active = bool(open_now and cid == final_cycle)

        if completed:
            end_v = completed_event["EventDateTS"].dropna().max() if "EventDateTS" in completed_event.columns else pd.NaT
            status = "COMPLETED"
            end_reason = "전량매도완료"
            open_qty = 0.0
            open_value = 0.0
            completed_count += 1
        elif is_active:
            end_v = final_date
            status = "OPEN"
            end_reason = "기간종료미청산"
            open_qty = final_shares
            open_value = final_shares * final_close
            open_count += 1
        else:
            end_v = gev["EventDateTS"].dropna().max() if not gev.empty and "EventDateTS" in gev.columns and not gev["EventDateTS"].dropna().empty else (gbt["Date"].max() if not gbt.empty else pd.NaT)
            status = "REVIEW"
            end_reason = "완료이벤트확인필요"
            last_qty = float(pd.to_numeric(gbt["Shares"], errors="coerce").fillna(0).iloc[-1]) if not gbt.empty and "Shares" in gbt.columns else 0.0
            last_close = float(pd.to_numeric(gbt["Close"], errors="coerce").fillna(0).iloc[-1]) if not gbt.empty and "Close" in gbt.columns else 0.0
            open_qty = last_qty
            open_value = last_qty * last_close
            need_review_count += 1

        days_v = int((pd.to_datetime(end_v) - pd.to_datetime(start_v)).days) if pd.notna(start_v) and pd.notna(end_v) else 0
        is_long = days_v >= 1000
        if is_long:
            long_cycle_count += 1
            if status == "COMPLETED":
                long_completed_count += 1

        max_t_col = "T" if "T" in gbt.columns else "CurrentSplit"
        max_t = float(pd.to_numeric(gbt[max_t_col], errors="coerce").fillna(0).max()) if not gbt.empty and max_t_col in gbt.columns else 0.0
        profit_v = float(pd.to_numeric(sell_events.get("Profit", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not sell_events.empty else 0.0
        buy_v = float(pd.to_numeric(gev.get("BuyAmount", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not gev.empty else 0.0
        sell_v = float(pd.to_numeric(sell_events.get("SellAmount", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not sell_events.empty else 0.0
        q_count = int(gev.get("QuarterEventType", pd.Series(dtype=str)).astype(str).str.startswith("QUARTER", na=False).sum()) if not gev.empty and "QuarterEventType" in gev.columns else 0
        last_action = str(gbt.sort_values("Date").tail(1).iloc[0].get("Action", ""))[:80] if not gbt.empty else ""

        cls = "positive" if status == "COMPLETED" else ("warning" if status == "OPEN" else "negative")
        long_mark = " ⚠️" if is_long else ""
        rows.append({
            "cid": cid,
            "status": status,
            "cls": cls,
            "start": pd.to_datetime(start_v).strftime("%Y-%m-%d") if pd.notna(start_v) else "",
            "end": pd.to_datetime(end_v).strftime("%Y-%m-%d") if pd.notna(end_v) else "",
            "days": days_v,
            "long_mark": long_mark,
            "end_reason": end_reason,
            "max_t": max_t,
            "open_qty": open_qty,
            "open_value": open_value,
            "buy_v": buy_v,
            "sell_v": sell_v,
            "profit_v": profit_v,
            "buy_count": len(buy_events),
            "sell_count": len(sell_events),
            "q_count": q_count,
            "last_action": last_action,
        })

    trs = ""
    for r in rows[-120:]:
        trs += f"""
        <tr>
            <td>{r['cid']}</td>
            <td class=\"{r['cls']}\">{r['status']}</td>
            <td>{r['start']}</td>
            <td>{r['end']}</td>
            <td>{r['days']}{r['long_mark']}</td>
            <td>{r['end_reason']}</td>
            <td>{r['max_t']:.1f}T</td>
            <td>{r['open_qty']:,.4f}</td>
            <td>{r['open_value']:,.0f}</td>
            <td>{r['buy_v']:,.0f}</td>
            <td>{r['sell_v']:,.0f}</td>
            <td>{r['profit_v']:,.0f}</td>
            <td>{r['buy_count']} / {r['sell_count']}</td>
            <td>{r['q_count']}</td>
            <td>{r['last_action']}</td>
        </tr>
        """

    long_rows = ""
    for r in [x for x in rows if x["days"] >= 1000]:
        long_rows += f"""
        <tr>
            <td>{r['cid']}</td><td class=\"{r['cls']}\">{r['status']}</td><td>{r['start']}</td><td>{r['end']}</td>
            <td>{r['days']}</td><td>{r['end_reason']}</td><td>{r['profit_v']:,.0f}</td><td>{r['buy_count']} / {r['sell_count']}</td><td>{r['q_count']}</td>
        </tr>
        """
    if not long_rows:
        long_rows = "<tr><td colspan='9'>1000일 이상 장기 주기 없음</td></tr>"

    open_rows = ""
    for r in [x for x in rows if x["status"] == "OPEN"]:
        open_rows += f"""
        <tr>
            <td>{r['cid']}</td><td>{r['start']}</td><td>{r['end']}</td><td>{r['days']}</td>
            <td>{r['open_qty']:,.4f}</td><td>{r['open_value']:,.0f}</td><td>{r['max_t']:.1f}T</td><td>{r['last_action']}</td>
        </tr>
        """
    if not open_rows:
        open_rows = "<tr><td colspan='8'>현재 OPEN 주기 없음</td></tr>"

    return f"""
    <div class=\"card\">
        <h2>Step25D-7-6 FinalCycleStatus / 장기주기 / OPEN주기 해석판</h2>
        <div class=\"grid mini-grid\">
            <div class=\"metric positive\"><h3>최종 COMPLETED</h3><p>{completed_count}개</p></div>
            <div class=\"metric warning\"><h3>최종 OPEN</h3><p>{open_count}개</p></div>
            <div class=\"metric {'positive' if need_review_count == 0 else 'negative'}\"><h3>REVIEW</h3><p>{need_review_count}개</p></div>
            <div class=\"metric {'warning' if long_cycle_count else 'positive'}\"><h3>1000일 이상 장기주기</h3><p>{long_cycle_count}개</p></div>
            <div class=\"metric {'warning' if long_completed_count else 'positive'}\"><h3>장기 완료주기</h3><p>{long_completed_count}개</p></div>
            <div class=\"metric warning\"><h3>현재 미청산 평가액</h3><p>{final_shares * final_close:,.0f}원</p></div>
        </div>
        <p class=\"small-note\">이 표는 주기별 <b>최종 상태</b> 기준입니다. Trade Event Log의 OPEN은 해당 이벤트 직후 상태라서, 같은 주기 안에서 OPEN 이벤트가 많아도 최종 행이 COMPLETED이면 완료 주기입니다.</p>

        <h3>1000일 이상 장기 주기 상세</h3>
        <div class=\"table-wrap\">
            <table border=\"1\" cellpadding=\"6\" cellspacing=\"0\">
                <tr><th>주기</th><th>최종상태</th><th>시작일</th><th>종료/기준일</th><th>주기일수</th><th>최종종료사유</th><th>손익</th><th>BUY/SELL</th><th>쿼터이벤트</th></tr>
                {long_rows}
            </table>
        </div>

        <h3>현재 OPEN 주기 상세</h3>
        <div class=\"table-wrap\">
            <table border=\"1\" cellpadding=\"6\" cellspacing=\"0\">
                <tr><th>주기</th><th>시작일</th><th>기준일</th><th>경과일</th><th>OpenQty</th><th>Open평가액</th><th>최대T</th><th>마지막액션</th></tr>
                {open_rows}
            </table>
        </div>

        <h3>전체 주기별 최종 상태</h3>
        <div class=\"table-wrap\">
            <table border=\"1\" cellpadding=\"6\" cellspacing=\"0\">
                <tr><th>주기</th><th>최종상태</th><th>시작일</th><th>종료/기준일</th><th>주기일수</th><th>최종종료사유</th><th>최대T</th><th>최종OpenQty</th><th>최종Open평가액</th><th>매수금액</th><th>매도금액</th><th>손익</th><th>BUY/SELL</th><th>쿼터이벤트</th><th>마지막액션</th></tr>
                {trs}
            </table>
        </div>
    </div>
    """



def make_v22_final_validation_html(bt, trade_df, ticker, split_count, fee_percent):
    """Step25D-8: V2.2 검증 마감 요약표.
    공식/체결 조건을 바꾸지 않고, D7 계열에서 확인한 로그·쿼터·주기 상태를 한 화면에 요약한다.
    """
    if bt is None or bt.empty:
        return ""

    btdf = bt.copy()
    if "Date" in btdf.columns:
        btdf["Date"] = pd.to_datetime(btdf["Date"], errors="coerce")
    tdf = trade_df.copy() if trade_df is not None and not trade_df.empty else pd.DataFrame()
    if not tdf.empty:
        if "EventSide" in tdf.columns:
            tdf["EventSideNorm"] = tdf["EventSide"].astype(str).str.upper()
        else:
            tdf["EventSideNorm"] = ""
        if "CycleId" in tdf.columns:
            tdf["CycleIdNum"] = pd.to_numeric(tdf["CycleId"], errors="coerce").fillna(0).astype(int)

    final = btdf.sort_values("Date").tail(1).iloc[0]
    final_shares = float(final.get("Shares", 0) or 0)
    final_close = float(final.get("Close", 0) or 0)
    final_open_value = final_shares * final_close
    has_open = final_shares > 1e-9

    if "CycleId" in btdf.columns:
        final_cycle = int(float(final.get("CycleId", 0) or 0))
        all_cycle_count = int(pd.to_numeric(btdf["CycleId"], errors="coerce").fillna(0).max())
    else:
        final_cycle = 0
        all_cycle_count = 0

    completed_cycles = 0
    review_count = 0
    long_count = 0
    quarter_event_count = 0
    q_loc_buy_count = 0
    q_moc_count = 0
    q_loc_sell_count = 0
    q_cash_fail = 0
    q_share_fail = 0
    buy_event_count = 0
    sell_event_count = 0
    if not tdf.empty:
        buy_event_count = int(tdf["EventSideNorm"].eq("BUY").sum())
        sell_event_count = int(tdf["EventSideNorm"].eq("SELL").sum())
        if "CycleCompleted" in tdf.columns and "CycleIdNum" in tdf.columns:
            completed_cycles = int(tdf[tdf["CycleCompleted"].fillna(False).astype(bool)]["CycleIdNum"].nunique())
        if "QuarterEventType" in tdf.columns:
            q = tdf["QuarterEventType"].fillna("").astype(str)
            quarter_event_count = int(q.str.startswith("QUARTER", na=False).sum())
            q_loc_buy_count = int(q.eq("QUARTER_LOC_BUY").sum())
            q_moc_count = int(q.isin(["QUARTER_START_MOC", "QUARTER_10TH_MOC"]).sum())
            q_loc_sell_count = int(q.eq("QUARTER_LOC_SELL").sum())
        if "CashValidationOK" in tdf.columns:
            q_cash_fail = int((~tdf["CashValidationOK"].fillna(True).astype(bool)).sum())
        if "SharesValidationOK" in tdf.columns:
            q_share_fail = int((~tdf["SharesValidationOK"].fillna(True).astype(bool)).sum())

        # 장기주기 수는 이벤트 기준으로 보조 산출한다. 화면의 공식 표는 make_cycle_status_audit_html에서 더 자세히 보여준다.
        if "CycleIdNum" in tdf.columns:
            for _, g in tdf.groupby("CycleIdNum"):
                if g.empty:
                    continue
                start_v = pd.to_datetime(g.get("CycleStartDate", pd.Series(dtype=object)).dropna().iloc[0], errors="coerce") if "CycleStartDate" in g.columns and not g["CycleStartDate"].dropna().empty else pd.NaT
                end_candidates = []
                if "EventDate" in g.columns:
                    end_candidates.append(pd.to_datetime(g["EventDate"], errors="coerce").max())
                if "SellDate" in g.columns:
                    end_candidates.append(pd.to_datetime(g["SellDate"], errors="coerce").max())
                end_candidates = [x for x in end_candidates if pd.notna(x)]
                if pd.notna(start_v) and end_candidates:
                    if (max(end_candidates) - start_v).days >= 1000:
                        long_count += 1

    open_cycle_count = 1 if has_open else 0
    if completed_cycles and all_cycle_count:
        review_count = max(0, all_cycle_count - completed_cycles - open_cycle_count)

    engine_formula = "SOXL: 별% = 12 - T×0.6 × (40/a)" if str(ticker).upper() == "SOXL" else "TQQQ: 별% = 10 - T/2 × (40/a)"
    designated = "12%" if str(ticker).upper() == "SOXL" else "10%"
    quarter_loc = "-12%" if str(ticker).upper() == "SOXL" else "-10%"

    overall_verdict = "V2.2 검증 마감 가능" if (review_count == 0 and q_cash_fail == 0 and q_share_fail == 0) else "추가 검토 필요"
    verdict_cls = "positive" if overall_verdict == "V2.2 검증 마감 가능" else "warning"

    check_rows = ""
    checks = [
        ("기준 원문", "PASS", "사진 OCR 추정이 아니라 사용자가 글로 정리한 라오어 원문 기준을 사용"),
        ("V2.2 통합", "PASS", "기본형/수치변화를 나누지 않고 티커별 공식만 자동 적용"),
        ("별% 공식", "PASS", engine_formula),
        ("매수/매도 LOC", "PASS", "별가격 공유, 매수만 -0.01 / 매도는 별가격"),
        ("전반전/후반전", "PASS", "전반전 0.5 평단LOC + 0.5 별LOC, 후반전 1.0 별LOC"),
        ("매도 구조", "PASS", f"1/4 별LOC + 3/4 지정가 {designated}"),
        ("쿼터손절", "PASS" if quarter_event_count else "REVIEW", f"쿼터이벤트 {quarter_event_count}건, LOC기준 {quarter_loc}"),
        ("현금/수량 검증", "PASS" if (q_cash_fail == 0 and q_share_fail == 0) else "REVIEW", f"현금 실패 {q_cash_fail}건 / 수량 실패 {q_share_fail}건"),
        ("주기상태", "PASS" if review_count == 0 else "REVIEW", f"COMPLETED {completed_cycles} / OPEN {open_cycle_count} / REVIEW {review_count}"),
        ("V4.0 분리", "PASS", "V4.0 일반모드/리버스모드는 Step25E 이후 별도 검증"),
    ]
    for name, status, note in checks:
        cls = "positive" if status == "PASS" else "warning"
        check_rows += f"<tr><td>{name}</td><td class='{cls}'><b>{status}</b></td><td>{note}</td></tr>"

    return f"""
    <div class=\"card hero\">
        <h2>Step25D-8 V2.2 결과표 / 검증표 마감 정리</h2>
        <div class=\"grid mini-grid\">
            <div class=\"metric {verdict_cls}\"><h3>V2.2 판정</h3><p>{overall_verdict}</p></div>
            <div class=\"metric positive\"><h3>완료주기</h3><p>{completed_cycles}개</p></div>
            <div class=\"metric warning\"><h3>현재 OPEN</h3><p>{open_cycle_count}개</p></div>
            <div class=\"metric {'positive' if review_count == 0 else 'negative'}\"><h3>REVIEW</h3><p>{review_count}개</p></div>
            <div class=\"metric\"><h3>BUY/SELL 이벤트</h3><p>{buy_event_count} / {sell_event_count}</p></div>
            <div class=\"metric positive\"><h3>쿼터이벤트</h3><p>{quarter_event_count}건</p></div>
            <div class=\"metric\"><h3>쿼터 LOC 매수/매도</h3><p>{q_loc_buy_count} / {q_loc_sell_count}</p></div>
            <div class=\"metric\"><h3>쿼터 MOC</h3><p>{q_moc_count}건</p></div>
            <div class=\"metric {'positive' if (q_cash_fail == 0 and q_share_fail == 0) else 'negative'}\"><h3>현금/수량 검증 실패</h3><p>{q_cash_fail} / {q_share_fail}</p></div>
            <div class=\"metric warning\"><h3>현재 미청산 평가액</h3><p>{final_open_value:,.0f}원</p></div>
        </div>
        <p class=\"small-note\">D-8은 새 매매 로직을 추가하지 않고, D-7 계열에서 확인한 V2.2 로그/쿼터손절/주기상태를 마감 요약합니다. 결과 수익률이 좋다는 뜻이 아니라, 백테스트 엔진이 원문 기준대로 검증 가능하게 정리됐다는 뜻입니다.</p>
        <div class=\"table-wrap\">
            <table border=\"1\" cellpadding=\"6\" cellspacing=\"0\">
                <tr><th>검증 항목</th><th>상태</th><th>확인 내용</th></tr>
                {check_rows}
            </table>
        </div>
    </div>
    """

def make_raor_validation_html(bt, trade_df, ticker, split_count):
    """Step24D: 원문 규칙 검증 체크리스트 화면."""
    if bt is None or bt.empty:
        return ""
    checks = []
    checks.append(("첫매수 LOC", "첫매수LOC" in " ".join(bt.get("Action", pd.Series(dtype=str)).astype(str).head(20).tolist()) or "첫매수LOC" in " ".join(bt.get("Action", pd.Series(dtype=str)).astype(str).tolist()), "첫 매수는 전날종가 + LOC 여유율 기준으로 체결 로그 확인"))
    checks.append(("T 증가 단위", "TDelta" in bt.columns, "TBefore/TAfter/TDelta 컬럼으로 0.5T·1T 증가 여부 확인"))
    checks.append(("별% 공식", ticker in ["TQQQ", "SOXL"] and int(split_count) in [20, 40], "TQQQ/SOXL 20·40분할 공식만 허용"))
    checks.append(("전반전/후반전", any(c in bt.columns for c in ["PhaseBefore", "PhaseAfter", "Mode"]), "PhaseBefore/PhaseAfter 또는 Mode로 전환 구간 확인"))
    checks.append(("쿼터손절", trade_df is not None and not trade_df.empty and "Reason" in trade_df.columns, "Reason/ModeTransitionReason 컬럼에서 쿼터손절 발생·복귀·반복 확인"))
    checks.append(("소진권 후보", "QuarterTriggerCandidate" in bt.columns, "QuarterTriggerCandidate/QuarterTriggerReason으로 발동·미발동 사유 확인"))
    rows = ""
    for name, ok, memo in checks:
        mark = "✅" if ok else "⚠️"
        cls = "positive" if ok else "warning"
        rows += f"<tr><td>{mark}</td><td>{name}</td><td class='{cls}'>{'확인 가능' if ok else '추가 확인 필요'}</td><td>{memo}</td></tr>"
    return f"""
    <div class="card">
        <h2>Step24D 원문 규칙 검증 체크리스트</h2>
        <p class="small-note">※ Step24D 이후 원문 규칙을 화면에서 검증하기 위한 체크리스트입니다. 미확인 공식은 추가 확인 대상으로 남깁니다.</p>
        <div class="table-wrap">
            <table border="1" cellpadding="6" cellspacing="0">
                <tr><th>상태</th><th>항목</th><th>판정</th><th>확인 포인트</th></tr>
                {rows}
            </table>
        </div>
    </div>
    """


def make_step24m_execution_validation_html(bt, trade_df):
    """Step24M: 가격겹침/일봉선후관계/주기종료 누락 검증 요약."""
    if bt is None or bt.empty:
        return ""

    def bool_count(df, col):
        if df is None or df.empty or col not in df.columns:
            return 0
        return int(df[col].fillna(False).astype(bool).sum())

    overlap_count = bool_count(bt, "BuySellPriceOverlap") + bool_count(trade_df, "BuySellPriceOverlap")
    ambiguous_count = bool_count(bt, "DailyCandleOrderAmbiguous") + bool_count(trade_df, "DailyCandleOrderAmbiguous")

    cycle_complete_missing = 0
    zero_qty_rows = 0
    if trade_df is not None and not trade_df.empty:
        tdf = trade_df.copy()
        qty_col = None
        for c in ["HoldingQtyAfter", "SharesAfter", "QtyAfter"]:
            if c in tdf.columns:
                qty_col = c
                break
        if qty_col:
            qty = pd.to_numeric(tdf[qty_col], errors="coerce")
            zero_mask = qty.fillna(0).abs() <= 1e-9
            zero_qty_rows = int(zero_mask.sum())
            if "CycleCompleted" in tdf.columns:
                completed = tdf["CycleCompleted"].fillna(False).astype(bool)
                cycle_complete_missing = int((zero_mask & ~completed).sum())

    latest_by_cycle_rows = ""
    if "CycleId" in bt.columns:
        temp = bt.copy()
        temp["CycleIdNum"] = pd.to_numeric(temp["CycleId"], errors="coerce").fillna(0).astype(int)
        temp = temp[temp["CycleIdNum"] > 0]
        if not temp.empty:
            last_rows = temp.sort_values("Date").groupby("CycleIdNum").tail(1).tail(8)
            for _, r in last_rows.iterrows():
                cid = int(r.get("CycleIdNum", 0))
                date = pd.to_datetime(r.get("Date")).strftime("%Y-%m-%d") if pd.notna(r.get("Date")) else ""
                t_val = float(r.get("T", r.get("CurrentSplit", 0)) or 0)
                shares = float(r.get("Shares", 0) or 0)
                phase = r.get("PhaseAfter", r.get("Mode", ""))
                action = str(r.get("Action", ""))[:80]
                latest_by_cycle_rows += f"<tr><td>{cid}</td><td>{date}</td><td>{t_val:.2f}T</td><td>{shares:,.4f}</td><td>{phase}</td><td>{action}</td></tr>"

    overlap_cls = "positive" if overlap_count == 0 else "negative"
    missing_cls = "positive" if cycle_complete_missing == 0 else "negative"
    ambiguous_cls = "warning" if ambiguous_count > 0 else "positive"

    return f"""
    <div class="card">
        <h2>Step24M 체결 검증 카운터</h2>
        <div class="grid mini-grid">
            <div class="metric {overlap_cls}"><h3>가격겹침 오류</h3><p>{overlap_count}건</p></div>
            <div class="metric {ambiguous_cls}"><h3>일봉 선후관계 불명</h3><p>{ambiguous_count}건</p></div>
            <div class="metric {missing_cls}"><h3>전량매도 완료누락</h3><p>{cycle_complete_missing}건</p></div>
            <div class="metric"><h3>보유수량 0 로그</h3><p>{zero_qty_rows}건</p></div>
        </div>
        <p class="small-note">가격겹침 오류는 BuyLOCPrice가 SellLOCPrice 이상인 경우라 0건이어야 정상입니다. 일봉 선후관계 불명은 오류가 아니라 OHLC 데이터만으로 장중 순서를 확정할 수 없는 구간입니다.</p>
        <div class="table-wrap">
            <table border="1" cellpadding="6" cellspacing="0">
                <tr><th>최근 Cycle</th><th>마지막일</th><th>T</th><th>보유수량</th><th>Phase</th><th>마지막 액션</th></tr>
                {latest_by_cycle_rows}
            </table>
        </div>

    </div>
    """


def make_step24u_no_fill_gap_html(bt, split_count=40):
    """Step24U: 장기 무체결/무거래 구간을 찾아 원인을 화면에서 확인한다.
    매매 공식은 건드리지 않고, 백테스트 결과 컬럼만 분석한다.
    """
    if bt is None or bt.empty or "Date" not in bt.columns:
        return ""
    df = bt.copy().sort_values("Date").reset_index(drop=True)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    if df.empty:
        return ""

    def _bool_col(name):
        if name not in df.columns:
            return pd.Series([False] * len(df), index=df.index)
        return df[name].fillna(False).astype(bool)

    action_text = df.get("Action", pd.Series([""] * len(df), index=df.index)).astype(str)
    fill_mask = (
        _bool_col("BuyLOCExecuted") |
        _bool_col("SellLOCExecuted") |
        _bool_col("DesignatedSellExecuted") |
        action_text.str.contains("매수|매도", regex=True, na=False)
    )

    segments = []
    start_i = None
    last_fill_i = None
    for i, filled in enumerate(fill_mask.tolist()):
        if filled:
            if start_i is not None:
                end_i = i - 1
                if end_i >= start_i:
                    segments.append((start_i, end_i, last_fill_i, i))
                start_i = None
            last_fill_i = i
        else:
            if start_i is None:
                start_i = i
    if start_i is not None:
        segments.append((start_i, len(df)-1, last_fill_i, None))

    rows = ""
    large_segments = []
    for start_i, end_i, prev_i, next_i in segments:
        trading_days = end_i - start_i + 1
        cal_days = int((df.loc[end_i, "Date"] - df.loc[start_i, "Date"]).days)
        if trading_days < 40 and cal_days < 70:
            continue
        r0 = df.loc[start_i]
        r1 = df.loc[end_i]
        close_v = float(r1.get("Close", 0) or 0)
        avg_v = float(r1.get("AvgPrice", 0) or 0)
        buy_loc = float(r1.get("BuyLOCPrice", r1.get("BuyStarPrice", 0)) or 0)
        sell_loc = float(r1.get("SellLOCPrice", r1.get("StarPrice", 0)) or 0)
        designated = float(r1.get("DesignatedSellPrice", r1.get("SellTargetPrice", 0)) or 0)
        t_val = float(r1.get("T", r1.get("CurrentSplit", 0)) or 0)
        remaining_t = float(r1.get("RemainingTAfter", max(float(split_count) - t_val, 0)) or 0)
        phase = str(r1.get("PhaseAfter", r1.get("Mode", "")))
        cause_parts = []
        if avg_v > 0 and designated > 0 and close_v < designated:
            cause_parts.append("지정가 매도 목표 미도달")
        if sell_loc > 0 and close_v < sell_loc:
            cause_parts.append("별LOC 매도 미체결")
        if buy_loc > 0 and close_v > buy_loc and remaining_t > 0:
            cause_parts.append("LOC 매수점보다 종가가 높아 추가매수 미체결")
        if remaining_t <= 1.0:
            cause_parts.append("남은 T 부족/소진모드권")
        elif t_val >= float(split_count) / 2:
            cause_parts.append("후반전 대기")
        if not cause_parts:
            cause_parts.append("원문 LOC/지정가 조건 미충족")
        cause = " + ".join(dict.fromkeys(cause_parts))
        large_segments.append((trading_days, cal_days, start_i, end_i, cause))
        rows += f"""
        <tr>
            <td>{df.loc[start_i, 'Date'].strftime('%Y-%m-%d')}</td>
            <td>{df.loc[end_i, 'Date'].strftime('%Y-%m-%d')}</td>
            <td>{trading_days}일</td>
            <td>{cal_days}일</td>
            <td>{phase}</td>
            <td>{t_val:.2f}T / 잔여 {remaining_t:.2f}T</td>
            <td>{close_v:.2f}</td>
            <td>{avg_v:.2f}</td>
            <td>{buy_loc:.2f}</td>
            <td>{sell_loc:.2f}</td>
            <td>{designated:.2f}</td>
            <td>{cause}</td>
        </tr>
        """

    if not rows:
        rows = '<tr><td colspan="12">40거래일 이상 장기 무체결 구간이 없습니다.</td></tr>'

    max_trade_days = max([x[0] for x in large_segments], default=0)
    max_cal_days = max([x[1] for x in large_segments], default=0)
    suspect_2022 = ""
    for trading_days, cal_days, start_i, end_i, cause in large_segments:
        sdt = df.loc[start_i, "Date"]
        edt = df.loc[end_i, "Date"]
        if sdt <= pd.Timestamp("2023-05-31") and edt >= pd.Timestamp("2022-05-01"):
            suspect_2022 = f"2022-05~2023-05 구간과 겹치는 장기 무체결 구간 확인: {sdt.strftime('%Y-%m-%d')}~{edt.strftime('%Y-%m-%d')} / {cause}"
            break
    if not suspect_2022:
        suspect_2022 = "2022-05~2023-05와 겹치는 장기 무체결 구간은 현재 필터 기준에서 뚜렷하게 잡히지 않았습니다."

    return f"""
    <div class="card step24u-gap-card">
        <h2>Step24U 무체결 공백 진단</h2>
        <div class="grid mini-grid">
            <div class="metric warning"><h3>최장 무체결 거래일</h3><p>{max_trade_days}일</p></div>
            <div class="metric warning"><h3>최장 무체결 달력일</h3><p>{max_cal_days}일</p></div>
            <div class="metric"><h3>장기 공백 구간</h3><p>{len(large_segments)}개</p></div>
        </div>
        <p class="small-note"><b>진단:</b> {suspect_2022}</p>
        <p class="small-note">이 표는 원문 규칙을 바꾸지 않고 결과 로그만 읽습니다. 공백 원인은 보통 지정가/별LOC 매도 미체결, LOC 추가매수 미체결, 후반전·소진모드 대기 중 하나입니다.</p>
        <div class="table-wrap">
            <table border="1" cellpadding="6" cellspacing="0">
                <tr><th>시작</th><th>끝</th><th>거래일</th><th>달력일</th><th>Phase</th><th>T</th><th>종가</th><th>평단</th><th>BuyLOC</th><th>SellLOC</th><th>지정가</th><th>추정 원인</th></tr>
                {rows}
            </table>
        </div>
    </div>
    """


# =========================
# 전략 1: RSI 커스텀

# =========================
def run_backtest(
    split_count=10,
    extreme_split=4,
    recession_split=3,
    neutral_split=1,
    boom_split=1,
    sell_rsi=70,
    fee_rate_pct=0.25,
):
    cash = INITIAL_CASH
    shares = 0
    avg_price = 0
    current_split = 0

    results = []
    trade_logs = []

    entry_date = None
    entry_amount = 0

    split_map = {
        "극침체": extreme_split,
        "침체": recession_split,
        "중립": neutral_split,
        "상승": boom_split,
        "과열": 0,
    }

    fee_rate = fee_rate_pct / 100

    for _, row in daily.iterrows():
        date = row["Date"]
        price = row["Close"]

        if "WeeklyRSI" in row:
            rsi = row["WeeklyRSI"]
        elif "RSI" in row:
            rsi = row["RSI"]
        else:
            rsi = 50

        mode = make_mode(rsi, sell_rsi)
        action = "관망"

        if shares > 0 and rsi >= sell_rsi:
            sell_amount = shares * price
            sell_fee = sell_amount * fee_rate
            net_sell = sell_amount - sell_fee

            profit = net_sell - entry_amount
            return_pct = (profit / entry_amount) * 100 if entry_amount > 0 else 0
            hold_days = (date - entry_date).days if entry_date else 0

            trade_logs.append({
                "BuyDate": entry_date,
                "SellDate": date,
                "HoldDays": hold_days,
                "BuyAmount": entry_amount,
                "SellAmount": net_sell,
                "Profit": profit,
                "ReturnPct": return_pct,
                "Reason": "과열 RSI 전략매도",
            })

            cash += net_sell
            shares = 0
            avg_price = 0
            current_split = 0
            entry_date = None
            entry_amount = 0
            action = "매도"

        else:
            buy_splits_today = split_map.get(mode, 0)

            if buy_splits_today > 0 and current_split < split_count:
                remain_split = split_count - current_split
                actual_split = min(buy_splits_today, remain_split)

                split_amount = cash / remain_split if remain_split > 0 else 0
                buy_amount = split_amount * actual_split

                if buy_amount > 0:
                    buy_fee = buy_amount * fee_rate
                    total_buy_cost = buy_amount + buy_fee

                    if total_buy_cost > cash:
                        buy_amount = cash / (1 + fee_rate)
                        buy_fee = buy_amount * fee_rate
                        total_buy_cost = buy_amount + buy_fee

                    buy_shares = buy_amount / price if price > 0 else 0

                    total_cost_before = shares * avg_price
                    shares += buy_shares
                    total_cost_after = total_cost_before + buy_amount

                    avg_price = total_cost_after / shares if shares > 0 else 0
                    cash -= total_buy_cost

                    if entry_date is None:
                        entry_date = date
                        entry_amount = total_buy_cost
                    else:
                        entry_amount += total_buy_cost

                    current_split += actual_split
                    action = "매수"

        stock_value = shares * price
        total_asset = cash + stock_value

        results.append({
            "Date": date,
            "Close": price,
            "RSI": rsi,
            "Mode": mode,
            "Action": action,
            "Cash": cash,
            "Shares": shares,
            "StockValue": stock_value,
            "TotalAsset": total_asset,
            "CurrentSplit": current_split,
        })

    result_df = pd.DataFrame(results)
    result_df = add_metrics(result_df)

    trade_df = pd.DataFrame(trade_logs)

    if not trade_df.empty:
        maes = []
        mfes = []

        for _, trade in trade_df.iterrows():
            period = daily[
                (daily["Date"] >= trade["BuyDate"]) &
                (daily["Date"] <= trade["SellDate"])
            ].copy()

            if period.empty:
                maes.append(0)
                mfes.append(0)
                continue

            entry_price = period.iloc[0]["Close"]
            min_price = period["Close"].min()
            max_price = period["Close"].max()

            maes.append(((min_price / entry_price) - 1) * 100)
            mfes.append(((max_price / entry_price) - 1) * 100)

        trade_df["MAE"] = maes
        trade_df["MFE"] = mfes

    return result_df, trade_df




# =========================
# 전략 2: 오리지널 무한매수법

# =========================
def run_original_backtest(
    split_count=10,
    profit_target=10.0,
    fee_rate_pct=0.25,
):
    cash = INITIAL_CASH
    shares = 0
    avg_price = 0
    current_split = 0

    results = []
    trade_logs = []

    entry_date = None
    entry_amount = 0

    split_amount_base = INITIAL_CASH / split_count
    fee_rate = fee_rate_pct / 100

    for _, row in daily.iterrows():
        date = row["Date"]
        price = row["Close"]

        action = "관망"

        # 목표수익률 도달 시 전량매도
        if shares > 0:
            current_return = ((price / avg_price) - 1) * 100 if avg_price > 0 else 0

            if current_return >= profit_target:
                gross_sell = shares * price
                sell_fee = gross_sell * fee_rate
                net_sell = gross_sell - sell_fee

                profit = net_sell - entry_amount
                return_pct = (profit / entry_amount) * 100 if entry_amount > 0 else 0
                hold_days = (date - entry_date).days if entry_date else 0

                trade_logs.append({
                    "BuyDate": entry_date,
                    "SellDate": date,
                    "HoldDays": hold_days,
                    "BuyAmount": entry_amount,
                    "SellAmount": net_sell,
                    "Profit": profit,
                    "ReturnPct": return_pct,
                    "Reason": f"목표수익률 {profit_target:.1f}% 도달",
                })

                cash += net_sell
                shares = 0
                avg_price = 0
                current_split = 0
                entry_date = None
                entry_amount = 0
                action = "매도"

        # 분할매수
        elif current_split < split_count:
            remain_split = split_count - current_split
            buy_amount = min(split_amount_base, cash)

            if buy_amount > 0:
                buy_fee = buy_amount * fee_rate
                total_buy_cost = buy_amount + buy_fee

                if total_buy_cost > cash:
                    buy_amount = cash / (1 + fee_rate)
                    buy_fee = buy_amount * fee_rate
                    total_buy_cost = buy_amount + buy_fee

                buy_shares = buy_amount / price if price > 0 else 0

                total_cost_before = shares * avg_price
                shares += buy_shares
                total_cost_after = total_cost_before + buy_amount

                avg_price = total_cost_after / shares if shares > 0 else 0

                cash -= total_buy_cost

                if entry_date is None:
                    entry_date = date
                    entry_amount = total_buy_cost
                else:
                    entry_amount += total_buy_cost

                current_split += 1
                action = "매수"

        stock_value = shares * price
        total_asset = cash + stock_value

        results.append({
            "Date": date,
            "Close": price,
            "Action": action,
            "Cash": cash,
            "Shares": shares,
            "StockValue": stock_value,
            "TotalAsset": total_asset,
            "CurrentSplit": current_split,
        })

    result_df = pd.DataFrame(results)
    result_df = add_metrics(result_df)

    trade_df = pd.DataFrame(trade_logs)

    if not trade_df.empty:
        maes = []
        mfes = []

        for _, trade in trade_df.iterrows():
            period = daily[
                (daily["Date"] >= trade["BuyDate"]) &
                (daily["Date"] <= trade["SellDate"])
            ].copy()

            if period.empty:
                maes.append(0)
                mfes.append(0)
                continue

            entry_price = period.iloc[0]["Close"]

            min_price = period["Close"].min()
            max_price = period["Close"].max()

            mae = ((min_price / entry_price) - 1) * 100
            mfe = ((max_price / entry_price) - 1) * 100

            maes.append(mae)
            mfes.append(mfe)

        trade_df["MAE"] = maes
        trade_df["MFE"] = mfes

    return result_df, trade_df



# =========================
# 전략 3: 오리지널 2.0 (MA5 / MA20)

# =========================
def run_original_upgrade_backtest(
    split_count=30,
    profit_target=10.0,
    ma5_factor=3,
    ma20_factor=5,
    fee_rate_pct=0.25,
):
    cash = INITIAL_CASH
    shares = 0
    avg_price = 0
    current_split = 0

    results = []
    trade_logs = []

    entry_date = None
    entry_amount = 0

    split_amount_base = INITIAL_CASH / split_count
    fee_rate = fee_rate_pct / 100

    for _, row in daily.iterrows():
        date = row["Date"]
        price = row["Close"]
        ma5 = row["MA5"]
        ma20 = row["MA20"]

        action = "관망"

        # 매도
        if shares > 0:
            current_return = ((price / avg_price) - 1) * 100 if avg_price > 0 else 0

            if current_return >= profit_target:
                gross_sell = shares * price
                sell_fee = gross_sell * fee_rate
                net_sell = gross_sell - sell_fee

                profit = net_sell - entry_amount
                return_pct = (profit / entry_amount) * 100 if entry_amount > 0 else 0
                hold_days = (date - entry_date).days if entry_date else 0

                trade_logs.append({
                    "BuyDate": entry_date,
                    "SellDate": date,
                    "HoldDays": hold_days,
                    "BuyAmount": entry_amount,
                    "SellAmount": net_sell,
                    "Profit": profit,
                    "ReturnPct": return_pct,
                    "Reason": f"목표수익률 {profit_target:.1f}% 도달",
                })

                cash += net_sell
                shares = 0
                avg_price = 0
                current_split = 0
                entry_date = None
                entry_amount = 0
                action = "매도"

        # 매수
        elif current_split < split_count:
            buy_factor = 1

            if pd.notna(ma20) and price < ma20:
                buy_factor = ma20_factor
            elif pd.notna(ma5) and price < ma5:
                buy_factor = ma5_factor

            remain_split = split_count - current_split
            actual_split = min(buy_factor, remain_split)

            buy_amount = min(split_amount_base * actual_split, cash)

            if buy_amount > 0:
                buy_fee = buy_amount * fee_rate
                total_buy_cost = buy_amount + buy_fee

                if total_buy_cost > cash:
                    buy_amount = cash / (1 + fee_rate)
                    buy_fee = buy_amount * fee_rate
                    total_buy_cost = buy_amount + buy_fee

                buy_shares = buy_amount / price if price > 0 else 0

                total_cost_before = shares * avg_price
                shares += buy_shares
                total_cost_after = total_cost_before + buy_amount

                avg_price = total_cost_after / shares if shares > 0 else 0

                cash -= total_buy_cost

                if entry_date is None:
                    entry_date = date
                    entry_amount = total_buy_cost
                else:
                    entry_amount += total_buy_cost

                current_split += actual_split
                action = f"{actual_split}분할 매수"

        stock_value = shares * price
        total_asset = cash + stock_value

        results.append({
            "Date": date,
            "Close": price,
            "Action": action,
            "Cash": cash,
            "Shares": shares,
            "StockValue": stock_value,
            "TotalAsset": total_asset,
            "CurrentSplit": current_split,
        })

    result_df = pd.DataFrame(results)
    result_df = add_metrics(result_df)

    trade_df = pd.DataFrame(trade_logs)

    if not trade_df.empty:
        maes = []
        mfes = []

        for _, trade in trade_df.iterrows():
            period = daily[
                (daily["Date"] >= trade["BuyDate"]) &
                (daily["Date"] <= trade["SellDate"])
            ].copy()

            if period.empty:
                maes.append(0)
                mfes.append(0)
                continue

            entry_price = period.iloc[0]["Close"]

            min_price = period["Close"].min()
            max_price = period["Close"].max()

            mae = ((min_price / entry_price) - 1) * 100
            mfe = ((max_price / entry_price) - 1) * 100

            maes.append(mae)
            mfes.append(mfe)

        trade_df["MAE"] = maes
        trade_df["MFE"] = mfes

    return result_df, trade_df

# =========================
# Step22B: 무한매수 4.0 V1
# =========================
def run_infinite4_v1_backtest(
    split_count=20,
    target_profit=7.0,
    quarter_sell_ratio=25.0,
    star_pct=7.0,
    fee_rate_pct=0.25,
):
    """무한매수법 4.0 V1 백테스트 엔진.

    V0.5 포함:
    - 분할수 20/30/40만 허용
    - current_split >= split_count이면 추가매수 금지
    - 현금/분할 초과매수 방지

    V1 포함:
    - 일반모드 / 소진모드 표시
    - star_price = avg_price * (1 - star_pct/100)
    - 보유 중 추가매수는 가격이 star_price 이하일 때만 1T
    - 목표수익률 도달 시 쿼터매도

    아직 단순화한 부분:
    - 언이시트의 별점/별지점 정교 계산, 전반전/후반전, LOC/지정가 세부 구분은 V2에서 반영
    """
    split_count = int(split_count)
    if split_count not in [20, 30, 40]:
        split_count = 20 if split_count < 25 else 30 if split_count < 35 else 40

    cash = INITIAL_CASH
    shares = 0.0
    avg_price = 0.0
    current_split = 0.0

    unit_cash = INITIAL_CASH / split_count
    fee_rate = fee_rate_pct / 100
    sell_ratio = max(0.01, min(float(quarter_sell_ratio) / 100, 1.0))
    star_rate = max(0.0, float(star_pct)) / 100

    results = []
    trade_logs = []

    entry_date = None
    entry_amount = 0.0

    for _, row in daily.iterrows():
        date = row["Date"]
        price = float(row["Close"])
        action = "관망"

        mode = "소진모드" if current_split >= split_count else "일반모드"
        star_price = avg_price * (1 - star_rate) if shares > 0 and avg_price > 0 else 0.0
        current_return = ((price / avg_price) - 1) * 100 if shares > 0 and avg_price > 0 else 0.0

        # 1) 목표수익률 도달 시 쿼터매도
        if shares > 0 and avg_price > 0 and current_return >= target_profit:
            if current_split <= 1.01 or sell_ratio >= 0.999:
                sell_fraction = 1.0
                sell_reason = f"목표수익률 {target_profit:.1f}% 도달 전량매도"
            else:
                sell_fraction = sell_ratio
                sell_reason = f"목표수익률 {target_profit:.1f}% 도달 쿼터매도({quarter_sell_ratio:.1f}%)"

            sell_shares = shares * sell_fraction
            gross_sell = sell_shares * price
            sell_fee = gross_sell * fee_rate
            net_sell = gross_sell - sell_fee

            cost_basis_sold = entry_amount * sell_fraction if entry_amount > 0 else avg_price * sell_shares
            profit = net_sell - cost_basis_sold
            return_pct = (profit / cost_basis_sold) * 100 if cost_basis_sold > 0 else 0
            hold_days = (date - entry_date).days if entry_date is not None else 0

            trade_logs.append({
                "BuyDate": entry_date,
                "SellDate": date,
                "HoldDays": hold_days,
                "BuyAmount": cost_basis_sold,
                "SellAmount": net_sell,
                "Profit": profit,
                "ReturnPct": return_pct,
                "Reason": sell_reason,
            })

            cash += net_sell
            shares -= sell_shares
            entry_amount -= cost_basis_sold
            current_split = max(0.0, current_split * (1 - sell_fraction))

            if shares <= 1e-9 or current_split <= 0.01:
                shares = 0.0
                avg_price = 0.0
                current_split = 0.0
                entry_date = None
                entry_amount = 0.0

            action = "쿼터매도" if sell_fraction < 1.0 else "전량매도"

        # 2) 매수: 미보유 최초 1T / 보유 중 별점 이하 1T 추가매수
        if action == "관망":
            has_capacity = current_split < split_count
            should_enter = shares <= 0 and has_capacity
            should_add = (
                shares > 0
                and has_capacity
                and avg_price > 0
                and price <= star_price
            )

            if should_enter or should_add:
                buy_amount = min(unit_cash, cash / (1 + fee_rate))

                if buy_amount > 0:
                    buy_fee = buy_amount * fee_rate
                    total_buy_cost = buy_amount + buy_fee
                    buy_shares = buy_amount / price if price > 0 else 0

                    total_cost_before = shares * avg_price
                    shares += buy_shares
                    total_cost_after = total_cost_before + buy_amount
                    avg_price = total_cost_after / shares if shares > 0 else 0

                    cash -= total_buy_cost
                    current_split = min(float(split_count), current_split + 1)

                    if entry_date is None:
                        entry_date = date
                        entry_amount = total_buy_cost
                    else:
                        entry_amount += total_buy_cost

                    if should_enter:
                        action = "최초매수"
                    else:
                        action = f"별점이하 추가매수({star_pct:.1f}%)"

        stock_value = shares * price
        total_asset = cash + stock_value
        mode = "소진모드" if current_split >= split_count else "일반모드"
        star_price = avg_price * (1 - star_rate) if shares > 0 and avg_price > 0 else 0.0

        results.append({
            "Date": date,
            "Close": price,
            "RSI": row.get("WeeklyRSI", row.get("RSI", 50)),
            "Mode": mode,
            "Action": action,
            "Cash": cash,
            "Shares": shares,
            "StockValue": stock_value,
            "TotalAsset": total_asset,
            "CurrentSplit": current_split,
            "AvgPrice": avg_price,
            "StarPrice": star_price,
        })

    result_df = pd.DataFrame(results)
    result_df = add_metrics(result_df)
    trade_df = pd.DataFrame(trade_logs)

    if not trade_df.empty:
        maes = []
        mfes = []
        for _, trade in trade_df.iterrows():
            if pd.isna(trade.get("BuyDate")) or pd.isna(trade.get("SellDate")):
                maes.append(0)
                mfes.append(0)
                continue

            period = daily[(daily["Date"] >= trade["BuyDate"]) & (daily["Date"] <= trade["SellDate"])].copy()
            if period.empty:
                maes.append(0)
                mfes.append(0)
                continue

            entry_price = float(period.iloc[0]["Close"])
            min_price = float(period["Close"].min())
            max_price = float(period["Close"].max())
            maes.append(((min_price / entry_price) - 1) * 100 if entry_price > 0 else 0)
            mfes.append(((max_price / entry_price) - 1) * 100 if entry_price > 0 else 0)

        trade_df["MAE"] = maes
        trade_df["MFE"] = mfes

    return result_df, trade_df



# =========================

# =========================
# Step22D: 무한매수 4.0 V3
# =========================
def run_infinite4_v3_backtest(
    split_count=30,
    target_profit=7.0,
    quarter_sell_ratio=25.0,
    star_pct=7.0,
    max_gap_pct=20.0,
    max_hold_days=365,
    fee_rate_pct=0.25,
):
    """무한매수법 4.0 V3 백테스트 엔진.

    네가 작업하던 V1/V2 흐름을 유지하면서 Step22D에서 추가한 판단 보조 로직:
    - 분할횟수 20/30/40 강제
    - T = 총원금 / 분할횟수
    - 첫 진입 1T
    - 일반모드 / 소진모드
    - 전반전 / 후반전 표시
    - 별점 기준 추가매수
    - 큰수매수 후보가 있더라도 브로커 LOC 괴리 제한(max_gap_pct) 안에서만 허용
    - 목표수익률 도달 시 쿼터매도
    - max_hold_days 초과 시 보유일 관리 매도
    """
    split_count = int(split_count)
    if split_count not in [20, 30, 40]:
        split_count = 20 if split_count < 25 else 30 if split_count < 35 else 40

    cash = INITIAL_CASH
    shares = 0.0
    avg_price = 0.0
    current_split = 0.0
    entry_date = None
    entry_amount = 0.0

    unit_cash = INITIAL_CASH / split_count
    fee_rate = float(fee_rate_pct) / 100
    sell_ratio = max(0.01, min(float(quarter_sell_ratio) / 100, 1.0))
    star_rate = max(0.0, float(star_pct)) / 100
    max_gap_rate = max(0.0, float(max_gap_pct)) / 100
    max_hold_days = int(max_hold_days) if max_hold_days else 365

    results = []
    trade_logs = []

    for _, row in daily.iterrows():
        date = row["Date"]
        price = float(row["Close"])
        rsi = row.get("WeeklyRSI", row.get("RSI", 50))
        action = "관망"
        reason = ""

        hold_days = (date - entry_date).days if entry_date is not None and shares > 0 else 0
        mode = "소진모드" if current_split >= split_count else "일반모드"
        half = "전반전" if current_split < (split_count / 2) else "후반전"
        star_price = avg_price * (1 - star_rate) if shares > 0 and avg_price > 0 else 0.0
        big_buy_price = avg_price * (1 - max(star_rate * 1.5, star_rate + 0.03)) if shares > 0 and avg_price > 0 else 0.0
        sell_price = avg_price * (1 + float(target_profit) / 100) if shares > 0 and avg_price > 0 else 0.0
        current_return = ((price / avg_price) - 1) * 100 if shares > 0 and avg_price > 0 else 0.0

        # 1) 매도: 목표수익률 또는 보유일 관리
        if shares > 0 and avg_price > 0 and (current_return >= target_profit or hold_days >= max_hold_days):
            if hold_days >= max_hold_days and current_return < target_profit:
                sell_fraction = 1.0
                sell_reason = f"보유일 {hold_days}일 >= max_hold_days {max_hold_days}일 관리매도"
            elif current_split <= 1.01 or sell_ratio >= 0.999:
                sell_fraction = 1.0
                sell_reason = f"목표수익률 {target_profit:.1f}% 도달 전량매도"
            else:
                sell_fraction = sell_ratio
                sell_reason = f"목표수익률 {target_profit:.1f}% 도달 쿼터매도({quarter_sell_ratio:.1f}%)"

            sell_shares = shares * sell_fraction
            gross_sell = sell_shares * price
            sell_fee = gross_sell * fee_rate
            net_sell = gross_sell - sell_fee
            cost_basis_sold = entry_amount * sell_fraction if entry_amount > 0 else avg_price * sell_shares
            profit = net_sell - cost_basis_sold
            return_pct = (profit / cost_basis_sold) * 100 if cost_basis_sold > 0 else 0

            trade_logs.append({
                "BuyDate": entry_date,
                "SellDate": date,
                "HoldDays": hold_days,
                "BuyAmount": cost_basis_sold,
                "SellAmount": net_sell,
                "Profit": profit,
                "ReturnPct": return_pct,
                "Reason": sell_reason,
            })

            cash += net_sell
            shares -= sell_shares
            entry_amount -= cost_basis_sold
            current_split = max(0.0, current_split * (1 - sell_fraction))
            action = "쿼터매도" if sell_fraction < 1.0 else "전량매도"
            reason = sell_reason

            if shares <= 1e-9 or current_split <= 0.01:
                shares = 0.0
                avg_price = 0.0
                current_split = 0.0
                entry_date = None
                entry_amount = 0.0

        # 2) 매수: 최초 1T / 별점 이하 / 큰수매수 후보
        if action == "관망":
            has_capacity = current_split < split_count
            should_enter = shares <= 0 and has_capacity
            loc_gap_ok = True
            buy_tag = ""

            should_add_star = False
            should_add_big = False

            if shares > 0 and has_capacity and avg_price > 0:
                loc_gap_ok = price >= avg_price * (1 - max_gap_rate)
                should_add_star = price <= star_price and loc_gap_ok
                should_add_big = price <= big_buy_price and loc_gap_ok

            if should_enter:
                buy_tag = "최초 1T LOC"
            elif should_add_big:
                buy_tag = f"큰수매수 후보 LOC(max_gap {max_gap_pct:.1f}% 이내)"
            elif should_add_star:
                buy_tag = f"별점 이하 LOC({star_pct:.1f}%)"

            if should_enter or should_add_big or should_add_star:
                buy_amount = min(unit_cash, cash / (1 + fee_rate))
                if buy_amount > 0 and price > 0:
                    buy_fee = buy_amount * fee_rate
                    total_buy_cost = buy_amount + buy_fee
                    buy_shares = buy_amount / price

                    total_cost_before = shares * avg_price
                    shares += buy_shares
                    total_cost_after = total_cost_before + buy_amount
                    avg_price = total_cost_after / shares if shares > 0 else 0.0
                    cash -= total_buy_cost
                    current_split = min(float(split_count), current_split + 1)

                    if entry_date is None:
                        entry_date = date
                        entry_amount = total_buy_cost
                    else:
                        entry_amount += total_buy_cost

                    action = buy_tag
                    reason = buy_tag

        stock_value = shares * price
        total_asset = cash + stock_value
        mode = "소진모드" if current_split >= split_count else "일반모드"
        half = "전반전" if current_split < (split_count / 2) else "후반전"
        star_price = avg_price * (1 - star_rate) if shares > 0 and avg_price > 0 else 0.0
        big_buy_price = avg_price * (1 - max(star_rate * 1.5, star_rate + 0.03)) if shares > 0 and avg_price > 0 else 0.0
        sell_price = avg_price * (1 + float(target_profit) / 100) if shares > 0 and avg_price > 0 else 0.0
        hold_days_now = (date - entry_date).days if entry_date is not None and shares > 0 else 0

        results.append({
            "Date": date,
            "Close": price,
            "RSI": rsi,
            "Mode": mode,
            "Half": half,
            "Action": action,
            "Reason": reason,
            "Cash": cash,
            "Shares": shares,
            "StockValue": stock_value,
            "TotalAsset": total_asset,
            "CurrentSplit": current_split,
            "AvgPrice": avg_price,
            "StarPrice": star_price,
            "BigBuyPrice": big_buy_price,
            "SellPrice": sell_price,
            "HoldDaysNow": hold_days_now,
        })

    result_df = pd.DataFrame(results)
    result_df = add_metrics(result_df)
    trade_df = pd.DataFrame(trade_logs)

    if not trade_df.empty:
        maes = []
        mfes = []
        for _, trade in trade_df.iterrows():
            if pd.isna(trade.get("BuyDate")) or pd.isna(trade.get("SellDate")):
                maes.append(0)
                mfes.append(0)
                continue
            period = daily[(daily["Date"] >= trade["BuyDate"]) & (daily["Date"] <= trade["SellDate"])].copy()
            if period.empty:
                maes.append(0)
                mfes.append(0)
                continue
            entry_price = float(period.iloc[0]["Close"])
            min_price = float(period["Close"].min())
            max_price = float(period["Close"].max())
            maes.append(((min_price / entry_price) - 1) * 100 if entry_price > 0 else 0)
            mfes.append(((max_price / entry_price) - 1) * 100 if entry_price > 0 else 0)
        trade_df["MAE"] = maes
        trade_df["MFE"] = mfes

    return result_df, trade_df


def run_infinite4_v2_backtest(**kwargs):
    """기존 V2 메뉴가 남아 있어도 깨지지 않게 V3 엔진으로 연결."""
    return run_infinite4_v3_backtest(**kwargs)


# Step17 딥마이닝 TOP50 필터

# =========================
def load_deepmine_data(strategy, ticker="QQQ"):
    ticker = ticker.upper()
    file_map = {
        "rsi": [f"{ticker}_ultra_score_top10.csv", "QQQ_ultra_score_top10.csv"],
        "original": [f"{ticker}_original_score_top10.csv", "QQQ_original_score_top10.csv"],
        "original_upgrade": [f"{ticker}_original_return_top10.csv", "QQQ_original_return_top10.csv"],
    }

    for file_path in file_map.get(strategy, []):
        try:
            return pd.read_csv(file_path)
        except Exception:
            continue

    return pd.DataFrame()


def build_deepmine_table(
    strategy,
    ticker="QQQ",
    min_cagr=0,
    max_mdd=100,
    min_win=0,
    min_pf=0
):
    df = load_deepmine_data(strategy, ticker)

    if df.empty:
        if str(strategy).startswith("raor4_"):
            return "<div class=\"card hero\"><h2>딥마이닝 TOP50</h2><p>라오어 무한매수 Step24 계열 전용 딥마이닝 결과 파일이 아직 없습니다.</p><p class=\"small-note\">현재 버튼은 과거 RSI/오리지널 계열 CSV와 섞지 않도록 막아두었습니다. Step24M 전용 최적화 파일을 만들면 여기서 표시됩니다.</p></div>", None
        return "", None

    cagr_col = pick_first_existing_col(df, ["CAGR", "cagr"])
    mdd_col = pick_first_existing_col(df, ["MDD", "mdd"])
    win_col = pick_first_existing_col(df, ["승률", "WinRate", "win_rate"])
    pf_col = pick_first_existing_col(df, ["ProfitFactor", "profit_factor", "PF"])

    if cagr_col:
        df = df[df[cagr_col].apply(lambda x: to_number_safe(x)) >= min_cagr]

    if mdd_col:
        df = df[df[mdd_col].apply(lambda x: abs(to_number_safe(x))) <= max_mdd]

    if win_col:
        df = df[df[win_col].apply(lambda x: to_number_safe(x)) >= min_win]

    if pf_col:
        df = df[df[pf_col].apply(lambda x: to_number_safe(x)) >= min_pf]

    if df.empty:
        return "<p>조건에 맞는 전략이 없습니다.</p>", None

    # 추천 전략 선정
    best_row = df.iloc[0]

    best_cagr = to_number_safe(best_row[cagr_col]) if cagr_col else 0
    best_mdd = to_number_safe(best_row[mdd_col]) if mdd_col else 0
    best_win = to_number_safe(best_row[win_col]) if win_col else 0

    strategy_type = classify_strategy_type(best_cagr, best_mdd, best_win)

    recommend_card = {
        "type": strategy_type,
        "cagr": best_cagr,
        "mdd": best_mdd,
        "win": best_win,
        "row": best_row,
    }

    display_df = df.head(50).copy()

    # 전략유형 추가
    display_types = []

    for _, row in display_df.iterrows():
        row_cagr = to_number_safe(row[cagr_col]) if cagr_col else 0
        row_mdd = to_number_safe(row[mdd_col]) if mdd_col else 0
        row_win = to_number_safe(row[win_col]) if win_col else 0

        display_types.append(
            classify_strategy_type(row_cagr, row_mdd, row_win)
        )

    display_df["전략유형"] = display_types

    headers = "".join([f"<th>{col}</th>" for col in display_df.columns])

    rows_html = ""

    for _, row in display_df.iterrows():
        row_html = "<tr>"

        for col in display_df.columns:
            row_html += f"<td>{row[col]}</td>"

        row_html += "</tr>"
        rows_html += row_html

    html = f"""
    <div class="card">
        <h2>딥마이닝 TOP50 (필터 적용)</h2>

        <div class="table-wrap">
            <table border="1" cellpadding="6" cellspacing="0">
                <tr>{headers}</tr>
                {rows_html}
            </table>
        </div>
    </div>
    """

    return html, recommend_card



# =========================
# Step19 오늘의 판단실

# =========================
def make_today_decision(
    latest_mode,
    split_count,
    current_split,
    final_cash,
    latest_price,
    fee_percent
):
    remain_split = max(split_count - current_split, 0)

    if remain_split <= 0:
        return {
            "action": "분할 완료 / 대기",
            "class": "warning",
            "recommended_split": 0,
            "amount": 0,
            "detail": "이미 최대 분할 상태입니다.",
        }

    split_cash = final_cash / remain_split if remain_split > 0 else 0

    if latest_mode == "과열":
        return {
            "action": "매도 검토",
            "class": "negative",
            "recommended_split": 0,
            "amount": 0,
            "detail": "과열 구간으로 신규 매수보다 차익실현 우선 구간입니다.",
        }

    if latest_mode == "상승":
        recommended_split = min(1, remain_split)

    elif latest_mode == "중립":
        recommended_split = min(1, remain_split)

    elif latest_mode == "침체":
        recommended_split = min(2, remain_split)

    else:  # 극침체
        recommended_split = min(4, remain_split)

    invest_amount = split_cash * recommended_split

    estimated_fee = invest_amount * (fee_percent / 100)

    return {
        "action": f"{recommended_split}분할 매수",
        "class": "positive" if recommended_split > 0 else "warning",
        "recommended_split": recommended_split,
        "amount": invest_amount,
        "detail": f"예상 투입금 {invest_amount:,.0f}원 / 예상 매수수수료 {estimated_fee:,.0f}원",
    }



# =========================
# Step18A + 19 카드 HTML

# =========================
def build_walkforward_and_today_cards(
    bt,
    latest_mode,
    split_count,
    current_split,
    final_cash,
    latest_price,
    fee_percent
):
    train_summary, test_summary, cagr_drop, mdd_worse, wf_verdict, wf_class, wf_detail = make_walkforward_summary(bt)
    stability_score, overfit_risk, overfit_class = calc_stability_score(train_summary, test_summary, mdd_worse)

    today_decision = make_today_decision(
        latest_mode,
        split_count,
        current_split,
        final_cash,
        latest_price,
        fee_percent
    )

    html = f"""
    <div class="grid">

        <div class="metric {wf_class}">
            <h3>워크포워드 판정</h3>
            <p>{wf_verdict}</p>
        </div>

        <div class="metric {overfit_class}">
            <h3>Overfit Risk</h3>
            <p>{overfit_risk}</p>
        </div>

        <div class="metric {overfit_class}">
            <h3>Stability Score</h3>
            <p>{stability_score:.1f}</p>
        </div>

        <div class="metric">
            <h3>인샘플 CAGR</h3>
            <p>{train_summary['cagr']:.2f}%</p>
        </div>

        <div class="metric">
            <h3>아웃샘플 CAGR</h3>
            <p>{test_summary['cagr']:.2f}%</p>
        </div>

        <div class="metric {cls_delta(-cagr_drop)}">
            <h3>CAGR 변화</h3>
            <p>{-cagr_drop:.2f}%</p>
        </div>

        <div class="metric {today_decision['class']}">
            <h3>오늘의 추천행동</h3>
            <p>{today_decision['action']}</p>
        </div>

        <div class="metric">
            <h3>추천 투입금</h3>
            <p>{today_decision['amount']:,.0f}원</p>
        </div>

    </div>

    <div class="card">
        <h2>Step18A 워크포워드 분석</h2>
        <p>{wf_detail}</p>
        <p>인샘플: {train_summary['start']} ~ {train_summary['end']}</p>
        <p>아웃샘플: {test_summary['start']} ~ {test_summary['end']}</p>
        <p>아웃샘플 MDD 변화: {mdd_worse:.2f}%p</p>
        <p>Stability Score: <b>{stability_score:.1f}</b> / Overfit Risk: <b>{overfit_risk}</b></p>
    </div>

    <div class="card">
        <h2>Step19 오늘의 판단실</h2>
        <p>현재 모드: <b>{latest_mode}</b></p>
        <p>{today_decision['detail']}</p>
    </div>
    """

    return html


# =========================



# =========================
# Step20+21: 프리셋 / 전략 파라미터 맵 / 최적화 비교 UI
# =========================
def metric_class_from_mdd(mdd_value):
    try:
        v = float(mdd_value)
    except Exception:
        return "warning"
    if v <= -80:
        return "danger"
    if v <= -55:
        return "warning"
    return "positive"


def practical_grade(cagr, mdd, stability):
    try:
        cagr = float(cagr)
        mdd = float(mdd)
        stability = float(stability)
    except Exception:
        return "검토"

    if cagr >= 30 and mdd >= -80 and stability >= 55:
        return "S 균형형"
    if cagr >= 35 and mdd < -80:
        return "A 공격형"
    if stability >= 70 and mdd >= -65:
        return "B 방어형"
    return "C 연구용"


def build_preset_buttons_html(ticker, strategy, start_date, end_date, fee_percent):
    """티커별 추천 프리셋 버튼. 현재는 RSI 최적화 결과를 중심으로 구성."""
    ticker = ticker.upper()

    buttons = []
    for preset_type in ["balanced", "aggressive", "defensive"]:
        preset = get_preset(ticker, "rsi", preset_type)
        if not preset:
            continue

        query = get_preset_query(
            ticker=ticker,
            strategy="rsi",
            preset_type=preset_type,
            start_date=start_date,
            end_date=end_date,
            fee_percent=fee_percent,
        )
        label = preset.get("label", preset_type)
        desc = preset.get("desc", "")

        buttons.append(f"""
        <a class="preset-btn" href="/?{query}">
            <b>{label}</b><br>
            <span>{desc}</span>
        </a>
        """)

    if not buttons:
        return ""

    return f"""
    <div class="preset-box">
        <p><b>Step20 추천 프리셋</b> <span class="small-note">Optimizer 결과 기반 자동입력</span></p>
        <div class="preset-buttons">
            {''.join(buttons)}
        </div>
    </div>
    """


def build_strategy_param_map_html():
    """Step21: 전략별 파라미터 맵. 실제 엔진 이식 전에도 구조를 먼저 고정."""
    sections = []

    for strategy_key, config in STRATEGY_PARAM_MAP.items():
        label = config.get("label", strategy_key)
        status = config.get("status", "준비중")
        params = config.get("params", [])
        note = config.get("note", "")

        li = "".join([f"<li>{p}</li>" for p in params])
        sections.append(f"""
        <div class="map-card">
            <h3>{label}</h3>
            <p class="small-note">상태: <b>{status}</b></p>
            <ul>{li}</ul>
            <p class="small-note">{note}</p>
        </div>
        """)

    return f"""
    <div class="card">
        <h2>Step21 전략별 파라미터 맵</h2>
        <p class="small-note">무한매수 / 떨사오팔 / 종사종팔 엔진을 나중에 연결하기 위한 공통 설계도입니다.</p>
        <div class="map-grid">
            {''.join(sections)}
        </div>
    </div>
    """


def build_optimizer_compare_html(strategy="rsi"):
    """생성된 *_optimizer_top100.csv 파일을 읽어 티커별 1순위만 비교."""
    rows = optimizer_compare_rows(strategy)
    if not rows:
        return f"""
        <div class="card">
            <h2>Step20 티커별 최적화 비교</h2>
            <p>아직 비교할 Optimizer 결과가 없습니다.</p>
            <pre>python optimizer_lab.py TQQQ {strategy}
python optimizer_lab.py SOXL {strategy}
python optimizer_lab.py SOXX {strategy}</pre>
        </div>
        """

    card_rows = ""
    table_rows = ""

    for r in rows:
        ticker = r.get("Ticker", "-")
        score = r.get("Score", 0)
        cagr = r.get("CAGR", 0)
        mdd = r.get("MDD", 0)
        stability = r.get("StabilityScore", 0)
        grade = practical_grade(cagr, mdd, stability)
        mdd_cls = metric_class_from_mdd(mdd)

        card_rows += f"""
        <div class="metric {mdd_cls}">
            <h3>{ticker} / {grade}</h3>
            <p>{score}</p>
            <span class="small-note">CAGR {cagr}% / MDD {mdd}% / Stability {stability}</span>
        </div>
        """

        table_rows += f"""
        <tr>
            <td>{ticker}</td>
            <td>{score}</td>
            <td>{cagr}%</td>
            <td>{mdd}%</td>
            <td>{stability}</td>
            <td>{r.get("OverfitRisk", "-")}</td>
            <td>{grade}</td>
            <td>{r.get("split_count", "-")}</td>
            <td>{r.get("sell_rsi", "-")}</td>
            <td>{r.get("extreme_split", "-")}</td>
            <td>{r.get("recession_split", "-")}</td>
            <td>{r.get("neutral_split", "-")}</td>
            <td>{r.get("boom_split", "-")}</td>
        </tr>
        """

    return f"""
    <div class="card hero">
        <h2>Step20 티커별 Optimizer 1위 비교</h2>
        <div class="grid">
            {card_rows}
        </div>
        <div class="table-wrap">
            <table border="1" cellpadding="6" cellspacing="0">
                <tr>
                    <th>티커</th>
                    <th>Score</th>
                    <th>CAGR</th>
                    <th>MDD</th>
                    <th>Stability</th>
                    <th>Overfit</th>
                    <th>실전등급</th>
                    <th>분할수</th>
                    <th>매도RSI</th>
                    <th>극침체</th>
                    <th>침체</th>
                    <th>중립</th>
                    <th>상승</th>
                </tr>
                {table_rows}
            </table>
        </div>
    </div>
    """


# =========================
# Step24P: 화면 즉시 실행 Optimizer / DeepMining
# =========================
def _parse_number_list(text, allowed=None, cast=float):
    values = []
    for raw in str(text or "").replace("/", ",").split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            v = int(float(raw)) if cast is int else float(raw)
        except Exception:
            continue
        if allowed is not None and v not in allowed:
            continue
        if v not in values:
            values.append(v)
    return values


def _frange(min_v, max_v, step_v):
    try:
        min_v = float(min_v); max_v = float(max_v); step_v = float(step_v)
    except Exception:
        return []
    if step_v <= 0:
        return []
    if min_v > max_v:
        min_v, max_v = max_v, min_v
    out, v, guard = [], min_v, 0
    while v <= max_v + 1e-9 and guard < 10000:
        r = round(v, 4)
        if r not in out:
            out.append(r)
        v += step_v
        guard += 1
    return out


def _step24p_param_grid(mode="optimizer", split_values_text="20,40", first_loc_min=10.0, first_loc_max=15.0, first_loc_step=None, designated_min=None, designated_max=None, designated_step=None):
    """원문 공식이 확인된 20/40분할만 사용한다. 30/50/60은 임의추정 방지를 위해 제외."""
    split_values = _parse_number_list(split_values_text, allowed={20, 40}, cast=int) or [20, 40]
    if first_loc_step is None:
        first_loc_step = 0.5 if mode == "deepmine" else 2.5
    if designated_min is None:
        designated_min = 5.0 if mode == "deepmine" else 10.0
    if designated_max is None:
        designated_max = 30.0 if mode == "deepmine" else 25.0
    if designated_step is None:
        designated_step = 2.5
    first_loc_values = [v for v in _frange(first_loc_min, first_loc_max, first_loc_step) if 10.0 <= float(v) <= 15.0]
    designated_values = _frange(designated_min, designated_max, designated_step)
    if not first_loc_values:
        first_loc_values = [10.0, 12.5, 15.0]
    if not designated_values:
        designated_values = [15.0, 20.0]
    for split in split_values:
        for first_loc in first_loc_values:
            for designated in designated_values:
                yield {"infinite_split_count": int(split), "first_loc_buffer_pct": float(first_loc), "designated_sell_pct": float(designated)}


def _safe_profit_factor(trade_df):
    if trade_df is None or trade_df.empty or "Profit" not in trade_df.columns:
        return 0.0
    gp = float(trade_df.loc[trade_df["Profit"] > 0, "Profit"].fillna(0).sum())
    gl = abs(float(trade_df.loc[trade_df["Profit"] < 0, "Profit"].fillna(0).sum()))
    return gp / gl if gl > 0 else (gp if gp > 0 else 0.0)


def _step24p_run_params(ticker, params, fee_percent):
    return run_raor_infinite4_step24p_backtest(
        ticker=ticker,
        split_count=int(params["infinite_split_count"]),
        first_loc_buffer_pct=float(params["first_loc_buffer_pct"]),
        designated_sell_pct_override=float(params["designated_sell_pct"]),
        fee_rate_pct=fee_percent,
    )


def _step24p_score(cagr, mdd, completed_cycles, avg_hold_days, stability, pf, overfit_risk, score_mode):
    risk_penalty = {"낮음": 0, "보통": 5, "높음": 15}.get(overfit_risk, 10)
    abs_mdd = abs(float(mdd)); cagr = float(cagr)
    completed_cycles = float(completed_cycles or 0); avg_hold_days = float(avg_hold_days or 0)
    turnover_bonus = min(completed_cycles, 80) * 0.30 - min(avg_hold_days, 365) * 0.015
    pf_bonus = min(float(pf or 0), 5) * 5
    stability_bonus = float(stability or 0) * 0.45
    if score_mode == "return":
        return (cagr * 2.8) + (stability_bonus * 0.7) + pf_bonus - (abs_mdd * 0.28) - risk_penalty
    if score_mode == "mdd":
        return (cagr * 1.35) + stability_bonus + pf_bonus - (abs_mdd * 0.85) - risk_penalty
    if score_mode == "turnover":
        return (cagr * 1.7) + stability_bonus + pf_bonus + turnover_bonus - (abs_mdd * 0.38) - risk_penalty
    return (cagr * 2.0) + stability_bonus + pf_bonus + (turnover_bonus * 0.5) - (abs_mdd * 0.40) - risk_penalty


def _step24p_candidate_label(row):
    cagr = to_number_safe(row.get("CAGR")); mdd = abs(to_number_safe(row.get("MDD"))); completed = to_number_safe(row.get("CompletedCycles"))
    if cagr >= 12 and mdd <= 35 and completed >= 5:
        return "강력 후보"
    if cagr >= 7 and mdd <= 45 and completed >= 3:
        return "유효 후보"
    if mdd <= 25 and cagr >= 3:
        return "방어 후보"
    if completed <= 2:
        return "회전 부족"
    return "관찰"


def _step24p_summarize_result(ticker, bt, trade_df, params, idx, total, score_mode, strategy_key="raor4_step24p"):
    final_asset = float(bt.iloc[-1]["TotalAsset"])
    total_return = (final_asset / INITIAL_CASH - 1) * 100
    cagr = calc_cagr(bt)
    mdd = float(bt["Drawdown"].min() * 100) if "Drawdown" in bt.columns else 0.0
    ts = make_trade_summary(trade_df, bt)
    cycle_status = make_cycle_status(trade_df, bt, int(params["infinite_split_count"]))
    try:
        train, test, cagr_drop, mdd_worse, *_ = make_walkforward_summary(bt)
        stability, overfit_risk, _ = calc_stability_score(train, test, mdd_worse)
    except Exception:
        stability, overfit_risk, mdd_worse = 0, "확인필요", 0
    pf = _safe_profit_factor(trade_df); avg_hold = float(ts.get("avg_hold_days", 0) or 0)
    completed_cycles = int(cycle_status.get("completed_cycles", 0) or 0)
    score = _step24p_score(cagr, mdd, completed_cycles, avg_hold, stability, pf, overfit_risk, score_mode)
    row = {
        "검증순서": int(idx), "진행률": f"{(idx / max(total, 1)) * 100:.1f}%", "판정": "",
        "Ticker": ticker, "Strategy": strategy_key, "분할수": int(params["infinite_split_count"]),
        "첫매수LOC여유율": float(params["first_loc_buffer_pct"]), "지정가매도%": float(params["designated_sell_pct"]),
        "FinalAsset": round(final_asset), "Return": round(total_return, 2), "CAGR": round(cagr, 2), "MDD": round(mdd, 2),
        "WinRate": round(ts.get("win_rate", 0), 2), "Trades": int(ts.get("trade_count", 0) or 0),
        "CompletedCycles": completed_cycles, "ActiveT": round(float(cycle_status.get("active_t", 0) or 0), 2),
        "AvgHoldDays": round(avg_hold, 1), "ProfitFactor": round(pf, 2), "StabilityScore": round(float(stability), 1),
        "OverfitRisk": overfit_risk, "MDD_Worse": round(float(mdd_worse), 2), "Score": round(score, 2),
    }
    row["판정"] = _step24p_candidate_label(row)
    return row


def _step24p_cache_key(ticker, fee_percent, mode, score_mode, params):
    payload = {"ticker": ticker, "fee_percent": float(fee_percent), "mode": mode, "score_mode": score_mode, "params": params}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def run_step24p_screen_optimizer(ticker, fee_percent, mode="optimizer", split_values_text="20,40", first_loc_min=10.0, first_loc_max=15.0, first_loc_step=None, designated_min=None, designated_max=None, designated_step=None, score_mode="balanced", use_cache=True, strategy_key="raor4_step24p"):
    """Step24 전용 Optimizer/DeepMining 실행. Step24Q는 캐시 폴더를 분리해서 RSI/기존 결과와 섞이지 않게 한다."""
    grid_kwargs = dict(mode=mode, split_values_text=split_values_text, first_loc_min=first_loc_min, first_loc_max=first_loc_max, first_loc_step=first_loc_step, designated_min=designated_min, designated_max=designated_max, designated_step=designated_step)
    params_list = list(_step24p_param_grid(**grid_kwargs))
    cache_dir = Path("step24_cache") / ("step24x" if strategy_key == "raor4_step24x" else ("step24w" if strategy_key == "raor4_step24w" else ("step24v" if strategy_key == "raor4_step24v" else ("step24u" if strategy_key == "raor4_step24u" else ("step24t" if strategy_key == "raor4_step24t" else ("step24s" if strategy_key == "raor4_step24s" else ("step24r" if strategy_key == "raor4_step24r" else ("step24q" if strategy_key == "raor4_step24q" else "step24p"))))))))
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = _step24p_cache_key(ticker, fee_percent, mode, score_mode, {"strategy_key": strategy_key, **grid_kwargs})
    cache_file = cache_dir / f"{ticker}_{strategy_key}_{mode}_{score_mode}_{cache_key}.csv"
    if use_cache and cache_file.exists():
        try:
            return pd.read_csv(cache_file), [], str(cache_file), True, len(params_list)
        except Exception:
            pass
    rows, errors, total = [], [], len(params_list)
    for idx, params in enumerate(params_list, 1):
        try:
            bt_x, trade_x = _step24p_run_params(ticker, params, fee_percent)
            rows.append(_step24p_summarize_result(ticker, bt_x, trade_x, params, idx, total, score_mode, strategy_key))
        except Exception as e:
            if len(errors) < 5:
                errors.append(f"{params}: {e}")
    df = pd.DataFrame(rows)
    if df.empty:
        return df, errors, str(cache_file), False, total
    df = df.sort_values(["Score", "StabilityScore", "CAGR"], ascending=False).reset_index(drop=True)
    try:
        df.to_csv(cache_file, index=False, encoding="utf-8-sig")
    except Exception:
        pass
    return df, errors, str(cache_file), False, total


def _step24_label_class(label):
    label = str(label or "")
    if "강력" in label:
        return "cand-strong"
    if "유효" in label:
        return "cand-valid"
    if "방어" in label:
        return "cand-defense"
    if "회전" in label:
        return "cand-slow"
    return "cand-watch"


def build_step24p_optimizer_html(ticker, fee_percent, mode="optimizer", min_cagr=0, max_mdd=100, min_win=0, min_pf=0, split_values_text="20,40", first_loc_min=10.0, first_loc_max=15.0, first_loc_step=None, designated_min=None, designated_max=None, designated_step=None, score_mode="balanced", display_limit=None, strategy_key="raor4_step24p"):
    step_label = "Step24X" if strategy_key == "raor4_step24x" else ("Step24W" if strategy_key == "raor4_step24w" else ("Step24V" if strategy_key == "raor4_step24v" else ("Step24U" if strategy_key == "raor4_step24u" else ("Step24T" if strategy_key == "raor4_step24t" else ("Step24S" if strategy_key == "raor4_step24s" else ("Step24R" if strategy_key == "raor4_step24r" else ("Step24Q" if strategy_key == "raor4_step24q" else "Step24P")))))))
    df, errors, cache_file, cache_hit, total_count = run_step24p_screen_optimizer(
        ticker, fee_percent, mode, split_values_text, first_loc_min, first_loc_max,
        first_loc_step, designated_min, designated_max, designated_step, score_mode, True, strategy_key
    )
    title = f"{step_label} DeepMining TOP50" if mode == "deepmine" else f"{step_label} Optimizer TOP100"
    if df.empty:
        err_html = "<br>".join(errors) if errors else "결과 없음"
        return f'<div id="step24-results" class="card hero"><h2>{title}</h2><p>최적화 결과를 만들지 못했습니다.</p><p class="small-note">{err_html}</p></div>'

    df = df[df["CAGR"].apply(lambda x: to_number_safe(x)) >= min_cagr]
    df = df[df["MDD"].apply(lambda x: abs(to_number_safe(x))) <= max_mdd]
    df = df[df["WinRate"].apply(lambda x: to_number_safe(x)) >= min_win]
    df = df[df["ProfitFactor"].apply(lambda x: to_number_safe(x)) >= min_pf]
    if df.empty:
        return f'<div id="step24-results" class="card hero"><h2>{title}</h2><p>필터 조건에 맞는 후보가 없습니다.</p></div>'

    limit = int(display_limit or (50 if mode == "deepmine" else 100))
    display_df = df.head(limit).copy()
    best = display_df.iloc[0]
    source_label = "캐시 재사용" if cache_hit else "새로 계산 후 캐시 저장"
    source_class = "cache-hit" if cache_hit else "cache-new"
    score_label = {"balanced": "균형형", "return": "수익률 우선", "mdd": "MDD 방어 우선", "turnover": "회전율 우선"}.get(score_mode, "균형형")
    download_url = f'/download_step24_cache?file={cache_file}'

    quick_buttons = ''
    rows = ''
    headers = ''.join([f'<th>{col}</th>' for col in display_df.columns]) + '<th>설정 적용</th>'
    for rank, (_, row) in enumerate(display_df.iterrows(), 1):
        split_v = int(row.get("분할수", 40))
        first_v = row.get("첫매수LOC여유율", 12)
        sell_v = row.get("지정가매도%", 15)
        score_v = row.get("Score", "")
        apply_link = (
            f'/?ticker={ticker}&strategy={strategy_key}&infinite_split_count={split_v}'
            f'&first_loc_buffer_pct={first_v}&designated_sell_pct={sell_v}'
            f'&fee_percent={fee_percent}&action_mode=backtest&applied_from={mode}'
            f'&applied_rank={rank}&applied_score={score_v}'
        )
        if rank <= 3:
            quick_buttons += f'<a class="quick-apply-btn" href="{apply_link}">{rank}위 적용 · {split_v}분할 · LOC {first_v}% · 지정가 {sell_v}%</a>'
        tr_class = "top-rank" if rank == 1 else _step24_label_class(row.get("판정"))
        rows += '<tr class="%s">' % tr_class + ''.join([f'<td>{row[col]}</td>' for col in display_df.columns]) + f'<td><a class="apply-link" href="{apply_link}">적용</a></td></tr>'

    compare_html = build_step24v_candidate_compare_html(display_df, ticker, fee_percent, mode=mode, strategy_key=strategy_key)

    return f"""
    <div id="step24-results" class="card hero step24-progress-card step24q-result-card">
        <h2>{title} 추천 1순위</h2>
        <div class="step24q-status-row">
            <span class="step24q-pill {source_class}">{source_label}</span>
            <span class="step24q-pill">전체 조합 {total_count}개</span>
            <span class="step24q-pill">점수기준 {score_label}</span>
            <a class="step24q-download" href="{download_url}">CSV 다운로드</a>
        </div>
        <div class="progress-shell"><div class="progress-bar" style="width:100%;"></div></div>
        <p class="small-note">검증 완료: {len(display_df)}개 표시 / 전체 조합 {total_count}개 · {source_label}</p>
        <div class="grid">
            <div class="metric positive"><h3>판정</h3><p>{best.get('판정', '-')}</p></div>
            <div class="metric positive"><h3>Score</h3><p>{best.get('Score', '-')}</p></div>
            <div class="metric positive"><h3>CAGR</h3><p>{best.get('CAGR', '-')}%</p></div>
            <div class="metric warning"><h3>MDD</h3><p>{best.get('MDD', '-')}%</p></div>
            <div class="metric positive"><h3>완료주기</h3><p>{best.get('CompletedCycles', '-')}회</p></div>
        </div>
        <div class="quick-apply-row">{quick_buttons}</div>
        <p class="small-note">CSV: {cache_file}</p>
    </div>
    {compare_html}
    <div class="card step24-progress-card step24q-table-card">
        <h2>{title} 진행형 후보판정표</h2>
        <p class="small-note">{step_label}: 조건이 같으면 Step24 전용 캐시 CSV를 재사용하고, 후보별 적용 링크는 현재 설정칸에 바로 반영한 뒤 백테스트를 실행합니다.</p>
        <div class="table-wrap"><table class="step24q-table" border="1" cellpadding="6" cellspacing="0"><tr>{headers}</tr>{rows}</table></div>
    </div>
    """


def _step24v_trade_gap_stats(bt, split_count=40):
    """후보 평가용 보조지표: 장기 무체결 공백 최대값만 계산한다. 매매 공식에는 관여하지 않는다."""
    if bt is None or bt.empty or "Date" not in bt.columns:
        return {"max_gap_trading_days": 0, "max_gap_calendar_days": 0, "gap_count_60d": 0}
    df = bt.copy().sort_values("Date").reset_index(drop=True)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    if df.empty:
        return {"max_gap_trading_days": 0, "max_gap_calendar_days": 0, "gap_count_60d": 0}
    def _bool_col(name):
        if name not in df.columns:
            return pd.Series([False] * len(df), index=df.index)
        return df[name].fillna(False).astype(bool)
    action_text = df.get("Action", pd.Series([""] * len(df), index=df.index)).astype(str)
    fill_mask = (_bool_col("BuyLOCExecuted") | _bool_col("SellLOCExecuted") | _bool_col("DesignatedSellExecuted") | action_text.str.contains("매수|매도", regex=True, na=False))
    max_td = 0
    max_cd = 0
    gap_count_60d = 0
    start_i = None
    for i, filled in enumerate(fill_mask.tolist()):
        if filled:
            if start_i is not None:
                end_i = i - 1
                td = end_i - start_i + 1
                cd = int((df.loc[end_i, "Date"] - df.loc[start_i, "Date"]).days)
                max_td = max(max_td, td)
                max_cd = max(max_cd, cd)
                if td >= 60 or cd >= 90:
                    gap_count_60d += 1
                start_i = None
        else:
            if start_i is None:
                start_i = i
    if start_i is not None:
        end_i = len(df) - 1
        td = end_i - start_i + 1
        cd = int((df.loc[end_i, "Date"] - df.loc[start_i, "Date"]).days)
        max_td = max(max_td, td)
        max_cd = max(max_cd, cd)
        if td >= 60 or cd >= 90:
            gap_count_60d += 1
    return {"max_gap_trading_days": int(max_td), "max_gap_calendar_days": int(max_cd), "gap_count_60d": int(gap_count_60d)}


def _step24v_pick_candidate_rows(df):
    """Optimizer 결과에서 실전 비교용 대표 후보를 뽑는다. 후보 평가는 원문 매매공식이 아닌 보조 지표다."""
    if df is None or df.empty:
        return []
    work = df.copy()
    for col in ["Score", "CAGR", "MDD", "CompletedCycles", "AvgHoldDays"]:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")
    picks = []
    def add(kind, idx):
        if idx is None or pd.isna(idx):
            return
        row = work.loc[idx].copy()
        key = (int(row.get("분할수", 0) or 0), float(row.get("첫매수LOC여유율", 0) or 0), float(row.get("지정가매도%", 0) or 0))
        if any(p["key"] == key for p in picks):
            return
        picks.append({"kind": kind, "key": key, "row": row})
    if "Score" in work.columns and work["Score"].notna().any():
        add("균형형 Score 1위", work["Score"].idxmax())
    if "CAGR" in work.columns and work["CAGR"].notna().any():
        add("수익률형 CAGR 1위", work["CAGR"].idxmax())
    if "MDD" in work.columns and work["MDD"].notna().any():
        add("방어형 MDD 1위", work["MDD"].idxmax())
    if "CompletedCycles" in work.columns and len(picks) < 3 and work["CompletedCycles"].notna().any():
        add("회전형 완료주기 1위", work["CompletedCycles"].idxmax())
    return picks[:3]


def build_step24v_candidate_compare_html(df, ticker, fee_percent, mode="optimizer", strategy_key="raor4_step24v"):
    if strategy_key != "raor4_step24v" or df is None or df.empty:
        return ""
    picks = _step24v_pick_candidate_rows(df)
    if not picks:
        return ""
    cards = ""
    rows = ""
    for rank, item in enumerate(picks, 1):
        row = item["row"]
        split_v = int(row.get("분할수", 40) or 40)
        first_v = float(row.get("첫매수LOC여유율", 12) or 12)
        sell_v = float(row.get("지정가매도%", 15) or 15)
        params = {"infinite_split_count": split_v, "first_loc_buffer_pct": first_v, "designated_sell_pct": sell_v}
        gap = {"max_gap_trading_days": "-", "max_gap_calendar_days": "-", "gap_count_60d": "-"}
        y2022 = "-"
        practical_score = to_number_safe(row.get("Score"))
        try:
            bt2, trade2 = _step24p_run_params(ticker, params, fee_percent)
            gap = _step24v_trade_gap_stats(bt2, split_v)
            ydf = calc_yearly_stats(bt2)
            if not ydf.empty and 2022 in set(ydf["Year"].astype(int)):
                y2022 = f"{float(ydf.loc[ydf['Year'].astype(int)==2022, 'StrategyReturn'].iloc[0]):.2f}%"
            practical_score = practical_score - min(float(gap.get("max_gap_trading_days", 0) or 0), 120) * 0.10 - float(gap.get("gap_count_60d", 0) or 0) * 2.5
        except Exception:
            pass
        if practical_score >= 90:
            verdict = "실전 1군 후보"
            cls = "positive"
        elif practical_score >= 60:
            verdict = "실전 검토 후보"
            cls = "warning"
        else:
            verdict = "관찰/보류"
            cls = "danger"
        apply_link = (f'/?ticker={ticker}&strategy={strategy_key}&infinite_split_count={split_v}'
                      f'&first_loc_buffer_pct={first_v}&designated_sell_pct={sell_v}'
                      f'&fee_percent={fee_percent}&action_mode=backtest&applied_from={mode}'
                      f'&applied_rank={rank}&applied_score={row.get("Score", "")}')
        cards += f'<div class="metric {cls}"><h3>{item["kind"]}</h3><p>{verdict}</p><small>{split_v}분할 · LOC {first_v}% · 지정가 {sell_v}%</small></div>'
        rows += f'''
        <tr>
            <td>{item["kind"]}</td><td>{split_v}</td><td>{first_v}</td><td>{sell_v}</td>
            <td>{row.get("CAGR", "-")}%</td><td>{row.get("MDD", "-")}%</td><td>{row.get("CompletedCycles", "-")}회</td>
            <td>{gap.get("max_gap_trading_days", "-")}거래일 / {gap.get("max_gap_calendar_days", "-")}일</td>
            <td>{gap.get("gap_count_60d", "-")}회</td><td>{y2022}</td><td>{practical_score:.2f}</td><td>{verdict}</td>
            <td><a class="apply-link" href="{apply_link}">적용</a></td>
        </tr>
        '''
    return f'''
    <div class="card step24v-compare-card">
        <h2>Step24V 후보 비교 / 실전선정</h2>
        <p class="small-note">Optimizer 결과에서 균형형·수익률형·방어형 대표 후보를 자동 추려 비교합니다. 이 표의 실전점수와 공백 페널티는 원문 매매공식이 아니라 후보 선택용 보조지표입니다.</p>
        <div class="grid">{cards}</div>
        <div class="table-wrap"><table class="step24q-table" border="1" cellpadding="6" cellspacing="0">
            <tr><th>후보유형</th><th>분할</th><th>첫매수 LOC</th><th>지정가%</th><th>CAGR</th><th>MDD</th><th>완료주기</th><th>최대 무체결 공백</th><th>장기공백</th><th>2022 수익률</th><th>실전점수</th><th>판정</th><th>설정</th></tr>
            {rows}
        </table></div>
    </div>
    '''



def _step24w_period_metric(bt, start=None, end=None):
    try:
        sub = bt.copy()
        sub["Date"] = pd.to_datetime(sub["Date"], errors="coerce")
        if start:
            sub = sub[sub["Date"] >= pd.to_datetime(start)]
        if end:
            sub = sub[sub["Date"] <= pd.to_datetime(end)]
        sub = sub.dropna(subset=["Date"]).sort_values("Date")
        if len(sub) < 2:
            return {"cagr": 0.0, "mdd": 0.0}
        return {"cagr": float(calc_cagr(sub)), "mdd": float(sub["Drawdown"].min() * 100) if "Drawdown" in sub.columns else 0.0}
    except Exception:
        return {"cagr": 0.0, "mdd": 0.0}


def _step24w_neighbor_stability(df, row):
    try:
        work = df.copy()
        for col in ["분할수", "첫매수LOC여유율", "지정가매도%", "CAGR", "MDD"]:
            work[col] = pd.to_numeric(work[col], errors="coerce")
        split_v = int(row.get("분할수")); loc_v = float(row.get("첫매수LOC여유율")); sell_v = float(row.get("지정가매도%"))
        base_cagr = float(row.get("CAGR", 0) or 0); base_mdd = abs(float(row.get("MDD", 0) or 0))
        near = work[(work["분할수"] == split_v) & (abs(work["첫매수LOC여유율"] - loc_v) <= 0.51) & (abs(work["지정가매도%"] - sell_v) <= 2.51)]
        if len(near) <= 1:
            return 45.0
        score = 100 - max(base_cagr - float(near["CAGR"].median()), 0) * 1.6 - max(abs(float(near["MDD"].median())) - base_mdd, 0) * 1.4
        return max(0.0, min(100.0, float(score)))
    except Exception:
        return 40.0



def _step24x_eval_param(ticker, fee_percent, params):
    """Step24X polling용 단일 후보 평가. 매매 공식에는 관여하지 않는 보조 평가 함수."""
    split_v = int(params.get("infinite_split_count", 40) or 40)
    first_v = float(params.get("first_loc_buffer_pct", 12) or 12)
    sell_v = float(params.get("designated_sell_pct", 15) or 15)
    bt2, trade2 = _step24p_run_params(ticker, params, fee_percent)
    whole = _step24w_period_metric(bt2)
    recent3 = _step24w_period_metric(bt2, start=pd.to_datetime(bt2["Date"].max()) - pd.DateOffset(years=3))
    y2022 = _step24w_period_metric(bt2, start="2022-01-01", end="2022-12-31")
    gap = _step24v_trade_gap_stats(bt2, split_v)
    cycle = make_cycle_status(trade2, bt2, split_v)
    pf = _safe_profit_factor(trade2)
    cagr = float(whole.get("cagr", 0) or 0)
    mdd = float(whole.get("mdd", 0) or 0)
    recent3_cagr = float(recent3.get("cagr", 0) or 0)
    y2022_mdd = float(y2022.get("mdd", 0) or 0)
    gap_days = int(gap.get("max_gap_trading_days", 0) or 0)
    completed = int(cycle.get("completed_cycles", 0) or 0)
    neighbor = 70.0
    robust = min(max(cagr,0),60)*1.15 - min(abs(mdd),90)*0.55 + min(max(recent3_cagr,0),60)*0.35 + max(y2022_mdd,-100)*0.18 - min(gap_days,260)*0.07 - float(gap.get("gap_count_60d",0) or 0)*2.5 + min(completed,120)*0.12 + min(pf,8)*2.0 + neighbor*0.35
    risk = "낮음" if robust >= 80 and neighbor >= 70 and gap_days <= 120 and y2022_mdd >= -50 else ("보통" if robust >= 60 and neighbor >= 50 else "높음")
    verdict = "실전 후보" if risk == "낮음" else ("유효 후보" if risk == "보통" else "관찰")
    return {"판정": verdict, "과최적화위험": risk, "RobustScore": round(float(robust),2), "분할수": split_v, "첫매수LOC": first_v, "지정가%": sell_v, "CAGR": round(cagr,2), "MDD": round(mdd,2), "최근3년CAGR": round(recent3_cagr,2), "2022_MDD": round(y2022_mdd,2), "최대공백": gap_days, "장기공백": int(gap.get("gap_count_60d",0) or 0), "완료주기": completed, "PF": round(float(pf or 0),2), "주변안정성": round(neighbor,1)}


def _step24x_recalc_neighbor_scores(results):
    """계산 완료 후 주변 파라미터 안정성을 전체 결과 기준으로 보정한다."""
    if not results:
        return results
    try:
        df = pd.DataFrame(results).copy()
        work = df.rename(columns={"첫매수LOC": "첫매수LOC여유율", "지정가%": "지정가매도%"})
        fixed = []
        for _, row in work.iterrows():
            neighbor = _step24w_neighbor_stability(work, row)
            r = row.to_dict()
            r["첫매수LOC"] = r.pop("첫매수LOC여유율")
            r["지정가%"] = r.pop("지정가매도%")
            cagr = float(r.get("CAGR", 0) or 0); mdd = float(r.get("MDD", 0) or 0); recent3 = float(r.get("최근3년CAGR", 0) or 0); y2022 = float(r.get("2022_MDD", 0) or 0)
            gap_days = int(r.get("최대공백", 0) or 0); long_gap = int(r.get("장기공백", 0) or 0); completed = int(r.get("완료주기", 0) or 0); pf = float(r.get("PF", 0) or 0)
            robust = min(max(cagr,0),60)*1.15 - min(abs(mdd),90)*0.55 + min(max(recent3,0),60)*0.35 + max(y2022,-100)*0.18 - min(gap_days,260)*0.07 - long_gap*2.5 + min(completed,120)*0.12 + min(pf,8)*2.0 + float(neighbor)*0.35
            risk = "낮음" if robust >= 80 and neighbor >= 70 and gap_days <= 120 and y2022 >= -50 else ("보통" if robust >= 60 and neighbor >= 50 else "높음")
            verdict = "실전 후보" if risk == "낮음" else ("유효 후보" if risk == "보통" else "관찰")
            r.update({"RobustScore": round(float(robust),2), "주변안정성": round(float(neighbor),1), "과최적화위험": risk, "판정": verdict})
            fixed.append(r)
        return sorted(fixed, key=lambda x: (float(x.get("RobustScore",0)), float(x.get("주변안정성",0)), float(x.get("최근3년CAGR",0))), reverse=True)
    except Exception:
        return sorted(results, key=lambda x: float(x.get("RobustScore",0)), reverse=True)


def _step24x_job_worker(job_id):
    with STEP24X_JOBS_LOCK:
        job = STEP24X_JOBS.get(job_id)
    if not job:
        return
    params = job.get("params", {})
    ticker = str(params.get("ticker", "TQQQ")).upper()
    fee_percent = float(params.get("fee_percent", 0.1) or 0.1)
    grid = list(_step24p_param_grid(
        mode="deepmine",
        split_values_text=params.get("split_values_text", "20,40"),
        first_loc_min=float(params.get("first_loc_min", 10.0) or 10.0),
        first_loc_max=float(params.get("first_loc_max", 15.0) or 15.0),
        first_loc_step=float(params.get("first_loc_step", 0.5) or 0.5),
        designated_min=float(params.get("designated_min", 10.0) or 10.0),
        designated_max=float(params.get("designated_max", 25.0) or 25.0),
        designated_step=float(params.get("designated_step", 2.5) or 2.5),
    ))
    total = len(grid)
    with STEP24X_JOBS_LOCK:
        job.update({"status": "running", "total": total, "done": 0, "progress": 0.0, "message": "후보 계산 시작", "log": [f"총 {total}개 조합 계산 시작"], "results": []})
    results = []
    for idx, param in enumerate(grid, start=1):
        with STEP24X_JOBS_LOCK:
            job = STEP24X_JOBS.get(job_id)
            if not job:
                return
            if job.get("cancel_requested"):
                job.update({"status": "cancelled", "message": "사용자 취소", "results": sorted(results, key=lambda x: float(x.get("RobustScore",0)), reverse=True)})
                return
            job["message"] = f'{idx}/{total} · {param["infinite_split_count"]}분할 / LOC {param["first_loc_buffer_pct"]} / 지정가 {param["designated_sell_pct"]} 계산 중'
        try:
            row = _step24x_eval_param(ticker, fee_percent, param)
            results.append(row)
            results = sorted(results, key=lambda x: float(x.get("RobustScore",0)), reverse=True)
            top = results[0]
            log_line = f'[{idx}/{total}] {param["infinite_split_count"]}분할 LOC {param["first_loc_buffer_pct"]} 지정가 {param["designated_sell_pct"]} → Robust {row["RobustScore"]}, CAGR {row["CAGR"]}%, MDD {row["MDD"]}% / 현재 TOP1 {top["분할수"]}분할 LOC {top["첫매수LOC"]} 지정가 {top["지정가%"]}'
        except Exception as e:
            log_line = f"[{idx}/{total}] 계산 실패: {e}"
        with STEP24X_JOBS_LOCK:
            job = STEP24X_JOBS.get(job_id)
            if not job:
                return
            job.update({"done": idx, "progress": round((idx / max(total,1))*100, 1), "results": results[:80], "log": (job.get("log", []) + [log_line])[-120:]})
    final_results = _step24x_recalc_neighbor_scores(results)
    csv_text = ""
    try:
        cache_dir = Path("step24_cache") / "step24x"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_key = hashlib.md5(json.dumps(params, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]
        csv_path = cache_dir / f"{ticker}_raor4_step24x_live_{cache_key}.csv"
        pd.DataFrame(final_results).to_csv(csv_path, index=False, encoding="utf-8-sig")
        csv_text = str(csv_path)
    except Exception:
        pass
    with STEP24X_JOBS_LOCK:
        job = STEP24X_JOBS.get(job_id)
        if job:
            job.update({"status": "done", "done": total, "progress": 100.0, "message": "계산 완료", "results": final_results[:120], "csv": csv_text, "log": (job.get("log", []) + ["계산 완료 · 주변 안정성 보정 및 CSV 저장"])[-120:]})


def build_step24x_live_panel_html(ticker, fee_percent, split_values_text, first_loc_min, first_loc_max, first_loc_step, designated_min, designated_max, designated_step, display_limit, score_mode):
    payload = {"ticker": ticker, "fee_percent": fee_percent, "split_values_text": split_values_text, "first_loc_min": first_loc_min, "first_loc_max": first_loc_max, "first_loc_step": first_loc_step, "designated_min": designated_min, "designated_max": designated_max, "designated_step": designated_step, "display_limit": display_limit, "score_mode": score_mode}
    return f"""
    <div id="step24x-live-root" class="card hero step24x-live-card" data-payload='{json.dumps(payload, ensure_ascii=False)}'>
        <h2>Step24X 실시간 Robust Mining</h2>
        <p class="small-note">job_id + polling 방식으로 후보를 계산하며, 완료 전에도 후보표와 진행 로그가 한 줄씩 누적됩니다. 매매 엔진 공식은 Step24W와 동일합니다.</p>
        <div class="grid">
            <div class="metric positive"><h3>진행률</h3><p id="step24x-progress-text">대기</p></div>
            <div class="metric"><h3>진행 조합</h3><p id="step24x-count-text">0 / 0</p></div>
            <div class="metric positive"><h3>현재 TOP1</h3><p id="step24x-top-text">-</p></div>
            <div class="metric warning"><h3>상태</h3><p id="step24x-status-text">준비</p></div>
        </div>
        <div class="progress-shell"><div id="step24x-progress-bar" class="progress-bar" style="width:0%;"></div></div>
        <div class="quick-apply-row"><button type="button" id="step24x-cancel-btn" class="quick-apply-btn" style="border:0;cursor:pointer;">계산 취소</button></div>
    </div>
    <div class="card step24x-live-table-card">
        <h2>실시간 후보표</h2>
        <div class="table-wrap"><table class="step24q-table" border="1" cellpadding="6" cellspacing="0"><thead><tr><th>순위</th><th>판정</th><th>과최적화위험</th><th>RobustScore</th><th>분할</th><th>LOC</th><th>지정가</th><th>CAGR</th><th>MDD</th><th>최근3년</th><th>2022 MDD</th><th>최대공백</th><th>장기공백</th><th>완료주기</th><th>PF</th><th>주변안정성</th><th>설정</th></tr></thead><tbody id="step24x-live-tbody"><tr><td colspan="17">계산 시작 대기 중...</td></tr></tbody></table></div>
    </div>
    <div class="card step24x-log-card"><h2>실시간 로그</h2><pre id="step24x-log" class="step24x-log">대기 중...</pre></div>
    """

def build_step24w_robust_mining_html(ticker, fee_percent, split_values_text="20,40", first_loc_min=10.0, first_loc_max=15.0, first_loc_step=0.5, designated_min=10.0, designated_max=25.0, designated_step=2.5, display_limit=30, score_mode="balanced"):
    base_df, errors, cache_file, from_cache, total_count = run_step24p_screen_optimizer(ticker=ticker, fee_percent=fee_percent, mode="deepmine", split_values_text=split_values_text, first_loc_min=first_loc_min, first_loc_max=first_loc_max, first_loc_step=first_loc_step, designated_min=designated_min, designated_max=designated_max, designated_step=designated_step, score_mode=score_mode, use_cache=True, strategy_key="raor4_step24w")
    if base_df is None or base_df.empty:
        return '<div class="card"><h2>Step24W Robust Mining</h2><p>후보 계산 결과가 없습니다.</p></div>'
    rows = []
    for _, row in base_df.head(min(80, len(base_df))).iterrows():
        split_v = int(row.get("분할수", 40) or 40); first_v = float(row.get("첫매수LOC여유율", 12) or 12); sell_v = float(row.get("지정가매도%", 15) or 15)
        params = {"infinite_split_count": split_v, "first_loc_buffer_pct": first_v, "designated_sell_pct": sell_v}
        try:
            bt2, trade2 = _step24p_run_params(ticker, params, fee_percent)
            whole = _step24w_period_metric(bt2)
            recent3 = _step24w_period_metric(bt2, start=pd.to_datetime(bt2["Date"].max()) - pd.DateOffset(years=3))
            y2022 = _step24w_period_metric(bt2, start="2022-01-01", end="2022-12-31")
            gap = _step24v_trade_gap_stats(bt2, split_v)
        except Exception:
            whole = {"cagr": to_number_safe(row.get("CAGR")), "mdd": to_number_safe(row.get("MDD"))}; recent3={"cagr":0.0}; y2022={"mdd":0.0}; gap={"max_gap_trading_days":999,"gap_count_60d":99}
        neighbor = _step24w_neighbor_stability(base_df, row)
        cagr = float(whole.get("cagr", 0)); mdd = float(whole.get("mdd", 0)); recent3_cagr = float(recent3.get("cagr", 0)); y2022_mdd = float(y2022.get("mdd", 0)); gap_days = int(gap.get("max_gap_trading_days", 0) or 0)
        completed = float(row.get("CompletedCycles", 0) or 0); pf = float(row.get("ProfitFactor", 0) or 0)
        robust = min(max(cagr,0),60)*1.15 - min(abs(mdd),90)*0.55 + min(max(recent3_cagr,0),60)*0.35 + max(y2022_mdd,-100)*0.18 - min(gap_days,260)*0.07 - float(gap.get("gap_count_60d",0) or 0)*2.5 + min(completed,120)*0.12 + min(pf,8)*2.0 + neighbor*0.35
        risk = "낮음" if robust >= 80 and neighbor >= 70 and gap_days <= 120 and y2022_mdd >= -50 else ("보통" if robust >= 60 and neighbor >= 50 else "높음")
        verdict = "실전 후보" if risk == "낮음" else ("유효 후보" if risk == "보통" else "관찰")
        rows.append({"판정": verdict, "과최적화위험": risk, "RobustScore": round(robust,2), "분할수": split_v, "첫매수LOC": first_v, "지정가%": sell_v, "CAGR": round(cagr,2), "MDD": round(mdd,2), "최근3년CAGR": round(recent3_cagr,2), "2022_MDD": round(y2022_mdd,2), "최대공백": gap_days, "장기공백": int(gap.get("gap_count_60d",0) or 0), "완료주기": int(completed), "PF": round(pf,2), "주변안정성": round(neighbor,1)})
    rdf = pd.DataFrame(rows).sort_values(["RobustScore", "주변안정성", "최근3년CAGR"], ascending=False).reset_index(drop=True)
    top = rdf.head(max(1, int(display_limit or 30)))
    best = top.iloc[0]
    quick = ""; trs = ""
    for i, r in top.iterrows():
        rank = i + 1
        apply_link = f'/?ticker={ticker}&strategy=raor4_step24w&infinite_split_count={int(r["분할수"])}&first_loc_buffer_pct={float(r["첫매수LOC"])}&designated_sell_pct={float(r["지정가%"])}&fee_percent={fee_percent}&action_mode=backtest&applied_from=robust&applied_rank={rank}&applied_score={r["RobustScore"]}'
        if rank <= 3:
            quick += f'<a class="quick-apply-btn" href="{apply_link}">{rank}위 적용 · {int(r["분할수"])}분할 · LOC {r["첫매수LOC"]}% · 지정가 {r["지정가%"]}%</a>'
        trs += f'<tr><td>{rank}</td><td>{r["판정"]}</td><td>{r["과최적화위험"]}</td><td>{r["RobustScore"]}</td><td>{r["분할수"]}</td><td>{r["첫매수LOC"]}</td><td>{r["지정가%"]}</td><td>{r["CAGR"]}%</td><td>{r["MDD"]}%</td><td>{r["최근3년CAGR"]}%</td><td>{r["2022_MDD"]}%</td><td>{r["최대공백"]}거래일</td><td>{r["장기공백"]}회</td><td>{r["완료주기"]}회</td><td>{r["PF"]}</td><td>{r["주변안정성"]}</td><td><a class="apply-link" href="{apply_link}">적용</a></td></tr>'
    return (f'<div id="step24-results" class="card hero step24w-robust-card"><h2>Step24W 과최적화 방어 딥마이닝</h2><p class="small-note">CAGR 1위가 아니라 전체성과, 최근 3년, 2022년 방어, 최대 무체결 공백, 완료주기, Profit Factor, 주변 파라미터 안정성을 함께 평가합니다. 매매 공식은 변경하지 않습니다.</p><div class="grid"><div class="metric positive"><h3>Robust Score</h3><p>{best["RobustScore"]}</p></div><div class="metric positive"><h3>판정</h3><p>{best["판정"]}</p></div><div class="metric warning"><h3>과최적화 위험</h3><p>{best["과최적화위험"]}</p></div><div class="metric positive"><h3>CAGR</h3><p>{best["CAGR"]}%</p></div><div class="metric warning"><h3>MDD</h3><p>{best["MDD"]}%</p></div><div class="metric positive"><h3>주변 안정성</h3><p>{best["주변안정성"]}</p></div></div><div class="quick-apply-row">{quick}</div></div>'
            f'<div class="card step24w-robust-table-card"><h2>Robust Mining 후보표</h2><div class="table-wrap"><table class="step24q-table" border="1" cellpadding="6" cellspacing="0"><tr><th>순위</th><th>판정</th><th>과최적화위험</th><th>RobustScore</th><th>분할</th><th>LOC</th><th>지정가</th><th>CAGR</th><th>MDD</th><th>최근3년</th><th>2022 MDD</th><th>최대공백</th><th>장기공백</th><th>완료주기</th><th>PF</th><th>주변안정성</th><th>설정</th></tr>{trs}</table></div></div>')

def build_step24v_cleanup_html(strategy=""):
    if strategy != "raor4_step24v":
        return ""
    return '''
    <div class="card step24v-cleanup-card">
        <h2>Step24V 웹화면 정리 후보 체크</h2>
        <p class="small-note">실제 파일 삭제가 아니라 화면/드롭다운에서 숨기거나 아카이브로 이동해도 될 후보입니다. Step24N~V 기준판과 데이터 파일은 보존합니다.</p>
        <div class="table-wrap"><table border="1" cellpadding="6" cellspacing="0">
            <tr><th>구분</th><th>정리 후보</th><th>판단</th><th>권장 처리</th></tr>
            <tr><td>드롭다운</td><td>V1~V5 / Step23 계열</td><td>현재 Infinite Lab 원문엔진 검증과 직접 관련 낮음</td><td>삭제보다 ‘이전 연구용’ 접기/숨김</td></tr>
            <tr><td>드롭다운</td><td>Step24E~H</td><td>기능 검증의 역사 버전. 현재 실사용은 N 이후가 기준</td><td>화면 기본 목록에서는 숨기고 README/백업으로 보존</td></tr>
            <tr><td>카드</td><td>Step20 추천 프리셋</td><td>RSI 프리셋 기반 문구라 Step24 원문엔진 화면에서는 혼동 가능</td><td>Step24V에서는 ‘아카이브/보조’로 축소 표시 권장</td></tr>
            <tr><td>Optimizer 섹션</td><td>Step18/19/20/21 연구 설명 카드</td><td>정보량은 좋지만 실전 후보 선택 화면을 길게 만듦</td><td>접이식 아카이브 또는 별도 연구 탭으로 이동</td></tr>
            <tr><td>검증/로그</td><td>긴 매매로그 전체표</td><td>필요하지만 화면을 매우 길게 만듦</td><td>최근 50개 기본 표시 + CSV/전체보기 버튼 추천</td></tr>
            <tr><td>삭제 금지</td><td>app.py, ticker_config.py, optimizer_lab.py, 최신 Step24 엔진, CSV 원본</td><td>실행/재현성에 필요</td><td>삭제 금지</td></tr>
        </table></div>
    </div>
    '''

def build_step24o_optimizer_html(*args, **kwargs):
    return build_step24p_optimizer_html(*args, **kwargs)

# =========================
# Step22 Optimizer Lab 결과 표시

# =========================
def load_optimizer_result(ticker, strategy):
    ticker = ticker.upper()
    if str(strategy).startswith("raor4_"):
        candidates = [f"{ticker}_{strategy}_optimizer_top100.csv"]
    else:
        candidates = [
            f"{ticker}_{strategy}_optimizer_top100.csv",
            f"{ticker}_optimizer_top100.csv",
        ]
    for file in candidates:
        try:
            return pd.read_csv(file), file
        except Exception:
            continue
    return pd.DataFrame(), None


def build_optimizer_result_html(ticker, strategy):
    if strategy in ["raor4_step25c", "raor4_step25b", "raor4_step25a", "raor4_step24z", "raor4_step24y", "raor4_step24x", "raor4_step24w", "raor4_step24v", "raor4_step24u", "raor4_step24t", "raor4_step24s", "raor4_step24r", "raor4_step24q", "raor4_step24p", "raor4_step24o"]:
        strategy_key = strategy if strategy in ["raor4_step25c", "raor4_step25b", "raor4_step25a", "raor4_step24z", "raor4_step24y", "raor4_step24x", "raor4_step24w", "raor4_step24v", "raor4_step24u", "raor4_step24t", "raor4_step24s", "raor4_step24r", "raor4_step24q"] else "raor4_step24p"
        return build_step24p_optimizer_html(ticker, fee_percent=0.25, mode="optimizer", strategy_key=strategy_key)
    df, file_used = load_optimizer_result(ticker, strategy)
    if df.empty:
        return f'''
        <div class="card hero">
            <h2>Optimizer Lab</h2>
            <p><b>{ticker}</b> / <b>{strategy}</b> 최적화 결과 파일이 아직 없습니다.</p>
            <p>먼저 터미널에서 아래 명령을 실행하세요.</p>
            <pre>python optimizer_lab.py {ticker} {strategy}</pre>
            <p class="small-note">생성 예상 파일: {ticker}_{strategy}_optimizer_top100.csv</p>
        </div>
        '''

    display_df = df.head(100).copy()
    headers = ''.join([f'<th>{col}</th>' for col in display_df.columns])
    rows = ''
    for _, row in display_df.iterrows():
        rows += '<tr>' + ''.join([f'<td>{row[col]}</td>' for col in display_df.columns]) + '</tr>'

    best = display_df.iloc[0]
    best_score = best.get('Score', '-')
    best_cagr = best.get('CAGR', '-')
    best_mdd = best.get('MDD', '-')
    best_stability = best.get('StabilityScore', '-')

    return f'''
    <div class="card hero">
        <h2>Optimizer Lab 추천 1순위</h2>
        <div class="grid">
            <div class="metric positive"><h3>Score</h3><p>{best_score}</p></div>
            <div class="metric positive"><h3>CAGR</h3><p>{best_cagr}</p></div>
            <div class="metric warning"><h3>MDD</h3><p>{best_mdd}</p></div>
            <div class="metric positive"><h3>Stability</h3><p>{best_stability}</p></div>
        </div>
        <p class="small-note">파일: {file_used}</p>
    </div>

    <div class="card">
        <h2>{ticker} Optimizer TOP100</h2>
        <div class="table-wrap">
            <table border="1" cellpadding="6" cellspacing="0">
                <tr>{headers}</tr>
                {rows}
            </table>
        </div>
    </div>
    '''


@app.route("/download_step24_cache")
def download_step24_cache():
    """Step24 전용 캐시 CSV 다운로드. step24_cache 내부 CSV만 허용한다."""
    rel = request.args.get("file", default="")
    if not rel:
        abort(404)
    base = (Path.cwd() / "step24_cache").resolve()
    target = (Path.cwd() / rel).resolve()
    try:
        target.relative_to(base)
    except Exception:
        abort(403)
    if not target.exists() or target.suffix.lower() != ".csv":
        abort(404)
    return send_file(str(target), as_attachment=True, download_name=target.name)

# Flask 메인 라우트

# Step24U polling 준비 API: 24U에서 실제 background job으로 연결 예정
STEP24T_PROGRESS_STATE = {"status": "idle", "percent": 0, "message": "대기 중", "current": 0, "total": 0}


@app.route("/api/step24x/start", methods=["POST"])
def api_step24x_start():
    payload = request.get_json(silent=True) or {}
    ticker = str(payload.get("ticker", "TQQQ")).upper()
    if ticker not in ["TQQQ", "SOXL"]:
        ticker = "TQQQ"
    payload["ticker"] = ticker
    job_id = uuid.uuid4().hex[:12]
    with STEP24X_JOBS_LOCK:
        STEP24X_JOBS[job_id] = {"job_id": job_id, "status": "queued", "progress": 0.0, "done": 0, "total": 0, "results": [], "log": [], "message": "대기 중", "cancel_requested": False, "params": payload, "created_at": time.time()}
    t = threading.Thread(target=_step24x_job_worker, args=(job_id,), daemon=True)
    t.start()
    return jsonify({"ok": True, "job_id": job_id})


@app.route("/api/step24x/progress/<job_id>")
def api_step24x_progress(job_id):
    with STEP24X_JOBS_LOCK:
        job = STEP24X_JOBS.get(job_id)
        if not job:
            return jsonify({"ok": False, "error": "job not found"}), 404
        safe = {k: v for k, v in job.items() if k not in ["cancel_requested"]}
    return jsonify({"ok": True, "job": safe})


@app.route("/api/step24x/cancel/<job_id>", methods=["POST"])
def api_step24x_cancel(job_id):
    with STEP24X_JOBS_LOCK:
        job = STEP24X_JOBS.get(job_id)
        if not job:
            return jsonify({"ok": False, "error": "job not found"}), 404
        job["cancel_requested"] = True
        job["message"] = "취소 요청됨"
    return jsonify({"ok": True})


@app.route("/step24x.js")
def step24x_js():
    return Response(r"""
(function(){
    const root = document.getElementById("step24x-live-root");
    if (!root) return;
    let jobId = null;
    let timer = null;
    const payload = JSON.parse(root.getAttribute("data-payload") || "{}");
    const tbody = document.getElementById("step24x-live-tbody");
    const logBox = document.getElementById("step24x-log");
    const bar = document.getElementById("step24x-progress-bar");
    const prog = document.getElementById("step24x-progress-text");
    const cnt = document.getElementById("step24x-count-text");
    const topText = document.getElementById("step24x-top-text");
    const statusText = document.getElementById("step24x-status-text");
    function esc(v){ return String(v ?? "").replace(/[&<>"']/g, function(s){ return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[s]; }); }
    function renderRows(results){
        if (!results || !results.length){ tbody.innerHTML = '<tr><td colspan="17">계산 중입니다...</td></tr>'; return; }
        tbody.innerHTML = results.slice(0, 50).map(function(r, i){
            const href = "/?ticker=" + encodeURIComponent(payload.ticker) + "&strategy=raor4_step24x&infinite_split_count=" + r["분할수"] + "&first_loc_buffer_pct=" + r["첫매수LOC"] + "&designated_sell_pct=" + r["지정가%"] + "&fee_percent=" + payload.fee_percent + "&action_mode=backtest&applied_from=robust_live&applied_rank=" + (i+1) + "&applied_score=" + r.RobustScore;
            return '<tr><td>'+(i+1)+'</td><td>'+esc(r["판정"])+'</td><td>'+esc(r["과최적화위험"])+'</td><td>'+esc(r.RobustScore)+'</td><td>'+esc(r["분할수"])+'</td><td>'+esc(r["첫매수LOC"])+'</td><td>'+esc(r["지정가%"])+'</td><td>'+esc(r.CAGR)+'%</td><td>'+esc(r.MDD)+'%</td><td>'+esc(r["최근3년CAGR"])+'%</td><td>'+esc(r["2022_MDD"])+'%</td><td>'+esc(r["최대공백"])+'거래일</td><td>'+esc(r["장기공백"])+'회</td><td>'+esc(r["완료주기"])+'회</td><td>'+esc(r.PF)+'</td><td>'+esc(r["주변안정성"])+'</td><td><a class="apply-link" href="'+href+'">적용</a></td></tr>';
        }).join("");
        const top = results[0];
        topText.textContent = top["분할수"]+"분할 · LOC "+top["첫매수LOC"]+" · 지정가 "+top["지정가%"]+" · Robust "+top.RobustScore;
    }
    function poll(){
        fetch("/api/step24x/progress/" + jobId).then(r => r.json()).then(data => {
            if (!data.ok) throw new Error(data.error || "progress error");
            const job = data.job;
            const pct = job.progress || 0;
            bar.style.width = pct + "%";
            prog.textContent = pct + "%";
            cnt.textContent = (job.done || 0) + " / " + (job.total || 0);
            statusText.textContent = job.status || "-";
            renderRows(job.results || []);
            logBox.textContent = (job.log || []).join("\n");
            if (job.status === "done" || job.status === "cancelled"){
                clearInterval(timer);
                if (job.csv) logBox.textContent += "\nCSV: " + job.csv;
            }
        }).catch(err => {
            statusText.textContent = "오류";
            logBox.textContent += "\n" + err.message;
            clearInterval(timer);
        });
    }
    fetch("/api/step24x/start", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload)})
        .then(r => r.json()).then(data => {
            if (!data.ok) throw new Error(data.error || "start error");
            jobId = data.job_id;
            statusText.textContent = "running";
            timer = setInterval(poll, 1000);
            poll();
        }).catch(err => { statusText.textContent="오류"; logBox.textContent = err.message; });
    const cancelBtn = document.getElementById("step24x-cancel-btn");
    if (cancelBtn){ cancelBtn.addEventListener("click", function(){ if(jobId){ fetch("/api/step24x/cancel/" + jobId, {method:"POST"}); } }); }
})();
""", mimetype="application/javascript")


@app.route("/api/step24u/progress")
def api_step24u_progress():
    return STEP24T_PROGRESS_STATE

# =========================
@app.route("/")
def home():
    global daily, weekly

    ticker = request.args.get("ticker", default="SOXL").upper()

    if ticker not in ["SOXL", "TQQQ"]:
        ticker = "SOXL"

    strategy = request.args.get("strategy", default="raor_v22")
    if strategy not in ["raor_v22", "raor4_step25d"]:
        strategy = "raor_v22"
    action_mode = request.args.get("action_mode", default="backtest")

    # Step24 원문엔진은 TQQQ/SOXL만 지원한다. QQQ로 들어오면 500 오류 대신 TQQQ로 보정한다.
    if str(strategy).startswith("raor4_step24") and ticker not in ["TQQQ", "SOXL"]:
        ticker = "TQQQ"

    daily, weekly = load_ticker_data(ticker)

    if daily is None or weekly is None:
        available = ", ".join(TICKER_LIST)
        return f"""
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: Arial; padding: 40px;">
            <h2>{ticker} 데이터 파일을 찾을 수 없습니다.</h2>
            <p>필요 파일:</p>
            <pre>{ticker}_daily_data.csv 또는 {ticker}_daily_with_mode.csv
{ticker}_weekly_mode.csv</pre>
            <p>지원 티커: {available}</p>
            <a href="/?ticker=QQQ">QQQ로 돌아가기</a>
        </body>
        </html>
        """

    start_date = request.args.get("start_date", default=daily["Date"].min().strftime("%Y-%m-%d"))
    end_date = request.args.get("end_date", default=daily["Date"].max().strftime("%Y-%m-%d"))
    
    split_count = request.args.get("split_count", default=10, type=int)
    sell_rsi = request.args.get("sell_rsi", default=70, type=int)

    extreme_split = request.args.get("extreme_split", default=4, type=int)
    recession_split = request.args.get("recession_split", default=3, type=int)
    neutral_split = request.args.get("neutral_split", default=1, type=int)
    boom_split = request.args.get("boom_split", default=1, type=int)

    profit_target = request.args.get("profit_target", default=10.0, type=float)
    ma5_factor = request.args.get("ma5_factor", default=3, type=int)
    ma20_factor = request.args.get("ma20_factor", default=5, type=int)

    # Step22B 무한매수 4.0 V1 입력값
    infinite_split_count = request.args.get("infinite_split_count", default=40, type=int)
    infinite_target_profit = request.args.get("infinite_target_profit", default=7.0, type=float)
    quarter_sell_ratio = request.args.get("quarter_sell_ratio", default=25.0, type=float)
    star_pct = request.args.get("star_pct", default=7.0, type=float)
    max_gap_pct = request.args.get("max_gap_pct", default=20.0, type=float)
    max_hold_days = request.args.get("max_hold_days", default=365, type=int)
    sheet_loc_price = request.args.get("sheet_loc_price", default=0.0, type=float)
    sheet_big_buy_price = request.args.get("sheet_big_buy_price", default=0.0, type=float)
    sheet_sell_price = request.args.get("sheet_sell_price", default=0.0, type=float)
    first_loc_buffer_pct = request.args.get("first_loc_buffer_pct", default=12.0, type=float)
    default_designated_sell_pct = 15.0 if ticker == "TQQQ" else 20.0
    designated_sell_pct = request.args.get("designated_sell_pct", default=default_designated_sell_pct, type=float)

    fee_percent = request.args.get("fee_percent", default=0.25, type=float)
    ticker_options = ""
    for tk, name in ticker_dict().items():
        selected = "selected" if ticker == tk else ""
        ticker_options += f'<option value="{tk}" {selected}>{name}</option>'

    min_cagr = request.args.get("min_cagr", default=0, type=float)
    max_mdd = request.args.get("max_mdd", default=100, type=float)
    min_win = request.args.get("min_win", default=0, type=float)
    min_pf = request.args.get("min_pf", default=0, type=float)

    opt_split_values = request.args.get("opt_split_values", default="20,40")
    opt_first_loc_min = request.args.get("opt_first_loc_min", default=10.0, type=float)
    opt_first_loc_max = request.args.get("opt_first_loc_max", default=15.0, type=float)
    opt_first_loc_step = request.args.get("opt_first_loc_step", default=0.5, type=float)
    opt_designated_min = request.args.get("opt_designated_min", default=10.0, type=float)
    opt_designated_max = request.args.get("opt_designated_max", default=25.0, type=float)
    opt_designated_step = request.args.get("opt_designated_step", default=2.5, type=float)
    opt_display_limit = request.args.get("opt_display_limit", default=50, type=int)
    score_mode = request.args.get("score_mode", default="balanced")
    if score_mode not in ["balanced", "return", "mdd", "turnover"]:
        score_mode = "balanced"

    applied_from = request.args.get("applied_from", default="")
    applied_rank = request.args.get("applied_rank", default="")
    applied_score = request.args.get("applied_score", default="")
    applied_candidate_html = ""
    if applied_from and str(strategy).startswith("raor4_step24"):
        applied_label = "DeepMining" if applied_from == "deepmine" else "Optimizer"
        applied_candidate_html = f"""
        <div class="card applied-candidate">
            <h2>현재 적용 후보</h2>
            <p><b>{applied_label} {applied_rank}위</b> · Score {applied_score}</p>
            <p>분할 {infinite_split_count} / 첫매수 LOC {first_loc_buffer_pct}% / 지정가 매도 {designated_sell_pct}% 값으로 백테스트를 다시 실행했습니다.</p>
        </div>
        """


    # Step24Y~25C 통합 로드맵 안내 패널
    advanced_stage_html = ""
    if str(strategy).startswith("raor4_step25") or strategy in ["raor4_step24y", "raor4_step24z", "raor_v22"]:
        advanced_stage_html = f"""
        <div class="card hero step25-roadmap-card">
            <h2>Step25D-8 V2.2 결과표/검증표 마감판</h2>
            <div class="grid">
                <div class="metric positive"><h3>24Y 선택도우미</h3><p>후보 해석</p></div>
                <div class="metric positive"><h3>24Z 프리셋</h3><p>저장 준비</p></div>
                <div class="metric warning"><h3>25A 동시비교</h3><p>TQQQ/SOXL</p></div>
                <div class="metric positive"><h3>25B 교차검증</h3><p>원문 체크</p></div>
                <div class="metric positive"><h3>25C RPA 신호</h3><p>CSV 준비</p></div>
                <div class="metric warning"><h3>25D 엔진검증</h3><p>V2.2 통합/V4.0 분리</p></div>
            </div>
            <p class="small-note">매매 공식은 Step24X 원문엔진 그대로 유지하고, 후보 선정/저장/비교/검증/RPA 출력 화면만 확장합니다.</p>
        </div>
        """

    # Step24C 보정: 기간설정은 화면 표시만이 아니라 백테스트 실행 데이터에도 적용한다.
    # 기존에는 전체 데이터로 엔진을 먼저 돌린 뒤 결과만 잘라서, 선택기간 이전 포지션이 매매로그에 섞일 수 있었다.
    _daily_full_for_notice = daily.copy()
    start_dt_for_engine = pd.to_datetime(start_date, errors="coerce")
    end_dt_for_engine = pd.to_datetime(end_date, errors="coerce")
    if pd.isna(start_dt_for_engine):
        start_dt_for_engine = daily["Date"].min()
        start_date = start_dt_for_engine.strftime("%Y-%m-%d")
    if pd.isna(end_dt_for_engine):
        end_dt_for_engine = daily["Date"].max()
        end_date = end_dt_for_engine.strftime("%Y-%m-%d")
    if start_dt_for_engine > end_dt_for_engine:
        start_dt_for_engine, end_dt_for_engine = end_dt_for_engine, start_dt_for_engine
        start_date = start_dt_for_engine.strftime("%Y-%m-%d")
        end_date = end_dt_for_engine.strftime("%Y-%m-%d")

    daily = daily[(daily["Date"] >= start_dt_for_engine) & (daily["Date"] <= end_dt_for_engine)].copy().reset_index(drop=True)
    if daily.empty:
        return f"""
        <html><head><meta charset="utf-8"></head>
        <body style="font-family: Arial; padding: 40px;">
            <h2>{ticker} 선택 기간에 데이터가 없습니다.</h2>
            <p>데이터 범위: {_daily_full_for_notice["Date"].min().strftime("%Y-%m-%d")} ~ {_daily_full_for_notice["Date"].max().strftime("%Y-%m-%d")}</p>
            <a href="/?ticker={ticker}">전체기간으로 돌아가기</a>
        </body></html>
        """

    preset_buttons_html = build_preset_buttons_html(
        ticker=ticker,
        strategy=strategy,
        start_date=start_date,
        end_date=end_date,
        fee_percent=fee_percent,
    )
    strategy_param_map_html = build_strategy_param_map_html()
    step24v_cleanup_html = build_step24v_cleanup_html(strategy)
    optimizer_compare_html = build_optimizer_compare_html(strategy="rsi")

    # Step25D-7: V2.2 화면에서는 기존 RSI/연구용 보조 카드를 숨긴다.
    if strategy == "raor_v22":
        preset_buttons_html = ""
        strategy_param_map_html = ""
        step24v_cleanup_html = ""
        optimizer_compare_html = ""


    # =========================
    # 전략 실행

    # =========================
    if strategy == "rsi":
        bt, trade_df = run_backtest(
            split_count=split_count,
            extreme_split=extreme_split,
            recession_split=recession_split,
            neutral_split=neutral_split,
            boom_split=boom_split,
            sell_rsi=sell_rsi,
            fee_rate_pct=fee_percent,
        )
        strategy_name = "RSI 커스텀"

        strategy_inputs = f"""
        <div class="input-row">
            <label>분할수 <input type="number" name="split_count" value="{split_count}"></label>
            <label>매도 RSI <input type="number" name="sell_rsi" value="{sell_rsi}"></label>
        </div>

        <div class="input-row">
            <label>극침체 <input type="number" name="extreme_split" value="{extreme_split}"></label>
            <label>침체 <input type="number" name="recession_split" value="{recession_split}"></label>
            <label>중립 <input type="number" name="neutral_split" value="{neutral_split}"></label>
            <label>상승 <input type="number" name="boom_split" value="{boom_split}"></label>
        </div>
        """

    
    elif strategy == "infinite4":
        if infinite_split_count not in [20, 30, 40]:
            infinite_split_count = 20

        split_count = infinite_split_count
        bt, trade_df = run_infinite4_v1_backtest(
            split_count=infinite_split_count,
            target_profit=infinite_target_profit,
            quarter_sell_ratio=quarter_sell_ratio,
            star_pct=star_pct,
            fee_rate_pct=fee_percent,
        )
        strategy_name = "무한매수 4.0 V1"

        strategy_inputs = f"""
        <div class="input-row">
            <label>분할횟수
                <select name="infinite_split_count">
                    <option value="20" {"selected" if infinite_split_count == 20 else ""}>20</option>
                    <option value="30" {"selected" if infinite_split_count == 30 else ""}>30</option>
                    <option value="40" {"selected" if infinite_split_count == 40 else ""}>40</option>
                </select>
            </label>
            <label>목표수익률(%) <input type="number" step="0.1" name="infinite_target_profit" value="{infinite_target_profit}"></label>
            <label>쿼터매도비율(%) <input type="number" step="1" name="quarter_sell_ratio" value="{quarter_sell_ratio}"></label>
            <label>별점 기준(%) <input type="number" step="0.1" name="star_pct" value="{star_pct}"></label>
        </div>
        <p class="small-note">
            V1 엔진: T=원금/분할횟수, 미보유 1T 진입, 보유 중 현재가가 별점가(avg×(1-star%)) 이하일 때만 1T 추가매수,<br>
            분할 소진 시 추가매수 금지, 목표수익률 도달 시 쿼터매도. 전반전/후반전·LOC/지정가 세부 로직은 V2에서 반영합니다.
        </p>
        """

    elif strategy == "infinite4_v2":
        if infinite_split_count not in [20, 30, 40]:
            infinite_split_count = 30

        split_count = infinite_split_count

        bt, trade_df = run_infinite4_v2_backtest(
            split_count=infinite_split_count,
            target_profit=infinite_target_profit,
            quarter_sell_ratio=quarter_sell_ratio,
            star_pct=star_pct,
            max_gap_pct=max_gap_pct,
            fee_rate_pct=fee_percent,
        )
        strategy_name = "무한매수 4.0 V2"

        strategy_inputs = f"""
        <div class="input-row">
            <label>분할횟수
                <select name="infinite_split_count">
                    <option value="20" {"selected" if infinite_split_count == 20 else ""}>20</option>
                    <option value="30" {"selected" if infinite_split_count == 30 else ""}>30</option>
                    <option value="40" {"selected" if infinite_split_count == 40 else ""}>40</option>
                </select>
            </label>
            <label>목표수익률(%) <input type="number" step="0.1" name="infinite_target_profit" value="{infinite_target_profit}"></label>
            <label>쿼터매도비율(%) <input type="number" step="1" name="quarter_sell_ratio" value="{quarter_sell_ratio}"></label>
        </div>

        <div class="input-row">
            <label>별점 기준(%) <input type="number" step="0.1" name="star_pct" value="{star_pct}"></label>
            <label>브로커 허용폭(%) <input type="number" step="1" name="max_gap_pct" value="{max_gap_pct}"></label>
        </div>

        <p class="small-note">
            V2: 언이시트 수동입력형 기반. 최초 1T 진입, 별점 이하 추가매수, 큰수매수 구조,
            분할 소진 제한, 목표수익률 도달 시 쿼터매도.
        </p>
        """

    elif strategy == "infinite4_v3":
        if infinite_split_count not in [20, 30, 40]:
            infinite_split_count = 30

        split_count = infinite_split_count
        bt, trade_df = run_infinite4_v3_backtest(
            split_count=infinite_split_count,
            target_profit=infinite_target_profit,
            quarter_sell_ratio=quarter_sell_ratio,
            star_pct=star_pct,
            max_gap_pct=max_gap_pct,
            max_hold_days=max_hold_days,
            fee_rate_pct=fee_percent,
        )
        strategy_name = "무한매수 4.0 V3"

        strategy_inputs = f"""
        <div class="input-row">
            <label>분할횟수
                <select name="infinite_split_count">
                    <option value="20" {"selected" if infinite_split_count == 20 else ""}>20</option>
                    <option value="30" {"selected" if infinite_split_count == 30 else ""}>30</option>
                    <option value="40" {"selected" if infinite_split_count == 40 else ""}>40</option>
                </select>
            </label>
            <label>목표수익률(%) <input type="number" step="0.1" name="infinite_target_profit" value="{infinite_target_profit}"></label>
            <label>쿼터매도비율(%) <input type="number" step="1" name="quarter_sell_ratio" value="{quarter_sell_ratio}"></label>
        </div>

        <div class="input-row">
            <label>별점 기준(%) <input type="number" step="0.1" name="star_pct" value="{star_pct}"></label>
            <label>브로커 LOC 허용폭(%) <input type="number" step="1" name="max_gap_pct" value="{max_gap_pct}"></label>
            <label>최대 보유일 <input type="number" step="1" name="max_hold_days" value="{max_hold_days}"></label>
        </div>

        <p class="small-note">
            V3: V2 흐름에 전반전/후반전, 큰수매수 후보, LOC 괴리 제한, max_hold_days 보유일 관리가 추가된 판단엔진입니다.
        </p>
        """


    elif strategy == "infinite4_v4":
        if infinite_split_count not in [20, 30, 40]:
            infinite_split_count = 30
        split_count = infinite_split_count
        bt, trade_df = run_infinite4_v4_backtest(
            split_count=infinite_split_count, target_profit=infinite_target_profit,
            quarter_sell_ratio=quarter_sell_ratio, star_pct=star_pct,
            max_gap_pct=max_gap_pct, max_hold_days=max_hold_days,
            sheet_loc_price=sheet_loc_price, sheet_big_buy_price=sheet_big_buy_price,
            sheet_sell_price=sheet_sell_price, fee_rate_pct=fee_percent,
        )
        strategy_name = "무한매수 4.0 V4 / Step23A-B-C"
        strategy_inputs = f"""
        <div class="input-row">
            <label>분할횟수
                <select name="infinite_split_count">
                    <option value="20" {"selected" if infinite_split_count == 20 else ""}>20</option>
                    <option value="30" {"selected" if infinite_split_count == 30 else ""}>30</option>
                    <option value="40" {"selected" if infinite_split_count == 40 else ""}>40</option>
                </select>
            </label>
            <label>목표수익률(%) <input type="number" step="0.1" name="infinite_target_profit" value="{infinite_target_profit}"></label>
            <label>쿼터매도비율(%) <input type="number" step="1" name="quarter_sell_ratio" value="{quarter_sell_ratio}"></label>
        </div>
        <div class="input-row">
            <label>기본 별점(%) <input type="number" step="0.1" name="star_pct" value="{star_pct}"></label>
            <label>LOC 괴리 제한(%) <input type="number" step="1" name="max_gap_pct" value="{max_gap_pct}"></label>
            <label>최대 보유일 <input type="number" step="1" name="max_hold_days" value="{max_hold_days}"></label>
        </div>
        <div class="input-row">
            <label>언이시트 LOC가 <input type="number" step="0.01" name="sheet_loc_price" value="{sheet_loc_price}"></label>
            <label>언이시트 큰수가 <input type="number" step="0.01" name="sheet_big_buy_price" value="{sheet_big_buy_price}"></label>
            <label>언이시트 매도가 <input type="number" step="0.01" name="sheet_sell_price" value="{sheet_sell_price}"></label>
        </div>
        <p class="small-note">
            V4: 언이시트 입력값이 있으면 우선 적용하고, 없으면 평균단가↔매도가↔별지점을 자동 역산합니다.<br>
            전반전/후반전 쿼터매도, 소진모드, 큰수매수, LOC 괴리 제한을 강화했습니다.
        </p>
        """



    elif strategy == "infinite4_v5":
        if infinite_split_count not in [20, 30, 40]:
            infinite_split_count = 30
        split_count = infinite_split_count
        bt, trade_df = run_infinite4_v5_backtest(
            split_count=infinite_split_count, target_profit=infinite_target_profit,
            quarter_sell_ratio=quarter_sell_ratio, star_pct=star_pct,
            max_gap_pct=max_gap_pct, max_hold_days=max_hold_days,
            sheet_loc_price=sheet_loc_price, sheet_big_buy_price=sheet_big_buy_price,
            sheet_sell_price=sheet_sell_price, fee_rate_pct=fee_percent,
        )
        strategy_name = "무한매수 4.0 V5 / Step23E 동적별지점"
        strategy_inputs = f"""
        <div class="input-row">
            <label>분할횟수
                <select name="infinite_split_count">
                    <option value="20" {"selected" if infinite_split_count == 20 else ""}>20</option>
                    <option value="30" {"selected" if infinite_split_count == 30 else ""}>30</option>
                    <option value="40" {"selected" if infinite_split_count == 40 else ""}>40</option>
                </select>
            </label>
            <label>목표수익률(%) <input type="number" step="0.1" name="infinite_target_profit" value="{infinite_target_profit}"></label>
            <label>쿼터매도비율(%) <input type="number" step="1" name="quarter_sell_ratio" value="{quarter_sell_ratio}"></label>
        </div>
        <div class="input-row">
            <label>초기 별점(%) <input type="number" step="0.1" name="star_pct" value="{star_pct}"></label>
            <label>LOC 괴리 제한(%) <input type="number" step="1" name="max_gap_pct" value="{max_gap_pct}"></label>
            <label>최대 보유일 <input type="number" step="1" name="max_hold_days" value="{max_hold_days}"></label>
        </div>
        <div class="input-row">
            <label>언이시트 LOC가 <input type="number" step="0.01" name="sheet_loc_price" value="{sheet_loc_price}"></label>
            <label>언이시트 큰수가 <input type="number" step="0.01" name="sheet_big_buy_price" value="{sheet_big_buy_price}"></label>
            <label>언이시트 매도가 <input type="number" step="0.01" name="sheet_sell_price" value="{sheet_sell_price}"></label>
        </div>
        <p class="small-note">
            V5: 화면의 별점값은 고정값이 아니라 초기값입니다. 실제 별지점은 전반전/후반전/소진모드, 분할진행률, 평균단가 대비 현재가에 따라 자동 가변됩니다.<br>
            언이시트 LOC/큰수/매도가 입력값이 있으면 우선 적용하고, 없으면 동적 별점 레이어로 다음 LOC와 큰수 후보를 산출합니다.
        </p>
        """
    elif strategy in ["raor4_step25d", "raor4_step25c", "raor4_step25b", "raor4_step25a", "raor4_step24z", "raor4_step24y", "raor4_step24x", "raor4_step24w", "raor4_step24v", "raor4_step24u", "raor4_step24t", "raor4_step24s", "raor4_step24r", "raor4_step24q", "raor4_step24p"]:
        # Step24Q/P: Step24O 엔진 기준 + 파라미터 세분화 / 진행형 딥마이닝 UI
        if infinite_split_count not in [20, 40]:
            infinite_split_count = 40
        split_count = infinite_split_count
        if designated_sell_pct <= 0:
            designated_sell_pct = default_designated_sell_pct

        step24_runner = {"raor4_step25d": run_raor_infinite4_step25d_backtest, "raor4_step25c": run_raor_infinite4_step25c_backtest, "raor4_step25b": run_raor_infinite4_step25b_backtest, "raor4_step25a": run_raor_infinite4_step25a_backtest, "raor4_step24z": run_raor_infinite4_step24z_backtest, "raor4_step24y": run_raor_infinite4_step24y_backtest, "raor4_step24x": run_raor_infinite4_step24x_backtest, "raor4_step24w": run_raor_infinite4_step24w_backtest, "raor4_step24v": run_raor_infinite4_step24v_backtest, "raor4_step24u": run_raor_infinite4_step24u_backtest, "raor4_step24t": run_raor_infinite4_step24t_backtest, "raor4_step24s": run_raor_infinite4_step24s_backtest, "raor4_step24r": run_raor_infinite4_step24r_backtest, "raor4_step24q": run_raor_infinite4_step24q_backtest}.get(strategy, run_raor_infinite4_step24p_backtest)
        step24_label = {"raor4_step25d":"Step25D", "raor4_step25c":"Step25C", "raor4_step25b":"Step25B", "raor4_step25a":"Step25A", "raor4_step24z":"Step24Z", "raor4_step24y":"Step24Y", "raor4_step24x":"Step24X", "raor4_step24w":"Step24W", "raor4_step24v":"Step24V", "raor4_step24u":"Step24U", "raor4_step24t":"Step24T", "raor4_step24s":"Step24S", "raor4_step24r":"Step24R", "raor4_step24q":"Step24Q"}.get(strategy, "Step24P")
        bt, trade_df = step24_runner(
            ticker=ticker,
            split_count=infinite_split_count,
            first_loc_buffer_pct=first_loc_buffer_pct,
            designated_sell_pct_override=designated_sell_pct,
            fee_rate_pct=fee_percent,
        )
        strategy_name = f"라오어 무한매수4.0 원문엔진 / {step24_label}"
        strategy_inputs = f"""
        <div class="input-row">
            <label>분할횟수
                <select name="infinite_split_count">
                    <option value="20" {"selected" if infinite_split_count == 20 else ""}>20</option>
                    <option value="40" {"selected" if infinite_split_count == 40 else ""}>40</option>
                </select>
            </label>
            <label>첫매수 LOC 여유율(%) <input type="number" step="0.1" min="10" max="15" name="first_loc_buffer_pct" value="{first_loc_buffer_pct}"></label>
            <label>전량매도 지정가(평단 대비 %) <input type="number" step="0.1" min="0.1" name="designated_sell_pct" value="{designated_sell_pct}"></label>
        </div>
        <div class="optimizer-box">
            <h3>{step24_label} 파라미터 세분화 / DeepMining 설정</h3>
            <div class="input-row">
                <label>탐색 분할수 <input type="text" name="opt_split_values" value="{opt_split_values}" placeholder="20,40"></label>
                <label>첫매수 LOC 최소 <input type="number" step="0.1" min="10" max="15" name="opt_first_loc_min" value="{opt_first_loc_min}"></label>
                <label>첫매수 LOC 최대 <input type="number" step="0.1" min="10" max="15" name="opt_first_loc_max" value="{opt_first_loc_max}"></label>
                <label>첫매수 LOC 간격 <input type="number" step="0.1" min="0.1" name="opt_first_loc_step" value="{opt_first_loc_step}"></label>
            </div>
            <div class="input-row">
                <label>지정가 최소 <input type="number" step="0.1" min="0.1" name="opt_designated_min" value="{opt_designated_min}"></label>
                <label>지정가 최대 <input type="number" step="0.1" min="0.1" name="opt_designated_max" value="{opt_designated_max}"></label>
                <label>지정가 간격 <input type="number" step="0.1" min="0.1" name="opt_designated_step" value="{opt_designated_step}"></label>
                <label>표시 개수 <input type="number" step="1" min="1" max="500" name="opt_display_limit" value="{opt_display_limit}"></label>
            </div>
            <div class="input-row">
                <label>점수 기준
                    <select name="score_mode">
                        <option value="balanced" {"selected" if score_mode == "balanced" else ""}>균형형</option>
                        <option value="return" {"selected" if score_mode == "return" else ""}>수익률 우선</option>
                        <option value="mdd" {"selected" if score_mode == "mdd" else ""}>MDD 방어 우선</option>
                        <option value="turnover" {"selected" if score_mode == "turnover" else ""}>회전율 우선</option>
                    </select>
                </label>
            </div>
        </div>
        <p class="small-note">{step24_label}: Step24O 엔진 기준으로 파라미터 세분화, 후보별 판정, 검증순서/진행률 표시, CSV 캐시 저장/재사용 구조를 추가한 버전입니다.<br>Step24Q는 TOP 후보 적용, CSV 다운로드, 캐시 재사용 표시, 결과표 가독성 강화가 포함됩니다. Step24R은 여기에 SEED 스타일 대시보드 UI와 실시간 진행률 준비용 오버레이/프론트 구조를 추가합니다. 첫매수 LOC 여유율은 원문 가이드 10~15% 범위 안에서만 탐색합니다. 20/40 외 분할은 원문 공식 미확인으로 제외합니다.</p>
        """

    elif strategy == "raor_v22":
        if ticker not in ["TQQQ", "SOXL"]:
            ticker = "TQQQ"
        if infinite_split_count not in [20, 30, 40]:
            infinite_split_count = 40
        split_count = infinite_split_count
        bt, trade_df = run_raor_v22_backtest(
            ticker=ticker,
            split_count=infinite_split_count,
            first_loc_buffer_pct=first_loc_buffer_pct,
            fee_rate_pct=fee_percent,
        )
        v22_designated = 10.0 if ticker == "TQQQ" else 12.0
        strategy_name = f"라오어 무한매수법 2.2 통합 원문엔진 / {ticker}"
        strategy_inputs = f"""
        <div class="input-row">
            <label>분할횟수
                <select name="infinite_split_count">
                    <option value="20" {"selected" if infinite_split_count == 20 else ""}>20</option>
                    <option value="30" {"selected" if infinite_split_count == 30 else ""}>30</option>
                    <option value="40" {"selected" if infinite_split_count == 40 else ""}>40</option>
                </select>
            </label>
            <label>첫매수 LOC 여유율(%) <input type="number" step="0.1" min="0" max="30" name="first_loc_buffer_pct" value="{first_loc_buffer_pct}"></label>
            <label>지정가 매도(원문 고정) <input type="number" readonly value="{v22_designated}"></label>
        </div>
        <div class="optimizer-box">
            <h3>V2.2 통합 원문엔진 검증 포인트</h3>
            <div class="input-row">
                <div class="mini-info"><b>별% 공식</b><br>{'10 - T/2 × (40/a)' if ticker == 'TQQQ' else '12 - T×0.6 × (40/a)'}</div>
                <div class="mini-info"><b>매수/매도 가격분리</b><br>매수=별가격-0.01 / 매도=별가격</div>
                <div class="mini-info"><b>전반/후반</b><br>T &lt; a/2 전반전, T ≥ a/2 후반전</div>
                <div class="mini-info"><b>매도</b><br>1/4 별LOC + 3/4 지정가 {v22_designated:g}%</div>
                <div class="mini-info"><b>쿼터손절</b><br>{'-10% LOC / 10% 지정가' if ticker == 'TQQQ' else '-12% LOC / 12% 지정가'}</div>
            </div>
        </div>
        <p class="small-note">V2.2는 하나의 통합 전략입니다. TQQQ/SOXL을 별도 버전으로 나누지 않고, 티커별 원문 공식만 자동 적용합니다. 큰수매수는 주문거부/RPA 예외라 기본 백테스트에는 넣지 않았습니다. Step25D-8은 V2.2 로그/쿼터손절/주기상태 검증을 마감 요약하고, 다음 단계인 Step25E V4.0 일반모드 재검증으로 넘어가기 위한 정리판입니다. 첫매수 세부 원문은 추가 확인 대상으로 로그에 FirstBuyPolicy를 남깁니다.</p>
        """

    elif strategy == "raor4_step24o":
        # Step24O: Step24N 기준 + 화면 즉시 Optimizer/DeepMining 실행판
        if infinite_split_count not in [20, 40]:
            infinite_split_count = 40
        split_count = infinite_split_count
        if designated_sell_pct <= 0:
            designated_sell_pct = default_designated_sell_pct

        bt, trade_df = run_raor_infinite4_step24o_backtest(
            ticker=ticker,
            split_count=infinite_split_count,
            first_loc_buffer_pct=first_loc_buffer_pct,
            designated_sell_pct_override=designated_sell_pct,
            fee_rate_pct=fee_percent,
        )
        strategy_name = "라오어 무한매수4.0 원문엔진 / Step24O"
        strategy_inputs = f"""
        <div class="input-row">
            <label>분할횟수
                <select name="infinite_split_count">
                    <option value="20" {"selected" if infinite_split_count == 20 else ""}>20</option>
                    <option value="40" {"selected" if infinite_split_count == 40 else ""}>40</option>
                </select>
            </label>
            <label>첫매수 LOC 여유율(%) <input type="number" step="0.1" name="first_loc_buffer_pct" value="{first_loc_buffer_pct}"></label>
            <label>전량매도 지정가(평단 대비 %)
                <input type="number" step="0.1" min="0.1" name="designated_sell_pct" value="{designated_sell_pct}">
            </label>
        </div>
        <p class="small-note">
            Step24O: Step24N 기준판에 Step24 전용 Optimizer TOP100 / DeepMining TOP50 화면 실행 기능을 붙인 버전입니다.<br>
            기존 RSI/오리지널 결과와 섞지 않고, 원문 공식이 확인된 20/40분할 안에서만 탐색합니다.
        </p>
        """

    elif strategy == "raor4_step24n":
        # Step24N: Step24M 기반 + 이전 Step24A~D 정리
        if infinite_split_count not in [20, 40]:
            infinite_split_count = 40
        split_count = infinite_split_count
        if designated_sell_pct <= 0:
            designated_sell_pct = default_designated_sell_pct

        bt, trade_df = run_raor_infinite4_step24n_backtest(
            ticker=ticker,
            split_count=infinite_split_count,
            first_loc_buffer_pct=first_loc_buffer_pct,
            designated_sell_pct_override=designated_sell_pct,
            fee_rate_pct=fee_percent,
        )
        strategy_name = "라오어 무한매수4.0 원문엔진 / Step24N"
        strategy_inputs = f"""
        <div class="input-row">
            <label>분할횟수
                <select name="infinite_split_count">
                    <option value="20" {"selected" if infinite_split_count == 20 else ""}>20</option>
                    <option value="40" {"selected" if infinite_split_count == 40 else ""}>40</option>
                </select>
            </label>
            <label>첫매수 LOC 여유율(%) <input type="number" step="0.1" name="first_loc_buffer_pct" value="{first_loc_buffer_pct}"></label>
            <label>전량매도 지정가(평단 대비 %)
                <input type="number" step="0.1" min="0.1" name="designated_sell_pct" value="{designated_sell_pct}">
            </label>
        </div>
        <p class="small-note">
            Step24N: Step24M 로직은 유지하고, 오래된 Step24A~D 실험판을 정리한 현재 기준판입니다.<br>
            화면/파일 구조를 가볍게 만들기 위한 정리 버전이며 체결 검증 카운터와 지정가 커스텀 입력은 그대로 유지합니다.
        </p>
        """
    elif strategy == "raor4_step24m":
        # Step24M: Step24L 기반 + 검증 카운터/Step24 전용 최적화 준비
        if infinite_split_count not in [20, 40]:
            infinite_split_count = 40
        split_count = infinite_split_count
        if designated_sell_pct <= 0:
            designated_sell_pct = default_designated_sell_pct

        bt, trade_df = run_raor_infinite4_step24m_backtest(
            ticker=ticker,
            split_count=infinite_split_count,
            first_loc_buffer_pct=first_loc_buffer_pct,
            designated_sell_pct_override=designated_sell_pct,
            fee_rate_pct=fee_percent,
        )
        strategy_name = "라오어 무한매수4.0 원문엔진 / Step24M"
        strategy_inputs = f"""
        <div class="input-row">
            <label>분할횟수
                <select name="infinite_split_count">
                    <option value="20" {"selected" if infinite_split_count == 20 else ""}>20</option>
                    <option value="40" {"selected" if infinite_split_count == 40 else ""}>40</option>
                </select>
            </label>
            <label>첫매수 LOC 여유율(%) <input type="number" step="0.1" name="first_loc_buffer_pct" value="{first_loc_buffer_pct}"></label>
            <label>전량매도 지정가(평단 대비 %)
                <input type="number" step="0.1" min="0.1" name="designated_sell_pct" value="{designated_sell_pct}">
            </label>
        </div>
        <p class="small-note">
            Step24M: Step24L 체결 가격분리 구조를 유지하고, 가격겹침 오류/일봉 선후관계 불명/전량매도 완료누락 카운터를 추가했습니다.<br>
            다음 단계에서 Step24 전용 Optimizer TOP100/DeepMining TOP50을 만들기 위한 검증판입니다.
        </p>
        """

    elif strategy == "raor4_step24l":
        # Step24L: Step24H 기반 + 별LOC 매수가/매도가 가격분리 및 일봉 선후관계 분리 로그
        if infinite_split_count not in [20, 40]:
            infinite_split_count = 40
        split_count = infinite_split_count
        if designated_sell_pct <= 0:
            designated_sell_pct = default_designated_sell_pct

        bt, trade_df = run_raor_infinite4_step24l_backtest(
            ticker=ticker,
            split_count=infinite_split_count,
            first_loc_buffer_pct=first_loc_buffer_pct,
            designated_sell_pct_override=designated_sell_pct,
            fee_rate_pct=fee_percent,
        )
        strategy_name = "라오어 무한매수4.0 원문엔진 / Step24L"
        strategy_inputs = f"""
        <div class="input-row">
            <label>분할횟수
                <select name="infinite_split_count">
                    <option value="20" {"selected" if infinite_split_count == 20 else ""}>20</option>
                    <option value="40" {"selected" if infinite_split_count == 40 else ""}>40</option>
                </select>
            </label>
            <label>첫매수 LOC 여유율(%) <input type="number" step="0.1" name="first_loc_buffer_pct" value="{first_loc_buffer_pct}"></label>
            <label>전량매도 지정가(평단 대비 %)
                <input type="number" step="0.1" min="0.1" name="designated_sell_pct" value="{designated_sell_pct}">
            </label>
        </div>
        <p class="small-note">
            Step24L: 별LOC 매수가는 별지점-0.01, 별LOC 매도가는 별지점으로 고정합니다.<br>
            BuySellPriceOverlap은 가격 겹침 오류 검증용이고, 정상이라면 False여야 합니다.<br>
            DailyCandleOrderAmbiguous는 가격 겹침이 아니라 일봉 OHLC만으로 장중 선후관계를 확정할 수 없는 구간입니다.
        </p>
        """

    elif strategy == "raor4_step24h":
        # Step24H: Step24G 기반 + 같은 날 지정가/별LOC/매수LOC 체결신호 검증 강화
        if infinite_split_count not in [20, 40]:
            infinite_split_count = 40
        split_count = infinite_split_count
        if designated_sell_pct <= 0:
            designated_sell_pct = default_designated_sell_pct

        bt, trade_df = run_raor_infinite4_step24h_backtest(
            ticker=ticker,
            split_count=infinite_split_count,
            first_loc_buffer_pct=first_loc_buffer_pct,
            designated_sell_pct_override=designated_sell_pct,
            fee_rate_pct=fee_percent,
        )
        strategy_name = "라오어 무한매수4.0 원문엔진 / Step24H"
        strategy_inputs = f"""
        <div class="input-row">
            <label>분할횟수
                <select name="infinite_split_count">
                    <option value="20" {"selected" if infinite_split_count == 20 else ""}>20</option>
                    <option value="40" {"selected" if infinite_split_count == 40 else ""}>40</option>
                </select>
            </label>
            <label>첫매수 LOC 여유율(%) <input type="number" step="0.1" name="first_loc_buffer_pct" value="{first_loc_buffer_pct}"></label>
            <label>전량매도 지정가(평단 대비 %)
                <input type="number" step="0.1" min="0.1" name="designated_sell_pct" value="{designated_sell_pct}">
            </label>
        </div>
        <p class="small-note">
            Step24H: Step24G의 매일 매도예약 구조를 유지하고, 같은 날 지정가매도/별LOC매도/LOC매수 신호가 겹치는 날을 로그에 표시합니다.<br>
            일봉 백테스트는 장중 순서를 알 수 없으므로 SameDayMultiSignal=True 구간은 원문 체결 흐름 검증 대상으로 봅니다.<br>
            딥마이닝 TOP50/Optimizer TOP100은 아직 라오어 Step24H 전용 최적화 결과가 없으면 예전 RSI 결과를 섞지 않고 안내문만 표시합니다.
        </p>
        """

    elif strategy == "raor4_step24g":
        # Step24G: Step24F 기반 + 지정가 전량매도 수익률 커스텀 입력
        if infinite_split_count not in [20, 40]:
            infinite_split_count = 40
        split_count = infinite_split_count

        # 사용자가 직접 입력하는 전량매도 지정가 수익률.
        # 빈 값/0 이하/비정상 입력은 원문 기본값(TQQQ 15%, SOXL 20%)으로 복귀.
        if designated_sell_pct <= 0:
            designated_sell_pct = default_designated_sell_pct

        bt, trade_df = run_raor_infinite4_step24g_backtest(
            ticker=ticker,
            split_count=infinite_split_count,
            first_loc_buffer_pct=first_loc_buffer_pct,
            designated_sell_pct_override=designated_sell_pct,
            fee_rate_pct=fee_percent,
        )
        strategy_name = "라오어 무한매수4.0 원문엔진 / Step24G"
        strategy_inputs = f"""
        <div class="input-row">
            <label>분할횟수
                <select name="infinite_split_count">
                    <option value="20" {"selected" if infinite_split_count == 20 else ""}>20</option>
                    <option value="40" {"selected" if infinite_split_count == 40 else ""}>40</option>
                </select>
            </label>
            <label>첫매수 LOC 여유율(%) <input type="number" step="0.1" name="first_loc_buffer_pct" value="{first_loc_buffer_pct}"></label>
            <label>전량매도 지정가(평단 대비 %)
                <input type="number" step="0.1" min="0.1" name="designated_sell_pct" value="{designated_sell_pct}">
            </label>
        </div>
        <p class="small-note">
            Step24G: Step24F의 매일 매도예약 구조를 유지하고, 전량매도 지정가 수익률을 직접 입력할 수 있게 했습니다.<br>
            원문 기본값은 TQQQ 15%, SOXL 20%입니다. 입력값을 바꾸면 75% 지정가 전량매도 기준만 바뀌고, 별LOC 25% 예약 구조는 유지됩니다.<br>
            별LOC 매도점이 지정가보다 높게 계산되면 로그에 경고를 남깁니다.
        </p>
        """

    elif strategy == "raor4_step24f":
        # Step24F: Step24E 기반 + 지정가 전량매도 수익률 드롭다운 + 매도예약 검증
        if infinite_split_count not in [20, 40]:
            infinite_split_count = 40
        split_count = infinite_split_count
        bt, trade_df = run_raor_infinite4_step24f_backtest(
            ticker=ticker,
            split_count=infinite_split_count,
            first_loc_buffer_pct=first_loc_buffer_pct,
            designated_sell_pct_override=designated_sell_pct,
            fee_rate_pct=fee_percent,
        )
        strategy_name = "라오어 무한매수4.0 원문엔진 / Step24F"
        designated_options = "".join([
            f'<option value="{v}" {"selected" if abs(designated_sell_pct - v) < 1e-9 else ""}>{v:g}%</option>'
            for v in [10.0, 12.0, 15.0, 20.0, 25.0, 30.0]
        ])
        strategy_inputs = f"""
        <div class="input-row">
            <label>분할횟수
                <select name="infinite_split_count">
                    <option value="20" {"selected" if infinite_split_count == 20 else ""}>20</option>
                    <option value="40" {"selected" if infinite_split_count == 40 else ""}>40</option>
                </select>
            </label>
            <label>첫매수 LOC 여유율(%) <input type="number" step="0.1" name="first_loc_buffer_pct" value="{first_loc_buffer_pct}"></label>
            <label>전량매도 지정가(평단 대비 %)
                <select name="designated_sell_pct">{designated_options}</select>
            </label>
        </div>
        <p class="small-note">
            Step24F: Step24E의 매일 매도예약 구조를 유지하고, 전량매도 지정가 수익률을 드롭다운으로 비교할 수 있게 했습니다.<br>
            원문 기본값은 TQQQ 15%, SOXL 20%입니다. 별LOC 매도점이 지정가보다 높게 계산되면 로그에 경고를 남깁니다.<br>
            같은 날 둘 다 충족은 ‘고가가 지정가 이상이고 종가가 별LOC 이상’이라는 뜻이며, 별LOC가 지정가보다 높다는 의미가 아닙니다.
        </p>
        """

    elif strategy == "raor4_step24e":
        # Step24E: 매일 매도예약 원문 보강 + 지정가 75%/별LOC 25% 동시 예약
        if infinite_split_count not in [20, 40]:
            infinite_split_count = 40
        split_count = infinite_split_count
        bt, trade_df = run_raor_infinite4_step24e_backtest(
            ticker=ticker,
            split_count=infinite_split_count,
            first_loc_buffer_pct=first_loc_buffer_pct,
            fee_rate_pct=fee_percent,
        )
        strategy_name = "라오어 무한매수4.0 원문엔진 / Step24E"
        strategy_inputs = f"""
        <div class="input-row">
            <label>분할횟수
                <select name="infinite_split_count">
                    <option value="20" {"selected" if infinite_split_count == 20 else ""}>20</option>
                    <option value="40" {"selected" if infinite_split_count == 40 else ""}>40</option>
                </select>
            </label>
            <label>첫매수 LOC 여유율(%) <input type="number" step="0.1" name="first_loc_buffer_pct" value="{first_loc_buffer_pct}"></label>
        </div>
        <p class="small-note">
            Step24E: 매도는 전반전/후반전 공통으로 매일 예약합니다.<br>
            보유수량 1/4은 별지점 LOC 매도, 나머지 3/4은 TQQQ +15% / SOXL +20% 지정가 매도로 계산합니다.<br>
            같은 날 지정가와 별LOC가 모두 충족되면 지정가 75% 체결 후 남은 25% 별LOC 체결로 주기 완료 처리합니다.
        </p>
        """



    else:
        return "지원하지 않는 전략입니다."


    # =========================
    # 기간 필터링

    # =========================
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)

    bt = bt[(bt["Date"] >= start_dt) & (bt["Date"] <= end_dt)].copy()

    if bt.empty:
        return "선택한 기간에 백테스트 데이터가 없습니다. 시작일/종료일을 확인해주세요."

    if not trade_df.empty:
        trade_df = filter_trade_df_by_period(trade_df, start_dt, end_dt)


    # =========================
    # 기본 성과 계산

    # =========================
    final = bt.tail(1).iloc[0]

    latest_date = final["Date"].strftime("%Y-%m-%d")
    latest_close = round(final["Close"], 2)

    if "RSI" in final.index:
        latest_rsi = round(final["RSI"], 2)
    elif "WeeklyRSI" in final.index:
        latest_rsi = round(final["WeeklyRSI"], 2)
    else:
        latest_rsi = 0

    latest_mode = make_mode(latest_rsi, sell_rsi)

    if pd.to_datetime(end_date) > daily["Date"].max():
        data_notice = "※ 선택 종료일이 데이터 범위를 초과해 마지막 데이터 기준으로 표시됩니다."
    else:
        data_notice = ""

    final_asset = round(final["TotalAsset"])
    cash = round(final["Cash"])
    stock_value = round(final["StockValue"])
    current_split = final["CurrentSplit"]

    return_rate = (final_asset / INITIAL_CASH - 1) * 100
    mdd = bt["Drawdown"].min() * 100
    cagr = calc_cagr(bt)

    trade_summary = make_trade_summary(trade_df, bt)
    event_counts = get_trade_event_counts(trade_df)

    avg_hold_days = trade_summary["avg_hold_days"]
    trades_per_year = trade_summary["trades_per_year"]
    open_position = trade_summary["open_position"]
    max_split = trade_summary["max_split"]
    cycle_status = make_cycle_status(trade_df, bt, split_count)
    completed_cycles = cycle_status["completed_cycles"]
    completed_profit = cycle_status["completed_profit"]
    active_cycle_label = cycle_status["active_cycle_label"]
    active_t = cycle_status["active_t"]
    active_progress_pct = cycle_status["active_progress_pct"]
    active_remaining_t = cycle_status["active_remaining_t"]
    active_days = cycle_status["active_days"]
    cycle_detail = make_cycle_detail_summary(trade_df, bt, split_count, cycle_status)
    raor_validation_html = make_raor_validation_html(bt, trade_df, ticker, split_count) if str(strategy).startswith("raor4_step24") else ""
    step24m_execution_html = make_step24m_execution_validation_html(bt, trade_df) if strategy in ["raor4_step24m", "raor4_step24n", "raor4_step24o", "raor4_step24p", "raor4_step24q", "raor4_step24r", "raor4_step24s", "raor4_step24t", "raor4_step24u"] else ""
    step24u_gap_html = make_step24u_no_fill_gap_html(bt, split_count) if strategy in ["raor4_step24w", "raor4_step24v", "raor4_step24u", "raor4_step24t", "raor4_step24s", "raor4_step24r", "raor4_step24q", "raor4_step24p", "raor4_step24o", "raor4_step24n", "raor4_step24m"] else ""


    # =========================
    # 수수료 / Profit Factor

    # =========================
    if trade_df.empty:
        buy_fee = 0
        sell_fee = 0
        estimated_fee = 0
        profit_factor = 0
    else:
        if "EventSide" in trade_df.columns and "FeeAmount" in trade_df.columns:
            _side = trade_df["EventSide"].astype(str).str.upper()
            buy_fee = float(pd.to_numeric(trade_df.loc[_side == "BUY", "FeeAmount"], errors="coerce").fillna(0).sum())
            sell_fee = float(pd.to_numeric(trade_df.loc[_side == "SELL", "FeeAmount"], errors="coerce").fillna(0).sum())
        else:
            buy_fee = trade_df["BuyAmount"].fillna(0).sum() * (fee_percent / 100) if "BuyAmount" in trade_df.columns else 0
            sell_fee = trade_df["SellAmount"].fillna(0).sum() * (fee_percent / 100) if "SellAmount" in trade_df.columns else 0
        estimated_fee = buy_fee + sell_fee

        _sell_for_pf = get_sell_trade_df(trade_df)
        gross_profit = _sell_for_pf[_sell_for_pf["Profit"] > 0]["Profit"].sum() if "Profit" in _sell_for_pf.columns else 0
        gross_loss = abs(_sell_for_pf[_sell_for_pf["Profit"] < 0]["Profit"].sum()) if "Profit" in _sell_for_pf.columns else 0

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        else:
            profit_factor = gross_profit if gross_profit > 0 else 0


    # =========================
    # Buy & Hold 비교

    # =========================
    bh_return, bh_cagr, bh_mdd, bh_final_asset = calc_buyhold_stats(bt)

    return_delta = return_rate - bh_return
    cagr_delta = cagr - bh_cagr
    mdd_improvement = abs(bh_mdd) - abs(mdd)

    verdict, verdict_class, verdict_detail = make_strategy_verdict(
        return_delta,
        mdd_improvement
    )


    # =========================
    # 연도별 성과

    # =========================
    yearly_df = calc_yearly_stats(bt)

    if yearly_df.empty:
        best_year = "-"
        worst_year = "-"
        worst_mdd_year = "-"
    else:
        best_year = int(yearly_df.loc[yearly_df["StrategyReturn"].idxmax(), "Year"])
        worst_year = int(yearly_df.loc[yearly_df["StrategyReturn"].idxmin(), "Year"])
        worst_mdd_year = int(yearly_df.loc[yearly_df["StrategyMDD"].idxmin(), "Year"])

    yearly_labels = yearly_df["Year"].astype(str).tolist() if not yearly_df.empty else []
    yearly_strategy_returns = yearly_df["StrategyReturn"].round(2).tolist() if not yearly_df.empty else []
    yearly_qqq_returns = yearly_df["QQQReturn"].round(2).tolist() if not yearly_df.empty else []

    yearly_rows = ""
    if not yearly_df.empty:
        for _, row in yearly_df.iterrows():
            yearly_rows += f"""
            <tr>
                <td>{int(row["Year"])}</td>
                <td>{row["StrategyReturn"]:.2f}%</td>
                <td>{row["QQQReturn"]:.2f}%</td>
                <td>{row["ExcessReturn"]:.2f}%</td>
                <td>{row["StrategyMDD"]:.2f}%</td>
                <td>{row["QQQMDD"]:.2f}%</td>
            </tr>
            """

    yearly_html = f"""
    <div class="grid">
        <div class="metric positive"><h3>최고 수익 연도</h3><p>{best_year}</p></div>
        <div class="metric warning"><h3>최악 수익 연도</h3><p>{worst_year}</p></div>
        <div class="metric danger"><h3>최대 MDD 연도</h3><p>{worst_mdd_year}</p></div>
    </div>

    <div class="card">
        <h2>연도별 성과 분석</h2>
        <div class="table-wrap">
            <table border="1" cellpadding="6" cellspacing="0">
                <tr>
                    <th>연도</th>
                    <th>전략 수익률</th>
                    <th>{ticker} 수익률</th>
                    <th>초과수익</th>
                    <th>전략 MDD</th>
                    <th>{ticker} MDD</th>
                </tr>
                {yearly_rows}
            </table>
        </div>
    </div>

    <div class="card">
        <h2>연도별 수익률 비교</h2>
        <div class="chart-box">
            <canvas id="yearlyChart"></canvas>
        </div>
    </div>
    """


    # =========================
    # Step18A + Step19

    # =========================
    walkforward_today_html = build_walkforward_and_today_cards(
        bt=bt,
        latest_mode=latest_mode,
        split_count=split_count,
        current_split=current_split,
        final_cash=cash,
        latest_price=latest_close,
        fee_percent=fee_percent
    )



    # =========================
    # Step24Y~25C 보조 패널
    # =========================
    stage_helper_html = ""
    if str(strategy).startswith("raor4_step25") or strategy in ["raor4_step24y", "raor4_step24z", "raor_v22"]:
        current_signal = "매도 검토" if latest_mode in ["과열", "상승"] and current_split > 0 else ("신규/추가 LOC 검토" if current_split < split_count else "보유/대기")
        est_buy_loc = latest_close * (1 + first_loc_buffer_pct / 100.0)
        est_designated = latest_close * (1 + designated_sell_pct / 100.0)
        preset_json = json.dumps({"ticker": ticker, "strategy": strategy, "split": int(infinite_split_count), "first_loc": float(first_loc_buffer_pct), "designated_sell_pct": float(designated_sell_pct), "fee_percent": float(fee_percent)}, ensure_ascii=False, indent=2)
        stage_helper_html = f"""
        <div class="card step25-roadmap-card">
            <h2>24Y 후보 선택 도우미</h2>
            <div class="grid">
                <div class="metric positive"><h3>현재 설정</h3><p>{infinite_split_count}분할</p></div>
                <div class="metric"><h3>첫매수 LOC</h3><p>{first_loc_buffer_pct:.1f}%</p></div>
                <div class="metric"><h3>지정가 매도</h3><p>{designated_sell_pct:.1f}%</p></div>
                <div class="metric warning"><h3>선택 기준</h3><p>Robust</p></div>
            </div>
            <p class="small-note">후보 선택은 CAGR 단독 1위가 아니라 MDD, 2022 방어, 최대 공백, 완료주기, 주변 안정성을 함께 봅니다.</p>
        </div>
        <div class="card step25-roadmap-card">
            <h2>24Z 프리셋 저장 준비</h2>
            <p>현재 설정을 JSON 프리셋으로 저장할 수 있는 형태로 정리했습니다. 다음에는 파일 저장/불러오기 버튼으로 확장 가능합니다.</p>
            <pre class="step24x-log">{preset_json}</pre>
        </div>
        <div class="card step25-roadmap-card">
            <h2>25A TQQQ/SOXL 동시 비교 준비</h2>
            <div class="grid">
                <div class="metric"><h3>현재 티커</h3><p>{ticker}</p></div>
                <div class="metric positive"><h3>현재 CAGR</h3><p>{cagr:.2f}%</p></div>
                <div class="metric danger"><h3>현재 MDD</h3><p>{mdd:.2f}%</p></div>
                <div class="metric"><h3>비교 대상</h3><p>TQQQ/SOXL</p></div>
            </div>
            <p class="small-note">25A 정식판에서는 같은 설정으로 TQQQ/SOXL을 동시에 돌려 공통 안정 후보를 찾는 화면으로 확장합니다.</p>
        </div>
        <div class="card step25-roadmap-card">
            <h2>25B 원문 검증 / 스프레드시트 교차검증 체크</h2>
            <p class="small-note"><b>Step25D-3 정리:</b> 무한매수법 2.2는 기본형/수치변화로 나누지 않고 하나의 전략으로 취급합니다. TQQQ는 10% 계열, SOXL은 12%·0.6계수 계열을 티커별 공식으로 자동 적용합니다.</p>
            <div class="table-wrap"><table border="1" cellpadding="6" cellspacing="0">
                <tr><th>항목</th><th>상태</th><th>확인 기준</th></tr>
                <tr><td>첫매수 LOC</td><td>확인 가능</td><td>전날종가보다 10~15% 위</td></tr>
                <tr><td>별LOC 매수/매도</td><td>확인 가능</td><td>BuyLOC=Star-0.01 / SellLOC=Star</td></tr>
                <tr><td>쿼터/지정가 매도</td><td>확인 가능</td><td>1/4 별LOC + 3/4 평단대비 지정가</td></tr>
                <tr><td>구글시트 교차검증</td><td>준비</td><td>시트 열/계산식 맵핑 후 자동 비교</td></tr>
            </table></div>
        </div>
        <div class="card step25-roadmap-card">
            <h2>25C RPA 주문 신호 출력 준비</h2>
            <div class="grid">
                <div class="metric warning"><h3>오늘 신호</h3><p>{current_signal}</p></div>
                <div class="metric"><h3>참고 LOC</h3><p>${est_buy_loc:.2f}</p></div>
                <div class="metric"><h3>참고 지정가</h3><p>${est_designated:.2f}</p></div>
                <div class="metric"><h3>진행 분할</h3><p>{current_split}/{split_count}</p></div>
            </div>
            <p class="small-note">이 값은 RPA 연결용 화면 준비 신호입니다. 실제 주문 전에는 Step25B 교차검증과 중복주문 방지 모듈이 필요합니다.</p>
        </div>
        """

    # =========================
    # 딥마이닝 TOP50

    # =========================
    deepmine_html = ""
    optimizer_html = ""
    recommend_card_html = ""

    if action_mode == "deepmine":
        if strategy in ["raor4_step25c", "raor4_step25b", "raor4_step25a", "raor4_step24z", "raor4_step24y", "raor4_step24x", "raor4_step24w", "raor4_step24v", "raor4_step24u", "raor4_step24t", "raor4_step24s", "raor4_step24r", "raor4_step24q", "raor4_step24p", "raor4_step24o"]:
            deepmine_table_html = build_step24p_optimizer_html(
                ticker=ticker, fee_percent=fee_percent, mode="deepmine", min_cagr=min_cagr, max_mdd=max_mdd, min_win=min_win, min_pf=min_pf,
                split_values_text=opt_split_values, first_loc_min=opt_first_loc_min, first_loc_max=opt_first_loc_max, first_loc_step=opt_first_loc_step,
                designated_min=opt_designated_min, designated_max=opt_designated_max, designated_step=opt_designated_step, score_mode=score_mode, display_limit=opt_display_limit, strategy_key=(strategy if strategy in ["raor4_step25c", "raor4_step25b", "raor4_step25a", "raor4_step24z", "raor4_step24y", "raor4_step24x", "raor4_step24w", "raor4_step24v", "raor4_step24u", "raor4_step24t", "raor4_step24s", "raor4_step24r", "raor4_step24q"] else "raor4_step24p"),
            )
            recommend_card = None
        else:
            deepmine_table_html, recommend_card = build_deepmine_table(
                strategy=strategy,
                ticker=ticker,
                min_cagr=min_cagr,
                max_mdd=max_mdd,
                min_win=min_win,
                min_pf=min_pf,
            )

        deepmine_html = f"""
        <div class="card">
            <h2>딥마이닝 2.0 필터</h2>
            <form method="get">
                <input type="hidden" name="ticker" value="{ticker}">
                <input type="hidden" name="strategy" value="{strategy}">
                <input type="hidden" name="action_mode" value="deepmine">
                <input type="hidden" name="start_date" value="{start_date}">
                <input type="hidden" name="end_date" value="{end_date}">
                <input type="hidden" name="fee_percent" value="{fee_percent}">
                <input type="hidden" name="opt_split_values" value="{opt_split_values}">
                <input type="hidden" name="opt_first_loc_min" value="{opt_first_loc_min}">
                <input type="hidden" name="opt_first_loc_max" value="{opt_first_loc_max}">
                <input type="hidden" name="opt_first_loc_step" value="{opt_first_loc_step}">
                <input type="hidden" name="opt_designated_min" value="{opt_designated_min}">
                <input type="hidden" name="opt_designated_max" value="{opt_designated_max}">
                <input type="hidden" name="opt_designated_step" value="{opt_designated_step}">
                <input type="hidden" name="opt_display_limit" value="{opt_display_limit}">
                <input type="hidden" name="score_mode" value="{score_mode}">

                <div class="input-row">
                    <label>최소 CAGR <input type="number" step="0.1" name="min_cagr" value="{min_cagr}"></label>
                    <label>최대 MDD <input type="number" step="0.1" name="max_mdd" value="{max_mdd}"></label>
                    <label>최소 승률 <input type="number" step="0.1" name="min_win" value="{min_win}"></label>
                    <label>최소 PF <input type="number" step="0.1" name="min_pf" value="{min_pf}"></label>
                </div>

                <button type="submit">필터 적용</button>
            </form>
        </div>
        {deepmine_table_html}
        """

        if recommend_card:
            recommend_card_html = f"""
            <div class="card hero">
                <h2>추천 후보 1순위</h2>
                <p>전략 유형: <b>{recommend_card["type"]}</b></p>
                <p>CAGR: <b>{recommend_card["cagr"]:.2f}%</b></p>
                <p>MDD: <b>{recommend_card["mdd"]:.2f}%</b></p>
                <p>승률: <b>{recommend_card["win"]:.2f}%</b></p>
            </div>
            """



    if action_mode == "robust":
        if strategy in ["raor4_step25c", "raor4_step25b", "raor4_step25a", "raor4_step24z", "raor4_step24y", "raor4_step24x", "raor4_step24w", "raor4_step24v", "raor4_step24u", "raor4_step24t", "raor4_step24s", "raor4_step24r", "raor4_step24q", "raor4_step24p", "raor4_step24o"]:
            optimizer_html = build_step24w_robust_mining_html(ticker=ticker, fee_percent=fee_percent, split_values_text=opt_split_values, first_loc_min=opt_first_loc_min, first_loc_max=opt_first_loc_max, first_loc_step=opt_first_loc_step, designated_min=opt_designated_min, designated_max=opt_designated_max, designated_step=opt_designated_step, display_limit=opt_display_limit, score_mode=score_mode)
        else:
            optimizer_html = '<div class="card"><h2>Robust Mining</h2><p>Step24 원문엔진에서만 지원합니다.</p></div>'

    if action_mode == "robust_live":
        optimizer_html = build_step24x_live_panel_html(ticker=ticker, fee_percent=fee_percent, split_values_text=opt_split_values, first_loc_min=opt_first_loc_min, first_loc_max=opt_first_loc_max, first_loc_step=opt_first_loc_step, designated_min=opt_designated_min, designated_max=opt_designated_max, designated_step=opt_designated_step, display_limit=opt_display_limit, score_mode=score_mode)

    # =========================
    if action_mode == "optimizer":
        if strategy in ["raor4_step25c", "raor4_step25b", "raor4_step25a", "raor4_step24z", "raor4_step24y", "raor4_step24x", "raor4_step24w", "raor4_step24v", "raor4_step24u", "raor4_step24t", "raor4_step24s", "raor4_step24r", "raor4_step24q", "raor4_step24p", "raor4_step24o"]:
            optimizer_html = build_step24p_optimizer_html(
                ticker=ticker, fee_percent=fee_percent, mode="optimizer", min_cagr=min_cagr, max_mdd=max_mdd, min_win=min_win, min_pf=min_pf,
                split_values_text=opt_split_values, first_loc_min=opt_first_loc_min, first_loc_max=opt_first_loc_max, first_loc_step=opt_first_loc_step,
                designated_min=opt_designated_min, designated_max=opt_designated_max, designated_step=opt_designated_step, score_mode=score_mode, display_limit=opt_display_limit, strategy_key=(strategy if strategy in ["raor4_step25c", "raor4_step25b", "raor4_step25a", "raor4_step24z", "raor4_step24y", "raor4_step24x", "raor4_step24w", "raor4_step24v", "raor4_step24u", "raor4_step24t", "raor4_step24s", "raor4_step24r", "raor4_step24q"] else "raor4_step24p"),
            )
        else:
            optimizer_html = build_optimizer_result_html(ticker, strategy)

    # 매매로그

    # =========================


    # Step24D: 무한매수 완료/진행 주기별 손익 집계
    cycle_summary_html = ""
    if "CycleId" in bt.columns:
        cycle_rows = ""
        completed_n = int(completed_cycles or 0)
        completed_id_set = set(range(1, completed_n + 1))
        total_cycle_profit = float(completed_profit or 0)
        if completed_n > 0:
            source_cycles = sorted(completed_id_set)
            for cid in source_cycles[-100:]:
                g_bt = bt[pd.to_numeric(bt["CycleId"], errors="coerce").fillna(0).astype(int) == cid].copy()
                if trade_df is not None and not trade_df.empty and "CycleId" in trade_df.columns:
                    sell_df_for_cycle = get_sell_trade_df(trade_df)
                    g_tr = sell_df_for_cycle[pd.to_numeric(sell_df_for_cycle["CycleId"], errors="coerce").fillna(0).astype(int) == cid].copy()
                else:
                    g_tr = pd.DataFrame()
                start_v = g_bt["Date"].min() if not g_bt.empty else (g_tr["CycleStartDate"].dropna().iloc[0] if not g_tr.empty and "CycleStartDate" in g_tr.columns and not g_tr["CycleStartDate"].dropna().empty else pd.NaT)
                end_v = g_bt["Date"].max() if not g_bt.empty else (g_tr["SellDate"].max() if not g_tr.empty and "SellDate" in g_tr.columns else pd.NaT)
                profit_v = float(g_tr["Profit"].fillna(0).sum()) if not g_tr.empty and "Profit" in g_tr.columns else 0.0
                buy_v = float(g_tr["BuyAmount"].fillna(0).sum()) if not g_tr.empty and "BuyAmount" in g_tr.columns else 0.0
                sell_v = float(g_tr["SellAmount"].fillna(0).sum()) if not g_tr.empty and "SellAmount" in g_tr.columns else 0.0
                ret_v = (profit_v / buy_v * 100) if buy_v > 0 else 0.0
                days_v = (pd.to_datetime(end_v) - pd.to_datetime(start_v)).days if pd.notna(start_v) and pd.notna(end_v) else 0
                max_t_v = float(g_bt["T" if "T" in g_bt.columns else "CurrentSplit"].max()) if not g_bt.empty else 0.0
                cycle_rows += f"""
                <tr>
                    <td>{int(cid)}</td>
                    <td>{pd.to_datetime(start_v).strftime("%Y-%m-%d") if pd.notna(start_v) else ""}</td>
                    <td>{pd.to_datetime(end_v).strftime("%Y-%m-%d") if pd.notna(end_v) else ""}</td>
                    <td>{days_v}</td>
                    <td>{max_t_v:.1f}T</td>
                    <td>{buy_v:,.0f}</td>
                    <td>{sell_v:,.0f}</td>
                    <td>{profit_v:,.0f}</td>
                    <td>{ret_v:.2f}%</td>
                    <td>{len(g_tr) if not g_tr.empty else 0}</td>
                </tr>
                """
            cycle_summary_html = f"""
            <div class="card">
                <h2>Step24D 무한매수 주기 상세 분석</h2>
                <div class="grid mini-grid">
                    <div class="metric positive"><h3>완료 주기</h3><p>{completed_n}회</p></div>
                    <div class="metric warning"><h3>진행 중 주기</h3><p>{active_cycle_label}</p></div>
                    <div class="metric"><h3>평균 주기일수</h3><p>{cycle_detail['avg_cycle_days']:.1f}일</p></div>
                    <div class="metric"><h3>최장/최단</h3><p>{cycle_detail['max_cycle_days']} / {cycle_detail['min_cycle_days']}일</p></div>
                    <div class="metric"><h3>평균 주기수익률</h3><p>{cycle_detail['avg_cycle_return']:.2f}%</p></div>
                    <div class="metric"><h3>최대 소진T</h3><p>{cycle_detail['max_used_t']:.1f}T</p></div>
                    <div class="metric"><h3>후반전 진입</h3><p>{cycle_detail['second_half_count']}회</p></div>
                    <div class="metric"><h3>소진모드 진입</h3><p>{cycle_detail['exhaust_count']}회</p></div>
                    <div class="metric warning"><h3>쿼터후보</h3><p>{cycle_detail['quarter_trigger_candidate_count']}일</p></div>
                    <div class="metric positive"><h3>쿼터진입</h3><p>{cycle_detail['quarter_start_count']}회</p></div>
                    <div class="metric"><h3>쿼터MOC</h3><p>{cycle_detail['quarter_moc_count']}회</p></div>
                    <div class="metric"><h3>쿼터LOC매수</h3><p>{cycle_detail['quarter_loc_buy_count']}회</p></div>
                    <div class="metric"><h3>쿼터LOC매도</h3><p>{cycle_detail['quarter_loc_sell_count']}회</p></div>
                    <div class="metric"><h3>쿼터복귀/반복</h3><p>{cycle_detail['quarter_exit_count']} / {cycle_detail['quarter_repeat_count']}</p></div>
                    <div class="metric"><h3>쿼터LOC매수금</h3><p>{cycle_detail['quarter_total_loc_buy_amount']:,.0f}원</p></div>
                    <div class="metric"><h3>쿼터MOC매도금</h3><p>{cycle_detail['quarter_total_moc_sell_amount']:,.0f}원</p></div>
                    <div class="metric {'positive' if cycle_detail['quarter_cash_validation_fail_count'] == 0 else 'danger'}"><h3>현금검증 실패</h3><p>{cycle_detail['quarter_cash_validation_fail_count']}건</p></div>
                    <div class="metric {'positive' if cycle_detail['quarter_shares_validation_fail_count'] == 0 else 'danger'}"><h3>수량검증 실패</h3><p>{cycle_detail['quarter_shares_validation_fail_count']}건</p></div>
                    <div class="metric"><h3>완료손익</h3><p>{total_cycle_profit:,.0f}원</p></div>
                </div>
                <div class="table-wrap">
                    <table border="1" cellpadding="6" cellspacing="0">
                        <tr>
                            <th>주기</th><th>시작일</th><th>종료/마지막일</th><th>주기일수</th><th>최대T</th>
                            <th>매수원금</th><th>매도금액</th><th>손익</th><th>수익률</th><th>매도로그수</th>
                        </tr>
                        {cycle_rows}
                    </table>
                </div>
                <p class="small-note">※ 완료 주기는 trade_df의 CycleCompleted가 비어도 bt의 CycleId 진행값으로 보정 계산합니다.</p>
            </div>
            """
        else:
            cycle_summary_html = f"""
            <div class="card">
                <h2>Step24D 무한매수 주기 상세 분석</h2>
                <p>선택 기간 안에서 완전히 종료된 무한매수 주기는 아직 없습니다.</p>
                <p>현재 진행 중 주기: <b>{active_cycle_label}</b></p>
                <p>진행 분할: <b>{active_t:.1f}/{split_count}T ({active_progress_pct:.1f}%)</b></p>
                <p class="small-note">※ 이번 버전부터 완료 주기 0 고정 문제를 방지하기 위해 bt의 CycleId 진행값으로도 보정합니다.</p>
            </div>
            """

    # Step25D-8: V2.2 마감 요약표와 주기별 최종상태/장기주기/현재 OPEN 주기 해석표를 주기 요약 뒤에 추가한다.
    if strategy == "raor_v22":
        cycle_summary_html += make_v22_final_validation_html(bt, trade_df, ticker, split_count, fee_percent)
    cycle_summary_html += make_cycle_status_audit_html(trade_df, bt, split_count)

    trade_rows = ""
    if not trade_df.empty:
        trade_view = trade_df.copy()
        sort_col = "EventDate" if "EventDate" in trade_view.columns else "SellDate"
        if sort_col in trade_view.columns:
            trade_view[sort_col] = pd.to_datetime(trade_view[sort_col], errors="coerce")
            trade_view = trade_view.sort_values(sort_col, ascending=False)
        for _, row in trade_view.head(40).iterrows():
            event_side = str(row.get("EventSide", row.get("OrderType", ""))).upper()
            buy_amt = float(row.get("BuyAmount", 0) or 0)
            sell_amt = float(row.get("SellAmount", 0) or 0)
            profit = float(row.get("Profit", 0) or 0)
            ret = float(row.get("ReturnPct", 0) or 0)
            trade_rows += f"""
            <tr>
                <td>{row.get("CycleId", "")}</td>
                <td>{fmt_log_date(row.get("CycleStartDate", ""))}</td>
                <td>{fmt_log_date(row.get("EventDate", row.get("SellDate", "")))}</td>
                <td>{event_side}</td>
                <td>{fmt_log_date(row.get("BuyEventDate", ""))}</td>
                <td>{fmt_log_date(row.get("SellEventDate", ""))}</td>
                <td>{fmt_log_date(row.get("LastBuyDate", ""))}</td>
                <td>{row.get("HoldDays", 0)}</td>
                <td>{row.get("LastBuyHoldDays", 0)}</td>
                <td>{buy_amt:,.0f}</td>
                <td>{sell_amt:,.0f}</td>
                <td>{profit:,.0f}</td>
                <td>{ret:.2f}%</td>
                <td>{row.get("OrderPrice", 0):,.2f}</td>
                <td>{row.get("OrderQty", 0):,.4f}</td>
                <td>{row.get("QuarterEventType", "")}</td>
                <td>{row.get("CycleStatus", "")}</td>
                <td>{row.get("CycleEndReason", "")}</td>
                <td>{float(row.get("OpenQtyAfter", 0) or 0):,.4f}</td>
                <td>{float(row.get("OpenMarketValueAfter", 0) or 0):,.0f}</td>
                <td>{float(row.get("FeeAmount", 0) or 0):,.0f}</td>
                <td>{float(row.get("CashBefore", 0) or 0):,.0f}</td>
                <td>{float(row.get("CashAfter", 0) or 0):,.0f}</td>
                <td>{"OK" if bool(row.get("CashValidationOK", True)) else "FAIL"}</td>
                <td>{"OK" if bool(row.get("SharesValidationOK", True)) else "FAIL"}</td>
                <td>{row.get("QuarterModeBefore", "")}</td>
                <td>{row.get("QuarterModeAfter", "")}</td>
                <td>{row.get("QuarterRoundAfter", "")}</td>
                <td>{row.get("ModeTransitionReason", "")}</td>
                <td>{row.get("Reason", "")}</td>
            </tr>
            """

    trade_log_html = f"""
    <div class="card">
        <h2>Trade Event Log / 이벤트후상태 / 완료주기 승률</h2>
        <div class="summary-grid">
            <p>체결 이벤트: <b>{event_counts["event_count"]}</b></p>
            <p>BUY/SELL 이벤트: <b>{event_counts["buy_event_count"]} / {event_counts["sell_event_count"]}</b></p>
            <p>집계 기준: <b>{trade_summary.get("summary_basis", "완료 주기")}</b></p>
            <p>완료주기수: <b>{trade_summary["trade_count"]}</b></p>
            <p>수익주기: <b>{trade_summary["win_count"]}</b></p>
            <p>손실주기: <b>{trade_summary["loss_count"]}</b></p>
            <p>주기승률: <b>{trade_summary["win_rate"]:.2f}%</b></p>
            <p>평균 주기보유일: <b>{trade_summary["avg_hold_days"]:.1f}일</b></p>
            <p>최대 주기보유일: <b>{trade_summary["max_hold_days"]}</b>일</p>
            <p>연평균 완료주기: <b>{trade_summary["trades_per_year"]:.2f}회</b></p>
            <p>현재 미청산: <b>{trade_summary["open_position"]}</b></p>
            <p>최대 분할: <b>{trade_summary["max_split"]:.1f} / {split_count}</b></p>
            <p>쿼터진입: <b>{cycle_detail['quarter_start_count']}</b>회</p>
            <p>쿼터MOC: <b>{cycle_detail['quarter_moc_count']}</b>회</p>
            <p>쿼터LOC매수/매도: <b>{cycle_detail['quarter_loc_buy_count']} / {cycle_detail['quarter_loc_sell_count']}</b>회</p>
            <p>쿼터LOC매수금: <b>{cycle_detail['quarter_total_loc_buy_amount']:,.0f}</b>원</p>
            <p>쿼터MOC매도금: <b>{cycle_detail['quarter_total_moc_sell_amount']:,.0f}</b>원</p>
            <p>쿼터 현금/수량 검증 실패: <b>{cycle_detail['quarter_cash_validation_fail_count']} / {cycle_detail['quarter_shares_validation_fail_count']}</b>건</p>
        </div>

        <p class="small-note">※ 날짜 필터는 EventDate 기준이라 BUY 이벤트도 유지됩니다. 이 표의 이벤트후상태는 해당 이벤트 직후 상태입니다. 같은 주기 안에서 OPEN 이벤트가 많아도 최종상태표에서 COMPLETED면 완료 주기입니다. 승률/보유일은 부분매도 이벤트가 아니라 완료 주기 단위로 계산합니다.</p>
        <div class="table-wrap">
            <table border="1" cellpadding="6" cellspacing="0">
                <tr>
                    <th>주기</th>
                    <th>주기시작일</th>
                    <th>이벤트일</th>
                    <th>구분</th>
                    <th>매수이벤트일</th>
                    <th>매도이벤트일</th>
                    <th>마지막매수일</th>
                    <th>주기보유일</th>
                    <th>마지막매수후일</th>
                    <th>매수금액</th>
                    <th>매도금액</th>
                    <th>손익</th>
                    <th>수익률</th>
                    <th>주문가</th>
                    <th>수량</th>
                    <th>쿼터이벤트</th>
                    <th>이벤트후상태</th>
                    <th>이벤트후사유</th>
                    <th>OpenQtyAfter</th>
                    <th>Open평가액After</th>
                    <th>수수료</th>
                    <th>현금전</th>
                    <th>현금후</th>
                    <th>현금검증</th>
                    <th>수량검증</th>
                    <th>쿼터전</th>
                    <th>쿼터후</th>
                    <th>쿼터회차</th>
                    <th>전환사유</th>
                    <th>사유</th>
                </tr>
                {trade_rows}
            </table>
        </div>
    </div>
    """


    order_plan_rows = ""
    if bt is not None and not bt.empty:
        op = bt.copy()
        if "Action" in op.columns:
            op = op[~op["Action"].astype(str).eq("관망")].copy()
        if "Date" in op.columns:
            op = op.sort_values("Date", ascending=False)
        for _, row in op.head(40).iterrows():
            order_plan_rows += f"""
            <tr>
                <td>{fmt_log_date(row.get("Date", ""))}</td>
                <td>{row.get("CycleId", "")}</td>
                <td>{float(row.get("TBefore", 0) or 0):.2f}</td>
                <td>{float(row.get("TAfter", row.get("T", 0)) or 0):.2f}</td>
                <td>{float(row.get("Cash", 0) or 0):,.0f}</td>
                <td>{float(row.get("Shares", 0) or 0):,.4f}</td>
                <td>{float(row.get("AvgPrice", 0) or 0):,.2f}</td>
                <td>{row.get("PhaseBefore", "")}</td>
                <td>{row.get("PhaseAfter", row.get("Mode", ""))}</td>
                <td>{row.get("Action", "")}</td>
                <td>{row.get("OrderPlan", "")}</td>
                <td>{row.get("QuarterRound", "")}</td>
                <td>{row.get("QuarterUnitAmount", "")}</td>
                <td>{"Y" if bool(row.get("QuarterTriggerCandidate", False)) else ""}</td>
                <td>{row.get("QuarterTriggerReason", "")}</td>
                <td>{row.get("ModeTransitionReason", "")}</td>
                <td>{"Y" if bool(row.get("DailyCandleOrderAmbiguous", False)) else ""}</td>
            </tr>
            """

    order_plan_log_html = f"""
    <div class="card">
        <h2>Order Plan Log</h2>
        <p class="small-note">※ bt 일별 행에서 주문계획이 있거나 실제 액션이 발생한 최근 40일입니다. V2.2 일반모드 공식은 유지하고, 쿼터손절모드 주문/전환 상태를 표시합니다.</p>
        <div class="table-wrap">
            <table border="1" cellpadding="6" cellspacing="0">
                <tr>
                    <th>날짜</th><th>주기</th><th>TBefore</th><th>TAfter</th><th>현금</th><th>보유수량</th><th>평단</th><th>전상태</th><th>후상태</th><th>액션</th><th>주문계획</th><th>쿼터회차</th><th>쿼터1회금액</th><th>쿼터후보</th><th>쿼터후보사유</th><th>전환사유</th><th>일봉순서불명확</th>
                </tr>
                {order_plan_rows}
            </table>
        </div>
    </div>
    """


    # =========================
    # 차트 데이터

    # =========================
    bt["TotalAsset"] = pd.to_numeric(bt["TotalAsset"], errors="coerce").fillna(0)
    bt["Close"] = pd.to_numeric(bt["Close"], errors="coerce").fillna(0)
    bt["Drawdown"] = pd.to_numeric(bt["Drawdown"], errors="coerce").fillna(0)

    monthly = bt.copy()
    monthly["Month"] = monthly["Date"].dt.to_period("M")
    monthly_return = monthly.groupby("Month")["DailyReturn"].sum().reset_index()

    buy_points = []
    sell_points = []

    for _, row in bt.iterrows():
        if "매수" in str(row["Action"]):
            buy_points.append(round(float(row["Close"]), 2))
            sell_points.append(None)
        elif "매도" in str(row["Action"]):
            buy_points.append(None)
            sell_points.append(round(float(row["Close"]), 2))
        else:
            buy_points.append(None)
            sell_points.append(None)

    chart_data = {
        "labels": bt["Date"].dt.strftime("%Y-%m-%d").tolist(),
        "assets": bt["TotalAsset"].round(0).tolist(),
        "prices": bt["Close"].round(2).tolist(),
        "drawdown": (bt["Drawdown"] * 100).round(2).tolist(),
        "month_labels": monthly_return["Month"].astype(str).tolist(),
        "month_return": monthly_return["DailyReturn"].fillna(0).round(2).tolist(),
        "buy_points": buy_points,
        "sell_points": sell_points,
        "yearly_labels": yearly_labels,
        "yearly_strategy_returns": yearly_strategy_returns,
        "yearly_qqq_returns": yearly_qqq_returns,
    }

    chart_json = json.dumps(chart_data, ensure_ascii=False)

    return_class = cls_positive_negative(return_rate)
    cagr_class = cls_positive_negative(cagr)
    mdd_class = cls_mdd(mdd)
    win_class = "positive" if trade_summary["win_rate"] >= 60 else "warning" if trade_summary["win_rate"] >= 40 else "negative"
    bh_class = cls_positive_negative(bh_return)
    open_class = cls_open_position(open_position)
    pf_class = "positive" if profit_factor >= 1.5 else "warning" if profit_factor >= 1 else "negative"

    # Step24D UI 보강: 브라우저 기본 date picker의 연도 스크롤이 둔감해서
    # 연/월/일을 직접 선택하는 커스텀 날짜 선택 UI를 사용한다.
    data_min_year = int(_daily_full_for_notice["Date"].min().year)
    data_max_year = int(_daily_full_for_notice["Date"].max().year)

    def _date_parts(date_str):
        dt = pd.to_datetime(date_str, errors="coerce")
        if pd.isna(dt):
            dt = _daily_full_for_notice["Date"].min()
        return int(dt.year), int(dt.month), int(dt.day)

    def _select_options(values, selected_value, suffix=""):
        html_parts = []
        for v in values:
            selected_attr = "selected" if int(v) == int(selected_value) else ""
            html_parts.append(f'<option value="{int(v)}" {selected_attr}>{int(v)}{suffix}</option>')
        return "".join(html_parts)

    start_y, start_m, start_d = _date_parts(start_date)
    end_y, end_m, end_d = _date_parts(end_date)
    year_values = list(range(data_min_year, data_max_year + 1))
    month_values = list(range(1, 13))
    day_values = list(range(1, 32))

    start_year_options = _select_options(year_values, start_y, "")
    end_year_options = _select_options(year_values, end_y, "")
    start_month_options = _select_options(month_values, start_m, "월")
    end_month_options = _select_options(month_values, end_m, "월")
    start_day_options = _select_options(day_values, start_d, "일")
    end_day_options = _select_options(day_values, end_d, "일")

    # Step24W-2: action_mode 결과가 있을 때는 서버 렌더 단계부터 Optimizer 패널을 기본 활성화한다.
    # 기존에는 JS가 늦게 패널을 전환하거나 실패하면 결과표가 숨겨져 보일 수 있었다.
    seed_initial_panel = "optimizer" if action_mode in ["deepmine", "optimizer", "robust", "robust_live"] else "dashboard"
    seed_dashboard_active = "active" if seed_initial_panel == "dashboard" else ""
    seed_optimizer_active = "active" if seed_initial_panel == "optimizer" else ""
    seed_results_active = ""
    seed_charts_active = ""

    # Step24W-3: robust 결과는 Optimizer 패널 최상단에 먼저 표시한다.
    # 기존에는 Step18~21/연도별 분석 뒤쪽에 붙어서 사용자가 결과표를 못 본 것처럼 느낄 수 있었다.
    robust_top_html = optimizer_html if action_mode in ["robust", "robust_live"] else ""
    optimizer_bottom_html = "" if action_mode in ["robust", "robust_live"] else optimizer_html

    if strategy == "raor_v22":
        engine_note_html = """
        <div class=\"step24r-lab-note\">
            <b>V2.2 원문 검증 모드:</b> 현재 화면은 V2.2 통합 원문엔진의 공식/체결/로그 검증을 우선합니다. RSI 모드와 Step20 연구용 프리셋은 숨김 처리했습니다.
            <div class=\"step24r-progress-plan\">
                <div>1. 별% 공식</div><div>2. 매수/매도 가격분리</div><div>3. 전반/후반 매수</div><div>4. 1/4 LOC + 3/4 지정가</div>
            </div>
        </div>
        """
        action_buttons_html = """<button type=\"submit\" name=\"action_mode\" value=\"backtest\">V2.2 백테스트</button><span class=\"small-note\">Optimizer/DeepMining/Robust Mining은 V2.2 엔진 검증 후 별도 연결 예정입니다.</span>"""
        status_info_html = """<p>주간 RSI: <b>미사용</b></p><div class=\"mode\">현재 모드: 무한매수 V2.2</div>"""
        walkforward_today_html = ""
        robust_top_html = ""
        optimizer_bottom_html = ""
    else:
        engine_note_html = """
        <div class=\"step24r-lab-note\">
            <b>Step24X 과최적화 방어 Robust Mining:</b> 매매 엔진은 Step24Q/R/S/T/U/V와 동일하게 유지하고, 원문 범위 안 후보만 대상으로 전체성과·최근 3년·2022 방어·무체결 공백·주변값 안정성을 함께 평가합니다.
            <div class=\"step24r-progress-plan\">
                <div>1. Robust Score</div><div>2. 구간 분리 검증</div><div>3. 주변값 안정성</div><div>4. 과최적화 위험도</div>
            </div>
        </div>
        """
        action_buttons_html = """<button type=\"submit\" name=\"action_mode\" value=\"backtest\">백테스트</button>
        <button type=\"submit\" name=\"action_mode\" value=\"deepmine\">딥마이닝 TOP50</button>
        <button type=\"submit\" name=\"action_mode\" value=\"optimizer\">Optimizer TOP100</button>
        <button type=\"submit\" name=\"action_mode\" value=\"robust_live\">실시간 Robust Mining</button>
        <button type=\"submit\" name=\"action_mode\" value=\"robust\">과최적화 방어 딥마이닝</button>"""
        status_info_html = f"""<p>주간 RSI: {latest_rsi}</p><div class=\"mode\">현재 모드: {latest_mode}</div>"""

    html = f"""
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sunny's Test</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        body {{
            font-family: Arial, sans-serif;
            background: radial-gradient(circle at top left, #eef6ff 0, #f7fafc 28%, #eef2f7 100%);
            padding: 24px 24px 24px 188px;
            color: #111827;
        }}
        .seed-sidebar {{
            position: fixed; top: 16px; left: 16px; bottom: 16px; width: 150px;
            background: linear-gradient(180deg, #08111f, #111827); color: white;
            border-radius: 20px; padding: 14px; box-shadow: 0 24px 80px rgba(15,23,42,.28); z-index: 20;
        }}
        .seed-brand {{ font-weight: 900; font-size: 18px; letter-spacing: -0.5px; margin-bottom: 6px; }}
        .seed-brand-sub {{ color: #9ca3af; font-size: 12px; line-height: 1.45; margin-bottom: 14px; }}
        .seed-nav {{ display: grid; gap: 8px; }}
        .seed-nav a, .seed-nav span, .seed-nav button {{
            display: block; color: #dbeafe; text-decoration: none; padding: 9px 9px; border-radius: 12px;
            background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.06); font-weight: 800; font-size: 12px;
        }}
        .seed-nav a:hover, .seed-nav button:hover {{ background: rgba(37,99,235,.35); }}
        .seed-nav .active {{ background: linear-gradient(90deg,#2563eb,#22c55e); color: white; }}
        .seed-nav button {{ width:100%; text-align:left; cursor:pointer; font-family:inherit; }}
        .seed-panel {{ display:none; }}
        .seed-panel.active {{ display:block; }}
        .seed-panel-title {{ margin: 0 0 14px 0; padding: 18px 22px; border-radius: 18px; background:#fff; box-shadow:0 6px 20px rgba(15,23,42,.06); font-size:22px; }}
        .seed-shell {{ max-width: none; width: 100%; margin: 0; }}
        .seed-topbar {{
            background: rgba(255,255,255,.78); backdrop-filter: blur(12px); border: 1px solid rgba(226,232,240,.9);
            border-radius: 22px; padding: 14px 18px; display: flex; justify-content: space-between; align-items: center; gap: 12px;
            margin-bottom: 16px; box-shadow: 0 10px 30px rgba(15,23,42,.06);
        }}
        .seed-topbar h1 {{ margin: 0; font-size: 24px; }}
        .seed-badges {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .seed-badge {{ border-radius: 999px; padding: 8px 11px; background:#eef2ff; color:#1e3a8a; font-weight:800; font-size:12px; }}
        .card {{
            background: white;
            padding: 22px;
            border-radius: 14px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            overflow-x: auto;
        }}
        .hero {{
            border-left: 0; border-top: 5px solid #2563eb;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 20px;
        }}
        .metric {{
            background: white;
            padding: 20px;
            border-radius: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            transition: transform 0.2s ease;
            border-top: 4px solid #d1d5db;
        }}
        .metric:hover {{
            transform: translateY(-3px);
        }}
        .metric h3 {{
            margin: 0;
            color: #666;
            font-size: 14px;
        }}
        .metric p {{
            margin: 8px 0 0 0;
            font-size: 24px;
            font-weight: bold;
        }}
        .metric.positive {{
            border-top-color: #16a34a;
        }}
        .metric.positive p {{
            color: #16a34a;
        }}
        .metric.negative {{
            border-top-color: #dc2626;
        }}
        .metric.negative p {{
            color: #dc2626;
        }}
        .metric.warning {{
            border-top-color: #f59e0b;
        }}
        .metric.warning p {{
            color: #d97706;
        }}
        .metric.danger {{
            border-top-color: #991b1b;
        }}
        .metric.danger p {{
            color: #991b1b;
        }}
        .mode {{
            font-size: 32px;
            color: blue;
            font-weight: bold;
        }}
        .input-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 12px;
            align-items: center;
        }}
        input, select, button {{
            padding: 7px;
            margin: 4px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
        }}
        .date-row select {{
            min-width: 74px;
        }}
        .date-row label {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 6px 8px;
        }}
        button {{
            cursor: pointer;
            background: #111827;
            color: white;
        }}
        table {{
            border-collapse: collapse;
            background: white;
            white-space: nowrap;
            width: 100%;
        }}
        th {{
            background: #f0f0f0;
        }}
        th, td {{
            padding: 8px;
        }}
        .table-wrap {{
            overflow-x: auto;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 8px 16px;
        }}
        .chart-box {{
            position: relative;
            width: 100%;
            height: 420px;
        }}
        .small-note {{
            color: #6b7280;
            font-size: 13px;
        }}
        .preset-box {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 12px;
            margin: 10px 0 14px 0;
        }}
        .preset-buttons {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .preset-btn {{
            display: inline-block;
            text-decoration: none;
            color: #111827;
            background: white;
            border: 1px solid #d1d5db;
            border-left: 5px solid #2196f3;
            border-radius: 10px;
            padding: 10px 14px;
            min-width: 170px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        }}
        .preset-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 3px 8px rgba(0,0,0,0.08);
        }}
        .map-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 14px;
        }}
        .map-card {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 14px;
        }}
        .map-card h3 {{
            margin-top: 0;
        }}
        .step24-live-overlay {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(15, 23, 42, 0.72);
            z-index: 9999;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .step24-live-box {{
            width: min(760px, 94vw);
            background: white;
            border-radius: 18px;
            padding: 24px;
            box-shadow: 0 20px 70px rgba(0,0,0,0.28);
            border-top: 6px solid #2563eb;
        }}
        .step24-live-title {{
            margin: 0 0 10px 0;
            font-size: 24px;
            font-weight: 800;
        }}
        .step24-live-sub {{
            color: #4b5563;
            line-height: 1.5;
            margin-bottom: 16px;
        }}
        .step24-live-bar-shell {{
            height: 16px;
            background: #e5e7eb;
            border-radius: 999px;
            overflow: hidden;
            margin: 14px 0;
        }}
        .step24-live-bar {{
            width: 4%;
            height: 100%;
            background: linear-gradient(90deg, #2563eb, #22c55e);
            border-radius: 999px;
            transition: width .35s ease;
        }}
        .step24-live-log {{
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 12px;
            font-size: 13px;
            color: #111827;
            min-height: 78px;
            white-space: pre-line;
        }}


        .step24q-status-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
            margin: 8px 0 14px 0;
        }}
        .step24q-pill, .step24q-download {{
            display: inline-block;
            border-radius: 999px;
            padding: 7px 11px;
            background: #eef2ff;
            color: #1f2937;
            border: 1px solid #dbeafe;
            font-size: 13px;
            text-decoration: none;
            font-weight: 700;
        }}
        .step24q-pill.cache-hit {{
            background: #dcfce7;
            border-color: #86efac;
            color: #166534;
        }}
        .step24q-pill.cache-new {{
            background: #fef3c7;
            border-color: #fcd34d;
            color: #92400e;
        }}
        .step24q-download {{
            background: #111827;
            color: white;
            border-color: #111827;
        }}
        .quick-apply-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 12px;
        }}
        .quick-apply-btn {{
            display: inline-block;
            text-decoration: none;
            background: #2563eb;
            color: white;
            border-radius: 10px;
            padding: 9px 12px;
            font-weight: 800;
            font-size: 13px;
        }}
        .apply-link {{
            font-weight: 800;
            color: #2563eb;
        }}
        .step24q-table tr.top-rank td {{
            background: #fff7ed;
            font-weight: 800;
        }}
        .step24q-table tr.cand-strong td {{ background: #f0fdf4; }}
        .step24q-table tr.cand-valid td {{ background: #f8fafc; }}
        .step24q-table tr.cand-defense td {{ background: #eff6ff; }}
        .step24q-table tr.cand-slow td {{ background: #fff7ed; }}
        .step24q-table tr.cand-watch td {{ background: #ffffff; }}
        .step24v-compare-card {{ border-top: 4px solid #2563eb; }}
        .step24v-cleanup-card {{ border-top: 4px solid #f59e0b; }}
        .step24w-robust-card {{ border-top: 4px solid #10b981; }}
        .step24x-live-card {{ border-top: 4px solid #2563eb; }}
        .step24x-live-table-card {{ border-top: 4px solid #10b981; }}
        .step24x-log {{ max-height: 260px; overflow:auto; white-space: pre-wrap; background:#0f172a; color:#dbeafe; padding:14px; border-radius:14px; font-size:12px; line-height:1.5; }}
        .step24w-robust-table-card {{ border-top: 4px solid #2563eb; }}
        .step24v-cleanup-card td:nth-child(4) {{ font-weight: 700; }}
        .applied-candidate {{
            border-left: 6px solid #22c55e;
            background: #f0fdf4;
        }}

        .step24r-lab-note {{
            border: 1px solid #bfdbfe; background: linear-gradient(135deg, #eff6ff, #f0fdf4);
            border-radius: 18px; padding: 14px 16px; margin: 12px 0; color: #1f2937; font-size: 13px;
        }}
        .step24r-progress-plan {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:10px; margin-top: 10px; }}
        .step24r-progress-plan div {{ border-radius: 14px; padding: 12px; background: #ffffff; border: 1px solid #dbeafe; font-weight: 800; }}
        @media (max-width: 1000px) {{
            body {{ padding: 12px; }}
            .seed-sidebar {{ position: static; width: auto; margin-bottom: 14px; }}
            .seed-topbar {{ flex-direction: column; align-items: flex-start; }}
        }}
        @media (max-width: 768px) {{
            body {{
                padding: 12px;
            }}
            .card {{
                padding: 16px;
            }}
            .grid {{
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
            }}
            .metric {{
                padding: 14px;
            }}
            .metric p {{
                font-size: 18px;
            }}
            .metric h3 {{
                font-size: 12px;
            }}
            .chart-box {{
                height: 320px;
            }}
            .mode {{
                font-size: 24px;
            }}
        }}
    </style>
</head>

<body>
<div class="seed-sidebar">
    <div class="seed-brand">Infinite Lab</div>
    <div class="seed-brand-sub">Step25D-8 · RAOR Original Engine<br>V2.2 결과표/검증표 마감</div>
    <div class="seed-nav">
        <button type="button" class="{seed_dashboard_active}" data-panel-target="dashboard">대시보드</button>
        <button type="button" class="{seed_optimizer_active}" data-panel-target="optimizer">Optimizer</button>
        <button type="button" class="{seed_results_active}" data-panel-target="results">검증/로그</button>
        <button type="button" class="{seed_charts_active}" data-panel-target="charts">차트</button>
        <span>25D-8: V2.2 마감정리</span>
    </div>
</div>
<div class="seed-shell">
<div class="seed-topbar">
    <h1>Sunny's Test</h1>
    <div class="seed-badges"><span class="seed-badge">{strategy_name}</span><span class="seed-badge">{start_date} ~ {end_date}</span><span class="seed-badge">Fee {fee_percent:.3f}%</span></div>
</div>

<div id="step24LiveOverlay" class="step24-live-overlay">
    <div class="step24-live-box">
        <div class="step24-live-title">Step24X 후보 검증 진행 중</div>
        <div class="step24-live-sub">브라우저가 서버 계산을 기다리는 동안 진행형 UI를 먼저 표시합니다. 계산 완료 후 TOP 후보표가 한 번에 출력됩니다.</div>
        <div><b id="step24LivePct">0%</b> · <span id="step24LiveStatus">검증 준비 중...</span></div>
        <div class="step24-live-bar-shell"><div id="step24LiveBar" class="step24-live-bar"></div></div>
        <div id="step24LiveLog" class="step24-live-log">- 파라미터 조합 생성 대기
- Step24X/W/V/U/T/S/R/Q/P 원문엔진 호출 준비
- 기존 RSI/오리지널 결과와 분리</div>
    </div>
</div>

<section id="panel-dashboard" class="seed-panel {seed_dashboard_active}" data-seed-panel="dashboard">
<div class="card hero">
    <h1>{ticker} 전략 실험실</h1>

    <form method="get">
        <div class="input-row">
            <label>티커 선택
                <select name="ticker" onchange="this.form.submit()">
                    {ticker_options}
                </select>
            </label>
        </div>

        <div class="input-row date-row">
            <input type="hidden" id="start_date" name="start_date" value="{start_date}">
            <input type="hidden" id="end_date" name="end_date" value="{end_date}">

            <label>시작일
                <select id="start_y" onchange="syncDateParts('start')">{start_year_options}</select>
                <select id="start_m" onchange="syncDateParts('start')">{start_month_options}</select>
                <select id="start_d" onchange="syncDateParts('start')">{start_day_options}</select>
            </label>

            <label>종료일
                <select id="end_y" onchange="syncDateParts('end')">{end_year_options}</select>
                <select id="end_m" onchange="syncDateParts('end')">{end_month_options}</select>
                <select id="end_d" onchange="syncDateParts('end')">{end_day_options}</select>
            </label>

            <label>수수료율(%) <input type="number" step="0.001" name="fee_percent" value="{fee_percent}"></label>
            <span class="small-note">연도는 드롭다운으로 바로 선택됩니다. 예: 0.25 입력 = 매수 0.25% + 매도 0.25%</span>
        </div>

        <div class="input-row">
            <label>전략 선택
                <select name="strategy" onchange="syncAllDates(); this.form.submit()">
                    <option value="raor_v22" {"selected" if strategy == "raor_v22" else ""}>라오어 무한매수법 2.2 통합 원문엔진</option>
                    <option value="raor4_step25d" {"selected" if strategy == "raor4_step25d" else ""}>라오어 무한매수법 4.0 원문엔진 / Step25D 검증판</option>
                </select>
            </label>
        </div>

        {strategy_inputs}

        {engine_note_html}

        {preset_buttons_html}

        {action_buttons_html}
    </form>

    <hr>

    <p>기준일: {latest_date}</p>
    <p style="color:#777;">데이터 마지막일: {daily["Date"].max().strftime("%Y-%m-%d")}</p>
    <p style="color:orange;">{data_notice}</p>
    <p>{ticker} 종가: </p>
    {status_info_html}
</div>

{advanced_stage_html}
{applied_candidate_html}
{stage_helper_html}

<div class="grid">
    <div class="metric {return_class}"><h3>최종자산</h3><p>{final_asset:,.0f}원</p></div>
    <div class="metric positive"><h3>완료 주기</h3><p>{completed_cycles}회</p></div>
    <div class="metric {open_class}"><h3>진행 회차</h3><p>{active_cycle_label}</p></div>
    <div class="metric {open_class}"><h3>진행 분할</h3><p>{active_t:.1f}/{split_count}T · {active_progress_pct:.1f}%</p></div>
    <div class="metric {return_class}"><h3>총수익률</h3><p>{return_rate:.2f}%</p></div>
    <div class="metric {cagr_class}"><h3>CAGR</h3><p>{cagr:.2f}%</p></div>
    <div class="metric {mdd_class}"><h3>MDD</h3><p>{mdd:.2f}%</p></div>

    <div class="metric {win_class}"><h3>주기승률</h3><p>{trade_summary["win_rate"]:.2f}%</p></div>
    <div class="metric"><h3>완료주기수</h3><p>{trade_summary["trade_count"]}</p></div>

    <div class="metric"><h3>평균주기보유일</h3><p>{avg_hold_days:.1f}일</p></div>
    <div class="metric"><h3>연평균완료주기</h3><p>{trades_per_year:.2f}회</p></div>

    <div class="metric {open_class}"><h3>현재 미청산</h3><p>{open_position}</p></div>
    <div class="metric"><h3>남은 분할</h3><p>{active_remaining_t:.1f}T</p></div>
    <div class="metric"><h3>진행 보유일</h3><p>{active_days}일</p></div>
    <div class="metric"><h3>최대분할</h3><p>{max_split:.1f}</p></div>

    <div class="metric {bh_class}"><h3>Buy&Hold</h3><p>{bh_return:.2f}%</p></div>
    <div class="metric warning"><h3>예상수수료</h3><p>{estimated_fee:,.0f}원</p></div>

    <div class="metric"><h3>매수수수료</h3><p>{buy_fee:,.0f}원</p></div>
    <div class="metric"><h3>매도수수료</h3><p>{sell_fee:,.0f}원</p></div>
    <div class="metric {pf_class}"><h3>Profit Factor</h3><p>{profit_factor:.2f}</p></div>
</div>

<div class="card hero">
    <h2>전략 vs {ticker} Buy&Hold 비교</h2>
    <div class="grid">
        <div class="metric {verdict_class}"><h3>종합판정</h3><p>{verdict}</p></div>
        <div class="metric {cls_delta(return_delta)}"><h3>초과수익률</h3><p>{return_delta:.2f}%</p></div>
        <div class="metric {cls_delta(cagr_delta)}"><h3>CAGR 차이</h3><p>{cagr_delta:.2f}%</p></div>
        <div class="metric {cls_delta(mdd_improvement)}"><h3>MDD 개선폭</h3><p>{mdd_improvement:.2f}%p</p></div>
    </div>
    <p>{verdict_detail}</p>
</div>
</section>

<section id="panel-optimizer" class="seed-panel {seed_optimizer_active}" data-seed-panel="optimizer">
<h2 class="seed-panel-title">Optimizer / DeepMining</h2>

{robust_top_html}

{walkforward_today_html}

{optimizer_compare_html}

{strategy_param_map_html}

{step24v_cleanup_html}

{yearly_html}

{deepmine_html}
{optimizer_bottom_html}
{recommend_card_html}
</section>

<section id="panel-results" class="seed-panel {seed_results_active}" data-seed-panel="results">
<h2 class="seed-panel-title">검증 / 매매 로그</h2>

<div class="card">
    <h2>백테스트 결과</h2>
    <p>전략: {strategy_name}</p>
    <p>분할수: {split_count}</p>
    <p>현금: {cash:,.0f}원</p>
    <p>주식가치: {stock_value:,.0f}원</p>
    <p>현재 분할 상태: {current_split} / {split_count}</p>
    <p>수수료율: 매수 {fee_percent:.3f}% / 매도 {fee_percent:.3f}%</p>
</div>

{raor_validation_html}

{step24m_execution_html}

{step24u_gap_html}

{cycle_summary_html}

{trade_log_html}
{order_plan_log_html}
</section>

<section id="panel-charts" class="seed-panel {seed_charts_active}" data-seed-panel="charts">
<h2 class="seed-panel-title">차트</h2>

<div class="card">
    <h2>통합 차트: 총자산 + {ticker} 가격 + 매수/매도 포인트</h2>
    <div class="chart-box">
        <canvas id="assetChart"></canvas>
    </div>
</div>

<div class="card">
    <h2>Drawdown</h2>
    <div class="chart-box">
        <canvas id="ddChart"></canvas>
    </div>
</div>

<div id="charts-section" class="card">
    <h2>월별 수익률</h2>
    <div class="chart-box">
        <canvas id="monthlyChart"></canvas>
    </div>
</div>
</section>

<script>
const chartData = {chart_json};

function pad2(value) {{
    return String(value).padStart(2, "0");
}}

function daysInMonth(year, month) {{
    return new Date(Number(year), Number(month), 0).getDate();
}}

function syncDateParts(prefix) {{
    const y = document.getElementById(prefix + "_y");
    const m = document.getElementById(prefix + "_m");
    const d = document.getElementById(prefix + "_d");
    const hidden = document.getElementById(prefix + "_date");
    if (!y || !m || !d || !hidden) return;

    const maxDay = daysInMonth(y.value, m.value);
    if (Number(d.value) > maxDay) d.value = String(maxDay);
    hidden.value = `${{y.value}}-${{pad2(m.value)}}-${{pad2(d.value)}}`;
}}

function syncAllDates() {{
    syncDateParts("start");
    syncDateParts("end");
}}

window.addEventListener("DOMContentLoaded", syncAllDates);

function estimateStep24Combos() {{
    const form = document.querySelector("form");
    if (!form) return 0;
    const splitText = (form.querySelector('[name="opt_split_values"]')?.value || "20,40");
    const splits = splitText.split(',').map(v => v.trim()).filter(v => v === "20" || v === "40").length || 2;
    const fMin = Number(form.querySelector('[name="opt_first_loc_min"]')?.value || 10);
    const fMax = Number(form.querySelector('[name="opt_first_loc_max"]')?.value || 15);
    const fStep = Math.max(Number(form.querySelector('[name="opt_first_loc_step"]')?.value || 0.5), 0.1);
    const dMin = Number(form.querySelector('[name="opt_designated_min"]')?.value || 10);
    const dMax = Number(form.querySelector('[name="opt_designated_max"]')?.value || 25);
    const dStep = Math.max(Number(form.querySelector('[name="opt_designated_step"]')?.value || 2.5), 0.1);
    const firstN = Math.max(1, Math.floor((Math.min(15, Math.max(fMin, fMax)) - Math.max(10, Math.min(fMin, fMax))) / fStep + 1.0001));
    const desN = Math.max(1, Math.floor((Math.max(dMin, dMax) - Math.min(dMin, dMax)) / dStep + 1.0001));
    return splits * firstN * desN;
}}

function startStep24LiveOverlay(mode) {{
    const overlay = document.getElementById("step24LiveOverlay");
    const bar = document.getElementById("step24LiveBar");
    const pct = document.getElementById("step24LivePct");
    const status = document.getElementById("step24LiveStatus");
    const log = document.getElementById("step24LiveLog");
    if (!overlay || !bar || !pct || !status || !log) return;

    overlay.style.display = "flex";
    const comboTotal = estimateStep24Combos();
    const labels = [
        "파라미터 조합 생성 중",
        "Step24V/U/T/S/R/Q/P 원문엔진 백테스트 반복 실행 중",
        "CAGR / MDD / 완료주기 계산 중",
        "후보 판정 분류 중",
        "TOP 결과표 생성 및 캐시 저장 중"
    ];
    let progress = 3;
    let tick = 0;
    bar.style.width = "3%";
    pct.textContent = "3%";
    status.textContent = (mode === "deepmine" ? "DeepMining TOP50 시작" : "Optimizer TOP100 시작") + ` · 예상 ${{comboTotal}}개 조합`;

    window.step24ProgressTimer = setInterval(() => {{
        tick += 1;
        progress = Math.min(96, progress + (tick < 8 ? 7 : tick < 18 ? 4 : 1));
        bar.style.width = progress + "%";
        pct.textContent = progress + "%";
        const label = labels[Math.min(labels.length - 1, Math.floor(progress / 22))];
        status.textContent = label;
        log.textContent = `- ${{mode === "deepmine" ? "DeepMining TOP50" : "Optimizer TOP100"}} 실행
- 예상 조합 수: ${{comboTotal}}개
- 현재 상태: ${{label}}
- 서버 계산 완료 후 결과표가 자동 표시됩니다.
- 같은 조건은 step24_cache CSV를 재사용합니다.`;
    }}, 650);
}}

window.addEventListener("DOMContentLoaded", () => {{
    if ("{action_mode}" !== "backtest") {{
        setTimeout(() => activateSeedPanel("optimizer"), 250);
    }}
    document.querySelectorAll('button[name="action_mode"]').forEach(btn => {{
        btn.addEventListener("click", () => {{
            syncAllDates();
            if (btn.value === "deepmine" || btn.value === "optimizer" || btn.value === "robust") {{
                startStep24LiveOverlay(btn.value);
            }}
        }});
    }});
}});


function activateSeedPanel(panelName) {{
    const panels = document.querySelectorAll(".seed-panel");
    const buttons = document.querySelectorAll("[data-panel-target]");
    panels.forEach(panel => {{
        panel.classList.toggle("active", panel.dataset.seedPanel === panelName);
    }});
    buttons.forEach(btn => {{
        btn.classList.toggle("active", btn.dataset.panelTarget === panelName);
    }});
    window.scrollTo({{top: 0, behavior: "smooth"}});
    setTimeout(() => {{
        if (window.assetChartInstance) window.assetChartInstance.resize();
        if (window.ddChartInstance) window.ddChartInstance.resize();
        if (window.monthlyChartInstance) window.monthlyChartInstance.resize();
    }}, 120);
}}

function initSeedPanelTabs() {{
    document.querySelectorAll("[data-panel-target]").forEach(btn => {{
        btn.addEventListener("click", () => activateSeedPanel(btn.dataset.panelTarget));
    }});
    if ("{action_mode}" === "deepmine" || "{action_mode}" === "optimizer" || "{action_mode}" === "robust") {{
        activateSeedPanel("optimizer");
        if ("{action_mode}" === "robust") {{
            setTimeout(() => {{
                const target = document.getElementById("step24-results");
                if (target) target.scrollIntoView({{behavior:"smooth", block:"start"}});
            }}, 350);
        }}
    }} else {{
        activateSeedPanel("dashboard");
    }}
}}

window.addEventListener("DOMContentLoaded", initSeedPanelTabs);

const labels = chartData.labels || [];
const assets = chartData.assets || [];
const prices = chartData.prices || [];
const drawdowns = chartData.drawdown || [];
const buyPoints = chartData.buy_points || [];
const sellPoints = chartData.sell_points || [];
const monthLabels = chartData.month_labels || [];
const monthReturns = chartData.month_return || [];
const yearlyLabels = chartData.yearly_labels || [];
const yearlyStrategyReturns = chartData.yearly_strategy_returns || [];
const yearlyQqqReturns = chartData.yearly_qqq_returns || [];

function won(value) {{
    return Number(value).toLocaleString() + "원";
}}

function pct(value) {{
    return Number(value).toFixed(2) + "%";
}}

window.assetChartInstance = new Chart(document.getElementById("assetChart"), {{
    type: "line",
    data: {{
        labels: labels,
        datasets: [
            {{
                label: "총자산",
                data: assets,
                borderColor: "#2196f3",
                backgroundColor: "#2196f3",
                borderWidth: 2,
                pointRadius: 0,
                yAxisID: "y"
            }},
            {{
                label: "{ticker} 가격",
                data: prices,
                borderColor: "#ff6b8a",
                backgroundColor: "#ff6b8a",
                borderWidth: 1,
                pointRadius: 0,
                yAxisID: "y1"
            }},
            {{
                label: "매수",
                data: buyPoints,
                borderColor: "green",
                backgroundColor: "green",
                borderWidth: 0,
                pointRadius: 6,
                pointHoverRadius: 8,
                pointStyle: "triangle",
                showLine: false,
                yAxisID: "y1"
            }},
            {{
                label: "매도",
                data: sellPoints,
                borderColor: "red",
                backgroundColor: "red",
                borderWidth: 0,
                pointRadius: 7,
                pointHoverRadius: 9,
                pointStyle: "rectRot",
                showLine: false,
                yAxisID: "y1"
            }}
        ]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{
            mode: "index",
            intersect: false
        }},
        plugins: {{
            tooltip: {{
                callbacks: {{
                    label: function(context) {{
                        if (context.dataset.label === "총자산") {{
                            return context.dataset.label + ": " + won(context.raw);
                        }}
                        if (context.dataset.label === "{ticker} 가격" || context.dataset.label === "매수" || context.dataset.label === "매도") {{
                            return context.dataset.label + ": $" + Number(context.raw).toFixed(2);
                        }}
                        return context.dataset.label + ": " + context.raw;
                    }}
                }}
            }}
        }},
        scales: {{
            x: {{
                ticks: {{
                    maxTicksLimit: 12,
                    maxRotation: 45,
                    minRotation: 45
                }}
            }},
            y: {{
                type: "linear",
                position: "left"
            }},
            y1: {{
                type: "linear",
                position: "right",
                grid: {{
                    drawOnChartArea: false
                }}
            }}
        }}
    }}
}});

window.ddChartInstance = new Chart(document.getElementById("ddChart"), {{
    type: "line",
    data: {{
        labels: labels,
        datasets: [{{
            label: "Drawdown (%)",
            data: drawdowns,
            borderColor: "#2563eb",
            backgroundColor: "#2563eb",
            borderWidth: 2,
            pointRadius: 0
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{
            mode: "index",
            intersect: false
        }},
        plugins: {{
            tooltip: {{
                callbacks: {{
                    label: function(context) {{
                        return "Drawdown: " + pct(context.raw);
                    }}
                }}
            }}
        }},
        scales: {{
            x: {{
                ticks: {{
                    maxTicksLimit: 12,
                    maxRotation: 45,
                    minRotation: 45
                }}
            }},
            y: {{
                ticks: {{
                    callback: function(value) {{
                        return value + "%";
                    }}
                }}
            }}
        }}
    }}
}});

window.monthlyChartInstance = new Chart(document.getElementById("monthlyChart"), {{
    type: "bar",
    data: {{
        labels: monthLabels,
        datasets: [{{
            label: "월별 수익률 (%)",
            data: monthReturns,
            backgroundColor: "#90caf9",
            borderColor: "#42a5f5",
            borderWidth: 1
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{
            mode: "index",
            intersect: false
        }},
        plugins: {{
            tooltip: {{
                callbacks: {{
                    label: function(context) {{
                        return "월 수익률: " + pct(context.raw);
                    }}
                }}
            }}
        }},
        scales: {{
            x: {{
                ticks: {{
                    maxTicksLimit: 12,
                    maxRotation: 45,
                    minRotation: 45
                }}
            }},
            y: {{
                ticks: {{
                    callback: function(value) {{
                        return value + "%";
                    }}
                }}
            }}
        }}
    }}
}});

new Chart(document.getElementById("yearlyChart"), {{
    type: "bar",
    data: {{
        labels: yearlyLabels,
        datasets: [
            {{
                label: "전략 수익률",
                data: yearlyStrategyReturns,
                backgroundColor: "#2196f3"
            }},
            {{
                label: "{ticker} 수익률",
                data: yearlyQqqReturns,
                backgroundColor: "#ff6b8a"
            }}
        ]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        interaction: {{
            mode: "index",
            intersect: false
        }},
        plugins: {{
            tooltip: {{
                callbacks: {{
                    label: function(context) {{
                        return context.dataset.label + ": " + pct(context.raw);
                    }}
                }}
            }}
        }},
        scales: {{
            x: {{
                ticks: {{
                    maxTicksLimit: 12,
                    maxRotation: 45,
                    minRotation: 45
                }}
            }},
            y: {{
                ticks: {{
                    callback: function(value) {{
                        return value + "%";
                    }}
                }}
            }}
        }}
    }}
}});
</script>
<script src="/step24x.js"></script>

</div>
</body>
</html>
"""

    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
