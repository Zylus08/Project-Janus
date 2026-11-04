# Project Janus v0.52 — Late Move Reductions (LMR) Design Specification

## 1. Theoretical Foundation & Governing Principles

In chess engine alpha-beta search, the **null-window / fail-low principle** states that if move ordering is effective, the vast majority of legal child moves at internal nodes will fail low ($score \le \alpha$) and will never contribute to the principal variation (PV). 

Searching unpromising, late-ordered quiet moves at full nominal depth wastes computational effort. **Late Move Reductions (LMR)** exploits this observation by searching late quiet moves at a reduced depth ($d - 1 - R$). If the move indeed fails low, the cutoff/bound is established with a fraction of the search tree size. If the move unexpectedly proves strong ($score > \alpha$), the reduction assumption is refuted, and the move is immediately re-searched at full nominal depth ($d - 1$).

---

## 2. Eligibility & Tactical Safety Invariants

A candidate move $m$ is reduced if and only if **all ten of the following conditions are simultaneously satisfied**:

```
+----------------------------------------------------------------------------------------------------------+
|                                    LMR ELIGIBILITY FILTER (ALL REQUIRED)                                 |
+----+--------------------------------+--------------------------------------------------------------------+
| #  | Eligibility Condition          | Exact Guard Expression                                             |
+----+--------------------------------+--------------------------------------------------------------------+
| 1  | Global Feature Activation      | g_use_lmr == true                                                  |
| 2  | Non-Root Node                  | ply > 0                                                            |
| 3  | Minimum Depth Threshold        | depth >= g_lmr_min_depth (Default: 3)                              |
| 4  | Move Ordering Rank Threshold   | moves_searched >= g_lmr_move_threshold (Default: 4th searched move)|
| 5  | Node Free from Check           | !in_check (Side to move is not currently in check)                 |
| 6  | Quiet Move (Non-Capture)       | undo.captured_piece == EMPTY_PIECE                                 |
| 7  | Non-Promotion Move             | m_flags < MOVE_PROMO_N                                             |
| 8  | Non-Checking Move              | !native_is_check(b) (Move does not deliver check to opponent king) |
| 9  | Non-Hash Move                  | m != tt_move (Transposition Table move is immune)                  |
| 10 | Non-Killer Move                | m != g_killer_moves[ply][0] && m != g_killer_moves[ply][1]         |
+----+--------------------------------+--------------------------------------------------------------------+
```

---

## 3. Reduction Formulation & Re-Search Protocol

### 3.1 Depth Allocation
- Nominal child depth: $d_{\text{nominal}} = \text{depth} - 1$.
- Reduction amount: $R = \text{g\_lmr\_base\_reduction}$ (Default: $1\text{ ply}$).
- Reduced search depth:
  $$d_{\text{reduced}} = \max(1, d_{\text{nominal}} - R)$$

### 3.2 Full-Depth Re-Search Policy
```cpp
// 1. Initial Reduced-Depth Probe
score = -negamax(b, d_reduced, -beta, -alpha, ply + 1, nodes, deadline, aborted, &child_best);

// 2. Re-Search Guard
if (score > alpha && !aborted) {
    g_lmr_researches++;
    // Re-search at full nominal depth
    score = -negamax(b, d_nominal, -beta, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
}
```

- If $score \le \alpha$, the fail-low result is accepted, and the reduction successfully pruned downstream branches.
- If $score > \alpha$, the candidate move is re-searched at full depth before updating `alpha` or recording PV lines.
- Transposition table updates use the actual depth of the search that produced the final accepted score.

---

## 4. UCI Protocol Configuration & Options

The native executable supports the following standard UCI options:

```
option name UseLMR type check default false
option name LMRMinDepth type spin default 3 min 2 max 8
option name LMRMoveThreshold type spin default 4 min 2 max 16
option name LMRBaseReduction type spin default 1 min 1 max 3
```

- When `UseLMR=false` (default), the engine executes the bit-exact N2 baseline search algorithm.
- Options can be set dynamically via `setoption name <name> value <value>` before or between games.

---

## 5. Telemetry & Instrumentation

The engine maintains dedicated atomic/static telemetry counters:
- `g_lmr_eligible_moves`: Total legal moves meeting all eligibility filters.
- `g_lmr_reduced_moves`: Total moves searched with reduced depth.
- `g_lmr_researches`: Total moves requiring full-depth re-search.
- `g_lmr_cutoffs`: Beta cutoffs achieved directly from reduced-depth searches.
- Exported query function: `native_get_lmr_telemetry(uint64_t* out_array)`.

