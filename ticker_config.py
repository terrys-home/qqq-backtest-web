"""Step20+21 티커/프리셋/전략 파라미터 중앙관리 파일.

이 파일만 수정하면:
- app.py 드롭다운
- update_data.py 데이터 생성 대상
- optimizer_lab.py 최적화 대상
이 함께 바뀌도록 설계했다.
"""
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd


# =========================
# Step20: 티커 중앙관리
# =========================
TICKER_LIST = [
    "QQQ",
    "TQQQ",
    "SOXX",
    "SOXL",
    "TECL",
    "FAS",
    "USD",
    "NVDL",
    "TSLL",
    "SNXX",
]


TICKER_META = {
    "QQQ": {"name": "QQQ", "group": "기준 ETF", "risk": "중"},
    "TQQQ": {"name": "TQQQ", "group": "나스닥 3배", "risk": "상"},
    "SOXX": {"name": "SOXX", "group": "반도체 원지수", "risk": "중상"},
    "SOXL": {"name": "SOXL", "group": "반도체 3배", "risk": "상"},
    "TECL": {"name": "TECL", "group": "기술주 3배", "risk": "상"},
    "FAS": {"name": "FAS", "group": "금융 3배", "risk": "상"},
    "USD": {"name": "USD", "group": "반도체 2배", "risk": "중상"},
    "NVDL": {"name": "NVDL", "group": "엔비디아 2배", "risk": "상"},
    "TSLL": {"name": "TSLL", "group": "테슬라 2배", "risk": "상"},
    "SNXX": {"name": "SNXX", "group": "샌디스크 2배", "risk": "상"},
}


def ticker_dict():
    return {ticker: TICKER_META.get(ticker, {}).get("name", ticker) for ticker in TICKER_LIST}


# =========================
# Step21: 전략별 파라미터 맵
# =========================
STRATEGY_LABELS = {
    "rsi": "RSI 커스텀",
    "original": "오리지널",
    "original_upgrade": "오리지널 2.0",
    "infinite4": "무한매수 4.0 v0",
    "tteolsa": "떨사오팔",
    "jongsajongpal": "종사종팔",
}


STRATEGY_PARAM_MAP = {
    "rsi": {
        "label": "RSI 커스텀",
        "status": "작동중",
        "params": ["분할수", "매도 RSI", "극침체 분할", "침체 분할", "중립 분할", "상승 분할"],
        "note": "현재 Optimizer Lab의 메인 전략입니다.",
    },
    "original": {
        "label": "오리지널",
        "status": "작동중",
        "params": ["분할수", "목표수익률", "수수료율"],
        "note": "간단한 목표수익률 기반 무한매수 베이스입니다.",
    },
    "original_upgrade": {
        "label": "오리지널 2.0",
        "status": "작동중",
        "params": ["분할수", "목표수익률", "MA5 매수배수", "MA20 매수배수"],
        "note": "이평선 기반 추가 매수배수를 테스트합니다.",
    },
    "infinite4": {
        "label": "무한매수 4.0 v0",
        "status": "v0 작동중",
        "params": [
            "분할횟수: 20 / 30 / 40",
            "T = 총원금 ÷ 분할횟수",
            "미보유 시 1T 최초매수",
            "평단 이하 1T 추가매수",
            "목표수익률 도달 시 쿼터매도",
            "쿼터매도 비율 기본 25%",
        ],
        "note": "v0는 단순 백테스트 엔진입니다. 별점/전반전·후반전/소진모드/LOC·지정가 세부 로직은 v1에서 연결합니다.",
    },
    "tteolsa": {
        "label": "떨사오팔",
        "status": "준비중",
        "params": ["낙폭 %", "익절 %", "분할 수", "반등 매도폭", "최대 보유일", "하락장 보정"],
        "note": "업로드한 떨사오팔 백테스트 소스를 엔진으로 이식 예정입니다.",
    },
    "jongsajongpal": {
        "label": "종사종팔",
        "status": "준비중",
        "params": ["첫 진입", "추매 가격", "분할 청산", "익절/손절 기준"],
        "note": "후속 단계에서 별도 엔진을 붙일 자리입니다.",
    },
}


# =========================
# Step20: 티커별 TOP1/추천 프리셋
# =========================
TOP1_PRESETS = {
    "QQQ": {
        "rsi": {
            "balanced": {
                "label": "QQQ 안정 추천",
                "desc": "Score/Stability 기준",
                "split_count": 8,
                "sell_rsi": 80,
                "extreme_split": 2,
                "recession_split": 1,
                "neutral_split": 1,
                "boom_split": 1,
            }
        }
    },
    "TQQQ": {
        "rsi": {
            "balanced": {
                "label": "TQQQ 균형 추천",
                "desc": "CAGR/MDD 균형형",
                "split_count": 10,
                "sell_rsi": 80,
                "extreme_split": 2,
                "recession_split": 2,
                "neutral_split": 2,
                "boom_split": 0,
            },
            "aggressive": {
                "label": "TQQQ 공격 추천",
                "desc": "수익률 우선",
                "split_count": 10,
                "sell_rsi": 80,
                "extreme_split": 2,
                "recession_split": 1,
                "neutral_split": 2,
                "boom_split": 0,
            },
            "defensive": {
                "label": "TQQQ 방어 추천",
                "desc": "분할 확대",
                "split_count": 15,
                "sell_rsi": 75,
                "extreme_split": 3,
                "recession_split": 2,
                "neutral_split": 1,
                "boom_split": 0,
            },
        }
    },
    "SOXL": {
        "rsi": {
            "balanced": {
                "label": "SOXL 균형 추천",
                "desc": "TOP1 기반",
                "split_count": 8,
                "sell_rsi": 80,
                "extreme_split": 2,
                "recession_split": 1,
                "neutral_split": 1,
                "boom_split": 1,
            },
            "aggressive": {
                "label": "SOXL 공격 추천",
                "desc": "CAGR 우선",
                "split_count": 8,
                "sell_rsi": 80,
                "extreme_split": 2,
                "recession_split": 1,
                "neutral_split": 2,
                "boom_split": 1,
            },
            "defensive": {
                "label": "SOXL 방어튜닝",
                "desc": "MDD 완화 실험",
                "split_count": 12,
                "sell_rsi": 75,
                "extreme_split": 4,
                "recession_split": 2,
                "neutral_split": 1,
                "boom_split": 0,
            },
        }
    },
    "SOXX": {
        "rsi": {
            "balanced": {
                "label": "SOXX 균형 추천",
                "desc": "SOXL 비교 기준",
                "split_count": 10,
                "sell_rsi": 75,
                "extreme_split": 3,
                "recession_split": 2,
                "neutral_split": 1,
                "boom_split": 0,
            }
        }
    },
}


def get_preset(ticker, strategy="rsi", preset_type="balanced"):
    return (
        TOP1_PRESETS
        .get(ticker.upper(), {})
        .get(strategy, {})
        .get(preset_type)
    )


def get_preset_query(ticker, strategy="rsi", preset_type="balanced", **extra):
    preset = get_preset(ticker, strategy, preset_type)
    if not preset:
        return urlencode({"ticker": ticker, "strategy": strategy, **extra})

    payload = {
        "ticker": ticker.upper(),
        "strategy": strategy,
        "action_mode": "backtest",
    }

    for key, value in extra.items():
        if value is not None:
            payload[key] = value

    for key, value in preset.items():
        if key not in ["label", "desc"]:
            payload[key] = value

    return urlencode(payload)


def optimizer_compare_rows(strategy="rsi", tickers=None):
    """각 티커별 optimizer TOP100 CSV의 1등만 모아 비교용 row 반환."""
    rows = []
    target_tickers = tickers or TICKER_LIST

    for ticker in target_tickers:
        path = Path(f"{ticker}_{strategy}_optimizer_top100.csv")
        if not path.exists():
            continue

        try:
            df = pd.read_csv(path)
            if df.empty:
                continue
            rows.append(df.iloc[0].to_dict())
        except Exception:
            continue

    return rows
