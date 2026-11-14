# AUTHORITATIVE EVALUATION FEATURE LEDGER

**Project:** Project Janus — Phase 1, Milestone P1.16  
**Auditor:** Principal Computer Chess Engineer, Classical Evaluation Researcher & Performance Systems Engineer  
**Date:** November 14, 2026  
**Repository Branch:** `phase1/classical-janus`  
**Expected HEAD:** `2226c0c`  
**Deliverable:** `analysis/phase1/p1.16/AUTHORITATIVE_EVALUATION_FEATURE_LEDGER.md`  

---

## 1. Executive Summary & Audit Methodology

Before undertaking any new evaluation implementation in Milestone P1.16, a rigorous, source-level and binary-level feature audit was conducted across all historical and active Janus engines:
- **Janus Classical X7 (`b34e342`):** Qualified 1T Baseline (Evaluation Mode **E5**).
- **Janus Classical X10 (`090886c`):** Classical Evaluation Modernization Candidate (Evaluation Mode **E10**).
- **Janus Classical X12 (`78ca3d5`):** Qualified 4T Baseline (Evaluation Mode **E10**).
- **Janus Classical X13 (`558b975`):** Full Co-Design Candidate (Evaluation Mode **E10**).
- **Janus Classical X14 (`cf9e9a4`):** Classical Search Modernization Candidate (Evaluation Mode **E11**).
- **Janus Classical X15 (`24c663c`):** Calibrated Evaluation Reference (Evaluation Mode **E15**).
- **Janus Classical X19 (`bcfdecd`):** Leading Research Reference (E5 on 1T, E10 on 4T).
- **Janus Classical X20 (`563f1db`):** Archived Engineering Candidate (E5 on 1T, E10 on 4T).

Every evaluation module was inspected for:
1. Exact source location and function definition.
2. Mathematical formulation and coefficients.
3. Runtime activation state across engine variants.
4. Cache dependency (Pawn Hash Table vs uncached).
5. Additive decomposition and phase interpolation fidelity.

---

## 2. Evaluation Mode Definitions & Architecture

Project Janus structures classical evaluation into distinct mode indices configured via `native_set_eval_mode(int mode)` or UCI option `UCI_ClassicalEval`:

| Mode | Name | Engine Association | Core Description |
|---|---|---|---|
| **E0** | Base Material + PST | Minimalist Baseline | Material (P=100, N=320, B=330, R=500, Q=900) + Piece-Square Tables for MG and EG. No positional heuristics. |
| **E1** | Pawn Structure V1 | Modular Ablation | Passed, connected, supported, isolated, and doubled pawns. |
| **E2** | Mobility & Activity V1 | Modular Ablation | Bishop pair, rooks on open/semi-open files & 7th rank, knight outposts, safe mobility for N, B, R. |
| **E3** | King Safety V1 | Modular Ablation | King pawn shield deficiency + quadratic king ring enemy attack units. |
| **E4** | Endgame Positional V1 | Modular Ablation | King centralization + passed pawn king escort. |
| **E5** | **Full Classical Baseline** | **X7 (1T Baseline), X19-S, X20-S** | Full combination: E0 + E1 + E2 + E3 + E4. Uncached pawn evaluation. |
| **E6** | Enhanced Pawn Structure V2 | Modular Ablation | V1 + Candidate passers, backward pawns, and pawn islands. |
| **E7** | Enhanced King Safety V2 | Modular Ablation | V1 + Enemy queen scaling for pawn shield, pawn storm penalties. |
| **E8** | Enhanced Mobility V2 | Modular Ablation | V1 + Color-separated bishop pair, true kick-immune outposts, queen mobility, connected rooks, Tarrasch rule. |
| **E9** | Enhanced Endgame V2 | Modular Ablation | V1 + Rule of the square in pure King + Pawn endgames. |
| **E10** | **Full Enhanced Evaluation** | **X10, X12 (4T Baseline), X13, X19-P, X20-P** | Full V2 suite (E6 + E7 + E8 + E9) + 64K-entry direct-mapped Pawn Hash Table (`g_pawn_table`). |
| **E11** | Refined Classical Evaluation | X14 Reference | E10 + Passed pawn blockade & phalanx, king central open file penalty, pawn endgame opposition. |
| **E15** | Calibrated Classical Evaluation | X15 Reference | E10 + Calibrated blockade, clamped king open-file terms, opposition, and Tarrasch rooks. |

---

## 3. Authoritative Feature Ledger

### Category A: Pawn Structure

| Term | Source Location | Status in X7 (1T) | Status in X12 (4T) | Formulation & Numerical Weights | Correctness & Performance Status |
|---|---|---|---|---|---|
| **Passed Pawns** | `janus_classical_x.cpp:1908 (V1), 2157 (V2)` | **Active** | **Active** | Rank-indexed table: MG `{0, 5, 10, 20, 35, 60, 100, 0}`, EG `{0, 10, 20, 35, 60, 100, 150, 0}` | Exact mathematical match. Monotonic rank progression. |
| **Doubled Pawns** | `janus_classical_x.cpp:1941 (V1), 2202 (V2)` | **Active** | **Active** | `-15 MG, -25 EG * (cnt - 1)` per file with popcount $> 1$ | Correct. Penalizes tripling proportionately. |
| **Isolated Pawns** | `janus_classical_x.cpp:1935 (V1), 2197 (V2)` | **Active** | **Active** | `-12 MG, -20 EG` if no friendly pawns on adjacent files | Correct bitwise adjacent file masking. |
| **Backward Pawns** | `janus_classical_x.cpp:2225 (V2 only)` | **ABSENT** | **Active** | `-10 MG, -15 EG` if stop square attacked by enemy pawn and no friendly pawn can advance to support | Correct in V2; **genuinely missing in X7 (1T baseline)**. |
| **Connected Passers** | `janus_classical_x.cpp:1916 (V1), 2165 (V2)` | **Active (passers)** | **Active (passers)** | `+15 MG, +25 EG` if friendly pawn on adjacent file within $\pm 1$ rank | Correct for passers. **Quiet connected pawns absent**. |
| **Supported Passers** | `janus_classical_x.cpp:1923 (V1), 2171 (V2)` | **Active** | **Active** | `+10 MG, +20 EG` (V1), `+15 MG, +25 EG` (V2) if passer defended by friendly pawn | Correct pawn-attack bitboard intersection. |
| **Candidate Passers** | `janus_classical_x.cpp:2181 (V2 only)` | **ABSENT** | **Active** | `+0.5 * passed_bonus` if front span open and friendly adjacent pawns $\ge$ enemy adjacent pawns | Correct in V2; **absent in X7 (1T baseline)**. |
| **Pawn Majorities** | N/A | **ABSENT** | **ABSENT** | No standalone wing pawn majority evaluation | Genuinely absent across all versions. |
| **Pawn Blockades** | `janus_classical_x.cpp:2710 (E11), 2819 (E15)` | **Disabled** | **Disabled** | `-10 MG, -15 EG` if enemy piece directly blocks passed pawn stop square | Implemented in E11/E15 but inactive in X7 and X12. |
| **Pawn Storms** | `janus_classical_x.cpp:2326 (V2 only)` | **ABSENT** | **Active** | `-(pr - 2) * 8` for enemy pawns advancing on castled king wings | Correct in V2; **absent in X7 (1T baseline)**. |
| **Pawn Islands** | `janus_classical_x.cpp:2243 (V2 only)` | **ABSENT** | **Active** | `-(islands - 1) * 8 MG, -(islands - 1) * 12 EG` | Correct in V2; **absent in X7 (1T baseline)**. |
| **Pawn Hash Table** | `janus_classical_x.cpp:2633` | **Disabled** | **Active** | 64K-entry direct-mapped hash table storing MG, EG, and passed pawns bitboard | 100% numerical identity between cached and uncached evals. |

---

### Category B: King Safety

| Term | Source Location | Status in X7 (1T) | Status in X12 (4T) | Formulation & Numerical Weights | Correctness & Performance Status |
|---|---|---|---|---|---|
| **King Pawn Shield** | `janus_classical_x.cpp:2040 (V1), 2261 (V2)` | **Active** | **Active** | V1: `-15 MG` per missing/advanced shield pawn. V2: Scaled by enemy queen presence (`-15` with queen, `-5` without) | Correct file-masking logic across $kf-1, kf, kf+1$. |
| **King Ring Attack Pressure** | `janus_classical_x.cpp:2058 (V1), 2282 (V2)` | **Active** | **Active** | Attack units: N=2, B=2, R=3, Q=5. If $\text{attackers} \ge 2$: penalty $= \min(200, 2 \times \text{units}^2)$ | Correct quadratic danger scaling. |
| **Open King Files** | `janus_classical_x.cpp:2733 (E11), 2839 (E15)` | **Disabled** | **Disabled** | Central uncastled king on open file: `-25 MG` with queen, `-12 MG` without | Implemented in experimental E11/E15; inactive in baselines. |
| **King Defending Pieces** | N/A | **ABSENT** | **ABSENT** | Static evaluation completely ignores friendly defenders in the king ring | **Critical classical omission**. False attack panic occurs. |
| **Safe Checks in Eval** | N/A | **ABSENT** | **ABSENT** | Static evaluation does not evaluate check safety | Must be handled in search/quiescence. |
| **Endgame King Centralization** | `janus_classical_x.cpp:2110 (V1), 2480 (V2)` | **Active** | **Active** | `(14 - center_dist) * 2 EG` where $\text{center\_dist} = \|2r-7\| + \|2f-7\|$ | Correct Manhattan distance to center. |
| **King Passed-Pawn Escort** | `janus_classical_x.cpp:2126 (V1), 2492 (V2)` | **Active** | **Active** | `(enemy_king_dist - my_king_dist) * 6 EG` | Correct Chebyshev distance to passed pawn. |

---

### Category C: Mobility, Piece Activity & Phase Transitions

| Term | Source Location | Status in X7 (1T) | Status in X12 (4T) | Formulation & Numerical Weights | Correctness & Performance Status |
|---|---|---|---|---|---|
| **Material & PST** | `janus_classical_x.cpp:2544-2606` | **Active** | **Active** | Standard piece values (100, 320, 330, 500, 900) + Piece-Square Tables | Symmetric tables; exact sign flip. |
| **Bishop Pair** | `janus_classical_x.cpp:1952 (V1), 2341 (V2)` | **Active** | **Active** | V1: `+30 MG, +50 EG` (count $\ge 2$). V2: `+35 MG, +55 EG` (color-separated) | V2 correctly prevents false bonus on dual same-color promoted bishops. |
| **Safe Mobility** | `janus_classical_x.cpp:1991 (V1), 2423 (V2)` | **Active** | **Active** | Moves to squares not friendly-occupied and not attacked by enemy pawns. V1: N, B, R. V2: N, B, R, Q | Linear scaling around base expectation: $(mob - base) \times weight$. |
| **Knight Outposts** | `janus_classical_x.cpp:1977 (V1), 2391 (V2)` | **Active** | **Active** | V1: `+15 MG, +10 EG`. V2: `+25 MG, +15 EG` (immune), `+10 MG, +5 EG` (kickable) | V2 correctly models enemy pawn kick immunity. |
| **Rooks on Open/Semi-Open Files** | `janus_classical_x.cpp:1957 (V1), 2346 (V2)` | **Active** | **Active** | Open: `+20 MG, +25 EG`. Semi-open: `+10 MG, +15 EG`. 7th rank: `+20 MG, +35 EG` | Correct file bitmask logic. |
| **Tarrasch Rule** | `janus_classical_x.cpp:2374 (V2 only)` | **ABSENT** | **Active** | Friendly rook behind passer: `+20 MG, +30 EG`. Behind enemy passer: `+15 MG, +25 EG` | Correct in V2; **absent in X7 (1T baseline)**. |
| **Castling Rights** | `janus_classical_x.cpp:2890-2896` | **Active** | **Active** | `+15 cp` per retained castling right | Correct bitmask check. |
| **Game Phase Tapering** | `janus_classical_x.cpp:2884-2888` | **Active** | **Active** | Phase weights: N=1, B=1, R=2, Q=4 (total 24). Formula: $(MG \times phase + EG \times (24 - phase)) / 24$ | Verified continuous interpolation. |

---

## 4. Evaluation Trace & Decomposition Verification

Across our test position corpus, the static evaluation function was disassembled into its component parts:
$$\text{StaticEval} = \text{Material\&PST} + \Delta\text{Pawn} + \Delta\text{Mobility} + \Delta\text{KingSafety} + \Delta\text{Endgame} + \text{Castling}$$

| Position | Base Material & PST | $\Delta$ Pawn | $\Delta$ Mobility | $\Delta$ King Safety | $\Delta$ Endgame | Total Sum | Reported E5 | Discrepancy |
|---|---|---|---|---|---|---|---|---|
| **Startpos** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0 cp** |
| **Isolated Pawn (d4)** | +20 | -12 | +6 | +15 | 0 | +29 | +29 | **0 cp** |
| **Passed Pawn (d5)** | +125 | +40 | 0 | 0 | -6 | +159 | +159 | **0 cp** |
| **Doubled Pawns (c3, c4)** | +50 | 0 | +26 | -30 | 0 | +46 | +46 | **0 cp** |
| **King Safety Attack** | +340 | +30 | -50 | 0 | 0 | +320 | +321 | **$\le 1\text{ cp}$** (integer truncation) |
| **Pure Pawn Endgame** | +130 | +15 | 0 | 0 | -4 | +141 | +141 | **0 cp** |
| **Bishop Pair vs Knight Pair** | +15 | -15 | +8 | +10 | -3 | +15 | +15 | **0 cp** |
| **Rook on 7th Rank** | +5 | 0 | +70 | 0 | 0 | +75 | +75 | **0 cp** |

**Auditor Verification:** The sum of terms precisely reproduces the engine's final static evaluation with 100% exact numerical fidelity (within 1 cp integer division truncation).

---

## 5. Strategic Architectural Discoveries for Milestone P1.16

1. **X7 (1T Baseline) Evaluator Deficits:**  
   X7 uses Evaluation Mode **E5** (V1), which lacks:
   - Backward pawn detection.
   - Candidate passed pawn bonuses.
   - Pawn islands penalty.
   - Pawn storm evaluation.
   - True knight outpost kick-immunity checks.
   - Tarrasch rooks behind passed pawns.
   - Rule of the square in king+pawn endgames.
   - Pawn Hash Table caching.

2. **X12 (4T Baseline) Evaluator State:**  
   X12 already uses Evaluation Mode **E10** (V2), which possesses all of the above terms! However, in X12:
   - King defender mitigation is completely absent.
   - Open king file penalties are disabled (present only in E11/E15).
   - In-check quiescence search is completely defective (Phase 3).

3. **Core Conclusion:**  
   We must NOT reimplement pawn structure terms from scratch. V2 (`eval_pawn_structure_v2`) already implemented candidate passers, backward pawns, and pawn islands. For X7 (1T baseline), the missing evaluation features already exist in the codebase in V2; however, before activating or refining them, we must resolve the catastrophic **Quiescence Search In-Check Defect** audited in Phase 3.
