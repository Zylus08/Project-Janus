# Project Janus v0.51 — Native Implementation & Source Code Audit

## 1. Audit Scope & Provenance

This document records an exhaustive, line-by-line engineering audit of the inherited v0.50 native codebase (`analysis/v0.50/native/janus_native.cpp` and `analysis/v0.50/native/janus_native_bridge.py`) frozen at commit `238b85b`.

In strict adherence to the governing principles of Project Janus, this audit verifies actual source code behaviour against the claims made in the v0.50 milestone report and architectural design documents.

---

## 2. Component-by-Component Source Code Inspection

### 2.1 Board Representation (`NativeBoard`)
- **Source Lines:** 61–71
- **Struct Fields:**
  * `uint64_t pieces[2][6]`: Piece bitboards per side (White=0, Black=1) and piece type (P, N, B, R, Q, K).
  * `uint64_t occupancy[3]`: White, Black, and Combined occupancy masks.
  * `uint8_t side_to_move`, `uint8_t castling_rights`, `uint8_t ep_square`, `uint16_t halfmove_clock`, `uint16_t fullmove_number`, `uint64_t zobrist_key`.
- **Verdict:** Fully conforms to bitboard specifications. State layout is packed and cache-aligned.

### 2.2 Make / Unmake Implementation (`native_make_move`, `native_unmake_move`)
- **Source Lines:** 497–616
- **Mechanism:**
  * Uses caller-provided `UndoInfo` struct (24 bytes).
  * Restores captured pieces, castling bitmask, ep square, halfmove clock, and 64-bit Zobrist key.
  * Castling updates both king and rook bitboards and toggles castling Zobrist hashes.
  * En passant moves correctly locate captured pawn square (`to - 8` or `to + 8`) and adjust bitboards.
- **Verdict:** Reversible make/unmake is mathematically exact and verified by 178 round-trip transition tests.

### 2.3 Move Encoding and Decoding
- **Source Lines:** 53–59
- **Encoding:** Compact 16-bit integer:
  * Bits 0–5: Source square (`m & 0x3F`).
  * Bits 6–11: Destination square (`(m >> 6) & 0x3F`).
  * Bits 12–13: Special flag (`(m >> 12) & 3`): 0=Normal, 1=Castle, 2=En Passant, 3=Promotion.
  * Bits 14–15: Promotion piece type (`(m >> 14) & 3`): 0=Knight, 1=Bishop, 2=Rook, 3=Queen.
- **Verdict:** Clean, unambiguous 16-bit encoding.

### 2.4 Attack and Legal Move Generation
- **Source Lines:** 127–346 (Attacks), 618–780 (Move generation)
- **Mechanism:**
  * Knight, King, and Pawn attacks are precomputed in 64-entry lookup tables.
  * Sliding attacks (Rook, Bishop, Queen) use ray-casting hyperbola simulation without magic bitboards.
  * `native_generate_legal_moves` generates pseudo-legal moves and filters out moves that leave the moving king in check via `is_square_attacked`.
  * Verified against all 18 standard Perft suites (15.0–16.16M NPS).
- **Verdict:** 100% compliant with FIDE legal move rules.

### 2.5 Zobrist Hashing
- **Source Lines:** 79–106, 381–460
- **Implementation:**
  * Polyglot-compatible 64-bit random tables: `zobrist_pieces[2][6][64]`, `zobrist_castling[16]`, `zobrist_ep[65]`, `zobrist_side`.
  * Incremental XOR hashing maintained across `native_make_move` and restored on unmake.
- **Verdict:** Verified exact against python-chess Zobrist keys across 37 positions.

### 2.6 Search Stack Bounds & PV Storage
- **Source Lines:** 1023–1133 (`negamax`), 1136–1180 (`native_search`)
- **Inspection Finding:**
  * Recursion depth is bounded only by runtime parameter `max_depth` (stack frames are on the native call stack).
  * `NativeSearchResult` defines `uint16_t pv[64]` and `int pv_length`, but **`negamax` does not populate `pv` or `pv_length`!**
  * Lines 1148–1170 set `out_res->best_move = iter_best_move;` and leave `pv_length = 0`.
- **Verdict:** PV extraction is missing from the search engine.

### 2.7 Transposition Table (TT) Indexing and Replacement
- **Source Lines:** 112–125, 1046–1059, 1120–1130
- **Implementation:**
  * Power-of-two table: `1 << 20` entries (1,048,576 entries, ~16 MB).
  * Direct-mapped indexing: `size_t tt_idx = key % TT_SIZE;`.
  * Replacement policy: **Always Replace**. Every non-aborted node overwrites the slot regardless of depth or generation age.
- **Verdict:** Functional but primitive; deep nodes can be overwritten by shallow noise from later iterations.

### 2.8 Mate-Score Normalization
- **Source Lines:** 1055–1057, 1071, 1126
- **Inspection Finding:**
  * Checkmate is returned as `-(MATE_SCORE - ply)` (Line 1071).
  * However, when storing into TT (Line 1126): `entry.score = (int16_t)best_score;` stores the raw score unadjusted for ply!
  * When probing from TT (Lines 1055–1057): `entry.score` is returned directly without adjusting for root-relative ply!
  * **Consequence:** If a mate in 2 found at ply 3 is probed at ply 1 in a subsequent iteration, the mate distance is corrupted.
- **Verdict:** Severe mate-score normalization defect in TT probe/store.

### 2.9 Quiescence Search & Move Ordering
- **Source Lines:** 968–1020 (`quiescence`), 926–965 (`score_move_for_ordering`)
- **Implementation:**
  * Quiescence generates all legal moves, filters captures and promotions, sorts by MVV-LVA, and applies stand-pat cutoffs.
  * In `negamax`: sorts moves by `score_move_for_ordering`.
  * Policy implemented: TT move (`10,000,000`), Promotions (`900,000 / 800,000`), Captures (`100,000 + victim*10 - attacker`), Quiet moves (`0`).
- **Verdict:** Solid core, but missing history heuristic and killer moves in the actual source code.

### 2.10 Repetition History & FIDE Draw Rules
- **Source Lines:** 1043–1044
- **Inspection Finding:**
  * `if (b->halfmove_clock >= 100) return 0;`
  * **There is NO game history table, NO repetition stack, and NO threefold or fivefold repetition detection in `janus_native.cpp`!**
  * The engine cannot detect repetitions during tree search and cannot detect repetitions that occurred before the search root.
- **Verdict:** Repetition tracking is completely absent in v0.50 N2.

### 2.11 Standalone UCI Protocol
- **Source Lines:** None.
- **Inspection Finding:**
  * `janus_native.cpp` only exports functions (`native_init`, `native_set_fen`, `native_search`, etc.) for compilation into a dynamic-link library (`janus_native.dll`).
  * There is **no `main()` function**, no `cin` loop, and no UCI parser in C++.
  * The engine cannot run as a standalone executable in tournament GUIs or controllers.
- **Verdict:** Standalone UCI integration is completely absent.

---

## 3. Discrepancy Matrix: v0.50 Documentation vs Actual Source Code

| Feature | v0.50 Report / Design Claim | Actual Source Code in `janus_native.cpp` | Severity / Action for v0.51 |
|---|---|---|---|
| **Standalone UCI Engine** | Roadmap goal for v0.51 | Only DLL exported; zero UCI loop | **Phase E Blocker:** Must implement standalone `janus_native_engine.exe` with full UCI protocol. |
| **Threefold Repetition** | Documented as deferred | Completely absent; only fifty-move rule checked | **Phase B Blocker:** Must implement 1,024-ply game history stack and repetition detection. |
| **Fivefold Repetition** | Documented as deferred | Completely absent | **Phase B Blocker:** Must implement automatic 5-fold draw. |
| **PV Line Output** | Claimed in struct definition | Struct field exists (`pv[64]`), but `negamax` never populates it | **Search Defect:** Must implement PV table / extraction for UCI `info pv`. |
| **Mate-Score Normalization** | Stated as handled in v0.50 text | TT stores and probes unadjusted raw mate scores | **Correctness Defect:** Must normalize `score +/- ply` on store and probe. |
| **History & Killer Moves** | Described in Architecture Design | Not present in `score_move_for_ordering`; quiets scored as 0 | **Move Ordering Gap:** Documented as absent; can be added in move ordering. |
| **TT Replacement Policy** | Described as depth-preferred | Implemented as Always Replace (`g_tt[idx] = ...`) | Documented; depth-preferred replacement needed. |

---

## 4. Remediation Plan for v0.51

To satisfy the requirements of Milestone v0.51, the following mandatory remediations must be executed in order:

1. **Phase B (Draw Semantics & Repetition):**
   - Add a 1,024-entry `uint64_t game_history[]` array and history pointer.
   - Implement threefold repetition detection during recursive search and against prior game history.
   - Implement claimable vs automatic draw distinctions (threefold vs fivefold, 50-move vs 75-move).
2. **Phase C (Memory Safety & Defensive Bounds):**
   - Fix mate-score TT normalization.
   - Implement PV tracking array (`pv_table[MAX_PLY][MAX_PLY]`).
   - Add strict bounds checking on search ply, move lists, and history buffers.
3. **Phase E (Standalone Native UCI Engine):**
   - Implement `janus_native_engine.cpp` with a high-performance, robust UCI command loop.
   - Support `uci`, `isready`, `ucinewgame`, `position`, `go` (depth, movetime, wtime/btime/winc/binc), `stop`, `quit`.
   - Provide clean stdout formatting (`id`, `uciok`, `readyok`, `info depth ... score ... nodes ... nps ... pv ...`, `bestmove`).

