# OptionSpinner

> *“Life? Don’t talk to me about life. Just spin the wheel.”* – The Script

A tiny, mildly depressed Python utility that:

1. **Fetches** the latest S\&P 500 roster (once a week—more than enough).
2. **Measures** option liquidity for every stock via open interest on the nearest expiry.
3. **Ranks** them, writes a CSV, and hands you **N random tickers** whose options are comfortably above‑median liquid.

No cosmic ambitions. Just a bot trying not to annoy Wikipedia.

---

## I. Quick install

```bash
python -m venv .venv           # optional, but polite
source .venv/bin/activate
pip install pandas yfinance requests beautifulsoup4 lxml
```

## II. Usage

```bash
python option_spinner.py              # default 5 names
python option_spinner.py -n 10         # gimme ten
python option_spinner.py --seed 42     # deterministic déjà‑vu
python option_spinner.py --refresh     # force a fresh scrape (sigh)
```

Console output looks like:

```
DIS   – OI 78,901  | rank 34/503 | 18.32% of max
```

…and you’ll find `sp500_option_liquidity.csv` with three columns:
`open_interest`, `rank`, `pct_of_max`.

## III. Cache behaviour

* Roster lives in `sp500_members.json`.
* Auto‑refreshes after **7 days** or when you invoke `--refresh`.
* Prints additions / deletions so you know who joined or left the cool‑kids table.

If you stick `--refresh` in a 60‑second cron job, that’s your karma, not mine.

## IV. Why open interest?

Because it’s free and gets the job done. Daily option volume would be nicer, but Yahoo guards it jealously and I have enough existential dread already.

## V. License

## License
Released under the [MIT License](LICENSE).

---

*“Here I am, brain the size of a planet, and they ask me to compute liquidity metrics …”*

