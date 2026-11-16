# Project Janus — Phase 2, Milestone P2.3
## Phase 0: P2.2 Evidence Reconciliation & Scientific Integrity Audit

**Author:** Principal Computer Chess Researcher & Tournament Integrity Auditor  
**Milestone:** P2.3 — King-Relative NNUE, Search-Grounded Neural Training, Incremental CPU Inference & Independent Playing-Strength Qualification  
**Date:** 2026-11-16  
**Parent Commit:** `aa66937`  
**Branch:** `phase2/nnue-r1`  

---

### 1. Environment & Baseline Cryptographic Audit

All historical executables, dynamic libraries, and neural weight binaries were re-audited via SHA-256 before initiating Milestone P2.3:

```
========================================================================================================================
CRYPTOGRAPHIC CONTROL RECONCILIATION (PHASE 0)
========================================================================================================================
Artifact ID     | Relative Path                                       | Verified SHA-256 Checksum
----------------+-----------------------------------------------------+-------------------------------------------------
H1 Candidate    | analysis/phase2/p2.1/control/janus_hybrid_h1.exe    | 755C451D064EA38ECC400274CBCE48D28B6F43F67747...
H1 Shared Lib   | analysis/phase2/p2.1/control/janus_hybrid_h1.dll    | D73EB8425F2F875DBD2AB2FFDD616072468955D36820...
H1 Model Binary | analysis/phase2/p2.1/models/janus_nnue_h1.bin       | FD4D8105C39FD9A08783D9D9AC0BB85B27DB99578B97...
R1 Foundation   | analysis/phase1/p1.22/control/janus_classical_r1.exe| 7312B2B73CD9D40F108EE1B5F3903632A2A7805B19BC...
X7 Baseline     | analysis/phase1/p1.3/control/janus_classical_x7.exe | 86392A2F4BD4182A4D7DC21E32940BD7939F6816794D...
X22 Reference   | analysis/phase1/p1.17/control/janus_classical_x22.exe| 35D095CFFE8A2EDA412171803C09BE52A74DFB3F9744...
========================================================================================================================
```

- **Branch:** `phase2/nnue-r1` confirmed clean and synchronized.
- **HEAD Commit:** `aa66937` (`Milestone P2.2: Neural Evaluation Failure Forensics, Score Calibration & Scalable Dataset Readiness`).
- **P2.2 Manifests:** `experiment_manifest.json` and `sha256_manifest.json` (48 hashed items) verified intact.

---

### 2. Reconstruction of H2 vs R1 Match (50 Games)

The 50-game authoritative head-to-head match between Candidate Hybrid H2 (50% Classical R1 + 50% Neural H1) and Classical R1.0 was parsed and validated using `python-chess`:

```
========================================================================================================================
MATCH RECONSTRUCTION SUMMARY: HYBRID H2 vs CLASSICAL R1.0
========================================================================================================================
Match Parameter              | Audited Value
-----------------------------+------------------------------------------------------------------------------------------
PGN Source File              | analysis/phase2/p2.2/raw/match_h2_vs_r1.pgn
Total Games Reconstructed    | 50 games (25 opening pairs, color-reversed)
Time Control                 | Fischer 5.0s + 0.05s
H2 Wins / Draws / Losses     | 0 Wins / 8 Draws / 42 Losses
H2 Total Points              | 4.0 / 50.0 points
H2 Score Percentage          | 8.00%
Pentanomial Distribution     | [17, 8, 0, 0, 0] (17 LL, 8 LD, 0 DD/LW, 0 WD, 0 WW)
Mean Game Score              | 0.0800
Standard Error of Mean (se)  | 0.0238
95% Paired Confidence Int.   | [3.33%, 12.67%] (p < 0.0001)
Relative Elo Rating          | -424.3 Elo vs Classical R1.0
Total Moves Reconstructed    | 3,866 plies
Illegal Moves / Forfeits     | 0 (100% legal compliance)
========================================================================================================================
```

### 3. Verification of H2 Blending Configuration & Evaluation Scale Impact

Inspection of the engine dispatch log confirms that H2 strictly executed with `UCI_Variant=H2` and `NNUE_Weight=50`:
$$\text{Score}_{\text{hybrid}} = \frac{50 \cdot \text{Score}_{\text{nnue}} + 50 \cdot \text{Score}_{\text{classical}}}{100} = 0.5 \cdot \text{Score}_{\text{classical}} + 0.5 \cdot \text{Score}_{\text{nnue}}$$

#### Impact on Alpha-Beta Search Pruning and TT Reuse:
1. **Severe Score Compression Dilution:**
   - Classical R1 evaluates a clean Queen advantage at $+867\text{ cp}$.
   - Neural H1 evaluates the same advantage at $+203\text{ cp}$ ($4.3\times$ compression).
   - The blended score drops to $+535\text{ cp}$ (a $38\%$ reduction).
   - In endgames where classical scores would trigger decisive pruning cutoffs ($\beta \le \text{eval} - \text{margin}$), the blended score remained within aspiration windows ($\pm 25\text{ cp}$ to $\pm 50\text{ cp}$), forcing the search to explore unnecessary branches.
2. **Injected Side-to-Move Initiative Bias:**
   - In quiet equal positions, H1 adds an uncalibrated $+52\text{ cp}$ bias to the side to move.
   - Blending injects a $+26\text{ cp}$ phantom initiative into every node evaluation.
   - When Classical R1 would prune a quiet move due to a positional deficit, H2 treated the position as favorable, allowing unsound piece sacrifices and tactical blunders.

---

### 4. Methodological Corrections to Overstated P2.2 Claims

To maintain strict scientific integrity, Milestone P2.3 explicitly corrects five claims from Milestone P2.2 that overstated empirical observations:

1. **Quantization Correctness is Empirical, Not Universal:**
   - *P2.2 Claim:* Quantization is "flawless and 100% verified".
   - *P2.3 Correction:* Quantization parity was measured across a curated set of 500 test positions ($r = 0.999636$, MAE $6.50\text{ cp}$). While this confirms that the fixed-point scaling formulas work properly on typical game positions, it is a statistical validation over a sample, not a formal mathematical proof across all $10^{40}$ reachable chess positions.
2. **Incremental Accumulator Correctness Scope:**
   - *P2.2 Claim:* Accumulators are "100% bug-free for all chess moves".
   - *P2.3 Correction:* The audit validated 14,781 legal moves across 100 sample games with $\Delta = 0$. While this confirms correct implementation of quiet, capture, promotion, castling, and en passant logic along those specific game paths, rigorous engine qualification requires edge-case tests (e.g. triple check evasions, underpromotions, corner castlings).
3. **Draw Frequency is Not the Unique Cause of Score Compression:**
   - *P2.2 Claim:* The $49.5\%$ draw rate in the dataset caused score compression.
   - *P2.3 Correction:* While a high draw proportion pulls binary cross-entropy logits toward zero, the *primary* cause of centipawn scale compression was the absence of continuous centipawn teacher targets. Training purely on binary/trinary game outcomes ($z \in \{0, 0.5, 1\}$) maps win probabilities directly to unbounded centipawns via a naive multiplier, without grounding in classical alpha-beta evaluation scales.
4. **Dense Neural Expressiveness Limits:**
   - *P2.2 Claim:* Dense neural networks cannot learn king safety without king-relative features.
   - *P2.3 Correction:* In principle, a sufficiently deep and wide multi-layer perceptron with non-linear activations can approximate any continuous function, including king shelter interactions. The limitation in H1 was parameter capacity ($768 \to 128 \times 2 \to 32 \to 1$) and sample efficiency: a linear accumulator layer with only $128$ hidden units cannot discover bilinear king-pawn cross-terms from $40,000$ positions without explicit king-relative feature indexing (HalfKP).
5. **Accumulator Update Latency vs Total Evaluation Latency:**
   - *P2.2 Claim:* Incremental evaluation takes $0.11\ \mu\text{s}$.
   - *P2.3 Correction:* The $0.11\ \mu\text{s}$ timing measures *only* the sparse vector addition/subtraction in the first accumulator layer. The full neural forward pass requires evaluating the clipped linear activations, the $256 \to 32$ hidden layer, the $32 \to 1$ output layer, and the centipawn scale transformation, which in aggregate takes approximately $1.0$ to $1.5\ \mu\text{s}$.

---

### 5. Conclusion & Research Readiness

Phase 0 is complete. 
All historical baselines are verified. The P2.2 evidence is reconciled. 
The project now advances to **Phase 1: Formal Neural Score Contract**.
