# PROJECT JANUS v0.60 — NNUE ARCHITECTURE SPECIFICATION
**Author:** Principal Chess Engine Research Architect, ML Systems Engineer & Independent Scientific Reproducibility Auditor  
**Date:** 2026-11-07  
**Repository:** `E:\ChessXML\project-janus`  
**Document Designation:** `NNUE_ARCHITECTURE_SPEC.md`  
**Milestone:** v0.60 (Efficient Neural Value Evaluation)

---

## 1. Executive Summary & Design Principles

This document specifies the neural network architecture, feature representation, mathematical operations, quantization layout, and incremental accumulator mechanics for Janus Neural Value V1 (`NNUE-V1`).

### Core Design Principles:
1. **Nanosecond Native Latency:** The primary failure mode of neural evaluation in alpha-beta engines is search slowdown. The architecture must evaluate positions in $< 50\ \text{ns}$ on a single CPU thread.
2. **Incremental Accumulator Compatibility:** The sparse feature transformer must allow $O(1)$ vector updates during tree traversal, updating only the rows corresponding to moved and captured pieces.
3. **Dual Perspective Symmetry:** Board features are evaluated from White and Black perspectives separately and symmetrized relative to the side to move.
4. **Quantization by Design:** The network uses integer arithmetic (INT16 accumulators, INT8 weights, Clipped ReLU activations), eliminating floating-point math during native inference.
5. **Architectural Ablation:** Two bounded variants are specified: **V1-Small** (minimum practical sparse-feature model) and **V1-Compact** (king-bucketed model).

---

## 2. Feature Representation & Perspective Mapping

### 2.1 Sparse Feature Space
Features are defined from the perspective of the side being evaluated ($p \in \{\text{White}, \text{Black}\}$):
- For player $p$, friendly pieces are colored $0$ (`US`), enemy pieces are colored $1$ (`THEM`).
- Piece types: Pawn (0), Knight (1), Bishop (2), Rook (3), Queen (4), King (5).
- Square indexing: $sq \in [0, 63]$ (where $0 = \text{a1}, 63 = \text{h8}$).
  - For White perspective: square index is unchanged: $sq_W = sq$.
  - For Black perspective: board is vertically mirrored: $sq_B = \text{sq} \oplus 56$ (rank $r \to 7 - r$, file unchanged).
- Linear Feature Index:
  $$\text{FeatureIndex}(c_{\text{rel}}, \text{piece}, sq_{\text{rel}}) = c_{\text{rel}} \cdot (6 \times 64) + \text{piece} \cdot 64 + sq_{\text{rel}}$$
  where $c_{\text{rel}} \in \{0, 1\}$, $\text{piece} \in [0, 5]$, $sq_{\text{rel}} \in [0, 63]$.
- Total sparse features per perspective: $2 \times 6 \times 64 = 768$ features.
- In any legal chess position, the number of active features per perspective is $K \in [2, 32]$ (at least 2 kings, at most 32 pieces).

### 2.2 Board Metadata Handling
- **Side to Move (STM):** Handled at the accumulator concatenation layer. The first half of the dense input is $\mathbf{acc}_{\text{stm}}$, and the second half is $\mathbf{acc}_{\text{nstm}}$.
- **Castling Rights:** Implicitly encoded by king and rook locations; additional castling flags can be added if empirical ablation justifies it, but are omitted from sparse accumulators to keep incremental updates simple and bitboard-aligned.
- **En Passant & Halfmove Clock:** Handled by classical search and draw adjudicators (repetition and 50-move checks occur before leaf evaluation).
- **Underpromotions:** Fully represented: pawn feature is removed; specific knight/bishop/rook/queen feature is inserted.

---

## 3. Candidate Architectures: V1-Small vs V1-Compact

### 3.1 Architecture Overview

```
[Sparse Features (768)]
         │
         ▼
[Feature Transformer] ─── Incremental Accumulator (White & Black)
         │
         ▼
[Clipped ReLU [0, 127]]
         │
         ▼
[Side-to-Move Concatenation: (stm, nstm)]
         │
         ▼
[Dense Layer 1 + Clipped ReLU]
         │
         ▼
[Output Linear Layer (Scalar Score in Centipawns)]
```

### 3.2 Formal Architectural Specifications

| Property | Candidate V1-Small | Candidate V1-Compact |
| :--- | :--- | :--- |
| **Sparse Feature Dimension ($D_{\text{in}}$)** | 768 (Piece-Square) | 3,072 (4 King Buckets × 768) |
| **Accumulator Dimension ($M$) per side** | 64 | 128 |
| **Total Accumulator Vector** | $2 \times 64 = 128$ | $2 \times 128 = 256$ |
| **Activation Function** | $\text{CReLU}(x) = \text{clamp}(x, 0, 127)$ | $\text{CReLU}(x) = \text{clamp}(x, 0, 127)$ |
| **Hidden Dense Layer 1** | $128 \to 16$ | $256 \to 32$ |
| **Hidden Activation** | $\text{CReLU}(x) = \text{clamp}(x, 0, 127)$ | $\text{CReLU}(x) = \text{clamp}(x, 0, 127)$ |
| **Output Layer** | $16 \to 1$ | $32 \to 1$ |
| **Feature Transformer Parameters** | $768 \times 64 + 64 = 49,216$ | $3,072 \times 128 + 128 = 393,344$ |
| **Dense Layer 1 Parameters** | $128 \times 16 + 16 = 2,064$ | $256 \times 32 + 32 = 8,224$ |
| **Output Layer Parameters** | $16 \times 1 + 1 = 17$ | $32 \times 1 + 1 = 33$ |
| **Total Parameters** | **51,297** | **401,601** |
| **FP32 Checkpoint Size** | $205.2\ \text{KB}$ | $1,606.4\ \text{KB}$ ($1.57\ \text{MB}$) |
| **INT16/INT8 Deployed Model Size** | $\mathbf{100.5\ \text{KB}}$ | $\mathbf{795.1\ \text{KB}}$ |
| **Working Accumulator Memory** | 256 bytes / ply | 512 bytes / ply |

---

## 4. Incremental Accumulator Mathematical Formulation

### 4.1 Accumulator State
For each ply $d$, the state maintains two accumulator vectors:
$$\mathbf{A}_W^{(d)} \in \mathbb{Z}^{M}, \quad \mathbf{A}_B^{(d)} \in \mathbb{Z}^{M}$$

### 4.2 Full Refresh (Root or Cold-Start)
$$\mathbf{A}_p^{(d)} = \mathbf{b}_{\text{ft}} + \sum_{i \in \text{ActiveFeatures}(p)} \mathbf{W}_{\text{ft}}[:, i]$$
Complexity: $K \times M$ additions (at most $32 \times 64 = 2,048$ additions for V1-Small).

### 4.3 Incremental Updates
When move $m$ transforms board from state $S$ to $S'$:
1. **Quiet Move (piece $P$ from $sq_1$ to $sq_2$):**
   $$\mathbf{A}_p^{(d+1)} = \mathbf{A}_p^{(d)} - \mathbf{W}_{\text{ft}}[:, \text{idx}(p, P, sq_1)] + \mathbf{W}_{\text{ft}}[:, \text{idx}(p, P, sq_2)]$$
   Cost: 1 vector subtract, 1 vector add per perspective ($2 \times 64$ additions, $2 \times 64$ subtractions).
2. **Capture (piece $P$ from $sq_1$ captures $V$ at $sq_2$):**
   $$\mathbf{A}_p^{(d+1)} = \mathbf{A}_p^{(d)} - \mathbf{W}_{\text{ft}}[:, \text{idx}(p, P, sq_1)] - \mathbf{W}_{\text{ft}}[:, \text{idx}(p, V, sq_2)] + \mathbf{W}_{\text{ft}}[:, \text{idx}(p, P, sq_2)]$$
   Cost: 2 vector subtracts, 1 vector add.
3. **Promotion (pawn promotes to $Q$ at $sq_2$, optional capture of $V$):**
   Subtract moving pawn at $sq_1$; subtract captured piece at $sq_2$ (if any); add promoted piece $Q$ at $sq_2$.
4. **En Passant:**
   Subtract pawn at $sq_1$; subtract captured enemy pawn at $(sq_2 \pm 8)$; add pawn at $sq_2$.
5. **Castling:**
   Move king: sub at $k_{\text{from}}$, add at $k_{\text{to}}$.
   Move rook: sub at $r_{\text{from}}$, add at $r_{\text{to}}$. Total: 2 vector subs, 2 vector adds.

### 4.4 King Bucket Transitions (V1-Compact)
In V1-Compact, if the friendly king crosses a bucket boundary, the friendly perspective accumulator undergoes a full refresh ($\le 32 \times 128 = 4,096$ additions), while the opponent perspective accumulator remains incrementally updated.
In V1-Small, king bucket transitions do not exist; updates are unconditionally $O(1)$.

---

## 5. Quantization & Native Integer Arithmetic

### 5.1 Quantization Scheme
- **Input Features:** Binary sparse $\{0, 1\}$.
- **Feature Transformer Weights ($\mathbf{W}_{\text{ft}}$):** Quantized to `int16_t` with scale $S_0 = 256$.
- **Feature Transformer Biases ($\mathbf{b}_{\text{ft}}$):** Quantized to `int16_t` with scale $S_0 = 256$.
- **Accumulator Values:** `int16_t`. Since at most 32 pieces contribute and weights are bounded, maximum accumulator value is bounded within $[-32768, 32767]$.
- **Activation Function:**
  $$f_{\text{act}}(x) = \text{clamp}(x / S_0, 0, 127) \in \text{uint8\_t}$$
- **Dense Layer 1 Weights ($\mathbf{W}_1$):** Quantized to `int8_t` with scale $S_1 = 64$.
- **Dense Layer 1 Biases ($\mathbf{b}_1$):** Quantized to `int32_t` with scale $S_0 \cdot S_1$.
- **Output Layer Weights ($\mathbf{W}_2$):** Quantized to `int8_t` with scale $S_2 = 128$.
- **Output Layer Bias ($\mathbf{b}_2$):** Quantized to `int32_t`.
- **Centipawn Scaling:** Final linear integer projection maps to centipawns with scale factor $S_{\text{eval}} = 600$.

### 5.2 Binary File Format Specification (`.jnnue`)
Model files use a strict 64-byte header followed by binary tensor payloads:
```cpp
struct NNUEHeader {
    uint32_t magic;           // 0x4A4E5545 ("JNUE")
    uint32_t version;         // 1
    uint32_t arch_id;         // 1 = V1-Small, 2 = V1-Compact
    uint32_t feature_dim;     // 768 or 3072
    uint32_t accum_dim;       // 64 or 128
    uint32_t l1_dim;          // 16 or 32
    uint32_t output_dim;      // 1
    uint32_t scale_accum;     // 256
    uint32_t scale_l1;        // 64
    uint32_t scale_output;    // 128
    uint32_t eval_scale;      // 600
    uint32_t checksum_crc32;  // CRC32 of weight payload
    uint8_t  reserved[16];    // Alignment padding to 64 bytes
};
```

---

## 6. Latency & Computational Cost Projections

| Metric | Handcrafted (C1) | V1-Small (NNUE) | V1-Compact (NNUE) |
| :--- | :--- | :--- | :--- |
| **Full Refresh Time** | $\approx 250\ \text{ns}$ | $\approx 80\ \text{ns}$ | $\approx 180\ \text{ns}$ |
| **Incremental Update Time** | N/A (Full recalc) | $\mathbf{\approx 8 - 12\ \text{ns}}$ | $\mathbf{\approx 18 - 25\ \text{ns}}$ |
| **Feedforward Inference Time** | N/A | $\mathbf{\approx 15 - 20\ \text{ns}}$ | $\mathbf{\approx 40 - 55\ \text{ns}}$ |
| **Total Leaf Eval Latency** | $\approx 250\ \text{ns}$ | $\mathbf{\approx 25 - 35\ \text{ns}}$ | $\mathbf{\approx 60 - 80\ \text{ns}}$ |
| **Peak Cache Working Set** | $< 1\ \text{KB}$ | $\mathbf{101\ \text{KB}}$ (Fits in L2) | $\mathbf{795\ \text{KB}}$ (Fits in L3) |

---

## 7. Architectural Decision & Milestone Plan

1. Both **V1-Small** and **V1-Compact** are rigorously specified and implemented in the PyTorch training pipeline.
2. In Phase 3, we train:
   - **E0:** Handcrafted Static Evaluation (Control).
   - **E1:** V1-Small ($M=64$, $768$ inputs, $51\text{K}$ params).
   - **E2:** V1-Compact ($M=128$, $3,072$ inputs, $401\text{K}$ params).
3. The model delivering the optimal Pareto trade-off between held-out teacher MAE and CPU leaf latency will be quantized and natively integrated into the engine.
