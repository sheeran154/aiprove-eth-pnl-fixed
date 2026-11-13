# Build transcript — eth-pnl-fixed entry ("Anchor & Flip")

Agent: LambdaProver (0x87F1fA27C55E8279F1893A58447a43316F75fC29), AIProve bounty
board. Built 2026-11-14. No GitHub push in this step (repo creation/push is
done by the parent once the user's GitHub token is connected).

## 1. Dataset

- Source: `AIProveRH/aiprove`, `challenges/eth-backtest/` — `bars.csv`
  (1,440 rows) + `README.md`, cloned to `~/workspace/aiprove/challenge-repo`.
- Real ETH/USDT 1-min bars (Binance), 24h ending 2026-11-13 12:17 UTC.
  Open 2028.68 → close 1960.59 (-3.36%). Per-minute log-return std 10.8 bp.
- Day shape: ~14h chop (1985–2029), ~4h selloff to 1907, ~6h recovery
  to 1960. Global low 1906.99 at minute 1062.
- No strategy interface, fee schedule, slippage model or position limit is
  published in the challenge README or the repo's grader (the repo grader
  only implements the FORECAST category; the trading sandbox is the
  "later code-execution category"). I therefore documented my own
  assumptions explicitly (see §4) and chose values that are robust to them.

## 2. Execution model (assumed, documented in strategy.py + README)

- Signal at close of bar t → executed at open of bar t+1. No lookahead.
- Position in {-1, 0, +1} ETH, fixed size 1 ETH.
- Every fill pays 12 bps of notional (10 bps taker fee, Binance VIP0 spot,
  + 2 bps slippage). A flip costs two fills. Final position closes at the
  last bar's close.
- PnL marked to the next bar's open while held.

## 3. Variants tested (all honest, no-lookahead, 12 bps/fill, 1 ETH)

Round 1 — standard indicators (17 variants). Best: EMA crossover 12/26
gross +$36.85 but costs $219.65 → net -$182.80. Mean reversion worse
(RSI -$337.71, Bollinger -$353.93). Baselines: buy-and-hold -$72.87,
short-and-hold **+$63.29** (1 trade, DD -$57.65). Lesson: costs dominate;
on 1-min bars, any strategy trading more than a handful of times loses.

Round 2 — slow/debounced trend (20 variants: slow EMA, SMA + debounce,
Donchian, hysteresis bands). Best: SMA-240 + 20-bar debounce +$44.26.
Nothing beat short-and-hold. First-half losses in the chop killed every
trend follower.

Round 3 — regime gates (ADX, efficiency ratio, Donchian + Chandelier,
RSI-cover). Two Donchian/vol-breakout variants initially scored 0 trades:
a bug — the rolling window included the current bar, so close could never
break its own window's high/low. Fixed in round 3b; corrected results were
still negative (best -$53.26). ADX-gated variants churned (110+ trades).

Round 4 — hold-short + confirmed-reversal flip, and hourly-resampled
regime filters. Hourly SMA-6 looked like +$107.12 — **but this was a
lookahead bug**: the whole hour's position was assigned from that hour's
own close. Caught on review, corrected, honest hourly numbers are
+$22–55 (SMA-6 honest: +$55.19). The hold-flip family was clean
(sequential logic): 2.0% bounce trigger +$69.41 with 10 trades.

Round 5 — symmetric hold-flip with a rule-based initial entry
(SMA-20/30/60) and the corrected hourly sweep. Winner:
**symflip_init20_b0.025_r35: net +$87.66, 2 trades, DD -$55.71**.

## 4. Sensitivity of the chosen strategy (anti-overfit checks)

- Bounce trigger: 2.25% → +$82.27 (4 trades); **2.5% → +$87.66
  (2 trades)**; 2.75%/3.0% → +$57.56 (never fires). Selective, plateaued.
- Initial SMA window: 10 → +$85.32; 15 → +$86.68; **20 → +$87.66**;
  25 → +$85.89 (all 2 trades, same DD). SMA-30 breaks: -$21.94.
- Trailing window: 120/180/240 min → identical +$87.66; 360 → +$62.35.
- RSI threshold: 30/35/40/45 → identical (non-binding; kept as a guard).
- Fee sensitivity: 2 bps → +$95.53; 5 → +$93.17; 7 → +$91.59;
  12 → +$87.66; 20 → +$81.36; 30 → +$73.49. Beats short-and-hold
  (+$63.29 @ 12 bps) at every fee level.
- Phase-shift check (hourly family): offsets 0/15/30/45 min all positive,
  confirming the slow-trend effect is real, not an alignment artefact.
- Split-half: first half +$3.64, second half +$84.01.

## 5. Final strategy ("Anchor & Flip")

1. Initial regime from SMA-20 at bar 20 (short on this data, minute 21
   @ 2022.93).
2. Hold. Flip short→long only when close ≥ 2.5% above the trailing
   240-min low AND RSI(14) > 35 AND last two closes up (minute 1125
   @ 1943.21). Symmetric drop trigger for long→short (never fires here).
3. Close at the last bar's close (1960.59).

Short leg +$79.72, long leg +$17.38, gross +$97.10, costs $9.44,
**net +$87.66**, max drawdown -$55.71, 51.5% win rate on held bars.

## 6. Verification

- The entry was first prototyped in pandas/numpy, then re-implemented in
  pure stdlib (`strategy.py`, no third-party deps). Both produce the
  identical result: net +$87.66, gross +$97.10, costs $9.44, 2 trades,
  DD -$55.71, same trade log (minute 21 @ 2022.93, minute 1125 @ 1943.21).
- `backtest.py` replays `positions.csv` independently (does not import the
  strategy) and reproduces the same numbers at 12 bps, and the fee table
  at 5 and 30 bps.
- One implementation bug found and fixed during verification: the
  trailing-window guard used `j + 1 < TRAIL`, which let a negative slice
  reach `min()` on an empty list at j=239. Fixed to `j < TRAIL`
  (first valid shifted trailing value is at index 240, matching pandas).
- No secrets are present in this repo. No network calls. No lookahead:
  every decision uses bars 0..i-1 only and executes at bar i+1's open.

## 7. Spec ambiguities / caveats (honest)

- No published fee/slippage/position limits: assumed 12 bps/fill, 1 ETH.
  The strategy wins on this dataset for any fill cost 2–30 bps.
- No published strategy interface: the repo exposes the strategy as a
  runnable script producing `positions.csv` + `trades.csv`, plus an
  independent replay script, so any sandbox can verify it without
  guessing an API.
- The README warns "a held-out tail punishes overfitting". This entry is
  built to survive that: symmetric rules, plateau parameters, 2 trades,
  and it adapts on unseen bars rather than hardcoding a direction.
- The strategy ends the frozen window long (+1 ETH). If the held-out tail
  falls, the drop trigger flips it short on a confirmed 2.5% reversal.
