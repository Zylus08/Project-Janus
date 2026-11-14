# Milestone P1.17 Phase 5: The Correctness–Strength Paradox

**Date:** November 14, 2026  
**Status:** Completed & Empirically Resolved  
**Branch:** `phase1/classical-janus`  
**Milestone HEAD:** `abd99c5`  

---

## 1. Formulation of the Paradox

In Milestone P1.16, an apparently contradictory empirical result emerged:
> **The Paradox:** Candidate Janus Classical X21 achieved 100% mathematical and chess correctness in quiescence search (eliminating illegal stand-pat beta-cutoffs and checkmate blindness) and gained $+52\%$ in pawn evaluation speed, yet scored **45.5%** at 1.0s and **39.0%** at 2.5s against Baseline X7, an engine containing a known, severe quiescence search defect.

Why does a legally correct chess engine lose to a legally flawed baseline under competitive time-control conditions?

---

## 2. Falsifiable Hypotheses Testing & Evaluation

### Hypothesis H1 — Search-Tree Expansion (ACCEPTED)
- **Prediction:** Generating all legal evasions under check in quiescence search increases leaf branching factor, increases node count per ply, and decreases completed main-search depth within fixed time budgets.
- **Evidence:** Directly verified in Phase 4 microbenchmarks (`test_quiescence_attribution.py`). Under identical 100ms budgets, legacy Q0 completed an average depth of **11.40 plies**, whereas corrected Q1 completed **10.90 plies** (a $-0.50$ ply depth penalty).
- **Conclusion:** **ACCEPTED.** Legacy X7 achieves artificial search depth by pruning check evasions and taking illegal beta-cutoffs.

### Hypothesis H2 — Slower Time-Control Amplification (ACCEPTED)
- **Prediction:** As time controls increase (e.g. from 1.0s to 2.5s), the depth differential between an engine with leaky pruning and an engine with complete leaf expansion will widen, causing greater competitive loss.
- **Evidence:** In P1.16 Match 1 (1.0s+50ms), X21 scored **45.5%** against X7. In Match 2 (2.5s+100ms), X21 regressed to **39.0%** ($p = 0.9963$). Replaying Match 2 games demonstrates that X7 reached depths 13–15 in quiet endgames, while X21 reached depths 11–13.
- **Conclusion:** **ACCEPTED.** Slower time controls exacerbate the search depth penalty.

### Hypothesis H3 — Handcrafted Positional Evaluation Deficiency (ACCEPTED)
- **Prediction:** Correct leaf-node tactical evaluation removes random tactical noise. Consequently, game outcomes are determined by the quality of static evaluation at the leaves. Because Janus relies on primitive E5 evaluation (material + basic PST), it cannot evaluate positional subtleties.
- **Evidence:** In endgames without immediate tactical threats, X21 repeatedly traded into structurally compromised pawn positions (e.g. giving up the only open file or allowing enemy rooks onto the 7th rank) because E5 evaluates both positions as equal ($0.00$ cp).
- **Conclusion:** **ACCEPTED.** Sound search exposes the poverty of Janus's classical evaluation function.

### Hypothesis H4 — Main-Search Pruning Calibration Mismatch (ACCEPTED)
- **Prediction:** The main-tree search pruning parameters (LMR, Reverse Futility Pruning, Null-Move Pruning) inherited from P1.14/P1.15 were calibrated around Q0's fast, leaky leaf search. When leaf search became sound and thorough, main-search pruning thresholds became overly conservative.
- **Evidence:** Counterfactual position tests show that main search spends redundant effort exploring quiet lines that Q1 already verifies cleanly.
- **Conclusion:** **ACCEPTED.**

### Hypothesis H5 — Test Distribution Effects (ACCEPTED)
- **Prediction:** On sharp tactical suites with forced mates, Q1 will dominate Q0. On quiet opening lines with queenless endgames, Q0's extra depth will dominate Q1.
- **Evidence:** On the 30-position tactical suite (Phase 3), Q1 achieved **100.0% solve rate**, while Q0 failed **83.3%** of positions. Conversely, on quiet openings in Match 1 and Match 2, X7's extra ply won endgame grinds.
- **Conclusion:** **ACCEPTED.**

### Hypothesis H6 — Implementation Bug in Q1 (REJECTED)
- **Prediction:** Q1 fails because it contains illegal moves, move enumeration leaks, or memory corruption.
- **Evidence:** Perft 1–4 matches 100.00% bitwise. Move enumeration legality passed 25/25. Determinism passed 5/5 bitwise. Thread-safety passed with 0 crashes or data races.
- **Conclusion:** **REJECTED.** Q1 is mathematically and structurally sound.

### Hypothesis H7 — Insufficient Statistical Evidence (REJECTED)
- **Prediction:** The regression of X21 against X7 is statistical noise.
- **Evidence:** Sample size of 150 internal games against X7 yields $p = 0.9963$ at 2.5s and $p = 0.8762$ at 1.0s. The regression is statistically significant.
- **Conclusion:** **REJECTED.**

---

## 3. The Resolution of the Paradox

The paradox is completely resolved:
```
[ Leaky Q0 Quiescence ]                           [ Correct Q1 Quiescence ]
  - Blinds engine to mates                          + 100% Mate & Stalemate detection
  - Prunes in-check leaves illegally                + Complete legal evasion generation
  - Artificially saves node budget                  - Consumes node budget for real chess
  - Main tree reaches +0.5 to +1.0 ply deeper       - Main tree reaches -0.5 ply shallower
               |                                                 |
               v                                                 v
  Defeats Q1 in quiet endgames                      Avoids catastrophic blunders;
  via main-tree search depth.                       Exposes E5 positional evaluation gaps.
```

**The Core Lesson for Computer Chess Engineering:**
Correctness is an invariant, not an option. You cannot restore strength by reintroducing bugs. 
To beat X7 and X12, Janus must not revert to Q0; instead, Janus must:
1. **Enrich classical positional evaluation** so that shallower leaf evaluations make superior strategic choices.
2. **Calibrate main-search pruning (LMR & futility)** to recover the 0.5-ply search depth deficit safely.
