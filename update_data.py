"""
멀티티커 데이터 자동 생성기
- 생성 파일:
  {TICKER}_daily_with_mode.csv
  {TICKER}_weekly_mode.csv

사용법:
  python update_data.py
  python update_data.py QQQ SOXL SOXX

필요 패키지:
  pip install yfinance pandas
"""

import sys
from pathlib import Path
import pandas as pd

try:
    import yfinance as yf
except ImportError as exc:
    raise SystemExit("yfinance가 없습니다. 먼저 실행: pip install yfinance") from exc

from ticker_config import TICKER_LIST

START_DATE = "1999-01-01"
OUTPUT_DIR = Path(".")


def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def normalize_yfinance_df(df: pd.DataFrame) -> pd.DataFrame:
    """yfinance 결과를 Date/Open/High/Low/Close/Volume 컬럼으로 정리."""
    if df.empty:
        return df

    df = df.copy()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    df = df.reset_index()

    rename_map = {}
    for col in df.columns:
        clean = str(col).strip()
        if clean.lower() in ["date", "datetime"]:
            rename_map[col] = "Date"
        elif clean.lower() == "open":
            rename_map[col] = "Open"
        elif clean.lower() == "high":
            rename_map[col] = "High"
        elif clean.lower() == "low":
            rename_map[col] = "Low"
        elif clean.lower() in ["close", "adj close"]:
            rename_map[col] = "Close"
        elif clean.lower() == "volume":
            rename_map[col] = "Volume"

    df = df.rename(columns=rename_map)

    needed = ["Date", "Open", "High", "Low", "Close", "Volume"]
    existing = [col for col in needed if col in df.columns]
    df = df[existing].copy()

    if "Date" not in df.columns or "Close" not in df.columns:
        raise ValueError("Date 또는 Close 컬럼을 찾을 수 없습니다.")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.tz_localize(None)
    df = df.dropna(subset=["Date", "Close"]).sort_values("Date").reset_index(drop=True)

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def build_weekly_mode(daily: pd.DataFrame) -> pd.DataFrame:
    weekly = (
        daily.set_index("Date")
        .resample("W-FRI")
        .last()
        .dropna(subset=["Close"])
        .reset_index()
    )
    weekly["RSI"] = calc_rsi(weekly["Close"], 14)
    weekly["WeeklyRSI"] = weekly["RSI"]
    return weekly[["Date", "Close", "RSI", "WeeklyRSI"]].copy()


def attach_weekly_rsi(daily: pd.DataFrame, weekly: pd.DataFrame) -> pd.DataFrame:
    daily = daily.sort_values("Date").copy()
    weekly_rsi = weekly[["Date", "WeeklyRSI"]].sort_values("Date").copy()

    out = pd.merge_asof(
        daily,
        weekly_rsi,
        on="Date",
        direction="backward",
    )
    out["WeeklyRSI"] = pd.to_numeric(out["WeeklyRSI"], errors="coerce").fillna(50)
    out["RSI"] = out["WeeklyRSI"]
    out["MA5"] = out["Close"].rolling(5).mean()
    out["MA20"] = out["Close"].rolling(20).mean()
    out["MA200"] = out["Close"].rolling(200).mean()
    return out


def update_one_ticker(ticker: str) -> bool:
    ticker = ticker.upper().strip()
    print(f"\n[{ticker}] 다운로드 시작")

    try:
        raw = yf.download(
            ticker,
            start=START_DATE,
            progress=False,
            auto_adjust=True,
            threads=False,
        )
        daily = normalize_yfinance_df(raw)

        if daily.empty:
            print(f"[{ticker}] 데이터 없음 - 건너뜀")
            return False

        weekly = build_weekly_mode(daily)
        daily_with_mode = attach_weekly_rsi(daily, weekly)

        daily_path = OUTPUT_DIR / f"{ticker}_daily_with_mode.csv"
        weekly_path = OUTPUT_DIR / f"{ticker}_weekly_mode.csv"

        daily_with_mode.to_csv(daily_path, index=False, encoding="utf-8-sig")
        weekly.to_csv(weekly_path, index=False, encoding="utf-8-sig")

        print(f"[{ticker}] 완료")
        print(f"  daily 마지막일 : {daily_with_mode['Date'].max().strftime('%Y-%m-%d')}")
        print(f"  weekly 마지막일: {weekly['Date'].max().strftime('%Y-%m-%d')}")
        print(f"  저장: {daily_path.name}, {weekly_path.name}")
        return True

    except Exception as exc:
        print(f"[{ticker}] 실패: {exc}")
        return False


def main():
    tickers = [arg.upper() for arg in sys.argv[1:]] if len(sys.argv) > 1 else TICKER_LIST
    ok = 0
    fail = 0

    print("멀티티커 데이터 생성 시작")
    print("대상:", ", ".join(tickers))

    for ticker in tickers:
        if update_one_ticker(ticker):
            ok += 1
        else:
            fail += 1

    print("\n완료")
    print(f"성공: {ok}개 / 실패: {fail}개")


if __name__ == "__main__":
    main()
