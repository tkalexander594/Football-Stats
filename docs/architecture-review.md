# Architecture Assessment Report

This report reviews the platform architecture proposed in Appendix A
("Proposed Platform Architecture — Build Plan") against general data-platform
best practices: storage formats, partitioning, versioning, data quality,
ETL/ELT structure, caching, and model serving. It assumes the reader has
Appendix A's project structure (Section 1), schema (Section 3), ingestion
pipelines (Section 4), and analytics (Section 5) for context.

Overall assessment: **the proposed architecture is right-sized for a
single-user, local-first fantasy analytics tool.** The recommendations below
are refinements that improve data-quality observability and raw-cache
efficiency without adding operational complexity (no new services, schedulers,
or cloud dependencies).

---

## 1. Storage formats

**Appendix A as written**: raw cache under `data/raw/` (CSV/JSON from
nflverse/CFBD), normalized into DuckDB tables.

**Recommendation**: cache raw nflverse downloads as **Parquet**, not CSV,
where the source offers it.

- nflverse-data GitHub releases publish both `.csv` and `.parquet` assets for
  most datasets — `nflverse_client.py` should prefer `.parquet` URLs.
- Parquet is typed (no string-parsing of numeric columns on every load),
  columnar (faster polars reads for wide tables like `player_stats`), and
  meaningfully smaller on disk (multi-season `player_stats` CSVs are tens of
  MB; Parquet is typically 3–5x smaller).
- CFBD responses are JSON (no choice there) — cache the raw JSON response as
  retrieved (`data/raw/cfbd/<endpoint>/<year>.json`), but the **normalized**
  intermediate (post-pivot, pre-DuckDB-load) DataFrames should also be
  written as Parquet if they're persisted for debugging/replay.
- This is a low-effort change (one URL-suffix decision in
  `nflverse_client.dataset_url()`) with a real read-speed and disk-usage
  payoff, and doesn't change the DuckDB schema at all.

## 2. DuckDB vs. Delta/Iceberg

**Appendix A as written**: single-file DuckDB database
(`data/football_stats.duckdb`).

**Recommendation**: **confirmed correct for v1.** DuckDB is purpose-built for
exactly this workload — single-user, local, analytical (OLAP) queries over a
dataset that's at most low-tens-of-GB (NFL player-week stats since 1999 +
NCAA player-season stats + draft/combine/recruiting is comfortably within
DuckDB's sweet spot). It supports the polars/Arrow zero-copy interop the
ingestion and dashboard layers already rely on, and requires zero
infrastructure (no server process, no cluster).

**Delta Lake / Iceberg would only become relevant if**:
- Multiple writers need concurrent access (e.g., a scheduled ingestion job and
  an interactive dashboard writing simultaneously) — DuckDB's single-writer
  model would become a bottleneck.
- The data moves to cloud object storage (S3/GCS) and needs to be queried by
  multiple compute engines (Spark, Trino, etc.).
- Time-travel/rollback across ingestion runs becomes a hard requirement beyond
  what `meta_ingestion_log` (Section 4 below) provides.

None of these apply to a local fantasy-prep tool. Revisit only if the project
pivots to a shared/hosted multi-user deployment.

## 3. Partitioning

**Appendix A as written**: `data/raw/` cache, season-based
delete-and-replace loads into DuckDB fact tables.

**Recommendation**: confirmed — **season-based delete-and-replace is
sufficient at this data volume** (largest tables are tens of thousands of
rows per season; a full-season delete+insert in DuckDB is sub-second).
Two refinements to the *raw cache* layout (not the DuckDB schema):

- Partition the raw Parquet cache by season:
  `data/raw/nflverse/<dataset>/season=<year>/<file>.parquet`
  (and `data/raw/cfbd/<endpoint>/season=<year>/...json` for CFBD). This makes
  the re-ingestion behavior described in
  `docs/data-source-validation.md` §4.7 (nflverse occasionally revises
  historical seasons retroactively) a matter of re-downloading and replacing
  one partition directory, not the whole dataset.
- For datasets without a natural `season` column (team metadata, crosswalk
  reference data), keep a flat `data/raw/nflverse/<dataset>/<file>.parquet` —
  don't force a partition scheme where there's no partition key.

No DuckDB-side partitioning (e.g., Hive-style partitioned tables) is
warranted — DuckDB's native storage already handles tables of this size
efficiently, and adding partition columns would only complicate the season
delete-and-replace logic for no query-performance benefit at this scale.

## 4. Versioning & data quality

This is the area with the most concrete additions relative to Appendix A.

### 4.1 `meta_ingestion_log` table

Appendix A doesn't currently track *what was ingested, from where, and when*.
Add a small log table (in `sql/schema/00_dimensions.sql` or a new
`06_meta.sql`):

```sql
CREATE TABLE IF NOT EXISTS meta_ingestion_log (
    ingestion_id     BIGINT,             -- surrogate, e.g. sequence or epoch-based
    source           VARCHAR NOT NULL,    -- 'nflverse' | 'cfbd'
    dataset          VARCHAR NOT NULL,    -- e.g. 'player_stats', 'draft_picks', 'recruiting'
    season           INTEGER,             -- nullable for non-season-scoped datasets
    source_version   VARCHAR,             -- nflverse release tag, or cfbd package version + fetch date
    row_count        BIGINT,
    started_at       TIMESTAMP,
    completed_at     TIMESTAMP,
    status           VARCHAR,             -- 'success' | 'failed' | 'partial'
    notes            VARCHAR,
    PRIMARY KEY (ingestion_id)
);
```

- For nflverse: `source_version` = the GitHub release tag/asset
  `updated_at` timestamp (poll via GitHub API per
  `docs/data-source-validation.md` §4.6).
- For CFBD: `source_version` = pinned `cfbd` package version + the fetch
  timestamp (CFBD is a live API, not a versioned release).
- This single table answers "when did we last refresh X for season Y" and
  "did the last ingestion of Z succeed" — both currently unanswerable in
  Appendix A's design — and is the natural place to record the row-count
  sanity-bound checks from `docs/data-source-validation.md` §4.1.

### 4.2 Schema/data-quality checks

Appendix A's `ingest/*/normalize.py` modules should run lightweight schema
validation on normalized DataFrames **before** the DuckDB load step:

- Use **pandera** (polars-compatible) schema definitions co-located with each
  `normalize.py` — column names, dtypes, and basic value constraints (e.g.,
  `season` between 1999 and current year, `position` in an allow-list).
- On validation failure: log to `meta_ingestion_log` with `status='failed'`
  and the pandera error detail in `notes`, and **do not** proceed to the
  delete-and-replace load (avoid replacing good data with a malformed batch).
- This operationalizes the "schema/type validation" and "null-rate threshold"
  checks from `docs/data-source-validation.md` §4.2/§4.4 as code, not just
  documentation.

### 4.3 Cross-source reconciliation as a scheduled check, not a one-off

`docs/data-source-validation.md` §4.5 (nflverse `draft_picks` vs. CFBD
`/draft/picks`) should be implemented as a `football-stats validate`
CLI command that runs the reconciliation query and writes discrepancies to a
`meta_reconciliation_log` table (or simply logs warnings) — run it after every
`ingest` of draft-related data, not just once during initial build-out.

## 5. ETL/ELT structure

**Appendix A as written**: CLI-orchestrated (Typer), sequential ingestion →
crosswalk → analytics → dashboard, no scheduler.

**Recommendation**: **confirmed right-sized.** A single-user local tool that's
run on-demand (or via a simple cron/launchd job calling
`football-stats pipeline`) does not need Dagster/Airflow/Prefect — those add
a scheduler process, a metadata database, and a UI for orchestration
observability that `meta_ingestion_log` (§4.1) already provides at a fraction
of the operational cost.

**Revisit only if**: ingestion needs to run on a fixed schedule with
alerting on failure (e.g., "tell me if Tuesday's nflverse refresh didn't
happen") *and* the user wants that without manually checking
`meta_ingestion_log` — at that point a cron job that runs
`football-stats pipeline` and emails/Slacks on non-zero exit is still
sufficient; a full orchestrator remains overkill until there are multiple
interdependent scheduled pipelines with complex retry/backfill semantics.

## 6. Caching (dashboard)

**Appendix A as written**: `@st.cache_resource` for the read-only DuckDB
connection.

**Recommendation**: add `@st.cache_data` (with a TTL) on `dashboard/queries.py`
functions, not just the connection:

```python
@st.cache_data(ttl=3600)
def get_sleeper_board(_conn, **filters) -> pl.DataFrame:
    ...
```

- The connection-level cache (`@st.cache_resource`) avoids reopening the
  DuckDB file per page load; the **query-level** cache (`@st.cache_data`)
  avoids re-running the same aggregation query on every filter-widget
  interaction within a session.
- TTL should be tied to ingestion cadence, not arbitrary: since
  `football-stats pipeline` is run on-demand (not continuously), a TTL of
  ~1 hour is generous — the underlying data only changes when a pipeline run
  completes. An alternative to a TTL is invalidating the cache based on
  `meta_ingestion_log.completed_at` (pass the latest ingestion timestamp as
  part of the cache key), which is more correct than a time-based guess.

## 7. Model serving

**N/A for v1** — `sleeper_score` (Appendix A Section 5, critiqued in
`docs/sleeper-model-review.md`) is a **deterministic SQL/polars computation**
over percentile ranks and weighted sums, not a trained model. There is no
serialized model artifact, no inference endpoint, and no model-versioning
concern at this stage.

**Future path** (tracked as P3 in `docs/roadmap.md`, see
`docs/sleeper-model-review.md` §6): if/when a trained classifier (logistic
regression → gradient boosting) replaces the heuristic `sleeper_score`
formula:

- The model artifact (e.g., a pickled scikit-learn/XGBoost model or an ONNX
  export) would live under `data/models/<model_name>/<version>/`, versioned
  alongside the `meta_ingestion_log` row(s) for the training data snapshot it
  was fit on (reproducibility: "this model version was trained on data as of
  ingestion run N").
- "Serving" remains **batch, not online** — `analytics/sleeper_score.py`
  would load the model artifact and write predictions into
  `fact_sleeper_scores` exactly as the current heuristic does, so the
  dashboard/query layer (`dashboard/queries.py`) doesn't need to change at
  all when the heuristic is swapped for a trained model. This is the main
  architectural payoff of keeping `fact_sleeper_scores` as a materialized
  table rather than a view: the consuming layer is insulated from the
  scoring methodology.

---

## Summary of changes vs. Appendix A

| Area | Appendix A | This review's recommendation | Effort |
|---|---|---|---|
| Raw cache format | CSV/JSON | Parquet where source provides it (nflverse) | S |
| Raw cache layout | `data/raw/<source>/<dataset>/<file>` | add `season=<year>/` partitioning | S |
| Ingestion tracking | none | `meta_ingestion_log` table | S |
| Data quality | implicit | pandera schema checks pre-load, fail loudly | M |
| Reconciliation | one-off check | `football-stats validate` CLI command, run post-ingest | S |
| DB engine | DuckDB | confirmed, no change | – |
| Orchestration | Typer CLI | confirmed, no change | – |
| Dashboard caching | `@st.cache_resource` only | add `@st.cache_data` keyed on `meta_ingestion_log` timestamp | S |
| Model serving | N/A | future: batch-materialize predictions into `fact_sleeper_scores`, no architecture change needed now | – |

These are additive to Appendix A's Section 9 phased plan and are merged into
the prioritized roadmap in `docs/roadmap.md`.
