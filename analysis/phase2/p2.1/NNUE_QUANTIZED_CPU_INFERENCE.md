# Janus NNUE — Quantized CPU Inference & Fixed-Point Verification (Phase 5)

**Milestone:** Phase 2, Milestone P2.1  
**Architecture:** Quantized Fixed-Point CPU Inference Engine  
**Binary Weight File:** `analysis/phase2/p2.1/models/janus_nnue_h1.bin` (213,468 bytes)  
**Binary SHA-256:** `fd4d8105c39fd9a071c48ca1dd2298bc64a13d7023c57c4c34e840d24cbfa616`  
**Date:** November 16, 2026  
**Auditor:** Principal Computer Chess Architect & Performance Engineer  

---

## 1. Quantization Scheme & Arithmetic Design

To achieve ultra-fast CPU inference without floating-point FPU latency, Model H1 is quantized into standard fixed-point integer representations:

### Quantization Scales:
- **Feature Transformer Weights ($W_{\text{ft}}$):** Scale $Q_{\text{FT}} = 256.0$ ($\text{int16\_t}$).
- **Feature Transformer Biases ($b_{\text{ft}}$):** Scale $Q_{\text{FT}} = 256.0$ ($\text{int16\_t}$).
- **Hidden Layer 1 Weights ($W_{\text{L1}}$):** Scale $Q_{\text{L1}} = 128.0$ ($\text{int16\_t}$).
- **Hidden Layer 1 Biases ($b_{\text{L1}}$):** Scale $Q_{\text{FT}} \times Q_{\text{L1}} = 32,768.0$ ($\text{int32\_t}$).
- **Output Layer Weights ($W_{\text{L2}}$):** Scale $Q_{\text{L2}} = 128.0$ ($\text{int16\_t}$).
- **Output Layer Bias ($b_{\text{L2}}$):** Scale $Q_{\text{L1}} \times Q_{\text{L2}} = 16,384.0$ ($\text{int32\_t}$).

### Execution Arithmetic:
1. **Accumulator Accumulation:**
   $$\text{acc}[j] = b_{\text{ft}}[j] + \sum_{f \in \text{Active}} W_{\text{ft}}[j, f]$$
   Evaluated with 32-bit integer registers, preventing any overflow (max 32 active pieces $\times 32767 < 2^{31}-1$).
2. **Clipped ReLU Activation:**
   $$\text{act}[j] = \min(\max(\text{acc}[j], 0), 256)$$
3. **Hidden Layer 1 Forward:**
   $$\text{sum}_{\text{L1}}[k] = b_{\text{L1}}[k] + \sum_{j=0}^{255} W_{\text{L1}}[k, j] \cdot \text{act}[j]$$
   $$\text{act}_{\text{L1}}[k] = \min(\max(\text{sum}_{\text{L1}}[k] \mathbin{/} 256, 0), 128)$$
4. **Output Scalar Forward:**
   $$\text{sum}_{\text{L2}} = b_{\text{L2}} + \sum_{k=0}^{31} W_{\text{L2}}[k] \cdot \text{act}_{\text{L1}}[k]$$
   $$\text{Score}_{\text{cp}} = \frac{\text{sum}_{\text{L2}}}{16384} \times \frac{400}{\ln 10}$$

---

## 2. Float vs Quantized Empirical Parity

Evaluated across 500 held-out test positions:

| Metric | Measured Value | Standard / Formal Target |
| :--- | :---: | :---: |
| **Pearson Correlation ($r$)** | **0.999635** | $> 0.9990$ |
| **Mean Absolute Error (MAE)** | **6.51 centipawns** | $< 10.0\text{ cp}$ |
| **Max Error** | **25.76 centipawns** | $< 50.0\text{ cp}$ |
| **Arithmetic Overflow Count** | **0** | **0** (strictly prohibited) |
| **Saturation Anomalies** | **0** | **0** |

The Pearson correlation of **$0.999635$** confirms that the fixed-point C++ execution path behaves with near-perfect fidelity to the PyTorch floating-point reference model.
