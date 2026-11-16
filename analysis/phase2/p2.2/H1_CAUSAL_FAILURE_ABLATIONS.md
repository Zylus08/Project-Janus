# Project Janus — Phase 2, Milestone P2.2
## Phase 8: Controlled Model Failure Ablations & Match Qualification

**Author:** Principal Computer Chess Architect & Experimental Statistician  
**Milestone:** P2.2 — Neural Evaluation Failure Forensics, Score Calibration & Scalable Dataset Readiness  
**Date:** 2026-11-16  
**Subject:** Causal Ablation Controls & Head-to-Head Qualification: Hybrid H2 vs Classical R1  

---

### 1. Executive Summary & The Central Scientific Resolution

Milestone P2.2 posed a fundamental question to resolve the central experimental contradiction of Phase 2:
> *"Does H2 improve on classical R1, or merely on weak H1?"*

In Milestone P2.1, Candidate H2 (50% Classical + 50% NNUE) achieved a dominant 99.0% score (+49 =1 -0) against Candidate H1 (pure NNUE). This led to the working hypothesis that hybrid evaluation might represent a net improvement over classical evaluation.

Phase 8 conducted an authoritative, pre-registered 50-game match between **Hybrid H2** and **Classical R1** under identical search parameters (5.0s + 0.05s, opening pair symmetry from `independent_openings_v056.json`).

**The Empirical Result is Decisive:**
- **Score:** Hybrid H2 scored **4.0 / 50 (+0 =8 -42) | 8.0% | Elo: -424.3** against Classical R1.
- **Pentanomial Distribution [0.0..2.0]:** `[17, 8, 0, 0, 0]` (17 double-losses, 8 loss-draws, 0 wins).
- **Paired 95% Confidence Interval:** $[3.3\%, 12.7\%]$ (SE: $0.0238$, $p < 0.0001$).

```
========================================================================================
THE PHASE 2 TRIADIC TOURNAMENT RESULTS
========================================================================================
Match Comparison                | Games | Candidate Score | Pts (%) | Elo Differential
--------------------------------+-------+-----------------+---------+-------------------
R1 (Classical) vs H1 (Pure NNUE)| 100   | 98.5 / 100      | 98.5%   | R1 +726.9 Elo
H2 (Hybrid)    vs H1 (Pure NNUE)| 50    | 49.5 / 50       | 99.0%   | H2 +798.3 Elo
Classical R1   vs H2 (Hybrid)   | 50    | 46.0 / 50       | 92.0%   | R1 +424.3 Elo
========================================================================================
Transitive Hierarchy: Classical R1 (Baseline) >> Hybrid H2 (-424 Elo) >> Pure NNUE H1 (-727 Elo)
```

**Scientific Conclusion:**
**Hybrid H2 does NOT improve upon Classical R1.**
Blending H1's neural evaluation into Classical R1 severely degrades Classical R1's playing strength (a drop of $424\text{ Elo}$). 
The only reason H2 defeated H1 by 99% in Milestone P2.1 is because H1 is even weaker (a further $300\text{ Elo}$ lower). 
The classical evaluation in H2 gave it enough material sanity to punish H1's blunders, but H1's compressed, distorted neural evaluations contaminated Classical R1's move ordering and tactical pruning.

---

### 2. Controlled Model Ablations Summary

| Ablation Configuration | Description | White +Q Score (cp) | Win Outcome on Equal Draw (cp) | Queen vs Knight Ratio | Held-Out Test Accuracy |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **A0 (Classical R1)** | Handcrafted E15 Classical Evaluation | $+867$ | $0$ | $867 / 270 = 3.21$ | N/A (Handcrafted) |
| **A1 (Frozen H1 NNUE)** | Original 208 KB DP-PS-768 Network | $+203$ | $+26$ | $203 / 226 = \mathbf{0.90}$ | $59.8\%$ |
| **A2 (Calibrated H1)** | Scale expanded 3.5x & de-biased by $-52\text{ cp}$ | $+528$ | $0$ | $528 / 609 = 0.87$ | $59.8\%$ |
| **A4 (Random / Untrained)**| Randomly initialized weights ($\mathcal{N}(0, 0.05)$) | $+4$ | $+2$ | Undefined | $50.1\%$ |
| **A5 (Controlled Hybrid H2)**| 50% Classical R1 + 50% Frozen H1 | $+535$ | $+13$ | $535 / 248 = 2.16$ | N/A (Composite) |

---

### 3. Answers to Mandatory Diagnostic Questions

1. **Does the original H1 outperform an untrained network?**
   **YES.** H1 achieves $59.8\%$ prediction accuracy on held-out positions compared to $50.1\%$ for a random network, and produces positive scores for winning sides. It has learned basic chess orientation.
2. **Does it reproduce known material advantages?**
   **NO.** H1 suffers from severe material distortion: in starting positions, it values a Knight ($+226\text{ cp}$) higher than a Queen ($+203\text{ cp}$).
3. **Does its error grow sharply on held-out openings?**
   **YES.** Because the DP-PS-768 architecture has no king-relative features and was trained on only 40k middlegame positions, opening positions with piece placements outside its training distribution exhibit noisy piece-square margins.
4. **Does corrected score orientation eliminate the catastrophic performance deficit?**
   **NO.** Score orientation is already correctly aligned with the side to move. While calibration fixes magnitude scaling, it cannot fix the fundamental lack of king shelter, king safety, and tactical awareness in the DP-PS-768 architecture.
5. **Does H2 improve on classical R1, or merely on weak H1?**
   **It merely beats weak H1.** In head-to-head play against Classical R1, H2 is crushed, scoring only $8.0\%$ (+0 =8 -42). Contaminating Classical R1 with H1 degrades playing strength by $-424\text{ Elo}$.

---

### 4. Milestone Release Policy Implication

Because H2 is demonstrably inferior to Classical R1, neither H1 nor H2 can serve as a production engine candidate. 
No new model (H3) may be trained using the flawed P2.1 training pipeline. 
The project must address the training objective, dataset quality, and feature architecture before training a successor model.
