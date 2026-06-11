# Data Source Validation Report

This report profiles the two primary data sources chosen for the platform —
**nflverse-data** (NFL) and **CollegeFootballData.com / CFBD** (NCAA) — plus
supplemental sources useful for cross-checking, and defines concrete data
quality validation checks the ingestion pipeline (Appendix A, Section 4)
should implement.

> **Status note**: `api.collegefootballdata.com`, `collegefootballdata.com/about`,
> and `collegefootballdata.com/api-tiers` could not be reached from this
> research sandbox (403/Cloudflare). The CFBD profile below is sourced from the
> `cfbd-python` client docs, `cfbfastR` documentation, and the CFBD blog. The
> open items in Section 5 should be manually re-verified against the live site
> by a user with network access before the project depends on specific
> numbers (rate limits, ToS).

---

## 1. nflverse-data (NFL)

### 1.1 Datasets and coverage

| Dataset | Loader | Coverage / notes |
|---|---|---|
| Play-by-play (`pbp`) | `load_pbp()` | 1999–present. EPA/WP/CP/CPOE/xYAC fields from 2006+. Player IDs are **inconsistent between 1999–2010 and 2011+** (different upstream sources stitched together) — use `decode_player_ids()` / the `nflverse-players` crosswalk, not raw IDs, for cross-era joins. |
| Player season/weekly stats (`player_stats`) | `load_player_stats()` | Derived from pbp via nflfastR methodology; effectively ~1999+, weekly granularity stronger from the 2000s on. This is the source for `fact_nfl_player_*` tables (includes `fantasy_points`/`fantasy_points_ppr`). |
| Team stats (`stats_team`) | `load_team_stats()` | Same basis as player stats. |
| Draft picks | `load_draft_picks()` | **Discrepancy**: `nflreadr::load_draft_picks()` is documented as "every pick since 1980" (PFR-sourced), but the `nfldata` repo's `draft_picks.csv` documentation says "2000 season forward." **Verify empirically** (`min(season)` on the actual release file) before relying on pre-2000 draft history. |
| Combine results | `load_combine()` | PFR-sourced NFL Scouting Combine results. Exact start year not confirmed in docs (PFR's combine DB generally starts ~2000) — verify against the release file. |
| Rosters / weekly rosters | `load_rosters()`, `load_rosters_weekly()` | **Discrepancy**: NFL Shield v2 API source goes back to 2002, but `nfldata/rosters.csv` (PFR-sourced) is documented as "2006 onward." Two roster sources with different start years exist — pick one and document which. |
| Schedules/games | `load_schedules()` | Long historical span via `nflreadr`; `nfldata/games.csv` is documented as 2006+ and excludes preseason — verify exact start year against the release used. |
| Snap counts | `load_snap_counts()` | PFR-sourced, **2012 season onward**. |
| Next Gen Stats | `load_nextgen_stats()` | Player-level weekly passing/rushing/receiving NGS, **2016 season onward**, players above minimum attempt thresholds only. |
| FTN charting | `load_ftn_charting()` | Manual charting from FTNFantasy.com, **2022 onward only**. Licensed **CC-BY-SA 4.0**, requires attribution to "FTN Data via nflverse." |
| Injuries | `load_injuries()` | Weekly injury reports, **since 2009**. See reliability caveat below. |
| Depth charts | `load_depth_charts()` | Daily updates, year-round. |
| Contracts | `load_contracts()` | Sourced from OverTheCap.com. |
| Players (master ID crosswalk) | `load_players()` (nflverse-players repo) | Canonical player ID-mapping database with a manual override mechanism for ID corrections — **should be the base for `dim_players`/`bridge_player_crosswalk` ID joins**, not a hand-rolled mapping. |

### 1.2 Update cadence

All datasets are produced via GitHub Actions automation (see
[`nflreadr` data schedule](https://github.com/nflverse/nflreadr/blob/main/vignettes/articles/nflverse_data_schedule.Rmd)):

- **pbp_raw**: within 15 minutes of a game ending.
- **pbp / player & team stats**: nightly after game days, with additional
  same-day updates. *"Thursday's `load_pbp()` is the cleanest data"* because
  the NFL issues stat corrections through Wednesday.
- **Schedules**: every 5 minutes during the season.
- **Rosters / PFR advanced stats / depth charts**: daily at 07:00 UTC
  (depth charts year-round).
- **Next Gen Stats**: nightly, ~3–5 AM ET during the season.
- **Snap counts / FTN charting**: every 6 hours during the season.
- **Static/combined datasets** (draft_picks, combine, contracts): updated
  periodically as source data changes, no fixed schedule.
- **Caveat observed during research**: the automation status page flagged
  *"no 2025 injuries data available"* at one point — injuries freshness has
  had gaps and should be checked at ingestion time, not assumed.

### 1.3 Known data quality issues (maintainer-documented)

- **Player ID inconsistency across eras** (1999–2010 vs. 2011+); 2022+ rookie
  pbp rows are missing GSIS IDs entirely and need `load_players()` joins.
- **`nflverse-players` manual override file** exists *because* automated ID
  matching is imperfect — treat ID coverage as a metric to monitor, not a
  guarantee.
- **Drive-level fields in pbp are documented as "extremely buggy"** — avoid
  drive-level aggregations.
- **Historical team-attribution bugs** for Jacksonville Jaguars 2011–2015
  (`timeout_team`, `return_team`, `fumble_recovery_1_team`).
- **Injuries data likely undercounts true injury incidence** — an independent
  academic study (sport-related concussion research) found publicly available
  NFL injury-report data did not match the NFL's internal EHR data and was
  "significantly lower" in several years. Treat `fact_*injuries*` as directional,
  not authoritative, if ever added.
- **Combine/snap counts are PFR-scrapes** — any PFR site change can break the
  nflverse scraper until patched.

### 1.4 Maintenance / reliability

- `nfldata` (Lee Sharpe + community) had commits as recent as **June 2026** —
  actively maintained.
- `nflfastR` (core pbp engine): maintained by Ben Baldwin, Sebastian Carl, and
  a large community; 527★/65 forks.
- The nflverse GitHub org spans **36 repos** (R, Python, Julia) — a mature,
  modular ecosystem, not a single fragile project. "Open Source Football"
  blog (opensourcefootball.com) is an active community hub.
- **Overall**: low risk of the project disappearing or going stale; moderate
  risk of small breaking schema changes season-to-season (mitigated by the
  schema/contract checks in Section 5).

### 1.5 Licensing

- **Code** (nflreadr, nflfastR, etc.): **MIT License**.
- **Data**: explicitly **not** covered by the MIT code license — "NFL data
  accessed by this package belong to their respective owners, and are governed
  by their terms of use" (an aggregation of NFL.com, PFR, ESPN, OverTheCap,
  etc.).
- **FTN charting data specifically**: CC-BY-SA 4.0, attribution to "FTN Data
  via nflverse" required if used.
- **Practical read**: personal/internal fantasy analytics use (this project)
  is low-risk. Redistributing or commercializing the raw data would need a
  closer look at each upstream source's terms.

---

## 2. CollegeFootballData.com (CFBD) API

### 2.1 Coverage

| Data category | Endpoint / class | Notes |
|---|---|---|
| Games/schedules | `GamesApi` | Multi-season historical game data + team box scores. |
| Player season stats | `StatsApi` | Long/EAV format: one row per `(player, team, conference, category, statType, stat, season)` — must be **pivoted** into wide tables (Appendix A `STAT_COLUMN_MAP`). |
| Team stats | `StatsApi`, `TeamsApi.get_fbs_teams()` | FBS team metadata + season aggregates. |
| Plays/PBP | `PlaysApi` | Sourced largely through **ESPN's data provider** per `cfbfastR` docs. Earliest reliable season **not definitively confirmed** — commonly-cited starting points are 2001–2004 for some stats, with play-level granularity considered more reliable from ~2004–2005 onward. **Verify empirically** by querying early years and checking row counts. |
| Recruiting | `RecruitingApi` | Documented **minimum coverage year = 2000** for both team and player recruiting rankings. |
| NFL Draft | `DraftApi.get_draft_picks()` | Returns college athlete ID, NFL athlete ID, college, NFL team, round/pick, pre-draft grades, hometown. This is the natural **cross-check dataset against nflverse `draft_picks`** (Section 5.5) — and the bridge that links NCAA `athlete_id` to NFL outcomes. |
| Rosters | `TeamsApi`/roster endpoints | Team rosters by season. |
| Transfer portal | Recruiting-adjacent endpoints | Included alongside recruiting data. |
| GraphQL | `graphql.collegefootballdata.com` | **Patreon Tier 3+ only**; field-level queries, joins, real-time subscriptions. |

### 2.2 Rate limits

- **Free tier**: API key required (free email signup), **1,000 calls/month**.
- **Patreon Tier 3 ($10/mo)**: **75,000 calls/month** + GraphQL access,
  weather data, advanced metrics.
- Higher volume: contact maintainers directly.
- **Cloudflare sits in front regardless of tier** — bursts of simultaneous
  requests can trigger a ~10-minute block independent of the monthly quota.
  The ingestion client needs throttling/backoff even when well under quota.
- *"Tiering and call limits are subject to change"* per the CFBD blog —
  re-verify against `collegefootballdata.com/api-tiers` at implementation
  time (blocked from this sandbox).

### 2.3 API stability and completeness

- REST **v2** is GA (a major bump from v1). The `cfbd` Python client is
  **auto-generated from the OpenAPI spec** — pin the client version and add a
  contract test against a known endpoint so upstream schema changes are caught
  early rather than silently breaking the pivot logic.
- CFBD's PBP/box-score data is **largely ESPN-sourced** — gaps/errors in
  ESPN's feed (more common for FCS games, smaller conferences, older seasons)
  propagate to CFBD. This also means **CFBD and the ESPN hidden API are not
  fully independent** for cross-validation purposes.
- FBS vs. FCS: both classifications exist in the schema
  (`homeClassification`/`awayClassification`), but FCS coverage is generally
  less complete for advanced stats/PBP, especially in older seasons.
- No definitive statement on missing stat categories by position was found —
  **empirical null-rate checks per stat column, by position and season**
  (Section 5.4) are the right way to discover this.

### 2.4 Maintenance / reliability

- Run by Bill Radjewski (CollegeFootballData.com / CollegeBasketballData.com).
- Self-reported scale: **9,000+ registered users, 100M+ API calls/season,
  1,500+ Patreon supporters**.
- API server (`CFBD/cfb-api`) is **open-source, MIT-licensed**, Node/Express,
  Swagger-documented, with active CI and recent commits/PRs — not a black box.
- `cfbfastR` (SportsDataverse's R wrapper) is itself actively maintained
  (CRAN updates as recent as May 2026), a strong secondary signal of CFBD's
  continued relevance.

### 2.5 Licensing / access

- API key required for **all** tiers, including free (no credit card for free
  tier).
- A formal open-data license (CC-BY, ODbL, etc.) was **not located** —
  `collegefootballdata.com/about` returned 403 to automated fetches. The API
  server code being MIT-licensed and the project's "community resource"
  framing suggest analytics use is fine, but **a manual check of the About/ToS
  page is an open item** before any redistribution of bulk CFBD data.

---

## 3. Alternative / supplemental sources

| Source | Best use | Access | Key constraint |
|---|---|---|---|
| **Pro-Football-Reference (PFR)** | Spot-check NFL draft/combine/snap-count totals (PFR is itself the *upstream* source for several nflverse datasets) | No API; scraping or paid **Stathead** ($9/mo, web only) | Sports-Reference network limits: **20 req/min for PFR** (10/min for Stathead/FBref). 429 → up to 1hr block (bot traffic) or 5min (real-user-classified), repeat violations → 24hr IP block. ToS prohibits bulk scraping and use for training generative AI. **Manual/occasional spot-checks only** — lean on nflverse's pre-scraped PFR data for bulk needs. |
| **ESPN hidden API** (`site.api.espn.com`) | Real-time CFB scores/schedules; fallback when CFBD quota exhausted | Unauthenticated JSON GET, no key | Completely undocumented/unofficial — can change or break without notice (the Fantasy API base URL moved in April 2024, breaking integrations overnight). Shares upstream lineage with CFBD's ESPN-sourced data, so **not fully independent** for cross-validation. |
| **Sports-Reference (College Football)** | Spot-check historical NCAA team/player/recruiting stats, especially older seasons where CFBD/ESPN coverage is thinner | No API; scraping | Same Sports-Reference network rate limits/ToS as PFR — manual/occasional only. |

---

## 4. Recommended data quality validation checks

These map to `meta_ingestion_log` + lightweight schema checks described in
`docs/architecture-review.md`, Section 4 (Data Quality).

### 4.1 Row-count sanity bounds

- Define an expected per-season row-count range for each dataset based on
  known league structure:
  - NFL draft picks: ~250–262 per year since 1994 (7 rounds × 32 teams +
    variable compensatory picks — **257 in 2026**; do not hardcode 262/261 as
    a denominator, see `docs/sleeper-model-review.md` §3).
  - FBS team-seasons: ~130–135 teams/year in recent seasons.
  - Weekly datasets (snap counts, NGS, injuries): roughly
    `(games that week) × (relevant roster subset)`.
- Alert if a newly ingested season's row count falls outside ±10% of the
  prior 3-season average — catches partial scrapes, pagination bugs, or
  upstream schema changes.

### 4.2 Schema / type validation

- Pin expected column names + dtypes per dataset/version (nflverse has
  added/renamed columns between seasons, e.g. the 2022 pbp player-ID change).
  Fail loudly on unexpected new/missing/retyped columns instead of silently
  coercing.
- Pin the `cfbd` package version; add a contract test that calls a known CFBD
  endpoint and asserts the response model fields match expectations.
- Validate categorical fields (`position`, `season_type`, `game_type`,
  `classification`) against an allow-list; flag unexpected new values.

### 4.3 Primary key / duplicate detection

- Player-season tables: assert uniqueness on
  `(player_id/gsis_id, season, team[, week])`.
- `draft_picks`: assert uniqueness on `(season, round, pick)`.
- CFBD recruiting: key on `(athleteId or normalized name, recruit_year, team)`
  since not all HS recruits have a stable numeric ID pre-draft.
- Build the canonical player crosswalk on `nflverse-players` as the base,
  supplemented by CFBD `athlete_id`; validate **join coverage rate** (% of
  rows mapped) rather than assuming clean joins.

### 4.4 Null-rate thresholds on key columns

- Track null/empty rates on join keys (`gsis_id`, `pfr_id`, `espn_id`,
  `cfbd_id`/`athlete_id`, `team_abbr`) per dataset/season; set thresholds
  (e.g., <2% null for `gsis_id` in modern seasons, higher tolerance documented
  for pre-2000/rookie-year rows).
- Compute stat-column null/zero rates **conditional on position** (a global
  check would mask, e.g., a QB legitimately having zero receiving stats vs. a
  real data gap).
- For CFBD, track null rates on advanced-stat fields by season/position to
  surface the "missing stat categories by position/era" issue.

### 4.5 Cross-source reconciliation: nflverse `draft_picks` vs. CFBD `/draft/picks`

Both ultimately trace to PFR/NFL draft records via different pipelines — CFBD
additionally links each pick to a **college `athlete_id`**, making it the
crosswalk bridge. For each draft season, join on `(season, round, pick)` or
normalized `(name, position, college)` and compare:

- Player name (accounting for Jr./Sr./suffixes), college, and exact
  round/pick — a round/pick mismatch is a strong signal of an error in one
  source.
- Total pick count per season matches between sources.
- Log discrepancies to a manual-review queue rather than silently resolving —
  both sources have documented ID-quality issues.

This reconciliation also serves as the empirical resolution to the
**draft_picks start-year discrepancy** flagged in §1.1 (1980 vs. 2000):
running this check across the full nflverse history will reveal where CFBD
coverage begins and whether nflverse data before that point is usable on its
own.

### 4.6 Freshness checks

- In-season (pbp, player_stats, snap_counts, NGS, injuries, FTN charting):
  alert if the latest record's date/week lags more than ~3 days behind the
  current week (nflverse's own "Thursday is cleanest" guidance means a 2–3
  day lag is *expected*, not an error).
- Poll nflverse GitHub release `published_at`/asset `updated_at` timestamps;
  alert if a dataset hasn't updated within its documented cadence (§1.2)
  during the season.
- CFBD (live API, not static files): validate that querying the current
  season/week returns non-empty, recent results.
- Both sources need **calendar-aware, off-season exceptions** — draft_picks
  and recruiting only update around their natural annual events (April draft,
  Dec/Feb recruiting cycles), not weekly.

### 4.7 General recommendations

- **Re-ingestion is not optional**: nflverse data is occasionally revised
  retroactively (JAX 2011–2015 fix, ID-crosswalk overrides) — support
  re-ingesting and overwriting historical seasons (e.g., a periodic full
  historical refresh), not "ingest once, append forever."
- **CFBD request budget**: track a monthly call budget against the 1,000/mo
  free cap; prioritize endpoints (player season stats, recruiting, draft
  picks first); consider the $10/mo Patreon tier early if more than a couple
  of full-season pulls/month are needed.
- **Pin dependency versions**: `cfbd` client version and the exact nflverse
  release tags/asset URLs consumed, since both ecosystems evolve
  independently of this project.

---

## 5. Open items requiring manual verification

These could not be confirmed from this sandbox (network-blocked) and should
be checked by a user with unrestricted network access before the report's
specific numbers are treated as final:

1. **nflverse `draft_picks` start year**: 1980 (`nflreadr::load_draft_picks()`)
   vs. 2000 (`nfldata/DATASETS.md`) — pull the actual release CSV and check
   `min(season)`.
2. **nflverse `rosters` start year**: 2002 (Shield v2 API) vs. 2006
   (`nfldata/rosters.csv`, PFR-sourced) — pick one as canonical and document
   it in `dim_players`/ingestion code.
3. **`load_combine()` start year** — verify against the released file (docs
   don't state it explicitly; PFR's combine DB generally starts ~2000).
4. **CFBD's earliest reliable play-by-play season** — query `/plays` for
   2001, 2002, 2005, etc. and inspect row counts/completeness.
5. **CFBD's formal data-use terms** — visit
   `https://collegefootballdata.com/about` and `/api-tiers` directly in a
   browser (both 403'd to automated fetches here) and capture the licensing
   language for the project's README/legal notes.
