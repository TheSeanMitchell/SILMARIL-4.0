/* SILMARIL 4.0 cockpit: the Trades, Forensics and Signals tabs.
   Reads data/ladder_cockpit.json, written by the nightly run (ladder/engine.py).
   Every number shown here is in that file; this script only sorts, filters and draws. */
(function () {
  "use strict";
  var D = null, MODE = "replay", shown = {}, drawnFor = {};
  var LBL = { crypto: "Crypto", stock: "Stocks", metal: "Metals", energy: "Energy" };
  var CATS = ["crypto", "stock", "metal", "energy"];
  var SLEEVES = ["HOLD", "TREND", "MOMENTUM", "VOLTARGET"];

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fmtN(v, d) { return Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }); }
  function money(v) { return v == null ? "—" : (v < 0 ? "−$" : "$") + fmtN(v, 2); }
  function smoney(v) { return v == null ? "—" : (v < 0 ? "−$" : "+$") + fmtN(v, 2); }
  function pct(v) { return v == null ? "—" : (v < 0 ? "−" : "+") + fmtN(v, 1) + "%"; }
  function px(v) { return v == null ? "—" : v >= 1 ? "$" + fmtN(v, 2) : "$" + Number(v).toPrecision(4); }
  function cls(v) { return v == null ? "" : (v >= 0 ? "good" : "badc"); }
  function css(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
  function bookName(b) {
    if (b === "MASTER") return "Master";
    var p = b.split(":"), c = LBL[p[0]] || p[0];
    return p[1] === "ACCOUNT" ? c + " account" : c + " · " + p[1];
  }
  function bookOrder() {
    var o = ["MASTER"];
    CATS.forEach(function (c) { o.push(c + ":ACCOUNT"); SLEEVES.forEach(function (s) { o.push(c + ":" + s); }); });
    return o;
  }
  function levelOf(b) { return b === "MASTER" ? "master" : (b.indexOf(":ACCOUNT") > 0 ? "account" : "sleeve"); }
  function good(t) { if (t.n21 == null) return null; return t.s === "BUY" ? t.n21 >= 0 : t.n21 <= 0; }

  /* ── loading ─────────────────────────────────────────────────────────────── */
  fetch("data/ladder_cockpit.json?v=" + Date.now())
    .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
    .then(function (d) {
      D = d;
      MODE = D.trades.some(function (t) { return t.m === "live"; }) ? "live" : "replay";
      window.addEventListener("tabshown", function (e) { render(e.detail); });
      var h = (location.hash || "#command").slice(1);
      render(h);
      document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeCase(); });
    })
    .catch(function (e) {
      ["trades", "forensics", "signals"].forEach(function (k) {
        var el = $(k + "-app");
        if (el) el.innerHTML = '<p class="badc">Could not load the trade data (' + esc(e.message || e) +
          '). The rest of the page is fine; reload in a minute.</p>';
      });
    });

  function render(tab) {
    if (!D) return;
    if (tab === "trades" || tab === "forensics" || tab === "signals") {
      if (drawnFor[tab] === MODE) return;
      drawnFor[tab] = MODE;
      ({ trades: renderTrades, forensics: renderForensics, signals: renderSignals })[tab]();
    }
  }
  function setMode(m) { MODE = m; drawnFor = {}; render((location.hash || "#command").slice(1)); }

  function modeBar() {
    var live = D.trades.some(function (t) { return t.m === "live"; });
    var h = '<div class="ctl" role="group" aria-label="Which record">' +
      '<button type="button" data-mode="live" aria-pressed="' + (MODE === "live") + '">Live, from the epoch</button>' +
      '<button type="button" data-mode="replay" aria-pressed="' + (MODE === "replay") + '">History replay, 2018 on</button></div>';
    if (MODE === "live" && !live) {
      h += '<div class="banner warn">Live trading starts at the close of the first market day on or after the epoch ' +
        '(Monday 9 November 2026). Switch to <b>History replay</b> to see every trade the same rules made on past prices.</div>';
    } else if (MODE === "replay") {
      h += '<p class="dim small">The replay is the same rules run over past prices. It is context, not proof: only the live record counts.</p>';
    }
    return h;
  }
  function wireMode(root) {
    root.querySelectorAll("button[data-mode]").forEach(function (b) {
      b.addEventListener("click", function () { setMode(b.getAttribute("data-mode")); });
    });
  }

  /* ── TRADES ──────────────────────────────────────────────────────────────── */
  var TS = { level: "all", book: "all", side: "all", q: "", page: 0 };
  function renderTrades() {
    var root = $("trades-app");
    var books = bookOrder();
    var h = modeBar() + '<div class="ctl">' +
      '<label for="t-level">Level</label><select id="t-level">' +
      [["all", "everything"], ["master", "Master"], ["account", "category accounts"], ["sleeve", "sleeves"]].map(function (o) {
        return '<option value="' + o[0] + '"' + (TS.level === o[0] ? " selected" : "") + ">" + o[1] + "</option>";
      }).join("") + "</select>" +
      '<label for="t-book">Account</label><select id="t-book"><option value="all">all</option>' +
      books.map(function (b) { return '<option value="' + b + '"' + (TS.book === b ? " selected" : "") + ">" + esc(bookName(b)) + "</option>"; }).join("") +
      "</select>" +
      '<label for="t-side">Side</label><select id="t-side">' +
      [["all", "buys and sells"], ["BUY", "buys"], ["SELL", "sells"]].map(function (o) {
        return '<option value="' + o[0] + '"' + (TS.side === o[0] ? " selected" : "") + ">" + o[1] + "</option>";
      }).join("") + "</select>" +
      '<label for="t-q">Symbol</label><input id="t-q" type="search" placeholder="e.g. BTC" value="' + esc(TS.q) + '" size="9"></div>' +
      '<div id="t-sum" class="small dim"></div><div class="tw" style="margin-top:8px"><table id="t-table"></table></div>' +
      '<div class="ctl" id="t-pager"></div>';
    root.innerHTML = h;
    wireMode(root);
    ["t-level", "t-book", "t-side"].forEach(function (id) {
      $(id).addEventListener("change", function (e) {
        TS[id.slice(2)] = e.target.value; TS.page = 0; tradeRows();
      });
    });
    $("t-q").addEventListener("input", function (e) { TS.q = e.target.value.trim().toUpperCase(); TS.page = 0; tradeRows(); });
    tradeRows();
  }
  function filteredTrades() {
    return D.trades.filter(function (t) {
      return t.m === MODE && (TS.level === "all" || t.lv === TS.level) && (TS.book === "all" || t.b === TS.book) &&
        (TS.side === "all" || t.s === TS.side) && (!TS.q || t.y.toUpperCase().indexOf(TS.q) >= 0);
    }).sort(function (a, b) { return a.d < b.d ? 1 : a.d > b.d ? -1 : (a.b < b.b ? -1 : 1); });
  }
  function tradeRows() {
    var rows = filteredTrades(), per = 100, pages = Math.max(1, Math.ceil(rows.length / per));
    TS.page = Math.min(TS.page, pages - 1);
    var bought = 0, sold = 0, fees = 0, judged = 0, right = 0;
    rows.forEach(function (t) {
      if (t.s === "BUY") bought += t.u; else sold += t.u;
      fees += t.f;
      var g = good(t); if (g != null) { judged++; if (g) right++; }
    });
    $("t-sum").innerHTML = rows.length.toLocaleString() + " fills · bought " + money(bought) + " · sold " + money(sold) +
      " · fees " + money(fees) + (judged ? " · " + Math.round(100 * right / judged) + "% were followed by the move the trade wanted (21 trading days later)" : "");
    var slice = rows.slice(TS.page * per, TS.page * per + per);
    var h = "<tr><th>date (close)</th><th>account</th><th>side</th><th>symbol</th><th>amount</th><th>fee</th><th>price</th>" +
      "<th>next 21 days</th><th>why</th></tr>";
    if (!slice.length) h += '<tr><td colspan="9" class="dim">No trades match.</td></tr>';
    slice.forEach(function (t, i) {
      var g = good(t);
      h += '<tr class="click" tabindex="0" data-ep="' + esc(t.e) + '"><td>' + esc(t.d) + "</td><td>" + esc(bookName(t.b)) +
        "</td><td>" + (t.s === "BUY" ? "▲ buy" : "▼ sell") + "</td><td>" + esc(t.y) + "</td><td>" + money(t.u) +
        "</td><td>" + money(t.f) + "</td><td>" + px(t.p) + '</td><td class="' + (g == null ? "dim" : g ? "good" : "badc") + '">' +
        (t.n21 == null ? "not yet" : pct(t.n21) + (g ? " ✓" : " ✗")) + '</td><td class="wrap small">' + esc(t.w) + "</td></tr>";
    });
    var tb = $("t-table"); tb.innerHTML = h;
    tb.querySelectorAll("tr.click").forEach(function (tr) {
      tr.addEventListener("click", function () { openCase(tr.getAttribute("data-ep")); });
      tr.addEventListener("keydown", function (e) { if (e.key === "Enter") openCase(tr.getAttribute("data-ep")); });
    });
    var p = $("t-pager");
    p.innerHTML = pages > 1 ? '<button type="button" id="t-prev"' + (TS.page ? "" : " disabled") + '>← newer</button>' +
      '<span class="small dim">page ' + (TS.page + 1) + " of " + pages + "</span>" +
      '<button type="button" id="t-next"' + (TS.page < pages - 1 ? "" : " disabled") + ">older →</button>" : "";
    if (pages > 1) {
      $("t-prev").addEventListener("click", function () { TS.page--; tradeRows(); });
      $("t-next").addEventListener("click", function () { TS.page++; tradeRows(); });
    }
  }

  /* ── the case file ───────────────────────────────────────────────────────── */
  function openCase(id) {
    var ep = D.episodes.filter(function (e) { return e.id === id; })[0];
    if (!ep) return;
    var fills = D.trades.filter(function (t) { return t.e === id; }).sort(function (a, b) { return a.d < b.d ? -1 : 1; });
    var open = ep.st === "open";
    var verdict = "";
    if (ep.during != null) {
      verdict = "This position " + (ep.pnl >= 0 ? "made " : "lost ") + money(Math.abs(ep.pnl)) + " (" + pct(ep.pct) +
        ") while " + esc(ep.y) + " itself moved " + pct(ep.during) + " over the same days.";
    }
    if (!open && ep.after21 != null) {
      verdict += " In the 21 trading days after the final sale it moved " + pct(ep.after21) +
        (ep.after21 <= 0 ? ", so selling avoided that." : ", so selling missed that.");
    }
    var h = '<div class="modal-bg" id="case-bg"><div class="modal" role="dialog" aria-modal="true" aria-labelledby="case-title">' +
      '<button type="button" class="x" id="case-x">Close ✕</button>' +
      '<h3 id="case-title">' + esc(ep.y) + " · " + esc(bookName(ep.b)) + "</h3>" +
      '<p class="dim small">' + (ep.m === "live" ? "Live record" : "History replay") + " · " +
      (open ? "position still open" : "round trip, closed") + " · " + ep.fills + " fills · " + ep.days + " trading days</p>" +
      (verdict ? "<p>" + verdict + "</p>" : "") +
      '<div class="grid" style="margin-top:10px">' +
      '<div class="card"><h3>Opened</h3><p><b>' + esc(ep.od) + "</b> at " + px(ep.ep) + '</p><p class="small">' + esc(ep.ew) + "</p></div>" +
      '<div class="card"><h3>' + (open ? "Still held" : "Closed") + "</h3>" +
      (open ? "<p>worth <b>" + money(ep.now) + "</b> at the latest close</p>"
        : "<p><b>" + esc(ep.cd) + "</b> at " + px(ep.xp) + '</p><p class="small">' + esc(ep.xw) + "</p>") + "</div>" +
      '<div class="card"><h3>Money</h3><div class="kv"><span>put in (with fees)</span><b>' + money(ep["in"]) + "</b></div>" +
      '<div class="kv"><span>taken out (after fees)</span><b>' + money(ep.out) + "</b></div>" +
      (open ? '<div class="kv"><span>still invested</span><b>' + money(ep.now) + "</b></div>" : "") +
      '<div class="kv"><span>fees paid</span><b>' + money(ep.fees) + "</b></div>" +
      '<div class="kv"><span>profit or loss</span><b class="' + cls(ep.pnl) + '">' + smoney(ep.pnl) + " (" + pct(ep.pct) + ")</b></div></div>" +
      '<div class="card"><h3>' + esc(ep.y) + " around the trade</h3>" +
      '<div class="kv"><span>21 days before buying</span><b>' + pct(ep.before21) + "</b></div>" +
      '<div class="kv"><span>while held</span><b>' + pct(ep.during) + "</b></div>" +
      '<div class="kv"><span>best / worst while held</span><b>' + pct(ep.best) + " / " + pct(ep.worst) + "</b></div>" +
      '<div class="kv"><span>21 days after selling</span><b>' + (open ? "—" : pct(ep.after21)) + "</b></div></div></div>" +
      '<div class="chart" id="case-chart" style="margin-top:12px"></div>' +
      '<div class="tw" style="margin-top:12px"><table><tr><th>date</th><th>side</th><th>amount</th><th>fee</th><th>price</th>' +
      "<th>next 21 days</th><th>why</th></tr>" +
      fills.map(function (t) {
        var g = good(t);
        return "<tr><td>" + esc(t.d) + "</td><td>" + (t.s === "BUY" ? "▲ buy" : "▼ sell") + "</td><td>" + money(t.u) +
          "</td><td>" + money(t.f) + "</td><td>" + px(t.p) + '</td><td class="' + (g == null ? "dim" : g ? "good" : "badc") + '">' +
          (t.n21 == null ? "not yet" : pct(t.n21)) + '</td><td class="wrap small">' + esc(t.w) + "</td></tr>";
      }).join("") + "</table></div>" +
      '<p class="dim small" style="margin-top:8px">"Before", "after" and "next 21 days" use hindsight to judge the decision. ' +
      "The rules never see them: every decision reads closes up to the day before it fills.</p></div></div>";
    closeCase();
    document.body.insertAdjacentHTML("beforeend", h);
    $("case-x").addEventListener("click", closeCase);
    $("case-bg").addEventListener("click", function (e) { if (e.target.id === "case-bg") closeCase(); });
    $("case-x").focus();
    caseChart(ep, fills);
  }
  function closeCase() { var b = $("case-bg"); if (b) b.parentNode.removeChild(b); }
  function caseChart(ep, fills) {
    var sig = D.signals[ep.y], host = $("case-chart");
    if (!sig) return;
    var a = sig.dates.indexOf(ep.od), b = ep.cd ? sig.dates.indexOf(ep.cd) : sig.dates.length - 1;
    if (a < 0 || b < 0) {
      host.innerHTML = '<p class="dim small">The price chart covers the last two years; this trade is older.</p>';
      return;
    }
    var i0 = Math.max(0, a - 30), i1 = Math.min(sig.dates.length - 1, b + 30);
    var idx = {}; sig.dates.forEach(function (d, i) { idx[d] = i; });
    var marks = fills.map(function (t) { return { i: idx[t.d] - i0, buy: t.s === "BUY", title: (t.s === "BUY" ? "buy " : "sell ") + money(t.u) }; })
      .filter(function (m) { return m.i >= 0; });
    lineChart(host, {
      dates: sig.dates.slice(i0, i1 + 1), h: 220, aria: ep.y + " price around this trade",
      series: [{ name: ep.y + " close", color: css("--c1"), vals: sig.close.slice(i0, i1 + 1) },
               { name: "200-day average", color: css("--c2"), vals: sig.sma200.slice(i0, i1 + 1), dash: "4 4" }],
      markers: marks, fmt: function (v) { return v >= 1000 ? fmtN(v, 0) : fmtN(v, 2); }
    });
  }

  /* ── FORENSICS ───────────────────────────────────────────────────────────── */
  var FS = { level: "all" };
  function renderForensics() {
    var root = $("forensics-app");
    var h = modeBar() + '<div class="ctl"><label for="f-level">Level</label><select id="f-level">' +
      [["all", "everything"], ["master", "Master"], ["account", "category accounts"], ["sleeve", "sleeves"]].map(function (o) {
        return '<option value="' + o[0] + '"' + (FS.level === o[0] ? " selected" : "") + ">" + o[1] + "</option>";
      }).join("") + '</select></div><div id="f-body"></div>';
    root.innerHTML = h;
    wireMode(root);
    $("f-level").addEventListener("change", function (e) { FS.level = e.target.value; forensicsBody(); });
    forensicsBody();
  }
  function forensicsBody() {
    var books = bookOrder().filter(function (b) { return FS.level === "all" || levelOf(b) === FS.level; });
    var eps = D.episodes.filter(function (e) { return e.m === MODE; });
    var trs = D.trades.filter(function (t) { return t.m === MODE; });
    var h = "<h3 style=\"margin:14px 0 6px\">Round trips (a position opened, then fully sold)</h3>" +
      '<div class="tw"><table><tr><th>account</th><th>closed</th><th>won</th><th>avg win</th><th>avg loss</th>' +
      "<th>payoff</th><th>total profit</th><th>fees</th><th>avg days</th><th>best</th><th>worst</th><th>still open</th></tr>";
    books.forEach(function (b) {
      var c = eps.filter(function (e) { return e.b === b && e.st === "closed"; });
      var o = eps.filter(function (e) { return e.b === b && e.st === "open"; });
      if (!c.length && !o.length) return;
      var w = c.filter(function (e) { return e.pnl > 0; }), l = c.filter(function (e) { return e.pnl <= 0; });
      var aw = w.length ? w.reduce(function (s, e) { return s + e.pct; }, 0) / w.length : null;
      var al = l.length ? l.reduce(function (s, e) { return s + e.pct; }, 0) / l.length : null;
      var tot = c.reduce(function (s, e) { return s + e.pnl; }, 0), fees = c.reduce(function (s, e) { return s + e.fees; }, 0);
      var days = c.length ? c.reduce(function (s, e) { return s + e.days; }, 0) / c.length : null;
      var best = c.length ? Math.max.apply(null, c.map(function (e) { return e.pct; })) : null;
      var worst = c.length ? Math.min.apply(null, c.map(function (e) { return e.pct; })) : null;
      h += "<tr><td>" + esc(bookName(b)) + "</td><td>" + c.length + "</td><td>" + (c.length ? Math.round(100 * w.length / c.length) + "%" : "—") +
        '</td><td class="good">' + pct(aw) + '</td><td class="badc">' + pct(al) + "</td><td>" +
        (aw != null && al ? (aw / Math.abs(al)).toFixed(2) : "—") + '</td><td class="' + cls(tot) + '">' + (c.length ? smoney(tot) : "—") +
        "</td><td>" + (c.length ? money(fees) : "—") + "</td><td>" + (days == null ? "—" : days.toFixed(0)) + '</td><td class="good">' + pct(best) +
        '</td><td class="badc">' + pct(worst) + "</td><td>" + o.length + "</td></tr>";
    });
    h += "</table></div><p class=\"dim small\">Payoff = average win ÷ average loss. The category accounts blend three sleeves, " +
      "so they rarely sell an asset completely; judge them by the decision table below.</p>";

    h += "<h3 style=\"margin:18px 0 6px\">Every decision, judged 21 trading days later</h3>" +
      '<div class="tw"><table><tr><th>account</th><th>buys</th><th>followed by a rise</th><th>avg after buying</th>' +
      "<th>sells</th><th>followed by a fall</th><th>avg after selling</th><th>sells that dodged a 5%+ drop</th><th>sells before a 5%+ rally</th></tr>";
    books.forEach(function (b) {
      var bt = trs.filter(function (t) { return t.b === b && t.n21 != null; });
      if (!bt.length) return;
      var buys = bt.filter(function (t) { return t.s === "BUY"; }), sells = bt.filter(function (t) { return t.s === "SELL"; });
      function avg(a) { return a.length ? a.reduce(function (s, t) { return s + t.n21; }, 0) / a.length : null; }
      var up = buys.filter(function (t) { return t.n21 > 0; }).length, dn = sells.filter(function (t) { return t.n21 < 0; }).length;
      h += "<tr><td>" + esc(bookName(b)) + "</td><td>" + buys.length + "</td><td>" + (buys.length ? Math.round(100 * up / buys.length) + "%" : "—") +
        '</td><td class="' + cls(avg(buys)) + '">' + pct(avg(buys)) + "</td><td>" + sells.length + "</td><td>" +
        (sells.length ? Math.round(100 * dn / sells.length) + "%" : "—") + '</td><td class="' + cls(avg(sells) == null ? null : -avg(sells)) + '">' + pct(avg(sells)) +
        '</td><td class="good">' + sells.filter(function (t) { return t.n21 <= -5; }).length + '</td><td class="badc">' +
        sells.filter(function (t) { return t.n21 >= 5; }).length + "</td></tr>";
    });
    h += "</table></div><p class=\"dim small\">A buy is right when its asset rose over the next 21 trading days; a sell is right when it fell. " +
      "Hindsight only: the rules never see these numbers.</p>";

    var closed = eps.filter(function (e) { return e.st === "closed" && books.indexOf(e.b) >= 0; });
    var best = closed.slice().sort(function (a, b) { return b.pnl - a.pnl; }).slice(0, 10);
    var worst = closed.slice().sort(function (a, b) { return a.pnl - b.pnl; }).slice(0, 10);
    function list(title, arr) {
      return "<div><h3 style=\"margin:18px 0 6px\">" + title + '</h3><div class="tw"><table><tr><th>account</th><th>symbol</th>' +
        "<th>opened</th><th>closed</th><th>profit</th><th>%</th></tr>" + (arr.length ? arr.map(function (e) {
          return '<tr class="click" tabindex="0" data-ep="' + esc(e.id) + '"><td>' + esc(bookName(e.b)) + "</td><td>" + esc(e.y) + "</td><td>" +
            esc(e.od) + "</td><td>" + esc(e.cd) + '</td><td class="' + cls(e.pnl) + '">' + smoney(e.pnl) + '</td><td class="' + cls(e.pct) + '">' + pct(e.pct) + "</td></tr>";
        }).join("") : '<tr><td colspan="6" class="dim">None yet.</td></tr>') + "</table></div></div>";
    }
    h += '<div class="mini">' + list("Ten best round trips", best) + list("Ten worst round trips", worst) + "</div>";
    var body = $("f-body"); body.innerHTML = h;
    body.querySelectorAll("tr.click").forEach(function (tr) {
      tr.addEventListener("click", function () { openCase(tr.getAttribute("data-ep")); });
      tr.addEventListener("keydown", function (e) { if (e.key === "Enter") openCase(tr.getAttribute("data-ep")); });
    });
  }

  /* ── SIGNALS ─────────────────────────────────────────────────────────────── */
  function renderSignals() {
    var root = $("signals-app"), M = D.signals._master;
    var lastSeats = M.seats[M.seats.length - 1] || [];
    var h = modeBar() + "<h3 style=\"margin:14px 0 6px\">The Master's scoreboard: each category account's momentum against T-bills</h3>" +
      '<p class="small">Seats now: <b>' + (lastSeats.length ? lastSeats.map(function (c) { return LBL[c]; }).join(" + ") : "none, all in T-bills") +
      '</b>. Every week the Master holds the two highest lines that sit above the dashed T-bills line.</p>' +
      '<div class="card"><div class="chart" id="sig-master"></div></div>' +
      '<h3 style="margin:18px 0 6px">Each asset: price, its 200-day average, and every buy ▲ and sell ▼</h3>' +
      '<p class="dim small">Marks show the Master and that category\'s account in the ' + (MODE === "live" ? "live record" : "history replay") + ".</p>" +
      '<div class="mini" id="sig-assets"></div>';
    root.innerHTML = h;
    wireMode(root);
    var cols = [css("--c1"), css("--c2"), css("--c3"), css("--c4")];
    lineChart($("sig-master"), {
      dates: M.dates, h: 260, aria: "category momentum against T-bills",
      series: CATS.map(function (c, k) { return { name: LBL[c], label: LBL[c], color: cols[k], vals: M.scores[c] }; })
        .concat([{ name: "T-bills", label: "T-bills", color: css("--dim"), vals: M.tbills, dash: "5 4" }]),
      endLabels: true, fmt: function (v) { return (v > 0 ? "+" : "") + v.toFixed(0) + "%"; },
      extra: function (i) { var s = M.seats[i] || []; return "seats: " + (s.length ? s.map(function (c) { return LBL[c]; }).join(" + ") : "T-bills"); }
    });
    var wrap = $("sig-assets");
    CATS.forEach(function (c) {
      Object.keys(D.signals).forEach(function (sym) {
        var s = D.signals[sym];
        if (sym[0] === "_" || s.cat !== c) return;
        var n = s.dates.length - 1, above = s.close[n] > s.sma200[n], tb = D.signals._tbills_mom[n];
        var card = document.createElement("div");
        card.className = "card";
        card.innerHTML = "<h3>" + esc(sym) + " · " + LBL[c] + '</h3><p class="small">' + (above ? '<span class="good">above</span>' : '<span class="badc">below</span>') +
          " its 200-day average · momentum " + pct(s.mom[n]) + " vs T-bills " + pct(tb) + '</p><div class="chart"></div>';
        wrap.appendChild(card);
        var idx = {}; s.dates.forEach(function (d, i) { idx[d] = i; });
        var marks = D.trades.filter(function (t) {
          return t.m === MODE && t.y === sym && (t.b === "MASTER" || t.b === c + ":ACCOUNT") && idx[t.d] != null;
        }).map(function (t) { return { i: idx[t.d], buy: t.s === "BUY", title: bookName(t.b) + " " + (t.s === "BUY" ? "buy " : "sell ") + money(t.u) }; });
        lineChart(card.querySelector(".chart"), {
          dates: s.dates, h: 190, aria: sym + " price and 200-day average",
          series: [{ name: "close", color: css("--c1"), vals: s.close }, { name: "200-day", color: css("--c2"), vals: s.sma200, dash: "4 4" }],
          markers: marks, fmt: function (v) { return v >= 1000 ? fmtN(v, 0) : fmtN(v, v >= 100 ? 0 : 1); }
        });
      });
    });
  }

  /* ── one small line chart with hover, used everywhere ────────────────────── */
  function lineChart(host, o) {
    var NS = "http://www.w3.org/2000/svg", W = 1000, H = o.h || 220, L = 58, R = o.endLabels ? 92 : 12, T = 10, B = 26;
    function el(tag, at, parent, text) {
      var e = document.createElementNS(NS, tag);
      for (var k in at) e.setAttribute(k, at[k]);
      if (text != null) e.textContent = text;
      if (parent) parent.appendChild(e);
      return e;
    }
    host.innerHTML = "";
    var n = o.dates.length; if (n < 2) { host.innerHTML = '<p class="dim small">Not enough data yet.</p>'; return; }
    var lo = Infinity, hi = -Infinity;
    o.series.forEach(function (s) { s.vals.forEach(function (v) { if (v != null) { lo = Math.min(lo, v); hi = Math.max(hi, v); } }); });
    if (!isFinite(lo)) return;
    var pad = (hi - lo) * 0.06 || 1; lo -= pad; hi += pad;
    function X(i) { return L + (W - L - R) * i / (n - 1); }
    function Y(v) { return T + (H - T - B) * (1 - (v - lo) / (hi - lo)); }
    var svg = el("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": o.aria || "chart" }, host);
    for (var k = 0; k <= 4; k++) {
      var v = lo + (hi - lo) * k / 4;
      el("line", { x1: L, x2: W - R, y1: Y(v), y2: Y(v), stroke: css("--grid"), "stroke-width": 1 }, svg);
      el("text", { x: L - 6, y: Y(v) + 4, "text-anchor": "end", "font-size": 11, fill: css("--dim") }, svg, o.fmt ? o.fmt(v) : v.toFixed(1));
    }
    if (lo < 0 && hi > 0) el("line", { x1: L, x2: W - R, y1: Y(0), y2: Y(0), stroke: css("--dim"), "stroke-width": 1 }, svg);
    for (var q = 0; q <= 4; q++) {
      var i = Math.round(q * (n - 1) / 4);
      el("text", { x: X(i), y: H - 6, "text-anchor": q === 0 ? "start" : q === 4 ? "end" : "middle", "font-size": 11, fill: css("--dim") }, svg, o.dates[i].slice(0, 7));
    }
    var ends = [];
    o.series.forEach(function (s) {
      var d = "", pen = false;
      s.vals.forEach(function (v, i) {
        if (v == null) { pen = false; return; }
        d += (pen ? "L" : "M") + X(i).toFixed(1) + " " + Y(v).toFixed(1); pen = true;
      });
      var at = { d: d, fill: "none", stroke: s.color, "stroke-width": 2, "stroke-linejoin": "round" };
      if (s.dash) at["stroke-dasharray"] = s.dash;
      el("path", at, svg);
      if (o.endLabels) {
        for (var j = s.vals.length - 1; j >= 0; j--) if (s.vals[j] != null) break;
        if (j >= 0) ends.push({ x: X(j) + 6, y: Y(s.vals[j]) + 4, t: s.label || s.name, c: s.color });
      }
    });
    // end labels: keep them at least 13px apart so they never print on top of each other
    ends.sort(function (a, b) { return a.y - b.y; });
    for (var e = 1; e < ends.length; e++) if (ends[e].y - ends[e - 1].y < 13) ends[e].y = ends[e - 1].y + 13;
    var over = ends.length ? ends[ends.length - 1].y - (H - B) : 0;
    if (over > 0) ends.forEach(function (x) { x.y -= over; });
    ends.forEach(function (x) {
      el("text", { x: x.x, y: x.y, "font-size": 11, fill: css("--ink") }, svg, x.t);
    });
    (o.markers || []).forEach(function (m) {
      var v = o.series[0].vals[m.i]; if (v == null) return;
      var x = X(m.i), y = Y(v), c = m.buy ? css("--pos") : css("--neg");
      var pts = m.buy ? [x, y + 4, x - 5, y + 13, x + 5, y + 13] : [x, y - 4, x - 5, y - 13, x + 5, y - 13];
      el("polygon", { points: pts.join(","), fill: c, stroke: css("--card"), "stroke-width": 1 }, svg);
    });
    var lg = document.createElement("div"); lg.className = "legend";
    lg.innerHTML = o.series.map(function (s) {
      return '<i style="background:' + s.color + '"></i>' + esc(s.name);
    }).join("") + ((o.markers || []).length ? ' <span class="good">▲</span> buy <span class="badc">▼</span> sell' : "");
    host.appendChild(lg);
    var cross = el("line", { y1: T, y2: H - B, stroke: css("--dim"), "stroke-width": 1, visibility: "hidden" }, svg);
    var tip = document.createElement("div"); tip.className = "tip"; tip.hidden = true; host.appendChild(tip);
    var hit = el("rect", { x: L, y: T, width: W - L - R, height: H - T - B, fill: "transparent" }, svg);
    function move(ev) {
      var r = svg.getBoundingClientRect(), sx = (ev.clientX - r.left) * W / r.width;
      var i = Math.max(0, Math.min(n - 1, Math.round((sx - L) / (W - L - R) * (n - 1))));
      cross.setAttribute("x1", X(i)); cross.setAttribute("x2", X(i)); cross.setAttribute("visibility", "visible");
      var lines = ["<b>" + esc(o.dates[i]) + "</b>"];
      o.series.forEach(function (s) {
        if (s.vals[i] != null) lines.push('<span style="color:' + s.color + '">●</span> ' + esc(s.name) + ": " + (o.fmt ? o.fmt(s.vals[i]) : s.vals[i]));
      });
      (o.markers || []).forEach(function (m) { if (m.i === i) lines.push((m.buy ? "▲ " : "▼ ") + esc(m.title)); });
      if (o.extra) lines.push(esc(o.extra(i)));
      tip.innerHTML = lines.join("<br>"); tip.hidden = false;
      var px = X(i) * r.width / W;
      tip.style.left = Math.max(0, Math.min(px + 12, host.clientWidth - tip.offsetWidth - 4)) + "px";
      tip.style.top = "6px";
    }
    hit.addEventListener("pointermove", move); hit.addEventListener("pointerdown", move);
    hit.addEventListener("pointerleave", function () { tip.hidden = true; cross.setAttribute("visibility", "hidden"); });
  }
})();
