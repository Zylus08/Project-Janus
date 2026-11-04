# Project Janus v0.50 — python-chess Dependency & Semantic Audit

**Milestone:** Project Janus v0.50  
**Parent Baseline Commit:** `d037f77` (v0.49 Final)  
**Evaluated Modules:** `src/janus/{search.py, evaluation.py, see.py, uci.py, time_manager.py, engine_session.py}`

---

## 1. Source-Level Dependency Audit (Phase B1)

An automated AST scan of `project-janus/src/janus/` identified all usages of `python-chess`:

| Module | Usages | Critical Dependencies in Hot Path | Native Replacement Requirement |
|---|---:|---|---|
| **`search.py`** | 16 | `board.legal_moves`, `board.generate_legal_captures()`, `board.push(m)`, `board.pop()`, `board.is_check()`, `board.gives_check(m)`, `board.is_repetition(2)`, `board.can_claim_draw()`, `chess.polyglot.zobrist_hash` | **REQUIRED IN NATIVE SEARCH CORE.** Must be executed natively to eliminate Python per-node overhead. |
| **`evaluation.py`** | 49 | `board.pieces(type, color)`, `board.piece_at(sq)`, `board.king(color)`, `board.has_kingside_castling_rights()`, `board.pawns` bitboard access | **REQUIRED FOR NATIVE EVALUATION.** Bitboard operations must be native to avoid Python callback overhead. |
| **`see.py`** | 14 | `board.piece_type_at(sq)`, `board.occupied`, `scan_forward`, `square_file`, `square_rank` | **REQUIRED IN NATIVE SEARCH CORE.** SEE is executed during move ordering at every node. |
| **`uci.py`** | 2 | `chess.Board`, `chess.Move.from_uci()`, `chess.Move.uci()` | **REMAINS IN PYTHON.** Acts as the top-level UCI protocol bridge and I/O handler. |
| **`time_manager.py`** | 3 | `chess.Color`, `chess.WHITE` | **REMAINS IN PYTHON.** High-level search budget orchestration. |
| **`engine_session.py`** | 5 | `chess.Board`, `chess.Move`, `STARTING_FEN` | **REMAINS IN PYTHON.** Benchmark and match harness runner. |

---

## 2. Rule-Semantics Specification (Phase B2)

The native search engine must strictly match the normative FIDE rules and `python-chess` semantics implemented in Janus:

### 2.1 Terminal & Draw Classifications

1. **Checkmate:**
   - Side to move is in check (`in_check == True`) and has 0 legal moves.
   - Evaluated as $-(\text{MATE\_SCORE} - \text{ply})$.
2. **Stalemate:**
   - Side to move is NOT in check (`in_check == False`) and has 0 legal moves.
   - Evaluated as $0$ (draw).
3. **Claimable Draws:**
   - **Threefold Repetition:** The same position (same piece placement, side to move, castling rights, and en-passant square) occurs for the 3rd time. In Janus alpha-beta search, `board.is_repetition(2)` triggers an immediate 0 evaluation.
   - **Fifty-Move Rule:** 50 consecutive moves (100 plies) completed by each player without a pawn move or capture (`halfmove_clock >= 100`). Evaluated as 0.
4. **Automatic Draws:**
   - **Fivefold Repetition:** Occurs 5 times automatically.
   - **Seventy-Five-Move Rule:** 75 full moves (150 plies) without pawn move or capture.
   - **Insufficient Material:**
     - $K$ vs $K$
     - $K + N$ vs $K$
     - $K + B$ vs $K$
     - $K + B$ vs $K + B$ (where bishops are on the same square color).

### 2.2 Special Move Rules

- **Castling:** King moves 2 squares towards rook. Requires: King and rook have not moved; squares between them are unoccupied; king does not start in check, pass through check, or land in check.
- **En Passant:** Can only be captured immediately on the ply following a two-square pawn advance. En-passant square cleared on any non-double-pawn advance.
- **Pawn Promotion:** Moving to rank 8 (white) or rank 1 (black). Must support Queen, Rook, Bishop, and Knight promotions (including underpromotions).
- **Chess960:** Verified **NOT supported** in current Janus engine interface (standard classical chess only).

---

## 3. Reference Test Inventory (Phase B3)

A comprehensive test inventory has been established across:
1. Standard initial board state.
2. Tactical middle games with multiple pins and discovered attacks.
3. Promotion and underpromotion endgames.
4. En passant discovery pins (where en-passant capture exposes king).
5. Castling across attacked squares vs rook attacked squares.
6. Stalemate vs checkmate boundary positions.
7. Fifty-move clock increment, reset on captures/pawn pushes, and undo restoration.

