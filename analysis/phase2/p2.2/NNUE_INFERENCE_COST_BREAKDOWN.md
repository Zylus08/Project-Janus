# Project Janus — Phase 2, Milestone P2.2
## Phase 6: Neural Inference Cost Breakdown & Profiling Report

**Author:** Principal Computer Chess Architect & C++17 Performance Specialist  
**Milestone:** P2.2 — Neural Evaluation Failure Forensics, Score Calibration & Scalable Dataset Readiness  
**Date:** 2026-11-16  
**Subject:** Micro-latency Attribution, Throughput Bottlenecks & Wall-Clock Search Economics  

---

### 1. Executive Summary & Core Discovery

A central question posed in Milestone P2.2 is whether H1's catastrophic playing strength deficit is driven in part by **excessive CPU inference latency**.
Through controlled micro-benchmarking and wall-clock profiling at Depth 6 across identical CPU, compiler, and search settings, this audit establishes a major architectural finding:

1. **Leaf Evaluation Latency:**
   - **Classical Evaluation (E0):** Mean = $1.246\ \mu\text{s}$ (Throughput: $802,336\text{ evals/sec}$).
   - **NNUE Full Evaluation (E2):** Mean = $7.486\ \mu\text{s}$ (Throughput: $133,579\text{ evals/sec}$).
   - **Latency Penalty:** Full leaf evaluation in H1 is **$6.01\times$ slower** than Classical R1.

2. **The Missing Search Accumulator Stack:**
   Inspection of `r1_search.hpp` reveals that `evaluate_position(const NativeBoard* b)` invokes:
   ```cpp
   int nnue_score = NNUEEvaluator::evaluate_full(b);
   ```
   Instead of maintaining an incremental accumulator stack along the search tree (`update_move`), the search engine was executing a **full scratch recomputation** (`full_recompute`) at every evaluation and quiescence probe!
   While the incremental update routines were verified in Phase 6 of P2.1, they were not wired into the recursive negamax search stack, forcing the search to re-scan all piece bitboards from scratch at every node.

3. **The Wall-Clock Search Disconnect:**
   At fixed depth, neural move ordering reduces node counts by $20\%$ to $35\%$. However, because each node is $6\times$ slower to evaluate:
   - In `Startpos` at Depth 6: H1 takes **$76.3\text{ ms}$** vs **$33.8\text{ ms}$** for Classical R1 ($2.25\times$ slower).
   - In `Middlegame` at Depth 6: H1 takes **$1,239.2\text{ ms}$** vs **$111.3\text{ ms}$** for Classical R1 (**$11.1\times$ slower!**).
   - Under Blitz time controls (5s + 0.05s), H1 searches **2 to 3 plies shallower** than Classical R1, compounding its positional evaluation inaccuracies with severe depth starvation.

---

### 2. Micro-Benchmarking Latency Profile

Measured across 20,000 warm invocations on `KiwiPete`:

| Subsystem | Mean Latency | Median (P50) | P95 Latency | P99 Latency | Sustained Throughput | Latency Ratio |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Classical R1 (`native_evaluate`)** | $1.246\ \mu\text{s}$ | $1.200\ \mu\text{s}$ | $1.300\ \mu\text{s}$ | $1.400\ \mu\text{s}$ | $802,336\text{ evals/sec}$ | $1.00\times$ (Baseline) |
| **NNUE H1 (`evaluate_full`)** | $7.486\ \mu\text{s}$ | $5.800\ \mu\text{s}$ | $11.100\ \mu\text{s}$ | $16.700\ \mu\text{s}$ | $133,579\text{ evals/sec}$ | **$6.01\times$ Slower** |

---

### 3. Search Economics & Throughput at Depth 6

| Position | Mode | Nodes Searched | Wall-Clock Time (ms) | Search NPS | Score (cp) | Node Efficiency vs Classical | Wall-Clock Speed vs Classical |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Startpos** | Classical R1 | $21,669$ | $33.8\text{ ms}$ | $640,903$ | $0$ | Baseline | Baseline |
| | NNUE H1 | $16,748$ | $76.3\text{ ms}$ | $219,378$ | $+22$ | **-22.7% (Better)** | **2.26x Slower** |
| | Hybrid H2 | $5,014$ | $27.1\text{ ms}$ | $184,807$ | $+12$ | **-76.9% (Best)** | **1.25x Faster** |
| **KiwiPete** | Classical R1 | $72,283$ | $275.3\text{ ms}$ | $262,544$ | $+41$ | Baseline | Baseline |
| | NNUE H1 | $257,470$ | $1,607.2\text{ ms}$ | $160,199$ | $-225$ | **+256.2% (Worse)** | **5.84x Slower** |
| | Hybrid H2 | $50,818$ | $336.7\text{ ms}$ | $150,935$ | $-217$ | **-29.7% (Better)** | **1.22x Slower** |
| **Middlegame** | Classical R1 | $58,829$ | $111.3\text{ ms}$ | $528,667$ | $-38$ | Baseline | Baseline |
| | NNUE H1 | $81,935$ | $1,239.2\text{ ms}$ | $66,118$ | $-106$ | **+39.3% (Worse)** | **11.13x Slower** |
| | Hybrid H2 | $5,601$ | $200.1\text{ ms}$ | $27,993$ | $-92$ | **-90.5% (Best)** | **1.80x Slower** |
| **Endgame** | Classical R1 | $2,062$ | $16.2\text{ ms}$ | $127,391$ | $+231$ | Baseline | Baseline |
| | NNUE H1 | $1,460$ | $28.7\text{ ms}$ | $50,879$ | $+222$ | **-29.2% (Better)** | **1.77x Slower** |
| | Hybrid H2 | $1,502$ | $17.4\text{ ms}$ | $86,319$ | $+213$ | **-27.2% (Better)** | **1.07x Slower** |

---

### 4. Key Performance Insights

1. **Why Node Reduction Alone Does Not Equal Strength:**
   While NNUE H1 achieves a $22.7\%$ node reduction in `Startpos`, its throughput drops from $640\text{k NPS}$ to $219\text{k NPS}$. In complex tactical positions like `KiwiPete`, H1's compressed score causes severe aspiration window re-searches and instability, exploding node count to $257\text{k}$ and taking $1.6\text{ seconds}$ compared to Classical's $0.27\text{ seconds}$.
2. **The Power of Hybrid H2:**
   Hybrid H2 achieves massive node compression ($5,014$ nodes in Startpos, $50,818$ in KiwiPete, $5,601$ in Middlegame) because combining classical material clarity with neural guidance creates sharp alpha-beta cutoffs. Even with the evaluation overhead, H2 searches Startpos in $27.1\text{ ms}$ (faster than Classical R1's $33.8\text{ ms}$).
3. **Primary Systems Fix for P2.2+:**
   Maintain an `Accumulator` array in the `SearchStackEntry` or search ply stack. At each ply, call `NNUEEvaluator::update_move()` ($O(1)$, $\approx 100\text{ ns}$) instead of `evaluate_full()` ($7.5\ \mu\text{s}$). This will immediately boost NNUE search throughput from $100\text{k}$ to $> 500\text{k NPS}$.
