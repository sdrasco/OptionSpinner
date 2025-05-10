# OptionSpinner

![OptionSpinner Logo](images/OptionSpinner_small.png)

OptionSpinner is a tiny Python utility that:

1. **Fetches** the latest S\&P 500 roster (no more than once a week, unless you insist).
2. **Measures** option liquidity for every stock via open interest on the nearest expiry.
3. **Ranks** the whole list, caches the table, and deals you **N random tickers** whose options are comfortably above‑median liquid.

---

## 1 · Quick install

```bash
python -m venv .venv              # optional, but polite
source .venv/bin/activate
pip install pandas yfinance requests beautifulsoup4 lxml
```

## 2 · Usage

```bash
python option_spinner.py              # default 5 names
python option_spinner.py -n 10        # gimme ten
python option_spinner.py --seed 42    # deterministic déjà‑vu
python option_spinner.py --refresh    # force fresh roster + liquidity fetch
```

### Sample console output

```
Loaded 503 members from cache (age 0 days).
Using cached liquidity table.

==============================
Median OI: 10.8k
Random pick (5):

PPL   | OI  15.7k | #205 |   0.7%
APA   | OI  25.2k | #153 |   1.1%
SMCI  | OI 480.6k | #  9 |  20.5%
CHRW  | OI  14.3k | #216 |   0.6%
GOOG  | OI 246.5k | # 19 |  10.5%

Done!
```

### Output files

* **`sp500_option_liquidity.csv`** – open‑interest table with columns `open_interest`, `rank`, `pct_of_max`.

## 3 · Cache behaviour

* **Roster** cached in `sp500_members.json`.
* **Liquidity** cached in `sp500_option_liquidity.csv`.
* Both caches auto‑refresh after **7 days** or when you pass `--refresh`.
* On refresh, additions and deletions are printed so you know who joined or left the cool‑kids table.

Running `--refresh` every minute is technically possible, but please don’t; Wikipedia will notice.

## 4 · Why open interest?

Open interest is free and stable. True option volume is more responsive intraday but requires a paid data feed this toy doesn’t use.

## 5 · License

Released under the [MIT License](LICENSE).

---

*“Here I am, brain the size of a planet, and they ask me to compute liquidity metrics …”*
