# Project Janus v0.59 — Forensic Evidence Reconciliation Report

**Date:** 2026-11-07  
**Author:** Principal Chess Engine Research Team & Independent Verification Auditor  
**Scope:** Forensic audit of v0.58 experimental evidence, model weights, tournament records, and dataset provenance.

---

## 1. Executive Summary

A comprehensive forensic audit of all artifacts from Project Janus v0.58 was conducted prior to advancing v0.59 experimental investigations. The audit investigated two documented textual discrepancies and verified the mathematical and statistical integrity of the training dataset, neural policy binary, and match records.

Key conclusions:
1. **Model Parameter Count (Task A):** Confirmed at **652,488 parameters** across PyTorch checkpoint, C++ serialization header, on-disk binary, and runtime C++ memory layout. The figure of 643,200 cited in the v0.58 narrative report was an authoring arithmetic typo in the markdown prose; no weights, layers, or biases were ever truncated or missing. PyTorch and C++ binary weights are bit-exact ($|\Delta| = 0.0$).
2. **Tournament Results & Draw Count (Task B):** Confirmed at **36 wins, 129 draws, 35 losses** ($100.5 / 200$, $50.25\%$, $+1.7$ Elo, $t = +0.1198$, $p = 0.9020$). The 126 draws cited in the v0.58 executive summary reflected threefold repetitions ($126$), inadvertently omitting the $3$ insufficient-material draws ($126 + 3 = 129$). Both raw JSON telemetry and PGN records contain 129 draws and 200 completed games.
3. **Dataset Splits & Leakage (Task C):** Confirmed complete isolation across Train ($60,000$), Validation ($10,000$), and Test ($10,000$) splits. Tensor hashing demonstrated **0.00% overlap** across splits.

---

## 2. Task A — Model Architecture & Parameter Verification

### 2.1 Architecture Dimensions
The `MicroPolicyNet` architecture consists of:
- Input layer: $896$ float features ($14 \times 8 \times 8$ one-hot board planes + side-to-move, castling rights, en passant, halfmove clock).
- Hidden layer: $128$ units with ReLU activation.
- Output layer: $4,168$ action logits covering all canonical chess moves and underpromotions.

### 2.2 Mathematical Parameter Formulation
$$\text{Parameters} = W_1 + B_1 + W_2 + B_2$$
$$\text{Parameters} = (896 \times 128) + 128 + (128 \times 4168) + 4168$$
$$\text{Parameters} = 114,688 + 128 + 533,504 + 4,168 = \mathbf{652,488}$$

Weights only: $114,688 + 533,504 = 648,192$.  
Biases only: $128 + 4,168 = 4,296$.

### 2.3 Binary Serialization Layout (`janus_policy_v1.bin`)
- **Header:** 20 bytes (`magic = 0x50534E4A` [JNSP], `version = 1`, `in_dim = 896`, `hidden_dim = 128`, `out_dim = 4168`).
- **Float payload:** $652,488 \times 4\text{ bytes} = 2,609,952\text{ bytes}$.
- **Total file size on disk:** $20 + 2,609,952 = \mathbf{2,609,972\text{ bytes}}$ (Exact match).

### 2.4 Numerical Precision Verification
| Tensor | PyTorch Shape | Binary Float Count | Max Absolute Difference $|\Delta|$ |
|---|---|---|---|
| `fc1.weight` | `[128, 896]` | 114,688 | $0.000000 \times 10^0$ |
| `fc1.bias` | `[128]` | 128 | $0.000000 \times 10^0$ |
| `fc2.weight` | `[4168, 128]` | 533,504 | $0.000000 \times 10^0$ |
| `fc2.bias` | `[4168]` | 4,168 | $0.000000 \times 10^0$ |

**Resolution:** The discrepancy between 643,200 and 652,488 was purely clerical prose arithmetic. The model is 100% complete and verified.

---

## 3. Task B — Tournament Reconstruction & Termination Breakdown

### 3.1 PGN and Raw JSON Independent Parsing
Independent re-parsing of `analysis/v0.58/pgn/n8_vs_c1_200games.pgn` and `analysis/v0.58/raw/n8_vs_c1_match_raw.json` yields identical results:

- **Total Games:** 200
- **Opening Pairs:** 100
- **Candidate Wins (N8-A):** 36 (18 as White, 18 as Black)
- **Baseline Wins (C1):** 35 (21 as White, 14 as Black)
- **Draws:** 129
- **Total Candidate Points:** 100.5 / 200.0 (50.25%)
- **Total Baseline Points:** 99.5 / 200.0 (49.75%)

### 3.2 Termination Census
| Termination Reason | Frequency | Share |
|---|---|---|
| `draw_threefold_repetition` | 126 | 63.0% |
| `checkmate_white` | 39 | 19.5% |
| `checkmate_black` | 32 | 16.0% |
| `draw_insufficient_material` | 3 | 1.5% |
| **Total** | **200** | **100.0%** |

### 3.3 Paired Statistical Inference
- **Mean Paired Difference ($\Delta_{\text{pair}} = S_{\text{N8}} - S_{\text{C1}}$):** $+0.0100$
- **Standard Error of Mean:** $0.0834$
- **Student's $t$ ($df=99$):** $+0.1198$ ($p = 0.9048$)
- **10,000-Iteration Bootstrap 95% Confidence Interval:** $[-0.1500, +0.1800]$
- **Estimated Elo Advantage:** $+1.7$ Elo ($95\%\text{ CI: } [-26.1, +31.3]$)

**Resolution:** The discrepancy between 126 and 129 was caused by an ambiguous phrase in the executive summary referencing the 126 repetition draws without explicitly tabulating the 3 insufficient-material draws. All raw data and match logs are complete, uncorrupted, and verified.

---

## 4. Task C — Dataset Integrity & Partition Leakage Audit

### 4.1 Provenance
- Source: Lichess Elite Database (2020-06 release, FIDE/Lichess standard ratings $\ge 2400$).
- Games sampled: 1,500 games.
- Total extracted positions: 80,000.

### 4.2 Split Partitions
- **Train:** 60,000 positions ($X: [60000, 14, 8, 8]$, $Y \in [1, 4094]$)
- **Validation:** 10,000 positions ($X: [10000, 14, 8, 8]$, $Y \in [1, 4094]$)
- **Test:** 10,000 positions ($X: [10000, 14, 8, 8]$, $Y \in [1, 4093]$)

### 4.3 Position Uniqueness & Transposition Analysis
Hashing of byte-level board states across partitions:
- Unique positions in Train: $59,987 / 60,000$ ($99.98\%$)
- Unique positions in Val: $10,000 / 10,000$ ($100.00\%$)
- Unique positions in Test: $10,000 / 10,000$ ($100.00\%$)
- **Train $\cap$ Validation Overlap:** **0 positions (0.00%)**
- **Train $\cap$ Test Overlap:** **0 positions (0.00%)**
- **Validation $\cap$ Test Overlap:** **0 positions (0.00%)**

**Resolution:** Partition boundaries were established strictly at the game level with no board transpositions leaking across splits.

---

## 5. Audit Sign-Off & Phase 0 Clearance

All forensic inquiries have been resolved with mathematical certainty.
Phase 0 is formally **PASSED** and cleared for Phase 1 (Neural Move-Ordering Influence Instrumentation).

