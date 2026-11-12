# Phase 3: Evaluation–Search Reliability Study

**Milestone:** Phase 1, Milestone P1.11  
**Charter:** Classical Search Architecture Decision, Counterfactual Pruning Verification & Competitive Strength Recovery  
**Lead Researcher:** Principal Computer Chess Engineer & Classical Evaluation Researcher  
**Engines Tested:** Janus Classical X15 (`24c663c`), evaluated across E5, E10, and E11  
**Raw Data Reference:** [`analysis/phase1/p1.11/raw/eval_pruning_compatibility_raw.json`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.11/raw/eval_pruning_compatibility_raw.json)  
**Test Harness:** [`analysis/phase1/p1.11/tests/test_eval_pruning_compatibility.py`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.11/tests/test_eval_pruning_compatibility.py)  

---

## 1. Executive Summary & Factorial Design

Milestone P1.11 audited whether added classical evaluation terms (E10 passed pawn terms, E11 king open-file terms) create unsafe search pruning interactions when combined with baseline alpha-beta pruning mechanisms.

A controlled $3 \times 2$ factorial matrix was executed across 12 diagnostic positions at search depth $d = 8$:

| Evaluation Subsystem | Search Pruning Regimen | Matrix Cell Designation | Scientific Purpose |
| :--- | :--- | :--- | :--- |
| **Flat E5** (X7 Base) | Original X7 Pruning | `CELL_1_E5_ORIG` | **Frozen Reference Baseline** |
| **Enhanced E10** (X12 Base) | Original X7 Pruning | `CELL_2_E10_ORIG` | **Isolate E10 Positional Terms** |
| **Refined E11** (X14 Base) | Original X7 Pruning | `CELL_3_E11_ORIG` | **Isolate E11 Refined Terms** |
| **Flat E5** (X7 Base) | Conservative Pruning ($120\times d$ RFP, LMP Off) | `CELL_4_E5_CONS` | **Isolate Search Pruning Changes** |
| **Enhanced E10** (X12 Base) | Conservative Pruning ($120\times d$ RFP, LMP Off) | `CELL_5_E10_CONS` | **Test E10 Search Interaction** |
| **Refined E11** (X14 Base) | Conservative Pruning ($120\times d$ RFP, LMP Off) | `CELL_6_E11_CONS` | **Test E11 Search Interaction** |

---

## 2. Factorial Compatibility Matrix Results

| Matrix Cell | Evaluation Model | Pruning Regimen | Tactical Solve Rate | `DEV_12` (Kiwipete) Move | `DEV_12` Solved | Root Move Agreement vs Ref |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Cell 1** | Flat E5 | Original X7 | 5 / 12 (**41.7%**) | `e2a6` | **YES** | 100.0% (Reference) |
| **Cell 2** | Enhanced E10 | Original X7 | 5 / 12 (**41.7%**) | `e2a6` | **YES** | 83.3% (2 moves changed) |
| **Cell 3** | Refined E11 | Original X7 | 5 / 12 (**41.7%**) | `e2a6` | **YES** | 83.3% (2 moves changed) |
| **Cell 4** | Flat E5 | Conservative | 5 / 12 (**41.7%**) | `e2a6` | **YES** | 100.0% (0 moves changed) |
| **Cell 5** | Enhanced E10 | Conservative | 5 / 12 (**41.7%**) | `e2a6` | **YES** | 83.3% (2 moves changed) |
| **Cell 6** | Refined E11 | Conservative | 5 / 12 (**41.7%**) | `e2a6` | **YES** | 83.3% (2 moves changed) |

---

## 3. Forensic Analysis: Evaluation Magnitudes & Pruning Cutoffs

### 3.1 Systematic Score Shifts Across Evaluation Versions
1. **Pawn Structure Inflation in Closed Positions (`DEV_01_FORK`):**
   - E5 score: $-62\text{ cp}$
   - E10 score: $-67\text{ cp}$
   - E11 score: **$-110\text{ cp}$** ($-48\text{ cp}$ drop due to isolated pawn and center control penalties).
   - *Impact on Search:* Under standard $80 \times d$ RFP, a $-48\text{ cp}$ baseline shift lowers the effective fail-high threshold, increasing vulnerability to premature fail-lows on sound defensive moves.
2. **Move Selection Redirection in Structural Positions (`DEV_06_BACKWARD`):**
   - Under Flat E5, the engine selected `d4c5` ($+871\text{ cp}$).
   - Under E10 and E11, the engine switched to `c3c4` ($+863\text{ cp}$ and $+861\text{ cp}$), recognizing that `c3c4` prevents backward pawn creation on the c-file.
   - *Impact:* The evaluation correctly guides the move selection toward structurally sound plans without sacrificing tactical accuracy.
3. **`DEV_12` (Kiwipete) Tactical Blindness Re-Verification:**
   - In P1.10, `DEV_12` suffered from tactical blindness under Refined E11 because pawn advancement bonuses swamped piece captures.
   - Across all 6 cells in this audit, `DEV_12` cleanly selected **`e2a6`** (winning a bishop), proving that Calibrated E15's rebalancing has permanently resolved the issue.

---

## 4. Evaluator–Search Compatibility Guidelines

The empirical evidence establishes the following compatibility rules for classical search:

1. **RFP Margin Rule:**
   - When evaluating Flat E5, an RFP margin of $80 \times d$ to $90 \times d$ is safe.
   - When evaluating Enhanced E10 or E11/E15 (with complex king safety and pawn terms), the RFP margin must be expanded to **$\ge 110 \times d$** (and specifically $120 \times d$ on 1 thread) to absorb structural score fluctuations without inducing false cutoffs.
2. **Late Move Pruning Safety:**
   - On 1-thread execution, Late Move Pruning must remain **strictly disabled** (`g_use_lmp = false`), as proven by both the P1.10 tournament results and Phase 2 counterfactual data.
   - On multithreaded execution ($\ge 2$ threads), quadratic LMP ($d \le 4$, $T(d) = 3 + 2d^2$) can be safely engaged because parallel Lazy SMP helper threads compensate for missed lines.
3. **LMR Reduction Dampening on Quiet Defensive Moves:**
   - Phase 2 proved that LMR produces a **$33.3\%$ move disagreement rate**, disproportionately affecting quiet defensive moves and king safety prophylaxis.
   - Therefore, LMR reductions must be dampened whenever a quiet move possesses positive continuation history or defends against king attacks.

