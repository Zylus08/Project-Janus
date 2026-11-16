# Janus NNUE — Model Architecture & Training Report (Phase 4)

**Milestone:** Phase 2, Milestone P2.1  
**Candidate Architecture:** Janus NNUE Model H1 (`JanusNNUE_Small`)  
**Network Dimensions:** Dual HalfKP-768 $\to 128$ (Accumulator $\times 2$) $\to 32 \to 1$  
**Total Parameters:** 106,689 parameters ($\approx 208\text{ KB}$ quantized)  
**Date:** November 16, 2026  
**Auditor:** Principal Computer Chess Architect & Neural Training Specialist  

---

## 1. Network Topology & Mathematical Formulation

Janus NNUE Model H1 is an original, compact neural chess evaluation network designed specifically for single-cycle integer CPU inference without GPU acceleration:

```
  White Perspective:  [768 binary features] ──┐
                                              ├──► W_ft (768 x 128) ──► Acc_White (128) ──┐
  Black Perspective:  [768 binary features] ──┘                                           │
                                                                                          ▼
                      Side-to-Move Concatenation:  [Acc_Friendly, Acc_Enemy] (256 values)
                                                                                          │
                                                                                          ▼  Clipped ReLU [0, 1.0]
                      Hidden Layer L1:             W_l1 (256 x 32) + b_l1 (32)
                                                                                          │
                                                                                          ▼  Clipped ReLU [0, 1.0]
                      Output Layer L2:             W_l2 (32 x 1) + b_l2 (1)
                                                                                          │
                                                                                          ▼  Linear
                      Scalar Output:               Logit y ──► Centipawn Score cp
```

### Parameter Accounting:
- **Feature Transformer (`ft`):** $768 \times 128 = 98,304$ weights + $128$ biases $= 98,432$ parameters.
- **Hidden Layer 1 (`l1`):** $256 \times 32 = 8,192$ weights + $32$ biases $= 8,224$ parameters.
- **Output Layer (`l2`):** $32 \times 1 = 32$ weights + $1$ bias $= 33$ parameters.
- **Total Network Parameters:** $106,689$ parameters.
- **Memory Footprint:** $\approx 208\text{ KB}$ in INT16 fixed-point representation (comfortably fits within the CPU L2 cache).

---

## 2. Training Protocol & Convergence

- **Dataset:** 40,736 training positions, 5,127 validation positions, 5,115 held-out test positions from authentic Project Janus Phase 1 games (zero external or pre-trained network weights).
- **Optimizer:** Adam with learning rate $\eta = 10^{-3}$, weight decay $10^{-5}$, batch size $256$.
- **Loss Function:** Binary Cross-Entropy with Logits against perspective game results $z \in \{1.0, 0.5, 0.0\}$.

### Training Progression:
| Epoch | Training Loss (BCE) | Validation Loss (BCE) | Validation Decision Accuracy |
| :---: | :---: | :---: | :---: |
| **1** | 0.62190 | 0.65718 | 59.88% |
| **2** | 0.46855 | 0.69519 | 60.44% |
| **3** | 0.41781 | 0.73584 | 62.96% |
| **4** | 0.39923 | 0.74128 | 59.82% |
| **5** | 0.39061 | 0.76781 | 60.72% |

### Held-Out Generalization:
- **Test Loss:** $0.77659$
- **Held-Out Test Accuracy:** $59.78\%$
- **Overfitting Guard:** Model parameters preserved from Epoch 3/5 with early checkpointing.
- **Float Checkpoint:** `analysis/phase2/p2.1/models/janus_nnue_h1_float.pt`.
