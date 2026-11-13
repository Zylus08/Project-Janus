# Architectural Priority Decision: Selection of the Single Classical Intervention
**Project Janus — Phase 1, Milestone P1.13**
**Author:** Principal Computer Chess Engine Architect & Systems Performance Engineer
**Repository:** `E:\ChessXML\project-janus-phase1`
**Parent Commit:** `5b44c3f`
**Date:** November 13, 2026

---

## 1. Executive Summary & Selection Mandate

Under the governing requirements of Milestone P1.13, **at most ONE primary classical search intervention** may be selected for implementation and testing in Candidate X18. Bundling multiple speculative features simultaneously (as occurred in Milestone P1.11 with Candidate X16) is strictly prohibited.

The intervention must be selected based on empirical evidence from:
1. Search Pipeline Profiling (Phase 2).
2. Decision Quality Audit (Phase 3).
3. Stockfish 11 Architectural Gap Analysis (Phase 4).

---

## 2. Quantitative Evaluation of Candidate Interventions

The identified search bottlenecks were scored across eight criteria (1–5 scale, where 5 is optimal):

| Evaluation Criteria | Weight | Candidate 1: History-Modulated LMR | Candidate 2: Singular Extensions | Candidate 3: Multi-Cut Pruning | Candidate 4: Complex Continuation History |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Reproducibility** | 15% | 5 (100% deterministic) | 4 (PV dependent) | 3 (Heuristic noise) | 4 (State dependent) |
| **2. Frequency Across Positions** | 15% | 5 (Applies at every quiet node) | 2 (Only at singular root/TT nodes) | 2 (Only at shallow cuts) | 4 (Applies at quiet moves) |
| **3. Competitive Severity** | 20% | 5 (Direct cause of 15× node gap) | 4 (Tactical horizon defense) | 3 (Node reduction) | 4 (Quiet move ordering) |
| **4. CPU / Memory Cost** | 15% | 5 (Zero memory, 1 CPU cycle) | 2 (Expensive re-searches) | 3 (Full move generation) | 3 (64 MB array footprint) |
| **5. Correctness Risk** | 15% | 5 (Zero risk to tree invariants) | 2 (High risk of search blowup) | 3 (Risk of illegal cuts) | 4 (Low risk) |
| **6. Ease of Independent Measurement**| 10% | 5 (Clean counterfactual ablation) | 3 (Hard to isolate) | 3 (High variance) | 3 (Interacts with LMR) |
| **7. Expected Generalization** | 10% | 5 (Robust across all game phases) | 3 (Sharp tactics only) | 2 (Heuristic failure risk) | 4 (Middlegame only) |
| **WEIGHTED SCORE** | **100%** | **4.95 / 5.00** | **2.95 / 5.00** | **2.75 / 5.00** | **3.70 / 5.00** |

---

## 3. The Chosen Intervention: History-Modulated Late Move Reductions (History-LMR)

### 3.1 Category Classification
**Category D: Search Selectivity Correction**

### 3.2 Specific Architectural Mechanism
In qualified baselines X7 and X12, Late Move Reductions (LMR) reduce quiet moves ($m \ge 4$) strictly based on static search depth and move index:
$$R_{\text{static}} = \text{g\_lmr\_table}[d][m]$$

In the proposed Candidate X18, this static reduction is modulated dynamically by the move's history heuristic score $H = \text{g\_history\_table}[\text{side}][\text{from}][\text{to}]$:
1. **History Preservation (Promising Quiet Moves):**
   If $H \ge +8000$, the move is known to frequently cause beta-cutoffs in sibling branches. Its reduction is decreased by 1 ply:
   $$R = \max(1, R_{\text{static}} - 1)$$
   This prevents the search from prematurely truncating strong positional moves.
2. **History Truncation (Demonstrably Inferior Quiet Moves):**
   If $H \le -2000$ and depth $d \ge 5$, the move has repeatedly failed low in sibling branches. Its reduction is increased by 1 ply:
   $$R = R_{\text{static}} + 1$$
   This prunes demonstrably unpromising subtrees 1 ply earlier, directly addressing the 15× node expansion bottleneck.

### 3.3 Implementation Invariants
1. Must be strictly switchable via UCI option (`UCI_HistoryLMR` / `UCI_Variant X18`).
2. When disabled, the search tree must exactly reproduce baseline X7 (1T) and X12 (4T).
3. Zero neural networks, learned parameters, SPSA weights, or offline-fitted tables.
4. Total code modification is constrained to $< 25$ lines of pure C++17 within `engine/classical_x/janus_classical_x.cpp`.

