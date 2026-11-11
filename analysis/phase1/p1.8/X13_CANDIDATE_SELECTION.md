# PROJECT JANUS — PHASE 1, MILESTONE P1.8
## Candidate Selection & Freeze: Janus Classical X13

### 1. Executive Summary & Selection Charter

Milestone P1.8 addresses the core barrier identified in classical chess engine performance: empirical evidence demonstrates that **83.3% of all chess failures** stem from static positional evaluation blindness (58.3%) and endgame horizon errors (25.0%), whereas selective search mechanisms and parallel concurrency are fundamentally sound.

Following the controlled $2 \times 3$ factorial ablation in Phase 6, **Janus Classical X13** is selected as the production candidate. X13 establishes the first complete co-design between:
1. The hardened 64-byte cache-line packed parallel search core qualified in P1.7 (X12).
2. The expressive handcrafted positional evaluation engine (E10) audited in P1.5 and Phase 2-3.
3. A zero-contention, thread-local pawn hash architecture residing entirely within private L2 CPU cache.

Janus Classical X13 adheres strictly to the non-ML charter: zero neural networks, zero NNUE, zero learned weights, and zero automated parameter tuning (SPSA).

---

### 2. Architectural Blueprint of Candidate X13

```
+-----------------------------------------------------------------------------------+
|                           JANUS CLASSICAL X13 (P1.8)                              |
+-----------------------------------------------------------------------------------+
|  1. SEARCH ENGINE CORE (Derived from Qualified Multithreaded Baseline X12)        |
|     - Cache-line packed 64-byte Transposition Table (3 entries / cluster + lock)  |
|     - Smart depth-preferred replacement with age clustering                       |
|     - Authoritative root arbitration across all worker threads                   |
|     - Warm history & continuation history table inheritance across iterations     |
|     - Safe quadratic Late Move Pruning (LMP mode 1, max depth 4)                  |
|     - Calibrated Late Move Reductions (L3) & Countermove Heuristic (M2)           |
+-----------------------------------------------------------------------------------+
|  2. CLASSICAL EVALUATION ENGINE (E10 Handcrafted Positional Evaluation)          |
|     - Passed Pawns: Rank advancement, connected/supported bonuses, candidates    |
|     - Pawn Structure: Penalties for isolated, doubled, backward pawns & islands   |
|     - King Safety: Attacking piece weight units scaled quadratically by queen     |
|     - Mobility & Coordination: Safe non-pawn mobility bitboards & bishop pair     |
|     - Positional Outposts: Knight outposts defended by pawns & immune to attacks  |
|     - Endgame Reliability: King escort to passed pawns, rook on 7th rank / open  |
+-----------------------------------------------------------------------------------+
|  3. CACHE & CONCURRENCY OPTIMIZATION (Thread-Local L2 Architecture)               |
|     - Pawn Hash: thread_local PawnHashEntry t_pawn_table[16384]                   |
|     - Footprint: Exactly 512 KB per thread (100% L2 cache resident, 1024 KB L2)   |
|     - Concurrency Safety: 0 shared locks, 0 bus invalidations, 0 torn reads       |
|     - Scaling: 3.20x effective parallel throughput scaling at 4 threads (6.0M NPS)|
+-----------------------------------------------------------------------------------+
```

---

### 3. Cryptographic Verification & Artifact Manifest

All artifacts for Janus Classical X13 have been compiled under MSVC 2022 (`/O2 /Oi /Ot /GL /Gy /std:c++17 /EHsc /MD /arch:AVX2 /DNDEBUG /link /LTCG /OPT:REF /OPT:ICF`) and frozen in the control staging directory:

| Artifact Path | File Size (Bytes) | SHA-256 Cryptographic Hash |
| :--- | :---: | :--- |
| `analysis/phase1/p1.8/control/janus_classical_x13.exe` | 1,303,040 | `a980cc08cd7cc99ae54a75c21f38dc9d65e568107a7fb79a31dd49fbe2533a29` |
| `analysis/phase1/p1.8/control/janus_classical_x13.dll` | 1,268,224 | `e41e83774ba0bd99da143b0d3b75a3c579fd3cd29abd94f65cad29484e22d86a` |
| `analysis/phase1/p1.8/control/janus_classical_x13.cpp` | 188,907 | `598c313639e3b62d3a7f54376770ed6e4b826862ff520e06469610b6ab3598e4` |
| `engine/classical_x/janus_classical_x.exe` | 1,303,040 | `a980cc08cd7cc99ae54a75c21f38dc9d65e568107a7fb79a31dd49fbe2533a29` |
| `engine/classical_x/janus_classical_x.dll` | 1,268,224 | `e41e83774ba0bd99da143b0d3b75a3c579fd3cd29abd94f65cad29484e22d86a` |

---

### 4. UCI Identification & Compliance

Verification of UCI handshake protocol:
```
id name Janus Classical X (P1.8 Candidate X13)
id author Project Janus Developers
option name Threads type spin default 1 min 1 max 16
option name UCI_LMP type combo default L1 var L0 var L1 var L2 var L3
option name UseKillerOrdering type check default true
option name UseHistoryOrdering type check default true
option name UsePVS type check default false
option name UseLMR type check default true
option name LMRMinDepth type spin default 3 min 2 max 8
option name LMRMoveThreshold type spin default 4 min 2 max 16
option name LMRBaseReduction type spin default 1 min 1 max 3
option name UseSEEOrdering type check default false
option name UseSEEInQuiescence type check default false
option name UCI_Variant type combo default X13 var X0 var X1 var X2 var X3 var X4 var X5 var X6 var X7 var X8 var X9 var X10 var X11 var X12 var X13
option name UCI_ContinuationHistory type combo default H3 var H0 var H1 var H2 var H3
option name UCI_DynamicLMR type combo default L3 var L0 var L1 var L2 var L3
option name UCI_ClassicalEval type combo default E10 var E0 var E1 var E2 var E3 var E4 var E5 var E6 var E7 var E8 var E9 var E10
option name UCI_TacticalOrdering type combo default M4 var M0 var M1 var M2 var M3 var M4
option name UCI_SingularExtensions type combo default S3 var S0 var S1 var S2 var S3
option name UCI_MultiCut type combo default C1 var C0 var C1
option name UCI_ProbCut type combo default P3 var P0 var P1 var P2 var P3
option name UCI_StagedMovegen type check default true
option name UCI_QuiescenceSEE type spin default 2 min 0 max 3
option name UCI_NullMovePruning type check default true
option name UCI_RFP type check default true
option name UCI_AspirationWindow type check default true
option name UCI_DynamicTime type check default true
option name UCI_PawnHash type check default true
uciok
```

Candidate X13 is now frozen and staged for Phase 8 correctness qualification.

