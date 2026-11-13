# Milestone P1.15: Strategic Research Direction
**Architectural Foundation:** Janus Classical X19 (MovePicker Stage Reform)  
**Parent Qualified Baselines:** Janus Classical X7 (`b34e342`) / Janus Classical X12 (`78ca3d5`)  
**Author:** Principal Computer Chess Engine Architect & Statistical Auditor  
**Date:** 2026-11-13  
**Status:** APPROVED ARCHITECTURAL ROADMAP FOR P1.15

---

## 1. Context and Accomplishments of P1.14

Milestone P1.14 achieved a decisive architectural breakthrough:
1. **Root Cause Resolved:** Identified that earlier engines searched losing tactical captures ($\text{SEE} < 0$) before killer moves and countermoves, artificially delaying cutoffs and inflating the effective branching factor.
2. **MovePicker Stage Reform (Option C):** Partitioning captures by $\text{SEE} \ge 0$ vs $\text{SEE} < 0$ and inserting Killers and Countermoves before Quiets reduced search nodes by **90%–94%** and surged first-move cutoffs (BF1) from **77% to 93%**.
3. **Playing Strength Breakthrough:**
   - 1T Primary vs X7: **55.50% (+38.4 Elo)** (first decisive victory over X7).
   - 4T Primary vs X12: **53.00% (+20.9 Elo)**.
   - Historical vs Stockfish 4: **5.00% (4 Draws)**.
   - Modern vs Stockfish 19 (4T): **3.75% (3 Draws)**.

However, Milestone P1.14 also uncovered a key empirical vulnerability:
- **Time-Control Divergence:** In Match 2 (Slow TC: 2.5s + 100ms), Candidate X19 scored **43.00% (-49.0 Elo)** against X7.
While X19 dominates at fast TC where high BF1 allows deeper tactical reaches, at longer time controls (where both engines achieve depth 14–18), deferring bad captures unconditionally to the very end of the move list can induce horizon blindness in complex tactical endgames.

---

## 2. Strategic Objectives for Milestone P1.15

Milestone P1.15 must consolidate the massive search tree savings of X19 while eliminating the slow time control degradation. The roadmap focuses on three targeted, non-ML classical search mechanisms:

### Objective 1: Depth-Dependent Bad Capture Deferral (Adaptive Stage 5)
- **Problem:** Currently, in `MovePicker`, all moves with $\text{SEE} < 0$ are dumped into `STAGE_BAD_CAPTURES` and searched after all quiet moves. In deep endgames with few pieces, a "bad capture" (e.g. piece sacrifice to prevent pawn promotion or mate) may be the only winning/drawing line. Forcing the engine to search 30 irrelevant quiet moves before examining this capture causes search cutoffs or timeouts before the vital move is evaluated.
- **Proposed Intervention:** 
  - For shallow depths or high piece counts: preserve full deferral.
  - In endgame states (total non-pawn material $\le 1$ minor piece per side) or at remaining depth $\le 2$: promote tactical captures to stage 1.5 if their SEE deficit is small (e.g., $-100 \le \text{SEE} < 0$).
  - Cap bad capture deferral so that if all quiets fail low, bad captures are evaluated with appropriate aspiration bounds.

### Objective 2: History Score Normalization & Sparse-History Uncertainty (H1 Resolution)
- **Problem:** The P1.14 History Atlas proved that in **44.7%** of move disagreements between Janus and Stockfish 11, the optimal reference move had a history score of **exactly 0**. Low history score does not imply move inferiority; it merely reflects lack of observation.
- **Proposed Intervention:**
  - Introduce **History Score Gravity / Linear Aging** between search iterations so stale history does not permanently overshadow unvisited legal moves.
  - Modulate LMR reductions so that unvisited moves (history score $\approx 0$) receive mild, neutral reductions ($R=1$) rather than punitive reductions.

### Objective 3: Singular Extensions Evaluation (Bridging to Stockfish 4/11)
- **Problem:** Stockfish 4 and 11 achieve enormous search depth advantages on critical lines because they recognize when the TT move is significantly superior to all alternatives (singular move) and extend search depth by +1 ply. Janus searches uniformly, occasionally missing tactical shots that appear 1 ply beyond its horizon.
- **Proposed Intervention:**
  - Implement a carefully constrained Singular Extension mechanism on PV and Cut nodes at depth $\ge 8$, extending by 1 ply only when the TT move margin exceeds $2 \times \text{depth}$ in centipawns.

---

## 3. Methodological Charter & Rules for P1.15

1. **Strictly Non-ML Charter:** Zero neural networks, NNUE, learned evaluation parameters, SPSA, Texel tuning, or automated offline fitting.
2. **Mandatory Multi-Control Testing:** Every proposed modification in P1.15 must be qualified across BOTH the standard rapid time control (1.0s + 50ms) and the slow time control (2.5s + 100ms) against X7, X12, and X19.
3. **Preservation of Baselines:** Janus Classical X7 and X12 remain permanent immutable controls.
4. **Reproducibility Standard:** 100% paired-opening books with color reversal, exact SHA-256 manifests, and open PGN archives.

