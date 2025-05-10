#!/usr/bin/env python3
"""
pick_liquid_sp500_tickers.py
----------------------------
Randomly select N S&P-500 tickers whose option chains show
above-median liquidity, cache the S&P-500 membership (to avoid
hammering Wikipedia), and report each ticker’s rank & percentile.

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
CACHE_PATH        = Path("sp500_members.json")   # where we cache the roster
MAX_CACHE_AGE_DAYS = 7                           # auto-refresh after N days
LIQ_CSV_PATH      = Path("sp500_option_liquidity.csv")  # output file
# ──────────────────────────────────────────────────────────────────────────────


# ═════════════════════════════════════════════════════════════════════════════
# 1.  S&P-500 membership helpers
# ═════════════════════════════════════════════════════════════════════════════
def scrape_sp500_members() -> List[str]:
    """Pull the current S&P-500 constituent table from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    df = pd.read_html(url, flavor="lxml")[0]
    return df["Symbol"].str.strip().tolist()


def load_cached_members() -> tuple[List[str] | None, dt.date | None]:
    """Return (tickers, as_of_date) or (None, None) if cache missing/corrupt."""
    if not CACHE_PATH.exists():
        return None, None
    try:
        with CACHE_PATH.open() as f:
            data = json.load(f)
        return data["tickers"], dt.date.fromisoformat(data["as_of"])
    except Exception:
        return None, None


def save_members(tickers: List[str]) -> None:
    payload = {"tickers": tickers, "as_of": dt.date.today().isoformat()}
    with CACHE_PATH.open("w") as f:
        json.dump(payload, f, indent=2)


def get_sp500_members(force_refresh: bool = False) -> List[str]:
    """
    Load cached members unless the cache is stale or refresh is forced.
    If we refresh, print adds/drops versus the prior cache.
    """
    cached, as_of = load_cached_members()
    cache_age = (dt.date.today() - as_of).days if as_of else None

    should_refresh = (
        force_refresh
        or cached is None
        or cache_age is None
        or cache_age > MAX_CACHE_AGE_DAYS
    )

    if not should_refresh:
        print(f"Loaded {len(cached)} members from cache (age {cache_age} days).")
        return cached

    print("Refreshing S&P-500 membership …")
    fresh = scrape_sp500_members()

    if cached:                                # diff against previous cache
        added   = sorted(set(fresh) - set(cached))
        dropped = sorted(set(cached) - set(fresh))
        if added or dropped:
            print("  ▸ Additions:", ", ".join(added) or "None")
            print("  ▸ Deletions:", ", ".join(dropped) or "None")
        else:
            print("  (No changes versus cached list)")

    save_members(fresh)
    print(f"Cached {len(fresh)} tickers → {CACHE_PATH}")
    return fresh


# ═════════════════════════════════════════════════════════════════════════════
# 2.  Option-liquidity utilities
# ═════════════════════════════════════════════════════════════════════════════
def option_liquidity_metric(ticker: str) -> int:
    """
    Liquidity proxy: total open interest (calls + puts) on the *nearest* expiry.
    Returns 0 on any retrieval problem.
    """
    try:
        tk = yf.Ticker(ticker)
        exps = tk.options
        if not exps:
            return 0
        nearest = exps[0]
        chain = tk.option_chain(nearest)
        total = (
            chain.calls["openInterest"].fillna(0).sum()
            + chain.puts["openInterest"].fillna(0).sum()
        )
        return int(total)
    except Exception:
        return 0


def build_liquidity_table(tickers: List[str]) -> Dict[str, int]:
    """
    Loop through tickers and return {ticker: open_interest}.
    Prints progress so long runs don’t look frozen.
    """
    liq: Dict[str, int] = {}
    for i, tkr in enumerate(tickers, 1):
        print(f"[{i:>3}/{len(tickers)}] {tkr:<5} …", end=" ")
        oi = option_liquidity_metric(tkr)
        liq[tkr] = oi
        print(f"OI {oi:,}")
    return liq


# ═════════════════════════════════════════════════════════════════════════════
# 3.  Main program
# ═════════════════════════════════════════════════════════════════════════════
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pick N above-median-liquidity S&P-500 tickers."
    )
    parser.add_argument("-n", "--count", type=int, default=5,
                        help="number of random tickers to output")
    parser.add_argument("--refresh", action="store_true",
                        help="force re-scrape of S&P-500 membership")
    parser.add_argument("--seed", type=int, default=None,
                        help="set RNG seed for reproducibility")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    warnings.filterwarnings("ignore", category=UserWarning, module="yfinance")

    # ------------------------------------------------------------------ roster
    sp500      = get_sp500_members(force_refresh=args.refresh)

    # ----------------------------------------------------------- pull liquidity
    liquidity  = build_liquidity_table(sp500)

    # ------------------------------------------------------- DataFrame w/ ranks
    ser             = pd.Series(liquidity, name="open_interest")
    df              = ser.to_frame()
    df["rank"]      = ser.rank(ascending=False, method="min").astype(int)
    df["pct_of_max"] = (ser / ser.max() * 100).round(2)   # e.g. 83.47

    # ---------------------------------------------------------- write full CSV
    df.to_csv(LIQ_CSV_PATH)
    print(f"\nFull liquidity table (rank & percentile) written to {LIQ_CSV_PATH}")

    # ------------------------------------------------------- sample candidates
    median_oi = ser.median()
    eligible  = df.loc[ser > median_oi].index.tolist()
    if len(eligible) < args.count:
        raise RuntimeError("Not enough eligible tickers to sample from.")

    picks = random.sample(eligible, args.count)

    # ------------------------------------------------------- pretty console out
    print("\n==============================")
    print(f"Median open interest: {median_oi:,.0f}")
    print(f"Random pick ({args.count} tickers):\n")
    for tkr in picks:
        row = df.loc[tkr]
        print(f"  {tkr:<5} – OI {row.open_interest:,}"
              f"  | rank {row.rank}/{len(df)}"
              f"  | {row.pct_of_max:.2f}% of max")
    print("\nDone!")


if __name__ == "__main__":
    main()