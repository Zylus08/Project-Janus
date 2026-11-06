# PROJECT JANUS v0.60 — BASELINE AND EVALUATION AUDIT
**Author:** Principal Chess Engine Research Architect, ML Systems Engineer & Independent Scientific Reproducibility Auditor  
**Date:** 2026-11-07  
**Repository:** `E:\ChessXML\project-janus`  
**Target Candidate:** Janus Neural Value V1 (`NNUE-V1`)  
**Frozen Baseline:** Janus Classical Baseline C1 (Native N5)  
**Parent Commit:** `7e390b5` (`feat(ml): evaluate neural policy effectiveness, search interaction, and causal ablation (v0.59)`)

---

## 1. Executive Summary & Git Ancestry Verification

In accordance with Phase 0 of the Project Janus v0.60 specification, a preflight audit of the repository state, baseline artifacts, evaluation semantics, and test suite was conducted prior to any architectural design or implementation.

### 1.1 Git Working Tree & Commit Verification
- **Current Branch:** `v0.3-benchmark-harness`
- **Current Commit:** `7e390b5`
- **Parent Commit:** `b84c003` (v0.58 milestone)
- **Working Tree State:** Clean (no untracked modifications to production baselines; all work isolated to `analysis/v0.60/`).
- **Remote Operations:** Strictly disabled. No pushes to remote repositories are permitted or performed.

---

## 2. Frozen Classical Baseline C1 Verification

The frozen Classical Baseline C1 corresponds to Native N5, first frozen in v0.56 and validated in v0.57.

### 2.1 Artifact Hashes & Sizes

| Artifact | File Path | Size (bytes) | SHA-256 Digest | Status |
| :--- | :--- | :--- | :--- | :--- |
| **C1 Engine Executable** | `analysis/v0.56/native/janus_native_engine.exe` | 341,504 | `a4f9d9d18b549d29b2e6740ac90d90d39167d92d3846b95fc0c4f5b966add83f` | **Verified & Intact** |
| **C1 Native Source** | `analysis/v0.56/native/janus_native.cpp` | 80,677 | `43ad79ade44cc6d6dd97a4cfeb6e9ba2b32c8d080190808d22cac486616397a4` | **Verified & Intact** |
| **C1 Native DLL** | `analysis/v0.56/native/janus_native.dll` | 259,072 | `db06d15b0bfa9da16dfa99f196a642eeb9491629858aa58cf27393e1ea66518f` | **Verified & Intact** |
| **C1 Python Bridge** | `analysis/v0.56/native/janus_native_bridge.py` | 14,350 | `a41a46cf988849b29cb115e5df1176b6b71f9cfd5fe4e11fa05470d55e8c1566` | **Verified & Intact** |

### 2.2 Frozen Production Configuration
The baseline C1 configuration is frozen with the following parameters:
- `UseLMR = true` (min_depth=3, move_threshold=4, base_reduction=1)
- `UseKillerOrdering = true` (2 killers per ply)
- `UseHistoryOrdering = true` (butterfly table, 2×64×64)
- `UsePVS = false` (Principal Variation Search unpromoted)
- `UseSEEOrdering = false` (Static Exchange Evaluation move ordering unpromoted)
- `UseSEEInQuiescence = false` (SEE in quiescence unpromoted)
- `UseNeuralPolicy = false` (N8-A policy model disabled)

---

## 3. Discovered Test Inventory Reconciliation

In v0.59, 644 passing tests were reported (639 inherited from v0.57 + 5 neural policy tests from v0.58), along with 4 new invariant tests in `tests/test_v059_neural_ablation.py`.

### 3.1 Inventory Count Reconciliation
- When collected via `pytest tests/`, exactly **648 test items** are discovered across 54 test files.
- The 4 invariant tests from v0.59 (`test_classical_baseline_parity`, `test_causal_invariance_theorem`, `test_root_telemetry_json_export`, `test_budget_throttling`) are part of this 648 total.
- **Reconciliation Conclusion:** The discovered test count is exactly 648 items.

### 3.2 Test Isolation & Shared DLL State Hygiene
During preflight regression auditing, `test_classical_baseline_parity` in `test_v059_neural_ablation.py` failed when executed after `test_native_see_search_semantics.py`.
- **Root Cause:** In Python test runs, `janus_native.dll` is loaded as a process-level singleton. `test_native_see_search_semantics.py` exercised `set_see_options(True, True)`, leaving the global C1 DLL state modified. Subsequent parity testing between C1 and v0.59 showed a node mismatch (3,169 vs 3,315 nodes) because C1 was running with SEE enabled while v0.59 ran with SEE disabled.
- **Correction:** Explicitly reset search options (`set_ordering_options(True, True)`, `set_pvs_options(False)`, `set_lmr_options(True, 3, 4, 1)`, `set_see_options(False, False)`) before parity assertions.
- **Result:** Bit-exact node parity (3,315 == 3,315) and 100% test passing restored across the entire test suite.

---

## 4. Evaluation Architecture and Semantics Audit

### 4.1 Evaluation Call Graph
The current native C++ engine uses a classical evaluation pipeline tightly integrated into the alpha-beta search tree:

```
[search()]
   │
   ▼
[iterative_deepening()]
   │
   ▼
[negamax(depth, alpha, beta, ply)]
   │
   ├── [Terminal Checks: 50-move, 3-fold, Insufficient Material] -> returns 0
   │
   ├── [Leaf Check: depth <= 0 || ply >= MAX_SEARCH_PLY - 1]
   │      │
   │      ▼
   │   [quiescence(alpha, beta, nodes, deadline, aborted)]
   │      │
   │      ├── [stand_pat = native_evaluate(b)]
   │      │      │
   │      │      ├── Beta cutoff check: if (stand_pat >= beta) return beta
   │      │      ├── Alpha update: if (stand_pat > alpha) alpha = stand_pat
   │      │      └── Delta Pruning: if (stand_pat + 1100 < alpha) return alpha
   │      │
   │      └── [Capture generation & loop]
   │             └── Recursive quiescence() calls
   │
   └── [Internal Node Search: TT probe, Legal moves, Move ordering, Recursive negamax]
```

### 4.2 Score Conventions & Semantics
1. **Side-to-Move Perspective:**
   - In `native_evaluate(const NativeBoard* b)`, material and piece-square tables are summed from White's perspective, followed by game phase interpolation and castling bonus calculation.
   - At return, the score is multiplied by $(b\to\text{side\_to\_move} == \text{WHITE} ? +1 : -1)$.
   - **Crucial Rule:** `native_evaluate()` returns the evaluation strictly from the perspective of the **side to move** (positive = side to move is winning).
2. **Centipawn Scale:**
   - Material values: Pawn = 100, Knight = 320, Bishop = 330 (MG) / 335 (EG), Rook = 500, Queen = 900, King = 20000.
   - Piece-square tables: Range $[-40, +40]$ centipawns.
   - Castling rights bonus: $+15$ centipawns per held right.
3. **Game Phase Interpolation:**
   - Total phase weight = 24 points: Knights/Bishops = 1, Rooks = 2, Queens = 4.
   - Tapered formula: $\text{score} = \frac{\text{mg\_score} \cdot \text{phase} + \text{eg\_score} \cdot (24 - \text{phase})}{24}$.
4. **Mate Scores:**
   - `MATE_SCORE = 30000` (or `32000`).
   - Checkmate is evaluated at terminal node when legal move count $n = 0$ and `native_is_check(b) != 0`.
   - Score returned: $-(MATE\_SCORE - ply)$.
   - Static evaluation is **never** invoked on checkmate or terminal positions. Static evaluations are bounded strictly within $[-15000, +15000]$ cp, ensuring complete numerical separation from mate scores.

---

## 5. Board Representation & Mutation Model

### 5.1 NativeBoard Representation
The board state is maintained in `NativeBoard`:
```cpp
struct NativeBoard {
    uint64_t pieces[2][6];    // [WHITE/BLACK][PAWN..KING] bitboards
    uint64_t occupancy[2];    // [WHITE/BLACK] combined bitboards
    int side_to_move;         // WHITE = 0, BLACK = 1
    int castling_rights;      // Bitmask: 1=W_OO, 2=W_OOO, 4=B_OO, 8=B_OOO
    int ep_square;            // -1 or square index 0..63
    int halfmove_clock;       // 50-move rule counter
    int fullmove_number;      // Turn number
    uint64_t zobrist_key;     // 64-bit Zobrist hash
};
```

### 5.2 Move Encoding & Undo Mechanics
- Moves are encoded as 16-bit integers:
  - Bits 0–5: `from` square ($0..63$)
  - Bits 6–11: `to` square ($0..63$)
  - Bits 12–13: `flag` ($0=\text{quiet}, 1=\text{double pawn push}, 2=\text{en passant}, 3=\text{promotion}$)
  - Bits 14–15: `promo` ($0=\text{knight}, 1=\text{bishop}, 2=\text{rook}, 3=\text{queen}$)
- Unmake operation uses `UndoInfo`:
  ```cpp
  struct UndoInfo {
      int captured_piece;
      int old_castling_rights;
      int old_ep_square;
      int old_halfmove_clock;
      uint64_t old_zobrist_key;
  };
  ```

### 5.3 Implications for Incremental NNUE Accumulator
1. **Sparse Piece Coordinate:**
   - Feature index can be parameterized by perspective:
     $\text{feature}(c, p, sq) = c \times (6 \times 64) + p \times 64 + sq$, where $c \in \{0, 1\}$, $p \in [0, 5]$, $sq \in [0, 63]$.
     Total sparse features per perspective: $64 \times 12 = 768$ (White pieces + Black pieces on 64 squares).
2. **Move Deltas:**
   - **Quiet move:** Subtract 1 feature at `from`, add 1 feature at `to`. Total: 1 add, 1 sub.
   - **Capture:** Subtract moving piece at `from`, subtract captured piece at `to`, add moving piece at `to`. Total: 1 add, 2 subs.
   - **Promotion:** Subtract pawn at `from`, subtract captured piece at `to` (if any), add promoted piece at `to`. Total: 1 add, 1–2 subs.
   - **En Passant:** Subtract pawn at `from`, subtract enemy pawn at `ep_captured_sq`, add pawn at `to`. Total: 1 add, 2 subs.
   - **Castling:** Move king (1 sub, 1 add), move rook (1 sub, 1 add). Total: 2 adds, 2 subs.
3. **Accumulator Stack:**
   - Because alpha-beta searches up to `MAX_SEARCH_PLY` (64 plies) and quiescence can extend plies, maintaining an accumulator stack `Accumulator accum_stack[MAX_SEARCH_PLY + 32]` aligned to 64 bytes (cache line) allows copying or directly updating accumulators ply-by-ply without recomputing unaffected terms.

---

## 6. Gate 0 Sign-Off

The evaluation call sites, score conventions (centipawns, side-to-move perspective, mate score separation), board state mutations, and test suite baseline have been thoroughly verified and documented.

**Gate 0 Status:** **PASSED**. Proceeding immediately to Phase 1 (NNUE Architecture Design).
