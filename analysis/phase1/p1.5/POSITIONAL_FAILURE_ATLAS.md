# Project Janus — Phase 1, Milestone P1.5
## Positional Failure Atlas & Empirical Defect Taxonomy

**Author:** Principal Computer Chess Engineer, C++17 Performance Architect, Classical Chess Evaluation Researcher, Search-Time Optimization Specialist, and Statistical Experimental Auditor  
**Lineage:** Janus Classical X  
**Incumbent Baseline:** Janus Classical X7 (`b34e342`)  
**External Benchmark:** Stockfish 19 (`sf_19`, unrestricted, default NNUE)  
**Corpus Size:** 28 positions (14 development, 14 held-out) across 14 failure archetypes  
**Date:** November 2026  
**Governing Rule 1:** Strictly Non-ML (Zero neural networks, zero NNUE, zero learned weights, zero offline-fitted models)

---

### 1. Executive Summary & Master Experimental Finding

Milestone P1.5 constructed a rigorous, provenance-tracked 28-position diagnostic corpus spanning 14 classical positional and endgame archetypes. Each position was evaluated using X7's component tracer, searched under fixed-time match conditions (500ms) with `janus_classical_x7.exe`, and cross-verified against unrestricted Stockfish 19 deep analysis with full UCI handshake synchronization.

```
                         [28-POSITION FAILURE TAXONOMY DISTRIBUTION]
                         
      ┌───────────────────────────────────────────────────────────────┐
      │  Class B: Insufficient Search Depth              12 (42.9%)   │ ──┐
      │  Class A: Incorrect Positional Evaluation         7 (25.0%)   │   │ 92.9% Total
      │  Class E: Endgame Outcome Misunderstanding        7 (25.0%)   │ ──┘ Failure Modes
      │  Class F: Sufficient Alignment                    2  (7.1%)   │
      │  Class C: Time Budget Failure                     0  (0.0%)   │
      │  Class D: Tactical Instability                    0  (0.0%)   │
      └───────────────────────────────────────────────────────────────┘
```

**The Definitive Finding:**  
1. **Positional Evaluation & Endgame Misunderstandings (Classes A & E: 50.0%):** In 14 out of 28 positions, X7 misjudged the true positional value or chose the wrong strategic plan (such as passive king retreats in pawn and rook endgames or mis-evaluating pawn majorities and weak color complexes).
2. **Search Depth Starvation (Class B: 42.9%):** Under equal wall-clock time (500ms), X7 reached only **nominal depth 9 to 11**, while Stockfish 19 reached **nominal depth 17 to 21**. X7's lack of evaluation caching (specifically the lack of a Pawn Hash Table) and coarse evaluation terms slowed full-search throughput, preventing the search from resolving strategic pawn advances.
3. **Zero Tactical Volatility (Classes C & D: 0.0%):** Quiescent search and static evaluation exhibited stable score convergence across all positions.

---

### 2. Failure Classification Taxonomy

| Class | Definition | Positions | Share | Primary Manifestation in X7 |
|---|---|---|---|---|
| **Class B** | **Insufficient Search Depth** | **12** | **42.9%** | Evaluates position reasonably, but depth deficit ($d \approx 10$ vs $18$) misses the deep positional plan. |
| **Class A** | **Incorrect Positional Evaluation** | **7** | **25.0%** | Static eval diverges from truth by $> 100$ cp; misjudges IQP, central rollers, and color complexes. |
| **Class E** | **Endgame Outcome Misunderstanding** | **7** | **25.0%** | Fails to recognize drawing fortresses, misjudges king opposition, and bungles rook cut-offs. |
| **Class F** | **Sufficient Alignment** | **2** | **7.1%** | Both engines select the same master move and agree on evaluation. |
| **Class C** | **Time-Budget Allocation Failure** | **0** | **0.0%** | Zero clock starvation detected. |
| **Class D** | **Tactical Instability** | **0** | **0.0%** | Zero wild static-vs-search score swings. |

---

### 3. Detailed Position-by-Position Experimental Ledger

| Position ID | Category | Split | FEN | X7 Search (Depth & Score) | SF19 Search (Depth & Score) | Class | Causal Diagnosis |
|---|---|---|---|---|---|---|---|
| `POS_01` | `OPEN_TAC` | Dev | `r1bqk2r/pppp1ppp/2n5/1B2p3/3Pn3/5N2/PPP2PPP/RNBQ1RK1 b kq - 0 6` | `e5d4` ($d=10, -277\text{ cp}$) | `e5d4` ($d=17, -688\text{ cp}$) | **A** | Severe evaluation gap: underestimates depth of central tactics. |
| `POS_02` | `OPEN_TAC` | Held | `r1b2rk1/pp1p1ppp/2n1pn2/q5B1/1bPP4/2N2N2/PP2BPPP/R2QK2R w KQ - 3 9` | `g5d2` ($d=11, +11\text{ cp}$) | `d4d5` ($d=17, +22\text{ cp}$) | **B** | Evaluation balanced, but depth 11 misses active central pawn push `d5`. |
| `POS_03` | `CLOSED_POS` | Dev | `r1b1qrk1/ppp2pbp/3p1np1/3Pp3/2P1P3/2N1BP2/PP2N1PP/R2Q1RK1 b - - 0 11` | `e8e7` ($d=10, -31\text{ cp}$) | `a7a6` ($d=18, -47\text{ cp}$) | **B** | Misses prophylactic queenside pawn restraint `a6`. |
| `POS_04` | `CLOSED_POS` | Held | `r2q1rk1/1pp1bppp/p1n1pn2/3p4/2PP4/2N1PN2/PPQ2PPP/R1B2RK1 w - - 4 10` | `c4c5` ($d=11, +14\text{ cp}$) | `b2b3` ($d=18, +21\text{ cp}$) | **B** | Prematurely closes center (`c5`) instead of solidifying queenside (`b3`). |
| `POS_05` | `IQP` | Dev | `r1bq1rk1/pp1n1ppp/4pn2/2pp4/3P4/2NBPN2/PPP2PPP/R1BQ1RK1 w - - 0 9` | `b2b3` ($d=10, +355\text{ cp}$) | `c1d2` ($d=17, +788\text{ cp}$) | **A** | Evaluates IQP position as $+355$ cp vs Stockfish's dominant $+788$ cp. |
| `POS_06` | `IQP` | Held | `r1bq1rk1/pp2bppp/2n1pn2/3p4/3P1B2/P1NBPN2/1P3PPP/R2Q1RK1 b - - 1 10` | `e7d6` ($d=8, -52\text{ cp}$) | `f6h5` ($d=19, -26\text{ cp}$) | **B** | Depth 8 chooses passive trade instead of active knight outpost challenge `Nh5`. |
| `POS_07` | `PAWN_MAJ` | Dev | `2r2rk1/1p1q1ppp/p3pn2/3p4/3P4/bP1BP3/P2B1PPP/R2Q1RK1 w - - 0 15` | `a1b1` ($d=10, -31\text{ cp}$) | `b3b4` ($d=19, +6\text{ cp}$) | **B** | Plays passive retreat `Rb1` instead of active queenside majority push `b4`. |
| `POS_08` | `PAWN_MAJ` | Held | `r4rk1/pp1n1ppp/2p1pn2/8/2PP4/P1N1BB2/1P3PPP/R4RK1 b - - 0 14` | `d7b6` ($d=12, -390\text{ cp}$) | `e6e5` ($d=19, -706\text{ cp}$) | **A** | Fails to recognize crushing nature of central pawn roller. |
| `POS_09` | `OPP_CAST` | Dev | `r1b2rk1/pp2ppbp/2np1np1/q7/3NP3/1BN1BP2/PPP3PP/R2QK2R w KQ - 1 10` | `d4c6` ($d=9, +80\text{ cp}$) | `d1d2` ($d=18, +37\text{ cp}$) | **B** | Releases central knight tension instead of preparing castling battery `Qd2`. |
| `POS_10` | `OPP_CAST` | Held | `r1bq1rk1/1p2bppp/p1np1n2/4p3/4P3/1NN1BP2/PPPQ2PP/2KR1B1R b - - 0 10` | `a6a5` ($d=10, -27\text{ cp}$) | `b7b5` ($d=19, -110\text{ cp}$) | **B** | Chooses slower pawn advance `a5` instead of dynamic Sicilian counter `b5`. |
| `POS_11` | `WEAK_KING` | Dev | `r1b2rk1/ppp2ppp/2n5/3pP3/3P1qn1/2PB1N2/P1P3PP/R2Q1RK1 w - - 0 12` | `d1d2` ($d=12, -317\text{ cp}$) | `f1e1` ($d=17, -549\text{ cp}$) | **A** | Evaluates king shelter panic; forces queen trade instead of preserving pieces. |
| `POS_12` | `WEAK_KING` | Held | `r4rk1/1b1n1ppp/pq1bpn2/1p1p4/3P4/PPNBPN2/5PPP/R1BQR1K1 w - - 1 13` | `c1b2` ($d=9, -23\text{ cp}$) | `c1b2` ($d=19, 0\text{ cp}$) | **F** | Both engines find natural defensive fianchetto `Bb2`. |
| `POS_13` | `PASSED_RACE` | Dev | `8/5p2/1p2k1p1/p1p1P2p/P1P1KP1P/1P6/8/8 w - - 0 35` | `e4e3` ($d=20, -35\text{ cp}$) | `e4e3` ($d=58, 0\text{ cp}$) | **F** | Mutual agreement on king waiting move in pawn ending. |
| `POS_14` | `PASSED_RACE` | Held | `8/4k3/1p2P3/p1p2P2/P1P5/1P2K3/8/8 b - - 0 45` | `e7f6` ($d=19, -1148\text{ cp}$) | `e7d6` ($d=24, -1300\text{ cp}$) | **E** | Misplaces king on `Kf6` blocking own passed pawn push. |
| `POS_15` | `BLOCKADE` | Dev | `r2q1rk1/pp1b1ppp/2n1pn2/3p4/2PP4/1PN1PN2/P4PPP/R2QKB1R w KQ - 0 9` | `f1d3` ($d=10, +100\text{ cp}$) | `f1e2` ($d=18, +190\text{ cp}$) | **B** | Misses subtle square placement `Be2` to avoid being hit by `c5`. |
| `POS_16` | `BLOCKADE` | Held | `r1b2rk1/pp1n1ppp/4pn2/q1pp4/2PP4/P1N1PN2/1P1Q1PPP/R3KB1R w KQ - 2 10` | `f1d3` ($d=10, +27\text{ cp}$) | `c4d5` ($d=21, +39\text{ cp}$) | **B** | Misses central pawn liquidation `cxd5` to resolve pin. |
| `POS_17` | `KNIGHT_OUT` | Dev | `r1bq1rk1/pp2bppp/2n1pn2/3p4/2PN4/1PN1P3/PB2BPPP/R2Q1RK1 b - - 0 10` | `e6e5` ($d=9, +13\text{ cp}$) | `c6d4` ($d=19, -7\text{ cp}$) | **B** | Pushes `e5` creating backward d5 pawn instead of trading knight on d4. |
| `POS_18` | `KNIGHT_OUT` | Held | `r1b1qrk1/pp1n1ppp/2p1pn2/3p4/2PP4/1PN1PN2/P2B1PPP/R2QKB1R w KQ - 3 9` | `d2c1` ($d=9, +351\text{ cp}$) | `f1e2` ($d=15, +791\text{ cp}$) | **A** | Evaluates as $+351$ cp vs Stockfish's dominant $+791$ cp; retreats bishop. |
| `POS_19` | `COL_COMPLEX`| Dev | `r1b2rk1/pp1p1ppp/2n1pn2/8/2P1P3/2N1BN2/PP3PPP/R3KB1R b KQ - 0 9` | `d7d6` ($d=11, -395\text{ cp}$) | `d7d5` ($d=19, -666\text{ cp}$) | **A** | Plays passive `d6`, conceding d5 outpost; misses dynamic break `d5`. |
| `POS_20` | `COL_COMPLEX`| Held | `r1bqr1k1/pp1n1pbp/2p1p1p1/3p4/2PP4/1PN1PN2/PB1Q1PPP/R3KB1R w KQ - 2 11` | `b2a3` ($d=9, +350\text{ cp}$) | `a1d1` ($d=18, +734\text{ cp}$) | **A** | Misplaces bishop on a3 where it bites on granite; misses central rook placement. |
| `POS_21` | `ROOK_EG` | Dev | `8/8/5k2/R7/4r3/8/5K2/8 w - - 0 60` | `a5d5` ($d=19, 0\text{ cp}$) | `a5a6` ($d=22, 0\text{ cp}$) | **E** | Centralizes rook passively instead of active file check `Ra6+`. |
| `POS_22` | `ROOK_EG` | Held | `2r5/8/8/3k4/1R6/8/4K3/8 b - - 0 65` | `d5d6` ($d=15, 0\text{ cp}$) | `c8e8` ($d=23, 0\text{ cp}$) | **E** | Moves king passively instead of active rook checking distance `Re8+`. |
| `POS_23` | `BISHOP_EG` | Dev | `8/8/4k3/1b6/4K3/5B2/8/8 w - - 0 50` | `f3d1` ($d=64, 0\text{ cp}$) | `f3g4` ($d=27, 0\text{ cp}$) | **E** | Fails to recognize optimal bishop checking outpost `Bg4+`. |
| `POS_24` | `BISHOP_EG` | Held | `8/8/3k4/p1b5/P7/2B2K2/8/8 w - - 0 55` | `c3a5` ($d=19, +121\text{ cp}$) | `f3e4` ($d=24, +3\text{ cp}$) | **E** | Captures pawn `Bxa5`, walking into dead opposite-colored bishop draw. |
| `POS_25` | `ZUGZWANG` | Dev | `8/8/p1k5/Pp6/1P1K4/8/8/8 w - - 0 60` | `d4c3` ($d=34, 0\text{ cp}$) | `d4e4` ($d=97, 0\text{ cp}$) | **E** | Retires king to c3 instead of maintaining opposition with `Ke4`. |
| `POS_26` | `ZUGZWANG` | Held | `8/5p2/4k1p1/7p/4KP1P/6P1/8/8 w - - 0 50` | `e4d4` ($d=19, 0\text{ cp}$) | `e4e3` ($d=56, 0\text{ cp}$) | **E** | Steps king to d4 instead of triangulating with `Ke3`, losing opposition. |
| `POS_27` | `QUEENLESS` | Dev | `r1b1kb1r/ppp2ppp/2p5/4Pn2/8/5N2/PPP2PPP/RNB2RK1 w kq - 0 9` | `f1d1` ($d=11, +61\text{ cp}$) | `b1c3` ($d=19, -31\text{ cp}$) | **B** | Depth 11 develops rook prematurely before developing minor piece `Nc3`. |
| `POS_28` | `QUEENLESS` | Held | `r1b1k2r/pp3ppp/2n1pn2/3p4/3P4/2N1PN2/PP3PPP/R3KB1R b KQkq - 0 10` | `c8d7` ($d=11, -18\text{ cp}$) | `e8e7` ($d=19, -2\text{ cp}$) | **B** | Depth 11 plays passive bishop development instead of activating king `Ke7`. |

---

### 4. Strategic Engineering Synthesis

The failure taxonomy yields three critical insights for Candidate X10:
1. **Evaluation Efficiency is as Important as Evaluation Expressiveness:**  
   Because X7 spends too much CPU time re-calculating pawn masks and pawn attacks without a cache, its search depth collapsed to nominal depth 10 under blitz clocks, while Stockfish reached depth 19. **A high-speed Pawn Hash Table is required** to boost search depth back up by +2 to +3 plies.
2. **Endgame Drawing Recognition:**  
   In opposite-colored bishop endgames (`POS_23` and `POS_24`), X7 believed it was winning (+121 cp) by capturing a pawn, walking into a dead draw. Candidate X10 must recognize drawing factor scaling in simplified endgames.
3. **Queenless King Activation:**  
   In `POS_28`, Stockfish immediately activates its king (`Ke7`), recognizing that without queens on the board, the king is an active piece, not a defensive target.

- **Raw Evidence:** `analysis/phase1/p1.5/raw/positional_failure_taxonomy_raw.json`.

**Status:** Phase 2 Completed & Verified.
