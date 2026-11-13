"""Independent replay of positions.csv through the documented cost model.

This is a *second* verification path: it does NOT import the strategy logic.
It reads the positions the strategy wrote, replays them bar by bar, and
recomputes every stat from scratch. If this disagrees with `strategy.py`,
something is wrong.

Cost model (same as strategy.py):
  - target[t] is executed at the open of bar t+1 (one-bar execution lag).
  - A held position is marked to the next bar's open; the final position
    closes at the last bar's close.
  - Every position change of |dpos| ETH pays 12 bps of fill notional
    (10 bps taker fee + 2 bps slippage).

Usage:
    python3 backtest.py [--bars bars.csv] [--positions positions.csv]
"""

import argparse
import csv
import os
import sys

FEE_BPS = 12.0
SIZE_ETH = 1.0


def load_bars(path):
    opens, closes = [], []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            opens.append(float(row["open"]))
            closes.append(float(row["close"]))
    return opens, closes


def load_positions(path):
    pos = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            pos[int(row["minute"])] = float(row["target_position"])
    n = max(pos) + 1
    return [pos.get(i, 0.0) for i in range(n)]


def main(argv=None):
    here = os.path.dirname(__file__)
    ap = argparse.ArgumentParser(description="Replay positions.csv through the cost model")
    ap.add_argument("--bars", default=os.path.join(here, "bars.csv"))
    ap.add_argument("--positions", default=os.path.join(here, "positions.csv"))
    ap.add_argument("--fee-bps", type=float, default=FEE_BPS)
    args = ap.parse_args(argv)

    opens, closes = load_bars(args.bars)
    target = load_positions(args.positions)
    n = len(closes)
    assert len(target) == n, f"positions ({len(target)}) != bars ({n})"

    # no-lookahead guard: a position held during bar i must have been
    # decided at or before bar i-1, i.e. target[i-1] == pos[i] for i >= 1.
    pos = [0.0] * n
    for t in range(n - 1):
        pos[t + 1] = target[t]

    pnl = [0.0] * n
    for i in range(n - 1):
        pnl[i] = pos[i] * SIZE_ETH * (opens[i + 1] - opens[i])
    pnl[n - 1] = pos[n - 1] * SIZE_ETH * (closes[n - 1] - opens[n - 1])

    cost = [0.0] * n
    prev = 0.0
    for i in range(n):
        d = abs(pos[i] - prev)
        if d:
            cost[i] = d * SIZE_ETH * opens[i] * args.fee_bps / 1e4
        prev = pos[i]
    cost[n - 1] += abs(pos[n - 1]) * SIZE_ETH * closes[n - 1] * args.fee_bps / 1e4

    net = [p - c for p, c in zip(pnl, cost)]
    eq, run = [], 0.0
    for v in net:
        run += v
        eq.append(run)
    trades = sum(1 for i in range(1, n) if pos[i] != pos[i - 1])
    peak, max_dd = 0.0, 0.0
    for v in [0.0] + eq:
        peak = max(peak, v)
        max_dd = min(max_dd, v - peak)
    held = [p for p, pp in zip(pnl, pos) if pp != 0]
    wins = sum(1 for v in held if v > 0)
    half = n // 2

    print("=== independent replay of positions.csv ===")
    print(f"bars: {n}  fee: {args.fee_bps:.0f} bps/fill  size: {SIZE_ETH:.0f} ETH")
    print(f"net PnL:        ${eq[-1]:.2f}")
    print(f"gross PnL:      ${sum(pnl):.2f}")
    print(f"costs:          ${sum(cost):.2f}")
    print(f"trades:         {trades}")
    print(f"max drawdown:   ${max_dd:.2f}")
    print(f"win rate (held bars): {wins / max(len(held), 1):.1%}")
    print(f"first half:     ${sum(net[:half]):.2f}")
    print(f"second half:    ${sum(net[half:]):.2f}")
    print(f"final position: {pos[-1]:+.0f} ETH")
    return 0


if __name__ == "__main__":
    sys.exit(main())
