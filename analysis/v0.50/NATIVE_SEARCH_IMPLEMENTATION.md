# Project Janus v0.50 — Native Search Architecture & Implementation

## 1. Executive Summary

Project Janus v0.50 establishes **N2**, the first-generation C++17 native search-core prototype. In prior milestones (v0.46–v0.49), profiling demonstrated that Python-level search orchestration was the dominating bottleneck:
- Eager move sorting absorbed ~7.4% of total search time (v0.46).
- Python-level incremental selection wrappers added ~16.9% overhead (v0.48).
- Calling native C DLLs for small subroutines (fine-grained FFI) regressed overall search time by +6.66% due to ctypes marshalling overhead (v0.49).

The N2 search prototype eliminates CPython orchestration overhead by moving the entire search tree traversal, move generation, static evaluation, move ordering, and transposition table into a compiled 64-bit native library (`janus_native.dll`). Python serves as the high-level orchestration, harness, and validation interface.

---

## 2. Search Architecture Overview

### 2.1 Component Breakdown

The native search engine is structured into five cohesive subsystems:
1. **Bitboard Board Representation (`NativeBoard`)**:
   - 64-bit piece occupancy (`pieces[2][6]` and `occupancy[3]`).
   - Compact 8-bit state metadata (`side_to_move`, `castling_rights`, `ep_square`).
   - Incremental 64-bit Zobrist hashing (`zobrist_key`).
   - Reversible undo mechanism via `UndoInfo` struct (zero memory allocation during make/unmake).
2. **Move Generation Engine**:
   - Precomputed attack tables for pawns, knights, and kings.
   - Magics-free hyperbola / ray-cast sliding attacks with 64-bit popcount and bitscan primitives (`_BitScanForward64`, `_BitScanReverse64`).
   - Full legal move generation filtering king-in-check positions before recursion.
3. **Static Evaluation Function**:
   - Midgame and Endgame piece values (P: 100/100, N: 320/320, B: 330/330, R: 500/500, Q: 900/900, K: 20000/20000).
   - Mirrored 64-square Piece-Square Tables (PST) matching Janus Python reference.
   - Tapered evaluation using game-phase weights based on non-pawn material count.
4. **Alpha-Beta Negamax Search**:
   - Iterative deepening driver starting at depth 1 up to `max_depth`.
   - Transposition table (1,048,576 entries, power-of-two mask, exact/lower/upper bounds).
   - Quiescence search with stand-pat evaluation, delta pruning (queen margin = 900 cp), and capture ordering.
   - Move ordering: TT move (100,000 pts), MVV-LVA captures (10,000 + victim - attacker), killer moves (2 slots per ply: 9,000 / 8,000 pts), history heuristic table (`[2][64][64]`).
   - Time-management check every 2,048 nodes with soft/hard limits.
5. **C-Linkage FFI Boundary**:
   - Zero object wrapping overhead per node.
   - Single top-level invocation per search: `native_search(board, max_depth, time_limit_sec, result)`.

---

## 3. Full Inventory of Implemented Search Features

| Subsystem | Feature | Native Implementation Details |
|---|---|---|
| **Iterative Deepening** | Depth progression | 1 to `max_depth` with aspiration/fail-soft negamax |
| **Iterative Deepening** | Best move recovery | Recovers best move and PV from completed iteration on timeout |
| **Transposition Table** | Capacity | 1,048,576 entries (~24 MB RAM) |
| **Transposition Table** | Entry layout | 64-bit Zobrist key, 16-bit best move, 16-bit score, 8-bit depth, 8-bit flag, 8-bit age |
| **Transposition Table** | Bounds handling | EXACT, LOWERBOUND (beta cutoff), UPPERBOUND (alpha fail-low) |
| **Transposition Table** | Mate score adjustment | Distance-from-root score conversion for mate scores |
| **Move Ordering** | TT Best Move | Highest priority (scored at 100,000) |
| **Move Ordering** | MVV-LVA Captures | Scored at `10,000 + victim_val * 10 - attacker_val` |
| **Move Ordering** | Killer Moves | Two killer move slots per search ply (`killer_moves[MAX_PLY][2]`) |
| **Move Ordering** | History Heuristic | Butterfly board history table `history[2][64][64]` bounded to 5,000 |
| **Quiescence Search** | Stand-pat cutoff | Evaluates static position; returns beta if `eval >= beta` |
| **Quiescence Search** | Delta Pruning | Skips captures if `stand_pat + 900 + 200 < alpha` |
| **Quiescence Search** | Tactical captures | Searches legal captures ordered by MVV-LVA |
| **Draw Detection** | 50-move rule | Evaluates to 0 if `halfmove_clock >= 100` |
| **Draw Detection** | Insufficient material | Evaluates bare kings and king+minor vs king as draw |
| **Time Management** | Wall-clock checks | Intermittent checks every 2,048 nodes using `std::chrono::steady_clock` |

---

## 4. Search Features Explicitly Deferred to Subsequent Milestones

To maintain controlled experimental validity and avoid confounding multiple changes, the following features are explicitly deferred:

1. **Reverse Futility Pruning (RFP)**: Kept disabled in baseline matching v0.45-v0.49 protocol (`enable_rfp=False`).
2. **Late Move Reductions (LMR)**: Deferred to v0.51 to isolate search-core overhead from pruning depth variations.
3. **Null Move Pruning (NMP)**: Deferred to v0.51.
4. **Threefold Repetition Detection**: Currently fifty-move rule and insufficient material are implemented in N2; full history-path repetition checking is deferred to v0.51.
5. **Static Exchange Evaluation (SEE)**: Captures are currently ordered via MVV-LVA; full bitboard SEE is deferred to v0.51.
6. **Multi-threading (Lazy SMP)**: Single-threaded search only in v0.50 to provide exact node-for-node and deterministic comparisons.

---

## 5. Architectural Pipeline Comparison: Python vs Native

```
+-------------------------------------------------------------+
|                     PYTHON K0 PIPELINE                      |
+-------------------------------------------------------------+
| Python UCI / Engine Session                                 |
|   └── search.py (Python bytecode execution)                |
|         ├── Board state: python-chess Python object         |
|         ├── Move generation: python-chess C-ext / Python    |
|         ├── Negamax recursion: CPython stack frames         |
|         ├── Evaluation: Python loops & dict lookups         |
|         ├── Move ordering: Python list.sort(key=...)        |
|         └── TT: Python dictionary / ctypes struct           |
|                                                             |
| Throughput: ~6,000 - 25,000 Nodes Per Second (NPS)          |
+-------------------------------------------------------------+

                               vs

+-------------------------------------------------------------+
|                     NATIVE N2 PIPELINE                      |
+-------------------------------------------------------------+
| Python UCI / Harness Layer (zero overhead during search)     |
|   └── Single ctypes call: native_search(...)                |
|         │                                                   |
|         ▼ [Entire search executes inside janus_native.dll]  |
|         ├── Bitboards: 64-bit uint64_t registers            |
|         ├── Move generation: Inlined bit-scan intrinsics    |
|         ├── Negamax recursion: Zero-allocation native stack |
|         ├── Evaluation: Pre-computed tables & bitops        |
|         ├── Move ordering: In-place array selection         |
|         └── TT: 1M-entry direct-mapped contiguous array     |
|                                                             |
| Throughput: 350,000 - 800,000 Nodes Per Second (NPS)        |
+-------------------------------------------------------------+
```

---

## 6. Compilation, Toolchain & Linking Verification

The native search core is built as a shared 64-bit Windows dynamic link library (`janus_native.dll`) using MSVC BuildTools 2022:

```powershell
cmd /c 'call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" && cl /O2 /LD /std:c++17 /EHsc /Fe:analysis\v0.50\native\janus_native.dll analysis\v0.50\native\janus_native.cpp'
```

- Compiler: Microsoft (R) C/C++ Optimizing Compiler Version 19.44.35222 for x64.
- Target Architecture: AMD64 / x86_64.
- Optimization Flags: `/O2` (Maximize Speed), `/std:c++17` (C++17 standard conformance), `/LD` (Create dynamic-link library).
- Binary Size: ~92 KB.

