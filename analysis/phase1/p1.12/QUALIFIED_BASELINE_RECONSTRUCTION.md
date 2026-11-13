# Qualified Classical Baseline Reconstruction & Certification

## 1. Executive Summary & Dual-Track Baseline Architecture

To permanently resolve the architectural confusion arising from conflating single-threaded efficiency and parallel search mechanics, Milestone P1.12 formally decouples Project Janus into two isolated, certified development baselines:

- **Track S — Single-Thread Qualified Baseline:** **Janus Classical X7** (Commit `b34e342`)
- **Track P — Four-Thread Qualified Baseline:** **Janus Classical X12** (Commit `78ca3d5`)

Neither track relies on reverse-engineering or feature-flag ablations of Candidate X16. Both baselines have been independently reconstructed from their exact commit sources, certified against standard test suites, and archived in dedicated experimental roots.

---

## 2. Track S: Janus Classical X7 Certification (Single-Thread)

### 2.1 Cryptographic & Systems Specification
- **Engine Identity:** Janus Classical X7 (Commit `b34e342`)
- **Dedicated Source Path:** `analysis/phase1/p1.12/baseline/track_s_x7/janus_classical_x7.cpp`
- **Frozen Binary Path:** `analysis/phase1/p1.3/control/janus_classical_x7.exe`
- **Source SHA-256:** `02f7c3f3b21a3cd77a37080128006ac736708f4f457aaa61dbe6e00fa61815f3`
- **Executable SHA-256:** `86392a2f4bd4182a4d7dc21e32940bd7939f6816794d5e1ab02f4082431ca28b`
- **Binary Size:** 370,176 bytes
- **Compiler:** Microsoft (R) C/C++ Optimizing Compiler Version 19.43.34809 for x64
- **Compilation Flags:** `/O2 /Ot /Oi /std:c++17 /EHsc`
- **CPU Architecture:** AMD64 / AVX2 / BMI2
- **Thread Architecture:** Dedicated single-thread execution (`g_num_threads = 1`), zero thread synchronization or lock primitives.
- **Transposition Table:** 128MB linear direct-mapped transposition table.
- **Evaluation Engine:** Lean Classical Evaluation E5 (handcrafted material + piece-square tables, pawn structure, king safety).
- **Search Pipeline:** Staged movegen, Quiescence SEE (Q2), Reverse Futility Pruning (margin $120\times d$), Null Move Pruning ($R=3$), static Late Move Reductions ($R=1$ on move count $\ge 4$). Zero search-stack evaluation tracking overhead.

### 2.2 Standard Benchmark Performance (Track S)
Measured via `test_baselines_certification.py` on AMD64 Windows:

| Benchmark Position | FEN | Depth 7 (Nodes / NPS / Move) | Depth 8 (Nodes / NPS / Move) | Movetime 100ms (Depth / Move) | Movetime 250ms (Depth / Move) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **STARTPOS** | `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1` | 52,122 / 1.95M / `d2d4` | 157,778 / 1.83M / `b1c3` | Depth 8 / `b1c3` (184K) | Depth 10 / `e2e4` (448K) |
| **KIWIPETE** | `r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1` | 247,595 / 1.19M / `e2a6` | 362,809 / 1.11M / `e2a6` | Depth 6 / `d5e6` (122K) | Depth 7 / `e2a6` (292K) |
| **TACTICAL_01**| `r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4` | 161,079 / 2.74M / `h5f7` | 349,324 / 2.55M / `h5f7` | Depth 7 / `h5f7` (161K) | Depth 8 / `h5f7` (349K) |
| **ENDGAME_01** | `8/8/4k3/3p4/3P4/4K3/8/8 w - - 0 1` | 13,010 / 0.77M / `e3f4` | 44,792 / 0.81M / `e3f4` | Depth 8 / `e3f4` (44K) | Depth 11 / `e3f4` (278K) |

---

## 3. Track P: Janus Classical X12 Certification (Four-Thread SMP)

### 3.1 Cryptographic & Systems Specification
- **Engine Identity:** Janus Classical X12 (Commit `78ca3d5`)
- **Dedicated Source Path:** `analysis/phase1/p1.12/baseline/track_p_x12/janus_classical_x12.cpp`
- **Frozen Binary Path:** `analysis/phase1/p1.7/control/janus_classical_x12.exe`
- **Source SHA-256:** `279ac4ea279b68b2ec50e7c2421e5542fcd8cb70231fb88760ab9828598510b7`
- **Executable SHA-256:** `00b4f5fedea02a392a1af9713a96512e5199a0e3ae55c295ad1c7cfff1b47059`
- **Binary Size:** 2,874,368 bytes
- **Compiler:** Microsoft (R) C/C++ Optimizing Compiler Version 19.43.34809 for x64
- **Compilation Flags:** `/O2 /Ot /Oi /std:c++17 /EHsc`
- **Thread Topology:** 4 Lazy SMP worker threads, shared lockless transposition table.
- **Transposition Table:** 64-byte cacheline-packed cluster design (`alignas(64)`: 3 entries $\times$ 16B + 4B atomic flag + 12B pad = 64B), eliminating false sharing across cores. Depth-preferred replacement policy.
- **Evaluation Engine:** Enhanced Classical Evaluation E10 (mobility, bishop pair, rook on open files, king danger zones).
- **Search Ordering & Cache:** M2 Countermove heuristic, 64K-entry shared pawn hash table, authoritative master root arbitration.

### 3.2 Standard Benchmark Performance (Track P)
Measured via `test_baselines_certification.py` on AMD64 Windows (4 threads):

| Benchmark Position | FEN | Depth 7 (Nodes / NPS / Move) | Depth 8 (Nodes / NPS / Move) | Movetime 100ms (Depth / Move) | Movetime 250ms (Depth / Move) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **STARTPOS** | `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1` | 94,376 / 4.84M / `b1c3` | 283,543 / 5.48M / `b1c3` | Depth 7 / `g1f3` (161K) | Depth 11 / `e2e4` (1.33M) |
| **KIWIPETE** | `r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1` | 1,029,457 / 4.18M / `d5e6` | 1,402,945 / 3.76M / `e2a6` | Depth 6 / `e2a6` (118K) | Depth 7 / `d5e6` (1.04M) |
| **TACTICAL_01**| `r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4` | 596,427 / 7.90M / `h5f7` | 1,312,799 / 7.27M / `h5f7` | Depth 6 / `h5f7` (143K) | Depth 7 / `h5f7` (680K) |
| **ENDGAME_01** | `8/8/4k3/3p4/3P4/4K3/8/8 w - - 0 1` | 42,912 / 1.70M / `e3f4` | 145,216 / 1.76M / `e3f4` | Depth 8 / `e3f4` (64K) | Depth 11 / `e3f4` (611K) |

---

## 4. Architectural Separation Guarantee

1. **No Shared Code Bloat:** Track S does not include SMP coordination threads, mutexes, or cacheline padding. Track P does not execute single-threaded fallback code during parallel searches.
2. **Preservation Invariant:** The frozen binaries `janus_classical_x7.exe` and `janus_classical_x12.exe` are read-only and cryptographically verified.
3. **Qualification Starting Point:** Any prospective candidate X17-S must branch strictly from Track S (`janus_classical_x7.cpp`). Any prospective candidate X17-P must branch strictly from Track P (`janus_classical_x12.cpp`).

