# Project Janus — Phase 1, Milestone P1.2
## Candidate Selection & Configuration Freeze: Janus Classical X7

**Author:** Principal Computer Chess Engineer, Systems Architect, Experimental Auditor  
**Lineage:** Janus Classical X  
**Frozen Baseline Control:** Classical C1 (`janus_native_engine.exe`, anchor `2b24d13`)  
**Frozen P1.1 Control:** Classical X6 (`janus_classical_x6.exe`, commit `135c019`)  
**New Formal Candidate:** Janus Classical X7  
**Branch:** `phase1/classical-janus`  
**Date:** 2026-11-10  
**Phase 1 Restriction:** Strictly Non-ML (Zero neural evaluation, zero learned weights, zero offline-fitted models)

---

### Candidate Specification

Janus Classical X7 combines the qualified P1.1 search foundation with the qualified P1.2 classical search intelligence and handcrafted positional evaluation:

```
================================================================================
                    JANUS CLASSICAL X7 CANDIDATE ARCHITECTURE
================================================================================
1. SEARCH SUBSYSTEM (Modernized Alpha-Beta / Negamax):
   - Move Generation: Staged Move Generation via MovePicker (Captures -> Killers -> Quiets)
   - Quiescence Search: Prune SEE < 0 (Q2 mode) with capture delta pruning
   - Null-Move Pruning: Adaptive R=3 with zugzwang verification
   - Static Pruning: Reverse Futility Pruning (d <= 3, margin = 80 * d)
   - Root Search: Aspiration Windows (delta = 25 cp, geometric expansion)
   - Move Ordering:
     * Triangular PV Table & Exact Transposition Table Probe (1,000,000 entries)
     * MVV-LVA Static Exchange Evaluation for Captures
     * Killer Moves (2 slots per ply)
     * 2D Butterfly History Heuristic Table
     * 1-ply Continuation History Table (6 x 64 x 6 x 64 int16, 288 KB)
     * 2-ply Continuation History Table (6 x 64 x 6 x 64 int16, 288 KB)
     * Bounded Gravity History Updates: cur + b - (cur * |b|) / 16384
   - Reductions:
     * Dynamic Logarithmic LMR Table: R(d, m) = floor(0.75 + ln(d)*ln(m)/2.25)
     * Dynamic History & Continuation History Modulation (R +/- 1)
     * 10 Invariant Safety Protections with Full-Depth Re-search on Alpha Exceed

2. EVALUATION SUBSYSTEM (Strictly Non-ML Handcrafted Positional Evaluation):
   - Module E0: Material & Mirror-Symmetric Piece-Square Tables (PSQT)
   - Module E1: Pawn Structure (Passed pawns rank-bonus, connected/defended passers, isolated/doubled penalties)
   - Module E2: Mobility & Coordination (Bishop pair, rooks on open files/7th rank, knight outposts, safe mobility)
   - Module E3: King Safety (Pawn shield defect penalty, king ring enemy attacker units with quadratic danger)
   - Module E4: Endgame Positional (King centralization, passed pawn escort)
   - Tapering: Smooth Middle-Game (MG) to End-Game (EG) game phase interpolation (phase 0..24)
   - Castling Rights: +15 cp per available castling right

3. UCI OPTIONS CONFIGURATION:
   - UCI_Variant: "X7" (default)
   - UCI_ContinuationHistory: "H3"
   - UCI_DynamicLMR: "L3"
   - UCI_ClassicalEval: "E5"
================================================================================
```

---

### SHA-256 Checksums of Frozen Candidate

| Artifact | Path | Size (bytes) | SHA-256 Hash |
|---|---|---|---|
| **Source** | `engine/classical_x/janus_classical_x.cpp` | 139,342 | `001e4ec9ffcfc3f87508dfd7d9a1ce98c61bb22f872c05e1975eec4db5f9a656` |
| **Standalone UCI Engine** | `engine/classical_x/janus_classical_x.exe` | 370,176 | `fcaeec69904944fae2eebfffa388fb4bcead3b0f588c7f3b89b4f995a5fbc400` |
| **Shared Library** | `engine/classical_x/janus_classical_x.dll` | 282,112 | `30a6ba2b442b36a18d196f7c5ecbe9da4b896dfa2843bb736ec788481489fc90` |
| **Control X6 Binary** | `analysis/phase1/p1.2/control/janus_classical_x6.exe` | 354,816 | `138b43bc3188696769f755f40898b69842e9e6c529e38a119d9734bad92a741c` |
| **Control C1 Binary** | `analysis/v0.56/native/janus_native_engine.exe` | 344,064 | `3c8d197992cb586e3fdbbfd474586d36e2f12255d6484379ba5df0dbcb6beeb2` |

---

### Selection Rationale

The candidate **Janus Classical X7** satisfies all milestone governance constraints:
1. It achieves an aggregate **36.65% reduction in search work** compared to Classical X6 while simultaneously incorporating four complete handcrafted positional evaluation modules.
2. It preserves 100% bit-exact invariance when configured to run in X6 mode.
3. It passed all legal perft checks (depths 1..4), anti-symmetry checks, and bounded score validations.
4. It is strictly non-ML, containing zero neural components, weights, or external runtime dependencies.

