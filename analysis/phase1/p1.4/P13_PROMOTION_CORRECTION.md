# Project Janus — Phase 1, Milestone P1.4
## Phase 0 Governance Document: Correction of the P1.3 Engine Promotion Decision

**Author:** Principal Computer Chess Engineer, Statistical Experimentalist, Independent Reproducibility Auditor  
**Lineage:** Janus Classical X  
**Repository Worktree:** `E:\ChessXML\project-janus-phase1`  
**Branch:** `phase1/classical-janus`  
**Date:** 2026-11-10  
**Phase 1 Constraint:** Strictly Non-ML (Zero neural evaluation, zero learned weights, zero offline-fitted models)

---

### 1. Executive Summary & Administrative Action

In Milestone P1.3, the integrated candidate **Janus Classical X8** was formally designated as the new developmental baseline. An independent reproducibility and experimental audit of the raw match artifacts (`analysis/phase1/p1.3/pgn/x8_vs_x7.pgn` and `analysis/phase1/p1.3/raw/x8_vs_x7_tournament_raw.json`) confirms that this promotion was scientifically unjustified and violated the core empirical standards of Project Janus.

Under identical computational resources and balanced opening conditions ($1.0\text{s} + 50\text{ms}$, 50 opening pairs), Candidate X8 scored **42.5 / 100 (42.50%)** against Baseline X7, representing a statistically significant playing-strength regression of **$-52.5$ Elo** ($p = 0.0404$).

Effective immediately, the Project Janus Phase 1 baseline registry is formally corrected:

| Engine Lineage | Git Source Anchor | Executable SHA-256 | Milestone Status | Official Designation |
|---|---|---|---|---|
| **Janus Classical X7** | `b34e342` | `86392a2f4bd4182a4d7dc21e32940bd7939f6816794d5e1ab02f4082431ca28b` | Qualified | **Qualified Classical Baseline** |
| **Janus Classical X8** | `501efbc` | `05cd4dc8c38581fd5ee775dc1cea89011c83e6969828caae17ca6e8136fa9429` | Experimental | **Frozen Experimental Selectivity Candidate** |
| **Janus Classical X6** | `135c019` | `138b43bc3188696769f755f40898b69842e9e6c529e38a119d9734bad92a741c` | Qualified | Frozen Historical Control |
| **Classical C1** | `e543dab` | `a4f9d9d18b549d29b2e6740ac90d90d39167d92d3846b95fc0c4f5b966add83f` | Historical | Frozen Root Control |

**Policy Enforcement:**
- Historical Git commits and P1.3 artifacts are preserved without alteration or rewriting.
- All development in Milestone P1.4 proceeds with **Janus Classical X7** as the sole qualified baseline control.
- No newly proposed engine candidate (e.g., Janus Classical X9) will be promoted without statistically rigorous, positive empirical proof of superiority over X7.

---

### 2. Forensic Recomputation of the X8 vs X7 Match

The 100-game match was parsed directly from the raw PGN record (`x8_vs_x7.pgn`):
- **Opponent Engines:** `Janus Classical X8` (Candidate) vs `Janus Classical X7` (Control).
- **Time Control:** 1.0s base + 50ms Fischer increment per move.
- **Openings Corpus:** 50 balanced, colour-reversed opening pairs from `independent_openings_v056.json`.
- **Adjudication:** Strict standard FIDE draw rules (threefold repetition, 50-move rule, stalemate, insufficient material).

#### Reconstructed Match Scoreboard
- **Wins for X8:** 25 games (25.0%)
- **Draws:** 35 games (35.0%)
- **Losses for X8 (Wins for X7):** 40 games (40.0%)
- **Total Points for X8:** **42.5 / 100 (42.50%)**
- **Win/Draw/Loss Ratio:** +25 =35 -40
- **Paired Opening Distribution:**
  - 4 clean sweeps for X8 ($2.0 - 0.0$)
  - 5 wins for X8 ($1.5 - 0.5$)
  - 17 color splits ($1.0 - 1.0$)
  - 20 losses for X8 ($0.5 - 1.5$)
  - 4 clean sweeps for X7 ($0.0 - 2.0$)

#### Statistical Significance & Uncertainty Metrics
- **Point Estimate Elo Difference:** $\Delta \text{Elo} = -400 \log_{10}(1 / 0.425 - 1) = \mathbf{-52.5\text{ Elo}}$
- **Binomial 95% Wilson Confidence Interval:** $[33.27\%, 52.29\%] \rightarrow \Delta \text{Elo}: [-120.9, +15.9]$
- **Opening-Pair Clustered 95% Confidence Interval (Student's $t$, $df=49$):**
  $$\text{Mean} = 0.850\text{ pts/pair}, \quad \text{SE} = 0.0732\text{ pts/pair}$$
  $$\text{Clustered 95% CI} = [35.15\%, 49.85\%] \rightarrow \Delta \text{Elo}: [-106.4, -1.0]$$
- **Paired $t$-Test against Equal Strength ($\mu = 1.0$):**
  $$t = -2.0494, \quad p = \mathbf{0.0404}$$
  *(Statistically significant regression at the $\alpha = 0.05$ threshold)*
- **Wilcoxon Signed-Rank Test:**
  $$W = 183.0, \quad z = -1.742, \quad p = 0.0815$$

---

### 3. Forensic Audit of the P1.3 Attributions

The P1.3 report attempted to justify the adoption of X8 by citing:
1. Improved tactical accuracy on a 16-position atlas (+6.25%, solving `TAC_15`).
2. An 84-ply threefold repetition draw achieved against unrestricted Stockfish 19 (0.5/20 vs 0.0/20).

While these empirical observations are factually correct, the governance decision to promote X8 was flawed:
- **Flaw 1 (Equating puzzle solvability with playing strength):** High solve rates on curated tactical puzzles cannot substitute for head-to-head playing strength across diverse opening structures.
- **Flaw 2 (Single-game outlier weighting):** A single draw in 20 games against Stockfish 19 (which still represents a 97.5% loss rate) does not overcome a statistically significant 100-game match regression against the native control engine.
- **Flaw 3 (The Verification Depth Deficit):** In P1.3, Candidate X8 simultaneously enabled Singular Extensions, Multi-Cut Pruning, ProbCut, and Capture History without measuring their individual computational costs. Under equal clock limits, X8's nominal search depth was restricted to $d \approx 6.8$, whereas X7 routinely reached $d \approx 7.9$. In quiet middlegames and technical endgames, this $-1.1$ ply deficit produced 20 pair losses against only 5 pair wins.

---

### 4. Directives for Milestone P1.4

1. **Feature-Level Decomposition:** Every single P1.3 modification must be isolated into independent test configurations (B0 through B7).
2. **Computational Cost Attribution:** Quantify the exact node and millisecond expense of verification searches vs cutoffs.
3. **Requalification Mandate:** Only features demonstrating positive net search economics per unit of computation will be considered for inclusion in Candidate X9.
4. **Retention Baseline:** If no tested candidate demonstrates statistically significant superiority over X7 in a 200-game match, **Janus Classical X7 will be retained as the permanent baseline of Phase 1**.

**Sign-off:** Principal Computer Chess Engineer & Independent Experimental Auditor.

