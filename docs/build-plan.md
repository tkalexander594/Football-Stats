# Build Plan ("Appendix A")

This is the original platform build plan — referred to as **"Appendix A"**
throughout `docs/architecture-review.md`, `docs/architecture-diagram.md`,
`docs/data-source-validation.md`, `docs/draft-strategy.md`,
`docs/sleeper-model-review.md`, and `docs/roadmap.md`. It predates those
review documents and describes the baseline architecture they critique and
extend. Section numbers below (1-9) are the `§N` references used elsewhere
(e.g. "Appendix A §3" = Section 3, "Appendix A §1" in `docs/roadmap.md`'s P0
table = Phase 1 of Section 9's phased order).

**Status**: this is the pre-implementation plan. `docs/roadmap.md` is the
authoritative, prioritized execution order — it merges this plan's Section 9
phases (as P0 items 0.1-0.9) with the additional P1-P3 items from the review
docs. Build against `docs/roadmap.md`; use this document for the detailed
design rationale (schema DDL, module responsibilities, file layout) behind
each P0 item.

## From notebook-based NFL.com scraper → DuckDB-backed fantasy/draft-prep data platform

## Context

The repo today is a half-finished, notebook-driven ETL (`Fantasy_Football/Extract`,
`Stage`, `Utility`, `Helper`, `Logging`) that scrapes NFL.com player/team stat tables
with BeautifulSoup and writes them to JSON/Delta files under a hardcoded macOS OneDrive
path. There's no dependency management, tests, or CI, and the design only covers NFL
stats (per the `NFL_ERD.drawio.png` star schema).

The user's actual goal is **fantasy football draft prep**: a queryable history of NFL
*and* NCAA player stats, plus draft/combine/recruiting data, so they can spot
"sleeper" prospects (college producers who went late in the draft or weren't highly
recruited) and review multi-year trends across teams and players at both levels.

This plan replaces the scraper with two reliable data sources, stores everything in a
local analytical database, and ships a dashboard that directly answers "who are my
sleeper picks this year." Confirmed approach (from prior discussion):
- **NFL data**: `nflverse-data` GitHub release CSVs (verified reachable; covers
  weekly/seasonal player stats, draft picks, combine, rosters back decades) — no
  scraping, no API key.
- **NCAA data**: CollegeFootballData.com (CFBD) API via the official `cfbd` Python
  package — needs a free `CFBD_API_KEY` from the user. `api.collegefootballdata.com`
  is blocked in *this* sandbox, so NCAA ingestion will be built and unit-tested with
  synthetic data here, and live-verified by the user (or CI) where network access to
  CFBD exists.
- **Storage**: DuckDB single-file database (`data/football_stats.duckdb`).
- **Reporting**: Streamlit multipage dashboard, with a "Draft Prospect / Sleeper
  Explorer" page as the v1 deliverable.

---

## 1. Project Structure

Replace `Fantasy_Football/` with an installable package at `src/football_stats/`.
Keep repo root (README, ERD, .git).

```
Football-Stats/
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore                      # data/, .env, *.duckdb, __pycache__, .venv, *.egg-info
├── NFL_ERD.drawio.png              # kept as historical reference
├── data/
│   ├── raw/                        # cached CSV/JSON from nflverse + CFBD (gitignored)
│   └── football_stats.duckdb       # gitignored
├── sql/
│   ├── schema/
│   │   ├── 00_dimensions.sql
│   │   ├── 01_nfl_facts.sql
│   │   ├── 02_ncaa_facts.sql
│   │   ├── 03_draft_combine_recruiting.sql
│   │   ├── 04_crosswalk.sql
│   │   └── 05_views_analytics.sql
│   └── seed/
│       └── nfl_teams.csv           # 32 teams + conference/division
├── src/football_stats/
│   ├── __init__.py
│   ├── config.py                   # pydantic-settings Settings
│   ├── db/
│   │   ├── connection.py           # get_connection() context manager
│   │   └── schema.py               # apply_schema(conn) runs sql/schema/*.sql
│   ├── ingest/
│   │   ├── common.py               # download/cache + DuckDB Arrow insert helpers
│   │   ├── nfl/
│   │   │   ├── nflverse_client.py  # dataset URLs, download+cache
│   │   │   ├── normalize.py        # column renames/casts, season aggregation
│   │   │   └── load.py             # load_* -> DuckDB tables
│   │   └── ncaa/
│   │       ├── cfbd_client.py      # cfbd.ApiClient wrapper, defensive on missing key
│   │       ├── normalize.py        # STAT_COLUMN_MAP pivot long->wide
│   │       └── load.py
│   ├── transform/
│   │   ├── seasons.py              # ported get_current_year/current_nfl_regular_season/ensure_iterable
│   │   └── crosswalk.py            # build_player_crosswalk(conn)
│   ├── analytics/
│   │   └── sleeper_score.py        # build_sleeper_scores(conn) -> fact_sleeper_scores
│   ├── dashboard/
│   │   ├── app.py                  # Streamlit entrypoint, cached read-only connection
│   │   ├── queries.py              # all dashboard SQL as functions returning pl.DataFrame
│   │   └── pages/
│   │       ├── 1_Draft_Prospect_Explorer.py   # MVP - full build
│   │       ├── 2_Player_Career_Search.py      # stub w/ working basic query
│   │       ├── 3_Team_Stat_Browser.py         # stub
│   │       └── 4_Trend_Comparisons.py         # stub
│   └── cli/
│       └── main.py                 # Typer app: init-db, ingest, build-crosswalk, build-sleeper-scores, dashboard, pipeline
└── tests/
    ├── conftest.py                 # tmp/in-memory duckdb fixture w/ schema applied
    ├── test_schema.py
    ├── test_config.py
    ├── ingest/
    │   ├── test_nfl_normalize.py
    │   └── test_ncaa_normalize.py  # synthetic data, no network
    └── transform/
        ├── test_crosswalk.py
        └── test_sleeper_score.py
```

### `pyproject.toml`
```toml
[project]
name = "football-stats"
version = "0.1.0"
description = "Fantasy football & draft-prep data platform (NFL + NCAA)"
requires-python = ">=3.11"
dependencies = [
    "polars>=1.20",
    "duckdb>=1.1",
    "pyarrow>=16.0",
    "requests>=2.31",
    "cfbd>=5.14",
    "streamlit>=1.38",
    "typer>=0.12",
    "pydantic-settings>=2.4",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov", "ruff>=0.6"]

[project.scripts]
football-stats = "football_stats.cli.main:app"

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py311"
[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["live: requires network/API key"]
```
Plain pip + pyproject (editable install `pip install -e ".[dev]"`). Drop
`beautifulsoup4`/`psutil` (no longer needed).

---

## 2. Configuration (`src/football_stats/config.py`)

`pydantic-settings.BaseSettings` reading `.env` at repo root:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    data_dir: Path = Path("data")
    raw_dir: Path | None = None
    db_path: Path | None = None
    cfbd_api_key: str | None = None
    default_start_year: int = 2010
    default_end_year: int | None = None

    @property
    def raw_path(self) -> Path: return self.raw_dir or (self.data_dir / "raw")
    @property
    def database_path(self) -> Path: return self.db_path or (self.data_dir / "football_stats.duckdb")
```

`.env.example` (committed): `CFBD_API_KEY=`, `DATA_DIR=data`, `DB_PATH=data/football_stats.duckdb`.

`transform/seasons.py` carries forward `get_current_year`, `current_nfl_regular_season`,
`ensure_iterable` from the old `Utility/utility.py` as typed pure functions.

CFBD client is built **lazily** in `cfbd_client.py` — importing the module never
requires a key; only an actual API call without `CFBD_API_KEY` raises `RuntimeError`.

---

## 3. Database Schema (DuckDB)

`apply_schema(conn)` runs `sql/schema/*.sql` in numeric order, all `CREATE TABLE IF
NOT EXISTS` (idempotent, safe on every CLI run).

### Design decisions
- **One wide fact table per stat domain** (not per the old 11 NFL.com categories) —
  matches nflverse's natural wide-CSV shape and avoids redundant joins for "show me a
  player's season line."
- **`season` column on every fact table** for multi-year history; loads are
  delete-by-season + insert, in a transaction.
- **Keys**: natural source IDs where stable (`gsis_id` for NFL, `cfbd_id` for NCAA);
  a surrogate `player_id` (= `gsis_id` if known, else `'ncaa_' || cfbd_id`) is the
  crosswalk's unifying key.

### 3.1 `00_dimensions.sql`
```sql
CREATE TABLE IF NOT EXISTS dim_players (
    player_id     VARCHAR PRIMARY KEY,
    gsis_id       VARCHAR, pfr_id VARCHAR, cfbd_id VARCHAR, espn_id VARCHAR,
    full_name     VARCHAR, first_name VARCHAR, last_name VARCHAR,
    position      VARCHAR, birth_date DATE, height_in INTEGER, weight_lb INTEGER,
    college       VARCHAR,
    draft_year INTEGER, draft_team VARCHAR, draft_round INTEGER, draft_pick INTEGER,
    entry_year    INTEGER,
    last_updated  TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS dim_nfl_teams (
    team_abbr VARCHAR PRIMARY KEY, team_name VARCHAR,
    team_conference VARCHAR, team_division VARCHAR
);

CREATE TABLE IF NOT EXISTS dim_college_teams (
    school VARCHAR PRIMARY KEY, conference VARCHAR, division VARCHAR,
    color VARCHAR, alt_color VARCHAR, logo_url VARCHAR
);

CREATE TABLE IF NOT EXISTS dim_seasons (
    season INTEGER PRIMARY KEY, season_label VARCHAR
);
```

### 3.2 `01_nfl_facts.sql` (nflverse)
```sql
CREATE TABLE IF NOT EXISTS fact_nfl_player_week_offense (
    player_id VARCHAR, gsis_id VARCHAR, season INTEGER, week INTEGER, season_type VARCHAR,
    team VARCHAR, opponent_team VARCHAR, position VARCHAR,
    completions INTEGER, attempts INTEGER, passing_yards DOUBLE, passing_tds INTEGER,
    interceptions INTEGER, sacks DOUBLE, sack_yards DOUBLE, passing_air_yards DOUBLE, passing_epa DOUBLE,
    carries INTEGER, rushing_yards DOUBLE, rushing_tds INTEGER, rushing_epa DOUBLE, rushing_fumbles INTEGER,
    receptions INTEGER, targets INTEGER, receiving_yards DOUBLE, receiving_tds INTEGER,
    receiving_air_yards DOUBLE, receiving_yards_after_catch DOUBLE, receiving_epa DOUBLE,
    fantasy_points DOUBLE, fantasy_points_ppr DOUBLE,
    PRIMARY KEY (player_id, season, week, season_type)
);

CREATE TABLE IF NOT EXISTS fact_nfl_player_season_offense (
    player_id VARCHAR, gsis_id VARCHAR, season INTEGER, team VARCHAR, position VARCHAR, games INTEGER,
    completions INTEGER, attempts INTEGER, passing_yards DOUBLE, passing_tds INTEGER,
    interceptions INTEGER, sacks DOUBLE,
    carries INTEGER, rushing_yards DOUBLE, rushing_tds INTEGER,
    receptions INTEGER, targets INTEGER, receiving_yards DOUBLE, receiving_tds INTEGER,
    fantasy_points DOUBLE, fantasy_points_ppr DOUBLE,
    PRIMARY KEY (player_id, season)
);

CREATE TABLE IF NOT EXISTS fact_nfl_player_week_defense (
    player_id VARCHAR, gsis_id VARCHAR, season INTEGER, week INTEGER, season_type VARCHAR,
    team VARCHAR, opponent_team VARCHAR, position VARCHAR,
    def_tackles_solo DOUBLE, def_tackles_with_assist DOUBLE, def_tackle_assists DOUBLE,
    def_sacks DOUBLE, def_sack_yards DOUBLE, def_qb_hits INTEGER,
    def_interceptions INTEGER, def_pass_defended INTEGER, def_tds INTEGER,
    def_fumbles_forced INTEGER, def_safety INTEGER,
    PRIMARY KEY (player_id, season, week, season_type)
);

CREATE TABLE IF NOT EXISTS fact_nfl_player_season_defense (
    player_id VARCHAR, gsis_id VARCHAR, season INTEGER, team VARCHAR, position VARCHAR, games INTEGER,
    def_tackles_solo DOUBLE, def_sacks DOUBLE, def_interceptions INTEGER,
    def_pass_defended INTEGER, def_tds INTEGER, def_fumbles_forced INTEGER,
    PRIMARY KEY (player_id, season)
);

CREATE TABLE IF NOT EXISTS fact_nfl_player_season_kicking (
    player_id VARCHAR, gsis_id VARCHAR, season INTEGER, team VARCHAR, position VARCHAR, games INTEGER,
    fg_made INTEGER, fg_att INTEGER, fg_pct DOUBLE, pat_made INTEGER, pat_att INTEGER,
    PRIMARY KEY (player_id, season)
);
```

### 3.3 `02_ncaa_facts.sql` (CFBD)
```sql
CREATE TABLE IF NOT EXISTS fact_ncaa_player_season_passing (
    player_id VARCHAR, cfbd_id VARCHAR, season INTEGER, team VARCHAR, conference VARCHAR,
    position VARCHAR, games INTEGER,
    completions DOUBLE, attempts DOUBLE, pass_yards DOUBLE, pass_tds DOUBLE, interceptions DOUBLE, ypa DOUBLE,
    PRIMARY KEY (player_id, season, team)
);

CREATE TABLE IF NOT EXISTS fact_ncaa_player_season_rushing (
    player_id VARCHAR, cfbd_id VARCHAR, season INTEGER, team VARCHAR, conference VARCHAR,
    position VARCHAR, games INTEGER,
    carries DOUBLE, rush_yards DOUBLE, rush_tds DOUBLE, ypc DOUBLE,
    PRIMARY KEY (player_id, season, team)
);

CREATE TABLE IF NOT EXISTS fact_ncaa_player_season_receiving (
    player_id VARCHAR, cfbd_id VARCHAR, season INTEGER, team VARCHAR, conference VARCHAR,
    position VARCHAR, games INTEGER,
    receptions DOUBLE, rec_yards DOUBLE, rec_tds DOUBLE, ypr DOUBLE,
    PRIMARY KEY (player_id, season, team)
);

CREATE TABLE IF NOT EXISTS fact_ncaa_player_season_defense (
    player_id VARCHAR, cfbd_id VARCHAR, season INTEGER, team VARCHAR, conference VARCHAR,
    position VARCHAR, games INTEGER,
    tackles DOUBLE, sacks DOUBLE, interceptions DOUBLE, pass_breakups DOUBLE, tfl DOUBLE,
    PRIMARY KEY (player_id, season, team)
);

CREATE TABLE IF NOT EXISTS fact_ncaa_team_season_stats (
    team VARCHAR, season INTEGER, conference VARCHAR, stat_name VARCHAR, stat_value DOUBLE,
    PRIMARY KEY (team, season, stat_name)
);

CREATE TABLE IF NOT EXISTS fact_ncaa_team_season_games (
    team VARCHAR, season INTEGER, games INTEGER, PRIMARY KEY (team, season)
);
```
CFBD's `get_player_season_stats` returns long/EAV records
(`{player, team, conference, category, statType, stat, season}`). `ingest/ncaa/normalize.py`
pivots these into the four wide tables above via a `STAT_COLUMN_MAP` dict, e.g.
`("passing","YDS") -> "pass_yards"`, `("rushing","CAR") -> "carries"`,
`("defensive","TFL") -> "tfl"`, etc. Unknown `(category, statType)` pairs are logged
and skipped, never raise.

### 3.4 `03_draft_combine_recruiting.sql`
```sql
CREATE TABLE IF NOT EXISTS fact_draft_picks (
    season INTEGER, draft_round INTEGER, draft_pick INTEGER, draft_team VARCHAR,
    player_name VARCHAR, position VARCHAR, college VARCHAR,
    gsis_id VARCHAR, pfr_id VARCHAR, cfbd_id VARCHAR,
    height_in INTEGER, weight_lb INTEGER, forty_yard DOUBLE, bench_press INTEGER,
    vertical_in DOUBLE, broad_jump_in DOUBLE, cone_drill DOUBLE, shuttle_run DOUBLE,
    PRIMARY KEY (season, draft_pick)
);

CREATE TABLE IF NOT EXISTS fact_combine_results (
    season INTEGER, player_name VARCHAR, position VARCHAR, school VARCHAR, pfr_id VARCHAR,
    height_in INTEGER, weight_lb INTEGER, forty_yard DOUBLE, bench_press INTEGER,
    vertical_in DOUBLE, broad_jump_in DOUBLE, cone_drill DOUBLE, shuttle_run DOUBLE,
    PRIMARY KEY (season, player_name, position, school)
);

CREATE TABLE IF NOT EXISTS fact_recruiting_rankings (
    recruit_year INTEGER, cfbd_id VARCHAR, name VARCHAR, position VARCHAR,
    height_in INTEGER, weight_lb INTEGER, stars INTEGER, rating DOUBLE, ranking INTEGER,
    committed_school VARCHAR, hometown_state VARCHAR,
    PRIMARY KEY (recruit_year, cfbd_id)
);
```
`fact_draft_picks` is sourced from nflverse's `draft_picks.csv` (already has
`cfb_id`/`pfr_id`/`gsis_id` together — ideal for the crosswalk). CFBD's `/draft/picks`
is **not** separately ingested in v1 (redundant, avoids reconciling two draft tables).

### 3.5 `04_crosswalk.sql`
```sql
CREATE TABLE IF NOT EXISTS bridge_player_crosswalk (
    player_id VARCHAR PRIMARY KEY,
    gsis_id VARCHAR, pfr_id VARCHAR, cfbd_id VARCHAR,
    full_name VARCHAR, position VARCHAR, college VARCHAR, draft_year INTEGER,
    match_method VARCHAR,      -- 'draft_picks_exact' | 'name_college_position' | 'unmatched_ncaa' | 'unmatched_nfl'
    match_confidence DOUBLE
);
```
**Matching strategy** (`transform/crosswalk.py:build_player_crosswalk`):
1. **Tier 1 (exact, conf 1.0)**: every `fact_draft_picks` row with `cfbd_id IS NOT NULL`
   → `player_id = gsis_id`, `match_method='draft_picks_exact'`.
2. **Tier 2 (fuzzy, conf ~0.7)**: unmatched NCAA players joined to draft picks on
   `(normalize_name(name), college, position)` — `normalize_name` strips Jr./Sr./III,
   punctuation, lowercases. `match_method='name_college_position'`.
3. **Tier 3**: remaining NCAA-only players → `player_id='ncaa_'||cfbd_id`,
   `match_method='unmatched_ncaa'`, `gsis_id=NULL` (still queryable for college-only
   prospect analysis).
4. Remaining NFL-only players (UDFAs, pre-CFBD era) → `player_id=gsis_id`,
   `match_method='unmatched_nfl'`.

After building the crosswalk, `dim_players` is upserted from it + `fact_draft_picks`
+ `fact_combine_results` + CFBD roster data. `match_method`/`match_confidence` stay
queryable so the dashboard can flag fuzzy matches if needed.

### 3.6 `05_views_analytics.sql`
Defines `fact_sleeper_scores` (real table, rebuilt by `analytics/sleeper_score.py` —
see Section 5).

---

## 4. Ingestion Pipelines

### 4.1 NFL (`ingest/nfl/`)
- **`nflverse_client.py`**: `NFLVERSE_RELEASE_BASE = "https://github.com/nflverse/nflverse-data/releases/download"`;
  `dataset_url(dataset, file=None)` builds e.g. `.../player_stats/player_stats.csv`,
  `.../draft_picks/draft_picks.csv`, `.../combine/combine.csv`. `download_dataset(dataset, cache_dir, force=False)`
  streams to `data/raw/nflverse/<dataset>/<file>.csv`, skip if cached. v1 datasets:
  `player_stats`, `player_stats_def`, `draft_picks`, `combine`, `rosters_seasonal`.
- **`normalize.py`**: `normalize_player_stats(df, season_filter)` (rename
  `recent_team`→`team`, derive `player_id`), `normalize_draft_picks(df)` (rename
  `cfb_id`→`cfbd_id`, parse `ht` "6-2"→`height_in`, `draft_ovr`→`draft_pick`),
  `normalize_combine(df)`, `aggregate_weekly_to_season(df, group_cols, sum_cols)`.
- **`load.py`**: `load_player_week_offense/defense`, `load_player_season_offense/
  defense/kicking`, `load_draft_picks`, `load_combine_results`, `load_dim_nfl_teams`
  (from `sql/seed/nfl_teams.csv`). Each does delete-by-season + Arrow-register insert
  in a transaction. `run_nfl_ingestion(conn, settings, start_year, end_year)`
  orchestrates all of the above.

### 4.2 NCAA (`ingest/ncaa/`)
- **`cfbd_client.py`**: `get_cfbd_configuration(settings)` sets
  `cfbd.Configuration(access_token=settings.cfbd_api_key)`, raises `RuntimeError` only
  when called without a key. `cfbd_api_client(settings)` context manager. Thin
  wrappers: `fetch_fbs_teams`, `fetch_player_season_stats`, `fetch_recruiting`,
  `fetch_roster`, `fetch_team_stats` — each catches `cfbd.exceptions.ApiException` and
  re-raises as `CFBDIngestError` with year/endpoint context. Cache raw responses to
  `data/raw/cfbd/<endpoint>/<year>.json`.
- **`normalize.py`**: `pivot_player_season_stats(records, season) -> dict[str, pl.DataFrame]`
  (keys `passing`/`rushing`/`receiving`/`defense`) using `STAT_COLUMN_MAP`;
  `normalize_recruiting`, `normalize_roster`, `cfbd_id_from_player`.
- **`load.py`**: `load_ncaa_player_season_stats`, `load_recruiting_rankings`,
  `load_dim_college_teams`, `load_ncaa_team_season_stats`.
  `run_ncaa_ingestion(conn, settings, start_year, end_year)` — per year: FBS teams →
  player season stats → recruiting → rosters; each year wrapped in try/except logging
  failures and continuing.

### 4.3 CLI (`cli/main.py`, Typer)
```
football-stats init-db
football-stats ingest nfl --start-year YYYY --end-year YYYY [--force]
football-stats ingest ncaa --start-year YYYY --end-year YYYY [--force]
football-stats build-crosswalk
football-stats build-sleeper-scores
football-stats dashboard            # subprocess: streamlit run dashboard/app.py
football-stats pipeline --start-year YYYY --end-year YYYY   # runs all of the above
```
Standard `logging` to stdout (optionally `data/logs/`) replaces the old hardcoded
OneDrive CSV audit log.

---

## 5. Analytics / Sleeper Scoring

`analytics/sleeper_score.py:build_sleeper_scores(conn)` builds `fact_sleeper_scores`
(one row per draft-eligible/recently-drafted player), reading via `conn.sql(...).pl()`
and joining: final-season `fact_ncaa_player_season_*`, `fact_ncaa_team_season_stats`
(market share denominators), `fact_recruiting_rankings`, `fact_draft_picks` +
`fact_combine_results`, `dim_players`.

```sql
CREATE TABLE IF NOT EXISTS fact_sleeper_scores (
    player_id VARCHAR PRIMARY KEY, full_name VARCHAR, position VARCHAR, college VARCHAR,
    draft_year INTEGER, draft_round INTEGER, draft_pick INTEGER,
    final_season INTEGER, yards_per_game DOUBLE, tds_per_game DOUBLE, receptions_per_game DOUBLE,
    yards_market_share DOUBLE, td_market_share DOUBLE,
    hs_stars INTEGER, hs_rating DOUBLE,
    forty_pctile DOUBLE, vertical_pctile DOUBLE, agility_pctile DOUBLE, athleticism_score DOUBLE,
    draft_capital_score DOUBLE, production_score DOUBLE,
    sleeper_score DOUBLE, breakout_age DOUBLE
);
```

Composite formula (documented constants, tunable later):
```
production_score    = percentile_rank(yards_market_share + td_market_share, within position group)
athleticism_score   = mean(non-null forty_pctile, vertical_pctile, agility_pctile)
draft_capital_score = 100 if undrafted else 100 * (1 - (draft_pick-1)/261)
sleeper_score = 0.45*production_score + 0.20*athleticism_score
              + 0.20*(100 - draft_capital_score) + 0.15*recruiting_inverse_score
```
Rewards players who produced in college but had low draft capital/recruiting hype
(likely undervalued). Percentiles computed within `(position, draft_year)` via polars
`.rank(method="average").over(["position","draft_year"])`. Exposed via
`football-stats build-sleeper-scores`, re-run after every ingestion + crosswalk build.

> **Note**: this formula is the one critiqued in `docs/sleeper-model-review.md` —
> the `draft_pick capped at 261` denominator and the flat 0.45/0.20/0.20/0.15
> weighting are both flagged for replacement (P2 items 2.8-2.10 in
> `docs/roadmap.md`). It remains the v1 baseline implementation.

---

## 6. Streamlit Dashboard

`dashboard/app.py`: `st.set_page_config`, landing page with DB stats (row counts,
`MAX(last_updated)`). Multipage via `dashboard/pages/`. `dashboard/queries.py`
centralizes all SQL as functions returning `pl.DataFrame` (pages stay UI-only,
queries unit-testable). Cached read-only connection via
`@st.cache_resource def get_conn(): return duckdb.connect(str(settings.database_path), read_only=True)`.

- **Page 1 (MVP — full build)**: `1_Draft_Prospect_Explorer.py` "Sleeper Explorer".
  Sidebar filters: draft class year(s), position(s), min `sleeper_score`, conference.
  Sortable table from `fact_sleeper_scores` ⋈ `dim_players` (name, position, college,
  draft year/round/pick, yards/TDs per game, market share, athleticism, sleeper
  score), default sorted by `sleeper_score` desc. Detail panel: select a player →
  college season-by-season line chart (`fact_ncaa_player_season_*` across years) +
  combine numbers + recruiting stars. Backed by `queries.get_sleeper_board(conn, **filters)`.
- **Page 2 (stub w/ working query)**: `2_Player_Career_Search.py` — name search
  (`dim_players.full_name ILIKE`), unified college→NFL season timeline via
  crosswalk `player_id`.
- **Page 3 (stub)**: `3_Team_Stat_Browser.py` — NFL/NCAA toggle, team/season
  aggregates, top players bar chart.
- **Page 4 (stub)**: `4_Trend_Comparisons.py` — multi-player line chart of a chosen
  metric across seasons with a draft-year marker.

---

## 7. Migration / Cleanup

- **Delete** `Fantasy_Football/` entirely (Archive/, Extract/extract.ipynb,
  Stage/stage.ipynb, Helper/helpers.py, Utility/utility.py, Logging/logs.py, all
  `__init__.py`s) once equivalents exist:
  - `current_nfl_regular_season`/`get_current_year`/`ensure_iterable` → `transform/seasons.py`
  - `write_json`/`write_delta`/`write_csv` → superseded by DuckDB loads (no Delta Lake dep)
  - category/sort_by maps → superseded by `STAT_COLUMN_MAP` (NFL.com scraping gone)
  - hardcoded OneDrive CSV audit log → standard `logging`, configurable via `Settings`
- **`NFL_ERD.drawio.png`**: keep as historical reference; new `README.md` points to
  `sql/schema/*.sql` as the source of truth (old ERD only covers NFL-only schema).
- **`README.md`**: rewrite — overview, setup (`pip install -e ".[dev]"`, copy
  `.env.example`→`.env`, set `CFBD_API_KEY`), CLI usage (`football-stats pipeline
  --start-year 2015 --end-year 2025`, `football-stats dashboard`), and an explicit
  note that NCAA ingestion needs network access to `api.collegefootballdata.com` not
  available in this sandbox.
- **`.gitignore`**: `data/`, `.env`, `*.duckdb`, `__pycache__/`, `.venv/`, `*.egg-info/`.

---

## 8. Testing & CI

- `tests/conftest.py`: in-memory/tmp DuckDB fixture with `apply_schema(conn)` applied;
  small synthetic polars DataFrames mimicking nflverse/CFBD shapes.
- `tests/test_schema.py`: all expected tables exist after `apply_schema`; applying
  twice doesn't error.
- `tests/ingest/test_nfl_normalize.py`: height/weight parsing (`"6-2"`→74),
  `player_id` derivation, weekly→season aggregation correctness.
- `tests/ingest/test_ncaa_normalize.py`: pivot of long-format CFBD records → wide
  passing/rushing/etc DataFrames; unknown stat types skipped gracefully. Pure
  synthetic data, no network.
- `tests/transform/test_crosswalk.py`: tiny in-memory DB with sample draft_picks +
  ncaa season rows → assert Tier 1/2/3 classification and `player_id` formats.
- `tests/transform/test_sleeper_score.py`: minimal fixture draft class → assert
  higher production + lower draft capital ⇒ higher `sleeper_score`.
- Live CFBD-dependent tests go in `tests/ingest/test_ncaa_client_live.py`, marked
  `@pytest.mark.skipif(not os.environ.get("CFBD_API_KEY"), ...)`.
- `.github/workflows/ci.yml`: `lint-test` job (ruff + `pytest -m "not live"`) always
  runs; `live-tests` job runs `pytest -m live` only `if: secrets.CFBD_API_KEY != ''`.

---

## 9. Phased Implementation Order

0. **Scaffolding**: `pyproject.toml`, `.env.example`, `.gitignore`, package skeleton,
   `config.py`; `pip install -e ".[dev]"`.
1. **DB layer**: all `sql/schema/*.sql`, `db/connection.py`, `db/schema.py`,
   `tests/conftest.py` + `test_schema.py` (run pytest), `sql/seed/nfl_teams.csv` + loader.
2. **NFL ingestion**: `ingest/common.py`, `ingest/nfl/{nflverse_client,normalize,load}.py`
   + tests; wire `football-stats ingest nfl`; smoke-test against real nflverse URLs
   for 1-2 recent seasons and verify row counts.
3. **NCAA ingestion**: `ingest/ncaa/{cfbd_client,normalize,load}.py` + synthetic-data
   tests; wire `football-stats ingest ncaa` (live run requires `CFBD_API_KEY` +
   network not available here — document in README).
4. **Crosswalk**: `transform/seasons.py` (+ tests), `transform/crosswalk.py` (+ tests
   with synthetic data); wire `football-stats build-crosswalk`, populate `dim_players`.
5. **Analytics**: `analytics/sleeper_score.py` (+ tests); wire
   `football-stats build-sleeper-scores`; add composite `football-stats pipeline`.
6. **Dashboard**: `dashboard/queries.py`, `dashboard/app.py`, Page 1 full MVP, Pages
   2-4 stubs; wire `football-stats dashboard`.
7. **Cleanup & docs**: delete `Fantasy_Football/`, rewrite `README.md`, run
   `ruff check .` and `pytest`, confirm `football-stats init-db` and
   `build-sleeper-scores` run end-to-end on whatever data is loadable in-sandbox
   (nflverse-only, since CFBD is blocked here).
8. **CI**: `.github/workflows/ci.yml`.

---

## Verification

- `pip install -e ".[dev]"` succeeds; `football-stats --help` shows all commands.
- `pytest` passes (schema, normalize, crosswalk, sleeper-score tests) with
  `-m "not live"`.
- `ruff check .` clean.
- `football-stats init-db` creates `data/football_stats.duckdb` with all tables
  (verify via `duckdb` CLI or a quick `information_schema.tables` query).
- `football-stats ingest nfl --start-year 2022 --end-year 2024` pulls real nflverse
  CSVs (reachable from this sandbox) and populates `fact_nfl_player_*`,
  `fact_draft_picks`, `fact_combine_results` — verify row counts > 0.
- `football-stats build-crosswalk` and `build-sleeper-scores` run without error on
  the NFL-only data loaded so far (NCAA tables empty in-sandbox is expected/handled).
- `football-stats dashboard` launches Streamlit; Page 1 renders (with whatever data
  is present) without exceptions.
- README documents that full NCAA ingestion + a populated Sleeper Explorer requires
  the user to run `football-stats ingest ncaa ...` with `CFBD_API_KEY` set in an
  environment with access to `api.collegefootballdata.com`.

## Critical Files
- `/home/user/Football-Stats/pyproject.toml`
- `/home/user/Football-Stats/sql/schema/*.sql`
- `/home/user/Football-Stats/src/football_stats/db/schema.py`
- `/home/user/Football-Stats/src/football_stats/ingest/nfl/load.py`
- `/home/user/Football-Stats/src/football_stats/ingest/ncaa/normalize.py`
- `/home/user/Football-Stats/src/football_stats/transform/crosswalk.py`
- `/home/user/Football-Stats/src/football_stats/analytics/sleeper_score.py`
- `/home/user/Football-Stats/src/football_stats/dashboard/pages/1_Draft_Prospect_Explorer.py`
- `/home/user/Football-Stats/src/football_stats/cli/main.py`
