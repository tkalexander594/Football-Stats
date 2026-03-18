# CLAUDE.md — Football-Stats Codebase Guide

This document is intended for AI assistants (Claude, Copilot, etc.) to understand the codebase structure, conventions, and workflows before making changes.

---

## Project Overview

**Football-Stats** is a Python-based ETL (Extract, Transform, Load) data pipeline that:
1. **Extracts** NFL player and team statistics from NFL.com via web scraping
2. **Transforms** raw JSON data into Delta Lake format
3. **Loads** processed data into organized storage layers (Raw → Bronze)
4. **Audits** all pipeline executions with structured CSV logging

**Tech Stack**: Python 3, Jupyter Notebooks, Polars, Delta Lake, BeautifulSoup4, Requests
**Data Scale**: ~35.8 MB spanning 55 years (1970–2024) of NFL statistics
**No web server, no REST API, no frontend** — this is purely a local data pipeline.

---

## Repository Structure

```
Football-Stats/
├── CLAUDE.md                     # This file
├── README.md                     # Minimal project readme
├── NFL_ERD.drawio.png            # Entity-Relationship Diagram (draw.io)
├── Fantasy_Football/             # All source code
│   ├── __init__.py
│   ├── Extract/                  # Phase 1: Raw data extraction notebooks
│   │   ├── extract_player_stats.ipynb
│   │   ├── extract_team_stats.ipynb
│   │   └── archive.ipynb         # Archived/unused
│   ├── Bronze/                   # Phase 2: Transform raw → Delta Lake
│   │   ├── stage.ipynb           # Main Bronze transformation
│   │   └── receiving.ipynb       # Example category-specific transform
│   ├── Helper/                   # Web scraping utilities
│   │   ├── __init__.py
│   │   ├── helper.py             # Current scraper (ACTIVE)
│   │   └── archive1.py           # Async scraper (ARCHIVED)
│   ├── Logging/                  # Audit logging
│   │   ├── AuditLogger.py        # Current logger class (ACTIVE)
│   │   └── archive.py            # Previous logger (ARCHIVED)
│   └── Utility/                  # Data utilities
│       ├── __init__.py
│       └── utility.py            # Core transformation functions
└── Storage/                      # Data storage (gitignored large files)
    ├── Raw/                      # Phase 1 output: JSON files
    │   ├── Player_Stats/
    │   │   ├── passing/          # passing_1979.json … passing_2023.json
    │   │   ├── rushing/
    │   │   ├── receiving/
    │   │   ├── fumbles/
    │   │   ├── tackles/
    │   │   ├── interceptions/
    │   │   ├── field-goals/
    │   │   ├── kickoffs/
    │   │   ├── kickoff-returns/
    │   │   ├── punts/
    │   │   └── punt-returns/
    │   └── Team_Stats/
    │       ├── offense/
    │       ├── defense/
    │       └── special-teams/
    ├── Bronze/                   # Phase 2 output: Delta Lake tables
    │   └── player_stats/
    │       ├── passing/
    │       ├── receiving/
    │       ├── rushing/
    │       └── …
    └── Logs/
        └── audit_logs.csv        # Pipeline execution audit log
```

---

## Key Source Files

### `Fantasy_Football/Helper/helper.py`
Web scraping utility — the primary data source interface.

- `get_data(url)` — Paginates through NFL.com stat table pages. Handles `aftercursor`-based pagination. Returns `(data: list[dict], headers: list[str])`.
- `get_stats(category, year, position=None)` — Constructs the correct NFL.com URL and calls `get_data`. For player stats omit `position`; for team stats provide `position` (offense/defense/special-teams).

URL patterns used:
- Player: `https://www.nfl.com/stats/player-stats/category/{category}/{year}/reg/all/{sort_by}/desc`
- Team:   `https://www.nfl.com/stats/team-stats/{position}/{category}/{year}/reg/all`

### `Fantasy_Football/Utility/utility.py`
All data transformation and I/O utilities (~285 lines).

Key functions:
| Function | Purpose |
|---|---|
| `write_json(path, df)` | Save Polars DataFrame to JSON |
| `write_delta(path, df)` | Save Polars DataFrame as Delta Lake table |
| `write_csv(path, df)` | Save Polars DataFrame to CSV |
| `concatenate_json_files(directory_path)` | Combine all JSON files in a folder, adding a `Season` column extracted from filenames |
| `current_nfl_regular_season()` | Returns the current NFL season year as an int |
| `get_valid_player_categories(categories)` | Validates and returns only known player stat categories |
| `get_valid_team_categories(category, position)` | Validates team stat category + position combo |
| `get_player_category_stats(category)` | Maps category name → NFL.com `sort_by` parameter |
| `get_team_category_stats(category, position)` | Maps team category + position → URL slug |
| `_extract_year(filename)` | Parses year from filenames like `passing_2023.json` → `2023` |

### `Fantasy_Football/Logging/AuditLogger.py`
Singleton audit logger that appends a row to `Storage/Logs/audit_logs.csv` on each pipeline execution.

CSV columns:
```
ID, Pipeline_Name, Start_Time, End_Time, Source_System, Destination_System,
Number_of_Records, Processing_Time_Seconds, CPU_Usage_Percent, Memory_Usage_MB,
Status, Status_Message
```

Uses `fcntl` file locking for safe concurrent writes. Always instantiate via the singleton.

---

## Data Categories Reference

### Player Stats (11 categories)
`passing`, `rushing`, `receiving`, `fumbles`, `tackles`, `interceptions`,
`field-goals`, `kickoffs`, `kickoff-returns`, `punts`, `punt-returns`

### Team Stats — Offense (5 categories)
`passing`, `rushing`, `receiving`, `scoring`, `downs`

### Team Stats — Defense (8 categories)
`passing`, `rushing`, `receiving`, `scoring`, `tackles`, `downs`, `fumbles`, `interceptions`

### Team Stats — Special Teams (6 categories)
`field-goals`, `scoring`, `kickoffs`, `kickoff-returns`, `punts`, `punt-returns`

---

## Data Layer Architecture (Medallion)

```
NFL.com  →  Raw (JSON)  →  Bronze (Delta Lake)
```

| Layer | Location | Format | Description |
|---|---|---|---|
| Raw | `Storage/Raw/` | JSON files per category/year | One file per category per season, e.g. `passing_2023.json` |
| Bronze | `Storage/Bronze/` | Delta Lake tables | Typed, versioned; adds `Season: int` column |
| Logs | `Storage/Logs/` | CSV | Append-only audit log for every pipeline run |

---

## Running the Pipeline

There is no CLI or scheduler. All execution is via Jupyter notebooks.

### Step 1 — Extract (Raw)
Open and run `Fantasy_Football/Extract/extract_player_stats.ipynb`:
```python
extract_and_save_player_stats(
    categories=["passing", "rushing"],
    years=[2023, 2024],
    base_path="/path/to/Storage/Raw/Player_Stats",
    source_system="NFL.com",
    destination_system="Local Storage",
    audit_logger=audit_logger
)
```

Open and run `Fantasy_Football/Extract/extract_team_stats.ipynb`:
```python
extract_and_save_team_stats(
    categories=["passing"],
    years=[2023],
    positions=["offense", "defense"],
    base_path="/path/to/Storage/Raw/Team_Stats",
    source_system="NFL.com",
    destination_system="Local Storage",
    audit_logger=audit_logger
)
```

### Step 2 — Transform (Bronze)
Open and run `Fantasy_Football/Bronze/stage.ipynb`:
```python
write_delta(
    read_path="/path/to/Storage/Raw/Player_Stats/passing",
    write_path="/path/to/Storage/Bronze/player_stats/passing",
    mode="overwrite"
)
```

### Step 3 — Verify
Check `Storage/Logs/audit_logs.csv` for execution status of each pipeline run.

---

## Development Conventions

### Language & Style
- **Python 3** throughout; no Python 2 compatibility needed
- **snake_case** for functions and variables: `get_data()`, `write_delta()`
- **PascalCase** for classes: `AuditLogger`
- **Type hints** required on all new functions (`Union`, `Optional`, `List` from `typing`)
- **Docstrings** required for all public functions (use NumPy-style format as seen in `utility.py`)

### Data Processing
- Use **Polars** (not Pandas) for all DataFrame operations
- Use **Delta Lake** format for all Bronze-layer writes
- Always add a `Season` column (int) when reading multi-year JSON files
- File naming convention for raw data: `{category}_{year}.json` (e.g., `passing_2023.json`)

### Error Handling
- Wrap network requests in try/except; log failures to the AuditLogger
- Use validation functions (`get_valid_player_categories`, `get_valid_team_categories`) before calling scrapers
- Do not raise unhandled exceptions from notebook pipeline cells — catch and log them

### Archived Code
Files named `archive.py`, `archive1.py`, or `archive.ipynb` are **kept for reference only**. Do not modify or delete them. Do not import from them in active code.

### Paths
- The repository currently contains some hardcoded absolute paths (e.g., OneDrive paths) in older notebook cells — these are legacy artifacts. New code should use relative paths or accept `base_path` as a parameter.
- There is no `.env` file or config system; path configuration is done via notebook parameters.

### Dependencies
- No `requirements.txt` exists yet. Key packages needed in the environment:
  - `requests`, `beautifulsoup4` — scraping
  - `polars` — data processing
  - `delta-rs` (or `deltalake`) — Delta Lake write support
  - `psutil` — system metrics in AuditLogger
  - `aiohttp` — async scraping (archived but available)

---

## Testing

There is **no automated test suite**. Manual validation is done via:
1. Running notebooks end-to-end
2. Inspecting `Storage/Logs/audit_logs.csv` for `Status` and `Status_Message`
3. Spot-checking output JSON/Delta files

When adding new features, consider verifying correctness by:
- Running a single year/category extraction and checking output shape
- Confirming `Number_of_Records` in audit log matches expected row counts

---

## Git Workflow

- **Main branch**: `master`
- **Development branches**: `DEV` for active development; feature branches prefixed `claude/` for AI-assisted changes
- Commit messages are descriptive and lowercase (e.g., `updated utility import packages`)
- Data files in `Storage/` are committed alongside code (no `.gitignore` on data currently)

---

## What NOT to Do

- Do not switch from **Polars** to Pandas — the entire pipeline is built on Polars APIs
- Do not delete or rename files in `Storage/Raw/` or `Storage/Bronze/` — they are the primary data store
- Do not modify `archive.py` / `archive1.py` files — they are reference artifacts
- Do not introduce `requirements.txt` changes without confirming all deps are intentional
- Do not hardcode absolute paths; use parameters or relative paths
- Do not add a web server, REST API, or frontend unless explicitly requested
