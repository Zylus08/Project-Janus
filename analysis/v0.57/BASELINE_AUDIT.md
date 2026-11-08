# Project Janus v0.57 — Baseline Audit & Reconciliation Report

**Milestone:** Project Janus v0.57  
**Document Classification:** Foundation Baseline Freeze Audit & Forensic Evidence Reconciliation  
**Author:** Principal Chess Engine Architect & Independent Reproducibility Auditor  
**Date:** 2026-11-06  
**Repository Branch:** `v0.3-benchmark-harness`  
**Base Commit:** `e543dab` (v0.56 Final)  
**Parent Baseline Commit:** `f6025c3`  
**Production Baseline Engine:** Janus Native N5  

---

## 1. Executive Summary & Verification Gates

This audit verifies the integrity of the Project Janus codebase at git commit `e543dab`, certifying that the native engine, test suites, UCI protocol interface, and empirical artifacts meet all reproducibility standards before commencing external calibration against Stockfish 19.

### Verification Status Table:
| Verification Item | Specification / Expected State | Audited State | Status |
| :--- | :--- | :--- | :---: |
| **Git Branch** | `v0.3-benchmark-harness` | `v0.3-benchmark-harness` | **VERIFIED** |
| **Git Commit HEAD** | `e543dab` | `e543dab` | **VERIFIED** |
| **Working Tree State** | Clean (0 modified, 0 untracked) | Clean (0 modified, 0 untracked) | **VERIFIED** |
| **Production Source** | `analysis/v0.56/native/janus_native.cpp` | Present, 80,677 bytes, SHA-256: `bb57b5fb...` | **VERIFIED** |
| **Production Binary** | `analysis/v0.56/native/janus_native_engine.exe` | Present, 341,504 bytes, SHA-256: `429dbde8...` | **VERIFIED** |
| **Inherited Regression Suite** | 639 unit tests | 639 passed, 0 failed, 0 errors (169.6s) | **VERIFIED** |
| **UCI Protocol Conformance** | `uci`, `isready`, `ucinewgame`, `position`, `go` | 100% compliant, correct defaults | **VERIFIED** |
| **v0.56 Artifact Manifests** | Full experimental & SHA-256 manifests | Present and consistent (39 tracked files) | **VERIFIED** |

---

## 2. Forensic Reconciliation: SEE Score Ranges & History Heuristic Interaction

The prompt requires reconciling the v0.56 report's SEE-ordering score ranges and verifying whether losing captures can outrank high-history quiet moves.

### 2.1 Implementation Code Audit
In `analysis/v0.56/native/janus_native.cpp`, lines 1422–1457:
```cpp
        if (g_use_see_ordering) {
            int see_val = janus_see(b, m);
            g_see_total_evaluations++;
            if (see_val > 0) {
                g_see_positive_captures++;
                return 100000 + mvv_lva;
            } else if (see_val == 0) {
                g_see_neutral_captures++;
                return 95000 + mvv_lva;
            } else {
                g_see_negative_captures++;
                g_see_ordering_inversions++;
                return 20000 + std::max(-10000, see_val) + mvv_lva;
            }
        }
```
Followed by quiet move scoring:
```cpp
    // Killer Moves (Quiet moves only)
    if (g_use_killer_ordering && ply >= 0 && ply < MAX_PLY) {
        if (m == g_killer_moves[ply][0]) return 90000;
        if (m == g_killer_moves[ply][1]) return 80000;
    }

    // History Heuristic (Quiet moves only)
    if (g_use_history_ordering) {
        int side = b->side_to_move;
        int h = g_history_table[side][from][to];
        if (h > 0) {
            return std::min(MAX_HISTORY_SCORE, h);
        }
    }

    return 0; // Quiet moves
```
Constants:
- `MAX_HISTORY_SCORE = 16384` (line 126)
- Piece values in centipawns: $P=100, N=300, B=300, R=500, Q=900, K=20000$

### 2.2 Mathematical Score Range Analysis
Consider any losing capture ($\text{SEE} < 0$). In regular chess positions:
- Queen blunders into defended pawn: $\text{SEE} = 100 - 900 = -800$ cp.
- Rook blunders into defended pawn: $\text{SEE} = 100 - 500 = -400$ cp.
- Minor piece blunders into defended pawn: $\text{SEE} = 100 - 300 = -200$ cp.
- Pawn blunders into defended pawn: $\text{SEE} = 100 - 100 = 0$ (Equal trade).

Applying the formula:
$$\text{Score}(\text{Losing Capture}) = 20,000 + \text{see\_val} + \text{mvv\_lva}$$
Where $\text{mvv\_lva} = (\text{victim} \times 10) - \text{attacker} \in [-5, +49]$.
- For a Queen blundering against a defended pawn:
  $$\text{Score} = 20,000 - 800 + (10 - 5) = 19,205$$
- For a Rook blundering against a defended pawn:
  $$\text{Score} = 20,000 - 400 + (10 - 4) = 19,606$$
- For a Minor piece blundering against a defended pawn:
  $$\text{Score} = 20,000 - 200 + (10 - 2) = 19,808$$

Comparing against History and Killer scores:
$$\text{Killer 1 } (90,000) > \text{Killer 2 } (80,000) > \mathbf{\text{Losing Captures } (19,000 - 20,000)} > \mathbf{\text{Max History } (16,384)} > \text{Unscored Quiets } (0)$$

### 2.3 Definitive Finding
**Losing captures ALWAYS outrank high-history quiet moves.**
Although the v0.56 integration successfully demoted losing captures below Killer 1 ($90,000$) and Killer 2 ($80,000$)—which directly produced the $+11.8\%$ jump in first-move cutoffs—losing captures were given a base offset of $20,000$. Because $20,000 - 900 = 19,100 > 16,384$, a losing capture never falls below a high-history quiet move.

In accordance with Governing Constraint 1 ("Do not implement new classical search optimizations"), this finding is formally recorded as an architectural property of the v0.56 experimental candidate without altering the production engine.

---

## 3. Forensic Reconciliation: Quiescence SEE & Factorial Node Identity

The prompt requires confirming whether quiescence SEE is genuinely active and whether its identical node counts in S1 (`g_use_see_ordering=true, g_use_see_in_quiescence=false`) and S3 (`g_use_see_ordering=true, g_use_see_in_quiescence=true`) reflect legitimate behaviour or an instrumentation/configuration defect.

### 3.1 Quiescence Search Implementation Audit
In `analysis/v0.56/native/janus_native.cpp`, lines 1503–1538:
```cpp
            } else if (g_use_see_in_quiescence) {
                // Explicit Quiescence SEE calculation
                int see_val = janus_see(b, m);
                g_see_total_evaluations++;
                if (see_val > 0) {
                    g_see_positive_captures++;
                    score = 100000 + mvv_lva;
                } else if (see_val == 0) {
                    g_see_neutral_captures++;
                    score = 95000 + mvv_lva;
                } else {
                    g_see_negative_captures++;
                    score = 10000 + std::max(-10000, see_val) + mvv_lva;
                }
            } else {
                score = score_move_for_ordering(b, m, 0, 0);
            }
```
Now examine the fallback branch:
When `g_use_see_in_quiescence` is `false` (as configured in S1), line 1537 calls:
`score = score_move_for_ordering(b, m, 0, 0);`

Inside `score_move_for_ordering(b, m, 0, 0)` (lines 1422–1436):
```cpp
        if (g_use_see_ordering) {
            int see_val = janus_see(b, m);
            g_see_total_evaluations++;
            if (see_val > 0) {
                g_see_positive_captures++;
                return 100000 + mvv_lva;
            } else if (see_val == 0) {
                g_see_neutral_captures++;
                return 95000 + mvv_lva;
            } else {
                g_see_negative_captures++;
                g_see_ordering_inversions++;
                return 20000 + std::max(-10000, see_val) + mvv_lva;
            }
        }
```

### 3.2 Architectural Explanation for Identical S1 vs S3 Node Counts
In configuration S1:
- `g_use_see_ordering = true`
- `g_use_see_in_quiescence = false`

When quiescence search scored its moves in S1, it took the `else` branch, invoking `score_move_for_ordering(b, m, 0, 0)`.
Because `g_use_see_ordering` was `true`, `score_move_for_ordering` **evaluated SEE on every capture in quiescence search anyway!**

Comparing the scoring of captures in quiescence between S1 and S3:
| Move Category | S1 Quiescence Score (via `score_move_for_ordering`) | S3 Quiescence Score (via `g_use_see_in_quiescence`) |
| :--- | :---: | :---: |
| **Winning Captures** ($\text{SEE} > 0$) | $100,000 + \text{mvv\_lva}$ | $100,000 + \text{mvv\_lva}$ |
| **Neutral Trades** ($\text{SEE} == 0$) | $95,000 + \text{mvv\_lva}$ | $95,000 + \text{mvv\_lva}$ |
| **Losing Captures** ($\text{SEE} < 0$) | $20,000 + \text{see} + \text{mvv\_lva}$ | $10,000 + \text{see} + \text{mvv\_lva}$ |

Crucially, in quiescence search, **only captures and promotions are generated**. No quiet moves are present.
Therefore:
- In both S1 and S3, winning captures outrank neutral trades, and neutral trades outrank losing captures.
- Within losing captures, both sort by `see + mvv_lva`.
- The difference in baseline offset ($20,000$ in S1 vs $10,000$ in S3) is an affine shift that has **zero effect on the sorted ordering of `caps`**.

### 3.3 Definitive Conclusion
1. **Quiescence SEE is genuinely active:** In S2 (`g_use_see_ordering=false, g_use_see_in_quiescence=true`), quiescence SEE operated cleanly, reducing nodes from 7,036,590 (S0) to 6,880,448 (S2) at Depth 6.
2. **S1 was an unintentionally combined configuration:** Because `score_move_for_ordering` queried `g_use_see_ordering`, S1 inadvertently activated SEE capture ordering in both main search and quiescence search.
3. **Legitimate Behaviour:** The identical node counts between S1 and S3 reflect exact mathematical equivalence of the resulting move permutations. There was no instrumentation defect or counter failure; S1 and S3 executed identical search trees because S1's fallback code path executed SEE ordering in quiescence search.

---

## 4. Production Engine Baseline Verification

The production baseline engine is verified as **Janus Native N5**:
- Compiler: Microsoft Visual C++ BuildTools 2022 (`v19.43.34809 x64`).
- Compilation Flags: `/O2 /Ot /Oi /std:c++17`.
- Executable: `analysis/v0.56/native/janus_native_engine.exe`.
- Default Options:
  - `UseKillerOrdering = true`
  - `UseHistoryOrdering = true`
  - `UsePVS = false`
  - `UseLMR = true`
  - `UseSEEOrdering = false`
  - `UseSEEInQuiescence = false`

When started without options, `janus_native_engine.exe` operates strictly as N5.

---

## 5. Gate Clearance

- **Correctness Regressions:** Zero regressions detected across 639 unit tests.
- **Evidence Reconciliation:** Complete; all architectural anomalies in v0.56 fully explained with mathematical and code-level evidence.
- **Milestone Gate 0:** **PASSED**. Proceeding to Phase 1 (Stockfish 19 Calibration).

