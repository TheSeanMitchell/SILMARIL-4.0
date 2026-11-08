"""ladder.engine — build the whole ladder from prices, every run, from scratch.

There is no hidden state. The sleeves, the four category accounts, the master and every
benchmark are recomputed from the price history and the registered rules each day, so a
missed run, a failed push or a crashed runner cannot lose or corrupt anything: the next
run produces exactly the same past and adds the new day. What is recorded is checked
against what is recomputed (see cli.py), so a silent change to the past is impossible.

Two money paths follow the SAME decisions:
  * the REPLAY starts when enough history exists (late 2018) — context, never proof;
  * the LIVE run opens every account with $10,000 at the epoch close — the experiment.

Besides the summary, build() returns the COCKPIT: every fill with the reason that caused
it, every round trip as a case file, the decisions in the rules' own words, and the
signals each rule is looking at — everything the page shows, nothing it has to guess.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from . import portfolio as PF
from . import rules as RU
from .config import REGISTERED, registration_hash
from .data import Tape

CATS = list(REGISTERED["categories"].keys())


def _index_on_or_after(tape: Tape, date: str) -> Optional[int]:
    for i, d in enumerate(tape.dates):
        if d >= date:
            return i
    return None


def _thin(curve: List[Optional[float]], tape: Tape, start: int, end: int, step: int) -> List:
    out = []
    for j in range(start, end + 1):
        if curve[j] is None:
            continue
        if (j - start) % step == 0 or j == end:
            out.append([tape.dates[j], round(curve[j], 2)])
    return out


def _ratio(tape: Tape, sym: str, a: int, b: int) -> Optional[float]:
    if a < 0 or b >= tape.n or a == b:
        return None
    pa, pb = tape.px[sym][a], tape.px[sym][b]
    if not pa or not pb:
        return None
    return round(100 * (pb / pa - 1.0), 2)


def _case_files(tape: Tape, sim: Dict, mode: str, level: str, sink_trades: List, sink_eps: List) -> None:
    """Turn a simulation's fills and round trips into case-file records for the cockpit.
    Each fill also gets n21: what its asset did over the next 21 closes (hindsight, for
    forensics only) - a sell before a fall and a buy before a rise were good calls."""
    idx = {d: i for i, d in enumerate(tape.dates)}
    for t in sim["trades"]:
        j = idx[t["date"]]
        sink_trades.append({"m": mode, "lv": level, "b": t["book"], "d": t["date"], "s": t["side"],
                            "y": t["sym"], "u": t["usd"], "f": t["fee"], "p": t["px"],
                            "w": t["why"], "e": mode + ":" + t["ep"],
                            "n21": _ratio(tape, t["sym"], j, j + 21)})
    last = tape.n - 1
    for ep in sim["episodes"]:
        o = ep["open_j"]
        c = ep.get("close_j", last)
        seg = [tape.px[ep["sym"]][k] for k in range(o, c + 1) if tape.px[ep["sym"]][k]]
        e0 = tape.px[ep["sym"]][o]
        sink_eps.append({
            "id": mode + ":" + ep["id"], "m": mode, "lv": level, "b": ep["book"], "y": ep["sym"],
            "st": ep["status"], "od": ep["open_date"], "cd": ep.get("close_date"),
            "ep": ep["entry_px"], "xp": ep.get("exit_px"), "ew": ep["entry_why"], "xw": ep.get("exit_why", ""),
            "in": ep["bought"], "out": ep["sold"], "now": ep.get("value_now"), "fees": ep["fees"],
            "fills": ep["fills"], "pnl": ep["pnl"], "pct": ep["pct"], "days": c - o,
            # the asset itself around the trade (hindsight forensics, never used to decide)
            "before21": _ratio(tape, ep["sym"], o - 21, o),
            "during": _ratio(tape, ep["sym"], o, c),
            "after21": _ratio(tape, ep["sym"], c, c + 21) if ep["status"] == "closed" else None,
            "best": round(100 * (max(seg) / e0 - 1.0), 2) if seg and e0 else None,
            "worst": round(100 * (min(seg) / e0 - 1.0), 2) if seg and e0 else None,
        })


def build(tape: Tape) -> Dict:
    warm = REGISTERED["warmup_bars"]
    w = tape.first_full_index(warm)
    if w is None or w + 2 >= tape.n:
        raise RuntimeError("not enough history for the registered warmup")
    start = w + 1
    epoch = _index_on_or_after(tape, REGISTERED["epoch_date"])
    last = tape.n - 1
    pre_end = (epoch - 1) if epoch is not None else last

    out: Dict = {"registration_hash": registration_hash(), "data_through": tape.dates[-1],
                 "replay_start": tape.dates[start],
                 "epoch_date": REGISTERED["epoch_date"],
                 "cadence": REGISTERED.get("rebalance", "monthly"),
                 "epoch_reached": epoch is not None,
                 "categories": {}, "master": {}, "benchmarks": {}}
    cock = {"trades": [], "episodes": [], "decisions": [], "curves": {}, "signals": {}}

    acct_tracks: Dict[str, List] = {}
    acct_curves: Dict[str, List] = {}
    acct_events: Dict[str, Dict[int, str]] = {}
    forward_values: Dict[str, Dict[str, float]] = {}

    def fwd_record(name: str, curve: List[Optional[float]]) -> None:
        if epoch is None:
            return
        for j in range(epoch, tape.n):
            if curve[j] is not None:
                forward_values.setdefault(tape.dates[j], {})[name] = round(curve[j], 2)

    def both_paths(name: str, track: List, events: Dict[int, str], level: str, rep_start: int):
        rep = PF.simulate(tape, track, rep_start, label=name, events=events)
        _case_files(tape, rep, "replay", level, cock["trades"], cock["episodes"])
        fw = None
        if epoch is not None:
            fw = PF.simulate(tape, track, epoch, label=name, events=events)
            _case_files(tape, fw, "live", level, cock["trades"], cock["episodes"])
        return rep, fw

    for cat in CATS:
        c: Dict = {"assets": REGISTERED["categories"][cat], "sleeves": {}}
        tracks, sev = {}, {}
        for name, fn in RU.SLEEVES.items():
            tr, ev = fn(tape, cat, start)
            tracks[name], sev[name] = tr, ev
            rep, fw = both_paths("%s:%s" % (cat, name), tr, ev, "sleeve", start)
            s = {"replay": PF.stats(rep["curve"], tape, start, pre_end),
                 "replay_trades": sum(1 for t in rep["trades"] if t["date"] <= tape.dates[pre_end]),
                 "replay_fees": round(sum(t["fee"] for t in rep["trades"]
                                          if t["date"] <= tape.dates[pre_end]), 2),
                 "avg_invested_pct": round(100 * rep["avg_invested"], 1),
                 "target_now": tr[last], "recent_events": [
                     {"date": tape.dates[j], "why": ev[j]} for j in sorted(ev)[-6:]]}
            if fw is not None:
                s["forward"] = PF.stats(fw["curve"], tape, epoch, last)
                s["forward_value"] = round(fw["curve"][last], 2)
                fwd_record("%s:%s" % (cat, name), fw["curve"])
            c["sleeves"][name] = s
        at, aev = RU.account_track(tracks, start, tape.n)
        # an account trade's reason = the sleeve decisions behind it, in their own words
        merged = {}
        for j in sorted(set(aev) | {k for n in RU.WORKING for k in sev[n]}):
            parts = ["%s: %s" % (n, sev[n][j]) for n in RU.WORKING if j in sev[n]]
            merged[j] = "; ".join(parts) or aev.get(j, "")
        acct_events[cat] = merged
        acct_tracks[cat] = at
        rep, fw = both_paths("%s:ACCOUNT" % cat, at, merged, "account", start)
        acct_curves[cat] = rep["curve"]
        hold_rep = PF.simulate(tape, tracks["HOLD"], start, label="%s:HOLD" % cat)
        acc = {"replay": PF.stats(rep["curve"], tape, start, pre_end),
               "replay_trades": sum(1 for t in rep["trades"] if t["date"] <= tape.dates[pre_end]),
               "replay_fees": round(sum(t["fee"] for t in rep["trades"]
                                        if t["date"] <= tape.dates[pre_end]), 2),
               "target_now": at[last],
               "recent_events": [{"date": tape.dates[j], "why": aev[j]} for j in sorted(aev)[-8:]],
               "replay_curve": _thin(rep["curve"], tape, start, pre_end, 5),
               "hold_curve": _thin(hold_rep["curve"], tape, start, pre_end, 5)}
        if fw is not None:
            fh = PF.simulate(tape, tracks["HOLD"], epoch, label="%s:HOLD" % cat)
            acc.update({"forward": PF.stats(fw["curve"], tape, epoch, last),
                        "forward_value": round(fw["curve"][last], 2),
                        "forward_hold_value": round(fh["curve"][last], 2),
                        "forward_trades": fw["trades"], "forward_holdings": fw["holdings"],
                        "forward_cash": fw["cash"],
                        "forward_curve": _thin(fw["curve"], tape, epoch, last, 1),
                        "forward_hold_curve": _thin(fh["curve"], tape, epoch, last, 1)})
            fwd_record("%s:ACCOUNT" % cat, fw["curve"])
        c["account"] = acc
        for j in sorted(merged):
            cock["decisions"].append({"d": tape.dates[j], "who": "%s account" % cat, "why": merged[j]})
        cash = REGISTERED["cash_symbol"]
        c["watch"] = {"tbills_score": RU.blended(tape.px[cash], last),
                      "scores": {s: RU.blended(tape.px[s], last) for s in c["assets"]},
                      "above_200d": {s: (tape.px[s][last] > (RU.sma(tape.px[s], last, 200) or 9e18))
                                     for s in c["assets"]},
                      "basket_vol": RU.basket_vol(tape.px[c["assets"][0]], tape.px[c["assets"][1]],
                                                  last, REGISTERED["vol_window"])}
        out["categories"][cat] = c

    # ── the master ────────────────────────────────────────────────────────────────
    ms = start + max(REGISTERED["momentum_lookbacks"]) + 2
    mt, mev, score_log, seats = RU.master_track(tape, acct_curves, acct_tracks, ms)
    mwhy = {}
    for j in range(ms, tape.n):
        parts = [mev[j]] if j in mev else []
        for cat in (seats[j] or []):
            if j in acct_events[cat] and (j - 1 < ms or (seats[j - 1] and cat in seats[j - 1])):
                parts.append("%s account: %s" % (cat, acct_events[cat][j]))
        if parts:
            mwhy[j] = " | ".join(parts)
    rep, fw = both_paths("MASTER", mt, mwhy, "master", ms)
    for j in sorted(mev):
        cock["decisions"].append({"d": tape.dates[j], "who": "Master", "why": mev[j]})
    ew = {s: 1.0 / 8 for cat in CATS for s in REGISTERED["categories"][cat]}
    ew_track = [None] * ms + [dict(ew)] * (tape.n - ms)
    spy_track = [None] * ms + [{"SPY": 1.0}] * (tape.n - ms)
    ew_rep = PF.simulate(tape, ew_track, ms, label="EQUAL-WEIGHT HOLD")
    spy_rep = PF.simulate(tape, spy_track, ms, label="SPY HOLD")
    m = {"replay_start": tape.dates[ms],
         "replay": PF.stats(rep["curve"], tape, ms, pre_end),
         "replay_trades": sum(1 for t in rep["trades"] if t["date"] <= tape.dates[pre_end]),
         "replay_fees": round(sum(t["fee"] for t in rep["trades"] if t["date"] <= tape.dates[pre_end]), 2),
         "avg_invested_pct": round(100 * rep["avg_invested"], 1),
         "target_now": mt[last],
         "seats_now": score_log[-1]["seats"] if score_log else [],
         "score_log_tail": score_log[-6:],
         "recent_events": [{"date": tape.dates[j], "why": mev[j]} for j in sorted(mev)[-10:]],
         "replay_curve": _thin(rep["curve"], tape, ms, pre_end, 5),
         "watch": {"tbills_score": RU.blended(tape.px[REGISTERED["cash_symbol"]], last),
                   "scores": {cat: RU.blended(acct_curves[cat], last) for cat in CATS}}}
    years = {}
    for j in range(ms, pre_end + 1):
        y = tape.dates[j][:4]
        years.setdefault(y, [j, j])[1] = j
    yt = []
    for y, (a, b) in sorted(years.items()):
        a0 = a - 1 if a > ms else a
        row = {"year": y}
        for key, cv in (("master", rep["curve"]), ("equal_weight", ew_rep["curve"]),
                        ("spy", spy_rep["curve"])):
            row[key] = round(100 * (cv[b] / cv[a0] - 1.0), 1)
        yt.append(row)
    m["replay_years"] = yt
    out["benchmarks"] = {
        "equal_weight_hold": {"replay": PF.stats(ew_rep["curve"], tape, ms, pre_end),
                              "replay_curve": _thin(ew_rep["curve"], tape, ms, pre_end, 5)},
        "spy_hold": {"replay": PF.stats(spy_rep["curve"], tape, ms, pre_end),
                     "replay_curve": _thin(spy_rep["curve"], tape, ms, pre_end, 5)}}
    if fw is not None:
        few = PF.simulate(tape, [None] * epoch + [dict(ew)] * (tape.n - epoch), epoch,
                          label="EQUAL-WEIGHT HOLD")
        fspy = PF.simulate(tape, [None] * epoch + [{"SPY": 1.0}] * (tape.n - epoch), epoch,
                           label="SPY HOLD")
        m.update({"forward": PF.stats(fw["curve"], tape, epoch, last),
                  "forward_value": round(fw["curve"][last], 2),
                  "forward_trades": fw["trades"], "forward_holdings": fw["holdings"],
                  "forward_cash": fw["cash"],
                  "forward_curve": _thin(fw["curve"], tape, epoch, last, 1)})
        out["benchmarks"]["equal_weight_hold"].update({
            "forward": PF.stats(few["curve"], tape, epoch, last),
            "forward_value": round(few["curve"][last], 2),
            "forward_curve": _thin(few["curve"], tape, epoch, last, 1)})
        out["benchmarks"]["spy_hold"].update({
            "forward": PF.stats(fspy["curve"], tape, epoch, last),
            "forward_value": round(fspy["curve"][last], 2),
            "forward_curve": _thin(fspy["curve"], tape, epoch, last, 1)})
        fwd_record("MASTER", fw["curve"])
        fwd_record("EQUAL-WEIGHT HOLD", few["curve"])
        fwd_record("SPY HOLD", fspy["curve"])
    out["master"] = m
    out["forward_values"] = forward_values

    # ── signals: what each rule is looking at, last two years, per asset ──────────
    cash = REGISTERED["cash_symbol"]
    s0 = max(0, tape.n - 504)
    for cat in CATS:
        for sym in REGISTERED["categories"][cat]:
            px = tape.px[sym]
            cock["signals"][sym] = {
                "cat": cat,
                "dates": tape.dates[s0:],
                "close": [round(v, 4) if v else None for v in px[s0:]],
                "sma200": [round(x, 4) if x else None for x in (RU.sma(px, j, 200) for j in range(s0, tape.n))],
                "mom": [round(100 * x, 2) if x is not None else None for x in (RU.blended(px, j) for j in range(s0, tape.n))],
            }
    cock["signals"]["_tbills_mom"] = [round(100 * x, 2) if x is not None else None
                                      for x in (RU.blended(tape.px[cash], j) for j in range(s0, tape.n))]
    cock["signals"]["_master"] = {
        "dates": tape.dates[max(ms, s0):],
        "scores": {cat: [round(100 * x, 2) if x is not None else None for x in
                         (RU.blended(acct_curves[cat], j) for j in range(max(ms, s0), tape.n))] for cat in CATS},
        "tbills": [round(100 * x, 2) if x is not None else None for x in
                   (RU.blended(tape.px[cash], j) for j in range(max(ms, s0), tape.n))],
        "seats": [seats[j] for j in range(max(ms, s0), tape.n)]}
    cock["decisions"].sort(key=lambda x: x["d"], reverse=True)
    cock["curves"] = {
        "replay": {"master": m["replay_curve"], "ew": out["benchmarks"]["equal_weight_hold"]["replay_curve"],
                   "spy": out["benchmarks"]["spy_hold"]["replay_curve"]},
        "live": {"master": m.get("forward_curve", []),
                 "ew": out["benchmarks"]["equal_weight_hold"].get("forward_curve", []),
                 "spy": out["benchmarks"]["spy_hold"].get("forward_curve", [])},
        "accounts": {cat: {"replay": out["categories"][cat]["account"]["replay_curve"],
                           "hold": out["categories"][cat]["account"]["hold_curve"],
                           "live": out["categories"][cat]["account"].get("forward_curve", []),
                           "live_hold": out["categories"][cat]["account"].get("forward_hold_curve", [])}
                     for cat in CATS}}
    out["cockpit"] = cock
    return out
