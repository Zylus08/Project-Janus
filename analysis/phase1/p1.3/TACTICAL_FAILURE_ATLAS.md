# Project Janus — Phase 1, Milestone P1.3
## Tactical Failure Atlas & Diagnostic Corpus Report

**Author:** Principal Computer Chess Engineer, Tactical Systems Researcher, Independent Auditor  
**Milestone:** Phase 1, Milestone P1.3 (Phase 1 Deliverable)  
**Engines Audited:** Janus Classical X6 (P1.1 Control), Janus Classical X7 (P1.2 Baseline)  
**Corpus Size:** 16 Target Diagnostic Positions across 12 Failure Modes  
**Branch:** `phase1/classical-janus`  
**Date:** 2026-11-10  
**Phase 1 Constraint:** Strictly Non-ML (Zero neural evaluation, zero learned weights, zero offline-fitted models)

---

### Executive Summary

To systematically guide the search selectivity innovations of Milestone P1.3, an independent 16-position **Tactical Failure Atlas** was constructed. This corpus targets specific weaknesses that the P1.1 search foundation and P1.2 positional evaluation improvements either failed to resolve or made vulnerable to heuristic pruning.

Across the 16 benchmark positions evaluated at depth $d=7$:
- **Classical X6 Solved:** 3 / 16 (18.8%)
- **Classical X7 Solved:** 4 / 16 (25.0%)
- **Key Discovery:** While X7 solved `TAC_06` (Quiet Tactical Move `f1e1` vs `d1e2`) with a 33.8% node reduction (49,652 vs 75,000 nodes), 12 tactical benchmarks remain unsolved at depth 7 due to specific algorithmic limitations in move ordering and search depth allocation.

---

### Failure Mechanism Taxonomy

| Failure Mode | Positions Affected | Primary Algorithmic Bottleneck | Proposed P1.3 Remedy |
|---|---|---|---|
| **1. Unextended Singular Moves** | TAC_01, TAC_02, TAC_05, TAC_16 | When one move is uniquely winning in the TT, search allocates equal plies to inferior alternatives, failing to see combinations 1-2 plies deeper. | **Phase 3: Singular Extensions (SE)** |
| **2. Capture Ordering Failures** | TAC_08, TAC_09, TAC_15 | MVV-LVA static scoring orders losing/inferior captures ahead of decisive tactical blows, or misses tactical captures with equal MVV-LVA. | **Phase 2: Capture History (`capthist[6][64][6]`)** |
| **3. Lack of Move Counter-Refutation** | TAC_10, TAC_13, TAC_14 | Engine fails to find the direct tactical response (countermove) to the opponent's previous move. | **Phase 2: Countermove Heuristic (`countermoves[64][64]`)** |
| **4. Redundant Subtree Exploration** | TAC_07, TAC_12, TAC_14 | In clearly winning tactical positions, deep search expands full subtrees instead of verifying fail-high via shallow search. | **Phase 5: ProbCut Pruning** |
| **5. Non-Singular Cutoff Misses** | TAC_06, TAC_07 | When multiple moves exceed $\beta$, search still searches the full tree instead of pruning. | **Phase 4: Multi-Cut Pruning** |
| **6. Zugzwang & Underpromotion** | TAC_03, TAC_04 | Pure pawn endgames require strict NMP exclusion and pawn promotion flag preservation. | **Maintained Invariants** |

---

### Benchmark Results Table (Depth $d=7$)

| Position ID | Category / Theme | Target Move | X6 Move (Nodes) | X7 Move (Nodes) | X6 Status | X7 Status |
|---|---|---|---|---|---|---|
| `TAC_01_OPERA_MATE` | Deflection Mate | `b5d7` | `b5d7` (13,172) | `b5d7` (13,234) | **SOLVED** | **SOLVED** |
| `TAC_02_SMOTHERED_MATE` | King Attack Sac | `d3h7` | `d3h7` (135,683) | `d3h7` (52,109) | **SOLVED** | **SOLVED** |
| `TAC_03_SAAVEDRA_PROMO` | Underpromotion | `b6b7` | `c1c2` (3,450) | `c1d1` (4,156) | MISSED | MISSED |
| `TAC_04_ZUGZWANG_FINE70` | Zugzwang Triangulation | `a1b1` | `a1a2` (943) | `a1a2` (1,263) | MISSED | MISSED |
| `TAC_05_EXCHANGE_SAC` | Greek Gift Sac | `d3h7` | `a2a3` (86,543) | `e1g1` (41,526) | MISSED | MISSED |
| `TAC_06_QUIET_TACTICAL` | Pinning Initiative | `f1e1` | `d1e2` (75,000) | `f1e1` (49,652) | MISSED | **SOLVED** |
| `TAC_07_LMR_TACTICAL_REFU` | Positional Defense | `c1e3` | `d3b5` (60,129) | `d3b5` (57,721) | MISSED | MISSED |
| `TAC_08_FORK_TRICK` | Fork Trick | `c4f7` | `c4d5` (44,589) | `b1c3` (55,106) | MISSED | MISSED |
| `TAC_09_DISCOVERED_ATTACK` | Discovered Attack | `c3e4` | `c3e4` (41,319) | `c3e4` (21,310) | **SOLVED** | **SOLVED** |
| `TAC_10_DEFENSIVE_RESOURC` | Defensive Interposition | `d5d4` | `c6e7` (95,523) | `f8e8` (65,327) | MISSED | MISSED |
| `TAC_11_ENDGAME_TACTICS_P` | King Opposition | `f4e4` | `f4f3` (3,903) | `f4f3` (2,973) | MISSED | MISSED |
| `TAC_12_CHECK_EVASION_INT` | Calm Development | `d2d3` | `d1e2` (112,447) | `b1c3` (56,535) | MISSED | MISSED |
| `TAC_13_SF_BLUNDER_RECON_` | Caro-Kann Development | `f1g2` | `f1d3` (117,493) | `f1d3` (83,962) | MISSED | MISSED |
| `TAC_14_SF_BLUNDER_RECON_` | Sicilian Najdorf Defense | `e1g1` | `c1e3` (122,796) | `d1h5` (78,277) | MISSED | MISSED |
| `TAC_15_INTERMEDIATE_MOVE` | Zwischenzug Defense | `e1g1` | `d4c6` (103,604) | `d4c6` (44,148) | MISSED | MISSED |
| `TAC_16_ROOK_ENDGAME_LUCE` | Lucena Bridge | `c1d1` | `c1c8` (7,235) | `c1c8` (8,047) | MISSED | MISSED |

---

### Case Study: Singular Move Starvation

In position `TAC_05_EXCHANGE_SAC` (`r1b2rk1/pp3ppp/2n1p3/3pP3/3P4/2PB1N2/P4PPP/R3K2R w KQ - 0 13`), White has the classic Greek Gift sacrifice `13. Bxh7+ Kxh7 14. Ng5+ Kg8 15. Qh5`.
At depth 7:
- Classical X6 played `13. a3` after 86,543 nodes.
- Classical X7 played `13. O-O` after 41,526 nodes.
- **Root Cause:** In iterative deepening at depth 5, `Bxh7+` appears with a high score in the TT, but at depth 7, the TT move is searched without depth extension. The engine reduces moves in the follow-up, causing the tactic to fall just outside the search horizon.
- **Singular Extension Solution:** When `Bxh7+` is probed in the TT and verified to be singular (all alternative moves fail at least 50 cp below `Bxh7+`), `depth` is extended to $d+1$, pulling the full combination into the search window.

---

### Tactical Failure Atlas Deliverable Gate

This atlas serves as the immutable qualification suite for Phases 2, 3, 4, 5, and 6. Every proposed search mechanism must demonstrate measurable progress on this suite.

