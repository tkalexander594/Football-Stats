# Sleeper Prediction Model Review & Improvements

This report critiques the `sleeper_score` formula proposed in Appendix A
(Section 5), proposes position-specific v2 metrics grounded in established
college-production-to-NFL-translation research, distinguishes **NCAA prospect
sleepers** from **NFL roster sleepers** (two different problems the current
formula conflates), and lays out a path to a statistically validated model.

### Current formula (under review)

```
production_score    = percentile_rank(yards_market_share + td_market_share, within position group & draft class)
athleticism_score   = mean(non-null 40-yard percentile, vertical percentile, agility [cone+shuttle] percentile)
draft_capital_score = 100 if undrafted else 100 * (1 - (draft_pick-1)/261)
sleeper_score = 0.45*production_score + 0.20*athleticism_score
              + 0.20*(100 - draft_capital_score) + 0.15*recruiting_inverse_score
```

---

## 1. Established college-production-to-NFL-translation metrics

### Dominator Rating

Measures a player's "market share" of their college team's production — the
**calculation differs by position**, which the current formula does not
account for:

- **WR/TE**: % of team **receiving** yards + % of team **receiving** TDs
  (averaged). Does *not* include rushing.
- **RB**: % of **total offensive production** (rushing + receiving), i.e.
  share of total team offense, not just team total yards.
- **QB**: Dominator Rating is **not used** — it's not a meaningful QB metric.

**Thresholds** (PlayerProfiler/RotoViz):

| Position | Elite | Mid-tier | Red flag |
|---|---|---|---|
| WR | 35%+ (potential WR1); ~45% = excellent | 20–35% | <20% |
| RB | ~40% = excellent | — | — |
| TE | ~30% = excellent | — | — |

**Career** (multi-season, weighted/averaged) dominator rating reportedly
correlates *better* with NFL outcomes than a single final-season number — a
direct gap vs. the current formula, which only uses the final season.

### Breakout Age

The age at which a player **first** crosses a position-specific dominator
threshold:

- **WR**: 20% dominator threshold; breakout age ≤ 19 is "excellent."
- **RB/TE**: lower **15%** threshold.

**Why it matters**: an 18–19 year old already producing at starter level
despite a physical/experience disadvantage vs. 21–22 year olds signals
unusual talent. Younger breakout age = stronger signal.

**Adjusted breakout age**: corrects for **college entry age** — a player who
enrolled at 20 (grayshirt, JUCO transfer, international) never had a chance
to break out at the "ideal" 18–19 age; raw breakout age unfairly penalizes
them without this adjustment.

The current formula has **no breakout-age concept at all** — it's the single
highest-value addition identified in this research.

### College Target Share / Yards Per Route Run (YPRR)

- **Not calculable from standard college box-score feeds** — requires
  "routes run" data from charting services (PFF College ~2014+, paywalled) or
  manual film charting. Target share is *somewhat* more feasible if a feed
  tracks targets (not just receptions), but many feeds don't.
- **Predictive value**: final-season YPRR is the most relevant single-season
  number, but **career YPRR → NFL rookie YPRR correlates ~0.26** vs. **~0.08**
  for final-season-only — multi-year trend beats a single season.
- Emerging research suggests **First Downs per Route Run (1D/RR)** may be
  slightly more predictive than YPRR — even less available from standard feeds.
- **Recommendation**: flag as a **"nice to have if a premium charting feed
  (PFF/SIS) is licensed"** — not a near-term requirement given the project's
  CFBD-based data feed.

### Athleticism composites: RAS / SPARQ

**RAS (Relative Athletic Score, Kent Lee Platte)**:
- Up to **10 measurements** (height, weight, 40-yard + splits, bench, vertical,
  broad jump, shuttle, 3-cone).
- Each test compared against **all players at that position since 1987**,
  converted to a 0–10 grade; component grades averaged into an overall 0–10
  RAS. Requires a **minimum of 6 completed tests** for a valid score —
  pro-day-only/injured prospects often have incomplete profiles (a
  missing-data flag is needed, not silent exclusion).

**Predictive value is highly position-dependent — the current formula's
uniform `mean(40-yard, vertical, agility)` is misaligned**:

| Position | Athleticism signal |
|---|---|
| **TE** | **Highly predictive.** Top-5 fantasy TEs consistently show higher RAS than TE31-50. Optimal RAS range **8.8–9.9**. "The position where Combine athleticism is most determinative of fantasy upside." |
| **WR** | **Weak/non-linear.** No meaningful correlation in some studies, but within the elite-RAS subset (8.5–10), hit rate over-indexes. |
| **RB** | **Component-specific, not raw speed.** Agility (shuttle/cone) and contact balance predict better than 40-time. PlayerProfiler: Speed Score = `(weight × 200) / (40-time)^4`; Burst Score = vertical + broad jump (equal-weighted); Agility Score = shuttle + 3-cone (lower = better). Height-adjusted Speed Score is PlayerProfiler's top metric overall, then agility, then burst. |

---

## 2. NFL-side "buy-low" roster sleeper signals (a *different* problem)

This is conceptually distinct from the NCAA prospect-sleeper model above —
the platform should treat it as a **second analysis** built on
`fact_nfl_player_season_offense` trend data, not a variant of `sleeper_score`.

- **FTA Sleeper Score framework** weights: **Efficiency 35%** (CPOE for QB,
  rush-yards-over-expected for RB, separation/route-win-rate for WR/TE),
  **ADP Gap 35%**, **Volume Trend 15%**, **Injury Return 15%**.
- **Efficiency-outpacing-volume**: a player with strong yards-per-target/YPRR
  but a target share below what that efficiency would predict — an
  "opportunity gap" a scheme change, depth-chart shakeup, or teammate injury
  could close.
- **Depth-chart/target-share trend**: WRs with a top-36 rookie-year target
  share but a finish outside the top-24 are classic year-2 positive-regression
  candidates — target share is "stickier" than rookie-year scoring efficiency.
- **Scheme/system fit**: a slot receiver moving to a team whose offense
  historically sends ~28% of targets to the slot is a *data-driven* sleeper
  signal — OC/scheme changes create the largest ADP dislocations because the
  market reprices slowly.
- **Age curves** (useful for "is this buy-low window still open"):
  - **RB**: peak ~25.5yo, established by 23, decline accelerates after 28
    (peak-season frequency 8.7% at 28 → 5.2% at 29 → 3.8% at 30), roughly
    **−15%/yr** in the back half of the prime.
  - **WR**: peak 26–28, prime decline closer to **−10%/yr**, sustained value
    into early 30s with a "drastic" decline only after 31.
  - **The WR window runs ~1.5 years longer than RB's at every career stage** —
    a useful heuristic (e.g., a 24–25yo underperforming WR has more long-term
    buy-low value than a same-age RB, all else equal).

---

## 3. Critique of the current formula

### Weighting (0.45 / 0.20 / 0.20 / 0.15)

No single canonical industry weighting exists, but the closest analog —
FFFaceoff's **Prospect Success Indicator (PSI)** — combines Breakout Age,
Weighted Dominator Rating, College Entry Age (as a breakout-age adjustment),
Athleticism, and Draft Capital, calibrated against the average Top-24
finisher profile. Separately, 4for4's published rookie WR model found a
**simple logistic regression on just production + draft capital** outperforms
more complex models *for finding undervalued players specifically*.

Issues with the current split:

- **45% production**: directionally reasonable — production/market-share is
  consistently the top-tier signal for WR/RB.
- **20% athleticism, flat across positions**: per §1, athleticism is
  near-decisive for TE, weak/non-linear for WR, and component-specific for
  RB (agility > speed). A uniform 20% mean-of-three-percentiles over- or
  under-credits depending on position.
- **20% on `(100 - draft_capital_score)`**: weighting "being drafted
  late/undrafted" as a *positive* contributor is conceptually circular and
  **double-counts with the recruiting term** (see below).
- **15% `recruiting_inverse_score`**: a real signal exists (3-star recruits
  are drafted at only ~5.3% the rate of 5-stars), but recruiting rating is
  largely a *proxy* for the athleticism/projectable-size traits the model
  already captures via `athleticism_score` — and is partially "explained
  away" by draft capital itself. Including it alongside both
  `athleticism_score` and `(100 - draft_capital_score)` risks
  **triple-counting the same underlying signal**.

### `draft_pick` capped at 261 — a real bug, not just a style issue

- The NFL draft is **not a fixed-size draft**. 32 teams × 7 rounds = 224
  "natural" picks, plus a variable number of compensatory picks (since 1994).
  **2026 had 33 comp picks → 257 total.** Other years range roughly 250–262+.
- A fixed denominator of 261/262 means a player picked #250 in a 257-pick
  draft gets a different `draft_capital_score` than the *same relative slot*
  in a 262-pick year — **a class-to-class inconsistency** for what should be
  a comparable "drafted very late" signal.
- **More fundamentally, the linear `1 - (pick-1)/261` relationship is the
  wrong shape.** The Chase Stuart / Football Perspective draft value curve
  (built from career Approximate Value) is a **power law**:
  `AV(pick) ≈ 100 × (1/pick)^0.67`. Under this curve, value falls off a cliff
  from pick 1→32 (~100→~20) but is nearly flat from pick 200→260. A linear
  scale **overstates how different mid-to-late-round picks really are** in
  outcome terms — it would, for example, treat the VORP-relevant gap between
  picks 100 and 150 as much larger than the empirical AV curve says it is.

**Recommendation**: replace the linear formula with a normalized power-law
curve, e.g. `draft_capital_score = 100 × (1/pick)^0.67` (rescaled 0–100,
undrafted = 0 on this scale before inversion), and if a single cross-year
scale is needed, normalize `pick` by `pick / total_picks_in_class_year`
rather than a hardcoded constant.

### Missing signals (ranked by expected value)

1. **Breakout age** (incl. adjusted-for-entry-age variant) — the single
   highest-value addition; the current formula has no concept of *when* a
   player became productive, only their final-season snapshot.
2. **Career/multi-year production trend** — career dominator correlates
   better than final-season-only; a rising trajectory vs. a one-year spike
   are different signals the current formula can't distinguish.
3. **Age at draft / college entry age** — both standalone and as the
   breakout-age adjustment described above.
4. **Target share / YPRR / 1D-per-route** — high value per the literature but
   gated on a premium charting data source; flag as future/contingent.
5. **Landing spot / situation** — depth chart, scheme fit, projected target
   share in the new offense. Not addressed at all currently, despite being
   arguably *the* biggest real-world driver of "will this sleeper get a
   chance."
6. **QB-specific metrics** — Dominator Rating is explicitly inapplicable to
   QBs. If the model covers QBs it needs a wholly separate metric set:
   adjusted yards/attempt (TANY/A-style), CPOE proxy, rushing
   yards/attempts, college passer rating (e.g., 3,700+ college passing yards
   correlates with ~17.7% higher top-5 NFL outcome rate).
7. **Position-specific dominator denominators** — the current formula's
   `yards_market_share + td_market_share` of "team total yards/TDs" reads as
   a WR-style calculation applied uniformly. RB dominator should be share of
   **total offense** (run+pass); using "team total yards" for a WR
   understates their true receiving-share dominator since it dilutes with
   rushing yards the WR had no part in.

### One formula or several?

The research strongly supports **position-specific formula variants**, not
optional polish:

- Dominator Rating itself is computed differently by position (already a
  mis-specification in the current single formula for RB/QB).
- Athleticism weight should vary dramatically: ~30–35% for TE, ~10% for WR,
  RB substituting an agility-weighted composite for the generic 3-test mean.
- Breakout-age thresholds differ (20% WR vs. 15% RB/TE).
- QB needs an entirely different production_score.

**Recommendation**: keep the same high-level structure (production /
athleticism / draft capital / context) but make sub-metric definitions and
weights **position-conditional** — at minimum WR/RB/TE/QB variants.

---

## 4. Proposed v2 `fact_sleeper_scores` additions

Building on Appendix A Section 5's table, add:

```sql
ALTER TABLE fact_sleeper_scores ADD COLUMN dominator_rating_final DOUBLE;     -- position-specific calc
ALTER TABLE fact_sleeper_scores ADD COLUMN dominator_rating_career DOUBLE;    -- multi-season weighted/avg
ALTER TABLE fact_sleeper_scores ADD COLUMN breakout_age DOUBLE;               -- age at first threshold crossing
ALTER TABLE fact_sleeper_scores ADD COLUMN breakout_age_adjusted DOUBLE;      -- adjusted for college entry age
ALTER TABLE fact_sleeper_scores ADD COLUMN breakout_threshold_met BOOLEAN;    -- 20% (WR) / 15% (RB,TE)
ALTER TABLE fact_sleeper_scores ADD COLUMN college_entry_age DOUBLE;
ALTER TABLE fact_sleeper_scores ADD COLUMN college_target_share DOUBLE;       -- nullable, premium-feed-dependent
ALTER TABLE fact_sleeper_scores ADD COLUMN production_trend_slope DOUBLE;     -- career dominator trend
```

`sleeper_score` itself becomes position-conditional (illustrative WR
weighting shown; RB/TE/QB variants substitute the athleticism term and
production definition per §1/§3):

```
sleeper_score_wr = 0.40 * production_score          -- dominator (receiving share), career-weighted
                  + 0.20 * breakout_age_score        -- inverse of adjusted breakout age, 20% threshold
                  + 0.10 * athleticism_score         -- de-emphasized for WR
                  + 0.25 * draft_capital_score       -- power-law curve, inverted
                  + 0.05 * recruiting_inverse_score  -- reduced from 0.15 to curb double-counting
```

---

## 5. NCAA prospect sleepers vs. NFL roster sleepers

The current `sleeper_score` is entirely a **pre-draft prospect** model. A
second, structurally different analysis is needed for **already-drafted NFL
players** who are undervalued *now* — these use different inputs and answer a
different fantasy question ("who should I trade for / stash" vs. "who should
I draft as a rookie"):

| | NCAA Prospect Sleeper (current) | NFL Roster Sleeper (new) |
|---|---|---|
| Population | Draft-eligible/recently-drafted players | Current NFL roster players |
| Core signal | College production + athleticism + draft capital | Efficiency-vs-volume gap, target-share trend, scheme fit, ADP gap |
| Data source | `fact_ncaa_player_season_*`, `fact_recruiting_rankings`, `fact_combine_results`, `fact_draft_picks` | `fact_nfl_player_season_offense` trend deltas, `fact_draft_rankings.adp_*` |
| Output table | `fact_sleeper_scores` (v2, position-conditional, §4) | new `fact_nfl_buy_low_scores` (future work) |

---

## 6. Path to a statistically validated model (future)

- **Label**: binary "NFL hit" = top-24 PPR finish at position within first 3
  seasons (top-12 for TE/QB given shallower depth) — consistent with 4for4's
  published framing and DynastyNerds' draft-capital hit-rate studies.
- **Feature set**: final + career dominator, breakout age (raw + adjusted),
  production trend, RAS/component athleticism (with missing-data flags),
  draft capital (AV-curve-normalized), age at draft, position, conference/SOS,
  HS star rating (low weight — multicollinear with athleticism/draft capital).
- **Modeling**: logistic regression baseline (interpretable, and per 4for4
  competitive with more complex models for *finding undervalued players*
  specifically); gradient boosting (XGBoost/LightGBM) as a secondary model
  for non-linear position interactions, with SHAP analysis to guard against
  the model simply rediscovering "draft capital correlates with outcome"
  (draft capital is itself informed by production/athleticism, so it can
  absorb signal from the other features if not checked).
- **Sample size**: one cited study used **draft classes 2000–2018 (1,349
  players)** for a draft-capital/outcome analysis — ~15–20 classes is a
  realistic minimum, though position-split samples will be modest (low
  hundreds for WR-only). Combine data is reliably digitized from ~2000;
  charting-based features (YPRR/target share, PFF ~2014+) would constrain a
  model that includes them to ~10 classes.
- **Class imbalance**: "top-24 in 3 years" is a relatively rare positive
  (~10–25% base rate by position) — needs class weighting or stratified CV.
- **Validation**: **walk-forward time-series CV** (train through class N,
  validate on N+1), not random k-fold — avoids leaking future information
  into the "predict before the draft" use case this model is built for.

This is explicitly a **3–5 year history** dependency (the platform needs
several seasons of `fact_sleeper_scores` + realized outcomes before this is
viable) — tracked as a P3 item in `docs/roadmap.md`.
