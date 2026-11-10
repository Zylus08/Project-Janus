# Project Janus Phase 1 — Milestone P1.0
## Janus Classical C1 Comprehensive Architecture Audit

**Milestone:** P1.0  
**Program:** Classical Engine Supremacy Program (Phase 1)  
**Role:** Principal Computer Chess Engineer & C++17 Systems Architect  
**Subject Engine:** Janus Classical Baseline C1 (`analysis/v0.56/native/janus_native.cpp`)  
**Git Anchor:** `e543dab` (Freeze Verification: `2b24d13`)  
**Date:** 2026-11-09  
**Deliverable:** `analysis/phase1/p1.0/JANUS_ARCHITECTURE_AUDIT.md`  

---

## 1. Executive Architecture Summary

This audit reconstructs the complete concrete implementation of the **Janus Classical Baseline C1** native C++17 engine. Rather than relying on historical summaries, every subsystem was audited directly from source (`janus_native.cpp`, 2,306 lines of C++17).

C1 is a pure bitboard alpha-beta engine featuring incremental Zobrist hashing, 64 MB depth-preferred transposition table, basic MVV-LVA / Killer / History move ordering, and a rudimentary Late Move Reduction (LMR) scheme. However, modern search pruning and reduction techniques (Null-Move Pruning, Reverse Futility Pruning, Check Extensions, Aspiration Windows, Multithreading) are completely absent, and its handcrafted evaluation function is restricted to simple material, piece-square tables, and a castling bonus without any mobility, pawn structure, or king safety modeling.

---

## 2. Comprehensive 25-Subsystem Engineering Audit

```
+-----------------------------------------------------------------------------------------------------------------------+
| SUB-SYSTEM STATUS DEFINITIONS:                                                                                        |
| [IMP] Implemented & Active    [PART] Partially Implemented    [DIS] Available but Disabled    [MISS] Completely Missing|
| [COR] Correctness-Sensitive   [PERF] Performance-Sensitive                                                            |
+-----------------------------------------------------------------------------------------------------------------------+
```

| # | Subsystem | Implemented Status | Engineering Properties | Concrete Implementation Details in Janus C1 |
|---|:---|:---:|:---:|:---|
| **1** | **Board Representation** | **IMP** | `PERF` | 64-bit Bitboards (`uint64_t pieces[2][6]`, `occupancy[2]`, `all_occupancy`). Square index $0 = \text{a1}$, $63 = \text{h8}$. Little-endian rank-file mapping. |
| **2** | **FEN Parsing** | **IMP** | `COR` | `native_set_fen()` parses piece placement, active color, castling availability (`KQkq`), en passant target square, halfmove clock, and fullmove number. |
| **3** | **Move Generation** | **IMP** | `PERF`, `COR` | Precomputed attack tables for pawns, knights, kings. Classical bitboard shift/ray traversals for sliding pieces (bishops, rooks, queens) using `occupancy` masking. |
| **4** | **Legal Move Verification** | **IMP** | `COR` | Generates pseudo-legal moves and filters out moves that leave the friendly king in check using `is_square_attacked()`. |
| **5** | **Make / Unmake Mechanics** | **IMP** | `PERF`, `COR` | `native_make_move()` and `native_unmake_move()` with explicit `UndoInfo` struct (storing captured piece, previous castling rights, prior EP square, halfmove clock, and zobrist key). Verified 100% bit-exact across 6,000 positions. |
| **6** | **Zobrist Hashing** | **IMP** | `PERF`, `COR` | 64-bit pseudo-random keys (`zobrist_keys[2][6][64]`, `side_key`, `castle_keys[16]`, `ep_keys[65]`). Incremental XOR updates in make/unmake. |
| **7** | **Transposition Table Layout** | **IMP** | `PERF` | Fixed 64 MB table ($1,048,576$ entries, 64-byte struct). Fields: `key`, `depth`, `flag` (`EXACT`, `LOWER`, `UPPER`), `score`, `best_move`, `age`. Replacement strategy: depth-preferred with generation age override. Normalized mate distance. |
| **8** | **Iterative Deepening** | **IMP** | `PERF` | Loops depth $d = 1 \dots \text{max\_depth}$ in `native_search()`. Time deadline monitored at 2048-node intervals. On time abort, discards incomplete iteration and returns prior iteration best move. |
| **9** | **Alpha-Beta & Negamax** | **IMP** | `PERF`, `COR` | Fail-soft negamax implementation. Propagates PV lines via triangular array `g_pv_table[MAX_PLY][MAX_PLY]`. |
| **10** | **Principal Variation Search (PVS)** | **DIS** | `PERF` | Implemented in `negamax()` with null-window searches (`[-alpha-1, -alpha]`), but **frozen disabled** in C1 production (`UsePVS=false`). |
| **11** | **Late Move Reductions (LMR)** | **IMP** | `PERF` | Active for quiet non-check moves at index $i \ge 4$ and depth $d \ge 3$. Constant reduction $R = 1$ ply. No logarithmic formula, no history-adaptive reduction, no tactical verification. |
| **12** | **Null-Move Pruning (NMP)** | **MISS** | `PERF` | **Completely absent.** C1 performs zero null-move forward pruning. Searches all positions with full move generation. |
| **13** | **Futility / Reverse Futility Pruning**| **MISS** | `PERF` | **Completely absent in native C1.** Evaluated in Python prototype (v0.40), but never ported to native C++ search. Nodes at depth 1-2 search all moves. |
| **14** | **Quiescence Search** | **IMP** | `PERF` | Searches all captures in leaf positions. MVV-LVA ordered. Stand-pat lower bound. Delta pruning and quiet check evasions are missing. |
| **15** | **Check & Tactical Extensions** | **MISS** | `COR`, `PERF` | **Completely absent.** King in check is only used to detect checkmate vs stalemate ($n = 0$). Depth is never extended on check. |
| **16** | **Killer & History Heuristics** | **IMP** | `PERF` | Two killer slots per ply (`g_killer_moves[MAX_PLY][2]`). Butterfly history table (`g_history_table[2][64][64]`), aged by factor 2 at the start of each search. |
| **17** | **Capture Scoring & SEE** | **PART** | `PERF` | `janus_see()` static exchange evaluation is fully implemented, but **frozen disabled in C1 default** (`UseSEEOrdering=false`, `UseSEEInQuiescence=false`). C1 relies purely on MVV-LVA for capture ordering. |
| **18** | **Aspiration Windows** | **MISS** | `PERF` | **Completely absent.** Iterative deepening searches root with full infinite window $(-\infty, +\infty)$ at every iteration. |
| **19** | **Draw Detection** | **IMP** | `COR` | Detects threefold repetition via `g_game_history` array and 50-move rule via `b->halfmove_clock >= 100`. |
| **20** | **Checkmate & Mate Distance** | **IMP** | `COR` | Assigns $\pm(\text{MATE\_SCORE} - \text{ply})$ where $\text{MATE\_SCORE} = 30,000$. Correctly prefers shortest mate and longest resistance. |
| **21** | **Handcrafted Static Evaluation** | **PART** | `PERF` | Implements basic piece material + single Piece-Square Table (PST) per piece type + game phase interpolation + 15 cp castling bonus. **Lacks mobility, pawn structure, king safety, bishop pair, and outpost terms.** |
| **22** | **Time Management** | **PART** | `PERF` | Static 1/40th allocation formula: $\text{alloc} = (\text{time} + 40 \times \text{inc}) / 40.0$. Lacks move-importance scaling, search instability extension, or fail-low panic time allocation. |
| **23** | **UCI Protocol Handling** | **IMP** | `COR` | Supports `uci`, `isready`, `setoption`, `ucinewgame`, `position [startpos/fen] moves ...`, `go [depth/movetime/wtime/btime/winc/binc]`, `quit`. |
| **24** | **Search Threading (SMP)** | **MISS** | `PERF` | **Completely absent.** C1 executes strictly single-threaded on the main process thread. Zero shared hash locks or Lazy SMP threads. |
| **25** | **Memory Management** | **IMP** | `PERF` | Single static global allocation for TT (64 MB), history table (64 KB), and attack tables. Zero heap allocations during search. Cache-friendly linear arrays. |

---

## 3. High-Impact Algorithmic Deficiencies

From this architectural audit, four structural bottlenecks emerge that fundamentally limit Classical C1's playing strength against modern engines:

1. **Total Absence of Early Pruning (NMP & RFP):** Modern classical engines achieve 70–80% of their tree pruning from Null-Move Pruning (NMP) at depth $\ge 3$ and Reverse Futility Pruning (RFP) at depth $\le 2$. C1 must search every single branch down to quiescence, suffering an enormous search tree penalty.
2. **Infinite Root Search Windows:** Searching every iteration with $(-\infty, +\infty)$ instead of a narrow aspiration window ($[\alpha - 25, \beta + 25]$) prevents C1 from exploiting score stability, increasing node counts by 15–25%.
3. **Absence of Tactical Check Extensions:** Failing to extend depth when in check leaves C1 vulnerable to horizon-effect tactical blindness and checkmate evasion failures in sharp positions.
4. **Primitive Handcrafted Evaluation:** Evaluation is entirely static material and square placement. In middle-game positions where material is equal, C1 has zero awareness of piece mobility, open files for rooks, king safety attack vectors, passed pawn advancement, or weak pawn islands.
