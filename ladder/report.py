"""ladder.report — the main page (docs/index.html), rebuilt every run.

Hierarchy of the page, top to bottom: is the data fresh and the record intact; what the
master holds and how it compares with simply holding; the four category accounts; the
sixteen sleeves; the history replay (labelled as context); the trade log; the rules.
Every money number is shown beside the do-nothing number it must beat.
"""
from __future__ import annotations

import html
import json
import math
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from .config import REGISTERED

CATS = list(REGISTERED["categories"].keys())
# where the frozen 7.x dashboard and Steward page live (the archive repository's site)
ARCHIVE_SITE = "https://theseanmitchell.github.io/SILMARIL-2.0/"
LABEL = {"crypto": "Crypto", "stock": "Stocks", "metal": "Metals", "energy": "Energy"}
SLEEVE_DESC = {
    "HOLD": "buy 50/50 on day one, never trade",
    "TREND": "each half only while above its 200-day average",
    "MOMENTUM": "the one stronger asset, only while it beats T-bills",
    "VOLTARGET": "50/50 sized to about 15% yearly volatility",
}

CSS = """
/* chart series use the validated categorical order: blue, orange, aqua, yellow */
:root{--bg:#f6f4ef;--card:#fffdf8;--ink:#1d2127;--dim:#68707b;--line:#e2ddd2;--pos:#1f7a52;--neg:#b5452f;
--gold:#9a6b12;--c1:#2a78d6;--c2:#eb6834;--c3:#1baf7a;--c4:#eda100;--grid:#e8e4da;--warnbg:#fbefd6;--badbg:#f7dfd8;--okbg:#dcefe4}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#101317;--card:#171b21;--ink:#e6e9ee;
--dim:#8f98a4;--line:#29303a;--pos:#6fc39a;--neg:#e58a76;--gold:#d8ad55;--c1:#3987e5;--c2:#d95926;--c3:#199e70;--c4:#c98500;
--grid:#232932;--warnbg:#2c2414;--badbg:#311c17;--okbg:#14291f;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#101317;--card:#171b21;--ink:#e6e9ee;--dim:#8f98a4;--line:#29303a;--pos:#6fc39a;
--neg:#e58a76;--gold:#d8ad55;--c1:#3987e5;--c2:#d95926;--c3:#199e70;--c4:#c98500;--grid:#232932;--warnbg:#2c2414;
--badbg:#311c17;--okbg:#14291f;color-scheme:dark}
nav.tabs{display:flex;flex-wrap:wrap;gap:2px;margin:16px 0 0;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--bg);z-index:5}
nav.tabs a{padding:9px 12px;text-decoration:none;color:var(--dim);border-bottom:2px solid transparent;font-weight:600;font-size:14px}
nav.tabs a[aria-current="page"]{color:var(--ink);border-bottom-color:var(--gold)}
nav.tabs a:focus-visible,.ctl :focus-visible,tr.click:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
.ctl{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0}
.ctl label{font-size:12px;color:var(--dim)}
.ctl select,.ctl input,.ctl button{font:inherit;font-size:13px;padding:6px 9px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink)}
.ctl button{cursor:pointer}.ctl button[aria-pressed="true"]{border-color:var(--gold);color:var(--gold);font-weight:600}
tr.click{cursor:pointer}tr.click:hover td{background:color-mix(in srgb,var(--gold) 9%,transparent)}
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.5);display:flex;align-items:flex-start;justify-content:center;padding:32px 16px;overflow:auto;z-index:30}
.modal{background:var(--card);border:1px solid var(--line);border-radius:10px;max-width:900px;width:100%;padding:18px 20px;min-width:0}
.modal h3{font-size:18px;margin-bottom:4px}.modal .x{float:right;font:inherit;background:none;border:1px solid var(--line);border-radius:6px;color:var(--ink);padding:4px 10px;cursor:pointer}
.chart{position:relative}.chart svg{display:block;width:100%;height:auto;overflow:visible}
.tip{position:absolute;pointer-events:none;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:6px 9px;font-size:12px;line-height:1.5;white-space:nowrap;box-shadow:0 2px 10px rgba(0,0,0,.15);z-index:3}
.good{color:var(--pos)}.badc{color:var(--neg)}
.small{font-size:12px}.mini{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;padding:24px 16px 72px}
.wrap{max-width:1080px;margin:0 auto}
h1{font-size:24px;letter-spacing:.02em}h1 small{color:var(--gold);font-size:13px;letter-spacing:.12em;margin-left:8px}
h2{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);margin:30px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}
p{margin:6px 0}.dim{color:var(--dim)}.pos{color:var(--pos)}.neg{color:var(--neg)}
.num{font-variant-numeric:tabular-nums}
.banner{border-radius:8px;padding:10px 14px;margin:14px 0;font-size:14px}
.ok{background:var(--okbg)}.warn{background:var(--warnbg)}.bad{background:var(--badbg)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.card h3{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);margin-bottom:6px}
.big{font-size:30px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.2}
.kv{display:flex;justify-content:space-between;gap:10px;font-size:13px;padding:3px 0;border-top:1px solid var(--line)}
.kv b{font-weight:600;font-variant-numeric:tabular-nums;text-align:right}
.tw{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:8px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{color:var(--dim);font-size:11px;letter-spacing:.08em;text-transform:uppercase;text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:6px 10px;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums;white-space:nowrap}
td.wrap{white-space:normal;min-width:220px}
.legend{font-size:12px;color:var(--dim);margin-top:6px}.legend i{display:inline-block;width:12px;height:3px;vertical-align:middle;margin:0 4px 0 10px}
svg text{fill:var(--dim);font-size:11px}
footer{margin-top:34px;color:var(--dim);font-size:12px;line-height:1.8;border-top:1px solid var(--line);padding-top:12px}
a{color:var(--c1)}
"""


def esc(x) -> str:
    return html.escape(str(x))


def money(v: Optional[float]) -> str:
    return "—" if v is None else "$" + format(round(v, 2), ",.2f")


def pct(v: Optional[float], plus: bool = True) -> str:
    if v is None:
        return "—"
    return ("%+.1f%%" if plus else "%.1f%%") % v


def cls(v: Optional[float]) -> str:
    return "" if v is None else ("pos" if v >= 0 else "neg")


def weights_text(w: Optional[Dict[str, float]]) -> str:
    if not w:
        return "all in T-bills (BIL)"
    parts = ["%s %.0f%%" % (s, 100 * v) for s, v in sorted(w.items(), key=lambda kv: -kv[1])]
    rest = 1.0 - sum(w.values())
    if rest > 0.005:
        parts.append("T-bills %.0f%%" % (100 * rest))
    return " · ".join(parts)


def chart(series: List[Dict], log: bool = False, height: int = 230) -> str:
    """series: [{"name", "color", "points": [[date, value], ...]}] -> inline SVG."""
    pts = [p for s in series for p in s["points"]]
    if len(pts) < 2:
        return '<p class="dim">Not enough points to draw yet.</p>'
    dates = sorted({p[0] for p in pts})
    di = {d: i for i, d in enumerate(dates)}
    f = (lambda v: math.log(v)) if log else (lambda v: v)
    vals = [f(p[1]) for p in pts if p[1] and p[1] > 0]
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-9:
        hi = lo + 1
    W, H, L, R, T, B = 1000, height, 58, 12, 10, 24
    def X(d):
        return L + (W - L - R) * di[d] / max(1, len(dates) - 1)
    def Y(v):
        return T + (H - T - B) * (1 - (f(v) - lo) / (hi - lo))
    out = ['<svg viewBox="0 0 %d %d" width="100%%" role="img" aria-label="equity chart">' % (W, H)]
    for k in range(5):
        fv = lo + (hi - lo) * k / 4
        v = math.exp(fv) if log else fv
        y = Y(v)
        out.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--line)"/>' % (L, W - R, y, y))
        out.append('<text x="%d" y="%.1f" text-anchor="end">%s</text>' % (L - 6, y + 4, "$" + format(round(v), ",")))
    step = max(1, len(dates) // 6)
    for i in range(0, len(dates), step):
        out.append('<text x="%.1f" y="%d" text-anchor="middle">%s</text>' % (X(dates[i]), H - 6, dates[i][:7]))
    for s in series:
        p = " ".join("%.1f,%.1f" % (X(d), Y(v)) for d, v in s["points"] if v and v > 0)
        out.append('<polyline fill="none" stroke="%s" stroke-width="%s" points="%s"/>' % (
            s["color"], s.get("width", 2), p))
    out.append("</svg>")
    leg = "".join('<i style="background:%s"></i>%s' % (s["color"], esc(s["name"])) for s in series)
    return "".join(out) + '<div class="legend">%s</div>' % leg


def _status(res: Dict) -> str:
    d = res.get("data", {})
    rec = res.get("record", {})
    bits = []
    if d.get("stale"):
        bits.append('<div class="banner bad"><b>STALE DATA.</b> The newest close is %s (%s days old). '
                    'No new decisions are made on a silent feed; they resume by themselves when '
                    'prices return.</div>' % (esc(d.get("newest_close")), esc(d.get("stale_days"))))
    if rec.get("drift_count"):
        bits.append('<div class="banner bad"><b>DRIFT: %d recorded values no longer match the '
                    'recomputation.</b> Either the code or the price history changed after the '
                    'fact. First case: %s</div>' % (rec["drift_count"], esc(json.dumps(rec["drift"][:1]))))
    if not bits:
        bits.append('<div class="banner ok">Data through <b>%s</b> (%s) · record intact: %d forward '
                    'days recorded, 0 drift · rules fingerprint <span class="num">%s</span></div>' % (
                        esc(res["data_through"]), esc(d.get("source", "")), rec.get("days_recorded", 0),
                        esc(res["registration_hash"])))
    return "".join(bits)


def _next_monthly(res: Dict) -> str:
    """The next scheduled decision day (weekly: the next Monday's close, or the first
    trading day of that week if Monday is a holiday)."""
    if REGISTERED.get("rebalance") == "weekly":
        from datetime import timedelta
        d = date.fromisoformat(res["data_through"])
        nxt = d + timedelta(days=7 - d.weekday())
        return "the first trading day of the week of %s" % nxt.strftime("%A %d %B %Y").replace(" 0", " ")
    y, m = int(res["data_through"][:4]), int(res["data_through"][5:7])
    y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return "first trading day of %s" % date(y, m, 1).strftime("%B %Y")


TABS = [("command", "Command"), ("trades", "Trades"), ("forensics", "Forensics"),
        ("signals", "Signals"), ("headlines", "Headlines"), ("health", "Health"), ("rules", "Rules")]


def _health(res: Dict, docs: Path) -> str:
    """Server-rendered health tab: freshness, the run log, drift, fingerprints, file sizes."""
    d, rec = res.get("data", {}), res.get("record", {})
    data = Path(docs) / "data"
    files = sorted(p for p in data.glob("ladder_*") if p.is_file())
    try:
        runs = [json.loads(l) for l in (data / "ladder_ledger.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    except Exception:
        runs = []
    from .headlines import rules_hash as _hh
    out = ['<div class="grid">',
           '<div class="card"><h3>Prices</h3><div class="kv"><span>newest close</span><b>%s</b></div>'
           '<div class="kv"><span>age</span><b>%s days%s</b></div><div class="kv"><span>source</span><b>%s</b></div>'
           '<div class="kv"><span>filled from the saved file</span><b>%s</b></div></div>' % (
               esc(d.get("newest_close")), esc(d.get("stale_days")), " (STALE)" if d.get("stale") else "",
               esc(d.get("source")), esc(", ".join(d.get("from_saved_file") or []) or "none")),
           '<div class="card"><h3>The record</h3><div class="kv"><span>live days recorded</span><b>%s</b></div>'
           '<div class="kv"><span>drift (recorded vs recomputed)</span><b class="%s">%s</b></div>'
           '<div class="kv"><span>live since</span><b>%s</b></div><div class="kv"><span>decisions</span><b>%s</b></div></div>' % (
               rec.get("days_recorded", 0), "badc" if rec.get("drift_count") else "good",
               rec.get("drift_count", 0), esc(REGISTERED["epoch_date"]),
               "weekly, first trading day" if REGISTERED.get("rebalance") == "weekly" else "monthly"),
           '<div class="card"><h3>Fingerprints</h3><div class="kv"><span>trading rules</span><b class="num">%s</b></div>'
           '<div class="kv"><span>headline test</span><b class="num">%s</b></div>'
           '<div class="kv"><span>page built</span><b>%s</b></div></div>' % (
               esc(res["registration_hash"]), esc(_hh()), esc(str(res.get("generated_at", ""))[:19].replace("T", " ") + " UTC")),
           '</div>']
    if rec.get("drift"):
        out.append('<div class="tw" style="margin-top:12px"><table><tr><th>date</th><th>book</th><th>recorded</th>'
                   '<th>recomputed</th></tr>%s</table></div>' % "".join(
                       "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                           esc(x["date"]), esc(x["book"]), money(x["recorded"]), money(x["recomputed"]))
                       for x in rec["drift"]))
    out.append('<h3 style="margin:18px 0 6px">Files this system writes (limit 25 MB each; GitHub refuses 100 MB)</h3>'
               '<div class="tw"><table><tr><th>file</th><th>size</th></tr>%s</table></div>' % "".join(
                   "<tr><td>%s</td><td>%.2f MB</td></tr>" % (esc(p.name), p.stat().st_size / 1e6) for p in files))
    out.append('<h3 style="margin:18px 0 6px">Every run (newest first)</h3><div class="tw"><table><tr><th>run (UTC)</th>'
               '<th>data through</th><th>source</th><th>age</th><th>drift</th><th>Master</th><th>hold all 8</th>'
               '<th>rules</th></tr>%s</table></div>' % "".join(
                   "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s d</td><td>%s</td><td>%s</td><td>%s</td><td class=\"num\">%s</td></tr>" % (
                       esc(str(r.get("t", ""))[:16].replace("T", " ")), esc(r.get("data_through")), esc(r.get("source")),
                       esc(r.get("stale_days")), esc(r.get("drift_count")), money(r.get("master")),
                       money(r.get("equal_weight_hold")), esc(r.get("hash")))
                   for r in reversed(runs[-40:])))
    return "".join(out)


def _rules(res: Dict) -> str:
    R = REGISTERED
    rt = R["round_trip_cost"]
    cats = "".join("<tr><td>%s</td><td>%s</td></tr>" % (LABEL[c], esc(" · ".join(s))) for c, s in R["categories"].items())
    sl = "".join("<tr><td><b>%s</b></td><td class=\"wrap\">%s</td></tr>" % (esc(k), esc(v)) for k, v in R["sleeves"].items())
    return ('<div class="card"><p><b>Decisions:</b> %s, on the first trading day of each %s, from the previous '
            'close; fills at that day\'s close. The MOMENTUM sleeves and the Master can also step out on any day.</p>'
            '<p><b>Costs:</b> crypto %.1f%% per round trip, ETFs %.1f%%, T-bills free; both sides of every trade pay. '
            '<b>Prices:</b> adjusted closes (dividends and splits included). <b>Idle money:</b> T-bills (BIL).</p>'
            '<p><b>Signals:</b> %d-day average; momentum = mean of %s-day returns; volatility over %d days, target %.0f%%; '
            'hysteresis %.0f point.</p>'
            '<p><b>Pass at week %d:</b> %s.</p>'
            '<p class="dim">Full text: <a href="https://github.com/TheSeanMitchell/SILMARIL-4.0/blob/main/REGISTRATION_4.md">'
            'REGISTRATION_4.md</a> · fingerprint <span class="num">%s</span></p></div>'
            '<div class="tw" style="margin-top:12px"><table><tr><th>category</th><th>assets</th></tr>%s</table></div>'
            '<div class="tw" style="margin-top:12px"><table><tr><th>sleeve</th><th>rule</th></tr>%s'
            '<tr><td><b>ACCOUNT</b></td><td class="wrap">%s</td></tr><tr><td><b>MASTER</b></td><td class="wrap">%s</td></tr>'
            '</table></div>'
            '<div class="card" style="margin-top:12px"><p><b>What to expect:</b> in the history replay these rules grew '
            'a little slower than holding all eight assets and fell much less in the worst stretch. A few months of '
            'live data cannot tell luck from skill; the page will not pretend otherwise.</p><p class="dim">%s</p></div>') % (
        esc(R.get("rebalance", "monthly").capitalize()), "week" if R.get("rebalance") == "weekly" else "month",
        100 * rt["crypto"], 100 * rt["etf"], R["sma_days"], "/".join(str(x) for x in R["momentum_lookbacks"]),
        R["vol_window"], 100 * R["vol_target"], 100 * R["hysteresis"], R["verdict"]["horizon_weeks"],
        esc(R["verdict"]["pass"]), esc(res["registration_hash"]), cats, sl, esc(R["account_rule"]),
        esc(R["master_rule"]), esc(R["no_halts_without_a_way_back"]))


def build(res: Dict, docs: Path, cockpit: Optional[Dict] = None) -> Path:
    m = res["master"]
    ew = res["benchmarks"]["equal_weight_hold"]
    spy = res["benchmarks"]["spy_hold"]
    fwd = res["epoch_reached"]
    H = []
    H.append('<!doctype html><html lang="en"><head><meta charset="utf-8">'
             '<meta name="viewport" content="width=device-width,initial-scale=1">'
             '<title>SILMARIL 4.0 · The Ladder</title><style>%s</style></head><body><div class="wrap">' % CSS)
    H.append('<h1>SILMARIL 4.0 <small>THE LADDER</small></h1>')
    H.append('<p class="dim">Sleeves → category accounts → master. Paper money, rebuilt from '
             'prices every day, every number beside the do-nothing number it has to beat.</p>')
    H.append(_status(res))
    H.append('<nav class="tabs" aria-label="Sections">%s</nav>' % "".join(
        '<a href="#%s" data-tab="%s">%s</a>' % (k, k, v) for k, v in TABS))
    H.append('<section class="tab" id="tab-command">')

    # ── the master ───────────────────────────────────────────────────────────────
    H.append("<h2>Master account</h2>")
    if fwd:
        mv, ev_, sv = m.get("forward_value"), ew.get("forward_value"), spy.get("forward_value")
        f = m.get("forward", {})
        H.append('<div class="grid">')
        H.append('<div class="card"><h3>Master (forward, from %s)</h3><div class="big %s">%s</div>'
                 '<div class="dim">%s since the epoch · %d trading days</div></div>' % (
                     esc(REGISTERED["epoch_date"]), cls((mv or 0) - 10000), money(mv),
                     pct(f.get("total_pct")), f.get("days", 0)))
        H.append('<div class="card"><h3>vs holding all 8 assets</h3><div class="big %s">%s</div>'
                 '<div class="dim">equal-weight hold is at %s</div></div>' % (
                     cls((mv or 0) - (ev_ or 0)), ("+" if (mv or 0) >= (ev_ or 0) else "−") +
                     money(abs((mv or 0) - (ev_ or 0)))[0:], money(ev_)))
        H.append('<div class="card"><h3>vs holding SPY</h3><div class="big %s">%s</div>'
                 '<div class="dim">SPY hold is at %s</div></div>' % (
                     cls((mv or 0) - (sv or 0)), ("+" if (mv or 0) >= (sv or 0) else "−") +
                     money(abs((mv or 0) - (sv or 0))), money(sv)))
        H.append("</div>")
    else:
        H.append('<div class="banner warn">The forward experiment opens at the close of <b>%s</b>. '
                 'Every account starts with $10,000 that day. Until then this page shows what the '
                 'same rules did on past prices.</div>' % esc(REGISTERED["epoch_date"]))
    seats = m.get("seats_now") or []
    H.append('<div class="card" style="margin-top:12px"><h3>What the master holds now</h3>'
             '<p><b>Seats:</b> %s</p><p><b>Target:</b> %s</p>'
             '<p class="dim">Next scheduled decision: %s (on the previous close). A held category '
             'that falls below T-bills is dropped the next day.</p>' % (
                 esc(" + ".join(LABEL[c] for c in seats) or "none — everything in T-bills"),
                 esc(weights_text(m.get("target_now"))), esc(_next_monthly(res))))
    w = m.get("watch", {})
    tb = w.get("tbills_score")
    rows = "".join('<div class="kv"><span>%s account momentum</span><b class="%s">%s</b></div>' % (
        LABEL[c], cls((v or 0) - (tb or 0)), pct(100 * v if v is not None else None))
        for c, v in sorted((w.get("scores") or {}).items(), key=lambda kv: -(kv[1] or -9)))
    H.append(rows + '<div class="kv"><span>T-bills (the bar to clear)</span><b>%s</b></div></div>' % (
        pct(100 * tb if tb is not None else None)))

    # ── category accounts ────────────────────────────────────────────────────────
    H.append("<h2>The four category accounts</h2>")
    H.append('<div class="grid">')
    for c in CATS:
        a = res["categories"][c]["account"]
        sl = res["categories"][c]["sleeves"]
        wt = res["categories"][c]["watch"]
        head = ""
        if fwd:
            av, hv = a.get("forward_value"), a.get("forward_hold_value")
            head = ('<div class="big %s">%s</div><div class="dim">hold twin %s · difference '
                    '<span class="%s">%s</span></div>' % (cls((av or 0) - 10000), money(av), money(hv),
                                                           cls((av or 0) - (hv or 0)),
                                                           ("+" if (av or 0) >= (hv or 0) else "−") +
                                                           money(abs((av or 0) - (hv or 0)))))
        mom = sl["MOMENTUM"]["target_now"] or {}
        vt = sum((sl["VOLTARGET"]["target_now"] or {}).values())
        tr = [s for s, up in wt["above_200d"].items() if up]
        H.append('<div class="card"><h3>%s · %s</h3>%s'
                 '<div class="kv"><span>holds now</span><b>%s</b></div>'
                 '<div class="kv"><span>TREND</span><b>%s</b></div>'
                 '<div class="kv"><span>MOMENTUM</span><b>%s</b></div>'
                 '<div class="kv"><span>VOLTARGET</span><b>%.0f%% invested</b></div>'
                 '<div class="kv"><span>replay CAGR · worst drop</span><b>%s · %s</b></div>'
                 '<div class="kv"><span>hold twin, same window</span><b>%s · %s</b></div></div>' % (
                     LABEL[c], esc(" / ".join(REGISTERED["categories"][c])), head,
                     esc(weights_text(a.get("target_now"))),
                     esc((" + ".join(tr) + " above 200-day") if tr else "both below 200-day → T-bills"),
                     esc((list(mom)[0] if mom else "T-bills")), 100 * vt,
                     pct(a["replay"].get("cagr_pct")), pct(a["replay"].get("max_dd_pct")),
                     pct(sl["HOLD"]["replay"].get("cagr_pct")), pct(sl["HOLD"]["replay"].get("max_dd_pct"))))
    H.append("</div>")

    # ── sleeves ─────────────────────────────────────────────────────────────────
    H.append("<h2>The sixteen sleeves</h2>")
    H.append('<p class="dim">History replay from %s to the epoch. HOLD is each category\'s '
             'do-nothing twin — the bar every other row has to clear.</p>' % esc(res["replay_start"]))
    t = ['<div class="tw"><table><tr><th>category</th><th>sleeve</th><th>rule</th><th>total</th>'
         '<th>per year</th><th>worst drop</th><th>Sharpe</th><th>trades</th><th>fees</th>'
         '<th>forward</th></tr>']
    for c in CATS:
        for name, s in res["categories"][c]["sleeves"].items():
            r = s["replay"]
            t.append('<tr><td>%s</td><td><b>%s</b></td><td class="wrap dim">%s</td><td class="%s">%s</td>'
                     '<td>%s</td><td class="neg">%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                         LABEL[c], name, esc(SLEEVE_DESC[name]), cls(r.get("total_pct")),
                         pct(r.get("total_pct")), pct(r.get("cagr_pct")), pct(r.get("max_dd_pct")),
                         r.get("sharpe") if r.get("sharpe") is not None else "—", s["replay_trades"],
                         money(s["replay_fees"]), money(s.get("forward_value")) if fwd else "—"))
    t.append("</table></div>")
    H.append("".join(t))

    # ── history replay ───────────────────────────────────────────────────────────
    H.append("<h2>History replay — context, not proof</h2>")
    r, er, sr = m["replay"], ew["replay"], spy["replay"]
    H.append('<p>Same rules, same costs, run over past prices from %s to %s, starting with $10,000. '
             'The master made <b class="%s">%s</b> (%s a year, worst drop %s). Holding all eight '
             'assets made <b class="%s">%s</b> (%s a year, worst drop %s). Holding SPY made '
             '<b class="%s">%s</b> (%s a year, worst drop %s).</p>' % (
                 esc(r.get("from")), esc(r.get("to")), cls(r.get("total_pct")), pct(r.get("total_pct")),
                 pct(r.get("cagr_pct")), pct(r.get("max_dd_pct")), cls(er.get("total_pct")),
                 pct(er.get("total_pct")), pct(er.get("cagr_pct")), pct(er.get("max_dd_pct")),
                 cls(sr.get("total_pct")), pct(sr.get("total_pct")), pct(sr.get("cagr_pct")),
                 pct(sr.get("max_dd_pct"))))
    H.append('<p class="dim">The rules were chosen from published research and frozen on %s before '
             'this replay was run for the first time; nothing was tuned to it. A replay still is not '
             'evidence of the future: only the forward record is.</p>' % esc(REGISTERED["registered_on"]))
    H.append('<div class="card">%s</div>' % chart([
        {"name": "Master", "color": "var(--c1)", "points": m["replay_curve"], "width": 2.4},
        {"name": "Equal-weight hold of all 8", "color": "var(--c2)", "points": ew["replay_curve"]},
        {"name": "SPY hold", "color": "var(--c3)", "points": spy["replay_curve"]}], log=True))
    yt = ['<div class="tw" style="margin-top:12px"><table><tr><th>year</th><th>master</th>'
          '<th>equal-weight hold</th><th>SPY hold</th></tr>']
    for y in m.get("replay_years", []):
        yt.append('<tr><td>%s</td><td class="%s">%s</td><td class="%s">%s</td><td class="%s">%s</td></tr>' % (
            y["year"], cls(y["master"]), pct(y["master"]), cls(y["equal_weight"]), pct(y["equal_weight"]),
            cls(y["spy"]), pct(y["spy"])))
    yt.append("</table></div>")
    H.append("".join(yt))

    # ── forward chart + trade log ────────────────────────────────────────────────
    if fwd:
        H.append("<h2>Forward record</h2>")
        H.append('<div class="card">%s</div>' % chart([
            {"name": "Master", "color": "var(--c1)", "points": m.get("forward_curve", []), "width": 2.4},
            {"name": "Equal-weight hold of all 8", "color": "var(--c2)", "points": ew.get("forward_curve", [])},
            {"name": "SPY hold", "color": "var(--c3)", "points": spy.get("forward_curve", [])}]))
        H.append('<p class="dim">Every live fill, with the reason it happened and its full case file, is in '
                 'the <a href="#trades">Trades</a> tab.</p>')

    # ── recent decisions ────────────────────────────────────────────────────────
    H.append("<h2>Recent decisions, in the rules' own words</h2>")
    dec = [("Master", e) for e in m.get("recent_events", [])[-6:]]
    for c in CATS:
        dec += [(LABEL[c] + " account", e) for e in res["categories"][c]["account"]["recent_events"][-3:]]
    dec.sort(key=lambda x: x[1]["date"], reverse=True)
    H.append('<div class="tw"><table><tr><th>date</th><th>who</th><th>decision</th></tr>%s</table></div>' % "".join(
        '<tr><td>%s</td><td>%s</td><td class="wrap">%s</td></tr>' % (esc(e["date"]), esc(who), esc(e["why"]))
        for who, e in dec[:18]))
    H.append('</section>')

    # ── the interactive tabs (drawn by cockpit.js from data/ladder_cockpit.json) ──
    for key, title, note in (
            ("trades", "Every trade, with its case file",
             "Every buy and sell by the Master, the four accounts and the sixteen sleeves, with the rule's "
             "own reason. Click a row to open its case file."),
            ("forensics", "Forensics",
             "How the round trips and the individual decisions worked out, account by account."),
            ("signals", "Signals",
             "What each rule is looking at: price against its 200-day average, momentum against T-bills, "
             "and every buy and sell marked on the chart.")):
        H.append('<section class="tab" id="tab-%s"><h2>%s</h2><p class="dim">%s</p><div id="%s-app">'
                 '<p class="dim">Loading…</p></div><noscript><p>This tab needs JavaScript. The same data is in '
                 '<a href="data/ladder_cockpit.json">data/ladder_cockpit.json</a>.</p></noscript></section>' % (
                     key, title, note, key))

    # ── the headline test (watch-only) ──────────────────────────────────────────
    hl = res.get("headlines")
    H.append('<section class="tab" id="tab-headlines">')
    if not hl:
        H.append('<h2>Headline test — watch-only</h2><p class="dim">No headline data yet.</p>')
    if hl:
        H.append("<h2>Headline test — watch-only</h2>")
        if hl.get("error"):
            H.append('<div class="banner warn">The headline reader failed this run (%s). Trading was '
                     'not affected; the test resumes on the next run.</div>' % esc(hl["error"]))
        else:
            v = hl["verdicts"]
            d, w = v["direction"], v["warning"]
            H.append('<p class="dim">Every day it reads the headlines for each category. Once a week it '
                     'calls UP, DOWN or nothing from their tone, and five closes later it checks whether '
                     'the call was right. It never trades. Rules frozen 8 Nov 2026 (fingerprint '
                     '<span class="num">%s</span>); %d %s of headlines recorded since %s.</p>' % (
                         esc(hl["rules_hash"]), hl.get("days_recorded", 0),
                         "day" if hl.get("days_recorded", 0) == 1 else "days", esc(hl.get("first_day") or "—")))
            if hl.get("rules_changed"):
                H.append('<div class="banner bad">The headline rules changed after recording began: %s</div>'
                         % esc(json.dumps(hl["rules_changed"])))

            def pill(s):
                c = {"PASSED": "ok", "KILLED": "bad"}.get(s, "warn")
                return '<span class="banner %s" style="padding:2px 8px;margin:0;font-size:12px">%s</span>' % (c, esc(s))

            H.append('<div class="grid">')
            H.append('<div class="card"><h3>Direction: does tone call next week?</h3><p>%s</p>'
                     '<div class="kv"><span>graded calls</span><b>%d of %d needed</b></div>'
                     '<div class="kv"><span>right</span><b>%s</b></div>'
                     '<div class="kv"><span>z versus a coin flip (pass 2.5)</span><b>%s</b></div>'
                     '<div class="kv"><span>average result per call</span><b>%s</b></div></div>' % (
                         pill(d["status"]), d["calls"], d["need"],
                         "—" if d["hit_rate_pct"] is None else "%s%% (%d)" % (d["hit_rate_pct"], d["hits"]),
                         "—" if d["z"] is None else d["z"],
                         "—" if d["avg_signed_pct"] is None else pct(d["avg_signed_pct"])))
            H.append('<div class="card"><h3>Warning: do headline surges come before big moves?</h3><p>%s</p>'
                     '<div class="kv"><span>graded surges</span><b>%d of %d needed</b></div>'
                     '<div class="kv"><span>next-week move vs normal (pass 1.5×)</span><b>%s</b></div>'
                     '<div class="kv"><span>t (pass 2.5)</span><b>%s</b></div></div>' % (
                         pill(w["status"]), w["surges"], w["need"],
                         "—" if w["avg_move_ratio"] is None else "%.2f×" % w["avg_move_ratio"],
                         "—" if w["t"] is None else w["t"]))
            H.append("</div>")
            rows = []
            for c in CATS:
                lw = (hl.get("latest_week") or {}).get(c)
                rec = (hl.get("recent") or {}).get(c) or {}
                heads = "<br>".join("%s %s" % ("▲" if x["score"] > 0 else "▼", esc(x["title"]))
                                    for x in (rec.get("headlines") or [])[:3]) or '<span class="dim">none scored yet</span>'
                if lw and not lw.get("days_covered"):
                    wk = '<span class="dim">recording; the first call comes after a full week of headlines</span>'
                elif lw:
                    wk = "%s · tone %s · %s · %d headlines, %d days%s" % (
                        esc(lw["week"]), pct(100 * lw["tone"]), esc(lw["call"] or "no call"), lw["n"],
                        lw["days_covered"], " · SURGE" if lw.get("surge") else "")
                else:
                    wk = '<span class="dim">first weekly call after a week of headlines</span>'
                rows.append('<tr><td>%s</td><td class="wrap">%s</td><td class="wrap">%s</td></tr>' % (
                    LABEL[c], wk, heads))
            H.append('<div class="tw" style="margin-top:12px"><table><tr><th>category</th><th>latest weekly call</th>'
                     '<th>latest scored headlines</th></tr>%s</table></div>' % "".join(rows))
            g = hl.get("graded_calls") or []
            if g:
                H.append('<div class="tw" style="margin-top:12px"><table><tr><th>week</th><th>category</th>'
                         '<th>call</th><th>from</th><th>to</th><th>result vs T-bills</th><th></th></tr>%s</table></div>' % "".join(
                             '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class="%s">%s</td><td>%s</td></tr>' % (
                                 esc(x["week"]), LABEL[x["cat"]], esc(x["call"]), esc(x["base_date"]), esc(x["end_date"]),
                                 cls(x["signed_pct"]), pct(x["signed_pct"]), "right" if x["hit"] else "wrong")
                             for x in reversed(g)))

    H.append('</section>')

    # ── health and rules ────────────────────────────────────────────────────────
    H.append('<section class="tab" id="tab-health"><h2>Health</h2>%s</section>' % _health(res, docs))
    H.append('<section class="tab" id="tab-rules"><h2>The rules, as registered</h2>%s</section>' % _rules(res))

    H.append('<footer>SILMARIL 4.0 · registration %s · generated %s · rebuilt from prices on every run, '
             'so a missed day loses nothing.<br>Archives: <a href="%ssilmaril7_archive.html">the legacy 7.x '
             'dashboard, frozen 8 Oct 2026</a> · <a href="%ssteward.html">Steward 8.0, frozen</a> · '
             '<a href="data/ladder_results.json">every number on this page (JSON)</a></footer>' % (
                 esc(res["registration_hash"]), esc(res.get("generated_at", "")), ARCHIVE_SITE, ARCHIVE_SITE))
    # the 7.x site registered an offline cache (sw.js); this page needs none, so retire it
    H.append("<script>try{if('serviceWorker' in navigator){navigator.serviceWorker.getRegistrations()"
             ".then(function(rs){rs.forEach(function(r){r.unregister()})})}}catch(e){}</script>")
    # tab router: without JavaScript every section simply shows, one after another
    H.append("<script>(function(){var T=%s;function show(){var h=(location.hash||'#command').slice(1);"
             "if(T.indexOf(h)<0)h='command';T.forEach(function(t){var s=document.getElementById('tab-'+t);"
             "if(s)s.hidden=(t!==h);var a=document.querySelector('nav.tabs a[data-tab=\"'+t+'\"]');"
             "if(a)a.setAttribute('aria-current',t===h?'page':'false');});"
             "window.dispatchEvent(new CustomEvent('tabshown',{detail:h}));}"
             "window.addEventListener('hashchange',show);show();})();</script>" % json.dumps([k for k, _ in TABS]))
    H.append('<script src="cockpit.js?v=%s" defer></script>' % esc(str(res.get("generated_at", ""))[:19]))
    H.append("</div></body></html>")
    # the interactive tabs' code ships beside the page
    src = Path(__file__).resolve().parent / "cockpit.js"
    if src.exists():
        (Path(docs) / "cockpit.js").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    path = Path(docs) / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".html.tmp")
    tmp.write_text("".join(H), encoding="utf-8")
    tmp.replace(path)
    return path
