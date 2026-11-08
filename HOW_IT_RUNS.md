# SILMARIL 4.0 — how it runs

**Nothing to do day to day.** One workflow, `SILMARIL 4.0 - The Ladder (daily)`, runs by
itself every night at 02:17 UTC and whenever its code changes. No outside cron service, no
tokens, no secrets.

Each run:
1. runs the 20 tests (nothing runs if one fails);
2. downloads fresh prices and rebuilds the whole ladder from them;
3. reads the day's headlines for the watch-only headline test;
4. checks every recorded day against the recomputation (DRIFT shows in red);
5. saves the page and data. If the save fails, the run turns **red** and GitHub emails you.

**What to look at:** <https://theseanmitchell.github.io/SILMARIL-4.0/> — every 13 weeks is
plenty. A monthly system makes about a dozen decisions a year.

**What never to do:** no resets, and no edits to `ladder/config.py` or `HEADLINE_RULES`
without writing a new registration. Changing a rule after seeing results is how the old
system fooled itself.

**Storage:** the files this lane writes are about 1 MB in total and may never exceed 25 MB
(the run refuses). The price cache is saved weekly, so the repository grows slowly.

**The earlier versions** (1.0 to 3.0, the 7.x engine and Steward) are frozen in
TheSeanMitchell/SILMARIL-2.0, site <https://theseanmitchell.github.io/SILMARIL-2.0/>.
