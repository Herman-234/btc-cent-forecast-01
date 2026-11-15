#!/usr/bin/env python3
"""BTC price forecast, 4 hours ahead (make.fun btc-cent-forecast-01).

Reads every case file <id>.in from $MAKEFUN_INPUT_DIR/input and writes a
forecast file <id>.out to $MAKEFUN_OUTPUT_DIR/output. Each output holds
exactly one JSON object: {"forecasts": [{"case": "<id>", "price": <n>]}.

Model: last close times exp(0.5 x time-of-day drift for the checkpoint
hour). Stdlib only. Deterministic: no clock, no randomness, no network.
"""

import json
import math
import os
from datetime import datetime, timezone

# Mean 4h log-return per checkpoint UTC hour, fitted on 252 checkpoints
# (42 per hour). Values are decimal log-returns, not percents; a checkpoint
# hour outside this table drifts 0.0 (pure persistence).
DRIFT_TABLE = ((0, -0.003), (4, 0.00091), (8, 0.0001), (12, -0.00295), (16, -0.00007), (20, -0.00107))
DRIFT = dict(DRIFT_TABLE)
SHRINK = 0.5
FALLBACK = 1.0
PRICE_CAP = 10_000_000.0


def utc_hour(stamp):
    """UTC hour of a checkpoint stamp (ISO text or epoch seconds)."""
    if isinstance(stamp, bool):
        return None
    if isinstance(stamp, (int, float)):
        try:
            return datetime.fromtimestamp(stamp, tz=timezone.utc).hour
        except (OverflowError, OSError, ValueError):
            return None
    text = str(stamp).strip()
    if not text:
        return None
    if text[-1:] in ("Z", "z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc)
    return parsed.hour


def last_close(case):
    """Last close of the btc-usdc market, or None when unusable."""
    markets = case.get("markets") if isinstance(case, dict) else None
    if not isinstance(markets, list):
        return None
    for market in markets:
        if not isinstance(market, dict):
            continue
        if market.get("id", "btc-usdc") != "btc-usdc":
            continue
        prices = market.get("prices")
        if not isinstance(prices, list) or not prices:
            continue
        value = prices[-1]
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and math.isfinite(value):
            return float(value)
    return None


def forecast_price(case):
    """Price 4h after the checkpoint, or the fallback when input is bad."""
    close = last_close(case)
    if close is None or close <= 0:
        return FALLBACK
    hour = utc_hour(case.get("at")) if isinstance(case, dict) else None
    drift = DRIFT.get(hour, 0.0) if hour is not None else 0.0
    price = close * math.exp(SHRINK * drift)
    price = round(price, 5)
    if not math.isfinite(price) or price <= 0:
        return FALLBACK
    if price >= PRICE_CAP:
        price = 9999999.99999
    return price


def run(indir, outdir):
    """Forecast every .in case into the output folder(s).

    Cases live under indir/input when the harness points at a competition
    folder, or directly under indir when it points at the input folder
    itself. Outputs go to outdir/output, with a copy beside it, so either
    layout finds them.
    """
    src = os.path.join(indir, "input")
    if not os.path.isdir(src):
        src = indir
    if not os.path.isdir(src):
        return
    dst = os.path.join(outdir, "output")
    os.makedirs(dst, exist_ok=True)
    for name in sorted(os.listdir(src)):
        if not name.endswith(".in"):
            continue
        stem = name[:-3]
        try:
            with open(os.path.join(src, name), "r", encoding="utf-8") as fh:
                case = json.load(fh)
        except (OSError, ValueError):
            case = {}
        if not isinstance(case, dict):
            case = {}
        ident = case.get("case")
        if not isinstance(ident, str) or not ident:
            ident = stem
        payload = {"forecasts": [{"case": ident, "price": forecast_price(case)}]}
        text = json.dumps(payload) + "\n"
        with open(os.path.join(dst, stem + ".out"), "w", encoding="utf-8") as fh:
            fh.write(text)
        with open(os.path.join(outdir, stem + ".out"), "w", encoding="utf-8") as fh:
            fh.write(text)


def main():
    indir = os.environ.get("MAKEFUN_INPUT_DIR", "")
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "")
    if not indir or not outdir:
        raise SystemExit("set MAKEFUN_INPUT_DIR and MAKEFUN_OUTPUT_DIR")
    run(indir, outdir)


if __name__ == "__main__":
    main()
