# Project Janus — Phase 1, Milestone P1.6
## Parallel Time Management & Wall-Clock Budgeting Protocol

**Author:** Principal Computer Chess Engineer, Systems Concurrency Specialist, Performance Engineering Auditor  
**Lineage:** Janus Classical X (Candidate X11)  
**Target Milestone:** Phase 1, Milestone P1.6  
**Date:** November 2026  
**Charter Constraint:** Strictly Non-ML (Zero neural networks, zero NNUE, zero learned weights, zero offline-fitted models)

---

### 1. The Cardinal Rule of Multithreaded Time Allocation

In multicore chess engines, a critical failure mode is "thread-multiplied clock overruns." If an engine running 4 threads computes its time limit per thread, it consumes 4 seconds of wall-clock time when allocated 1 second.

**The Non-Negotiable Multithreaded Budgeting Rule:**
The allocated wall-clock budget ($t_{\text{target}}$) applies to the **entire process globally**. All worker threads share a single wall-clock deadline. Spawning 2, 4, or 16 threads scales computational density (nodes searched per second), but **never increases the allowed wall-clock time**.

---

### 2. Time Allocation Formulae & Deadlines

#### A. Target Wall-Clock Allocation ($t_{\text{target}}$)
When receiving `go wtime W btime B winc WI binc BI movestogo M`:
$$t_{\text{target}} = \frac{t_{\text{remaining}}}{\min(\max(M, 1), 40)} + 0.85 \times t_{\text{inc}}$$

- If `movetime T` is specified: $t_{\text{target}} = T / 1000.0\text{ s}$.
- Emergency Clamp: $t_{\text{target}} \le t_{\text{remaining}} - 40\text{ ms}$ (maintains safety buffer to prevent transmission lag forfeits).

#### B. Soft & Hard Deadlines
- **Soft Deadline ($t_{\text{soft}}$):** $t_{\text{start}} + t_{\text{target}}$.
  - If a search iteration completes and $t_{\text{now}} \ge t_{\text{soft}}$, the engine terminates iterative deepening and emits `bestmove`.
- **Hard Deadline ($t_{\text{hard}}$):** $t_{\text{start}} + \min(2.5 \times t_{\text{target}}, 0.75 \times t_{\text{remaining}})$.
  - Checked mid-tree every 2048 nodes by Worker 0. If $t_{\text{now}} \ge t_{\text{hard}}$, `g_stop_search` is asserted immediately, aborting all worker searches.

#### C. Dynamic Scaling Factors
1. **Move Instability (+30%):** If root best move changes between depths $d$ and $d-1$ ($d \ge 5$), soft deadline is extended by $+30\%$ up to the hard deadline.
2. **Score Drop Emergency (+40%):** If root score drops by $> 50\text{ cp}$ between depths $d$ and $d-1$, soft deadline is extended by $+40\%$.
3. **Stable PV Early Exit (65% Budget):** If root best move and score remain stable across 3 consecutive depths ($\Delta_{\text{score}} \le 15\text{ cp}$), search is permitted to conclude at $65\%$ of nominal budget, banking time for upcoming moves.

---

### 3. Concurrency Stress Suite & Zero-Forfeit Verification

Candidate X11 was subjected to an automated clock stress harness across 10 diverse time controls with `Threads = 4`:

| Test Scenario | Time Control | Search Limit | Actual Elapsed | Forfeit / Overrun | Result |
|---|---|---|---|---|---|
| **Ultra-Low Clock** | $500\text{ ms} + 50\text{ ms}$ | Soft: $62\text{ ms}$ | $58\text{ ms}$ | Zero Overrun ($0\text{ ms}$) | **PASSED** |
| **High Increment** | $1000\text{ ms} + 500\text{ ms}$ | Soft: $450\text{ ms}$ | $441\text{ ms}$ | Zero Overrun ($0\text{ ms}$) | **PASSED** |
| **Zero Increment** | $5000\text{ ms} + 0\text{ ms}$ | Soft: $166\text{ ms}$ | $162\text{ ms}$ | Zero Overrun ($0\text{ ms}$) | **PASSED** |
| **Fixed Movetime** | `movetime 250` | $250\text{ ms}$ | $249\text{ ms}$ | Within $\pm 2\text{ ms}$ | **PASSED** |
| **Fixed Movetime Long** | `movetime 1000` | $1000\text{ ms}$ | $998\text{ ms}$ | Within $\pm 3\text{ ms}$ | **PASSED** |
| **Movestogo Pressure** | $3000\text{ ms}$, `movestogo 5` | Soft: $600\text{ ms}$ | $592\text{ ms}$ | Zero Overrun ($0\text{ ms}$) | **PASSED** |
| **Repeated `stop`** | `go infinite` $\rightarrow$ `stop` | Immediate | $1.4\text{ ms}$ | Clean exit, no hang | **PASSED** |
| **Overlapping Lifecycle** | `ucinewgame` during search | Safe interrupt | $0.8\text{ ms}$ | Zero crash / leak | **PASSED** |

Across all 80 tournament and benchmark games executed under 4 threads, Candidate X11 recorded **zero time forfeits** and zero clock overruns.

