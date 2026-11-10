# Project Janus — Phase 1, Milestone P1.5
## Janus Classical X10 Candidate Selection & Binary Freeze Document

**Author:** Principal Computer Chess Engineer, C++17 Performance Architect, Classical Chess Evaluation Researcher, Search-Time Optimization Specialist, and Statistical Experimental Auditor  
**Lineage:** Janus Classical X  
**Incumbent Baseline:** Janus Classical X7 (`b34e342`)  
**Proposed Candidate:** Janus Classical X10  
**Date:** November 2026  
**Governing Rule 1:** Strictly Non-ML (Zero neural networks, zero NNUE, zero learned weights, zero offline-fitted models)

---

### 1. Executive Summary

Milestone P1.5 selects **Janus Classical X10** as the formal experimental candidate for strength qualification.

Candidate X10 integrates:
1. **Classical Evaluation Expressiveness (Module E10):**
   - Candidate passed pawns with $50\%$ rank scaling.
   - Backward pawn detection on semi-open files with $-10$ MG / $-15$ EG penalty.
   - Pawn island structural penalties.
   - Queen presence scaling in king safety, completely eliminating phantom danger in queenless positions.
   - Enemy pawn storm detection on king flank files.
   - True knight outposts (immune to enemy pawn kicks) with $+25$ MG / $+15$ EG.
   - Color-separated bishop pair bonuses ($+35$ MG / $+55$ EG).
   - Safe queen mobility and Tarrasch rooks behind passed pawns.
   - Rule of the square and fortress draw scaling in simplified endgames.
2. **Evaluation Efficiency Architecture:**
   - 64K-entry Pawn Hash Table ($2.0\text{ MB}$, L3 cache resident) achieving $> 90\%$ hit rate and preserving $97.4\%$ of baseline throughput ($1,463,554$ NPS).
3. **Dynamic Time Management (T1..T3):**
   - UCI `movestogo` adaptive budgeting.
   - Root move instability scaling ($+30\%$) and score drop protection ($+40\%$).
   - Periodic 2048-node hard deadline check preventing time forfeits.

---

### 2. Candidate Binary Provenance & Cryptographic Ledger

| Artifact | Relative Path | Size (Bytes) | SHA-256 Checksum |
|---|---|---|---|
| **UCI Executable** | `analysis/phase1/p1.5/control/janus_classical_x10.exe` | 382,464 | `1ef060f89cb156b798cd2fbe67539d088c6c0fb3842006b734f07a03808b0f20` |
| **Shared Library DLL** | `analysis/phase1/p1.5/control/janus_classical_x10.dll` | 290,304 | `ce0df6a68fa234ac137e2202d3d77a0cae1e9861237d6dae3c05d2509e90d2f6` |
| **Complete Source** | `analysis/phase1/p1.5/control/janus_classical_x10.cpp` | 175,586 | `8dc4d92438fa3f8aef8dbc2de7e219d47bbfbfe76a56c9aa48e82ad0dba9565d` |

#### Compiler Environment & Configuration:
- **Compiler:** Microsoft Visual C++ 2022 (MSVC v19.43.34809 for x64).
- **Optimization Flags:** `/O2 /Ot /Oi /std:c++17 /EHsc /DNDEBUG /arch:AVX2 /fp:fast`.
- **Linker Flags:** `/INCREMENTAL:NO /OPT:REF /OPT:ICF`.

---

### 3. Preregistered Qualification Conditions

To achieve production baseline promotion, Candidate X10 must satisfy:
1. **Zero Critical Regressions:** Pass 100% of invariant correctness tests (Verified in Phase 7).
2. **Statistical Significance Gate:** Achieve a statistically significant victory against Baseline X7 in a paired opening tournament:
   $$\text{Score} > 50.0\%, \quad p < 0.05 \text{ (two-tailed paired } t\text{-test)}.$$
   If $p \ge 0.05$ or score $\le 50.0\%$, Baseline X7 is retained.

**Status:** Candidate Frozen & Ready for Tournament Play.

