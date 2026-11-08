# Project Janus v0.63 — Targeted Diagnostic Intervention: Phase-Tapered Adaptive Blending

**Document ID:** `analysis/v0.63/TARGETED_INTERVENTION.md`  
**Milestone:** v0.63 — Opening-Regime Generalization, Neural Evaluation Failure Analysis & Research Direction Qualification  
**Date:** 2026-11-07  
**Author:** Principal Chess Engine Research Scientist & C++17 Systems Engineer  
**Scope:** Bounded development intervention evaluating Phase-Tapered Adaptive Hybrid Blending  

---

## 1. Motivation & Intervention Design

Phases 2 and 5 established the primary causal mechanism behind the v0.62 replication divergence:
1. **Middlegame Excellence:** In middlegames (Phase $> 16$), NNUE-V2 is superior to Classical C1 (MAE 186.7 vs 208.1 cp).
2. **Endgame Pathology:** In endgames (Phase $\le 16$), NNUE-V2 suffers from feature sparsity and a negative rank correlation ($\rho = -0.125$).
3. **Calibration Flaw:** Frozen N1 enforces a rigid 50/50 blend in all game phases, cutting Classical C1's passed pawn bonuses in half during endgames.

### Proposed Bounded Intervention: Phase-Tapered Adaptive Blending (PT-Hybrid)
Instead of a static 50/50 blend factor across the entire game, the neural contribution is scaled dynamically by the remaining material phase:
$$\text{Weight}_{\text{Neural}}(\text{Phase}) = 0.50 \times \left(\frac{\text{Phase}}{24}\right)$$
$$\text{Weight}_{\text{Classical}}(\text{Phase}) = 1.0 - \text{Weight}_{\text{Neural}}(\text{Phase})$$

- **In the Opening / Middlegame ($\text{Phase} = 24$):** 50% Classical / 50% Neural. Retains 100% of the neural tactical sharpness and $-29.4\%$ search tree contraction.
- **In the Endgame ($\text{Phase} \to 0$):** Neural weight smoothly tapers to 0%, while Classical evaluation smoothly increases to 100%, restoring classical passed pawn progression and king centralization rules.

---

## 2. Empirical Validation on Held-Out Test Set (500 Positions)

The Phase-Tapered intervention was evaluated against Stockfish 19 ground truth across the 500 held-out positions from Phase 2:

| Positional Regime | Position Count | Metric | Classical C1 | Frozen N1 (50/50) | Phase-Tapered (PT-Hybrid) | Relative Improvement |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| **Overall** | 500 | **MAE (cp)** | 212.8 | 202.5 | **198.7** | **-3.8 cp over N1, -14.1 cp over C1** |
| | | **Spearman $\rho$** | 0.328 | 0.275 | **0.336** | **Outperforms both C1 and N1** |
| **Middlegame ($\text{Phase} > 16$)** | 387 | **MAE (cp)** | 208.1 | 186.7 | **186.9** | Preserves neural accuracy |
| | | **Spearman $\rho$** | 0.301 | 0.330 | **0.355** | **Highest correlation of all** |
| **Endgame ($\text{Phase} \le 16$)** | 113 | **MAE (cp)** | 228.9 | 256.8 | **239.0** | **-17.8 cp error reduction** |
| | | **Spearman $\rho$** | 0.382 | 0.150 | **0.276** | **Nearly doubles N1 correlation** |

---

## 3. Findings and Scientific Assessment

1. **Simultaneous Accuracy and Rank Gain:**  
   Phase-Tapered Blending simultaneously achieves the **lowest overall MAE (198.7 cp)** and the **highest overall rank correlation ($\rho = 0.336$)**, surpassing both pure classical and fixed hybrid baselines.
2. **Endgame Recovery Without Retraining:**  
   By fading out the neural network in piece-depleted endgames, the intervention suppresses the negative correlation of NNUE-V2 without requiring a single weight update or architectural change.
3. **Preregistered Constraint Adherence:**  
   As mandated by Phase 6 guidelines, this intervention is strictly a diagnostic proof of concept. No engine promotion or full tournament is conducted in this phase. The frozen Neural Baseline N1 remains unchanged in production code.
