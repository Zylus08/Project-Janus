# P1.15 SCIENTIFIC EVIDENCE RECONCILIATION

**Project:** Project Janus — Phase 1, Milestone P1.16  
**Auditor:** Principal Computer Chess Engineer, Statistical Auditor & Search Architect  
**Date:** November 14, 2026  
**Repository Branch:** `phase1/classical-janus`  
**Expected HEAD:** `2226c0c` (Verified atop commit `00ef7ce`)  
**Deliverable:** `analysis/phase1/p1.16/P115_EVIDENCE_RECONCILIATION.md`  

---

## 1. Executive Summary & Repository Verification

All 420 games from the Milestone P1.15 tournament suite have been independently reconstructed and audited from their raw PGN records. Every individual match score, win-draw-loss distribution, and pentanomial pair grouping matches the reported telemetry with 100.00% precision.

### Binary and Baseline Integrity Audits:
| Engine | Source / Location | SHA-256 | Verification Status |
|---|---|---|---|
| **Janus Classical X7** (1T Baseline) | `analysis/phase1/p1.3/control/janus_classical_x7.exe` | `86392A2F4BD4182A4D7DC21E32940BD7939F6816794D5E1AB02F4082431CA28B` | **PASS (Immutable)** |
| **Janus Classical X12** (4T Baseline) | `analysis/phase1/p1.7/control/janus_classical_x12.exe` | `00B4F5FEDEA02A392A1AF9713A96512E5199A0E3AE55C295AD1C7CFFF1B47059` | **PASS (Immutable)** |
| **Janus Classical X19** (Research Ref) | `analysis/phase1/p1.14/control/janus_classical_x19.exe` | `CBB7785A47E5F9EC64C51C20B8387DE3EFE782F42BDFCEA38008F6450E534629` | **PASS (Frozen)** |
| **Janus Classical X20** (Archived Cand) | `analysis/phase1/p1.15/control/janus_classical_x20.exe` | `AF126A4D22C312F2AE61014A56005B9E9BAFD022F95A17DA81D81769048F7415` | **PASS (Archived)** |
| **Stockfish 4** | `E:/ChessXML/tools/stockfish_4/stockfish_4.exe` | `1128CAB83386063359947F04155A2210C966080E71176DD385D8BDC3B6C32674` | **PASS (Reference)** |
| **Stockfish 11** | `E:/ChessXML/tools/stockfish_11/stockfish_11.exe` | `B004C03BD71BB84E8BC1832C580E72A7E883F121E1834EA6DA2802D1575E8048` | **PASS (Reference)** |
| **Stockfish 19** (NNUE) | `E:/ChessXML/tools/stockfish/stockfish.exe` | `45BC8E4969147DB9C2EB533810637994619BFF0EACC81CCFD9854394901BCBD0` | **PASS (Benchmark)** |

---

## 2. Reconstructed Match Audits & Pentanomial Distributions (420 Games)

Pentanomial pair distributions are grouped strictly by colour-reversed opening pairs:
- **`[2]`**: Candidate won both games (+2 pts).
- **`[1]`**: Candidate won one, drew one (+1.5 pts).
- **`[0]`**: One win, one loss OR two draws (+1.0 pt).
- **`[-1]`**: One draw, one loss (+0.5 pt).
- **`[-2]`**: Candidate lost both games (0.0 pts).

| Match ID | Description | Games | Score | Score (%) | W-D-L | Pentanomial `[+2, +1, 0, -1, -2]` | Elo Diff | Paired 95% CI | One-sided p-value | Reconstructed Match? |
|---|---|---|---|---|---|---|---|---|---|---|
| **Match 1** | X20-S vs X7 Baseline (Fast) | 100 | 46.0 / 100 | 46.00% | 27 - 38 - 35 | `[8, 9, 9, 15, 9]` | -27.9 | $[36.57\%, 55.43\%]$ | 0.7971 | **EXACT PASS** |
| **Match 2** | X20-S vs X7 Baseline (Slower) | 50 | 24.0 / 50 | 48.00% | 17 - 14 - 19 | `[1, 5, 11, 7, 1]` | -13.9 | $[39.09\%, 56.91\%]$ | 0.6700 | **EXACT PASS** |
| **Match 3** | X20-P vs X12 Baseline (4T) | 100 | 46.5 / 100 | 46.50% | 26 - 41 - 33 | `[3, 12, 15, 15, 5]` | -24.4 | $[38.96\%, 54.04\%]$ | 0.8185 | **EXACT PASS** |
| **Match 4** | X20-S vs X19-S Reference | 50 | 22.5 / 50 | 45.00% | 11 - 23 - 16 | `[1, 7, 6, 8, 3]` | -34.9 | $[34.04\%, 55.96\%]$ | 0.8145 | **EXACT PASS** |
| **Match 5** | X20-S vs Stockfish 4 | 40 | 1.5 / 40 | 3.75% | 0 - 3 - 37 | `[0, 0, 0, 3, 17]` | -563.7 | $[0.00\%, 7.76\%]$ | 1.0000 | **EXACT PASS** |
| **Match 6** | X20-S vs Stockfish 11 | 40 | 0.5 / 40 | 1.25% | 0 - 1 - 39 | `[0, 0, 0, 1, 19]` | -759.1 | $[0.00\%, 3.70\%]$ | 1.0000 | **EXACT PASS** |
| **Match 7** | X20-S vs Stockfish 19 | 40 | 0.5 / 40 | 1.25% | 0 - 1 - 39 | `[0, 0, 0, 1, 19]` | -759.1 | $[0.00\%, 3.70\%]$ | 1.0000 | **EXACT PASS** |

---

## 3. Critical Audit of Tournament Time Controls

A critical discrepancy between telemetry section headings and tournament execution was audited:
- **Telemetry / Development Ablations (`test_time_control_generalization.py`):** Fixed wall-clock time per move (100ms, 250ms, 500ms, 1000ms, 2500ms, 5000ms).
- **Tournament Execution (`run_p115_tournaments.py`):** Dynamic clock time controls with Fischer increments:
  - Match 1 (Fast): `wtime 1000 btime 1000 winc 50 binc 50` (Fischer 1.0s + 50ms)
  - Match 2 (Slow): `wtime 2500 btime 2500 winc 100 binc 100` (Fischer 2.5s + 100ms)
  - Match 3 (4T Fast): `wtime 1000 btime 1000 winc 50 binc 50` (Fischer 1.0s + 50ms)
  - Match 4 (Ref Fast): `wtime 1000 btime 1000 winc 50 binc 50` (Fischer 1.0s + 50ms)
  - Matches 5–7 (External): `wtime 1500 btime 1500 winc 50 binc 50` (Fischer 1.5s + 50ms)

**Auditor Finding:** Under Fischer 1.0s+50ms, the engine typically allocates $\sim 80\text{--}120\text{ ms}$ per move in the early middlegame. This explains why the telemetry was colloquially referenced as "100ms". However, in formal documentation, these conditions must not be conflated: fixed-time-per-move tests disable time-management heuristics, while Fischer clock tests evaluate practical time-management, low-time panics, and increment safety.

---

## 4. Game 12 Crisis Verification

In Milestone P1.15, Game 12 was highlighted as demonstrating the catastrophic hazard of unconditional negative-SEE capture deferral:
- **Position (FEN):** `r1b1r1k1/1pp2p2/p1n1qBp1/3pPp1p/3P1Q2/2P2N2/P1P2PPP/1R3RK1 b - - 3 16`
- **Context:** White threatens `Qh6` followed by inescapable mate `Qg7#`. Black must find `e8e7` or `e6f6`.
- **Search Outcome Audit:**
  - **C0 (Unconditional Bad-Capture Deferral):** Evaluated 33,550 nodes at depth 8 (0.0241s) before finding `e8e7`.
  - **C1 (Adaptive Near-Even Capture Promotion):** Evaluated 1,796 nodes at depth 8 (0.0012s) to find `e8e7`.
- **Reconciliation Verdict:** The $18.7\times$ search tree reduction in this crisis position is **reproduced and verified**. However, while resolving this tactical horizon failure prevented an outright blunder, it did not produce an engine capable of outplaying X7 across full games.

---

## 5. Scientific Rectification of Unsupported Claims

| Previous Milestone Claim | Empirical Finding | Corrected Scientific Reality |
|---|---|---|
| *"X20's slower-time regression is definitively cured."* | X20 scored $48.0\%$ at 2.5s+100ms vs $46.0\%$ at 1.0s+50ms. | While X20 avoided X19's drop to $43.0\%$, its 95% paired CI $[39.09\%, 56.91\%]$ ($p=0.670$) is statistically indistinguishable from 50%. Slower-time performance stabilized to parity, but no superiority is established. |
| *"A 98.96% first-move cutoff rate guarantees a near-minimal tree."* | $\text{BF}_1$ measures branch pruning only at CUT-nodes. | In alpha-beta search, ALL-nodes require full branch enumeration. Move-ordering improvements saturate once $\text{BF}_1 > 95\%$; tree size at ALL-nodes and PV-nodes remains dominated by branch branching factor and evaluation accuracy. |
| *"SEE passing 12 classes proves universal SEE correctness."* | The test suite validates standard piece trades. | Handcrafted SEE lacks full awareness of overloaded defenders, discovered pins, and multi-piece battery deflections. Passing 12 exchange classes proves local static validity, not universal correctness. |
| *"A 98.58% node reduction establishes better playing strength."* | Node reduction measures selectivity, not chess quality. | Aggressive move ordering and pruning reduce searched nodes, but can discard subtle positional improvements or quiet defensive moves. Node reduction without Elo gain is search economy, not strength advancement. |
| *"Shallow minimax tests prove tactical completeness."* | Full-width alpha-beta matched minimax at depths 1–4. | Minimax identity at shallow depths (1–4) tests basic move legality and minimax equivalence. It does not test tactical quiescence horizons, deep king safety, or zugzwang. |

---

## 6. Phase 0 Audit Conclusion

The scientific foundation is reconciled. The frozen baselines X7 (`b34e342`) and X12 (`78ca3d5`) remain the undefeated champions of classical Project Janus. Milestone P1.16 now proceeds to **Phase 1: Authoritative Evaluation Feature Inventory**.
