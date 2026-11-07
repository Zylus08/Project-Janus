# NNUE-V2 Numerical Precision, Quantization & Arithmetic Audit

**Milestone:** Project Janus v0.61  
**Author:** ML Training Engineer & Independent Experimental Auditor  
**Date:** 2026-11-07  
**Artifact Evaluated:** `analysis/v0.61/models/janus_nnue_v2_small.jnnue` (CRC32: `0x81d61206`) & `janus_nnue_v2_compact.jnnue` (CRC32: `0xe0ddb558`)  

---

## 1. Mathematical Architecture & Quantization Formulation

NNUE-V2 adopts an incrementally updatable HalfKP-style feature transformer coupled to a dual-perspective clipped linear feedforward network ($768 \to M \to L_1 \to 1$):

1. **Feature Transformer Layer ($\text{Input} \to \text{Accumulator}$):**
   - Active input features $\mathcal{F}_{\text{stm}}$ and $\mathcal{F}_{\text{opp}}$ where $|\mathcal{F}| \le 32$.
   - Scale factor: $S_{\text{accum}} = 127$.
   - Weights: $W_{\text{ft}} \in \mathbb{Z}^{768 \times M}$ stored as `int16_t`.
   - Biases: $b_{\text{ft}} \in \mathbb{Z}^M$ stored as `int16_t`.
   - Forward pass:
     $$\text{Acc}[p] = b_{\text{ft}} + \sum_{f \in \mathcal{F}_p} W_{\text{ft}}[f]$$
   - Quantized Activation (Clipped ReLU):
     $$a_{\text{accum}}[i] = \text{clamp}\left(\text{Acc}[i], 0, 127\right) \in [0, 127] \quad (\text{uint8\_t})$$

2. **Hidden Linear Layer 1 ($\text{FC1}$):**
   - Input dimension: $2M$ (concatenation of stm and opponent perspectives: $[a_{\text{stm}} \,\|\, a_{\text{opp}}]$).
   - Weights: $W_{\text{fc1}} \in \mathbb{Z}^{L_1 \times 2M}$ stored as `int8_t`.
   - Biases: $b_{\text{fc1}} \in \mathbb{Z}^{L_1}$ stored as `int32_t`.
   - Scale factor: $S_{\text{L1}} = 64$ ($2^6$).
   - Dot product accumulation:
     $$\text{sum}_j = b_{\text{fc1}}[j] + \sum_{i=0}^{2M-1} a_{\text{accum}}[i] \cdot W_{\text{fc1}}[j, i] \quad (\text{int32\_t})$$
   - Activation (Right-shift by 6 with arithmetic floor and clamp):
     $$a_{\text{L1}}[j] = \text{clamp}\left(\text{sum}_j \gg 6, 0, 127\right) \in [0, 127] \quad (\text{uint8\_t})$$

3. **Output Evaluation Layer ($\text{FC2} \to \text{Score}$):**
   - Input dimension: $L_1$.
   - Weights: $W_{\text{fc2}} \in \mathbb{Z}^{1 \times L_1}$ stored as `int8_t`.
   - Bias: $b_{\text{fc2}} \in \mathbb{Z}$ stored as `int32_t`.
   - Centipawn evaluation scaling factor: $S_{\text{eval}} = 16$.
   - Output score:
     $$\text{Score}_{\text{cp}} = \left(b_{\text{fc2}} + \sum_{j=0}^{L_1-1} a_{\text{L1}}[j] \cdot W_{\text{fc2}}[j]\right) / S_{\text{eval}}$$

---

## 2. Formal Mathematical Proof of Non-Saturation in AVX2 Dot Products

A critical engineering vulnerability in AVX2 integer neural implementations is 16-bit intermediate accumulator overflow when using `_mm256_maddubs_epi16`.

`_mm256_maddubs_epi16` operates on:
- First operand: Unsigned 8-bit integers ($u_0, u_1 \in [0, 255]$).
- Second operand: Signed 8-bit integers ($s_0, s_1 \in [-128, 127]$).
- Operation: Computes pairwise products and adds adjacent pairs into signed 16-bit integers:
  $$\text{result} = \text{saturate}_{16}\left(u_0 \cdot s_0 + u_1 \cdot s_1\right)$$

### Theorem: Zero Saturation Overflow
Under the Janus NNUE-V2 quantization scheme, `_mm256_maddubs_epi16` will **never** saturate.

### Proof:
1. In NNUE-V2, accumulator activations are clamped to $[0, 127]$:
   $$0 \le u_k \le 127$$
2. The weight values are signed 8-bit:
   $$-128 \le s_k \le 127$$
3. The maximum possible positive product sum occurs when $u_0 = u_1 = 127$ and $s_0 = s_1 = 127$:
   $$\text{Max} = 127 \times 127 + 127 \times 127 = 16,129 + 16,129 = 32,258$$
   Comparing with the maximum signed 16-bit integer $2^{15}-1 = 32,767$:
   $$32,258 \le 32,767$$
4. The minimum possible negative product sum occurs when $u_0 = u_1 = 127$ and $s_0 = s_1 = -128$:
   $$\text{Min} = 127 \times (-128) + 127 \times (-128) = -16,256 - 16,256 = -32,512$$
   Comparing with the minimum signed 16-bit integer $-2^{15} = -32,768$:
   $$-32,512 \ge -32,768$$
5. Because $[-32,512, +32,258] \subset [-32,768, +32,767]$, every intermediate product sum is strictly representable as a standard signed 16-bit integer without truncation, wrap-around, or saturation clamping. $\blacksquare$

---

## 3. PyTorch Float32 vs Native INT8/INT16 Quantization Parity

Quantization parity was audited across 1,000 stratified held-out test positions:

| Metric | NNUE-V2-Small ($M=64, L_1=16$) | NNUE-V2-Compact ($M=128, L_1=32$) | Preregistered Acceptance Threshold | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Pearson Correlation ($r$)** | **0.998887** | **0.999257** | $\ge 0.995$ | **PASS** |
| **Sign Agreement** | **98.50%** | **97.60%** | $\ge 95.0\%$ | **PASS** |
| **Quantization MAE** | **10.01 cp** | **9.31 cp** | $\le 15.0\text{ cp}$ | **PASS** |
| **Max Quantization Delta** | **44.0 cp** | **38.0 cp** | $\le 60.0\text{ cp}$ | **PASS** |
| **Binary CRC32 Check** | `0x81d61206` (MATCH) | `0xe0ddb558` (MATCH) | Header == Computed | **PASS** |

Both models exhibit near-perfect fidelity ($r > 0.998$) between continuous Float32 gradients and quantized native integer arithmetic.

---

## 4. Scalar vs AVX2 Implementation Equivalence

Verification tests executed via `test_nnue_v2_native.exe`:

1. **Full Refresh Accumulator Parity:**
   `acc_scalar` == `acc_avx2` for both White and Black perspectives across all accumulator indices ($0 \dots M-1$). **Bit-exact (Diff = 0 across 100% of tested cells).**
2. **Incremental Update Parity:**
   Sequential quiet move (e.g. `e2e4`, `g1f3`) updates produce bit-exact accumulator states between scalar and AVX2 code paths.
3. **Static Evaluation Parity:**
   Starting position evaluation:
   - Scalar: **16 cp**
   - AVX2: **16 cp**
   - Difference: **0 cp (Bit-Exact)**.

---

## 5. Audit Conclusion
The NNUE-V2 quantization pipeline and native AVX2 SIMD arithmetic meet all mathematical correctness, precision, and numerical safety requirements. No arithmetic overflow, unaligned memory access, or quantization degradation was observed.

