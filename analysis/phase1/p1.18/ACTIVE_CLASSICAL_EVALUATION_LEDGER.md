# Milestone P1.18 — Active Classical Evaluation Architecture Ledger

**Author:** Principal Computer Chess Engine Architect & Classical Evaluation Researcher  
**Date:** November 14, 2026  
**Reference Engine Under Audit:** Janus Classical X22 (`e33f292`)  
**Historical Control Sources:** Janus Classical X7 (`b34e342`), X10 (`milestone p1.5`), X12 (`78ca3d5`), X14 (`milestone p1.9`)  

---

## 1. Executive Summary & Source Provenance

Milestone P1.18 establishes a source-level audit of all classical evaluation terms present in the active codebase (`engine/classical_x/janus_classical_x.cpp`).

Janus Classical X22 executes under **Evaluation Mode 5 (`emode == 5`)**, which inherits the foundational additive architecture of Janus Classical X7, augmented by the **64K Thread-Local Pawn Hash Table** (Milestone P1.16) and **True Outposts with Enemy Pawn Immunity** (Milestone P1.17).

Total evaluation is strictly tapered between Middlegame (MG) and Endgame (EG) via game phase ($0 \le \text{phase} \le 24$):
$$\text{Eval} = \frac{\text{MG} \times \text{phase} + \text{EG} \times (24 - \text{phase})}{24}$$

---

## 2. Pawn Structure Evaluation Ledger

| Feature | Status in X22 | Exact Source Function | Mathematical Formula | MG / EG Values | Cache Dependency | Failure Atlas Risk |
| :--- | :---: | :--- | :--- | :---: | :---: | :--- |
| **Passed Pawns** | **ACTIVE** | `eval_pawn_structure` | `PASSED_PAWN_BONUS[rank]` | MG: `[0, 5, 10, 20, 35, 60, 100, 0]`<br>EG: `[0, 10, 20, 35, 60, 100, 150, 0]` | Cached in Pawn Hash | Ignores blockades |
| **Connected Passers** | **ACTIVE** | `eval_pawn_structure` | `adj_pawns & near_ranks` | $+15\text{ mg} / +25\text{ eg}$ | Cached in Pawn Hash | Sound |
| **Supported Passers** | **ACTIVE** | `eval_pawn_structure` | `pawn_defenders & my_pawns` | $+10\text{ mg} / +20\text{ eg}$ | Cached in Pawn Hash | Sound |
| **Candidate Passers** | *INACTIVE* | `eval_pawn_structure_v2` | No enemy in front span & $adj_{my} \ge adj_{en}$ | $\frac{1}{2}\text{PassedBonus}$ (E10 only) | Not in E5 | Misses outside passers |
| **Isolated Pawns** | **ACTIVE** | `eval_pawn_structure` | `(my_pawns & adj_files) == 0` | $-12\text{ mg} / -20\text{ eg}$ | Cached in Pawn Hash | Equal on open/closed files |
| **Doubled Pawns** | **ACTIVE** | `eval_pawn_structure` | `(cnt - 1) * Penalty` | $-15\text{ mg} / -25\text{ eg}$ | Cached in Pawn Hash | Equal on open/closed files |
| **Backward Pawns** | *INACTIVE* | `eval_pawn_structure_v2` | Stop square attacked by enemy pawn, no friendly support behind | $-10\text{ mg} / -15\text{ eg}$ (E10 only) | Not in E5 | **Major Blind Spot** |
| **Connected Non-Passers** | *ABSENT* | — | None | $0 / 0$ | None | Cannot value phalanxes |
| **Pawn Islands** | *INACTIVE* | `eval_pawn_structure_v2` | `(islands - 1) * Penalty` | $-8\text{ mg} / -12\text{ eg}$ (E10 only) | Not in E5 | Minor impact |
| **Blockaded Passers** | *ABSENT* | — | None | $0 / 0$ | None | Overvalues blocked passers |
| **Pawn Storms** | *ABSENT* | — | None | $0 / 0$ | None | Blind to pawn charges |

---

## 3. King Safety Evaluation Ledger

| Feature | Status in X22 | Exact Source Function | Mathematical Formula | MG / EG Values | Cache Dependency | Failure Atlas Risk |
| :--- | :---: | :--- | :--- | :---: | :---: | :--- |
| **King Pawn Shield** | **ACTIVE** | `eval_king_safety` | $-15\text{ mg} \times \text{missing\_pawns}$ on $kf-1, kf, kf+1$ | $-15\text{ mg} / 0\text{ eg}$ | None (Dynamic) | Coarse, ignores advanced storm |
| **King Ring Attackers** | **ACTIVE** | `eval_king_safety` | $N=2, B=2, R=3, Q=5$; If $\text{att} \ge 2: -\min(200, 2 \times \text{units}^2)$ | Quadratic up to $-200\text{ mg}$ | None (Dynamic) | Sound quadratic curve |
| **Open File King Exposure**| *ABSENT* | — | None | $0 / 0$ | None | **Critical Blind Spot** |
| **Safe Checking Threats** | *ABSENT* | — | None | $0 / 0$ | None | Blind to checks until qsearch |
| **Attacker Coordination** | *ABSENT* | — | Simple sum of attack units | $0 / 0$ | None | Treats isolated threats as coordinated |
| **Defending Pieces** | *ABSENT* | — | None | $0 / 0$ | None | Over-penalizes well-defended kings |
| **Endgame King Safety** | **ACTIVE** | `eval_king_safety` | King safety strictly zeroed out in EG (mg only) | MG only | Tapered | Sound |

---

## 4. Other Positional Evaluation Ledger

| Feature | Status in X22 | Exact Source Function | Mathematical Formula | MG / EG Values | Correctness / Status |
| :--- | :---: | :--- | :--- | :---: | :--- |
| **True Knight Outpost** | **ACTIVE** | `eval_mobility_and_coordination` | Rank 4–6, defended by pawn, **no enemy pawn on adjacent files can ever attack** | $+28\text{ mg} / +18\text{ eg}$ | **P1.17 Addition (Verified Sound)** |
| **Transient Knight Outpost**| **ACTIVE** | `eval_mobility_and_coordination` | Rank 4–6, defended by pawn, but kickable by enemy pawn | $+8\text{ mg} / +4\text{ eg}$ | P1.17 Addition |
| **True Bishop Outpost** | **ACTIVE** | `eval_mobility_and_coordination` | Rank 4–6, files c–f, defended by pawn, enemy pawn immune | $+22\text{ mg} / +14\text{ eg}$ | P1.17 Addition |
| **Transient Bishop Outpost**| **ACTIVE** | `eval_mobility_and_coordination` | Rank 4–6, files c–f, defended by pawn, but kickable | $+6\text{ mg} / +3\text{ eg}$ | P1.17 Addition |
| **Bishop Pair** | **ACTIVE** | `eval_mobility_and_coordination` | $\text{popcount}(Bishops) \ge 2$ | $+30\text{ mg} / +50\text{ eg}$ | Standard Classical |
| **Rook on Open File** | **ACTIVE** | `eval_mobility_and_coordination` | No friendly or enemy pawns on file | $+20\text{ mg} / +25\text{ eg}$ | Standard Classical |
| **Rook on Semi-Open File**| **ACTIVE** | `eval_mobility_and_coordination` | No friendly pawn, enemy pawn present on file | $+10\text{ mg} / +15\text{ eg}$ | Standard Classical |
| **Rook on 7th Rank** | **ACTIVE** | `eval_mobility_and_coordination` | Rank 7 (White) / Rank 2 (Black) | $+20\text{ mg} / +35\text{ eg}$ | Standard Classical |
| **Piece Mobility** | **ACTIVE** | `eval_mobility_and_coordination` | $(mob - baseline) \times weight$ | Scaled per piece | Safe squares (not attacked by enemy pawns) |
| **King Centralization (EG)**| **ACTIVE** | `eval_endgame_positional` | $(14 - \text{center\_dist}) \times 2$ | $0\text{ mg} / \text{EG}$ | Manhattan distance to e4/d4/e5/d5 |
| **Passed Pawn Escort (EG)** | **ACTIVE** | `eval_endgame_positional` | King proximity to passed pawns | $\pm 3\text{ eg} \times (8 - dist)$ | Friendly bonus / Enemy penalty |

---

## 5. Architectural Comparison: X7 vs X10 vs X12 vs X14 vs X22

1. **X7 (Qualified 1T Baseline):** Base E5 evaluation, no pawn hash, legacy Q0 quiescence (illegal stand-pat while checked), legacy pseudo-outposts without pawn immunity.
2. **X10 (Milestone P1.5):** Introduced experimental E10 terms (backward pawns, candidate passers, pawn islands, queen-contact king safety), but suffered from non-linearities and high evaluation latency ($-35\%$ NPS), leading to rejection.
3. **X12 (Qualified 4T Baseline):** X7 search and evaluation scaled to 4 threads via ABDADA SMP.
4. **X14 (Milestone P1.9):** Refined E11 evaluation, but lacked thread-safe pawn caching.
5. **X22 (Current Leading Reference):** Corrected Q1 quiescence search (mandatory check evasions, no stand-pat under check), 64K thread-local pawn hash table ($+52\%$ eval speedup), and True Outposts with Enemy Pawn Immunity.
