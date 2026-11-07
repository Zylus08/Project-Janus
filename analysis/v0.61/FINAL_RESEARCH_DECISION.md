# Project Janus v0.61 — Final Research & Scientific Release Decision

**Document Classification:** Formal Scientific Review, Release Qualification & Architecture Roadmap  
**Milestone:** Project Janus v0.61 — Neural Value Scaling, Native Optimization & Conditional Strength Qualification  
**Author:** Principal Chess Engine Research Scientist, NNUE Architect, C++17/AVX2 Optimization Engineer, ML Training Engineer, and Independent Experimental Auditor  
**Date:** 2026-11-07  
**Repository Branch:** `v0.3-benchmark-harness`  
**Parent Commit:** `08db0c0`  
**Control Baseline:** Janus Classical Baseline C1 (Native N5 Frozen)  
**Qualified Candidate:** Janus Neural Value V2 (NNUE-V2-Small Hybrid 50/50, Native AVX2)  

---

## 1. Formal Milestone Release Classification

| Release Category | Designation | Mathematical & Empirical Criteria | v0.61 Empirical Outcome | Status |
| :---: | :--- | :--- | :--- | :---: |
| **Category A** | **Production Strength Promotion** | $\Delta\text{Elo} > +15.0$ with $p < 0.05$, 95% Bootstrap CI lower bound $> 0$, and zero regressions on baseline suite. | **$\Delta\text{Elo} = \mathbf{+49.0\text{ Elo}}$ ($p = 0.0105$), 95% CI: $[+12.2, +85.0]$, 658/658 tests passed (100%).** | **ACHIEVED & SELECTED** |
| **Category B** | Research Prototype Qualified | $-15.0 \le \Delta\text{Elo} \le +15.0$ or $p \ge 0.05$ with robust correctness. | Surpassed by $+49.0\text{ Elo}$ significant gain. | Not Selected |
| **Category C** | Rework Required | $\Delta\text{Elo} < -15.0$ with $p < 0.05$; significant regression. | No regression observed. | Not Selected |
| **Category D** | Rejection | Engine instability, illegal moves, or system crashes. | Zero crashes, zero forfeits across 200 games. | Not Selected |

### Formal Verdict:
**CATEGORY A — PRODUCTION STRENGTH PROMOTION CANDIDATE QUALIFIED.**  
Janus Neural Value V2 (Hybrid 50/50) is formally qualified as Project Janus's first empirically verified, statistically significant neural playing-strength improvement over Classical Baseline C1 (+49.0 Elo, $p = 0.0105$).

---

## 2. Answers to the 10 Governing Scientific Review Questions

### Question 1: Did scaled training data improve teacher-score prediction over v0.60?
**Yes, decisively.**  
Scaling the training dataset from 16,000 to 80,000 master positions (labeled by Stockfish 19 at 10,000 nodes) reduced test MAE from 200.28 cp (NNUE-V1-Small) to **162.46 cp** (NNUE-V2-Small), representing a **$-37.81\text{ cp}$ error reduction** ($p < 10^{-15}$). Furthermore, NNUE-V2 broke past the Classical Baseline C1 error floor (178.63 cp), achieving $+7.5\%$ higher sign agreement (77.0% vs 69.5%) and $-46.7\%$ lower opening error.

### Question 2: Did larger model capacity ($M=128$) improve playing strength over $M=64$?
**No.**  
Evaluating the capacity scaling hypothesis between NNUE-V2-Small ($M=64$, 51K params) and NNUE-V2-Compact ($M=128$, 106K params) revealed that test MAE differed by only $-0.29$ cp (162.46 vs 162.15 cp, $p = 0.78$), which is statistically indistinguishable from zero. However, $M=128$ doubled the memory footprint and reduced evaluation throughput by **2.30x** (3.38M/s vs 7.79M/s). Because alpha-beta search is highly latency-sensitive, $M=64$ proved to be the superior operational architecture.

### Question 3: Did native AVX2 SIMD yield measurable speedups in leaf evaluation latency and search NPS?
**Yes, exceptionally.**  
The AVX2 SIMD vectorized kernel (`_mm256_maddubs_epi16`, aligned accumulator additions, and vector dot products) reduced end-to-end leaf evaluation latency from 624.81 ns to **128.36 ns** (**4.87x speedup**, isolated throughput of **7,790,690 evals/s**). In tree search, AVX2 enabled NNUE-V2 to search at **1,404,311 NPS** (151.7% of C1's NPS at depth 5), completely eliminating the evaluation latency bottleneck that paralyzed earlier prototypes.

### Question 4: How did alpha-beta search interact with neural value evaluation (node reduction, tree shape, cutoffs)?
**Neural evaluation produced sharper bounds and massive search tree contraction.**  
Pure NNUE-V2 cut total search nodes by **$-55.89\%$** at depth 4 and **$-32.65\%$** at depth 5 across diverse benchmark positions. Because neural static evaluation produces smooth, continuous king-relative gradients rather than coarse material step functions, beta-cutoffs occurred significantly earlier in the move list, allowing LMR and null-window searches to prune unpromising branches aggressively.

### Question 5: Did neural evaluation alone improve strength or was hybrid blending required?
**Hybrid blending (50% Neural + 50% Classical) was essential for peak competitive strength.**  
Calibration revealed that while Pure NNUE-V2 achieved the greatest node reduction, its move agreement with Stockfish was only 10% due to tactical horizon vulnerability in sharp tactics. Blending 50% NNUE-V2 with 50% Classical C1 combined neural positional insight with classical material discipline, boosting move agreement with Stockfish to 40.0% and delivering the **+49.0 Elo** tournament victory.

### Question 6: What is the empirical Elo difference and paired statistical significance vs Classical C1?
In the preregistered 200-game match under Fischer 3.0s+0.1s time controls:
- **Score:** 114.0 / 200 (71 wins, 86 draws, 43 losses, **57.00%**)
- **Empirical Elo Delta:** **+49.0 Elo**
- **10,000-Resample Bootstrap 95% Elo CI:** **$[+12.2, +85.0]$ Elo** (strictly excludes 0)
- **Mean Paired Difference per Opening Pair:** **+0.280** (95% CI: $[+0.070, +0.480]$)
- **Paired Student-t:** $t = +2.6075, p = 0.01053$ ($df = 99$, $p < 0.05$)
- **Verdict:** Statistically significant improvement.

### Question 7: Were any regressions observed in baseline C1 behavior when neural evaluation is disabled?
**Zero regressions.**  
When `UseNeuralValue=false`, all native move outputs, node counts, depth iterations, and score telemetry are 100% bit-exact identical to Classical Baseline C1. Full repository regression suite passed 100% (**658/658 tests passed** in 94.87s).

### Question 8: Did the candidate pass all preregistered qualification gates?
**Yes, all six Candidate Qualification Gates passed:**
1. Generalization Superiority: PASS ($p < 10^{-10}$)
2. Quantization Fidelity: PASS ($r = 0.9989$, CRC32 bit-exact)
3. Native AVX2 Throughput: PASS (128.36 ns, 7.79M evals/s)
4. System Correctness & Invariance: PASS (658/658 tests passed)
5. Search Efficiency: PASS ($-32.7\%$ nodes at d5, $151.7\%$ NPS)
6. Tactical Sanity & Mating: PASS (Mating scores intact $\ge 28,000$, 40% SF19 agreement)

### Question 9: What are the key architectural recommendations for subsequent neural research (e.g. v0.62)?
1. **Dynamic / Phase-Dependent Hybrid Blending:**  
   Currently, blend is static (50/50). An opening/endgame tapered blend (e.g. 70% neural in opening/middlegame, 80% classical in endgame pawn races) could further enhance tactical precision.
2. **King-Bucketed Feature Transformer ($4 \times 768 \to M$):**  
   Now that AVX2 SIMD throughput is established, sub-bucketing input features by king placement can provide localized piece-king interaction without inflating leaf feedforward latency.
3. **PVS & SEE Integration with Neural Values:**  
   Re-evaluating Principal Variation Search (PVS) and Static Exchange Evaluation (SEE) move ordering now that leaf evaluation provides reliable positional bounds.

### Question 10: What is the formal release classification?
**Category A — Production Strength Promotion.**

---

## 3. Configuration & Governance Directives

To maintain complete backward compatibility and preserve Baseline C1 guarantees:
1. **Default Engine State:**  
   `UseNeuralValue=false` is preserved as the native C1 default state.
2. **Qualified Neural Candidate State:**  
   UCI command:
   ```text
   setoption name NeuralValueModelPath value analysis/v0.61/models/janus_nnue_v2_small.jnnue
   setoption name NeuralValueBlend value 50
   setoption name NeuralValueUseAVX2 value true
   setoption name UseNeuralValue value true
   ```
3. **Zero Git Remote Pushes:**  
   All milestones remain local to the local repository `E:\ChessXML\project-janus`.
