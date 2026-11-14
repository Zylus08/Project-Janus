# Strategic Direction for Milestone P1.21: Deep Selective Alpha-Beta Search & Advanced King-Safety Architecture

## 1. Executive Summary & Milestone P1.20 Retrospective

Milestone P1.20 achieved a major scientific breakthrough by resolving the fundamental question of why successive classical research candidates regressed at longer time controls:
1. **The Causal Mechanism of Slow-TC Degradation Identified:** Static positional penalties (such as the backward-pawn terms introduced in P1.18–P1.19) systematically suppressed Reverse Futility Pruning (RFP) by depressing static evaluations below beta, leading to a $+27.3\%$ node explosion in quiescent subtrees and inducing passive piece defense in deep endgame searches.
2. **The Slow-TC Anomaly Resolved:** Milestone P1.20 replaced static penalties with dynamic evaluation bonuses via **Option B: Connected & Supported Passed Pawns**. In Match 5, Candidate X25-S achieved **49.0%** against Baseline X7 at $3.0\text{s}+100\text{ms}$ ($p = 0.8380$), completely eliminating the $-92.5$ Elo regression suffered by X24.
3. **The Limits of Static Evaluation Heuristics:** Across 950 games in P1.20, Candidate X25 achieved solid parity against Reference X22 (48.0% fast, 44.0% slow) and Baseline X7 (48.0% fast, 49.0% slow). However, neither X22, X24, nor X25 was able to displace Baseline X7. Furthermore, external calibration against Stockfish 4 (1.25%), Stockfish 11 (0.00%), and Stockfish 19 NNUE (7.50%) confirms that a ~250–300 Elo gap separates Janus from mature classical engines.

**Strategic Epiphany:** Positional pawn evaluation adjustments alone have reached diminishing marginal returns. To achieve a statistically significant Elo leap ($+50$ to $+100$ Elo) and displace Baselines X7 and X12, Milestone P1.21 must transition to **Selective Search Tree Deepening** and **Tactical Pruning Enhancements**.

---

## 2. Core Strategic Pillars for Milestone P1.21

### Pillar 1: Singular Extensions (SE)
- **Current Limitation:** Janus Classical executes uniform-depth search at Principal Variation (PV) nodes. When a tactical blunder or subtle defense exists at depth $D+1$, uniform search suffers from horizon blunders.
- **P1.21 Architectural Design:**
  - At depth $\ge 8$, when a Transposition Table (TT) move exists with an exact or lower-bound score, execute a reduced-depth verification search (depth $D/2$ or $D - 3$) with an excluded move.
  - If no alternative move can achieve within $s\text{ cp}$ (e.g. $s = 20\text{–}30\text{ cp}$) of the TT score, the TT move is declared **singular**.
  - Extend the search for that singular move by $+1$ ply (or $+2$ plies for double-singular moves).
  - This allows critical forcing lines to reach depths of 14–18 plies within the same time budget, directly targeting the tactical superiority displayed by Stockfish 4 and 11.

### Pillar 2: ProbCut (Probabilistic Cutoffs)
- **Current Limitation:** Janus Classical relies on standard Null-Move Pruning ($R=3$), Late Move Reductions (LMR), and Reverse Futility Pruning (RFP). It explores many branches that have an infinitesimal probability of improving alpha.
- **P1.21 Architectural Design:**
  - In non-PV nodes at depth $\ge 5$, execute a shallow search (depth $D - 4$) with a raised beta margin ($\beta + 150\text{ cp}$).
  - If this shallow search triggers a beta cutoff, prune the entire subtree immediately.
  - This prunes hopelessly lost branches early, redirecting CPU cycles toward critical tactical variations.

### Pillar 3: Multi-Piece King Danger Zone & Attacker Geometry
- **Current Limitation:** Track B (P1.18) attempted to penalize open files near the king statically, which resulted in fatal blunders because it penalized the king even when the opponent possessed no attacking pieces.
- **P1.21 Architectural Design:**
  - Define a dynamic 12-square King Zone (the 8 surrounding squares plus 4 squares in front).
  - Track an Attacker Count ($N_{\text{att}}$) and an Attacker Weight Sum ($W_{\text{att}}$) for enemy pieces whose move ray intersects the King Zone.
  - Condition: King danger penalties are strictly zero unless $N_{\text{att}} \ge 2$ (at least two attacking pieces).
  - Apply a non-linear quadratic danger formula:
    $$\text{KingExposurePenalty} = \frac{(W_{\text{att}})^2}{64}$$
  - This creates genuine tactical awareness of mating attacks while remaining 100% immune to the phantom penalties that doomed Track B.

### Pillar 4: Endgame King Proximity to Passed Pawns
- **Current Limitation:** Candidate X25 rewards connected passed pawns, but does not evaluate king proximity to the promotion path. In rook and pawn endgames, Janus frequently allows the enemy king to escort passed pawns unchecked.
- **P1.21 Architectural Design:**
  - For each passed pawn, compute the Manhattan/Chebyshev distance from both friendly and enemy kings to the promotion square.
  - Reward friendly king proximity: $+5\text{ cp} \times (7 - \text{dist})$.
  - Penalize enemy king proximity when the pawn is unsupported: $-8\text{ cp} \times (7 - \text{dist})$.
  - Combine with Option B's connected passer bonuses to create decisive endgame conversion capabilities.

---

## 3. Baselines & Reference Control Hierarchy for P1.21

| Engine Designation | Version / Commit | Architectural Role | Checksum |
| :--- | :--- | :--- | :--- |
| **Janus Classical X7** | Commit `b34e342` | Qualified 1T Strength Baseline | `86392A2F4BD4182A...` |
| **Janus Classical X12** | Commit `78ca3d5` | Qualified 4T SMP Strength Baseline | `00B4F5FEDEA02A39...` |
| **Janus Classical X22** | Commit `e33f292` | Correctness Reference Foundation | `35D095CFFE8A2EDA...` |
| **Janus Classical X25** | Milestone P1.20 | Dynamic Evaluation Reference (Option B) | `2C163B4AD5B976C8...` |
| **Stockfish 4** | 2014 Classical | Historical External Target (~3100 Elo) | `1128CAB833860633...` |
| **Stockfish 11** | 2020 Classical | Mature External Target (~3450 Elo) | `B004C03BD71BB84E...` |
| **Stockfish 19** | NNUE SOTA | Unrestricted Benchmark (~3650+ Elo) | `45BC8E4969147DB9...` |

---

## 4. Mandatory Experimental Governance for Milestone P1.21

1. **Strict Non-ML Charter:** Absolute prohibition of neural networks, NNUE, learned evaluation parameters, SPSA, Texel tuning, or automated offline optimization.
2. **Independent Feature Isolation:** Singular Extensions (SE) and ProbCut must be tested in strict isolation before any combined candidate is submitted to the qualification gate.
3. **Mandatory Multi-TC Non-Regression Protocol:** All candidates must be audited at both fast blitz ($1.0\text{s}+50\text{ms}$) and slow tournament time controls ($3.0\text{s}+100\text{ms}$) to guarantee search-tree stability.
4. **Adversarial Harness Certification:** The 15-case referee test suite must be passed with 100% resolution prior to any tournament game execution.
5. **Single Atomic Commit:** Milestone conclusion must occur on branch `phase1/classical-janus` via a single atomic commit with zero remote git push.
