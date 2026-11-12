# Phase 7: Competitive Testing Standard & Statistical Verification Framework

**Milestone:** Phase 1, Milestone P1.11  
**Charter:** Classical Search Architecture Decision, Counterfactual Pruning Verification & Competitive Strength Recovery  
**Lead Methodologist:** Principal Computer Chess Engineer & Statistical Experimentalist  
**Governing Standard:** FIDE & CCRL/SPRT-Inspired Competitive Chess Testing  

---

## 1. Executive Testing Philosophy

To prevent premature promotion, misattributed draws, zero-variance mathematical artifacts, and unsupported claims of "equivalence", Milestone P1.11 formalizes the **Janus Competitive Testing Standard (JCTS v1.11)**.

All strength qualification tournaments in Project Janus must adhere to the preregistered mathematical principles detailed below.

---

## 2. Experimental Design Principles

### 2.1 Opening-Paired Color Symmetry
- All matches must use balanced opening suites (e.g. `independent_openings_v056.json`) containing neutral 2-ply and 4-ply opening lines.
- Every opening line must be played exactly **twice**, with strict color inversion:
  - Game 1: Engine A as White, Engine B as Black.
  - Game 2: Engine B as White, Engine A as Black.
- This guarantees that opening bias is mathematically eliminated from the pair difference.

### 2.2 Pentanomial Outcome Formulation
Each opening pair yields an independent random variable $S_i \in \{0.0, 0.5, 1.0, 1.5, 2.0\}$ representing the points scored by Engine A across the pair:
- **Pair Outcome Categories ($ww, wd, dd/wl, ld, ll$):**
  1. $ww$ (Win-Win, $+2.0\text{ pts}$): $d_i = +1.0$ (Clean sweep win).
  2. $wd$ (Win-Draw, $+1.5\text{ pts}$): $d_i = +0.5$.
  3. $dd$ or $wl$ (Draw-Draw or Win-Loss, $+1.0\text{ pts}$): $d_i = 0.0$ (Neutral tie).
  4. $ld$ (Loss-Draw, $+0.5\text{ pts}$): $d_i = -0.5$.
  5. $ll$ (Loss-Loss, $0.0\text{ pts}$): $d_i = -1.0$ (Clean sweep loss).
- The paired difference is defined as:
  $$d_i = \frac{S_i - (2.0 - S_i)}{2} = S_i - 1.0 \in \{-1.0, -0.5, 0.0, +0.5, +1.0\}$$

---

## 3. Statistical Inference & Hypothesis Testing

### 3.1 Paired Student's $t$-Distribution Test
- Given $N$ opening pairs, let:
  $$\bar{d} = \frac{1}{N}\sum_{i=1}^N d_i, \quad s_d^2 = \frac{1}{N-1}\sum_{i=1}^N (d_i - \bar{d})^2, \quad SE = \sqrt{\frac{s_d^2}{N}}$$
- The test statistic is:
  $$t = \frac{\bar{d}}{SE}, \quad df = N - 1$$
- The exact two-tailed $p$-value is evaluated via incomplete beta functions.
- **Zero-Variance Invariant:** If all pairs yield identical non-zero differences ($s_d^2 = 0, \bar{d} \ne 0$, such as all losses against Stockfish), the exact binomial probability $p = 0.5^N$ is reported.

### 3.2 Formal Equivalence Testing: Two One-Sided Tests (TOST)
- **Mandate:** $p > 0.05$ on a difference test **does not prove equivalence**.
- When claiming that an engine is "equivalent" to a baseline, TOST must be applied with an equivalence bound $\Delta_{\text{eq}} = 0.10$ pair score ($\approx \pm 5\%$ score or $\pm 35$ Elo):
  $$t_1 = \frac{\bar{d} - (-\Delta_{\text{eq}})}{SE}, \quad t_2 = \frac{\bar{d} - \Delta_{\text{eq}}}{SE}$$
- Equivalence is statistically proven at $\alpha = 0.05$ **only if both** one-sided null hypotheses are rejected:
  $$p_{\text{TOST}} = \max(p_1, p_2) < 0.05$$

### 3.3 Elo Rating Delta & Wilson Score Confidence Intervals
- Score fraction: $p = \frac{\text{Points}}{2N}$.
- Elo difference (for $0 < p < 1$):
  $$\Delta\text{Elo} = -400 \log_{10}\left(\frac{1}{p} - 1\right)$$
- If $p = 0.0$ or $p = 1.0$, Elo is unbounded ($-\infty$ or $+\infty$); Wilson score confidence intervals are reported:
  $$\text{CI}_{95\%}(p) = \frac{p + \frac{z^2}{2N} \pm z\sqrt{\frac{p(1-p)}{N} + \frac{z^2}{4N^2}}}{1 + \frac{z^2}{N}}, \quad z = 1.95996$$

---

## 4. Technical Incident & Adjudication Protocol

1. **Clock Forfeits:** Engines running out of allocated base time + increment immediately forfeit the game ($0-1$).
2. **Crashes & Pipe Exceptions:** Subprocess non-zero exit code or broken pipe immediately forfeits ($0-1$) and flags a critical correctness incident.
3. **Illegal Moves:** FIDE move validation via `python-chess`. Illegal move attempt immediately forfeits.
4. **Draw Adjudication:**
   - 3-fold repetition: Automatically adjudicated as draw (`1/2-1/2`).
   - 50-move rule: Automatically adjudicated as draw.
   - Material insufficiency: Automatically adjudicated as draw.

