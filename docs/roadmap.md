# Prioritized Implementation Roadmap

Merges Appendix A Section 9 (phased build plan, now committed as
`docs/build-plan.md`) with the additional items identified in
`docs/architecture-review.md`, `docs/data-source-validation.md`,
`docs/draft-strategy.md`, and `docs/sleeper-model-review.md`.

**Priority key**:
- **P0** — blocks core sleeper/draft-prep features; nothing else works without these.
- **P1** — data quality/validation; not blocking, but should land early to avoid building on bad data.
- **P2** — strategy/analytics enhancements that make the platform useful, not just functional.
- **P3** — future work, contingent on data history or premium data sources not yet available.

**Effort key**: S = part of a day, M = 1–3 days, L = a week+.

---

## P0 — Foundation (blocks core sleeper/draft features)

| # | Item | Effort | Depends on | Source |
|---|---|---|---|---|
| 0.1 | Project scaffolding: `pyproject.toml`, `.env.example`, `.gitignore`, package skeleton, `config.py` | S | – | Appendix A §0 |
| 0.2 | DB layer: `sql/schema/*.sql` (00–05), `db/connection.py`, `db/schema.py`, `tests/conftest.py` + `test_schema.py`, `sql/seed/nfl_teams.csv` + loader | M | 0.1 | Appendix A §1 |
| 0.3 | NFL ingestion: `ingest/common.py`, `ingest/nfl/{nflverse_client,normalize,load}.py` + tests; wire `football-stats ingest nfl`; smoke-test against real nflverse URLs | M | 0.2 | Appendix A §2 |
| 0.4 | NCAA ingestion: `ingest/ncaa/{cfbd_client,normalize,load}.py` + synthetic-data tests; wire `football-stats ingest ncaa` (live run needs `CFBD_API_KEY` + network) | M | 0.2 | Appendix A §3 |
| 0.5 | Crosswalk: `transform/seasons.py` (+ tests), `transform/crosswalk.py` (+ tests with synthetic data); wire `football-stats build-crosswalk`, populate `dim_players` | M | 0.3, 0.4 | Appendix A §4 |
| 0.6 | Sleeper analytics v1: `analytics/sleeper_score.py` (+ tests); wire `football-stats build-sleeper-scores`; composite `football-stats pipeline` | M | 0.5 | Appendix A §5 |
| 0.7 | Dashboard MVP: `dashboard/queries.py`, `dashboard/app.py`, Page 1 (Sleeper Explorer) full build, Pages 2–4 stubs; wire `football-stats dashboard` | L | 0.6 | Appendix A §6 |
| 0.8 | Cleanup & docs: delete `Fantasy_Football/`, rewrite `README.md`, `ruff check .` + `pytest` clean, end-to-end run on nflverse-only data | M | 0.1–0.7 | Appendix A §7 |
| 0.9 | CI: `.github/workflows/ci.yml` (lint-test always; live CFBD tests gated on secret) | S | 0.8 | Appendix A §8 |

---

## P1 — Data quality & validation

These should land alongside or immediately after the P0 ingestion work
(0.3/0.4) — building the crosswalk and sleeper scores on unvalidated data
means redoing analytics work later.

| # | Item | Effort | Depends on | Source |
|---|---|---|---|---|
| 1.1 | `meta_ingestion_log` table + write-on-every-ingest | S | 0.2 | architecture-review §4.1 |
| 1.2 | Raw cache: prefer Parquet over CSV for nflverse downloads; partition `data/raw/<source>/<dataset>/season=<year>/` | S | 0.3 | architecture-review §1, §3 |
| 1.3 | pandera schema checks on normalized DataFrames pre-load, fail loudly, log to `meta_ingestion_log` | M | 0.3, 0.4, 1.1 | architecture-review §4.2; data-source-validation §4.2/4.4 |
| 1.4 | Row-count sanity bounds per dataset/season (±10% of trailing 3-season avg) | S | 1.3 | data-source-validation §4.1 |
| 1.5 | Primary-key/duplicate checks on player-season, draft_picks, recruiting tables | S | 1.3 | data-source-validation §4.3 |
| 1.6 | `football-stats validate` CLI: cross-source reconciliation, nflverse `draft_picks` vs. CFBD `/draft/picks` | M | 0.3, 0.4 | data-source-validation §4.5; architecture-review §4.3 |
| 1.7 | Freshness checks (in-season lag alerts, calendar-aware off-season exceptions) | S | 1.1 | data-source-validation §4.6 |
| 1.8 | Manual verification of open items: nflverse `draft_picks`/`rosters`/`combine` start years, CFBD earliest PBP season, CFBD ToS page | S | – | data-source-validation §5 |
| 1.9 | Dashboard query caching: `@st.cache_data` keyed on `meta_ingestion_log.completed_at` | S | 0.7, 1.1 | architecture-review §6 |

---

## P2 — Strategy & sleeper-model enhancements

Builds on the P0 MVP once real data is flowing; these are the "make it
actually useful for draft prep" items.

| # | Item | Effort | Depends on | Source |
|---|---|---|---|---|
| 2.1 | `league_format_config` table + Half-PPR derivation from `fantasy_points`/`fantasy_points_ppr` | S | 0.3 | draft-strategy §3, §5.2 |
| 2.2 | `fact_draft_rankings` table + VORP/VOLS computation against `league_format_config` baselines | M | 0.5, 2.1 | draft-strategy §1, §5.1 |
| 2.3 | Tier detection (gap-detection over `vorp_score` per position) | S | 2.2 | draft-strategy §1 |
| 2.4 | ADP ingestion: Fantasy Football Calculator API → `adp` source table; `value_vs_adp` / `value_classification` in `fact_draft_rankings` | M | 2.2 | draft-strategy §2 |
| 2.5 | `dim_age_curve` table, derived from platform's own `fantasy_points_ppr` by position/age | M | 0.6 (≥1 season of data) | draft-strategy §5.3 |
| 2.6 | `dim_draft_pick_value` table (seed from cited hit rates: 68.6%/28%/16.4%), `dynasty_value_score` in `fact_draft_rankings` | M | 2.2, 2.5 | draft-strategy §5.3 |
| 2.7 | Dashboard: Draft Strategy page — VORP/tier board, ADP-delta sleeper/bust filter, Dynasty toggle | M | 2.2–2.6 | draft-strategy (all); Appendix A §6 |
| 2.8 | `sleeper_score` v2: position-specific formulas (WR/RB/TE/QB variants), corrected dominator-rating denominators | M | 0.6 | sleeper-model-review §3, §4 |
| 2.9 | Replace linear `draft_capital_score` with power-law curve (`100 × (1/pick)^0.67`), normalize `pick` by class-year total | S | 2.8 | sleeper-model-review §3 |
| 2.10 | Add `breakout_age` / `breakout_age_adjusted` / `college_entry_age` / `dominator_rating_career` / `production_trend_slope` to `fact_sleeper_scores` | M | 2.8 | sleeper-model-review §4 |
| 2.11 | NFL roster "buy-low" sleeper analysis (`fact_nfl_buy_low_scores`): efficiency-vs-volume, target-share trend, ADP gap | L | 0.6, 2.4 | sleeper-model-review §2, §5 |

---

## P3 — Future / contingent

| # | Item | Effort | Depends on | Source |
|---|---|---|---|---|
| 3.1 | College target share / YPRR / 1D-per-route metrics | L | Premium charting feed (PFF/SIS) licensed — not available via CFBD | sleeper-model-review §1 |
| 3.2 | ML-based sleeper model (logistic regression baseline + gradient boosting w/ SHAP), walk-forward CV | L | 3–5 years of `fact_sleeper_scores` + realized outcomes; 2.8–2.10 | sleeper-model-review §6 |
| 3.3 | Trained-model serving for `fact_sleeper_scores` (batch materialization, versioned model artifacts under `data/models/`) | M | 3.2 | architecture-review §7 |
| 3.4 | Scheduled ingestion + failure alerting (cron + email/Slack on non-zero exit) | S | 1.1 | architecture-review §5 |
| 3.5 | Segment `dim_draft_pick_value` hit rates by round + college production tier via crosswalk | M | 2.6, 0.5 | draft-strategy §5.3 cross-cutting note |

---

## Cross-reference summary

- **Appendix A** (Sections 1-9 of the original build plan) is committed as
  `docs/build-plan.md`. **Appendix A Section 9** phases 0–8 map to **P0**
  items 0.1–0.9 above (unchanged in scope; this roadmap doesn't reorder them,
  just adds P1–P3 alongside).
- Every P1 item traces to `docs/architecture-review.md` (storage/versioning/
  quality sections) or `docs/data-source-validation.md` §4 (validation
  checks).
- Every P2 item traces to `docs/draft-strategy.md` (VBD/ADP/Dynasty) or
  `docs/sleeper-model-review.md` §3–5 (formula critique + v2 metrics).
- All P3 items are explicitly gated on either external data the project
  doesn't currently have (premium charting) or historical depth the project
  hasn't accumulated yet (3–5 seasons for ML) — they are not blocked on any
  remaining design work, only on time/data.

**Suggested execution order**: P0 (0.1→0.9) end-to-end first to get a working
MVP with real nflverse data (NCAA ingestion in 0.4 will need the user's
`CFBD_API_KEY` and network access this sandbox doesn't have — build/test with
synthetic data here, live-verify in the user's environment). Interleave P1
items 1.1–1.3 into 0.3/0.4 directly (cheap, prevents rework). Then P2 in
roughly the listed order (2.1→2.2→2.3/2.4 unlocks the Draft Strategy page;
2.8→2.9→2.10 improves the existing Sleeper Explorer without a new page).
P3 revisited once P0/P1/P2 are stable and enough seasons of data have
accumulated.
