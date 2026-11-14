# Candidate Selection & Freezing Protocol: Janus Classical X24

## 1. Candidate Identification & Architectural Specification

Candidate **Janus Classical X24** represents the formal culmination of Milestone P1.19. It isolates the classical backward-pawn evaluation term (Track A) from the regressive king-file exposure penalty (Track B) introduced in Milestone P1.18, preserving the proven correctness invariants of Reference X22 (Q1 quiescence search) and the high-efficiency 64K pawn-structure hash table.

### 1.1 Architectural Composition

| Subsystem | Architectural Specification | Implementation Details |
| :--- | :--- | :--- |
| **Search Framework** | Iterative Deepening Alpha-Beta | PVS, Aspiration Windows, Null Move Pruning ($R=3$), Late Move Reductions (LMR), Adaptive Move Ordering (TT move, Good Captures MVV-LVA, Killer Moves, History Heuristic). |
| **Quiescence Search** | Tactical Correctness Reference (Q1) | Full check-evasion generation in quiescence; stand-pat suppressed when in check; negative-SEE captures pruned unless giving check or escaping check; mate-in-1 / stalemate resolution. |
| **Pawn Structure Hash** | 64K-Entry Direct Mapped Table | 16-byte aligned entries: 64-bit Zobrist key, 16-bit packed score (MG/EG), 8-bit passed pawns bitboard, 8-bit semi-open files bitboard. $+13.58\%$ evaluation acceleration. |
| **Track A (Evaluation)** | Backward-Pawn Structural Term | **Active**: $-10\text{ mg} / -15\text{ eg}$ penalty applied strictly to pawns on half-open/closed files unable to advance safely or receive friendly pawn support. |
| **Track B (King Safety)** | King-File Exposure Term | **Permanently Disabled ($0\text{ mg} / 0\text{ eg}$)**: Complete elimination of open-file king penalties that previously induced catastrophic premature shield pawn advances. |
| **SMP Concurrency** | Shared-Memory Parallelism (4T) | Lockless transposition table with XOR verification, worker thread pool dispatch, split-point workload distribution. Tested safely up to 2.91M NPS. |
| **Charter Invariance** | Strictly Non-ML | Zero neural networks, NNUE, offline parameter fitting, SPSA, or Texel tuning. |

---

## 2. Cryptographic Manifest & Frozen Artifacts

All binaries have been compiled with Microsoft (R) C/C++ Optimizing Compiler Version 19.43.34809 for x64 with compiler flags `/O2 /Oi /Ot /std:c++17 /EHsc` and frozen under cryptographic SHA-256 verification.

### 2.1 Candidate X24 Artifacts

| Artifact | File Path | SHA-256 Checksum |
| :--- | :--- | :--- |
| **Candidate Binary (EXE)** | `analysis/phase1/p1.19/control/janus_classical_x24.exe` | `D8BE5521B91A353C7C4D2E8BAD51AF008147B3FD11989C2055780CE4ED91981F` |
| **Native Library (DLL)** | `analysis/phase1/p1.19/control/janus_classical_x24.dll` | `B6EC9E806E20DC22664043557677796E11FCAFF800B42B4E4DBDC75C5BA899B1` |
| **Source Archive (CPP)** | `analysis/phase1/p1.19/control/janus_classical_x24.cpp` | `3A1A5C854C836AAEE9A5EC586983D0A46A2A28C588A986FC412915079023F9D8` |

### 2.2 Frozen Control Baselines & External References

| Engine Identity | Role in Milestone P1.19 | File Path | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| **Janus Classical X7** | Qualified 1T Strength Baseline | `analysis/phase1/p1.3/control/janus_classical_x7.exe` | `86392A2F4BD4182A4D7DC21E32940BD7939F6816794D5E1AB02F4082431CA28B` |
| **Janus Classical X12** | Qualified 4T Strength Baseline | `analysis/phase1/p1.7/control/janus_classical_x12.exe` | `00B4F5FEDEA02A392A1AF9713A96512E5199A0E3AE55C295AD1C7CFFF1B47059` |
| **Janus Classical X22** | Correctness Reference Engine | `analysis/phase1/p1.17/control/janus_classical_x22.exe` | `35D095CFFE8A2EDA412171803C09BE52A74DFB3F9744C04F573D2A7FFB1C2F1C` |
| **Janus Classical X23** | Rejected Milestone P1.18 Candidate | `analysis/phase1/p1.18/control/janus_classical_x23.exe` | `39E875841B36AC82F464ABC7F31DB19D7CF5ABCD0F15B0A923B086A5BB393E39` |
| **Stockfish 4** | Historical External Benchmark (2014) | `E:\ChessXML\tools\stockfish_4\stockfish_4.exe` | `1128CAB83386063359947F04155A2210C966080E71176DD385D8BDC3B6C32674` |
| **Stockfish 11** | Mature Classical Benchmark (2020) | `E:\ChessXML\tools\stockfish_11\stockfish_11.exe` | `B004C03BD71BB84E8BC1832C580E72A7E883F121E1834EA6DA2802D1575E8048` |
| **Stockfish 19** | Ultimate SOTA Benchmark (NNUE) | `E:\ChessXML\tools\stockfish\stockfish.exe` | `45BC8E4969147DB9C2EB533810637994619BFF0EACC81CCFD9854394901BCBD0` |

---

## 3. Candidate Promotion Gates & Criteria

The formal qualification of Candidate X24 will be adjudicated according to the following strict criteria across Matches 1–7:

1. **Category A (Full Baseline Replacement):**
   - Must achieve a statistically significant win rate over Qualified 1T Baseline X7 (Match 2: paired 95% CI lower bound $> 50.0\%$ and $p < 0.05$).
   - Must achieve a statistically significant win rate over Qualified 4T Baseline X12 (Match 3: paired 95% CI lower bound $> 50.0\%$ and $p < 0.05$).
   - Must demonstrate non-regressive performance at slow time control (Match 4: $\ge 50.0\%$).
2. **Category B (Research Reference Candidate):**
   - Must demonstrate a statistically significant win rate or verified tactical superiority over Reference X22 (Match 1: $p < 0.05$ or score $> 50.0\%$).
   - Retained as the foundational architecture for future classical evaluation research, even if it does not surpass Baselines X7 and X12.
3. **Category C (Rejected Candidate):**
   - If Candidate X24 scores $< 50.0\%$ against Reference X22 and demonstrates persistent positional drag. In this event, Reference X22 remains the active research reference.
