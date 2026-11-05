# PROJECT JANUS v0.54 — MOVE ORDERING ARCHITECTURE AUDIT

**Phase:** Phase 1 — Move Ordering Architecture Audit  
**Date:** 2026-11-05  
**Baseline Engine:** Janus Native N3 (C++17, LMR enabled, PVS disabled)  

---

## 1. Executive Summary

This audit inspects the complete move-ordering pipeline of the compiled C++17 Janus search core (`janus_native.cpp`), examines the interactions between move ordering and pruning/reduction heuristics (LMR, PVS, Quiescence Search), and establishes the quantitative baseline for move-ordering effectiveness.

---

## 2. Current Move Ordering Hierarchy (Production Baseline N3)

The production engine sorts all generated legal moves in `negamax()` via `score_move_for_ordering()` followed by `std::sort()`:

```
+----+--------------------------+-----------------------+------------------------------------------+
| #  | Category                 | Ordering Score Range  | Implementation Logic                     |
+----+--------------------------+-----------------------+------------------------------------------+
| 1  | Transposition Table Move | 10,000,000            | m == tt_move                             |
| 2  | Queen Promotion          | 900,000               | move_flag == 3 && move_promo == QUEEN    |
| 3  | Underpromotions          | 800,000               | move_flag == 3 && move_promo != QUEEN    |
| 4  | Tactical Captures        | 99,996 - 100,040      | 100,000 + (victim * 10) - attacker       |
| 5  | Killer Moves             | NONE (0)              | Not implemented in N3                    |
| 6  | History-Scored Quiets    | NONE (0)              | Not implemented in N3                    |
| 7  | All Other Quiet Moves    | 0                     | Arbitrary move-generator order           |
+----+--------------------------+-----------------------+------------------------------------------+
```

### 2.1 Capture Ordering Mechanism
- Captures are ordered strictly via **MVV-LVA** (Most Valuable Victim – Least Valuable Attacker) using integer piece indices:
  $$\text{Score} = 100,000 + 10 \times \text{Victim} - \text{Attacker}$$
  Where $\text{Piece} \in \{ \text{Pawn}: 0, \text{Knight}: 1, \text{Bishop}: 2, \text{Rook}: 3, \text{Queen}: 4, \text{King}: 5 \}$.
- Maximum capture score: Pawn takes Queen ($100,000 + 40 - 0 = 100,040$).
- Minimum capture score: Queen takes Pawn ($100,000 + 0 - 4 = 99,996$).
- En Passant captures are treated as Pawn victims ($100,000 + 0 - 0 = 100,000$).
- Static Exchange Evaluation (SEE) is absent; losing captures (e.g., $Q \times P$ defended by $P$) are ordered alongside winning captures. (Per milestone constraints, SEE is not introduced in v0.54).

### 2.2 The Quiet Move Bottleneck
All non-capture, non-promotion moves receive score `0`. Because `std::sort()` is used on moves with identical score `0`, quiet moves are searched in the order they happen to be produced by `native_generate_legal_moves()`. There is no mechanism to remember which quiet moves were effective at sibling nodes or shallower plies.

---

## 3. Subsystem Interactions

### 3.1 Interaction with Late Move Reductions (LMR)
LMR reduces quiet moves when:
- `moves_searched >= g_lmr_move_threshold` (Default: 4).
- `undo.captured_piece == NO_PIECE` (Quiet move).
- `depth >= 3` and `ply > 0` and `!in_check` and move is non-checking.

**Critical Weakness:** Because quiet moves are unordered, a strong quiet move (e.g., an unblockable tactical threat or defensive maneuver) may be placed at move index 5 or 6 simply because of move generation ordering. It is then reduced by $R = 1$, fails low, or requires an expensive full-depth re-search. If it were prioritized into move indices 1, 2, or 3 (via killer or history), it would be searched at full depth immediately, producing a fast beta cutoff without reduction or re-search overhead.

### 3.2 Interaction with Principal Variation Search (PVS)
PVS searches moves after the first with null window $[-\alpha - 1, -\alpha]$. If a late move fails high, PVS triggers a full-window re-search. Better move ordering ensures that if a quiet move is the best move in the position, it is searched earlier, minimizing null-window re-search cycles.

### 3.3 Interaction with Quiescence Search
In `quiescence()`, only captures are generated and searched. Killer moves and history heuristic apply strictly to quiet moves in regular `negamax()`. They have zero impact on quiescence search, preserving quiescence correctness.

### 3.4 Interaction with Transposition Table
The TT move is always assigned score $10,000,000$. Killer moves ($90,000$ / $80,000$) and history moves ($1 - 70,000$) are strictly lower in priority than the TT move and all captures ($>99,990$). Therefore, the TT move is guaranteed to be searched first whenever present.

---

## 4. Quantitative Baseline Search Profile

Across the 53-position diagnostic benchmark suite at fixed depth 6 in N3:
- **Total Nodes:** 8,539,679
- **Wall Time:** 32.82 s
- **Effective NPS:** ~260,000 NPS
- **Beta Cutoffs Caused by First Move:** ~74.2% (dominated by TT moves)
- **Beta Cutoffs Caused by Quiet Moves:** ~18.5%
- **LMR Re-search Rate:** 1.39%

---

## 5. Architectural Objectives for Janus N5

1. Implement **two killer move slots per search ply**: `killer_moves[MAX_PLY][2]`.
2. Implement a **history heuristic table**: `history[2][64][64]`.
3. Expose independent UCI options: `UseKillerOrdering` and `UseHistoryOrdering`.
4. Ensure zero alteration to baseline behavior when both options are disabled.
5. Provide comprehensive telemetry to quantify move-ordering contributions across all four experimental configurations (C0, C1, C2, C3).

