# Project Janus v0.42 — Draw Rule Semantics Audit (Phase D)

**Milestone:** v0.42  
**Scope:** Audit of draw detection semantics in `src/janus/search.py`  
**Date:** 2026-11-02  

---

## 1. Chess Draw Rule Taxonomy

| Draw Type | Rule | Who Triggers | When |
|:---|:---|:---|:---|
| Insufficient material | Automatic | Engine (python-chess) | Immediately |
| Stalemate | Automatic | Engine | When no legal moves, not in check |
| **Fivefold repetition** | **Automatic** | **Arbiter/Engine** | **After 5th occurrence of same position** |
| **75-move rule** | **Automatic** | **Arbiter/Engine** | **After 75 moves (halfmove_clock ≥ 150) with no pawn move/capture** |
| **Threefold repetition** | **Claimable** | **Player (must claim)** | **After 3rd occurrence of same position** |
| **50-move rule** | **Claimable** | **Player (must claim)** | **After 50 moves (halfmove_clock ≥ 100) with no pawn move/capture** |

The key distinction for engine implementation:
- **Automatic draws**: Must be recognized unconditionally — no option to continue
- **Claimable draws**: A player **may** claim a draw; the draw does not happen automatically

---

## 2. Current Implementation Audit

### 2.1 `_terminal_score` (lines 505–518)

```python
def _terminal_score(self, board: chess.Board, ply: int = 0) -> Optional[int]:
    if (
        board.is_insufficient_material()
        or (ply > 0 and board.is_repetition(3))
        or board.is_fivefold_repetition()
        or board.is_seventyfive_moves()
    ):
        return 0
    if board.is_check():
        if not any(board.generate_legal_moves()):
            return -MATE_SCORE + ply
    elif not any(board.generate_legal_moves()):
        return 0
    return None
```

### 2.2 `_quiescence` (lines 636–642)

```python
if (
    board.is_insufficient_material()
    or (ply > 0 and board.is_repetition(3))
    or board.is_fivefold_repetition()
    or board.is_seventyfive_moves()
):
    return 0
```

### 2.3 `_negamax` (lines 732–739)

```python
# Fast rule-mandated draws that do not require move generation
if (
    board.is_insufficient_material()
    or (ply > 0 and board.is_repetition(3))
    or board.is_fivefold_repetition()
    or board.is_seventyfive_moves()
):
    return 0, []
```

---

## 3. Semantic Analysis

### 3.1 Correctly Implemented (Automatic Draws)

| Check | Method | Triggers at | Verdict |
|:---|:---|:---|:---:|
| Insufficient material | `is_insufficient_material()` | Instantly | ✓ CORRECT |
| Fivefold repetition | `is_fivefold_repetition()` | 5th occurrence | ✓ CORRECT |
| 75-move rule | `is_seventyfive_moves()` | halfmove_clock ≥ 150 | ✓ CORRECT |

### 3.2 Claimable Draw Treated as Automatic

| Check | Implementation | Issue |
|:---|:---|:---|
| `is_repetition(3)` | Treated as draw when `ply > 0` | Threefold is *claimable*, not automatic |
| 50-move rule (halfmove_clock ≥ 100) | **Not implemented** | Correctly absent from engine |

**Threefold Repetition Treatment:**

The engine calls `board.is_repetition(3)` and returns a draw score at `ply > 0`. This is an **intentional modeling choice** — treating threefold repetition as automatic avoids the engine playing into a repetition that a human opponent would claim. This is a **common and accepted practice** in chess engine design.

The `ply > 0` guard ensures:
- At the **root** (`ply == 0`): The engine does NOT automatically treat the position as a draw even if the position is repeated 3 times. The engine can search for a winning move to avoid the repetition.
- At **non-root plies**: The position is scored as 0 (draw), preventing the engine from choosing moves that lead to repetition when it can avoid them.

**50-move rule (halfmove_clock ≥ 100):**

The 50-move rule is a **claimable** draw, not automatic. The engine correctly does NOT auto-draw at halfmove_clock ≥ 100. A note from v0.41: Adding `halfmove_clock >= 100` checks caused test failures because it violated the TT semantics tests that expected non-draw behavior at that threshold.

### 3.3 Confirmed Absent: halfmove_clock >= 100

**Verification:** The three draw-check blocks in `_terminal_score`, `_quiescence`, and `_negamax` do NOT contain `halfmove_clock >= 100`. This is confirmed by reading the source code.

**Verdict:** ✓ CORRECT — 50-move claimable draw correctly excluded from automatic draw detection.

---

## 4. Draw Detection at Root

The root call to `_negamax` passes `ply=0`. Since the repetition check uses `ply > 0`, the engine will NOT immediately score the root position as a draw even if the position has been repeated 3 times. This is correct behavior — it allows the engine to search for a move that avoids the repetition.

---

## 5. NMP Halfmove Clock Guard

Both the RFP and NMP blocks include `board.halfmove_clock < 140`. This prevents null-move or futility pruning when the position is within 10 moves of the 75-move automatic draw threshold, avoiding incorrect pruning near draw-forced positions.

---

## 6. Known Limitations and Modeling Choices

| # | Item | Type | Impact |
|:---:|:---|:---|:---|
| 1 | Threefold repetition treated as automatic at ply > 0 | Intentional choice | LOW — standard engine practice |
| 2 | 50-move claimable draw not enforced | Correct omission | NONE — rule requires explicit claim |
| 3 | No opponent draw-claim modeling | Limitation | LOW — in game play, Stockfish will claim draws |
| 4 | Root does not auto-draw on threefold | Intentional (by ply > 0 guard) | CORRECT behavior |

---

## 7. Test Coverage

**Existing tests for draw semantics:**
- `tests/test_v041_repetition_quiescence.py` — 7 tests covering:
  - 3-fold repetition draw detection at ply > 0
  - Quiescence repetition draw
  - 75-move automatic draw (`is_seventyfive_moves()`)
  - Insufficient material draw
- `tests/test_zobrist_tt.py` — Includes TT draw-proximity guard tests

All 444 tests pass (verified at Phase A).

---

## 8. Phase D Verdict

**GATE D1 — Automatic draw implementation:** ✓ PASS  
**GATE D2 — Claimable draw (50-move) correctly absent:** ✓ PASS  
**GATE D3 — Threefold repetition draw is documented intentional choice:** ✓ PASS  
**GATE D4 — `halfmove_clock >= 100` correctly absent from draw blocks:** ✓ PASS  
**GATE D5 — Draw-proximity guard in NMP/RFP:** ✓ PASS (`halfmove_clock < 140`)

**Overall Phase D Status:** ✓ VERIFIED — Draw semantics are correct and well-tested.

**Key Limitation Documented:** The engine treats `is_repetition(3)` as an automatic draw at `ply > 0` — this is an intentional modeling choice that is standard in chess engine design and does not constitute a bug.

