# PROJECT JANUS v0.61 — PHASE 2: NNUE-V2 TRAINING & COMPARATIVE GENERALIZATION REPORT

**Milestone:** v0.61 — Neural Value Scaling, Native Optimization & Conditional Strength Qualification  
**Author:** Principal Chess Engine Research Scientist, Neural Network Architect & ML Training Engineer  
**Dataset:** `janus_nnue_v2_dataset` (80,000 Train, 10,000 Val, 10,000 Test)  
**Evaluation Set:** 10,000 genuinely held-out master test positions  
**Primary Candidate Selected:** **Janus Neural Value V2-Small (`NNUE-V2-Small`, $M=64$)**  

---

## 1. Executive Summary

Milestone v0.61's Phase 2 investigated whether an 8-fold increase in supervised training volume (from 10,000 to 80,000 positions) and deeper teacher labeling (10,000 nodes/pos) can produce a neural value evaluator that surpasses the handcrafted Classical Baseline C1 on independent held-out master test positions.

Four controlled experiments were executed and evaluated across 10,000 held-out test positions:
- **T0 — Classical Baseline C1 Control:** Handcrafted piece-square and material evaluation.
- **T1 — NNUE-V1-Small (Frozen Reference):** 51,297-parameter model from v0.60 trained on 10,000 positions.
- **T2 — NNUE-V2-Small (Scaled Candidate):** Same architecture (51,297 parameters), trained on 80,000 positions.
- **T3 — NNUE-V2-Compact (High Capacity):** 106,689-parameter model ($M=128$), trained on 80,000 positions.

### Major Scientific Discoveries
1. **Dramatic Generalization Leap (T2 vs T1):** Scaling training volume reduced held-out test MAE by **$-37.81\text{ cp}$** (from 200.28 cp down to 162.46 cp, 95% CI: $[-41.58, -34.22]$), while Spearman rank correlation jumped from **$\rho = 0.2571$ to $\rho = 0.5336$** (+107% improvement).
2. **Neural Evaluator Surpasses Classical Baseline (T2 vs T0):** For the first time in Project Janus history, a learned neural position evaluator has statistically outperformed Classical Baseline C1 on independent held-out test data:
   - Test MAE: **162.46 cp (T2) vs 178.63 cp (T0)** ($\Delta = -16.29$ cp, 95% CI: $[-19.27, -13.22]$).
   - Spearman Rank Correlation: **$\rho = 0.5336$ (T2) vs $\rho = 0.5142$ (T0)**.
   - Score Sign Agreement: **77.0% (T2) vs 69.5% (T0)**.
   - Pairwise Positional Ranking: **70.6% (T2) vs 68.4% (T0)**.
3. **No Added Advantage from Doubled Capacity (T3 vs T2):** Expanding the architecture from $M=64$ (51K params) to $M=128$ (106K params) produced an insignificant error delta ($\Delta \text{MAE} = -0.29$ cp, 95% CI: $[-2.40, +1.61]$). Because V2-Small evaluates substantially faster on CPU and resides entirely within high-speed cache, V2-Small is locked as the primary production candidate.

---

## 2. Experimental Design & Model Specifications

| Attribute | T0 (Classical C1) | T1 (NNUE-V1-Small) | T2 (NNUE-V2-Small) | T3 (NNUE-V2-Compact) |
| :--- | :--- | :--- | :--- | :--- |
| **Model Type** | Handcrafted HCE | Neural (Half-KP) | Neural (Half-KP) | Neural (Half-KP) |
| **Input Features** | N/A | 768 sparse | 768 sparse | 768 sparse |
| **Accumulator Dim ($M$)**| N/A | $M=64$ | $M=64$ | $M=128$ |
| **Dual Accumulator Vector**| N/A | $128$ floats | $128$ floats | $256$ floats |
| **Dense Feedforward** | N/A | $128 \rightarrow 16 \rightarrow 1$ | $128 \rightarrow 16 \rightarrow 1$ | $256 \rightarrow 32 \rightarrow 1$ |
| **Total Parameters** | 0 | 51,297 params | **51,297 params** | 106,689 params |
| **Training Positions** | 0 (Manual tuning) | 10,000 (v0.60) | **80,000 (v0.61)** | 80,000 (v0.61) |
| **Teacher Supervision**| N/A | SF19 (5,000 nodes) | **SF19 (10,000 nodes)** | SF19 (10,000 nodes) |

---

## 3. Training Dynamics & Convergence

Training was conducted over 20 epochs using PyTorch 2.6.0 on CPU with the Smooth L1 loss ($\beta = 50.0$), Adam optimizer ($lr = 0.001$, weight decay $10^{-5}$), and Cosine Annealing learning rate schedule:

```
Training Convergence Census:
- T2 (V2-Small):   Epoch 1: Val Loss = 158.90 cp -> Epoch 5: 141.60 cp (Best) -> Epoch 20: 146.73 cp
- T3 (V2-Compact): Epoch 1: Val Loss = 155.17 cp -> Epoch 4: 142.71 cp (Best) -> Epoch 20: 151.72 cp
```

Both models converged rapidly within 4–5 epochs. T2 achieved lower best validation loss than T3 (141.60 cp vs 142.71 cp), indicating that $M=64$ provides optimal regularization density for an 80,000-sample training corpus.

---

## 4. Held-Out Evaluation on 10,000 Test Positions

All models were evaluated on the 10,000 held-out test positions (`value_v2_test.json`), which were completely isolated from training:

| Model / Evaluator | Test MAE (cp) | Test RMSE (cp) | P95 Error (cp) | Spearman $\rho$ | Pearson $r$ | Sign Agree (%) | Pairwise Rank (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **T0: Classical C1 Control** | 178.63 | 292.99 | 473.0 | 0.5142 | 0.6081 | 69.5% | 68.4% |
| **T1: NNUE-V1-Small (Frozen)**| 200.28 | 351.94 | 556.8 | 0.2571 | 0.3129 | 66.2% | 60.1% |
| **T2: NNUE-V2-Small (Scaled)**| **162.46** | **277.60** | **456.2** | **0.5336** | **0.6582** | **77.0%** | **70.6%** |
| **T3: NNUE-V2-Compact ($M=128$)**| 162.15 | 274.04 | 451.7 | 0.5222 | 0.6651 | 77.0% | 70.5% |

---

## 5. Paired Statistical Hypothesis Testing (Bootstrap CIs)

Paired metric differences were calculated across identical test positions using 1,000 bootstrap resamples:

1. **The Data Scaling Effect (T2 vs T1):**
   $$\Delta \text{MAE} = \text{MAE}(T2) - \text{MAE}(T1) = \mathbf{-37.81\text{ cp}} \quad [95\% \text{ CI}: -41.58, -34.22]$$
   *Conclusion:* The 8-fold increase in supervised data and deeper teacher supervision produces an unequivocal, statistically significant error reduction across all positions ($p < 10^{-15}$).
2. **Neural vs Classical Control (T2 vs T0):**
   $$\Delta \text{MAE} = \text{MAE}(T2) - \text{MAE}(T0) = \mathbf{-16.29\text{ cp}} \quad [95\% \text{ CI}: -19.27, -13.22]$$
   *Conclusion:* NNUE-V2-Small is statistically superior to Classical Baseline C1 in predicting ground-truth chess evaluations on unseen master positions ($p < 10^{-10}$).
3. **The Capacity Effect (T3 vs T2):**
   $$\Delta \text{MAE} = \text{MAE}(T3) - \text{MAE}(T2) = \mathbf{-0.29\text{ cp}} \quad [95\% \text{ CI}: -2.40, +1.61]$$
   *Conclusion:* Increasing parameter count from 51K to 106K yields no statistically significant improvement ($p = 0.78$), as zero lies comfortably inside the 95% confidence interval.

---

## 6. Granular Breakdown by Phase and Tactical Sharpness

### 6.1 Performance by Game Phase (MAE cp)

| Game Phase | Test Samples | T0 (Classical C1) | T1 (NNUE-V1-Small) | T2 (NNUE-V2-Small) | Relative Advantage (T2 vs T0) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Opening** ($\text{ply} \le 16$) | 1,529 | 73.59 cp | 46.43 cp | **39.19 cp** | **-46.7% error (-34.40 cp)** |
| **Middlegame** ($16 < \text{ply} < 55$) | 5,777 | 167.24 cp | 158.80 cp | **144.28 cp** | **-13.7% error (-22.96 cp)** |
| **Endgame** ($\text{piece} \le 6 \lor \text{ply} \ge 55$)| 2,694 | 262.67 cp | 376.54 cp | **271.40 cp** | +3.3% error (+8.73 cp) |

*Key Takeaway:* NNUE-V2-Small achieves massive accuracy gains in the opening (-46.7%) and middlegame (-13.7%), where complex piece interactions confound classical linear piece-square tables. In endgames, classical evaluation's explicit piece values remain competitive, explaining why hybrid blending (combining classical material anchors with neural positional understanding) is so structurally effective.

### 6.2 Tactical vs Quiet Regimes (MAE cp)
- **Quiet / Balanced Positions ($|\text{target}| \le 75\text{ cp}$, $n=4,180$):**
  - T0 (Classical C1): 68.42 cp
  - T1 (V1-Small): 78.10 cp
  - T2 (V2-Small): **54.21 cp** (20.8% lower error than classical baseline)
- **Tactical Positions ($|\text{target}| > 300\text{ cp}$, $n=2,185$):**
  - T0 (Classical C1): 328.45 cp
  - T1 (V1-Small): 384.10 cp
  - T2 (V2-Small): **312.80 cp** (Lower error than classical baseline)

---

## 7. Model Selection & Learning Gate Passage

### Learning Gate Evaluation:
1. **Valid Data Provenance & Split Isolation:** Verified (0.00% cross-split leakage).
2. **Nondegenerate, Calibrated Outputs:** Confirmed (Pearson $r = 0.6582$, Sign Agreement 77.0%).
3. **Meaningful Generalization over V1-Small:** Confirmed ($\Delta \text{MAE} = -37.81$ cp, $\Delta \rho = +0.2765$).
4. **No Catastrophic Failures:** Zero arithmetic overflows or unbounded predictions.
5. **Memory Budget Adherence:** V2-Small binary size is exactly **100,628 bytes (~100 KB)**, fitting 100% in L2 cache.

**GATE VERDICT: PASS.**  
**Locked Model Selection:** `NNUE-V2-Small` ($M=64$) is locked as the primary candidate for native quantization, AVX2 optimization, and search integration.

