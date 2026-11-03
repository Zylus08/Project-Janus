# Search Architecture & Move-Ordering Audit — v0.46

**Milestone:** Project Janus v0.46  
**Date:** 2026-11-03  
**Auditor:** Autonomous Senior Chess-Engine Researcher & Search Algorithm Engineer  
**Status:** COMPLETE (Gate B Validated)

---

## 1. Executive Summary

This audit establishes the concrete execution lifecycle, move-ordering priority hierarchy, and state invariant guarantees in Project Janus (`src/janus/search.py` and `src/janus/uci.py`).

The search engine implements a single-threaded negamax alpha-beta search enhanced with iterative deepening, aspiration windows, principal variation search (PVS), late move reductions (LMR), conservative null-move pruning (NMP), transposition tables (TT), and Reverse Futility Pruning (RFP, disabled in production).

---

## 2. Search Execution Pipeline

The 12-stage execution flow operates as follows:

```
[1] UCI Ingestion (`uci.py:278-361`):
    Parse "go" command tokens (`wtime`, `btime`, `movetime`, `depth`). Allocate time budget.
      │
[2] Root Initialization (`search.py:1059-1083`):
    Set deadline `self.deadline = start + time_limit`. Reset node counters and telemetry queues.
      │
[3] Iterative Deepening Loop (`search.py:1218-1375`):
    Iterate nominal depth $d = 1, 2, \dots, \text{max\_depth}$.
      │
[4] Transposition Table Probe (`search.py:326-353`):
    Probe Zobrist hash key. Retrieve cached bounds, score, and `tt_move`.
      │
[5] Frontier Pruning Evaluation (`search.py:869-925`):
    - RFP (Static NMP) if enabled: $static\_eval - margin \ge \beta$ at $d \le 2$.
    - NMP if enabled: null move search at reduced depth $d - 1 - R$ at $d \ge 3$.
      │
[6] Legal Move Generation (`search.py:673`):
    Generate complete legal move list: `moves = list(board.legal_moves)`.
      │
[7] Move Scoring & Full Sorting (`search.py:582-684`):
    Every legal move is scored by `_move_order_score` and fully sorted via Python's Timsort (`moves.sort(reverse=True)`).
      │
[8] Move Search Loop (`search.py:984-1065`):
    - PV Move (index 0): Full-window search $[- \beta, - \alpha]$.
    - Later Moves (index > 0): Null-window scout search $[- \alpha - 1, - \alpha]$ via PVS.
      │
[9] Late Move Reductions (LMR) (`search.py:990-1035`):
    Quiet non-check moves at index $\ge 3$ and depth $\ge 3$ searched with reduced depth $d - 2$.
    If score $> \alpha$, re-search at full depth.
      │
[10] Quiescence Search (`search.py:734-805`):
     Invoked at horizon ($d \le 0$). Evaluates stand-pat score and searches legal captures (and promotions) ordered by MVV/LVA.
      │
[11] Search Interruption Handling (`search.py:515-521`, `1230-1280`):
     Check deadline every 128 nodes (`nodes & 127 == 0`). If deadline exceeded, raise `SearchTimeout`.
     Recursive stack unwinds via `try...finally: board.pop()`. Interrupted iteration discarded.
      │
[12] Result Publication (`search.py:1270-1378`):
     Publish move, score, PV, and depth from the last completed iteration to UCI `bestmove`.
```

---

## 3. Concrete Move-Ordering Hierarchy

The move ordering score is computed in `_move_order_score` (lines 582–643):

| Tier | Move Category | Score / Priority | Condition / Notes |
|---|---|---|---|
| **1** | **Transposition Table Move** | **$10,000,000$** | `move == tt_move` (searched first) |
| **2** | **Capture with Promotion** | $\approx 1,800,000 + \text{promo}$ | Capture that also promotes pawn |
| **3** | **Winning / Equal Captures** | **$1,000,000 + \text{MVV\_LVA}$** | With SEE off (default): all captures. With SEE on: $\text{SEE} \ge 0$. |
| **4** | **Quiet Promotions** | **$800,000 + \text{promo}$** | Non-capture pawn promotions ($800,002\text{--}800,005$) |
| **5** | **Primary Killer Move** | **$700,000$** | `move == self.killers[ply][0]` |
| **6** | **Secondary Killer Move** | **$600,000$** | `move == self.killers[ply][1]` |
| **7** | **Countermove** | **$550,000$** | If enabled: `move == countermoves[from][to]` |
| **8** | **Losing Captures (SEE < 0)** | $50,000 + 10 \times \text{SEE} + \text{MVV\_LVA}$ | Only active when `enable_see_ordering = True` |
| **9** | **Quiet History Moves** | **$0\text{--}500,000$** | `history[from][to]` (clamped to $500,000$) |
| **10** | **Unranked Quiet Moves** | **$0$** | Moves with 0 history score |

### Structural Property: Eager Full Sort vs Incremental Selection
- Janus executes **eager full sorting**: `moves.sort(key=lambda m: self._move_order_score(...), reverse=True)`.
- It evaluates and sorts all $N$ legal moves up front.
- If move 0 causes a beta cutoff (as occurs in $\sim 80\text{--}90\%$ of cutoff nodes in efficient alpha-beta search), the time spent computing scores and sorting moves $1, \dots, N-1$ is computational waste.

---

## 4. State Invariants & Correctness Audit

1. **Board State Invariance:**
   - `_move_order_score` only inspects `board.piece_at()` and `board.is_capture()`. It never modifies piece locations, turn, or move stacks.
2. **TT Move Legality:**
   - In `_ordered_moves`, `moves = list(board.legal_moves)` generates all legal moves first.
   - `move == tt_move` is tested exclusively against members of this legal list. An illegal or corrupted TT move is never emitted.
3. **History and Killer Update Scopes:**
   - Killer moves are updated exclusively on quiet beta cutoffs (`not is_capture and not is_promotion`, line 1073).
   - History table updates are similarly restricted to quiet cutoff moves.
4. **Exception Safety:**
   - All `board.push()` calls are matched with `finally: board.pop()`. Stack unwinding on `SearchTimeout` leaves the board clean.

---

## 5. Gate B Conclusion & Sign-Off

The search pipeline and move-ordering mechanisms are verified to be structurally sound and free of state-corruption defects.

**Gate B Status:** **PASS** — Proceeding to Phase C (Move-Ordering Instrumentation).
