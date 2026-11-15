#!/usr/bin/env python3
"""make.fun btc-cent-forecast-01 entry: BTC price 4h ahead, one guess per case.

Forecast: last close x exp(0.5 * time-of-day drift for the checkpoint hour).

Why this, and why so small -- the honest backtest (45 days of BTC 1-minute
closes, 252 checkpoints every 4h, score = mean absolute error in cents):
  * persistence (guess = last close) is the best single model found.
    tune MAE 36,020c, test MAE 48,564c. It IS the house baseline, so an entry
    that guesses exactly persistence ties the baseline and takes no prize
    (a prize needs a score strictly below it).
  * every trend/momentum model tested LOSES to persistence out of sample:
    72h/24h/12h/4h drift extrapolation +2% to +28% worse; EWMA momentum
    +4% to +26% worse; mean-reversion to 24h MA +0.3% to +6% worse;
    median-4h-change +2.1% worse; denoised last price (median/mean of the
    last 5-60 min) -0.6% to +4.5% on Binance and +3% to +27% worse on the
    kit's own 5 scored practice cases. At a 4h horizon BTC returns are,
    to the resolution of 252 cases, unpredictable: the best forecast under
    MAE (a proper scoring rule: the optimal guess is the conditional
    median) is the last price.
  * the only adjustment that did not lose out of sample is a heavily
    shrunk (x0.5) time-of-day drift: -1.67% in-sample, -0.17% out of
    sample (i.e. a wash, within noise). It is kept at half strength
    because a pure-persistence entry cannot win (tie = no prize), while
    this tilt costs ~nothing in expectation and gives the entry a real
    chance to land below the baseline on the 12 final cases by luck.
    It is a lottery ticket, and it is priced as one.

The drift table is the mean 4h log-return by checkpoint UTC hour, fitted
on all 252 Binance BTCUSDT checkpoints (2026-09-30 .. 2026-11-14).
The final's 12 checkpoints fall on hours 08, 12, 16, 20, 00, 04 UTC only.

Input:  $MAKEFUN_INPUT_DIR (else /input) holding <id>.in files, one JSON
  object per case: {"at", "case", "competition", "horizon_minutes": 240,
  "markets": [{"id": "btc-usdc", "prices": [4320 closes]}]}.
  The last price is the close at the checkpoint.
Output: $MAKEFUN_OUTPUT_DIR (else /output) gets <id>.out per case, exactly
  {"forecasts": [{"case": "<id>", "price": <number>}]}, price rounded to
  the 5-decimal grid and clamped to (0, 10_000_000), as RULES.txt requires.
  An invalid case is scored as persistence AND disqualifies the entry from
  prizes, so this program is written to never emit an invalid case: any
  parse problem falls back to a well-formed output (last usable price,
  else 1.0) instead of crashing.

Stdlib only, no network, no randomness, no clock use: two runs on the
same case write byte-identical output. Runs in milliseconds per case.
"""

import json
import math
import os
import sys

# Mean 4h log-return by checkpoint UTC hour, fitted on 252 Binance BTCUSDT
# checkpoints (2026-09-30..2026-11-14). Applied at half strength (x0.5).
TOD_DRIFT = {
    0: -0.00300,
    4: +0.00091,
    8: +0.00010,
    12: -0.00295,
    16: -0.00007,
    20: -0.00107,
}
SHRINK = 0.5

MIN_PRICE = 0.00001
MAX_PRICE = 9_999_999.99999


def price5(x):
    """Round to the 5-decimal grid, clamped to the scorer's (0, 10_000_000)."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return 1.0
    if not math.isfinite(x):
        return 1.0
    x = min(MAX_PRICE, max(MIN_PRICE, x))
    return round(x * 100000.0) / 100000.0


def checkpoint_hour(case):
    """UTC hour of the case's checkpoint, from its ISO 'at' field."""
    at = case.get("at") if isinstance(case, dict) else None
    if not isinstance(at, str):
        return None
    try:
        # "2026-11-10T06:00:00.000Z" -> hour 6. Fixed layout, no date parsing.
        return int(at[11:13])
    except (ValueError, IndexError):
        return None


def forecast(case):
    """One guess: last close tilted by the shrunk time-of-day drift."""
    try:
        markets = case["markets"]
        prices = markets[0]["prices"]
        last = float(prices[-1])
    except (KeyError, IndexError, TypeError, ValueError):
        return 1.0
    if not math.isfinite(last) or last <= 0:
        return 1.0
    hour = checkpoint_hour(case)
    drift = TOD_DRIFT.get(hour, 0.0) if hour is not None else 0.0
    return price5(last * math.exp(SHRINK * drift))


def main():
    in_dir = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    try:
        files = sorted(f for f in os.listdir(in_dir) if f.endswith(".in"))
    except OSError:
        files = []
    for fname in files:
        case_id = fname[: -len(".in")]
        guess = 1.0
        try:
            with open(os.path.join(in_dir, fname), "r", encoding="utf-8") as fh:
                case = json.load(fh)
            guess = forecast(case)
        except Exception:
            guess = 1.0
        out = {"forecasts": [{"case": case_id, "price": guess}]}
        with open(os.path.join(out_dir, case_id + ".out"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
