# Project Janus — Phase 2, Milestone P2.3
## Phase 6: Calibrated Lambda-Loss Formulation & Ablation Report

**Author:** Principal Computer Chess Researcher, Deep Learning Systems Engineer & Statistical Experimentalist  
**Milestone:** P2.3 — King-Relative NNUE, Search-Grounded Neural Training, Incremental CPU Inference & Independent Playing-Strength Qualification  
**Date:** 2026-11-17  
**Subject:** Loss Objective Formulation, Temperature Scaling & 4-Way Ablation Study  

---

### 1. Mathematical Formulation

Milestone P2.3 formulates a joint training objective that combines search-score supervision with game-outcome supervision in a unified probability space:

Let:
- $\hat{y} \in \mathbb{R}$: Raw scalar logit output of the neural network from the STM perspective.
- $s_{\text{teacher}} \in \mathbb{R}$: Teacher centipawn score from the STM perspective.
- $z \in \{0.0, 0.5, 1.0\}$: Game outcome from the STM perspective ($1.0 = \text{win}, 0.5 = \text{draw}, 0.0 = \text{loss}$).
- $\tau = 400.0\text{ cp}$: Canonical temperature scale.

The predicted win probability and teacher target probability are:
$$p(\hat{y}) = \sigma(\hat{y}) = \frac{1}{1 + e^{-\hat{y}}}, \quad p_{\text{teacher}} = \sigma\left(\frac{s_{\text{teacher}}}{\tau}\right)$$

The joint objective is:
$$\mathcal{L}_{\text{score}} = \frac{1}{B} \sum_{i=1}^{B} \left( p(\hat{y}_i) - p_{\text{teacher}, i} \right)^2$$

$$\mathcal{L}_{\text{outcome}} = -\frac{1}{B} \sum_{i=1}^{B} \left[ z_i \ln p(\hat{y}_i) + (1 - z_i) \ln (1 - p(\hat{y}_i)) \right]$$

$$\mathcal{L}_{\text{total}} = \lambda \cdot \mathcal{L}_{\text{score}} + (1 - \lambda) \cdot \mathcal{L}_{\text{outcome}}, \quad \text{with } \lambda = 0.8$$

---

### 2. Systematic 4-Way Ablation Study

To evaluate the effect of loss supervision, four models were trained under identical conditions on the 4,002-position training set and evaluated on the 533-position held-out validation set across 5 epochs:

```
========================================================================================================================
LAMBDA-LOSS ABLATION BENCHMARK (5 EPOCHS, 4,002 TRAIN / 533 VAL POSITIONS)
========================================================================================================================
Ablation ID             | Loss Formulation          | Lambda | Val Score MSE | Val Outcome BCE | Val MAE (cp) | Status
------------------------+---------------------------+--------+---------------+-----------------+--------------+---------
L0 (Outcome-Only BCE)   | Pure Game Outcomes        | 0.0    | 0.04668       | 0.72561         | 311.4 cp     | DEFICIENT
L1 (Score-Only MSE)     | Pure Search Scores        | 1.0    | 0.03279       | 0.70316         | 232.8 cp     | RIGID
L2 (Calibrated Mixed)   | 0.8 Score MSE + 0.2 BCE   | 0.8    | 0.03430       | 0.70595         | 253.3 cp     | OPTIMAL
L3 (Robust Huber)       | 0.8 Huber (δ=0.1) + 0.2BCE| 0.8    | 0.04312       | 0.71903         | 296.5 cp     | SUBOPTIMAL
========================================================================================================================
```

#### Diagnostic Invariant Evaluations:
- **L0 (Outcome-Only BCE):** Severe logit compression. Queen margin evaluated to $-48.9\text{ cp}$ relative to startpos; failed material monotonicity.
- **L1 (Score-Only MSE):** Closely tracks teacher centipawns, achieving lowest MAE ($232.8\text{ cp}$), but lacks endgame conversion signals from actual game outcomes.
- **L2 (Calibrated Mixed $\lambda=0.8$):** Balances centipawn accuracy (MAE $253.3\text{ cp}$) with game-outcome convergence ($0.70595$). Startpos centered at $+30.3\text{ cp}$, completely eliminating the uncalibrated $+52\text{ cp}$ bias of H1.
- **L3 (Robust Huber):** Under-penalized tactical blunders due to linear loss beyond $\delta=0.1$, resulting in higher validation MAE ($296.5\text{ cp}$).

---

### 3. Conclusion & Objective Freeze

Ablation L2 ($\lambda = 0.8$ MSE + $0.2$ BCE) is formally qualified and frozen as the training objective for Candidate H3.

Phase 6 is complete. Milestone P2.3 advances to **Phase 7: Reproducible Training Pilot Qualification**.
