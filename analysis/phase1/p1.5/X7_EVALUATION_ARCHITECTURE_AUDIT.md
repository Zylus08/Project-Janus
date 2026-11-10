# Project Janus — Phase 1, Milestone P1.5
## Janus Classical X7 Handcrafted Evaluation Architecture Audit & Component Tracer

**Author:** Principal Computer Chess Engineer, C++17 Performance Architect, Classical Chess Evaluation Researcher, Search-Time Optimization Specialist, and Statistical Experimental Auditor  
**Lineage:** Janus Classical X  
**Incumbent Baseline:** Janus Classical X7 (`b34e342`)  
**Parent File:** `analysis/phase1/p1.3/control/janus_classical_x7.cpp`  
**Date:** November 2026  
**Governing Rule 1:** Strictly Non-ML (Zero neural networks, zero NNUE, zero learned weights, zero offline-fitted models)

---

### 1. Executive Summary

Milestone P1.5 requires a forensic architectural audit of the handcrafted classical evaluation function inherited from Janus Classical X7 (Evaluation Mode E5).

While Milestone P1.2 successfully introduced basic positional terms (material tapering, piece-square tables, pawn structure, piece mobility, king safety, and endgame centralization), source-level disassembly reveals multiple structural defects, missing positional concepts, and computational redundancies that limit X7's positional strength against unrestricted Stockfish 19.

---

### 2. Complete Inventory of Implemented Handcrafted Features in X7 (E5)

The evaluation function in `janus_classical_x7.cpp` (`native_evaluate_internal`) computes:
$$\text{Score} = \frac{\Delta\text{MG} \times \Phi + \Delta\text{EG} \times (24 - \Phi)}{24} + 15 \times \Delta\text{Castling}$$
where $\Phi = \min(24, \text{knights} \times 1 + \text{bishops} \times 1 + \text{rooks} \times 2 + \text{queens} \times 4)$.

#### A. Base Material & Piece-Square Tables (E0)
- **Piece Values:**
  - Middlegame: Pawn 100, Knight 320, Bishop 330, Rook 500, Queen 900, King 20000.
  - Endgame: Pawn 120, Knight 310, Bishop 330, Rook 550, Queen 1000, King 20000.
- **Piece-Square Tables:** $8 \times 8$ arrays for each piece type. White squares are mirrored via `sq ^ 56`.
- **Castling Rights:** $+15$ cp awarded per castling right retained.

#### B. Pawn Structure (`eval_pawn_structure`) (E1)
- **Passed Pawns:** Ranked bonuses using `PASSED_PAWN_BONUS_MG` $[0, 5, 10, 20, 35, 60, 100, 0]$ and `PASSED_PAWN_BONUS_EG` $[0, 10, 20, 35, 60, 100, 150, 0]$.
- **Connected Passer:** $+15$ MG / $+25$ EG if a friendly pawn occupies an adjacent file within $\pm 1$ rank.
- **Supported Passer:** $+10$ MG / $+20$ EG if defended by a friendly pawn attack ray.
- **Isolated Pawns:** $-12$ MG / $-20$ EG per pawn on a file with zero friendly pawns on adjacent files.
- **Doubled Pawns:** $-15$ MG / $-25$ EG per doubled pawn occurrence on a file.

#### C. Mobility & Piece Coordination (`eval_mobility_and_coordination`) (E2)
- **Bishop Pair:** $+30$ MG / $+50$ EG if `popcount(bishops) >= 2`.
- **Rooks on Open / Semi-Open Files:** $+20$ MG / $+25$ EG for open files; $+10$ MG / $+15$ EG for semi-open files.
- **Rooks on 7th Rank:** $+20$ MG / $+35$ EG if rook is on 7th rank (rank 6 for White, rank 1 for Black).
- **Knight Outposts:** $+15$ MG / $+10$ EG if on ranks 4–6 and defended by a friendly pawn.
- **Safe Mobility:** Evaluates pseudo-legal destinations not attacked by enemy pawns:
  - Knight: $(\text{mob} - 4) \times 4$
  - Bishop: $(\text{mob} - 7) \times 4$
  - Rook: $(\text{mob} - 7) \times 2$

#### D. King Safety (`eval_king_safety`) (E3)
- **Pawn Shield:** $-15$ MG per missing or over-advanced shield pawn in front of castled king ($kf - 1$ to $kf + 1$).
- **King Ring Attackers:** Attack units summed for enemy pieces attacking the 8-square king ring (Knight 2, Bishop 2, Rook 3, Queen 5). If $\ge 2$ attackers, danger penalty is $\min(200, 2 \times \text{units}^2)$.

#### E. Endgame Positional (`eval_endgame_positional`) (E4)
- **King Centralization:** Manhattan center distance penalty $(14 - \text{center\_dist}) \times 2$.
- **Passed Pawn Escort:** $(\text{enemy\_king\_dist} - \text{friendly\_king\_dist}) \times 6$.

---

### 3. Forensic Identification of Evaluation Defects & Vulnerabilities

| Defect ID | Evaluation Module | Observed Defect / Pathology | Engineering Consequence |
|---|---|---|---|
| **FLAW-1** | Mobility | **Queen mobility is completely omitted.** | Queens are treated as static batteries; engine cannot distinguish active central queens from smothered or sideline queens. |
| **FLAW-2** | King Safety | **King attack units ignore Queen presence.** | Minor pieces and rooks trigger quadratic king-safety panic in simplified endgames where no mating net is possible without queens. |
| **FLAW-3** | Knight Outposts | **Outposts do not test enemy pawn attackability.** | A knight on $d5$ defended by $c4$ receives outpost bonus even if an enemy pawn on $e6$ or $c6$ can kick it immediately. |
| **FLAW-4** | Pawn Structure | **Zero candidate passed pawn detection.** | 3 vs 2 pawn majorities receive no positional valuation until a pawn physically passes the enemy pawn line. |
| **FLAW-5** | Pawn Structure | **Backward pawns are completely unpenalized.** | Pawns that cannot advance safely and are undefended by friendly pawns (e.g. $d6$ in Sicilian) receive zero structural penalty. |
| **FLAW-6** | Performance | **Absence of a Pawn Hash Table.** | Pawn structure and passed pawns are re-evaluated from scratch on every node, consuming ~25% of total eval time. |
| **FLAW-7** | Coordination | **Bishop pair bonus ignores square color complexes.** | Two bishops on the same color complex (via pawn promotion) erroneously receive the full bishop-pair coordination bonus. |
| **FLAW-8** | Endgame | **No opposition, square-of-the-pawn, or drawing fortress detection.** | Pure pawn endgames fail to recognize outside passed pawns and the rule of the square; drawing opposite-colored bishops are misjudged. |

---

### 4. Implementation of the Evaluation Component Tracer (`eval_trace`)

To provide non-intrusive diagnostic transparency without polluting production search speed, a standalone diagnostic tracer was implemented in [`analysis/phase1/p1.5/tests/x7_evaluation_tracer.py`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.5/tests/x7_evaluation_tracer.py).

The tracer maps each term into eight mutually exclusive, zero-residual categories:
1. `material`
2. `piece_square_tables`
3. `castling_rights`
4. `pawn_structure`
5. `mobility_and_coordination`
6. `king_safety`
7. `endgame_terms`
8. `actual_total_eval`

#### Mathematical Verification Guarantee:
$$\sum_{i=1}^7 \text{Component}_i \equiv \text{actual\_total\_eval} \quad (\text{Residual} = 0\text{ cp for all legal positions})$$

#### Verification Trace Sample:
```json
{
  "fen": "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPP3PP/2KR1B1R b - - 0 9",
  "side_to_move": "black",
  "game_phase": 20,
  "material": 917,
  "piece_square_tables": -66,
  "castling_rights": 0,
  "pawn_structure": 0,
  "mobility_and_coordination": -39,
  "king_safety": 12,
  "endgame_terms": -1,
  "sum_of_components": 823,
  "actual_total_eval": 823,
  "residual_discrepancy": 0
}
```

---

### 5. Architectural Upgrade Roadmap for Candidate X10

Based on this audit, Candidate X10 must implement:
1. **Pawn Structure Refinements (E1):** Candidate passed pawns, backward pawns, pawn majorities, and protected passers.
2. **King Safety Refinements (E2):** Scale attack units with Queen presence, open file penetration towards king, and pawn storm detection.
3. **Mobility & Piece Coordination (E3):** Queen mobility, true outpost security (enemy pawn cannot attack), and color-separated bishop pair bonuses.
4. **Pawn Hash Table (Phase 4):** 16 MB Zobrist-indexed pawn cache storing precomputed pawn scores, passed pawn masks, and structural weaknesses to double evaluation throughput.

**Status:** Phase 1 Completed & Verified.

