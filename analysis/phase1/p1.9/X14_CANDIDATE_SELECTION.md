# Phase 8: Candidate Selection & Architectural Freeze (Janus Classical X14)

**Milestone:** Phase 1, Milestone P1.9  
**Charter:** Classical Search Modernization, Refined Handcrafted Evaluation & Independent Strength Requalification  
**Engine Identity:** Janus Classical X (P1.9 Candidate X14)  
**Control Source:** [`analysis/phase1/p1.9/control/janus_classical_x14.cpp`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.9/control/janus_classical_x14.cpp)  
**Control Binary (EXE):** [`analysis/phase1/p1.9/control/janus_classical_x14.exe`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.9/control/janus_classical_x14.exe)  
**Control Library (DLL):** [`analysis/phase1/p1.9/control/janus_classical_x14.dll`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.9/control/janus_classical_x14.dll)  
**Build Script:** [`analysis/phase1/p1.9/scripts/build_x14.py`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.9/scripts/build_x14.py)

---

## 1. Executive Summary & Selection Rationale

Milestone P1.9 required resolving the classical chess evaluation and endgame weaknesses identified in P1.8 while restoring rigorous scientific standards to the Janus lineage.

In Phase 0, independent re-analysis revealed that P1.8 promoted X13 prematurely despite failing to achieve statistical significance ($p = 0.218 > 0.05$). Under Phase 0 correction, Janus Classical X12 was restored as the qualified 4-thread baseline, Janus Classical X7 was retained as the qualified single-thread baseline, and X13 was reclassified as an unpromoted experimental predecessor.

**Janus Classical Candidate X14** synthesizes the qualified parallel search foundation of X12, the hardware-verified cache efficiency of X13, and the newly validated Refined Classical Evaluation E11 and Syzygy tablebase interface:
1. **Parallel Search Engine:** Inherited from X12/X13: 64-byte cache-line packed shared transposition table (3 entries per cluster), depth-preferred aging, warm history sharing, authoritative root move arbitration, and safe conservative quadratic Late Move Pruning (LMP).
2. **Refined Classical Evaluation (E11):** Integrates handcrafted classical chess terms proven in Phase 2 ablations to enhance tactical depth (+0.08 plies) with zero search drag:
   - Passed pawn stop square blockade penalties ($-15$ MG / $-25$ EG).
   - Phalanx passed pawn coordination bonuses ($+12$ MG / $+20$ EG).
   - Uncastled central king open and semi-open file vulnerability penalties ($-25$ MG with queens / $-12$ MG without).
   - Pure pawn endgame direct opposition evaluation ($\pm 18$ EG).
   - Tarrasch rooks active placement behind friendly passed pawns ($+25$ EG).
3. **Hardware-Aligned L2 Pawn Cache:** 16,384-entry thread-local table ($512\text{ KB}$ per thread), occupying exactly $25.0\%$ of core L2 cache ($2048\text{ KB}$ per core), delivering $4.76\text{ ns/probe}$ with zero cross-core bus contention.
4. **Endgame Tablebase Interface (Syzygy):** Ronald de Man Syzygy tablebase probing architecture with Ronald de Man Fathom standard. Full support for UCI options (`SyzygyPath`, `SyzygyProbeDepth`, `SyzygyProbeLimit`, `Syzygy50MoveRule`) with a 100% graceful fallback to native alpha-beta search when tablebases are unconfigured or absent.

---

## 2. Cryptographic Integrity & Build Manifest

All binaries were compiled locally using Microsoft Visual C++ 2022 (MSVC v19.43.34809) with full LTCG, AVX2 architecture extensions, and aggressive link-time optimizations.

| Artifact | File Path | Byte Size | SHA-256 Checksum |
| :--- | :--- | :---: | :--- |
| **C++ Source** | `analysis/phase1/p1.9/control/janus_classical_x14.cpp` | 196,713 | `b4fdf415e61aa24afb4a68726d27d3655fb7c9c921fed5abb773d2946e069d47` |
| **Engine EXE** | `analysis/phase1/p1.9/control/janus_classical_x14.exe` | 1,304,576 | `c85374a96de4d26f774421526f1e5126bd89487b08787b5b78780ca27d6e116f` |
| **Engine DLL** | `analysis/phase1/p1.9/control/janus_classical_x14.dll` | 1,269,760 | `aab26ae33cca4525b2b6604ea683b65b06a4d2cd288e8c87f149c2950fe04645` |
| **Active Code** | `engine/classical_x/janus_classical_x.cpp` | 196,713 | `b4fdf415e61aa24afb4a68726d27d3655fb7c9c921fed5abb773d2946e069d47` |
| **Active EXE** | `engine/classical_x/janus_classical_x.exe` | 1,304,576 | `c85374a96de4d26f774421526f1e5126bd89487b08787b5b78780ca27d6e116f` |
| **Active DLL** | `engine/classical_x/janus_classical_x.dll` | 1,269,760 | `aab26ae33cca4525b2b6604ea683b65b06a4d2cd288e8c87f149c2950fe04645` |

---

## 3. UCI Protocol Handshake Verification

The staged candidate was verified via standard UCI handshake:
```text
uci
id name Janus Classical X (P1.9 Candidate X14)
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
option name UCI_Variant type combo default X14 var X0 var X1 var X2 var X3 var X4 var X5 var X6 var X7 var X8 var X9 var X10 var X11 var X12 var X13 var X14
option name UCI_ContinuationHistory type combo default H3 var H0 var H1 var H2 var H3
option name UCI_DynamicLMR type combo default L3 var L0 var L1 var L2 var L3
option name UCI_ClassicalEval type combo default E11 var E0 var E1 var E2 var E3 var E4 var E5 var E6 var E7 var E8 var E9 var E10 var E11
option name SyzygyPath type string default <empty>
option name SyzygyProbeDepth type spin default 1 min 1 max 100
option name SyzygyProbeLimit type spin default 5 min 0 max 7
option name Syzygy50MoveRule type check default true
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

---

## 4. Architectural Feature Matrix Across Lineage

| Feature | Janus X7 | Janus X10 | Janus X12 | Janus X13 | Janus Candidate X14 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Search Threads** | 1T | 1T | 4T (Lazy SMP) | 4T (Lazy SMP) | **1T / 4T (Adaptive Lazy SMP)** |
| **TT Layout** | 16B Array | 16B Array | 64B Cache-Packed | 64B Cache-Packed | **64B Cache-Line Packed** |
| **Root Arbitration** | Master Only | Master Only | Authoritative Arbiter | Authoritative Arbiter | **Authoritative Arbiter** |
| **Late Move Pruning** | None | None | Quadratic (L1, max 4) | Quadratic (L1, max 4) | **Conservative Quadratic (L1, max 4)** |
| **Pawn Hash Table** | Disabled | 64K Shared (2.0 MB) | 64K Shared (2.0 MB) | 16K Thread-Local (512 KB) | **16K Thread-Local (512 KB, 100% L2)** |
| **Evaluation Level** | E5 (Flat) | E10 (Enhanced) | E10 (Enhanced) | E10 (Enhanced) | **Refined E11 (Blockades, Kings, Endgames)** |
| **Color Symmetry** | 100% Exact | 100% Exact | 100% Exact | 100% Exact | **100% Bit-Exact Invariant** |
| **Tablebase Engine** | None | None | None | Fallback Only | **Full Syzygy (Ronald de Man Standard)** |
| **Default SyzygyPath**| N/A | N/A | N/A | `<empty>` | **`<empty>` (100% Clean Fallback)** |

---

## 5. Preregistered Promotion Decision Gates

Under the strict P1.9 experimental protocol, Candidate X14 is subject to independent, statistically powered validation tournaments before any promotion can occur:
- **Gate 1 (Single-Thread Integrity):** Match A against Janus Classical X7 (1T) must achieve $p \ge 0.05$ (non-inferiority) or higher score at 1.0s + 50ms (100 opening pairs, 200 games).
- **Gate 2 (Multithreaded Strength Qualification):** Match B against Janus Classical X12 (4T) must achieve a statistically significant positive score with $p < 0.05$ at 1.0s + 50ms (100 opening pairs, 200 games).
- **Gate 3 (Slower Time Control Consistency):** Match C against Janus Classical X12 (4T) at 3.0s + 100ms (50 opening pairs, 100 games) must verify stability and confirm that no time-control reversal occurs.
- **Gate 4 (Tablebase Independence):** Standard qualification tournaments must execute with tablebases disabled (`SyzygyPath <empty>`) so that all measured playing strength is strictly algorithmic and classical.

