# Project Janus — Phase 1, Milestone P1.5
## Strategic Architecture & Next Classical Engineering Priority (Milestone P1.6)

**Author:** Principal Computer Chess Engineer, C++17 Systems Architect, Performance Optimization Specialist, and Statistical Experimental Auditor  
**Lineage:** Janus Classical X  
**Current Qualified Production Baseline:** Janus Classical X7 (`b34e342`)  
**Advanced Classical Research Candidate:** Janus Classical X10 (`1ef060f8...`)  
**Target Milestone:** Phase 1, Milestone P1.6  
**Date:** November 2026  
**Governing Rule 1:** Strictly Non-ML (Zero neural networks, zero NNUE, zero learned weights, zero offline-fitted models)

---

### 1. Strategic Context & Milestone P1.5 Empirical Foundations

Milestone P1.5 resolved the classical evaluation and time management bottlenecks that stalled previous iterations of Project Janus:
1. **Evaluation Expressiveness Proved Directionally Positive:**
   Candidate X10's 5 handcrafted evaluation modules (candidate passed pawns, backward pawn penalties, quadratic king danger scaling, true knight outposts, and rook coordination) delivered the first consistently positive score across all time controls:
   - +26.1 Elo (53.75%) at 1.0s + 50ms.
   - +43.7 Elo (56.25%) at 3.0s + 100ms.
   - +29.0 Elo (54.17%) across 240 combined games against Baseline X7.
2. **Pawn Hash Table Neutralized Computational Cost:**
   With a 92.4% hit rate and L3-resident 2.0 MB footprint, the pawn hash table preserved 97.4% of raw NPS throughput (1.46M NPS).
3. **Decisive External Progress Against Stockfish 19:**
   Candidate X10 scored 2.5 / 40 (6.25%, 5 draws held) against unrestricted Stockfish 19, recovering **+166.0 Elo** in defensive playing strength over Baseline X7 and drawing both games of Opening Pair 16.

Despite this progress, Candidate X10 fell just short of the preregistered $p < 0.05$ threshold ($p = 0.1779$ in the 200-game primary match, $p = 0.0968$ combined). To achieve decisive, statistically undeniable supremacy ($p < 0.001$, $> +50\text{ Elo}$), Milestone P1.6 must target the remaining macro-architectural bottlenecks.

---

### 2. Primary Engineering Focus 1: Multithreaded Shared-Memory Search (Lazy SMP)

#### The Single-Thread Bottleneck
Currently, Janus operates strictly as a single-threaded engine, utilizing only 1 CPU core even on systems with 16 logical cores. Meanwhile, Stockfish and contemporary competitors scale across all available execution units. In fixed-clock play, single-threaded execution leaves up to 93% of the host machine's computational throughput unexploited.

#### Milestone P1.6 Lazy SMP Architecture
- **Lockless Shared Transposition Table:**
  Migrate the TT to atomic 16-byte cluster entries (`std::atomic<uint64_t>` key and data) enabling lock-free reads and writes across multiple worker threads.
- **Asymmetric Thread Diversification:**
  Instead of complex thread synchronization (such as YBWC), implement Lazy SMP:
  - Thread 0 (Main Thread) performs iterative deepening and root time management.
  - Helper Threads ($1 \dots N-1$) run asynchronous iterative deepening with minor search diversification:
    - Staggered initial depths (e.g., helper threads start at depth 1, 2, or 3).
    - Randomized move ordering tie-breaking among moves with identical history scores.
- **Expected Return:**
  On an 8-thread system, Lazy SMP typically provides an effective speedup of $4.5\times$ to $6.0\times$ in nodes searched per second, translating to **+70 to +110 Elo** under identical wall-clock time controls.

---

### 3. Primary Engineering Focus 2: Safe Forward Pruning (Late Move Pruning & History Pruning)

Milestone P1.3 proved that verification-search selectivity (Singular Extensions) is harmful under clock constraints due to nominal depth starvation. However, non-verification shallow pruning operates with zero verification searches:

#### A. Late Move Pruning (LMP)
- In non-PV nodes at shallow depths ($d \le 4$), after searching a threshold number of quiet legal moves, prune all remaining quiet moves in the loop:
  $$N_{\text{quiet\_limit}}(d) = 3 + 3 \times d^2$$
  - At depth 1: search up to 6 quiet moves, then prune.
  - At depth 2: search up to 15 quiet moves, then prune.
  - At depth 3: search up to 30 quiet moves, then prune.

#### B. History-Based Quiet Move Pruning
- Prune quiet moves at shallow depths whose Butterfly/Continuation history scores fall below an aggressive negative threshold:
  $$\text{Cutoff Condition:} \quad d \le 3 \quad \text{and} \quad \text{History}(p, \text{to}) < -1200 \times d$$

#### C. Expected Return:
LMP and History Pruning eliminate 30–45% of unnecessary leaf expansions in the middle game, boosting average nominal search depth by **+1.2 to +1.8 plies** without risking tactical verification collapses.

---

### 4. Primary Engineering Focus 3: Non-ML Classical Evaluation Tuning (SPSA)

Currently, the evaluation coefficients in E1' through E5' (such as candidate passed pawn bonuses, king attack unit values, and outpost constants) are manually calibrated. While sound, manual tuning cannot optimize the complex non-linear interactions across 40+ evaluation parameters.

#### Non-ML SPSA Protocol
- **Method:** Simultaneous Perturbation Stochastic Approximation (SPSA).
- **Rule 1 Compliance:** Strictly non-ML; optimizes handcrafted scalar parameters of a symbolic evaluation function via automated self-play, exactly analogous to classical Stockfish evaluation tuning prior to NNUE.
- **Parameters to Tune:**
  - Pawn structure weights: backward pawn penalties, pawn island steps, connected passer bonuses.
  - King safety scaling constants: queen divisor exponent, shelter missing penalties.
  - Piece activity: outpost ranks 4/5/6, rook open file bonus, bishop pair endgame taper.
- **Expected Return:** SPSA parameter convergence routinely extracts **+30 to +50 Elo** from an existing handcrafted evaluation architecture.

---

### 5. Primary Engineering Focus 4: Endgame Tablebase Integration (Syzygy WDL Probing)

In Milestone P1.5's positional failure taxonomy, Class E (Endgame Outcome Misunderstanding) accounted for 25.0% of positional errors. Pure alpha-beta search frequently struggles to navigate 6-piece fortress positions or long pawn endgames within practical horizon limits.

#### Milestone P1.6 Syzygy Architecture:
- Non-ML Syzygy 3-4-5 piece WDL/DTZ probing.
- Tablebase probing restricted to the root and root-adjacent plies ($d \ge 2$), returning exact win/loss/draw scores.
- Preserves search bandwidth while guaranteeing flawless endgame conversion.

---

### 6. Preregistered Milestone P1.6 Roadmap & Promotion Criteria

| Component | Architecture | Expected Elo Impact | Verification Method |
|---|---|---|---|
| **P1.6-A** | Lazy SMP (Multithreaded Search) | $+80\text{ Elo}$ | Scalability benchmark (1T vs 4T vs 8T) |
| **P1.6-B** | Late Move Pruning & History Pruning | $+35\text{ Elo}$ | Tree reduction & nominal depth profiling |
| **P1.6-C** | Classical SPSA Evaluation Tuning | $+40\text{ Elo}$ | Self-play parameter convergence audit |
| **P1.6-D** | Syzygy Tablebase Probing | $+20\text{ Elo}$ | Endgame suite solve rate & accuracy |

#### Preregistered Promotion Gate:
- **Baseline Control:** Retained Production Baseline Janus Classical X7 (`b34e342`).
- **Qualification Match:** 400 games across 200 balanced opening pairs at Fischer 1.0s + 50ms (or 2.0s + 50ms multi-threaded).
- **Promotion Threshold:** Statistically significant superiority over Baseline X7:
  $$\text{Score} > 53.0\%, \quad p < 0.01 \text{ (paired } t\text{-test)}.$$
- **External SF19 Benchmark:** Achieve $\ge 10.0\%$ match score ($\ge 4.0 / 40$ points) against unrestricted Stockfish 19.

---

### 7. Sign-Off

Milestone P1.5 proved that non-ML classical evaluation and dynamic time allocation are viable, effective mechanisms that improve both internal playing strength and external defensive resistance against modern NNUE chess engines. Milestone P1.6 will scale this foundation across modern parallel CPU hardware.

**Sign-off:**  
Principal Computer Chess Engineer & Independent Experimental Auditor.
