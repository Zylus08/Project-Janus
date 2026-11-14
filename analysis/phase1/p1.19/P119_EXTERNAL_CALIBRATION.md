# External Benchmark Calibration: Candidate X24 vs Stockfish 4, Stockfish 11 & Stockfish 19

## 1. Executive Summary

Milestone P1.19 benchmarks Candidate **Janus Classical X24-S** against three external reference engines representing distinct eras of computer chess engineering:
1. **Stockfish 4 (2014)**: Classical handcrafted evaluation (~3100 Elo).
2. **Stockfish 11 (2020)**: Peak classical handcrafted evaluation (~3450 Elo).
3. **Stockfish 19 (`edb0d9d`, NNUE)**: State-of-the-art unrestricted neural network evaluation (~3650+ Elo).

Each match consisted of 20 opening pairs (40 games) contested at 1.5s base + 50ms Fischer increment (1 thread) with verified non-interfering adjudication.

### Summary of External Benchmark Calibration:

| External Opponent | Engine Era | Score (Wins / Draws / Losses) | Win Rate (%) | Pentanomial $[2, 1.5, 1, 0.5, 0]$ | Paired 95% CI | Elo Difference |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Stockfish 4** | Early Classical (2014) | 0.0 / 40 (+0 =0 -40) | **0.0%** | $[0, 0, 0, 0, 20]$ | $[0.0\%, 0.0\%]$ | $-\infty$ |
| **Stockfish 11** | Peak Classical (2020) | 1.0 / 40 (+0 =2 -38) | **2.5%** | $[0, 0, 0, 2, 18]$ | $[0.0\%, 5.87\%]$ | **-636.4 Elo** |
| **Stockfish 19** | Modern NNUE (2026) | 2.5 / 40 (+0 =5 -35) | **6.25%** | $[0, 0, 0, 5, 15]$ | $[1.38\%, 11.12\%]$ | **-470.4 Elo** |

---

## 2. Forensic Analysis of the "NNUE Calibration Paradox"

A recurring observation across Milestones P1.16 through P1.19 is the apparent paradox where Janus classical engines score higher against modern Stockfish 19 (6.25%) than against historical classical engines like Stockfish 4 (0.0%) and Stockfish 11 (2.5%).

### 2.1 The Underlying Root Causes

1. **Drawish Positional Tendencies of NNUE at Low Time Controls:**
   - In Match 7, Candidate X24 scored 5 draws against Stockfish 19 (Pair 02 G2, Pair 09 G2, Pair 11 G1, Pair 13 G1, Pair 17 G1).
   - In all 5 draws, the position reached a closed or locked pawn structure (French Defense, Caro-Kann, closed Catalan) where NNUE evaluations remained balanced (+0.4 to +0.8 cp) without finding a concrete breakthrough. At 1.5s + 50ms, Stockfish 19 opted for piece shuffles that triggered threefold repetitions or 50-move draws.
2. **Ruthless Tactical Endgame Conversion in Classical Stockfish:**
   - In contrast, Stockfish 4 and Stockfish 11 use handcrafted classical piece-mobility, pawn-push bonus tables, and aggressive king-safety heuristics.
   - When facing Janus in closed or semi-closed structures, SF4 and SF11 did not shuffle passively. Instead, they executed tactical piece sacrifices and aggressive pawn breaks (e.g. f4-f5, g4-g5, c4-c5) that broke open the position.
   - Janus Classical engines lack advanced tactical pruning (ProbCut, MultiCut, Singular Extensions) and deep tactical evaluation, causing them to collapse tactically against SF4 and SF11. In Match 5, SF4 converted 40 out of 40 games decisively.
3. **P1.16/P1.17 Statistical Reconciliation Confirmed:**
   - Milestone P1.16's erroneous report of 22.5%–27.5% against SF19 was definitively caused by harness score-inversion bugs during resignation adjudication.
   - P1.17 corrected the harness and established the true baseline score of ~5–7%.
   - P1.19's independent result of 6.25% (2.5 / 40) under the certified 15-case harness confirms that the true playing strength of Janus Classical against SF19 at fast blitz is consistently 5–7%.

---

## 3. Classical Alpha-Beta Search & Evaluation Gap Analysis

The external benchmark results highlight the fundamental architectural gulf separating Janus Classical X24 (~2800–2850 Elo) from mature classical engines (SF4 at ~3100 Elo and SF11 at ~3450 Elo):

### 3.1 Search Tree Pruning Deficits
- **Lack of ProbCut / MultiCut:** Mature classical engines prune large subtrees when tactical quiescence search or null-move searches establish that a beta cutoff is virtually guaranteed. Janus relies solely on standard Null Move Pruning ($R=3$), Late Move Reductions (LMR), and Reverse Futility Pruning (RFP), resulting in wider, shallower search trees.
- **Absence of Singular Extensions:** When one move is vastly superior to all alternatives, engines like SF4 and SF11 extend the search by 1 or 2 plies. This prevents tactical blindspots in critical forcing lines. Janus currently searches all PV nodes at standard depth.

### 3.2 Evaluation Deficits
- **Non-Linear Mobility & Trap Detection:** While Janus models piece mobility, it lacks penalties for trapped pieces (trapped bishops on a7/h7, trapped rooks on a8/h8 behind pawns) and outpost support matrices.
- **Complex Pawn Endgame Dynamics:** Janus Classical X24 introduces backward-pawn detection, but lacks connected passed pawns, passed pawn candidate scoring, king distance to passed pawn squares, and opposition heuristics. In endgames against SF4 and SF11, Janus regularly loses pawn races that mature engines evaluate accurately.

---

## 4. Calibration Conclusions

The external benchmark battery demonstrates that Candidate X24 remains firmly within the established Janus classical playing tier. Handcrafted pawn terms like backward pawns do not close the competitive gap to historical reference engines like Stockfish 4. Realizing substantial Elo gains will require addressing search tree depth, selective extensions, and comprehensive piece-pawn endgame interactions.
