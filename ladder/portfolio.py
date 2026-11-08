"""ladder.portfolio — turn a target track into money, honestly.

One function, used by every sleeve, account, master and benchmark alike:

  * Holdings are DOLLARS per symbol. Between closes each holding grows by the ratio of its
    two adjusted closes; idle cash grows by the T-bill ETF's ratio. No other source of
    money exists.
  * The portfolio trades only when its target changes (plus day one). It then brings every
    symbol to target at that day's close: sells first, then buys, all on the same date.
  * Every traded dollar pays half its symbol's round trip. Buys are scaled down if cash
    (after fees) cannot cover them, so cash can never go negative.
  * A trade smaller than min_trade_frac of the account is skipped (a real broker minimum),
    except a full exit, which always executes.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .config import REGISTERED, round_trip
from .data import Tape


def simulate(tape: Tape, track: List[Optional[Dict[str, float]]], start: int,
             label: str = "", seed: Optional[float] = None,
             events: Optional[Dict[int, str]] = None) -> Dict:
    """...and every fill carries the reason that caused it (events[j]) and the id of the
    ROUND TRIP it belongs to: a round trip opens when a symbol goes from not held to
    held and closes when it is fully sold. Adds and trims in between stay inside it."""
    seed = REGISTERED["start_cash"] if seed is None else seed
    cash_sym = REGISTERED["cash_symbol"]
    min_frac = REGISTERED["min_trade_frac"]
    hold: Dict[str, float] = {}
    cash = seed
    curve: List[Optional[float]] = [None] * tape.n
    trades: List[Dict] = []
    fees = 0.0
    invested_sum, invested_n = 0.0, 0
    last_tgt: Optional[Dict[str, float]] = None
    open_ep: Dict[str, Dict] = {}
    episodes: List[Dict] = []

    def record(j: int, side: str, s: str, usd: float, fee: float, closes: bool) -> None:
        why = (events or {}).get(j, "")
        px = round(tape.px[s][j], 6)
        ep = open_ep.get(s)
        if ep is None:
            ep = {"id": "%s|%s|%s" % (label, s, tape.dates[j]), "book": label, "sym": s,
                  "open_j": j, "open_date": tape.dates[j], "entry_px": px, "entry_why": why,
                  "bought": 0.0, "sold": 0.0, "fees": 0.0, "fills": 0}
            open_ep[s] = ep
        if side == "BUY":
            ep["bought"] += usd + fee
        else:
            ep["sold"] += usd - fee
        ep["fees"] += fee
        ep["fills"] += 1
        trades.append({"date": tape.dates[j], "side": side, "sym": s, "usd": round(usd, 2),
                       "fee": round(fee, 2), "px": px, "book": label, "why": why,
                       "ep": ep["id"]})
        if closes:
            ep.update(close_j=j, close_date=tape.dates[j], exit_px=px, exit_why=why,
                      status="closed")
            episodes.append(ep)
            del open_ep[s]

    for j in range(start, tape.n):
        if j > start:
            for s in list(hold):
                hold[s] *= tape.px[s][j] / tape.px[s][j - 1]
            cash *= tape.px[cash_sym][j] / tape.px[cash_sym][j - 1]
        tgt = track[j] or {}
        if j == start or tgt != last_tgt:
            eq = cash + sum(hold.values())
            # sells (and trims) first
            for s in sorted(set(hold) | set(tgt)):
                want = tgt.get(s, 0.0) * eq
                have = hold.get(s, 0.0)
                diff = want - have
                if diff >= 0:
                    continue
                full_exit = want <= 1e-9
                if not full_exit and -diff < min_frac * eq:
                    continue
                fee = -diff * round_trip(s) / 2.0
                hold[s] = have + diff
                if full_exit:
                    hold.pop(s, None)
                cash += -diff - fee
                fees += fee
                record(j, "SELL", s, -diff, fee, full_exit)
            # then buys, scaled to the cash actually available
            buys = {}
            for s in sorted(tgt):
                want = tgt[s] * eq
                diff = want - hold.get(s, 0.0)
                if diff > 0 and diff >= min_frac * eq:
                    buys[s] = diff
            need = sum(v * (1.0 + round_trip(s) / 2.0) for s, v in buys.items())
            scale = min(1.0, cash / need) if need > 0 else 1.0
            for s, v in buys.items():
                v *= scale
                fee = v * round_trip(s) / 2.0
                hold[s] = hold.get(s, 0.0) + v
                cash -= v + fee
                fees += fee
                record(j, "BUY", s, v, fee, False)
            cash = max(cash, 0.0)
            last_tgt = tgt
        eq = cash + sum(hold.values())
        curve[j] = eq
        invested_sum += (eq - cash) / eq if eq > 0 else 0.0
        invested_n += 1
    for s, ep in open_ep.items():
        ep.update(status="open", value_now=round(hold.get(s, 0.0), 2))
        episodes.append(ep)
    for ep in episodes:
        end_val = ep["sold"] + ep.get("value_now", 0.0)
        ep["pnl"] = round(end_val - ep["bought"], 2)
        ep["pct"] = round(100 * (end_val / ep["bought"] - 1.0), 2) if ep["bought"] else 0.0
        for k in ("bought", "sold", "fees"):
            ep[k] = round(ep[k], 2)
    return {"curve": curve, "trades": trades, "fees": fees, "start": start,
            "episodes": episodes,
            "holdings": {s: round(v, 2) for s, v in hold.items()}, "cash": round(cash, 2),
            "avg_invested": invested_sum / invested_n if invested_n else 0.0}


def stats(curve: List[Optional[float]], tape: Tape, start: int, end: Optional[int] = None) -> Dict:
    """Total return, CAGR, max drawdown, volatility, Sharpe vs T-bills, over [start, end]."""
    end = tape.n - 1 if end is None else end
    xs = [(j, curve[j]) for j in range(start, end + 1) if curve[j] is not None]
    if len(xs) < 2:
        return {"days": len(xs), "total_pct": 0.0}
    v0, v1 = xs[0][1], xs[-1][1]
    days = len(xs) - 1
    peak, mdd = v0, 0.0
    for _, v in xs:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1.0)
    cash_sym = REGISTERED["cash_symbol"]
    ex = []
    for (j0, a), (j1, b) in zip(xs, xs[1:]):
        rf = tape.px[cash_sym][j1] / tape.px[cash_sym][j0] - 1.0
        ex.append((b / a - 1.0) - rf)
    m = sum(ex) / len(ex)
    sd = (sum((r - m) ** 2 for r in ex) / (len(ex) - 1)) ** 0.5 if len(ex) > 1 else 0.0
    rets = [b / a - 1.0 for (_, a), (_, b) in zip(xs, xs[1:])]
    mr = sum(rets) / len(rets)
    vol = (sum((r - mr) ** 2 for r in rets) / (len(rets) - 1)) ** 0.5 if len(rets) > 1 else 0.0
    years = days / 252.0
    return {
        "from": tape.dates[xs[0][0]], "to": tape.dates[xs[-1][0]], "days": days,
        "start_value": round(v0, 2), "end_value": round(v1, 2),
        "total_pct": round(100 * (v1 / v0 - 1.0), 2),
        "cagr_pct": round(100 * ((v1 / v0) ** (1 / years) - 1.0), 2) if years >= 0.5 else None,
        "max_dd_pct": round(100 * mdd, 2),
        "vol_pct": round(100 * vol * 252 ** 0.5, 2),
        "sharpe": round(m / sd * 252 ** 0.5, 2) if sd > 0 and years >= 0.5 else None,
    }
