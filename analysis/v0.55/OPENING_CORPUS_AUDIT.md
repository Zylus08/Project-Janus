# Project Janus v0.55 — Independent Opening Corpus Audit Report

**Milestone:** v0.55  
**Date:** 2026-11-05  
**Auditor:** Principal Chess Engine Research Architect & Experimental Statistician  
**Corpus File:** `analysis/v0.55/corpus/independent_openings_v055.json`  
**Corpus SHA-256:** `8c98c1f07aac802acdc3883b031c16a4b1bad8b0c2edd4f68d4117acd60c40a3`  
**Generator Script:** `analysis/v0.55/tests/generate_independent_corpus.py`  
**Reference Blacklist:** `analysis/v0.54/corpus/openings_v052_100.json` (SHA-256: `90b6cb509d3b4588e14620f4c94da8a25d2c80be357a6671faaa29ec62d5cb3c`)  

---

## 1. Corpus Independence & Non-Overlap Verification

To satisfy Phase 2.1 requirements for out-of-sample statistical testing:
1. **Zero Overlap with Historical Suites:** Every candidate position was checked against the complete set of 100 board states used in the v0.52, v0.53, and v0.54 primary strength matches using normalized Extended Position Description (`chess.Board.epd()`).
   - Exact FEN/EPD matches: **0 / 100 (0.0%)**
   - Transposition collisions: **0 / 100 (0.0%)**
2. **Zero Internal Transpositions:** Every generated board state is unique within the 100-position suite.
3. **Strict Move Legality:** All move sequences were validated move-by-move using `chess.Board.push_san()`. No illegal moves, illegal castling, or pawn-structure corruptions exist.
4. **No Premature Terminal States:** All 100 positions terminate with active play available (0 checkmates, 0 stalemates, 0 threefold repetitions).
5. **No Candidate Outcome Consultation:** Positions were curated strictly based on standard classical ECO opening lines prior to any match execution.

---

## 2. Structural Composition & ECO Distribution

$$\begin{array}{|l|l|c|c|l|}
\hline
\textbf{ECO Class} & \textbf{Family Description} & \textbf{Count} & \textbf{Percentage} & \textbf{Representative Systems Included} \\
\hline
\textbf{ECO A} & \text{Flank, English, Dutch, Reti, Unorthodox} & 22 & 22.0\% & \text{Bird's, Larsen, Reti Gambit, English Four Knights, Dutch Stonewall} \\
\textbf{ECO B} & \text{Semi-Open Games (excl. French)} & 25 & 25.0\% & \text{Caro-Kann Fantasy/Two Knights, Pirc 150, Sicilian Alapin/Smith-Morra/Najdorf} \\
\textbf{ECO C} & \text{Open Games (e4 e5) \& French} & 25 & 25.0\% & \text{Vienna Gambit, Scotch Mieses, Berlin 4.O-O, Marshall Attack, Schliemann} \\
\textbf{ECO D} & \text{Closed Games (d4 d5) \& Gruenfeld} & 15 & 15.0\% & \text{QGD Albin/Chigorin/Semi-Tarrasch, Jobava London, Gruenfeld Bf4} \\
\textbf{ECO E} & \text{Indian Defenses \& Catalan} & 13 & 13.0\% & \text{Open Catalan, Bogo-Indian, Nimzo-Rubinstein, King's Indian Mar del Plata} \\
\hline
\textbf{Total} & \textbf{Independent Master Suite} & \mathbf{100} & \mathbf{100.0\%} & \textbf{Complete Stratified Coverage across Modern Chess Theory} \\
\hline
\end{array}$$

### 2.1 Ply Depth Stratification
- Minimum Move Depth: 4 plies (2 full moves)
- Maximum Move Depth: 18 plies (9 full moves)
- Mean Move Depth: 10.42 plies (5.2 full moves)
- Side to Move: 54 White to move, 46 Black to move (ensuring natural branching variability from both sides).

---

## 3. Pairing Protocol Compliance

Every position in `independent_openings_v055.json` will serve as an opening pair:
- **Game 1:** Candidate plays White, Baseline plays Black.
- **Game 2:** Candidate plays Black, Baseline plays White.
- **Strict Color Reversal:** Guarantees that any opening bias cancels out exactly in paired difference tests ($d_i = \text{score}_{\text{cand}, i} - \text{score}_{\text{base}, i}$).

**Corpus Status:** **FROZEN AND CRYPTOGRAPHICALLY LOCKED (`8c98c1f...`)**.

