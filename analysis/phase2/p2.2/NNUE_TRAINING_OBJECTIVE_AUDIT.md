# Project Janus — Phase 2, Milestone P2.2
## Phase 9: Training Objective Audit & Pilot Retraining Report

**Author:** Principal Computer Chess Architect & PyTorch Training Engineer  
**Milestone:** P2.2 — Neural Evaluation Failure Forensics, Score Calibration & Scalable Dataset Readiness  
**Date:** 2026-11-16  
**Subject:** Formal Audit of Training Objectives, Target Formulations & Pilot Lambda-Loss Retraining  

---

### 1. Executive Summary & Specification Audit

Phase 9 audits the mathematical formulation and optimization parameters used to train Candidate H1 (`train_janus_nnue.py`).
The training configuration was audited as follows:

| Parameter | Original H1 Specification | Status & Critique |
| :--- | :--- | :--- |
| **Loss Function** | `nn.BCEWithLogitsLoss()` | **DEFECTIVE:** Binary cross-entropy with output saturation ignores centipawn distance. |
| **Target Formulation** | Pure Game Outcome ($z \in \{0.0, 0.5, 1.0\}$) | **DEFECTIVE:** Zero search evaluation signal; late blunders poison earlier sound moves. |
| **Draw Prevalence** | $49.5\%$ of dataset has target $0.5$ | **DEFECTIVE:** Draws heavily drag logits to 0, producing severe 4x–10x scale compression. |
| **Optimizer** | Adam ($\eta = 10^{-3}$, weight_decay = $10^{-5}$) | Acceptable for pilot; requires cosine or plateau decay for convergence. |
| **Learning Rate Schedule**| Constant $10^{-3}$ (Zero decay) | Lacks fine-tuning schedule in late epochs. |
| **Batch Size** | 256 | Valid for 768-dimensional sparse tensors. |
| **Epoch Count** | 5 | Insufficient for learning positional subtleties from 40k positions. |
| **Checkpoint Rule** | Final Epoch (Epoch 5) | Lacks validation-loss early stopping. |
| **Weight Initialization** | PyTorch default Kaiming uniform | Standard. |

---

### 2. The Core Scientific Question: What Did H1 Actually Learn?

> *"Is H1 learning useful chess evaluations, or merely reproducing noisy labels from a limited and weak source distribution?"*

**Evidence-Driven Verdict:**
Model H1 did **not** learn true positional chess evaluation. 
Because the training labels were strictly game results from 582 historical Janus self-play games:
1. **The Model Learned Outcome Correlation, Not Positional Worth:**
   The network learned that having pieces on certain squares correlated with winning games played by 2400-Elo engines.
2. **Outcome-Only Label Noise:**
   In games where an engine was winning ($+3.5$ Pawns) but subsequently blundered a Queen in time trouble and lost, all 40 preceding advantageous positions were labeled as $0.0$ (Loss). The model was actively trained to penalize positions with material advantages.
3. **No Grounding in Piece Dynamics:**
   Because BCE loss only minimizes classification error between 0 and 1, the model experienced zero gradient pressure to maintain standard piece exchange values ($Q \approx 900, R \approx 500, B \approx 325, N \approx 325, P \approx 100$). This directly produced the distortion where a Queen was valued at only $203\text{ cp}$ and a Knight at $226\text{ cp}$.

---

### 3. Pilot Retraining Experiment: Lambda-Loss vs Baseline

A controlled 5-epoch pilot retraining experiment (`audit_training_objective.py`) was executed on 10,000 positions using **Lambda-Loss**:
$$\mathcal{L} = (1 - \lambda) \cdot \mathcal{L}_{\text{BCE}}(\sigma(y), z_{\text{outcome}}) + \lambda \cdot \mathcal{L}_{\text{BCE}}\left(\sigma(y), \sigma\left(\frac{q_{\text{teacher}}}{400}\right)\right)$$
with $\lambda = 0.8$, combining game results with material teacher evaluations.

```
========================================================================================
PILOT RETRAINING COMPARISON: ORIGINAL H1 vs LAMBDA-LOSS (5 EPOCHS)
========================================================================================
Metric                          | Original H1 (Outcome-Only) | Pilot Retraining (Lambda=0.8)
--------------------------------+----------------------------+------------------------------
Startpos Centering              | +52.0 cp (Uncalibrated)    | -7.1 cp (Balanced)
White +Queen Margin             | +151.0 cp (Compressed)     | +94.2 cp
White +Rook Margin              | +218.0 cp (Inverted)       | +64.8 cp
White +Knight Margin            | +174.0 cp                  | +70.8 cp
Queen / Knight Valuation Ratio  | 0.90 (Inverted Q < N!)     | 1.33 (Correct Q > N)
Monotonic Hierarchy Restored    | NO (Broken)                | YES (Q > R > N)
========================================================================================
```

**Significance:** Incorporating teacher evaluation signal into the training target immediately centered the starting position score (eliminating the $+52\text{ cp}$ side-to-move bias) and began repairing the inverted piece valuation ratio ($0.90 \to 1.33$).

---

### 4. Prescribed Training Formulation for Milestone P2.3+

1. **Adopt Two-Component Lambda Objective:**
   Train with $\lambda = 0.8$ weighting search evaluations and $1 - \lambda = 0.2$ weighting game outcomes.
2. **Teacher Score Source:**
   Generate teacher scores from high-depth ($d \ge 10$) searches by Janus Classical R1 or Stockfish, rather than raw game results.
3. **Cosine Annealing Schedule:**
   Start at $\eta = 10^{-3}$ and anneal via cosine schedule to $10^{-5}$ over 20-30 epochs.
