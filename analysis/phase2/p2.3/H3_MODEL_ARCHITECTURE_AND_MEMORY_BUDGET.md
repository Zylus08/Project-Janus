# Project Janus — Phase 2, Milestone P2.3
## Phase 3: H3 Model Architecture & Memory Budget Specification

**Author:** Principal Computer Chess Researcher, Deep Learning Systems Engineer & Performance Architect  
**Milestone:** P2.3 — King-Relative NNUE, Search-Grounded Neural Training, Incremental CPU Inference & Independent Playing-Strength Qualification  
**Date:** 2026-11-17  
**Subject:** HalfKP Topology Selection, Parameter Sharing Formulation & Hardware Cache Allocation  

---

### 1. Topology Selection (Candidate N1)

To overcome the expressiveness limitations of H1's DP-PS-768 schema while maintaining high CPU inference throughput, Candidate **N1** is selected:

$$\textbf{Input Features: } 40,960 \longrightarrow \textbf{Accumulator: } 128 \times 2 \longrightarrow \textbf{Hidden Layer: } 32 \longrightarrow \textbf{Output: } 1$$

```
========================================================================================================================
TOPOLOGY SPECIFICATION & PARAMETER BUDGET
========================================================================================================================
Layer Component          | Input Dim | Output Dim | Weights Count | Biases Count | Quantization | Footprint
-------------------------+-----------+------------+---------------+--------------+--------------+-----------------------
Feature Transformer (FT) | 40,960    | 128        | 5,242,880     | 128          | INT16        | 10,486,016 bytes (10.0 MB)
Hidden Dense Layer 1     | 256       | 32         | 8,192         | 32           | INT8 / INT32 | 8,320 bytes (8.1 KB)
Output Dense Layer 2     | 32        | 1          | 32            | 1            | INT8 / INT32 | 36 bytes
Binary Header & Metadata | -         | -          | -             | -            | Raw binary   | 64 bytes
-------------------------+-----------+------------+---------------+--------------+--------------+-----------------------
TOTAL PARAMETERS         | -         | -          | 5,251,104     | 161          | -            | 5,251,265 parameters
TOTAL BINARY FILE SIZE   | -         | -          | -             | -            | -            | 10,494,436 bytes (10.01 MB)
========================================================================================================================
```

---

### 2. Symmetrical Parameter Sharing

A naive two-perspective HalfKP network without parameter sharing would require two distinct weight matrices of shape $40,960 \times 128$, ballooning model storage to $> 20.97\text{ MB}$.

Under Candidate N1's formulation:
- Coordinate mapping mirrors the rank and switches friendly/enemy indices between perspectives.
- Both the White accumulator and Black accumulator evaluate through the **identical shared weight matrix** $W_{\text{ft}} \in \mathbb{R}^{40960 \times 128}$ and shared bias vector $b_{\text{ft}} \in \mathbb{R}^{128}$.
- Parameter storage is reduced by exactly **50.0%**, cutting memory bandwidth demands in half.

---

### 3. CPU Cache Hierarchy & Runtime Search Stack Footprint

```
========================================================================================================================
CACHE HIERARCHY RESIDENCY ANALYSIS
========================================================================================================================
Storage Domain           | Size per Thread / Process | Target CPU Cache Level      | Cache Residency Behavior
-------------------------+---------------------------+-----------------------------+------------------------------------
Single Ply Accumulator   | 512 bytes (128x2 int16)   | L1 Data Cache (32KB - 48KB) | 100% L1 resident across active ply
Search Stack (128 plies) | 65,536 bytes (64.0 KB)    | L2 Cache (512KB - 1024KB)   | Fits entirely in dedicated L2
Dense Layer Weights      | 8,356 bytes (8.2 KB)      | L1 Instruction / Data Cache | Permanent L1 residency
Feature Transformer W_ft | 10,486,016 bytes (10.0 MB)| L3 Unified Cache (16MB-32MB)| 100% resident in shared L3 cache
========================================================================================================================
```

By ensuring the entire model ($10.01\text{ MB}$) fits within standard CPU L3 cache, main memory DRAM bus traffic is completely avoided during search leaf evaluations.

---

### 4. Comparison with Alternatives

- **N0 (Frozen H1 DP-PS-768):** $106,689$ parameters ($208\text{ KB}$). Zero king conditioning; cannot learn king shelter or open file threats.
- **N1 (HalfKP-40960 128x2 -> 32 -> 1):** $5,251,265$ parameters ($10.01\text{ MB}$). Full king-piece conditioning; fits in L3 cache; $64\text{ KB}$ search stack. **(CHOSEN DESIGN)**
- **N2 (HalfKP-40960 256x2 -> 32 -> 1):** $10.5\text{M}$ parameters ($21.0\text{ MB}$). Exceeds L3 cache capacity on typical consumer architectures; increases memory latency without verified positional justification.

Phase 3 is complete. Milestone P2.3 now advances to **Phase 4: Data Quality Pilot**.
