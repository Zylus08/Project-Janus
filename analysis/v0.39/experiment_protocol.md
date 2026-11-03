# Project Janus v0.39 — Strength Validation Experiment Protocol

## 1. Objective and Pre-Registration

This protocol defines the formal, pre-registered testing methodology to evaluate the playing strength of Project Janus v0.39 candidate enhancements against the calibrated external opponent anchor (Stockfish 19 at Elo 1320).

The experimental objective is to determine whether fixing the quiescence search check-evasion fail-low bug (Candidate Q0), calibrating middlegame and uncastled king-safety evaluation terms (Candidate K0), and combining them (Candidate Q0+K0) produces measurable strength gains or preserves the benchmark anchor score while eliminating catastrophic horizon blunders.

---

## 2. Experimental Design & Parameters

### 2.1 Opponent Specification
- **Engine Binary:** Stockfish 19 (`E:\ChessXML\tools\stockfish\stockfish.exe`)
- **Binary Hash (SHA-256):** `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`
- **Configuration Options:**
  - `Threads`: 1
  - `Hash`: 64 MB
  - `UCI_LimitStrength`: `true`
  - `UCI_Elo`: 1320

### 2.2 Janus Candidate Specification
- **Candidate Q0+K0:**
  - Python Environment: `3.13.2`
  - Engine Entry Point: `python -m janus.uci`
  - Evaluation: `--eval-all` (Tapered evaluation with calibrated uncastled and central open-file king safety K0)
  - Search: Corrected quiescence check evasion fail-low handling, fail-soft bounds, threefold repetition detection, hard ply cap, ordered root-move fallback (Q0)
  - Time Control Policy: `--time-policy arm_c` (Adaptive Fischer increment time allocation)

### 2.3 Match Structure & Time Control
- **Total Games:** 50 games (25 complete colour-reversed opening pairs).
- **Time Control:** 3,000 ms initial clock + 100 ms Fischer increment per move.
- **Opening Suite:** `benchmarks/openings.json` (SHA-256: `90b4bf10ca1c4b7bca06c9a9307779d71c4805e3230a10d0f2f5bf6230f6a192`).
- **Opening Selection:** Deterministic shuffle with seed `42`.
- **Pair Balancing:** In Game 1 of Pair $i$, Janus plays White; in Game 2 of Pair $i$, Janus plays Black with the identical opening position.
- **Move Limit:** 200 plies (100 full moves).
- **Adjudication:** Strict Python-chess rules (threefold repetition, 50-move rule, checkmate, stalemate, insufficient material).

---

## 3. Statistical Methodology

1. **Paired Unit of Analysis:**
   For each opening pair $i \in \{1, \dots, 25\}$, the paired score is:
   $$D_i = S_{i, \text{White}} + S_{i, \text{Black}} \in \{0.0, 0.5, 1.0, 1.5, 2.0\}$$
   where $S \in \{1.0 \text{ (win)}, 0.5 \text{ (draw)}, 0.0 \text{ (loss)}\}$.

2. **Null Hypothesis ($H_0$):**
   $$\mu_D = 1.0 \quad (\text{or } \mu_D \le 1.12 \text{ vs v0.38 baseline } 56.0\%)$$
   Candidate does not outperform equal score (or baseline score).

3. **Paired Student's t-test:**
   $$t = \frac{\bar{D} - 1.0}{s_D / \sqrt{n}}, \quad \text{dof} = 24$$

4. **10,000-Sample Paired Bootstrap Confidence Interval:**
   Resampling 25 opening pairs with replacement 10,000 times to construct an exact, non-parametric percentile 95% confidence interval $[CI_{2.5\%}, CI_{97.5\%}]$.

5. **Elo Rating Difference:**
   $$R_{\text{diff}} = -400 \log_{10}\left(\frac{1}{S} - 1\right)$$
   For $S = 28/50 = 56.0\%$, $R_{\text{diff}} = +41.9$ Elo.

---

## 4. Success Criteria

1. **Validity:** Exactly 50 valid games across 25 complete pairs with zero unhandled engine crashes or time forfeit disqualifications.
2. **Playing Strength:** Overall score $\ge 56.0\%$ against Stockfish 19 Elo 1320 anchor.
3. **Horizon Safety:** Elimination of zero-depth mate blunders observed in v0.38 (e.g. `f4c7` mate-in-1 blunder).

