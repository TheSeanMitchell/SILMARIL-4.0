# SILMARIL 4.0 — THE LADDER — THE REGISTRATION

registration-hash: 566c8a43a3fb4b71

Frozen on 8 November 2026, before the first forward close. `ladder/config.py` holds the same
rules as numbers; `scripts/test_ladder.py` fails if the two ever disagree. Changing a number
is a re-registration: a new hash, written here, on purpose.

## Registration history (all on 8 Nov 2026, all before the epoch)

1. `d6ebfac647c082b8` — first registration under the working name "SILMARIL 9", monthly
   decisions. The history replay was run once with these rules, untuned.
2. `e6a469bdd537a239` — renamed SILMARIL 4.0. Name and version only; every trading number
   identical.
3. **`566c8a43a3fb4b71` — weekly decisions (this one).** The operator asked whether deciding
   weekly would be more powerful. Before testing, a pass rule was written down
   (`CADENCE_TEST_RULE.md` in the audit folder): weekly would be adopted only if, for the
   Master over the same replay and after costs, its Sharpe ratio was higher, its worst
   drawdown no deeper, and it beat monthly in at least 5 of 8 calendar years. It passed all
   three (Sharpe 0.74 vs 0.63, worst drop −34.8% vs −40.9%, 6 of 8 years), and still won at
   double the registered costs. **This is an in-sample choice between two cadences and is
   disclosed as such.** Nothing else changed: lookbacks, costs, hysteresis and exits are the
   same.

## The ladder

| level | what it is | its do-nothing twin |
|---|---|---|
| **Sleeves** (16) | four per category: HOLD, TREND, MOMENTUM, VOLTARGET | HOLD *is* the twin |
| **Category accounts** (4) | crypto (BTC, ETH) · stocks (SPY, QQQ) · metals (GLD, SLV) · energy (XLE, USO). Each holds the average of its TREND, MOMENTUM and VOLTARGET sleeves | the category's HOLD sleeve |
| **Master** (1) | every week, holds the two category accounts whose own track records are rising fastest, half each, only while they beat T-bills | equal-weight hold of all 8 assets; SPY hold |

Idle money in every account sits in T-bills (BIL), so cash earns what cash really earns.

## The sleeves (decisions on the first trading day of each week, from the previous close)

* **HOLD** — 50/50 of the two assets on day one; never trades again.
* **TREND** — weekly. Each asset holds its half while its close is above its 200-day average; otherwise that half sits in T-bills. (Faber, 2007.)
* **MOMENTUM** — weekly. Holds the one asset with the best blended 1/3/6-month return, only if it beats T-bills over the same windows; a 1-point margin keeps the incumbent. Checked daily for a fast exit. (Moskowitz, Ooi and Pedersen, 2012; Antonacci, 2014.)
* **VOLTARGET** — weekly. The 50/50 basket, sized so its last-63-day volatility is about 15% a year, the rest in T-bills; resized only when the size moves by more than 10 points. (Moreira and Muir, 2017.)

## Execution

* Every decision for day D reads closes up to day D−1 only. Fills happen at the close of day D. All legs of a rebalance fill on the same day.
* Round-trip costs: crypto 0.8% (0.4% a side), ETFs 0.1%, T-bills free.
* Prices are adjusted closes (splits and dividends included) for holdings and benchmarks alike.
* Trades smaller than 1% of an account are skipped, except full exits.

## What is deliberately absent

* **No governor that can lock the system out forever.** Risk control lives inside the rules, which step aside and step back in by themselves.
* **No resets.** The epoch is 9 November 2026. The system is rebuilt from prices on every run, so a missed run, failed push or crashed runner loses nothing.
* **No hidden state.** Each day's values are written to an append-only record; any later recomputation that disagrees by more than a cent is shown in red as DRIFT.

## The verdict, stated before the data

* Horizon: 104 weeks from the epoch. Progress shown every 13 weeks; no verdict is read before week 104.
* **Pass:** the master beats the equal-weight hold of all 8 assets after costs, with a smaller worst drawdown.
* Expectation from the replay (May 2019 to November 2026, weekly): the master grew about 19.5% a year with a worst drop of about −35% (537 trades, $1,879 fees on a $10,000 start). Equal-weight holding grew about 22% a year with a worst drop of about −61%. SPY grew about 15% a year with a worst drop of about −34%. **In the replay the rules bought a much smaller fall than holding everything, for somewhat less money.** The forward test asks whether that holds.
* P($1,000 a month on $10,000): about zero. No rule here pursues it.

## Where the earlier versions live

SILMARIL 1.0 to 3.0 (the 7.x engine and Steward 8.0, April to November 2026) stay frozen in
the repository **TheSeanMitchell/SILMARIL-2.0**, with their pages at
<https://theseanmitchell.github.io/SILMARIL-2.0/>.
