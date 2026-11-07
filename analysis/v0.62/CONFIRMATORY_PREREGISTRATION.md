# Confirmatory Experiment Preregistration

**Milestone:** Project Janus v0.62  
**Document Type:** Formal Scientific Match Preregistration Protocol  
**Author:** Principal Chess Engine Research Scientist & Independent Experimental Auditor  
**Date:** 2026-11-07  
**Match Identification:** `v062_confirmatory_v2_vs_c1`  
**Candidate Engine:** Janus Neural Value V2 (NNUE-V2-Small Hybrid 50/50, Native AVX2)  
**Control Baseline:** Janus Classical Baseline C1 (Native N5 Frozen)  

---

## 1. Scientific Objective & Hypothesis

The objective of this confirmatory experiment is to independently replicate the reported **+49.0 Elo** playing-strength improvement of Janus Neural Value V2 over the frozen Classical Baseline C1 under strict confirmatory protocols on a **completely new, unseen opening suite**.

### Hypothesis:
- **Null Hypothesis ($H_0$):** The true playing-strength delta of the candidate is non-positive ($\Delta\text{Elo} \le 0$).
- **Alternative Hypothesis ($H_1$):** The true playing-strength delta of the candidate is positive ($\Delta\text{Elo} > 0$).

---

## 2. Statistical Power & Precision Analysis

### Sample Size & Configuration:
- **Total Games:** 200 games.
- **Opening Structure:** 100 color-reversed opening pairs (each opening played twice, once as White and once as Black).
- **Degrees of Freedom:** $df = 99$ pairs.

### Standard Error & Detectable Effect Size:
Based on empirical draw rates in v0.58–v0.61 (40–45% draws):
- Pair score difference variance: $\sigma_D^2 \approx 1.15$ ($s_D \approx 1.07$).
- Standard error of the mean pair difference:
  $$\text{SE} = \frac{s_D}{\sqrt{N}} = \frac{1.07}{\sqrt{100}} \approx 0.107\text{ points/pair}$$
- In terms of win percentage: $\text{SE}_{\%} \approx 2.68\%$, corresponding to an Elo uncertainty of approximately $\pm 18.5$ Elo.
- **Minimum Detectable Effect (MDE) at 80% Power ($\alpha = 0.05$, two-tailed):**
  $$\text{MDE} = (z_{0.975} + z_{0.80}) \times \text{SE} = (1.96 + 0.84) \times 0.107 \approx 0.30\text{ points/pair} \approx +26.0\text{ Elo}$$
- **Statistical Power to Detect Claimed +49.0 Elo:**
  A true effect of +49.0 Elo corresponds to $\bar{D} = +0.280$ points per pair ($t \approx 2.61$). The power of a 200-game match to detect this effect is **$\ge 95\%$**.

---

## 3. Preregistered Statistical Decision Rules

### Primary Outcome Measure:
Mean paired score difference across the 100 opening pairs:
$$\bar{D} = \frac{1}{100} \sum_{k=1}^{100} \left(S_{\text{cand}}(k) - S_{\text{ctrl}}(k)\right) \in [-2.0, +2.0]$$

### Uncertainty & Hypothesis Testing:
1. **Primary Uncertainty Metric:** 10,000 paired bootstrap resamples generating the empirical 95% confidence interval of $\bar{D}$ and $\Delta\text{Elo}$.
2. **Confirmatory Hypothesis Test:** Paired Student-t test ($df = 99$, two-tailed).
3. **Preregistered Replication Standard:**
   - **Replicated (Positive):** $\Delta\text{Elo} > 0$, Student-t $p < 0.05$, and lower bound of 95% bootstrap Elo CI $> 0$.
   - **Inconclusive:** $p \ge 0.05$ or 95% CI spans 0.0.
   - **Refuted:** $\Delta\text{Elo} < 0$ with $p < 0.05$.

---

## 4. Opening Suite Independence Guarantee

To guarantee strict confirmatory independence from the v0.61 tournament:
- **Opening Corpus:** `analysis/v0.62/corpus/independent_openings_v062.json`
- **Corpus Size:** Exactly 100 openings covering ECO codes A00–E99.
- **Independence Audit:** **0% overlap** with `independent_openings_v056.json` (zero shared opening terminal positions).
- **Legality Verification:** All 100 move sequences were parsed and validated via python-chess.

---

## 5. Frozen Engine Configurations & Executable Hashes

Both competitors are frozen and locked with recorded SHA-256 hashes:

### Candidate: Janus Neural Value V2 (Hybrid 50/50)
- **Binary:** `analysis/v0.61/native/janus_native_engine.exe`
- **SHA-256:** `fc82936845a758df6e25dc74ec069c9bcf04724a350122e23b88939c39bc077b`
- **Model File:** `analysis/v0.61/models/janus_nnue_v2_small.jnnue`
- **Model SHA-256:** `ff7ac9a0d45d1426615b13cf17d23f38d3886f4df344f6f4370db0420eb24f2b`
- **UCI Parameters:**
  - `NeuralValueModelPath`: `analysis/v0.61/models/janus_nnue_v2_small.jnnue`
  - `UseNeuralValue`: `true`
  - `NeuralValueBlend`: `50`
  - `NeuralValueUseAVX2`: `true`
  - `UseKillerOrdering`: `true`
  - `UseHistoryOrdering`: `true`
  - `UseLMR`: `true`
  - `UsePVS`: `false`
  - `UseSEEOrdering`: `false`
  - `UseSEEInQuiescence`: `false`

### Control: Janus Classical Baseline C1
- **Binary:** `analysis/v0.56/native/janus_native_engine.exe`
- **SHA-256:** `a4f9d9d18b549d29b2e6740ac90d90d39167d92d3846b95fc0c4f5b966add83f`
- **UCI Parameters:**
  - `UseKillerOrdering`: `true`
  - `UseHistoryOrdering`: `true`
  - `UseLMR`: `true`
  - `UsePVS`: `false`
  - `UseSEEOrdering`: `false`
  - `UseSEEInQuiescence`: `false`

---

## 6. Match Protocol & Tournament Governance

1. **Time Control:** Fischer 3.0 seconds base + 100 milliseconds increment per move.
2. **Concurrency:** 8 worker processes executed via Python `ProcessPoolExecutor`.
3. **Adjudication Standards:**
   - Checkmate (Article 1.2)
   - Stalemate (Article 5.2.1)
   - Threefold repetition (Article 9.2)
   - 50-move rule (Article 9.3)
   - Insufficient material (Article 9.6)
   - 300-ply emergency safety limit
4. **Invalidation Policy:** Any unhandled crash, pipe disconnect, or illegal move immediately fails the tournament.
5. **Output Artifacts:** Full PGN stream (`analysis/v0.62/pgn/v062_confirmatory_match.pgn`) and raw game telemetry JSON (`analysis/v0.62/raw/v062_confirmatory_match_raw.json`).
