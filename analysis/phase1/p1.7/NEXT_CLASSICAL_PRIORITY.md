# PROJECT JANUS — PHASE 1, MILESTONE P1.7
## Milestone P1.8 Roadmap & Classical Engineering Priorities

**Role:** Principal Computer Chess Engineer, Systems Architect, Search & Evaluation Specialist  
**Repository:** `E:\ChessXML\project-janus-phase1`  
**Branch:** `phase1/classical-janus`  
**Status:** Approved Architectural Roadmap  

---

### 1. Architectural Gap Analysis: Janus Classical X vs State-of-the-Art Classical Engines

With the completion of Milestone P1.7, Project Janus has resolved the multithreaded scaling pathology (reversing X11's -107.5 Elo multicore deficit to +8.7 Elo scaling over X7, with 100% thread safety and 33.3M ops/sec concurrent TT throughput). However, an enormous playing-strength gap remains between Janus Classical X and unrestricted Stockfish 19.

To systematically close this gap using strictly classical, non-ML computer chess engineering, we have audited the architectural divergences across four principal subsystems:

```
+----------------------------------------------------------------------------------------------------+
|                                SUBSYSTEM GAP & PRIORITY MATRIX                                     |
|                                                                                                    |
| 1. POSITIONAL EVALUATION     [SEVERELY DEFICIENT]  ──> Needs tapered eval, pawn structure, king    |
|                                                        safety zones, piece mobility bitboards.     |
| 2. ENDGAME KNOWLEDGE         [MISSING]             ──> Zero tablebase support; 3-4-5 piece Syzygy  |
|                                                        WDL/DTZ integration needed.                 |
| 3. SEARCH MOVE ORDERING      [MODERATELY ADVANCED] ──> Has conthist + countermove, lacks capture  |
|                                                        history, threat ordering & quiet histories. |
| 4. PARAMETER TUNING          [MANUALLY CALIBRATED] ──> Non-ML SPSA optimization of ~100 classical  |
|                                                        coefficients required.                      |
+----------------------------------------------------------------------------------------------------+
```

---

### 2. Ranked Initiatives for Milestone P1.8 and Beyond

#### Priority 1: Handcrafted Positional Evaluation & King Safety (Primary Focus for P1.8)
* **Status:** Current evaluation (E10) uses simplified piece-square tables, a primitive 64K-entry pawn hash, and basic material sums. It lacks pawn structure nuances and dynamic king safety.
* **Concrete Deliverables:**
  1. **Tapered Game-Phase Evaluation:** Implement continuous game-phase interpolation ($0 \le \text{phase} \le 24$) blending Midgame (MG) and Endgame (EG) scores smoothly rather than discrete material thresholds.
  2. **Detailed Pawn Structure Bitboards:**
     - Passed pawns with rank-based bonuses, candidate passers, and protected passers.
     - Isolated, backward, doubled, and connected pawn penalties and bonuses.
     - King-distance to passed pawns in endgames (Rule of the Square / pawn shelter).
  3. **Piece Mobility & Outposts:**
     - Safe mobility calculations using attack bitboard intersections excluding attacked squares.
     - Knight and Bishop outposts supported by pawns on ranks 4–6.
     - Bishop pair bonus and bad bishop penalties (pawns on same color).
     - Rooks on open and semi-open files, rooks on the 7th rank.
  4. **Attacking King Safety Model:**
     - Dynamic King Zone bitboard (surrounding squares + pawn shield).
     - Attacking piece weight accumulator (knights=2, bishops=2, rooks=3, queens=5).
     - Penalties for missing pawn shelter and open enemy files pointing at the king.
* **Expected Strength Impact:** +80 to +140 Elo against classical opponents; drastically improves defensive resilience against Stockfish 19.

---

#### Priority 2: Syzygy Endgame Tablebases Integration (3-4-5 Piece WDL & DTZ)
* **Status:** Janus currently searches deep into known theoretical endgames (e.g., KBNK, KRKP, KQKQ), often suffering from 50-move rule horizon effects or horizon-induced blunders.
* **Concrete Deliverables:**
  1. Embed Fathom / Syzygy probing core with zero ML runtime.
  2. Implement root DTZ (Distance-to-Zero) probing for instantaneous perfect moves in endgames $\le 5$ pieces.
  3. Implement search WDL (Win-Draw-Loss) probing at interior nodes near the leaves to instantly prune drawn and winning subtrees.
* **Expected Strength Impact:** +30 to +50 Elo; eliminates endgame blunders and saves massive search time in late games.

---

#### Priority 3: Non-ML SPSA Parameter Calibration (When Authorized)
* **Status:** Current search thresholds and evaluation weights are manually calibrated heuristics.
* **Concrete Deliverables:**
  1. Implement automated SPSA (Simultaneous Perturbation Stochastic Approximation) framework running self-play games under short time controls (e.g. 500ms).
  2. Simultaneously tune ~60 evaluation parameters (pawn weights, mobility factors, king safety weights) and ~25 search parameters (LMR base/divisor, futility margins, RFP multipliers, LMP cutoffs).
  3. Guarantee: Strictly non-ML; SPSA tunes handcrafted mathematical coefficients of classical algorithms.
* **Expected Strength Impact:** +40 to +70 Elo.

---

#### Priority 4: Search Move Ordering & Tactical Reductions Modernization
* **Status:** X12 features 1-ply + 2-ply continuation history and countermove heuristics.
* **Concrete Deliverables:**
  1. **Capture History Table:** Order quiet captures and bad captures by capture history score ($[6][64][6]$ piece $\times$ to $\times$ captured piece).
  2. **Threat / Check Extensions:** Safe check extensions (1 ply) in critical variations to prevent tactical blindness.
  3. **Correction History:** Track and correct static evaluation errors based on search results at TT depth cutoffs.
* **Expected Strength Impact:** +20 to +40 Elo.

---

### 3. Proposed Milestone P1.8 Objective

Establish **Janus Classical X13** with:
1. Full Tapered Evaluation (MG/EG) with King Safety & Pawn Bitboards.
2. Embedded Syzygy Tablebase Probing ($\le 5$ pieces).
3. Verified multithreaded scaling across 1T, 2T, 4T, and 8T.
4. Independent qualification against Frozen X7, Frozen X12, and Matched Stockfish 19.

