# Project Janus v0.53 — Search Architecture Reconnaissance & PVS Insertion Audit

**Milestone:** v0.53  
**Target Codebase:** `analysis/v0.53/native/janus_native.cpp`  
**Parent Engine:** Janus Native N3 (v0.52 Category A Promoted Baseline)  
**Date:** 2026-11-05  

---

## 1. Architectural Survey of the N3 Search Core

The search core of Janus N3 is implemented in standard C++17 with zero dynamic heap allocations during search tree traversal.

### 1.1 Structural Search Flow Map

```mermaid
flowchart TD
    ID[native_search: Iterative Deepening Loop, depth = 1..max_depth] --> RootInit[Root Variable Setup & g_tt_age Increment]
    RootInit --> AlphaBeta["negamax(b, depth, alpha=-INF, beta=INF, ply=0)"]
    
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
    TermCheck -- Yes --> MateCheck{in_check?}
    MateCheck -- Yes --> Checkmate[Return -(MATE_SCORE - ply)]
    MateCheck -- No --> Stalemate[Return 0 cp]
    
    TermCheck -- No --> MoveOrder[score_move_for_ordering: Hash > Promo > Captures MVV-LVA > Quiets]
    MoveOrder --> LoopMoves[Iterate Ordered Moves 0..n-1]
    
    LoopMoves --> MakeMove[native_make_move & native_push_history]
    MakeMove --> MoveFork{moves_searched == 1?}
    
    MoveFork -- First Move (PV) --> FullWindowSearch["Search Child: [-beta, -alpha] at depth - 1"]
    MoveFork -- Subsequent Moves --> NullWindowSearch["PVS Candidate: [-alpha-1, -alpha]"]
    
    FullWindowSearch --> PopMove[native_pop_history & native_unmake_move]
    NullWindowSearch --> PopMove
    
    PopMove --> BetaCheck{score >= beta?}
    BetaCheck -- Yes (Beta Cutoff) --> BreakLoop[Break Move Loop]
    BetaCheck -- No --> AlphaCheck{score > alpha?}
    AlphaCheck -- Yes --> UpdateAlpha[alpha = score; Update g_pv_table[ply]]
    AlphaCheck -- No --> NextMove{More Moves?}
    
    NextMove -- Yes --> LoopMoves
    NextMove -- No --> TTStore[Store Transposition Table Entry: score_to_tt]
```

---

## 2. Component-by-Component Invariant Audit

| Search Component | Current Implementation in N3 | Status & Invariants | PVS Interaction / Impact |
|---|---|---|---|
| **Iterative Deepening** | Depth $1 \to \text{max\_depth}$ in `native_search` | Fully completed iterations stored in `out_res->depth` | Provides warm TT and reliable PV move for iteration $d+1$ |
| **Search Paradigm** | Full-Window Alpha-Beta Negamax | All child searches currently use $[-\beta, -\alpha]$ | **Primary Refactoring Target:** Replace with 1st move full window + subsequent null windows |
| **PV / Non-PV Nodes** | Implicit | Alpha and Beta define window; no explicit PV node flag | PVS introduces explicit handling of first move vs subsequent moves |
| **Quiescence Search** | Stand-pat + MVV-LVA Captures + Delta Pruning | Stand-pat cutoff at $\beta$; delta pruning margin $1100\text{ cp}$ | Evaluated at leaves ($depth \le 0$); receives narrowed $\alpha, \beta$ correctly |
| **Transposition Table** | 1,048,576 entries (16 MB), depth-preferred replacement with aging | Exact, Upper, Lower bound flags; mate score clamping | Null-window searches generate sharper Upper ($\le \alpha$) and Lower ($\ge \beta$) bounds |
| **Move Ordering** | TT Hash ($10^7$) $\to$ Promo ($9 \cdot 10^5$) $\to$ MVV-LVA ($10^5$) $\to$ Quiets ($0$) | Eager sort with `std::sort` | Crucial for PVS: if TT move is best, 1st move establishes true $\alpha$; rest fail low |
| **Late Move Reductions** | 10 guards: quiet, non-check, non-checking, $d \ge 3$, move $\ge 4$ | $R=1$ ply reduction; full-depth re-search if $score > \alpha$ | Interacts directly with PVS null windows (see Section 3) |
| **Draw Detection** | 50-move, insufficient material, 2-fold repetition in search tree | Evaluated strictly for $ply > 0$; returns $0\text{ cp}$ | Preserved unchanged |
| **Mate Distance** | Normalization via `score_to_tt` and `score_from_tt` | Offsets by $ply$ to preserve shortest mate distance | Must guard against overflow in null-window offsets |
| **Time Management** | Fischer allocation $(T + 40 \times \text{inc})/40$, reserve $50\text{ms}$ | Monotonic clock polled every 2048 nodes | Preserved unchanged |

---

## 3. PVS and LMR Interaction Analysis

In the current N3 search, every child search uses $[-\beta, -\alpha]$. When Late Move Reductions is active on move $m$ ($moves\_searched \ge 4$):
- Reduced probe: searches at $d_{\text{reduced}} = \max(1, d - 1 - R)$ with full window $[-\beta, -\alpha]$.
- Re-search: if $score > \alpha$, re-searches at $d - 1$ with full window $[-\beta, -\alpha]$.

### 3.1 PVS + LMR Combined Execution Flow:
When PVS is enabled, moves are partitioned into three distinct paths:

1. **Move 1 (Principal Variation Move):**
   - Full nominal child depth $d - 1$.
   - Full search window $[-\beta, -\alpha]$.
   - Zero LMR reduction.

2. **Subsequent Moves ($moves\_searched > 1$) NOT Eligible for LMR:**
   - Full nominal child depth $d - 1$.
   - **Null Window Probe:** $[-\alpha - 1, -\alpha]$.
   - If $score \le \alpha$: Accepted as fail-low (no re-search).
   - If $score > \alpha$ and $score < \beta$: **PVS Re-Search** at full nominal depth $d - 1$ with full window $[-\beta, -\alpha]$.
   - If $score \ge \beta$: Beta cutoff accepted directly.

3. **Subsequent Moves ($moves\_searched \ge 4$) ELIGIBLE for LMR:**
   - **Reduced Null Window Probe:** $[-\alpha - 1, -\alpha]$ at reduced depth $d_{\text{reduced}} = \max(1, d - 1 - R)$.
   - If $score \le \alpha$: Accepted as fail-low (both LMR and PVS prune this branch without re-search).
   - If $score > \alpha$:
     - Move unexpectedly succeeded at reduced depth.
     - **Stage 2 (Full-Depth Null-Window Re-search):** Search at full nominal depth $d - 1$ with null window $[-\alpha - 1, -\alpha]$.
     - If Stage 2 yields $score > \alpha$ and $score < \beta$:
       - **Stage 3 (Full-Depth Full-Window Re-search):** Search at full nominal depth $d - 1$ with full window $[-\beta, -\alpha]$.
     - If Stage 2 yields $score \le \alpha$: Fails low at full depth; no full-window search needed!

This 3-stage hierarchy guarantees that full-window searches ($[-\beta, -\alpha]$) are executed **only when a move has been proven to beat $\alpha$ at full nominal depth**, minimizing expensive wide-window searches across the entire tree.

