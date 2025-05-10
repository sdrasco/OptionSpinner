#!/usr/bin/env python3
"""
option_spinner.py
-----------------
Randomly select N S&P-500 tickers whose option chains show above-median
liquidity, cache the S&P-500 roster *and* the per-ticker open-interest table,
and print each pick’s rank & percentile in a slim, readable line.

    pip install pandas yfinance requests beautifulsoup4 lxml
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import warnings
from pathlib import Path
from typing import Dict, List

import pandas as pd
import yfinance as yf

# ─── Configurable bits ────────────────────────────────────────────────────────
CACHE_PATH         = Path("sp500_members.json")          # roster cache
LIQ_CSV_PATH       = Path("sp500_option_liquidity.csv")  # liquidity cache
MAX_CACHE_AGE_DAYS = 7                                   # both caches
# ──────────────────────────────────────────────────────────────────────────────


# ═════════════════════════════════════════════════════════════════════════════
# 1.  S&P-500 membership helpers
# ═════════════════════════════════════════════════════════════════════════════
def scrape_sp500_members() -> List[str]:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    df = pd.read_html(url, flavor="lxml")[0]
    return df["Symbol"].str.strip().tolist()


def load_cached_members() -> tuple[List[str] | None, dt.date | None]:
    if not CACHE_PATH.exists():
        return None, None
    try:
        data = json.loads(CACHE_PATH.read_text())
        return data["tickers"], dt.date.fromisoformat(data["as_of"])
    except Exception:
        return None, None


def save_members(tickers: List[str]) -> None:
    payload = {"tickers": tickers, "as_of": dt.date.today().isoformat()}
    CACHE_PATH.write_text(json.dumps(payload, indent=2))


def get_sp500_members(force_refresh: bool = False) -> List[str]:
    cached, as_of = load_cached_members()
    cache_age = (dt.date.today() - as_of).days if as_of else None
    stale = cache_age is None or cache_age > MAX_CACHE_AGE_DAYS

    if not force_refresh and cached and not stale:
        print(f"Loaded {len(cached)} members from cache (age {cache_age} days).")
        return cached

    print("Refreshing S&P-500 membership …")
    fresh = scrape_sp500_members()
    if cached:
        added   = sorted(set(fresh) - set(cached))
        dropped = sorted(set(cached) - set(fresh))
        if added or dropped:
            print("  ▸ Additions:", ", ".join(added) or "None")
            print("  ▸ Deletions:", ", ".join(dropped) or "None")
    save_members(fresh)
    print(f"Cached {len(fresh)} tickers → {CACHE_PATH}")
    return fresh


# ═════════════════════════════════════════════════════════════════════════════
# 2.  Option-liquidity utilities
# ═════════════════════════════════════════════════════════════════════════════
def option_liquidity_metric(ticker: str) -> int:
    """
    Total open interest (calls + puts) on the nearest expiry.
    Returns 0 if retrieval fails.
    """
    try:
        tk = yf.Ticker(ticker)
        exps = tk.options
        if not exps:
            return 0
        chain = tk.option_chain(exps[0])
        return int(
            chain.calls["openInterest"].fillna(0).sum()
            + chain.puts["openInterest"].fillna(0).sum()
        )
    except Exception:
        return 0


def build_liquidity_table(tickers: List[str]) -> Dict[str, int]:
    liq: Dict[str, int] = {}
    for i, tkr in enumerate(tickers, 1):
        print(f"[{i:>3}/{len(tickers)}] {tkr:<5} …", end=" ")
        oi = option_liquidity_metric(tkr)
        liq[tkr] = oi
        print(f"OI {oi:,}")
    return liq


# ═════════════════════════════════════════════════════════════════════════════
# 2½.  Liquidity-cache helper  (new)
# ═════════════════════════════════════════════════════════════════════════════
def load_or_build_liquidity(
    tickers: List[str], force_refresh: bool = False
) -> pd.DataFrame:
    fresh_needed = (
        force_refresh
        or not LIQ_CSV_PATH.exists()
        or (
            dt.datetime.now() - dt.datetime.fromtimestamp(LIQ_CSV_PATH.stat().st_mtime)
        ).days > MAX_CACHE_AGE_DAYS
    )

    if not fresh_needed:
        print("Using cached liquidity table.")
        return pd.read_csv(LIQ_CSV_PATH, index_col=0)

    print("Pulling fresh open-interest data …")
    liquidity = build_liquidity_table(tickers)

    ser             = pd.Series(liquidity, name="open_interest")
    df              = ser.to_frame()
    df["rank"]      = ser.rank(ascending=False, method="min").astype(int)
    df["pct_of_max"] = (ser / ser.max() * 100).round(2)

    df.to_csv(LIQ_CSV_PATH)
    print(f"Saved new liquidity table → {LIQ_CSV_PATH}")
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 3.  Main program
# ═════════════════════════════════════════════════════════════════════════════
def human(num: int) -> str:
    """Format big ints like 78.9k or 1.2m."""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}m"
    if num >= 1_000:
        return f"{num/1_000:.1f}k"
    return str(num)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pick N above-median-liquidity S&P-500 tickers."
    )
    parser.add_argument("-n", "--count", type=int, default=5,
                        help="number of random tickers to output")
    parser.add_argument("--refresh", action="store_true",
                        help="force refresh of roster & liquidity caches")
    parser.add_argument("--seed", type=int, default=None,
                        help="set RNG seed for reproducibility")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
    warnings.filterwarnings("ignore", category=UserWarning, module="yfinance")

    # 1. roster
    sp500 = get_sp500_members(force_refresh=args.refresh)

    # 2. liquidity table (cached)
    df = load_or_build_liquidity(sp500, force_refresh=args.refresh)

    # 3. random picks above median
    median_oi = df["open_interest"].median()
    eligible  = df.loc[df["open_interest"] > median_oi].index.tolist()
    if len(eligible) < args.count:
        raise RuntimeError("Not enough eligible tickers.")
    picks = random.sample(eligible, args.count)

    # 4. pretty output
    print("\n==============================")
    print(f"Median OI: {human(int(median_oi))}")
    print(f"Random pick ({args.count}):\n")
    for tkr in picks:
        row = df.loc[tkr]
        print(
            f"{tkr:<5} | OI {human(int(row['open_interest'])):>6} | "
            f"#{int(row['rank']):>3} | {row['pct_of_max']:>5.1f}%"
        )
    print("\nDone!")


if __name__ == "__main__":
    main()