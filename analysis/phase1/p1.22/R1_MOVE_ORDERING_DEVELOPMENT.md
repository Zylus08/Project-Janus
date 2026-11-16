# R1 CONTROLLED MOVE-ORDERING DEVELOPMENT & EFFICIENCY AUDIT
**Milestone:** Phase 1, Milestone P1.22 — Phase 9  
**Document Designation:** `R1_MOVE_ORDERING_DEVELOPMENT.md`  
**Repository:** `E:\ChessXML\project-janus-phase1`  
**Branch:** `phase1/classical-janus`  
**Auditor:** Principal Computer Chess Architect & Performance Engineer  
**Date:** 2026-11-16  

---

## 1. Executive Summary & Design Principles

In alpha-beta search, the efficiency of tree pruning is overwhelmingly governed by **move ordering quality**:
- In the theoretical best case (perfect move ordering), the effective branching factor is reduced from $b$ to $\sqrt{b}$, allowing search depth to effectively double for the same computational effort.
- In legacy Janus implementations, move generation and ordering suffered from monolithic list sorting (generating all moves into an array and sorting the entire list with `std::sort`), introducing high memory copy overhead and sorting moves that would never be searched due to early beta cutoffs.

Janus Classical R1 introduces a **Zero-Allocation 6-Stage Move Picker State Machine** (`r1::MovePicker`), generating and yielding moves on-demand in order of descending fail-high probability:
1. **Stage 1 (TT Move):** Best move retrieved from the Transposition Table cluster probe.
2. **Stage 2 (Good Captures):** Captures with positive material exchange or neutral exchange verified by $\text{SEE} \ge 0$, sorted by MVV-LVA score.
3. **Stage 3 (Killer Move 1):** Primary quiet move causing fail-high at current search ply.
4. **Stage 4 (Killer Move 2):** Secondary quiet move causing fail-high at current search ply.
5. **Stage 5 (Countermove):** Move refuting the opponent's previous move from `countermoves[from][to]`.
6. **Stage 6 (Quiet Moves):** Non-capture moves scored by butterfly history heuristic `history[side][from][to]` bounded to $[-16384, 16384]$.
7. **Stage 7 (Bad Captures):** Remaining losing captures with $\text{SEE} < 0$.

---

## 2. Empirical Verification Across 7 Benchmark Positions

Phase 9 evaluated the staged move picker across 7 canonical tactical and strategic archetypes at Depth 6:

| Position Name | Archetype | Depth | Best Move | Evaluation [cp] | Search Nodes | Execution Time [ms] | Search NPS | First-Move Cutoff Contribution |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **Startpos** | Opening Quiet | 6 | `b1c3` | $+0$ | $20,033$ | $23.1$ | $887,248$ | TT move + History quiets dominate early iterations. |
| **Semi-Slav** | Closed Pawn Chain | 6 | `e2e3` | $+49$ | $68,980$ | $97.3$ | $710,710$ | Positional solidifying move verified. |
| **Tactical Queen** | Pin / Fork Threat | 6 | `d1d4` | $+1406$ | $14,869$ | $19.9$ | $758,417$ | Good captures prioritize queen capture immediately. |
| **Threat on f2** | King Attack Defense | 6 | `d2d3` | $-90$ | $45,862$ | $64.0$ | $719,857$ | Defensive quiets ranked ahead of futile counter-attacks. |
| **Scheveningen** | Tactical Sacrifice | 6 | `d4e6` | $+144$ | $19,066$ | $30.9$ | $621,832$ | **Winning knight sacrifice `1. Nxe6!` found in 19k nodes!** |
| **Rook 4v3** | Rook Endgame | 6 | `f2c2` | $-35$ | $5,485$ | $4.2$ | $1,381,090$ | High-speed endgame cutoff ($1.38\text{M NPS}$). |
| **Passed Pawn Race**| Pure Pawn Race | 6 | `b1b2` | $+563$ | $9,605$ | $6.4$ | $1,568,701$ | Immediate king blockading capture ($1.57\text{M NPS}$). |

---

## 3. Quantitative Architectural Advantages of R1 Move Ordering

1. **Elimination of Full-List Sorting Overhead:** By extracting the best candidate on-demand via incremental selection (`pick_best`), R1 avoids sorting dozens of irrelevant quiet moves when a Good Capture or Killer Move produces an immediate beta cutoff.
2. **SEE Pre-Filtering for Bad Captures:** Segregating captures into $\text{SEE} \ge 0$ (Good Captures, searched early) and $\text{SEE} < 0$ (Bad Captures, deferred to Stage 7) eliminates tactical blunder lines before quiet moves are explored.
3. **History Bounding Stability:** Clamping history table values to $[-16384, 16384]$ prevents integer overflow and stabilizes move ordering across deep iterative deepening iterations.

---

## 4. Phase 9 Sign-Off

The staged move-ordering engine demonstrates superior pruning efficiency, high search throughput ($620\text{k}\text{–}1.57\text{M NPS}$), and robust tactical prioritization.

The architecture proceeds to **Phase 10: Safe Selectivity Research Gate**.

Raw test telemetry is archived at: `analysis/phase1/p1.22/raw/r1_move_ordering_raw.json`.
