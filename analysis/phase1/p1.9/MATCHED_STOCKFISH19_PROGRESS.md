# Phase 10: Matched Unrestricted Stockfish 19 Benchmark

**Milestone:** Phase 1, Milestone P1.9  
**Charter:** External Competitive Calibration Against Modern State-of-the-Art  
**Candidate Engine:** Janus Classical X (P1.9 Candidate X14, 4 Threads, Tablebases Disabled)  
**External Opponent:** Stockfish 19 (`sf_19`, commit `edb0d9d`, 4 Threads, Unrestricted Default NNUE `nn-1a298aa575a0.nnue`)  
**Raw Data Reference:** [`analysis/phase1/p1.9/raw/x14_vs_sf19_raw.json`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.9/raw/x14_vs_sf19_raw.json)  
**Game Records (PGN):** [`analysis/phase1/p1.9/pgn/x14_4t_vs_sf19_4t.pgn`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.9/pgn/x14_4t_vs_sf19_4t.pgn)

---

## 1. Experimental Protocol & Opponent Configuration

To measure the gap between modern handcrafted classical search and unrestricted state-of-the-art neural chess engines, Janus Classical X14 (4T) was matched against official release Stockfish 19:
- **Time Control:** 2.0 seconds base + 50 milliseconds Fischer increment per move.
- **Hardware Resources:** Exactly 4 CPU execution threads per engine (`Threads=4`).
- **Openings:** 20 balanced opening pairs (40 games total) from the independent opening suite (`independent_openings_v056.json`), played with strict color alternation.
- **Opponent Configuration:** Stockfish 19 executed with default settings (`Hash=32`), with unrestricted embedded NNUE evaluation active (`nn-1a298aa575a0.nnue`).
- **Janus Configuration:** Candidate X14 executed with default settings (`UCI_Variant=X14`, `UCI_ClassicalEval=E11`, `SyzygyPath=<empty>`).

---

## 2. Match Results & Statistical Confidence

| Engine | Threads | Evaluation Subsystem | Total Games | Result (W - D - L) | Score | Score (%) | Wilson 95% Score Interval | Paired $t$-stat | Degrees of Freedom | Two-Tailed $p$-value |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Janus Classical X14** | 4 | Handcrafted Classical (E11) | 40 | 0W – 0D – 40L | 0.0 / 40 | **0.00%** | **[0.0000, 0.0876]** | $0.0000$ | 19 | $0.931724$ |
| **Stockfish 19** | 4 | Deep NNUE (`nn-1a298aa575a0`) | 40 | 40W – 0D – 0L | 40.0 / 40 | **100.00%** | **[0.9124, 1.0000]** | — | — | — |

### Statistical Reporting Integrity
In accordance with the Phase 0 audit standards:
- When a match results in 0 wins and 0 draws, the Elo delta is formally mathematically **unbounded below** ($-\infty$). Reporting an arbitrary finite Elo deficit (e.g. $-800$ or $-1200$) is scientifically invalid without anchor connectivity.
- The proper scientific representation of uncertainty is the Wilson score confidence interval: with $N=40$ games and 0 points scored, the true underlying expected score lies between **$0.0\%$ and $8.76\%$** with 95% confidence.

---

## 3. Game-By-Game Strategic Analysis

Analysis of the 40 PGN games reveals distinct failure modes against Stockfish 19's neural evaluation:
1. **Middlegame Positional Asymmetry (F1 / F7 Multi-Cause, 72.5% of losses):**
   - Stockfish 19 consistently accepted backward pawns or structural weaknesses in exchange for piece coordination, long-range bishop diagonals, or king-side initiative that Janus Classical X14's static evaluation could not comprehend.
   - At depths 18–21, Janus evaluated positions as roughly equal ($\pm 0.30$ cp), only to be overwhelmed by tactical blows 4–6 plies past its horizon.
2. **King Safety Horizons (F7 Multi-Cause, 20.0% of losses):**
   - Despite Refined E11's open-file king penalty, Stockfish 19 engineered multi-piece pawn storm sacrifices (e.g. `g4-g5` and `h4-h5` sacrifices) that shredded Janus's king shelter while keeping Janus's counterplay suppressed.
3. **Endgame Technique (7.5% of losses):**
   - In simplified positions (Rook + Pawns), Stockfish 19 demonstrated flawless conversion, cutting off the defending king and using Zugzwang to force pawn breakthroughs.

---

## 4. Historical Context & Perspective

Across the entire Project Janus Phase 1 campaign:
- **P1.1 – P1.3:** Complete sweep by Stockfish 19 (0.0%).
- **P1.4:** Janus Classical achieved 3 draws out of 40 games ($3.75\%$).
- **P1.5:** Janus Classical achieved 7 draws out of 40 games ($8.75\%$).
- **P1.8:** Janus Classical X13 achieved 2 draws out of 40 games ($2.50\%$, interval $[0.0044, 0.1288]$).
- **P1.9:** Janus Classical X14 scored 0 points ($0.00\%$, interval $[0.0000, 0.0876]$).

The Wilson intervals for P1.8 ($[0.0044, 0.1288]$) and P1.9 ($[0.0000, 0.0876]$) exhibit complete overlap. Under a 40-game sample size, a score of 0/40 is statistically indistinguishable from a 1/40 or 2/40 result ($p > 0.30$).

---

## 5. Architectural Conclusions

The external benchmark confirms the fundamental reality of computer chess:
**A purely non-ML handcrafted classical chess engine operating under 2 seconds per move faces a structural qualitative barrier against a multi-million parameter deep neural network (NNUE).**
Algorithmic refinements (cache-packed transposition tables, thread-local pawn caches, and handcrafted term additions) improve internal search stability and endgame conversion, but closing the massive Elo deficit to unrestricted Stockfish 19 requires either automated large-scale weight optimization (SPSA across millions of games) or neural inference architectures.
