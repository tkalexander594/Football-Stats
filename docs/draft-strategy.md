# Draft Strategy Enhancement Recommendations

This document proposes a draft-strategy engine layered on top of the
nflverse/CFBD data model from Appendix A: round-by-round value rankings,
positional scarcity, ADP-based sleeper/bust detection, league-format handling
(Standard/PPR/Half-PPR), and a Dynasty/Keeper valuation layer. All proposals
are designed to be computed as SQL/polars transformations against existing
`fact_nfl_player_season_*` tables (which already carry `fantasy_points` and
`fantasy_points_ppr` per nflverse convention) plus the player crosswalk.

---

## 1. Value-Based Drafting (VBD) / Value Over Replacement Player (VORP)

### Methodology

VBD assigns every player a value by comparing their projected fantasy points
to a **replacement-level baseline at the same position** — raw point totals
aren't comparable across positions (a 350-point QB isn't "more valuable" than
a 220-point RB in isolation), but `points − positional baseline` is.

`Player Value = Projected Points − Baseline Player's Projected Points`

Baseline variants differ only in *which player* defines the baseline:

- **VORP (Value Over Replacement Player)** — baseline = best available
  free-agent/waiver player at the position (the first player *not* drafted).
- **VOLS (Value Over Last Starter)** — baseline = the worst *starter* given
  league roster requirements (e.g., QB12 in a 12-team 1-QB league).
- **VONA (Value Over Next Available)** — baseline = the next player at that
  position likely to still be available at your *next* pick; a live-draft,
  dynamic comparison rather than a static pre-draft number.
- **BEER / "man-games"** — refinements that account for bye weeks, injury
  risk, and realistic usable starts over a season rather than a single
  season-total projection.

### Replacement-level baselines (12-team standard roster)

`Baseline rank at position = starters_per_team × num_teams`, with shared FLEX
slots apportioned across RB/WR/TE by usage rate:

| Position | Starters/team | Baseline rank (12-team) |
|---|---|---|
| QB | 1 | QB12 |
| RB | 2 (+ flex share) | RB24 (often RB28–30 w/ flex) |
| WR | 3 (+ flex share) | WR36 (often WR40+ w/ flex) |
| TE | 1 (+ flex share) | TE12 (often TE14–15 w/ flex) |
| K | 1 | K12 |
| DST | 1 | DST12 |

Flex slots are typically apportioned ~60% RB / ~35% WR / ~5% TE in standard
scoring, shifting toward WR in PPR.

### Positional scarcity

Scarcity = how steeply points drop from the elite tier to the replacement
baseline at a position. In 12-team PPR, the RB1→RB24 gap is commonly 100+
points vs. ~60 points for QB1→QB12 — the quantitative basis for prioritizing
RB early. VBD captures this *automatically*: a steep elite-to-replacement
slope produces large VBD scores for that position's top players, naturally
elevating them in the cross-positional ranking without manual position
weights.

**Caveat**: 2025 commentary argues the classic scarcity premise has weakened
as the player pool flattens (especially at RB, due to committee backfields).
Treat VBD as a *starting point and tiering tool*, not an absolute truth —
it still produces useful relative rankings even if the absolute gaps have
narrowed.

### From VBD to tiers and round-by-round targets

1. Compute VBD score for every player (`projected_points − positional baseline`).
2. Sort all players into one cross-positional list (the "big board").
3. Detect **tiers**: natural breakpoints/cliffs in the sorted VBD list — gap
   detection or std-dev-based breakpoints over `vorp_score` partitioned by
   position.
4. **Round-by-round targets**: map tiers to draft rounds via a snake-draft
   turn calculation — if Tier 2 RBs run out before your next pick, prioritize
   the last Tier-2 RB now rather than reaching elsewhere (this is VONA logic
   layered on top of static VOLS/VBD tiers).

---

## 2. ADP-based value identification

### "ADP vs. VORP" delta

Rank players two ways — by **projected VORP/VBD** (internal ranking) and by
**market ADP** (where the field actually drafts them) — and take the delta:

```
value_score = adp_rank - vorp_rank
```

- **Positive** (ADP rank worse/higher number than VORP rank) → **sleeper /
  value**: the market is undervaluing this player relative to projection.
- **Negative** → **bust / reach**: the market is overpaying relative to
  projection.

Important framing: *"A sleeper is not a prediction; it's an underpriced
asset, and a bust is not a disappointment; it's an overpriced asset."* If a
sleeper's ADP catches up to its true value before your pick, the edge is
gone — ADP-delta is most valuable as a **live, continuously-refreshed signal
during a draft**, not just a static pre-draft list.

### ADP data sources

| Source | Access | Notes |
|---|---|---|
| **Fantasy Football Calculator** | Free REST API, JSON, explicitly licensed for personal/commercial reuse. `GET /api/v1/adp/{format}?teams=12&year=YYYY`, formats include `standard`, `ppr`, `half-ppr`, `2qb`, `dynasty`. | **Recommended primary source** — lowest friction, ToS-clean, covers the formats this platform needs. |
| **Sleeper API** | Public, unauthenticated, ~90 req/min/IP. | No dedicated published "ADP" endpoint confirmed; ADP would need to be derived by aggregating real draft picks from Sleeper's draft endpoints. Good secondary/validation source for "real user" drafts. |
| **FantasyPros** | Real-Time ADP / consensus ADP pages exist (industry "gold standard," aggregated across ESPN/Yahoo/Sleeper/CBS) | No confirmed free public API; pages returned 403 to automated fetch in research, suggesting bot-blocking — likely requires a paid tier or manual export. |
| **Fantasy Nerds API** | Has an explicit ADP-by-format-and-league-size endpoint, appears to require an API key (freemium). | Secondary option if FFC coverage is insufficient. |
| **ESPN hidden API** | Unofficial, undocumented, has broken/moved before (April 2024 base-URL migration). | **Not recommended** as a primary dependency. |

**Recommendation**: Fantasy Football Calculator as the primary `adp` source
table, Sleeper draft-data as a secondary cross-check.

---

## 3. League format differences

### Scoring format: Standard vs. Half-PPR vs. Full PPR

The only rule that changes is points-per-reception (0 / 0.5 / 1), but it
ripples through positional value:

- **Standard**: RBs much more valuable (workhorse rushing/TD volume scores
  regardless of receptions); WRs take a relative hit (target volume alone
  doesn't score).
- **Full PPR**: WR value rises sharply (high-target-volume receivers gain
  value even with modest yardage); pass-catching RBs gain on pure rushers; TE
  gets a modest boost; RB takes a slight relative hit.
- **Half-PPR**: the "balanced" middle ground — once the handful of true
  workhorse RBs are gone, top WRs and the rest of RB1/RB2 become roughly
  fungible.

**Practical strategy**: Standard → prioritize early-down/goal-line workhorse
RBs; PPR → prioritize 3-down pass-catching RBs and high-target WR/TE even at
the cost of rushing volume.

### Deriving Half-PPR (and any custom reception value) from existing columns

Since `fantasy_points_ppr = fantasy_points + receptions × 1.0` under nflverse
convention, `receptions = fantasy_points_ppr − fantasy_points`, and therefore:

```
fantasy_points_custom = fantasy_points + pts_per_reception × (fantasy_points_ppr - fantasy_points)
fantasy_points_half_ppr = fantasy_points + 0.5 × (fantasy_points_ppr - fantasy_points)
```

No raw-stat recomputation needed for any `pts_per_reception` value — this
only holds if the platform's PPR points were computed with exactly +1/reception
and no other rule differences (true under nflverse convention).

### Dynasty / Keeper vs. redraft

Dynasty/keeper optimizes for **career-long value with a near-term weighting**,
not single-season points:

- **Age curves**: RBs decline earlier (often by 27–28) than WRs (elite into
  early 30s) or QBs (productive into late 30s). Dynasty rankings combine
  3/5/10-year projections with position-specific aging models.
- **Draft picks as tradeable assets**: published trade-value charts (e.g.,
  Draft Sharks Dynasty Trade Value / Dynasty Startup charts) assign each
  future rookie pick slot (1st-early, 1st-late, 2nd, 3rd...) an implied
  player-value equivalent for trade comparisons.
- **Win-now vs. rebuild**: teams assess their competitive window — higher
  projected finish → win-now (trade picks/youth for proven veterans); lower
  projected finish → rebuild (trade aging veterans for picks/youth). This is
  a roster-construction decision layered on top of, not a replacement for,
  the value rankings.
- **Empirical rookie-pick hit rates** (useful as seed values for a draft-pick
  value table): since 2020, **~68.6% of 1st-round rookie picks** produce a
  viable fantasy season, falling to **~28% for 2nd-round** and **~16.4% for
  3rd-round**.
- **Keeper leagues** sit between redraft and dynasty — typically 1–3 kept
  players/team, often with an ADP-based "cost" (the kept player's effective
  draft slot moves up N rounds); keeper value = projected value next season
  minus the opportunity cost of the draft slot surrendered.

---

## 4. Draft strategy archetypes

These are roster-construction sequencing strategies layered on top of the
same VORP/tier data — they differ in risk tolerance, not in the underlying
valuation method:

| Strategy | Definition | Data it consumes |
|---|---|---|
| **Robust RB** | Draft 2–3 RBs within the first 4–5 rounds to lock in workhorse volume while the position is deep. | RB positional-scarcity gap (RB1→RB24), injury/role-share trends |
| **Zero RB** | Avoid RBs in rounds 1–5; load elite WR/QB/TE, then mine RB value (handcuffs, pass-catchers, rookies) from round 6+. | WR depth/replaceability vs. RB's high in-season attrition rate; ADP value at WR rounds 1–5 |
| **Hero RB** | One elite RB1 in rounds 1–2 as an "anchor," then ignore RB until much later. Hybrid of Zero/Robust RB. | Same VBD/tier data; needs to identify which RB1s are "safe" anchors (high snap share + receiving role, low committee risk) |
| **Late-Round QB** | Deprioritize QB until round 8+ — the value curve from QB5 to QB15 is relatively flat. | QB VBD gap analysis (small marginal VORP gain QB1–4 vs QB5–15 relative to the draft-capital cost of an early QB) |

Each archetype can be expressed as a filter/sort rule against
`fact_draft_rankings` (e.g., "Zero RB" = "highest-VORP non-RB players
available, rounds 1–5") — which is the argument for building
`fact_draft_rankings` as the foundational layer rather than encoding any one
strategy directly.

---

## 5. Proposed table designs

### 5.1 `fact_draft_rankings`

Grain: **one row per player, per projection season, per league-format config**
(so the same player/season has multiple rows for Standard/PPR/Half-PPR/Dynasty
variants).

```sql
CREATE TABLE fact_draft_rankings (
    -- Identity / grain
    player_id              VARCHAR NOT NULL,   -- FK to bridge_player_crosswalk
    season                  INTEGER NOT NULL,   -- projection/draft season
    league_format_id        VARCHAR NOT NULL,   -- FK to league_format_config

    -- Projection inputs
    position                 VARCHAR NOT NULL,
    projected_fantasy_pts    DOUBLE,
    projection_source        VARCHAR,            -- e.g. 'historical_avg_3yr', 'naive_lastseason'

    -- VBD / VORP
    replacement_baseline_pts DOUBLE,
    vorp_score                DOUBLE,             -- projected_fantasy_pts - replacement_baseline_pts
    vols_score                DOUBLE,             -- value over last starter (alt baseline)
    vona_score                DOUBLE,             -- value over next available (live-draft, nullable)

    -- Ranking & tiering
    overall_rank              INTEGER,
    position_rank             INTEGER,
    tier                       INTEGER,            -- 1 = elite, increments downward
    tier_label                 VARCHAR,

    -- ADP / market value
    adp_overall                DOUBLE,
    adp_position_rank          INTEGER,
    adp_source                  VARCHAR,            -- 'ffcalculator' | 'sleeper' | ...
    value_vs_adp                DOUBLE,             -- adp_overall_rank - overall_rank
    value_classification        VARCHAR,            -- 'sleeper' | 'value' | 'fair' | 'reach' | 'bust'

    -- Dynasty / keeper layer (nullable for redraft)
    age_at_season_start         DOUBLE,
    age_curve_multiplier         DOUBLE,
    dynasty_value_score           DOUBLE,           -- vorp_score * age_curve_multiplier
    rookie_draft_pick_equiv       VARCHAR,           -- e.g. 'Mid 1st'

    computed_at                   TIMESTAMP,
    PRIMARY KEY (player_id, season, league_format_id)
);
```

`value_classification` thresholds (e.g., `value_vs_adp >= +12 ranks =>
'sleeper'`, `<= -12 => 'bust'`) live in `league_format_config` so they're
tunable without code changes. `tier` is a window-function gap-detection over
`vorp_score` partitioned by `position`.

### 5.2 `league_format_config`

Single source of truth for scoring weights (used to derive
`projected_fantasy_pts` / Half-PPR from `fantasy_points`/`fantasy_points_ppr`)
and roster requirements (used for replacement-level baselines):

```sql
CREATE TABLE league_format_config (
    league_format_id        VARCHAR PRIMARY KEY,  -- 'standard_12team', 'half_ppr_12team', 'dynasty_ppr_12team_sf', ...
    format_label              VARCHAR,
    num_teams                  INTEGER NOT NULL,

    -- Scoring weights
    pts_per_reception          DOUBLE DEFAULT 0.0,   -- 0 / 0.5 / 1.0
    pts_per_passing_yard       DOUBLE DEFAULT 0.04,
    pts_per_passing_td         DOUBLE DEFAULT 4.0,
    pts_per_interception       DOUBLE DEFAULT -2.0,
    pts_per_rushing_yard       DOUBLE DEFAULT 0.1,
    pts_per_rushing_td         DOUBLE DEFAULT 6.0,
    pts_per_receiving_yard     DOUBLE DEFAULT 0.1,
    pts_per_receiving_td       DOUBLE DEFAULT 6.0,
    -- additional K/DST scoring columns as needed, or normalize to a child table

    -- Roster requirements (drives replacement-level baselines)
    starters_qb                 INTEGER DEFAULT 1,
    starters_rb                  INTEGER DEFAULT 2,
    starters_wr                  INTEGER DEFAULT 2,
    starters_te                  INTEGER DEFAULT 1,
    starters_flex                INTEGER DEFAULT 1,   -- RB/WR/TE eligible
    flex_rb_share                 DOUBLE DEFAULT 0.6,
    flex_wr_share                 DOUBLE DEFAULT 0.35,
    flex_te_share                 DOUBLE DEFAULT 0.05,
    starters_k                    INTEGER DEFAULT 1,
    starters_dst                  INTEGER DEFAULT 1,
    bench_slots                   INTEGER DEFAULT 6,

    -- League type
    league_type                    VARCHAR DEFAULT 'redraft',  -- 'redraft' | 'keeper' | 'dynasty'
    is_superflex                   BOOLEAN DEFAULT FALSE,

    -- ADP-delta thresholds
    sleeper_rank_delta_threshold    INTEGER DEFAULT 12,
    bust_rank_delta_threshold       INTEGER DEFAULT -12
);
```

Replacement-level baseline rank per position:

```
QB_baseline_rank = starters_qb * num_teams                                  (×2 if is_superflex)
RB_baseline_rank = (starters_rb + starters_flex * flex_rb_share) * num_teams
WR_baseline_rank = (starters_wr + starters_flex * flex_wr_share) * num_teams
TE_baseline_rank = (starters_te + starters_flex * flex_te_share) * num_teams
K_baseline_rank  = starters_k  * num_teams
DST_baseline_rank = starters_dst * num_teams
```

### 5.3 Dynasty/Keeper adjustment layer

**`dim_age_curve`** — multiplier applied to `vorp_score` to produce
`dynasty_value_score`:

```sql
CREATE TABLE dim_age_curve (
    position          VARCHAR NOT NULL,
    age                INTEGER NOT NULL,     -- age as of season start
    value_multiplier   DOUBLE NOT NULL,      -- e.g. 1.15 for a 23yo WR, 0.70 for a 29yo RB
    PRIMARY KEY (position, age)
);
```

This table is **derivable directly from the platform's own data** — group
`fantasy_points_ppr` by `position` and `age` (from `birth_date` in
`dim_players`), normalize to an index where the age of peak production = 1.0.
No external dependency required.

**`dim_draft_pick_value`** — maps future rookie draft pick slots to a
trade-comparable value on the same scale as `dynasty_value_score`:

```sql
CREATE TABLE dim_draft_pick_value (
    pick_type            VARCHAR NOT NULL,   -- '1st_round_early' | '1st_round_mid' | '1st_round_late' | '2nd_round' | '3rd_round'
    league_type           VARCHAR NOT NULL,   -- 'dynasty' | 'keeper'
    value_score            DOUBLE NOT NULL,
    historical_hit_rate     DOUBLE              -- seed: 0.686 / 0.28 / 0.164 for 1st/2nd/3rd round
);
```

Seed `historical_hit_rate` from the cited empirical rates (68.6% / 28% /
16.4%), but recompute longitudinally from the platform's own
`fact_draft_picks` + crosswalk + subsequent `fantasy_points_ppr` season totals
once enough history accumulates — and consider segmenting further by
**draft round + college production tier** via the NCAA crosswalk for a more
granular rookie-pick value than a flat per-round average.

`dynasty_value_score = vorp_score × age_curve_multiplier`, optionally blended
across multi-year projections (`0.5×year1 + 0.3×year2 + 0.2×year3`).

### Cross-cutting note

The college↔NFL crosswalk enables two refinements that fall out "for free":

- `age_curve_multiplier` for rookies (no NFL data yet) can be seeded from
  **draft capital + combine athletic profile** before any NFL production
  exists.
- `dim_draft_pick_value` hit rates can be segmented by **round + college
  production tier** (via NCAA crosswalk) rather than a flat per-round average.
