# SILMARIL 4.0 — The Ladder

Paper-money research system, rebuilt from prices every night by GitHub Actions and shown at
<https://theseanmitchell.github.io/SILMARIL-4.0/>.

**The ladder:** 16 sleeves (HOLD, TREND, MOMENTUM, VOLTARGET for each of crypto, stocks,
metals and energy) feed 4 category accounts, which feed 1 Master that holds the two
categories rising fastest while they beat T-bills. Decisions are weekly. Every number is shown beside the
do-nothing number it has to beat.

* Rules: `REGISTRATION_4.md` (fingerprint `566c8a43a3fb4b71`, frozen 8 Nov 2026)
* Headline test, watch-only: `REGISTRATION_HEADLINES.md` (fingerprint `e8b180560092fcf0`)
* Tests: `python scripts/test_ladder.py`
* One workflow: `.github/workflows/ladder.yml`, daily at 02:17 UTC and on any code change

The full history of SILMARIL 2.0 through 7.x and Steward 8.0 (April to November 2026) lives
in the legacy repository **TheSeanMitchell/SILMARIL-2.0** (site: <https://theseanmitchell.github.io/SILMARIL-2.0/>).

Paper results only. Not investment advice.
