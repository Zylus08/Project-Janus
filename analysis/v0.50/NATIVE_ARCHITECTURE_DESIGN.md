# Project Janus v0.50 — Native Architecture & Data Representation

**Milestone:** Project Janus v0.50  
**Parent Baseline Commit:** `d037f77` (v0.49 Final)  
**Proposed Native Architecture:** Candidate N2 (Native Search Core Prototype)  
**Implementation Language:** C++17 compiled via MSVC BuildTools 2022 to a 64-bit dynamic library (`janus_native.dll`) with C-linkage export boundary (`extern "C"`).

---

## 1. Technology Selection (Phase C1)

| Technology | Evaluation | Verdict |
|---|---|---|
| **Cython** | Generates intermediate C/C++ files; requires `cython` and `setuptools` pip packages in the venv; complex ABI debugging in Python 3.13. | Rejected for core search. |
| **Pure C (C99/C11)** | Low-level bit manipulation; lacks template metaprogramming for color/piece specializations; requires manual struct management. | Viable, but C++17 offers cleaner abstractions. |
| **C++17 (MSVC)** | **Native bitboard arithmetic (`uint64_t`), `constexpr` attack tables, inline functions, zero-cost abstractions, compiled directly via MSVC BuildTools 2022.** | **SELECTED.** |

---

## 2. Board Representation (Phase C2)

The native board state uses standard 64-bit bitboards matching `python-chess` square indexing:

### Square Indexing:
- Square $0 = \text{A1}, 1 = \text{B1}, \dots, 7 = \text{H1}$
- Square $56 = \text{A8}, 57 = \text{B8}, \dots, 63 = \text{H8}$
- Rank index: `sq >> 3` ($0 \dots 7$)
- File index: `sq & 7` ($0 \dots 7$)

### State Structure:
```cpp
struct NativeBoard {
    uint64_t pieces[2][6];    // [Color][PieceType]: Pawn=0, Knight=1, Bishop=2, Rook=3, Queen=4, King=5
    uint64_t occupancy[3];    // White=0, Black=1, Both=2
    uint8_t side_to_move;     // White=0, Black=1
    uint8_t castling_rights;  // Bit 0: W_OO, Bit 1: W_OOO, Bit 2: B_OO, Bit 3: B_OOO
    uint8_t ep_square;        // 0..63, or 64 if none
    uint16_t halfmove_clock;  // 50-move rule counter
    uint16_t fullmove_number; // Move counter
    uint64_t zobrist_key;     // Polyglot-compatible 64-bit Zobrist key
};
```

---

## 3. Compact Move Representation (Phase C3)

Moves are encoded in a compact 16-bit unsigned integer (`uint16_t`):
- **Bits 0–5 (6 bits):** `from_square` ($0 \dots 63$)
- **Bits 6–11 (6 bits):** `to_square` ($0 \dots 63$)
- **Bits 12–13 (2 bits):** `special_type` ($0 = \text{Normal/Promotion}$, $1 = \text{Castling}$, $2 = \text{En Passant}$)
- **Bits 14–15 (2 bits):** `promotion_piece` ($0 = \text{None}$, $1 = \text{Knight}$, $2 = \text{Bishop}$, $3 = \text{Rook}$, $4 = \text{Queen}$)

---

## 4. Make / Unmake Architecture (Phase C4)

To guarantee exact reversibility and avoid position reconstruction overhead:
```cpp
struct UndoInfo {
    uint8_t captured_piece;     // 0..5, or 6 if none
    uint8_t castling_rights;    // previous castling mask
    uint8_t ep_square;          // previous en-passant square
    uint16_t halfmove_clock;    // previous halfmove clock
    uint64_t zobrist_key;       // previous Zobrist hash
};
```
Each search depth maintains an `UndoInfo` frame on the stack. `make_move(board, move, undo)` updates the board and records state; `unmake_move(board, move, undo)` restores bitboards and hashes in $O(1)$.

---

## 5. Memory Ownership and Boundary Policy (Phase C5)

1. **Pre-Allocated Search Structures:** All node move buffers (`MoveList moves[MAX_PLY]`), undo stacks (`UndoInfo undo[MAX_PLY]`), and the Transposition Table (`TTEntry* tt_table`) are allocated natively at engine initialization. Zero heap allocations occur during alpha-beta traversal.
2. **Boundary Minimalization:** The Python engine sends the root FEN string, search depth, and time limits to `native_search(...)`. The search runs entirely in native C++, returning the best move, root score, completed depth, node count, and PV in a single C struct.

