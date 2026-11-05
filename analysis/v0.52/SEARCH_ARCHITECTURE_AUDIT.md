# Project Janus v0.52 — Native Search Architecture Audit & LMR Insertion Analysis

## 1. Architectural Survey of Candidate N2 Search Core

The search core of Candidate N2 (`analysis/v0.51/native/janus_native.cpp`) is implemented in standard C++17 with strict zero-heap memory allocation during tree traversal.

### 1.1 Structural Search Flow Map

```mermaid
flowchart TD
    ID[native_search: Iterative Deepening Loop, depth = 1..max_depth] --> RootInit[Root Variable Setup & g_tt_age Increment]
    RootInit --> AlphaBeta["negamax(b, depth, alpha, beta, ply=0)"]
    
    AlphaBeta --> TimeCheck{Nodes & 2047 == 0?}
    TimeCheck -- Yes --> ClockPoll{Now >= Deadline?}
    ClockPoll -- Yes --> AbortSearch[Set aborted = true; Return 0]
    ClockPoll -- No --> RepCheck{ply > 0?}
    TimeCheck -- No --> RepCheck
    
    RepCheck -- Yes --> DrawEval[Fifty-Move Rule / Insufficient Material / native_is_repetition(2)]
    DrawEval -- Draw Detected --> ReturnZero[Return 0 cp]
    DrawEval -- No Draw --> LeafCheck{depth <= 0 or ply >= 127?}
    RepCheck -- No --> LeafCheck
    
    LeafCheck -- Yes --> QSearch[quiescence: MVV-LVA Captures + Delta Pruning]
    LeafCheck -- No --> TTProbe[Transposition Table Probe: g_tt[key % TT_SIZE]]
    
    TTProbe --> TTCheck{TT Hit & depth >= entry.depth & ply > 0?}
    TTCheck -- Yes (Exact/Bound Cutoff) --> ReturnTT[Return score_from_tt]
    TTCheck -- No --> GenMoves[native_generate_legal_moves: Pins & Checks]
    
    GenMoves --> TermCheck{n == 0?}
    TermCheck -- Yes --> MateCheck{native_is_check?}
    MateCheck -- Yes --> Checkmate[Return -(MATE_SCORE - ply)]
    MateCheck -- No --> Stalemate[Return 0 cp]
    
    TermCheck -- No --> MoveOrder[score_move_for_ordering: Hash > Captures > Killers > History]
    MoveOrder --> LoopMoves[Iterate Ordered Moves 0..n-1]
    
    LoopMoves --> MakeMove[native_make_move & native_push_history]
    MakeMove --> SubtreeSearch["negamax(b, depth - 1, -beta, -alpha, ply + 1)"]
    SubtreeSearch --> PopMove[native_pop_history & native_unmake_move]
    
    PopMove --> BetaCheck{score >= beta?}
    BetaCheck -- Yes (Beta Cutoff) --> BreakLoop[Save Killer Move; Break Loop]
    BetaCheck -- No --> AlphaCheck{score > alpha?}
    AlphaCheck -- Yes --> UpdateAlpha[alpha = score; Update g_pv_table[ply]]
    AlphaCheck -- No --> NextMove{More Moves?}
    
    NextMove -- Yes --> LoopMoves
    NextMove -- No --> TTStore[Store Transposition Table Entry: score_to_tt]
```

---

## 2. Component-Level Invariant Audit

| Search Component | Implementation in N2 | Invariant / Semantic Guarantees |
|---|---|---|
| **Iterative Deepening** | Depth-by-depth ($1 \to \text{max\_depth}$) in `native_search` | Preserves PV line from previous iteration; warm TT speeds up deeper iterations |
| **Search Paradigm** | Standard Alpha-Beta Negamax | Full window $[-\beta, -\alpha]$ across all child nodes; PVS / zero-window search not yet implemented |
| **Quiescence Search** | Stand-pat + MVV-LVA capture ordering + delta pruning ($900\text{ cp}$) | Evaluates checks/captures until quiet terminal frontier is reached |
| **Transposition Table** | 1,048,576 entries ($16\text{ MB}$), depth-preferred replacement with aging | Clamps mate scores with `score_to_tt(score, ply)` and `score_from_tt(score, ply)` |
| **Move Ordering** | Hash Move ($2,000,000$) $\to$ MVV-LVA ($10,000 + 10V - A$) $\to$ Killer 1 ($9,000$) $\to$ Killer 2 ($8,000$) $\to$ History ($0 \to 7,999$) | Eager sort via `std::sort` |
| **Draw Detection** | 50-move rule, insufficient material, and twofold in-tree repetition heuristic | Returns $0\text{ cp}$ strictly for `ply > 0` |
| **Time Management** | Fischer allocation: $(T + 40 \times \text{inc}) / 40$ with $50\text{ms}$ reserve | Monotonic clock polled every 2,048 nodes |

---

## 3. LMR Insertion Point & Safety Requirements

In the current N2 search, every legal child move is searched with full nominal child depth $d - 1$:
```cpp
int score = -negamax(b, depth - 1, -beta, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
```

### Safety Requirements for LMR Integration:
1. **Root Immunity:** Moves at `ply == 0` must never be reduced.
2. **Tactical Immunity:** In-check positions (`in_check`), capture moves (`undo.captured_piece != EMPTY_PIECE`), pawn promotions, and checking moves must never be reduced.
3. **Priority Immunity:** Hash moves (`tt_move`) and Killer moves (`g_killer_moves`) must never be reduced.
4. **Depth Floor:** Shallow searches (`depth < 3`) must never be reduced ($d_{\text{reduced}} \ge 1$).
5. **Re-Search Obligation:** If a reduced-depth search yields `score > alpha`, the reduction is assumed to be an inaccurate heuristic shortcut, and a full-depth re-search with nominal depth $d - 1$ must be executed before updating `alpha` or the PV table.
6. **Default-Safe Toggling:** A global runtime option `g_use_lmr` (accessible via UCI `UseLMR`) must allow instant, zero-leak toggling back to baseline N2 search.

### Exact Insertion Architecture:
```cpp
bool is_lmr_eligible = g_use_lmr && (ply > 0) && (depth >= g_lmr_min_depth) &&
                       (moves_searched >= g_lmr_move_threshold) && !in_check &&
                       (undo.captured_piece == EMPTY_PIECE) && (m_flags < MOVE_PROMO_N) &&
                       !native_is_check(b) && (m != tt_move) &&
                       (m != g_killer_moves[ply][0]) && (m != g_killer_moves[ply][1]);

int child_depth = depth - 1;
if (is_lmr_eligible) {
    int reduction = g_lmr_base_reduction;
    int reduced_depth = std::max(1, child_depth - reduction);
    score = -negamax(b, reduced_depth, -beta, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
    if (score > alpha && !aborted) {
        // Full-depth re-search
        score = -negamax(b, child_depth, -beta, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
    }
} else {
    score = -negamax(b, child_depth, -beta, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
}
```

This insertion preserves all baseline semantics when `UseLMR=false` and guarantees that no reduced move can establish an unverified score above `alpha`.

