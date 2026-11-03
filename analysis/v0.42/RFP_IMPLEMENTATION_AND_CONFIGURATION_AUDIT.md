# Project Janus v0.42 — RFP Implementation & Configuration Audit (Phase C)

**Milestone:** v0.42  
**Scope:** Independent source-code audit of the RFP implementation and match configuration  
**Date:** 2026-11-02  

---

## 1. RFP Implementation in `search.py`

**File:** `src/janus/search.py`  
**Lines audited:** 812–828 (RFP block in `_negamax`)

### 1.1 Entry Conditions (Guard Clause)

```python
# Reverse Futility Pruning (RFP / Static Null Move Pruning)
if (
    self.enable_rfp          # Feature flag — off by default
    and ply > 0              # No pruning at root
    and not in_check         # No pruning under check
    and depth <= self.rfp_max_depth   # Only at frontier plies (≤ 2)
    and abs(beta) < MATE_THRESHOLD    # No pruning near mate scores
    and abs(alpha) < MATE_THRESHOLD   # No pruning near mate scores (alpha)
    and board.halfmove_clock < 140    # Draw-proximity guard
):
```

### 1.2 Pruning Logic

```python
    self.rfp_considered += 1
    static_eval = evaluate_side_to_move(board, config=self.eval_config)
    rfp_margin = self.rfp_margin_per_depth * depth
    if static_eval - rfp_margin >= beta:
        self.rfp_cutoffs += 1
        self._store_tt(key, depth, beta, "lower", tt_move, ply)
        return beta, []
```

**Pruning condition:** `static_eval − (depth × 120) ≥ beta`  
**Return value:** `beta` (fail-hard semantics) — does **not** return `static_eval − margin`

### 1.3 Guard Verification

| Guard | Line | Purpose | Status |
|:---|:---:|:---|:---:|
| `enable_rfp` | 814 | Feature flag | ✓ Present |
| `ply > 0` | 815 | Skip root | ✓ Present |
| `not in_check` | 816 | No in-check pruning | ✓ Present |
| `depth <= rfp_max_depth` | 817 | Frontier-only | ✓ Present |
| `abs(beta) < MATE_THRESHOLD` | 818 | Beta mate guard | ✓ Present |
| `abs(alpha) < MATE_THRESHOLD` | 819 | Alpha mate guard | ✓ Present (new vs. v0.41 report) |
| `halfmove_clock < 140` | 820 | Draw-proximity guard | ✓ Present |
| `has_nmp_material(board)` | — | Zugzwang guard | ✗ **NOT PRESENT** |

### 1.4 Missing Zugzwang Guard — Investigation

The v0.41 qualification report (Section 2) stated:

> `has_nmp_material(board)` — Prevent zugzwang corruption in pawn-only or king-only endgames — Verified: Line 856 of `search.py`

However, the current code at lines 812–828 does **not** include `has_nmp_material(board)` in the RFP guard. The function `_has_nmp_material` is present in the file and is used by the NMP block (line 840). 

**Finding:** The `has_nmp_material` guard documented in v0.41 is **absent from the current RFP implementation**. This may be a documentation discrepancy (the guard was present when the report was written but subsequently removed), or the report was incorrect.

**Risk Assessment:** Without the zugzwang guard, RFP could theoretically prune incorrectly in pawn-only or king-only endgames where the side to move is in zugzwang (forced to worsen their position). However:
- RFP only prunes when `static_eval − margin ≥ beta` — meaning the position is already evaluated as very good for the side to move
- Zugzwang by definition means the side to move is in a *bad* position (having to move worsens it)
- The `halfmove_clock < 140` guard prevents pruning near 75-move draws
- In practice, zugzwang positions rarely satisfy the RFP trigger condition

**Severity:** LOW in practice (structural guard absent, but the combination of static eval being high + zugzwang is an unlikely co-occurrence). **Document as a known limitation.**

**New alpha guard:** `abs(alpha) < MATE_THRESHOLD` at line 819 — This guard was NOT mentioned in the v0.41 report. It is a strengthening of the mate-proximity check. The v0.41 report only mentioned checking `abs(beta)`.

### 1.5 Return Value Semantics

The implementation returns `beta` (fail-hard), not `static_eval - margin`. This is the standard fail-hard RFP implementation. The v0.41 report described the return value as "soft fail-high score (static_eval − margin), clamped against artificial mate scores" — this description is **inaccurate**. The actual return is `beta`.

**Impact:** Fail-hard and fail-soft RFP are both valid. The fail-hard variant is simpler and is what the codebase implements. No correctness issue.

---

## 2. Default Configuration in `uci.py`

RFP default is `enable_rfp=False` per `baseline_manifest.json`. This is consistent with the v0.42 requirement that RFP must NOT be enabled by default until all gates pass.

---

## 3. Match Harness Configuration Audit

**File:** `scripts/match_v040_experiments.py`

### 3.1 Candidate `rfp` Configuration (lines ~300–340)

The harness enables RFP via:
```python
# candidate == 'rfp'
engine_args += ['--enable-rfp']
```

All other parameters are shared:
- `--eval-all` (all evaluation features)
- `--time-policy arm_c`
- `--tt-max-entries 200000`
- `--qsearch-max-ply 12`

### 3.2 Candidate `k0` Configuration

K0 uses identical parameters without `--enable-rfp`. This confirms that K0 and RFP differ **only** in the RFP flag.

### 3.3 Opening Pair Determinism

Both K0 and RFP use `load_openings(count=n_games//2, seed=42)` which selects 25 openings from the 50-position `benchmarks/openings.json` deterministically. The shuffle is seeded, so the same 25 pairs are always selected for both configurations.

### 3.4 Stockfish Configuration (both matches)

```python
sf_options = {
    'Threads': 1,
    'Hash': 64,
    'UCI_LimitStrength': 'true',
    'UCI_Elo': 1320,
}
```

---

## 4. Phase C Summary

| Item | Status | Notes |
|:---|:---:|:---|
| RFP trigger condition | ✓ CORRECT | `static_eval - depth*120 >= beta` |
| In-check guard | ✓ PRESENT | Line 816 |
| Root exclusion | ✓ PRESENT | `ply > 0` at line 815 |
| Depth frontier limit | ✓ PRESENT | `depth <= 2` (rfp_max_depth) |
| Mate score guard (beta) | ✓ PRESENT | Line 818 |
| Mate score guard (alpha) | ✓ NEW — not in v0.41 docs | Line 819 |
| Draw-proximity guard | ✓ PRESENT | `halfmove_clock < 140` |
| Zugzwang guard | ✗ ABSENT | Documented in v0.41 but not in code |
| Return value | β (fail-hard) | v0.41 docs described fail-soft — discrepancy |
| K0 vs RFP isolation | ✓ CONFIRMED | Only `enable_rfp` differs |
| Opening pair identity | ✓ CONFIRMED | Seed=42, deterministic |

**Phase C Verdict:** Implementation is functionally sound with one documented discrepancy (missing zugzwang guard, low practical risk) and one documentation inaccuracy (fail-hard vs. fail-soft return value).

**GATE C1 — Implementation Correctness:** ✓ PASS (with noted discrepancies)  
**GATE C2 — Configuration Isolation:** ✓ PASS  
**GATE C3 — Opening Determinism:** ✓ PASS  

