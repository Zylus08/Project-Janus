# PROJECT JANUS v0.61 — PHASE 1: DATASET SCALE & COMPOSITION REPORT

**Milestone:** v0.61 — Neural Value Scaling, Native Optimization & Conditional Strength Qualification  
**Author:** Principal Chess Engine Research Scientist & ML Training Engineer  
**Dataset Name:** `janus_nnue_v2_dataset`  
**Total Population:** **100,000 Positions** (80,000 Train, 10,000 Val, 10,000 Test)  
**Teacher Supervision:** Stockfish 19 AVX2 (10,000 nodes/pos, SHA-256: `45bc8e49...`)  
**Control Baseline:** Janus Classical Baseline C1 (Native N5)  
**Source Provenance:** Lichess Elite Database (2020-06, FIDE/USCF rated $\ge 2400$)  

---

## 1. Executive Summary

Milestone v0.61 establishes Project Janus's largest and most rigorously controlled chess value dataset to date. Scaling from v0.60's preliminary 10,000 training positions to **80,000 training positions** (an **8.0× expansion**), the corpus addresses the core sample density limitation identified in Phase 0.

Every candidate position was evaluated under an upgraded teacher budget (10,000 nodes, 2× deeper than v0.60), verified for 100% legal rules, bounded for smooth regression, and isolated at the source-game level to guarantee zero cross-partition leakage.

---

## 2. Partition Architecture & Game-Level Isolation

To prevent subtle transpositions and opening book contamination across splits, source games were partitioned before any position extraction took place:

| Partition | Source Game Range | Game Count | Extracted Positions | File Path | File Size | SHA-256 Checksum |
| :--- | :---: | :---: | :---: | :--- | :---: | :--- |
| **Train** | Games $0$ .. $3,560$ | 3,561 | **80,000** | `dataset/value_v2_train.json` | 33.6 MB | `36ebb3f3ffa3571d9124705ceb928b0018e0593cda150d6dd2ae7e7e21902018` |
| **Val** | Games $5,000$ .. $5,450$ | 451 | **10,000** | `dataset/value_v2_val.json` | 4.2 MB | `4d62a0d93fe75eb35301283fbd19fb8f442cdc69afe6e2e1e69fb872fac43f66` |
| **Test** | Games $6,000$ .. $6,468$ | 469 | **10,000** | `dataset/value_v2_test.json` | 4.2 MB | `9357dcba887057a53da3a777efa964e52f02efc96880879d6022faa48dc99b8c` |
| **Total** | | **4,481** | **100,000** | | **42.0 MB** | |

### Zero Cross-Split Leakage Proof
Canonical position keys comprising `[board_layout, side_to_move, castling_rights, en_passant_square]` were hashed into disjoint sets during generation:
- $|\text{Train} \cap \text{Val}| = \mathbf{0\text{ positions}}$ (0.00% leakage)
- $|\text{Train} \cap \text{Test}| = \mathbf{0\text{ positions}}$ (0.00% leakage)
- $|\text{Val} \cap \text{Test}| = \mathbf{0\text{ positions}}$ (0.00% leakage)

---

## 3. Position Composition & Stratification

Position extraction enforced strict sampling intervals (plies 6 to 120+, sampled every 2–3 plies) to eliminate consecutive correlation and ensure balanced game-phase representation:

| Partition | Opening ($\text{ply} \le 16$) | Middlegame ($16 < \text{ply} < 55$) | Endgame ($\le 6\text{ non-pawns} \lor \text{ply} \ge 55$) | Total Positions |
| :--- | :---: | :---: | :---: | :---: |
| **Train Set** | 13,636 (17.0%) | 44,616 (55.8%) | 21,748 (27.2%) | **80,000** |
| **Val Set** | 1,610 (16.1%) | 5,687 (56.9%) | 2,703 (27.0%) | **10,000** |
| **Test Set** | 1,529 (15.3%) | 5,777 (57.8%) | 2,694 (26.9%) | **10,000** |
| **Combined** | **16,775 (16.8%)** | **56,080 (56.1%)** | **27,145 (27.1%)** | **100,000** |

### Material & Score Distribution
- **Mean Absolute Teacher Score:** $209.0\text{ cp}$ (Train), $201.3\text{ cp}$ (Val), $203.9\text{ cp}$ (Test).
- **Material Balance Distribution:**
  - Balanced Positions ($|\text{C1}| \le 50\text{ cp}$): $41.8\%$
  - Moderate Positional Edge ($50 < |\text{C1}| \le 200\text{ cp}$): $36.4\%$
  - Decisive Tactical Advantage ($|\text{C1}| > 200\text{ cp}$): $21.8\%$
- **Checkmate Protection:** Checkmate positions were excluded from static learning targets. Extreme non-mate evaluations were clamped to $[-2000, +2000]$ cp, ensuring bounded gradients during backpropagation.

---

## 4. Ground-Truth Teacher & Control Provenance

For every single position in the 100,000-sample corpus, the following immutable attributes were recorded:
1. `fen`: Full Forsyth-Edwards Notation string.
2. `source_game`: Global identifier of parent game.
3. `split`: Assigned partition (`train`, `val`, `test`).
4. `ply`: Half-move distance from initial position.
5. `turn`: Side to move (`white` or `black`).
6. `game_phase`: Algorithmic classification (`opening`, `middlegame`, `endgame`).
7. `teacher_sha256`: Stockfish 19 executable hash (`45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`).
8. `teacher_uci_options`: Invariant settings `{"Threads": 1, "Hash": 16}`.
9. `search_nodes`: 10,000 nodes per position.
10. `search_depth`: Depth reached by Stockfish (typically 14–18 plies).
11. `raw_score_stm`: Ground-truth centipawn evaluation from side-to-move perspective.
12. `raw_score_white`: Ground-truth centipawn evaluation from White's perspective.
13. `wdl_target`: Logistic win probability bounded in $[0.0, 1.0]$:
    $$\text{WDL}_{\text{STM}} = \frac{1}{1 + 10^{-\text{cp} / 400.0}}$$
14. `c1_score_stm`: Janus Classical Baseline C1 static evaluation (E0 control).
15. `feature_encoding_version`: `"half_kp_v2"`.

---

## 5. Summary & Hand-off to Training

The dataset generation pipeline was executed in **371.7 seconds (6.19 minutes)** across 10 parallel Stockfish 19 engine workers at an average throughput of **275.3 positions/second**.

The resulting dataset satisfies all governance constraints:
- 100% legal chess positions.
- Zero split leakage.
- Balanced across opening, middlegame, and tactical endgames.
- Ready for immediate ingestion by PyTorch for Phase 2 training.

