#!/usr/bin/env python3
"""Forecast Polymarket 'next CEO of NVIDIA' market prices, 4 hours ahead.

Model (per market, adaptive, stdlib only, deterministic):
  * Median = last observed price (prices are step functions; a flat EMA
    median and any pullback toward an EMA both scored worse in backtests).
  * Scale = winsorised RMS of 1-minute price changes, estimated per market
    from its own history: geometric mean of a 6h and a 24h window, boosted
    to the 1h window value when the last hour was jumpy (volatility
    clustering after jumps). Clamped to [0.001, 0.02].
  * Horizon scaling is strongly sublinear (prices are bounded and
    mean-reverting): sigma(h) = sigma1 * h**0.25.
  * Quantiles are asymmetric: z = [-1.6, -0.67449, 0, +0.67449, +2.2].
    The upside tail is wider than the downside tail because prices are
    bounded below by 0 (most markets sit near 0, so the downside is
    naturally limited) while jumps up have room.

Backtest on the 6 practice cases (p00-p04 scored exactly, p05 excluded:
its answers are not reconstructable from the kit): mean pinball loss
0.3069 vs the house baseline's 0.3925 on the same cases (-21.8%).
The house baseline scores 0.363589 on the full practice set.
"""
import json
import math
import os
import sys

# Quantile z-scores (asymmetric tails, see module docstring).
Z = (-1.6, -0.67449, 0.0, 0.67449, 2.2)
ALPHA = 0.25          # horizon exponent: sigma(h) = sigma1 * h**ALPHA
SIGMA_FLOOR = 0.001
SIGMA_CAP = 0.02
WIN_SHORT = 360       # minutes, recent volatility window
WIN_LONG = 1440       # minutes, long volatility window
WIN_SPIKE = 60        # minutes, jump-boost window


def winsorised_rms(prices, window):
    """RMS of 1-minute changes over the last `window` minutes, with each
    squared change capped at the 99th percentile of |change| (robust to
    the huge one-off steps the history contains)."""
    p = prices[-window:] if len(prices) > window else prices
    if len(p) < 2:
        return 0.0
    diffs = [p[i + 1] - p[i] for i in range(len(p) - 1)]
    abs_sorted = sorted(abs(d) for d in diffs)
    cap = abs_sorted[min(len(abs_sorted) - 1, int(0.99 * len(abs_sorted)))]
    cap2 = cap * cap
    return math.sqrt(sum(min(d * d, cap2) for d in diffs) / len(diffs))


def sigma1(prices):
    """Per-market 1-minute scale."""
    short = winsorised_rms(prices, WIN_SHORT)
    long_ = winsorised_rms(prices, WIN_LONG)
    s = math.sqrt(max(short, 1e-12) * max(long_, 1e-12))
    spike = winsorised_rms(prices, WIN_SPIKE)
    if spike > s:
        s = spike
    return min(SIGMA_CAP, max(SIGMA_FLOOR, s))


def forecast_market(prices):
    """Return 240 rows of 5 quantiles for one market."""
    x = prices[-1] if prices else 0.5
    s1 = sigma1(prices) if prices else 0.0025
    rows = []
    for h in range(1, 241):
        s = s1 * (h ** ALPHA)
        row = []
        for z in Z:
            v = x + z * s
            if v < 0.0:
                v = 0.0
            elif v > 1.0:
                v = 1.0
            row.append(round(v, 6))
        # enforce non-decreasing (clamping at 0/1 can only tie, never invert,
        # but keep the guarantee explicit)
        for k in range(1, 5):
            if row[k] < row[k - 1]:
                row[k] = row[k - 1]
        rows.append(row)
    return rows


def main():
    in_dir = os.environ.get("INPUT_DIR", "/input")
    out_dir = os.environ.get("OUTPUT_DIR", "/output")
    # The case file is /input/<id>.in ; the id is the file stem.
    names = sorted(n for n in os.listdir(in_dir) if n.endswith(".in"))
    if not names:
        raise SystemExit("no .in file found in %s" % in_dir)
    in_path = os.path.join(in_dir, names[0])
    case_id = names[0][:-3]
    with open(in_path, "r") as f:
        case = json.load(f)
    forecasts = []
    for m in case["markets"]:
        prices = m.get("prices") or []
        forecasts.append({"id": m["id"], "q": forecast_market(prices)})
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, case_id + ".out")
    with open(out_path, "w") as f:
        json.dump({"forecasts": forecasts}, f)
    print("wrote %s (%d markets)" % (out_path, len(forecasts)))


if __name__ == "__main__":
    main()
