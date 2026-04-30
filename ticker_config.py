"""
Step22D Infinite Lab Core
RSI + 무한매수 4.0 V3
- Original / Original Upgrade 제거 방향
- 자동주문/RPA 없음
"""

TICKER_LIST = [
    "QQQ", "TQQQ", "SOXX", "SOXL", "TECL", "FAS", "USD", "NVDL", "TSLL", "SNXX",
]

STRATEGY_LABELS = {
    "rsi": "RSI 커스텀",
    "infinite4": "무한매수4.0 V1",
    "infinite4_v2": "무한매수4.0 V2",
    "infinite4_v3": "무한매수4.0 V3",
    "infinite4_v4": "무한매수4.0 V4 / Step23A-B-C",
    "infinite4_v5": "무한매수4.0 V5 / Step23E 동적별지점",
    "raor4_original": "라오어 무한매수4.0 원문엔진 / Step24A",
    "raor4_step24b": "라오어 무한매수4.0 원문엔진 / Step24B",
    "raor4_step24c": "라오어 무한매수4.0 원문엔진 / Step24C",
    "raor4_step24d": "라오어 무한매수4.0 원문엔진 / Step24D",
    "raor4_step24e": "라오어 무한매수4.0 원문엔진 / Step24E",
    "raor4_step24f": "라오어 무한매수4.0 원문엔진 / Step24F",
    "raor4_step24m": "라오어 무한매수4.0 원문엔진 / Step24M",
    "raor4_step24l": "라오어 무한매수4.0 원문엔진 / Step24L",
    "raor4_step24h": "라오어 무한매수4.0 원문엔진 / Step24H",
    "raor4_step24g": "라오어 무한매수4.0 원문엔진 / Step24G",
}

# 기존 app.py가 import하던 이름들을 유지하기 위한 호환용 기본값
TOP1_PRESETS = {}
STRATEGY_PARAM_MAP = {
    "rsi": {
        "label": "RSI 커스텀",
        "status": "사용 가능",
        "params": ["split_count", "sell_rsi", "extreme_split", "recession_split", "neutral_split", "boom_split"],
        "note": "기존 RSI 모드 백테스트 엔진입니다.",
    },
    "infinite4_v3": {
        "label": "무한매수4.0 V3",
        "status": "사용 가능",
        "params": ["split_count", "target_profit", "quarter_sell_ratio", "star_pct", "max_gap_pct", "max_hold_days"],
        "note": "V3: 전반전/후반전, 큰수매수 후보, LOC 괴리 제한, 보유일 관리 포함.",
    },
    "infinite4_v4": {
        "label": "무한매수4.0 V4 / Step23A-B-C",
        "status": "실험중",
        "params": ["split_count", "target_profit", "quarter_sell_ratio", "star_pct", "max_gap_pct", "max_hold_days", "sheet_loc_price", "sheet_big_buy_price", "sheet_sell_price"],
        "note": "V4: 언이시트 수동값 우선, 동적 별지점, 전/후반전 쿼터매도, 소진모드, LOC 괴리 제한 강화.",
    },
    "infinite4_v5": {
        "label": "무한매수4.0 V5 / Step23E 동적별지점",
        "status": "실험중",
        "params": ["split_count", "target_profit", "quarter_sell_ratio", "star_pct", "max_gap_pct", "max_hold_days", "sheet_loc_price", "sheet_big_buy_price", "sheet_sell_price"],
        "note": "V5: 별점 입력값을 초기값으로만 쓰고 전반전/후반전/소진모드, 분할진행률, 평균단가 대비 현재가로 별지점을 자동 가변합니다.",
    },
    "raor4_original": {
        "label": "라오어 무한매수4.0 원문엔진 / Step24A",
        "status": "원문기반 신규",
        "params": ["split_count", "first_loc_buffer_pct"],
        "note": "Step24A: T 기반 별% 공식, 첫매수 전날종가+10~15% LOC, 잔금/(분할수-T), 전반전 0.5T+0.5T 구조를 반영합니다.",
    },
    "raor4_step24b": {
        "label": "라오어 무한매수4.0 원문엔진 / Step24B",
        "status": "원문기반 확장",
        "params": ["split_count", "first_loc_buffer_pct"],
        "note": "Step24B: Step24A 기반에서 후반전, 소진모드, 쿼터매도 LOC, 후반전 지정가/LOC 분기, T 추적 로그를 강화합니다.",
    },
    "raor4_step24c": {
        "label": "라오어 무한매수4.0 원문엔진 / Step24C",
        "status": "원문기반 확장",
        "params": ["split_count", "first_loc_buffer_pct"],
        "note": "Step24C: Step24B 기반에서 매수일 표시 보정, 기간 직접 실행, 완료 주기별 손익 집계를 추가합니다.",
    },
    "raor4_step24d": {
        "label": "라오어 무한매수4.0 원문엔진 / Step24D",
        "status": "원문기반 검증",
        "params": ["split_count", "first_loc_buffer_pct"],
        "note": "Step24D: 완료주기 0 고정 보정, 원문검증 체크리스트, 주기별 상세 분석과 로그 컬럼을 강화합니다.",
    },
    "raor4_step24e": {
        "label": "라오어 무한매수4.0 원문엔진 / Step24E",
        "status": "원문기반 매도예약 보강",
        "params": ["split_count", "first_loc_buffer_pct"],
        "note": "Step24E: 매일 별LOC 25%와 지정가 75% 매도예약을 전후반 공통으로 반영합니다.",
    },
    "raor4_step24f": {
        "label": "라오어 무한매수4.0 원문엔진 / Step24F",
        "status": "원문기반 매도예약 검증",
        "params": ["split_count", "first_loc_buffer_pct", "designated_sell_pct"],
        "note": "Step24F: 매일 별LOC 25%와 지정가 75% 매도예약을 유지하고, 지정가 전량매도 수익률 드롭다운과 별LOC>지정가 경고 검증을 추가합니다.",
    },
    "raor4_step24m": {
        "label": "라오어 무한매수4.0 원문엔진 / Step24M",
        "status": "원문기반 체결검증+최적화준비",
        "params": ["split_count", "first_loc_buffer_pct", "designated_sell_pct"],
        "note": "Step24M: Step24L 구조에 가격겹침 오류, 일봉선후관계 불명, 전량매도 완료누락 카운터를 추가합니다.",
    },
    "raor4_step24l": {
        "label": "라오어 무한매수4.0 원문엔진 / Step24L",
        "status": "원문기반 체결검증",
        "params": ["split_count", "first_loc_buffer_pct", "designated_sell_pct"],
        "note": "Step24L: 별LOC 매수=별지점-0.01, 별LOC 매도=별지점, 가격겹침/일봉선후관계를 분리 검증합니다.",
    },
    "raor4_step24h": {
        "label": "라오어 무한매수4.0 원문엔진 / Step24H",
        "status": "원문기반 체결검증",
        "params": ["split_count", "first_loc_buffer_pct", "designated_sell_pct"],
        "note": "Step24H: Step24G 기반에서 지정가매도/별LOC매도/LOC매수 동시신호와 체결 플래그를 로그로 검증합니다.",
    },
    "raor4_step24g": {
        "label": "라오어 무한매수4.0 원문엔진 / Step24G",
        "status": "원문기반 매도예약 검증",
        "params": ["split_count", "first_loc_buffer_pct", "designated_sell_pct"],
        "note": "Step24G: Step24F의 매일 별LOC 25%와 지정가 75% 매도예약을 유지하고, 전량매도 지정가 수익률을 사용자가 직접 입력할 수 있게 합니다.",
    },
}


def ticker_dict():
    return {ticker: ticker for ticker in TICKER_LIST}


DEFAULT_RSI_PRESET = {
    "split_count": 10,
    "sell_rsi": 75,
    "extreme_split": 2,
    "recession_split": 2,
    "neutral_split": 1,
    "boom_split": 0,
}

DEFAULT_INFINITE4_V3_PRESET = {
    "split_count": 30,
    "target_profit": 7,
    "quarter_sell_ratio": 25,
    "star_pct": 7,
    "max_gap_pct": 20,
    "max_hold_days": 365,
}

DEFAULT_INFINITE4_V4_PRESET = {
    "split_count": 30,
    "target_profit": 7,
    "quarter_sell_ratio": 25,
    "star_pct": 7,
    "max_gap_pct": 20,
    "max_hold_days": 365,
    "sheet_loc_price": 0,
    "sheet_big_buy_price": 0,
    "sheet_sell_price": 0,
}

DEFAULT_RAOR4_PRESET = {
    "split_count": 40,
    "first_loc_buffer_pct": 12,
}

STRATEGY_PRESETS = {
    "QQQ": {
        "rsi": DEFAULT_RSI_PRESET,
        "infinite4_v3": DEFAULT_INFINITE4_V3_PRESET,
    },
    "TQQQ": {
        "rsi": {
            "split_count": 10,
            "sell_rsi": 80,
            "extreme_split": 2,
            "recession_split": 2,
            "neutral_split": 2,
            "boom_split": 0,
        },
        "infinite4_v3": DEFAULT_INFINITE4_V3_PRESET,
    },
    "SOXL": {
        "rsi": {
            "split_count": 8,
            "sell_rsi": 80,
            "extreme_split": 2,
            "recession_split": 1,
            "neutral_split": 1,
            "boom_split": 0,
        },
        "infinite4_v3": {
            "split_count": 40,
            "target_profit": 10,
            "quarter_sell_ratio": 25,
            "star_pct": 10,
            "max_gap_pct": 15,
            "max_hold_days": 365,
        },
    },
}

# 나머지 티커는 기본 프리셋 자동 보완
for _ticker in TICKER_LIST:
    STRATEGY_PRESETS.setdefault(_ticker, {})
    STRATEGY_PRESETS[_ticker].setdefault("rsi", DEFAULT_RSI_PRESET)
    STRATEGY_PRESETS[_ticker].setdefault("infinite4_v3", DEFAULT_INFINITE4_V3_PRESET)
    STRATEGY_PRESETS[_ticker].setdefault("infinite4_v4", DEFAULT_INFINITE4_V4_PRESET)
    STRATEGY_PRESETS[_ticker].setdefault("infinite4_v5", DEFAULT_INFINITE4_V4_PRESET)
    STRATEGY_PRESETS[_ticker].setdefault("raor4_original", DEFAULT_RAOR4_PRESET)
    STRATEGY_PRESETS[_ticker].setdefault("raor4_step24b", DEFAULT_RAOR4_PRESET)
    STRATEGY_PRESETS[_ticker].setdefault("raor4_step24c", DEFAULT_RAOR4_PRESET)
    STRATEGY_PRESETS[_ticker].setdefault("raor4_step24d", DEFAULT_RAOR4_PRESET)
    STRATEGY_PRESETS[_ticker].setdefault("raor4_step24e", DEFAULT_RAOR4_PRESET)
    STRATEGY_PRESETS[_ticker].setdefault("raor4_step24f", DEFAULT_RAOR4_PRESET)
    STRATEGY_PRESETS[_ticker].setdefault("raor4_step24m", DEFAULT_RAOR4_PRESET)
    STRATEGY_PRESETS[_ticker].setdefault("raor4_step24l", DEFAULT_RAOR4_PRESET)
    STRATEGY_PRESETS[_ticker].setdefault("raor4_step24h", DEFAULT_RAOR4_PRESET)
    STRATEGY_PRESETS[_ticker].setdefault("raor4_step24g", DEFAULT_RAOR4_PRESET)


def get_preset(ticker, strategy, preset_type=None):
    """기존 app.py/프리셋 버튼 호환용.

    - get_preset(ticker, strategy) 형태 지원
    - get_preset(ticker, strategy, preset_type) 형태도 오류 없이 지원
    """
    ticker = ticker.upper()
    preset = STRATEGY_PRESETS.get(ticker, {}).get(strategy, {})
    if preset_type:
        label_map = {
            "balanced": "균형형",
            "aggressive": "공격형",
            "defensive": "방어형",
        }
        enriched = dict(preset)
        enriched.setdefault("label", label_map.get(preset_type, preset_type))
        enriched.setdefault("desc", f"{strategy} 기본 프리셋")
        return enriched
    return preset


def get_preset_query(ticker, strategy, preset_type="balanced", start_date=None, end_date=None, fee_percent=0.25):
    preset = get_preset(ticker, strategy, preset_type) or {}
    params = {
        "ticker": ticker,
        "strategy": strategy,
        "start_date": start_date,
        "end_date": end_date,
        "fee_percent": fee_percent,
    }
    params.update({k: v for k, v in preset.items() if k not in ["label", "desc"]})

    # app.py의 무한매수 입력명과 맞춤
    if strategy in ["infinite4_v3", "infinite4_v4", "infinite4_v5", "raor4_original", "raor4_step24b", "raor4_step24c", "raor4_step24d", "raor4_step24e", "raor4_step24f", "raor4_step24g", "raor4_step24h", "raor4_step24l", "raor4_step24m"]:
        if "split_count" in params:
            params["infinite_split_count"] = params.pop("split_count")
        if "target_profit" in params:
            params["infinite_target_profit"] = params.pop("target_profit")

    return "&".join([f"{k}={v}" for k, v in params.items() if v is not None])


def optimizer_compare_rows(strategy="rsi"):
    """app.py의 Step20 비교 UI 호환용. 결과 파일이 없으면 빈 리스트 반환."""
    import os
    import pandas as pd

    rows = []
    for ticker in TICKER_LIST:
        candidates = [
            f"{ticker}_{strategy}_optimizer_top100.csv",
            f"{ticker}_optimizer_top100.csv",
        ]
        for file in candidates:
            if not os.path.exists(file):
                continue
            try:
                df = pd.read_csv(file)
                if not df.empty:
                    row = df.iloc[0].to_dict()
                    row.setdefault("Ticker", ticker)
                    rows.append(row)
                break
            except Exception:
                continue
    return rows
