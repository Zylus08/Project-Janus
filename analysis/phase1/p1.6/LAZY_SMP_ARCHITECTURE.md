# Project Janus — Phase 1, Milestone P1.6
## Lazy SMP Parallel Search Architecture Specification

**Author:** Principal Computer Chess Engineer, C++17 Concurrency Architect, Systems Performance Specialist  
**Lineage:** Janus Classical X (Candidate X11)  
**Control Baseline:** Janus Classical X7 (`b34e342`)  
**Advanced Research Reference:** Janus Classical X10 (`1ef060f8...`)  
**Target Milestone:** Phase 1, Milestone P1.6  
**Date:** November 2026  
**Charter Constraint:** Strictly Non-ML (Zero neural networks, zero NNUE, zero learned weights, zero offline-fitted models)

---

### 1. Architectural Motivation & Concurrency Strategy

In Milestone P1.5, Janus demonstrated competitive classical playing strength on a single thread (+26.1 Elo vs X7 at 1s, +43.7 Elo at 3s, and 5 draws held against unrestricted Stockfish 19). However, modern computer chess is executed on multicore architectures. Running single-threaded on a 16-logical-core processor leaves over 90% of available CPU computing throughput idle.

#### Why Lazy SMP Over YBWC or Split-Point Search?
1. **Young Brothers Wait Concept (YBWC) & Distributed Search Drawbacks:**
   - Requires heavy thread synchronization at split points in the alpha-beta tree.
   - Imposes significant thread idle wait time, complex work-stealing queues, and high synchronization overhead on modern NUMA and multi-core systems.
   - Vulnerable to race conditions and deadlocks during search aborts.
2. **Lazy SMP Advantages:**
   - **Zero Synchronous Communication:** Worker threads never wait for each other at tree split points.
   - **Shared Transposition Table as Implicit Communication Medium:** When Worker $A$ evaluates a branch and stores a cutoff score or best move in the shared TT, Worker $B$ immediately accesses this entry upon reaching the same transposition, causing an instantaneous cutoff or accelerating move ordering.
   - **Deterministic Fallback:** When `Threads = 1`, the architecture collapses to standard single-threaded iterative deepening with zero synchronization penalty.

---

### 2. High-Level System Architecture

```
+-----------------------------------------------------------------------------------+
|                                 MAIN UCI THREAD                                   |
|   - UCI Command Parser (uci, isready, setoption, position, go, stop, quit)       |
|   - Master Time Allocator (movestogo, soft/hard deadlines, instability scaling)   |
|   - ThreadPool Life-Cycle Controller (thread creation, synchronization, shutdown) |
|   - Final Result Selection & Bestmove Publisher                                   |
+-----------------------------------------------------------------------------------+
                                         |
                +------------------------+------------------------+
                |                                                 |
                v                                                 v
   +--------------------------+                      +--------------------------+
   |   WORKER 0 (MASTER)      |                      |  WORKER 1..N-1 (HELPERS) |
   | - Local Board & History  |                      | - Local Board & History  |
   | - Local Search Stack     |                      | - Local Search Stack     |
   | - Local Killers & Hist   |                      | - Local Killers & Hist   |
   | - Iterative Deepening    |                      | - Iterative Deepening    |
   | - Primary PV Collection  |                      | - Diversified Aspiration |
   +--------------------------+                      +--------------------------+
                |                                                 |
                +------------------------+------------------------+
                                         |
                                         v
   +--------------------------------------------------------------------------------+
   |                     SHARED THREAD-SAFE TRANSPOSITION TABLE                     |
   |   - 262,144 Lock-Striped 4-Entry Clusters (1,048,576 Total Entries, 32 MB)     |
   |   - Spinlock Protected Clusters: std::atomic_flag with _mm_pause()             |
   |   - 4-Way Associative Replacement (Exact match / Old age / Lowest depth)       |
   |   - Atomic Search Stop Flag: std::atomic<bool> g_stop_search                   |
   |   - Global Search Epoch: std::atomic<uint8_t> g_tt_age                         |
   +--------------------------------------------------------------------------------+
```

---

### 3. Detailed Component Specifications

#### A. Master Thread
- **Thread ID:** 0 (Main Execution Thread).
- **Responsibilities:**
  - Manages standard input/output streams and non-blocking line reading.
  - Computes search clock limits (`wtime`, `btime`, `winc`, `binc`, `movestogo`, `movetime`).
  - Broadcasts root search parameters to all worker threads via a thread pool condition variable.
  - Monitors the master wall-clock deadline; checks periodically (every 2048 nodes in Worker 0).
  - Broadcasts `g_stop_search = true` when deadline is reached or upon receiving `stop` / `quit`.
  - Aggregates node counts across all active workers:
    $$\text{Nodes}_{\text{total}} = \sum_{i=0}^{N-1} \text{Worker}_i.\text{nodes}$$
  - Selects the final `bestmove` and emits the UCI `bestmove` token.

#### B. Worker Threads (1 to $N-1$)
- **Local State Isolation:**
  To guarantee complete absence of data races, each worker thread maintains fully independent memory structures:
  - `NativeBoard local_board`: Deep-copied from the root board state.
  - `SearchStackEntry local_ss[MAX_SEARCH_PLY]`: Ply-by-ply move and piece tracker.
  - `uint16_t local_killers[MAX_SEARCH_PLY][2]`: Two killer move slots per ply.
  - `int local_history[2][64][64]`: Butterfly history heuristic table.
  - `int local_conthist_1ply[6][64][6][64]`: 1-ply continuation history.
  - `int local_conthist_2ply[6][64][6][64]`: 2-ply continuation history.
  - `uint16_t local_countermoves[64][64]`: Countermove table.
  - `uint16_t local_pv_table[MAX_SEARCH_PLY][MAX_SEARCH_PLY]`: Triangular PV table.
- **Worker Search Execution:**
  Workers run continuous iterative deepening starting from depth 1 until `g_stop_search` is asserted.

#### C. Asymmetric Worker Diversity
To prevent helper threads from searching identical branches and duplicating work:
1. **Worker 0 (Main):** Baseline aspiration windows ($\pm 25\text{ cp}$), standard depth progression ($1, 2, 3, 4, 5 \dots$).
2. **Worker 1:** Slightly wider initial aspiration window ($\pm 50\text{ cp}$) to catch extreme score swings early.
3. **Worker 2:** Depth-staggered start (searches depth 1 twice or starts at depth 2) to explore sibling root moves.
4. **Worker 3:** Modest move ordering tie-break perturbation among quiet moves with equal history scores.

---

### 4. UCI Interface & Configuration

The engine exposes standard UCI options for thread configuration:

```
option name Threads type spin default 1 min 1 max 16
```

- When `Threads = 1`: No background worker threads are dispatched. The search executes entirely in the main thread with zero concurrency overhead.
- When `Threads = 2`: 1 main thread + 1 helper thread.
- When `Threads = 4`: 1 main thread + 3 helper threads.

Worker threads are allocated and pooled upon receiving `setoption name Threads value N` or `isready`, preventing thread spawn latency during the `go` command.

---

### 5. Memory Model & Concurrency Guarantees

1. **Zero Data Races:** All shared writes and reads pass through explicit atomic synchronization primitives (`std::atomic_flag`, `std::atomic<bool>`, `std::memory_order_acquire`, `std::memory_order_release`).
2. **Zero Deadlocks:** Worker threads only lock single TT clusters with bounded spinlocks. No nested locks are permitted.
3. **Safe Interruption:** Checking `g_stop_search.load(std::memory_order_relaxed)` every 2048 nodes ensures immediate termination upon `stop` or time expiration within $< 2\text{ ms}$.

