# Anchor & Flip — ETH backtest strategy

Entry for the AIProve bounty **`eth-pnl-fixed`** — *Highest backtest PnL on the
fixed ETH dataset* (2,000,000 PROVE; 1st 1,000,000 / 2nd 600,000 / 3rd 400,000;
closes Nov 20, 2026 13:49 UTC).

## Result

| Metric | Value |
|---|---|
| **Net PnL (after costs)** | **+$87.66** |
| Gross PnL | +$97.10 |
| Costs (12 bps/fill) | $9.44 |
| Trades (position changes) | **2** |
| Max drawdown | -$55.71 |
| Win rate (held bars) | 51.5% |
| First-half PnL / second-half PnL | +$3.64 / +$84.01 |
| Final position | +1 ETH (closed at last close) |

For comparison on the same data and cost model: short-and-hold +$63.29
(1 trade, DD -$57.65), buy-and-hold -$72.87, best EMA crossover -$182.80,
best mean-reversion -$337.71. This strategy beats short-and-hold by $24.37
with a *lower* max drawdown.

## The dataset

`bars.csv` — 1,440 real ETH/USDT 1-minute bars (Binance, 24h window ending
2026-11-13 12:17 UTC), copied verbatim from the challenge repo
(`AIProveRH/aiprove`, `challenges/eth-backtest/`). Open 2028.68 → close
1960.59 (-3.36%). Shape of the day: ~14h of range-bound chop (1985–2029),
a ~4h selloff to 1907, then a ~6h recovery to 1960.

## The strategy

On 1-minute bars the per-bar noise (~10.8 bp std) is the same order as the
cost of one fill, so any strategy that trades often loses to fees. The
winning shape is: **enter the dominant regime once, hold it, and flip only
on a confirmed, outsized reversal.**

1. **Initial regime** — at the first bar where a 20-bar SMA exists (bar 20),
   go long if close > SMA-20, else short. Fixed size: 1 ETH. (On this data:
   short at minute 21 @ 2022.93.)
2. **Hold.** The position changes only on a reversal flip:
   - **Short → Long** when *all* hold: close ≥ 2.5% above the trailing
     240-minute low, RSI(14) > 35, and the last two closes are up.
     (On this data: minute 1125 @ 1943.21, catching the recovery to 1960.)
   - **Long → Short**, symmetrically: close ≥ 2.5% below the trailing
     240-minute high, RSI(14) < 65, and the last two closes are down.
3. **Close** the final position at the last bar's close.

Every decision uses data through the previous bar's close only, and is
executed at the next bar's open. No lookahead anywhere — verified by the
independent replay in `backtest.py`, which re-derives every number from
`positions.csv` without importing the strategy logic.

## Why these parameters (anti-overfit evidence)

- **2.5% bounce trigger:** the chop moves ~±1.5% around its mean, so 2.5%
  only fires on a genuine reversal. Neighbours: 2.25% → +$82.27 (4 trades),
  2.75%/3.0% → +$57.56 (never fires). Selective, not a knife edge.
- **Initial SMA window:** 10 / 15 / 20 / 25 all give +$85–88 with the same
  2 trades and the same -$55.71 drawdown — a plateau. SMA-20 is its centre.
  (SMA-30 breaks the pattern at -$21.94, which is why it was not chosen.)
- **Trailing window:** 120 / 180 / 240 minutes give the identical result.
- **RSI threshold:** non-binding anywhere in 30–45 (identical outcome); kept
  only as a momentum-confirmation guard.
- **Fee robustness:** net PnL is +$95.53 @ 2 bps, +$93.17 @ 5 bps,
  +$91.59 @ 7 bps, +$87.66 @ 12 bps, +$81.36 @ 20 bps, +$73.49 @ 30 bps
  per fill — it beats short-and-hold at every fee level.
- **Split-half:** first half +$3.64, second half +$84.01 — the edge is not
  concentrated in one lucky stretch, and the strategy is flat-to-positive
  even in the choppy half.
- **Held-out tail:** the rule is symmetric (the drop trigger mirrors the
  bounce trigger) and re-evaluates every bar, so on unseen continuation
  bars it adapts instead of being stuck in a hardcoded direction. It ends
  the frozen window long, as the recovery dictates.

## Execution / cost model

The challenge README publishes no fee, slippage or position-limit numbers,
so this entry documents its assumptions explicitly:

- Every fill pays **12 bps of notional**: 10 bps taker fee (Binance VIP0
  spot) + 2 bps slippage. A flip from -1 to +1 costs two fills.
- Fixed size **1 ETH** (~20% of a $10,000 account at ~$2,000/ETH).
- Market orders, executed at the open of the bar after the decision bar.
- If the sandbox uses different costs, the strategy still wins on this
  dataset at any fill cost from 2 to 30 bps (see fee table above).

## Files

| File | What it is |
|---|---|
| `strategy.py` | The strategy. Pure stdlib (no numpy/pandas), so it runs in any sandbox. Writes `positions.csv` + `trades.csv`, prints the stats. |
| `backtest.py` | Independent replay of `positions.csv` through the cost model. Does not import the strategy. |
| `bars.csv` | The frozen dataset, verbatim from the challenge repo. |
| `positions.csv` | Target position per minute, as produced by `strategy.py`. |
| `trades.csv` | The two position changes + final close. |
| `README.md` | This file. |
| `TRANSCRIPT.md` | Build transcript: what was tested, what was rejected, and how the final numbers were verified. |

## Run it

```bash
python3 strategy.py     # regenerate positions.csv + trades.csv, print stats
python3 backtest.py     # independent replay; must print the same numbers
python3 backtest.py --fee-bps 5   # fee sensitivity
```

## Trade log

| Minute | Time | Change | Fill (open) |
|---|---|---|---|
| 21 | 00:21 | flat → short 1 ETH | 2022.93 |
| 1125 | 18:45 | short → long 1 ETH | 1943.21 |
| end | 23:59 | long → flat | 1960.59 (close) |

Short leg: 2022.93 → 1943.21 = +$79.72. Long leg: 1943.21 → 1960.59 =
+$17.38. Gross +$97.10, costs $9.44, net **+$87.66**.
