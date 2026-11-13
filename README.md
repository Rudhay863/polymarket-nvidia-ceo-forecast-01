# polymarket-nvidia-ceo-forecast-01

Forecast for make.fun competition `polymarket-nvidia-ceo-forecast-01`:
Polymarket's next NVIDIA CEO market prices, minute by minute, 4 hours ahead.

## Model (`main.py`, Python 3.13, stdlib only, deterministic)

Per market, adaptive to that market's own 72h history:

- **Median = last observed price.** Prices are step functions; a flat EMA
  median and any pullback toward an EMA both scored worse in backtests.
- **Scale = winsorised RMS of 1-minute price changes** (99th-percentile
  cap, robust to the huge one-off steps in the history): geometric mean of
  a 6h and a 24h window, boosted to the 1h window value when the last hour
  was jumpy (volatility clustering after jumps). Clamped to [0.001, 0.02].
- **Horizon scaling is strongly sublinear** (prices are bounded and
  mean-reverting): sigma(h) = sigma1 * h**0.25.
- **Quantiles are asymmetric:** z = [-1.6, -0.67449, 0, +0.67449, +2.2].
  The upside tail is wider than the downside tail because prices are
  bounded below by 0 (most markets sit near 0, so the downside is naturally
  limited) while jumps up have room.

## Backtest (practice cases, scored locally)

| model | mean pinball loss (p00-p04) |
|---|---|
| house baseline (sigma 0.0025 * sqrt(h)) | 0.3925 |
| this model | **0.3069** (-21.8%) |

The house baseline scores 0.363589 on the full 6-case practice set.
p05 is excluded from the local score: its answers are not reconstructable
from the kit (the live CLOB history API no longer reproduces the house
grids for that window); p00-p04 answers come from the next case's file
and are exact.

## Usage

```sh
python3 main.py   # reads /input/<id>.in, writes /output/<id>.out
```

Runs in ~0.1s per case, deterministic (two runs byte-identical), output
~277 KB (< 1 MiB). Verified from this repository: `python3 main.py` on
each kit practice case reproduces the 0.3069 loss above.

## Referral

Built for the make.fun bounty — if you join, use this link:
https://make.fun/r/xk7vph3j
