# Project Janus v0.52 — Final Disposition & Architectural Decision

**Milestone:** v0.52 — Native Late Move Reductions, Tactical Safety & Controlled Strength Ablation  
**Date:** 2026-11-04  
**Auditor / Principal Engineer:** Principal Chess Engine Research Engineer  
**Selected Outcome:** **CATEGORY A — Candidate N3 Promoted to Production Default**  

---

## 1. Official Disposition: CATEGORY A

Project Janus v0.52 preregistered four explicit outcome categories:
- **Category A:** Clear playing-strength improvement. Promoted to default search configuration.
- **Category B:** Neutral playing strength (within error margin), but efficiency improvement. Retained as optional configuration.
- **Category C:** Negative playing strength. LMR rejected for production.
- **Category D:** Inconclusive / experimental issues.

### Verdict:
**Candidate N3 (`UseLMR=true`) is formally classified as CATEGORY A.**

### Primary Justification:
1. **Statistically Significant Strength Improvement:**
   - 200-game preregistered match against Baseline N2 resulted in 115.0 / 200 points (57.50% score).
   - Paired Student-t statistic $t = 3.2764$, $df = 99$, with $p = 0.00145$ ($p < 0.005$).
   - 95% bootstrap confidence interval strictly positive: $[+0.0600, +0.2400]$ points per opening pair.
   - Empirical Elo advantage of **+52.5 Elo** ($95\%\text{ CI: } [+20.9, +85.0]\text{ Elo}$).
2. **Superior Search Horizon Under Clock Controls:**
   - Monotonic nominal depth gain across all 7 tested time tiers (from +0.19 plies at 50ms to **+1.12 plies at 3000ms**).
3. **Massive Algorithmic Efficiency:**
   - Up to 64.6% search tree pruning at Depth 5 and **3.05x speedup** at Depth 6.
   - Extremely low re-search rate (0.88% at Depth 5, 1.39% at Depth 6).
4. **Impeccable Tactical Safety & Invariant Integrity:**
   - 20/20 invariant tests passing (`test_native_lmr_semantics.py`).
   - 0 tactical regressions across 28 puzzle positions.
   - 100% sound FIDE game terminations with zero illegal moves or engine crashes.

---

## 2. Updated Production Configuration

To reflect Category A promotion, the native C++17 engine configuration default for `UseLMR` is updated to `true`:

```cpp
// Production Configuration (Janus v0.52 - Category A Promoted)
static bool g_use_lmr = true; // Enabled by default in production
static int g_lmr_min_depth = 3;
static int g_lmr_move_threshold = 4;
static int g_lmr_base_reduction = 1;
```

In the UCI protocol:
```
option name UseLMR type check default true
option name LMRMinDepth type spin default 3 min 2 max 8
option name LMRMoveThreshold type spin default 4 min 2 max 16
option name LMRBaseReduction type spin default 1 min 1 max 3
```

Baseline N2 search can still be accessed at any time via UCI:
```
setoption name UseLMR value false
```

---

## 3. Engineering Checklist

- [x] All 20 LMR semantic invariants verified and passing.
- [x] Controller 150-ply artificial cutoff removed and replaced with standard FIDE adjudications.
- [x] Tactical regression benchmark verified (zero dropped tactics).
- [x] Fixed-depth ablation benchmark complete across Depths 3–6.
- [x] Fixed-time ladder benchmark complete across 7 tiers (50ms–3000ms).
- [x] Preregistered 200-game match completed under strict controls.
- [x] Parametric paired Student-t test verified ($t = 3.2764$, $p = 0.00145$).
- [x] Non-parametric 100,000 paired bootstrap verified ($[+20.9, +85.0]$ Elo).
- [x] Complete PGN logged and verified.
- [x] SHA-256 and experiment manifests generated.
- [x] Production defaults updated to `UseLMR=true`.

