# make.fun — BTC price forecast, 4h ahead (`btc-cent-forecast-01`)

Entry for the $250 USDC bounty "Forecast Bitcoin's price 4 hours ahead,
12 times over 48 hours" (deadline Sun 15 Nov 2026 08:00 UTC / 15:00 WIB).
**Submission set = `main.py` + `LICENSE` (MIT) + this README.** Everything
else used to build it lives in `scratch/` (kit, backtests, price data).

## What the program does

Reads one case at a time: 4,320 one-minute BTC closes (72h up to a
checkpoint) in `/input/<id>.in`, writes one guess to `/output/<id>.out`:
exactly `{"forecasts": [{"case": "<id>", "price": <number>}]}`.

Forecast = **last close × exp(0.5 × time-of-day drift for the checkpoint
hour)**, price rounded to the 5-decimal grid and clamped to (0, 10,000,000).

The drift table is the mean 4h log-return by checkpoint UTC hour, fitted on
252 Binance BTCUSDT checkpoints (2026-09-30..2026-11-14):

| hour (UTC) | 00 | 04 | 08 | 12 | 16 | 20 |
|---|---|---|---|---|---|---|
| drift | −0.300% | +0.091% | +0.010% | −0.295% | −0.007% | −0.107% |

The final's 12 checkpoints fall on hours 08, 12, 16, 20, 00, 04 only.

## Why this — the honest backtest

45 days of BTC 1-minute closes, 252 checkpoints every 4h, score = mean
absolute error in cents (100 × mean |guess − actual|). Tune = first 60%,
test = last 40%.

- **Persistence (guess = last close) is the best model found.**
  Tune MAE 36,020c, test MAE 48,564c. It IS the house baseline, so an
  entry guessing exactly persistence ties the baseline and takes no prize
  (a prize needs a score *strictly below* it).
- Every trend/momentum model tested LOSES to persistence out of sample:
  72h/24h/12h/4h drift extrapolation +2% to +28% worse; EWMA momentum
  +4% to +26% worse; mean-reversion to 24h MA +0.3% to +6% worse;
  median-4h-change +2.1% worse; denoised last price (median/mean of the
  last 5–60 min) −0.6% to +4.5% on Binance and +3% to +27% worse on the
  kit's own 5 scored practice cases. At a 4h horizon BTC returns are, to
  the resolution of 252 cases, unpredictable.
- The only adjustment that did not lose out of sample is the heavily
  shrunk (×0.5) time-of-day drift: −1.67% in-sample, −0.17% out of sample
  (a wash, within noise). It is kept because pure persistence cannot win
  (tie = no prize), while this tilt costs ~nothing in expectation and
  gives the entry a real chance to land below the baseline on the 12
  final cases by luck. **This is a lottery ticket, priced as one.**
  Expected value ≈ $0–a few dollars; do not mistake it for an edge.

Practice cases (kit, real Orca pool data, 5 scored): model MAE 47,055c,
identical to persistence — the practice checkpoints fall on hours
02/06/10/14/18/22, which never occur in the final, so the tilt is 0
there. The tilt was verified separately on synthetic cases at the final's
hours (08: +$3.74; 12: −$110.20; 00: −$112.06 at ~$74,765).

Verified: deterministic (two runs byte-identical), ~0.04 s/case (limit 8 s),
stdlib only, no network, no clock, no randomness. Malformed input can
never produce an invalid case: any parse problem falls back to a
well-formed output (price 1.0) instead of crashing — an invalid case
would rank the entry below all-valid entries and forfeit prizes.

## Run it locally (practice)

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=scratch/kit/btc-cent-forecast-01-kit/input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

## Submission checklist (for the person submitting — not done by the builder)

- New public GitHub repo, created AFTER the competition opened
  (2026-11-14T20:00:00Z), containing `main.py` + `LICENSE` (+ README).
  Repo must be public; commit SHA submitted.
- Account: make.fun sign-in is by Solana wallet (the payout wallet).
  The entry message (`make.fun entry v1`) must be signed by a wallet on
  the account within 10 minutes of submitting; the prize is claimed in
  USDC on Solana from the $250 escrow.
- Transcripts: the AI sessions that built the entry must be uploaded
  (makefun bundle or loose files); the transcript gate needs ≥30% of
  counted lines accounted for and ≥5 assistant turns. A handed-over
  session (no recorded log) is ranked but takes NO paid place.
- If the repo's GitHub owner is not the account's GitHub login, add
  `.makefun/owner.json` = `{"wallet": "<a wallet on the account>"}`.
- One entry per account (max_total 1). Deadline 2026-11-15T08:00:00Z.
- Final grading: 12 cases from the deadline to +48h; results due by
  2026-12-01T15:00:00Z. A prize needs a score strictly below the house
  persistence baseline AND a top-100 rank.

## Input format (verified from the official kit, not assumed)

`/input/<id>.in` is JSON:
`{"at", "case", "competition", "horizon_minutes": 240,
"markets": [{"id": "btc-usdc", "prices": [4320 closes]}]}` — last price
is the close at the checkpoint. The price is the cbBTC/USDC Orca
Whirlpool quote on Solana (not Binance, not an index); answers are the
same pool's close at `at` + 240 min.
