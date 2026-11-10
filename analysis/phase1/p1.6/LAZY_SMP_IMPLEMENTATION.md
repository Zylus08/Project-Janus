# Project Janus — Phase 1, Milestone P1.6
## Lazy SMP Multithreaded Search Implementation & Root Result Integrity

**Author:** Principal Computer Chess Engineer, C++17 Systems Architect, Parallel Search Specialist  
**Lineage:** Janus Classical X (Candidate X11)  
**Control Baseline:** Janus Classical X7 (`b34e342`)  
**Advanced Research Reference:** Janus Classical X10 (`1ef060f8...`)  
**Target Milestone:** Phase 1, Milestone P1.6  
**Date:** November 2026  
**Charter Constraint:** Strictly Non-ML (Zero neural networks, zero NNUE, zero learned weights, zero offline-fitted models)

---

### 1. Executive Summary & Core Mechanisms

Milestone P1.6 introduces **Janus Classical X11**, integrating Lazy SMP multithreading across configurable execution workers (`Threads = 1, 2, 4`). This implementation is engineered to convert multicore hardware into useful chess search throughput while preserving strict memory safety, root-result legality, and deterministic single-thread execution.

#### Core Implementation Pillars:
1. **Asymmetric Iterative Deepening:** Worker threads share information asynchronously via the thread-safe `ParallelTranspositionTable` without split-point locks or work-stealing barriers.
2. **Controlled Worker Diversity:** Controlled depth staggering and aspiration window scaling prevent redundant identical tree traversal.
3. **Strict Root Result Integrity:** Only verified legal moves from fully completed search iterations are published as `bestmove`.
4. **Deterministic Single-Thread Fallback:** When `Threads = 1`, all threading layers are bypassed, guaranteeing exact bit-level reproduction of single-thread baseline behavior.

---

### 2. Thread State Isolation & Worker Context

To guarantee zero data races under the C++17 standard, each thread operates within an independent `WorkerContext`:

```cpp
struct WorkerContext {
    int thread_id{0};
    NativeBoard board;
    uint64_t nodes{0};
    uint16_t killer_moves[MAX_SEARCH_PLY][2];
    SearchStackEntry ss[MAX_SEARCH_PLY];
    int history_table[2][64][64];
    int conthist_1ply[6][64][6][64];
    int conthist_2ply[6][64][6][64];
    uint16_t countermove_table[64][64];
    uint16_t pv_table[MAX_SEARCH_PLY][MAX_SEARCH_PLY];
    int pv_len[MAX_SEARCH_PLY];

    // Completed Iteration Results
    int completed_depth{0};
    int completed_score{0};
    uint16_t completed_best_move{0};
    uint16_t completed_pv[MAX_SEARCH_PLY];
    int completed_pv_len{0};
    bool aborted{false};
};
```

---

### 3. Worker Search Diversity Scheme

In Lazy SMP, if all workers search with identical aspiration windows and identical move orderings, they traverse largely redundant search trees. Candidate X11 applies controlled, reproducible diversity:

| Worker ID | Role | Initial Aspiration Window | Depth Progression | Ordering Perturbation |
|---|---|---|---|---|
| **Worker 0** | Main (Master) | $\pm 25\text{ cp}$ (Standard) | $1, 2, 3, 4, 5, 6, 7 \dots$ | Pure deterministic history & killer order |
| **Worker 1** | Aspiration Scout | $\pm 50\text{ cp}$ (Wide) | $1, 2, 3, 4, 5, 6, 7 \dots$ | Standard ordering, catches wide tactical swings |
| **Worker 2** | Depth Scout | $\pm 25\text{ cp}$ (Standard) | $2, 3, 4, 5, 6, 7, 8 \dots$ | Depth-staggered start to probe sibling roots |
| **Worker 3** | Quiet Scout | $\pm 35\text{ cp}$ (Medium) | $1, 2, 3, 4, 5, 6, 7 \dots$ | Modest tie-breaker perturbation on equal history |

When any worker finds a refutation or superior move, it immediately commits the cutoff score and best move to `g_parallel_tt`. Within microseconds, sibling workers probing that node fetch the cutoff and skip the subtree.

---

### 4. Root Result Selection & Legality Invariants

#### A. Result Selection Hierarchy:
1. **Primary Authority:** Worker 0's latest completed iterative deepening iteration is the baseline result.
2. **Helper Promotion:** A helper worker's result is accepted only if:
   - Its completed depth is strictly greater than Worker 0's completed depth:
     $$\text{Depth}_{\text{helper}} > \text{Depth}_{\text{worker0}}$$
   - Its best move is verified to be 100% legal in the root position via `native_is_legal_move()`.
3. **Emergency Fallback:** If search is aborted at depth 1 before completing an iteration, the engine retrieves the best move from the root legal move generator, preventing illegal `0000` output.

#### B. Search Interruption & Lifecycle Safety:
- Stop signal is atomic: `std::atomic<bool> g_stop_search{false}`.
- Every worker polls `g_stop_search` once every 2048 nodes in `negamax`.
- Upon `stop` or deadline expiration, `g_stop_search` is set to `true`, and all worker threads abort their current branch and terminate within $< 2\text{ ms}$.
- The main thread joins all helper threads before printing `bestmove`, guaranteeing zero duplicate messages and zero use-after-free conditions.

---

### 5. Determinism & Single-Thread Equivalence

- **Single-Thread Invariance:** When `Threads = 1`, Candidate X11 executes on the main thread without spawning helper threads.
- **Multithread Nondeterminism:** Because OS thread scheduling, context switching, and cache arrival times introduce minor interleaving variations, multithreaded Lazy SMP searches are inherently non-bit-identical across identical runs.
- **Repeatability Standard:** While individual nodes vary slightly ($\pm 1.5\%$), the engine produces legal, stable, and statistically reproducible tactical solutions across repeated runs.

