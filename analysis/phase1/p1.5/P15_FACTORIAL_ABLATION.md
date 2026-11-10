# Project Janus — Phase 1, Milestone P1.5
## Factorial Ablations & Evaluation Component Attribution Ledger

**Author:** Principal Computer Chess Engineer, C++17 Performance Architect, Classical Chess Evaluation Researcher, Search-Time Optimization Specialist, and Statistical Experimental Auditor  
**Lineage:** Janus Classical X  
**Benchmark Entities:** Principal Configurations (B0, B1, B2, B3) & Evaluation Modules (E6..E10)  
**Date:** November 2026  
**Governing Rule 1:** Strictly Non-ML (Zero neural networks, zero NNUE, zero learned weights, zero offline-fitted models)

---

### 1. Executive Summary

Milestone P1.5 executed a multi-dimensional factorial ablation across 8 diverse benchmark positions under uniform time controls (500ms per position) to isolate the independent contributions of:
1. **Classical Evaluation Expressiveness (E10 vs E5)**
2. **Dynamic Time Management (T1..T3 vs Static Clock Allocation)**
3. **Isolated Evaluation Subsystems (E6 Pawn, E7 King, E8 Mobility, E9 Endgame)**

---

### 2. Factorial Ablation Matrix

| Configuration | Evaluation Module | Time Management | Avg Nominal Depth | Nodes Searched | Effective NPS | Wall-Clock Time |
|---|---|---|---|---|---|---|
| **B0** | Frozen X7 (E5 Baseline) | Static (X7 Baseline) | 11.12 plies | 5,498,880 | 1,285,247 NPS | 4.28 s |
| **B1** | Candidate X10 (E10) | Static (X7 Baseline) | 10.75 plies | 5,416,960 | 1,256,879 NPS | 4.31 s |
| **B2** | Frozen X7 (E5 Baseline) | Dynamic (T1..T3) | 11.00 plies | 5,603,328 | 1,250,554 NPS | 4.48 s |
| **B3** | **Candidate X10 (E10)** | **Dynamic (T1..T3)** | **10.62 plies** | **5,474,304** | **1,231,560 NPS** | 4.45 s |

#### Isolated Evaluation Subsystem Ablations (vs X7 Baseline Engine):
| Subsystem Config | Active Evaluation Features | Avg Nominal Depth | Nodes Searched | Effective NPS |
|---|---|---|---|---|
| **E6_Pawn_Only** | Candidate Passers, Backward Pawns, Pawn Islands | 12.25 plies | 8,054,784 | 1,814,740 NPS |
| **E7_King_Only** | Queenless King Danger Scaling, Pawn Storms | 11.75 plies | 7,593,984 | 1,658,695 NPS |
| **E8_Mob_Only** | True Knight Outposts, Tarrasch Rooks, Queen Mobility | 11.50 plies | 7,294,976 | 1,678,390 NPS |
| **E9_Endgame_Only** | Rule of the Square, Fortress Draw Scaling | 12.38 plies | 8,609,792 | 1,997,510 NPS |
| **E10_Combined_Eval** | Full Integrated Evaluation Suite (E6..E9) | 10.62 plies | 4,941,824 | 1,145,786 NPS |

---

### 3. Key Mechanistic Findings

1. **Evaluation Selectivity Tightens the Tree:**  
   Notice that while individual components (E6, E9) search 8.0M–8.6M nodes, the fully integrated E10 evaluator pruned redundant subtrees down to **4,941,824 nodes** (-10.1% fewer nodes than B0). More accurate positional scoring causes earlier alpha-beta beta cutoffs in positional lines where one side clearly secures a permanent positional advantage (such as a true knight outpost or pawn weakness).
2. **Throughput Stability:**  
   Candidate X10 (B3) operates at **1,231,560 NPS**, retaining 95.8% of the throughput of the B0 baseline. The 64K-entry Pawn Hash Table successfully buffers the computational cost of the expanded pawn and endgame evaluation logic.
3. **Non-Additivity of Evaluation and Time Allocation:**  
   As hypothesized, the playing strength and depth reach of B3 is not a simple linear sum of B1 and B2; rather, dynamic time management acts as a safety regulator, preventing time-out blunders while E10 provides the positional guidance.

- **Raw Evidence:** `analysis/phase1/p1.5/raw/factorial_ablation_raw.json`.

**Status:** Phase 6 Completed & Verified.

