# Project Janus v0.56 — Capture Ordering Architecture Audit

**Milestone:** v0.56  
**Auditor:** Principal Chess Engine Architect & C++17 Search Systems Engineer  
**Date:** 2026-11-05  
**Target Codebase:** `analysis/v0.55/native/janus_native.cpp`  
**Classification:** Pre-Implementation Architectural Audit  

---

## 1. Executive Summary

This audit examines the capture-ordering and move-scoring pipeline of Janus Native N5 (`janus_native.cpp`). The current architecture relies on a classical multi-tier heuristic system: Transposition Table (TT) best move, pawn promotions, Most Valuable Victim – Least Valuable Attacker (MVV-LVA) captures, Killer moves (2 slots per ply), History heuristic table, and unranked quiet moves.

While computationally lightweight, pure MVV-LVA orders moves using only local attacker-victim piece types without considering whether the target square is defended. Consequently, **bad or suicidal captures** (such as $Q \times P$ on a heavily defended square) are scored ahead of proven quiet refutations (killer moves and high-scoring history moves).

---

## 2. Current Move Ordering Hierarchy in N5

In `analysis/v0.55/native/janus_native.cpp`, move scoring is governed by `score_move_for_ordering(const NativeBoard* b, uint16_t m, uint16_t tt_move, int ply)`:

$$\begin{array}{|c|l|c|l|}
\hline
\textbf{Tier} & \textbf{Move Category} & \textbf{Score Range} & \textbf{Scoring Logic} \\
\hline
1 & \text{Hash / TT Move} & 10,000,000 & \text{Matches TT entry best move} \\
2 & \text{Queen Promotion} & 900,000 & \text{Pawn promotion to Queen} \\
3 & \text{Underpromotion} & 800,000 & \text{Pawn promotion to Knight/Bishop/Rook} \\
4 & \mathbf{MVV-LVA \ Captures} & \mathbf{99,995 \dots 100,050} & \mathbf{100,000 + (10 \times \text{Victim}) - \text{Attacker}} \\
5 & \text{Killer Move 1} & 90,000 & \text{Primary quiet beta-cutoff at current ply} \\
6 & \text{Killer Move 2} & 80,000 & \text{Secondary quiet beta-cutoff at current ply} \\
7 & \text{History Quiet Moves} & 1 \dots 16,384 & \text{Historical cutoff counter: } \min(16384, \text{history}) \\
8 & \text{Unranked Quiet Moves} & 0 & \text{Default fallback} \\
\hline
\end{array}$$

### 2.1 MVV-LVA Capture Scoring Formula
```cpp
if (victim != NO_PIECE) {
    int attacker = NO_PIECE;
    for (int p = 0; p < 6; p++) {
        if (b->pieces[b->side_to_move][p] & (1ULL << from)) {
            attacker = p;
            break;
        }
    }
    return 100000 + (victim * 10) - attacker;
}
```
Piece indices are:
- `PAWN` = 0
- `KNIGHT` = 1
- `BISHOP` = 2
- `ROOK` = 3
- `QUEEN` = 4
- `KING` = 5

#### Representative MVV-LVA Scores:
- $P \times Q$: $100,000 + (10 \times 4) - 0 = 100,040$ (Best possible capture)
- $N \times Q$: $100,000 + (10 \times 4) - 1 = 100,039$
- $P \times R$: $100,000 + (10 \times 3) - 0 = 100,030$
- $P \times P$: $100,000 + (10 \times 0) - 0 = 100,000$
- $Q \times P$: $100,000 + (10 \times 0) - 4 = 99,996$
- $K \times P$: $100,000 + (10 \times 0) - 5 = 99,995$ (Worst capture score)

---

## 3. Structural Deficiencies of the MVV-LVA Pipeline

### 3.1 Inversion Between Bad Captures and Killer Moves
Because all captures receive scores in $[99,995, 100,050]$, every legal capture—regardless of whether it is defended or completely suicidal—is searched before Killer Move 1 ($90,000$), Killer Move 2 ($80,000$), and history-ranked quiet moves.

**Concrete Failure Mode:**
Suppose White has a choice between:
1. $Q \times P$ where the pawn on $e5$ is defended by Black's $d6$-pawn and $c6$-knight.
2. A quiet move $Nf3-g5$ that previously produced a beta cutoff at this ply (Killer 1).

Under MVV-LVA:
- $Q \times P$ is scored $99,996$.
- $Nf3-g5$ is scored $90,000$.

The engine is forced to search $Q \times P$ first, explore the entire sub-tree refuting the queen sacrifice, and only then search $Nf3-g5$. If $Nf3-g5$ produces an immediate cutoff, the entire search subtree of $Q \times P$ was wasted.

### 3.2 Capture Ordering in Quiescence Search
In `quiescence(NativeBoard* b, int alpha, int beta, ...)`:
```cpp
for (int i = 0; i < n; i++) {
    uint16_t m = moves[i];
    int to = move_to(m);
    int them = 1 - b->side_to_move;
    bool is_cap = (b->occupancy[them] & (1ULL << to)) || (move_flag(m) == 2);
    if (is_cap || move_flag(m) == 3) {
        caps[n_caps++] = { m, score_move_for_ordering(b, m, 0, 0) };
    }
}
std::sort(caps, caps + n_caps, [](const ScoredMove& a, const ScoredMove& b) {
    return a.score > b.score;
});
```
In quiescence search:
- Captures are ordered strictly by MVV-LVA.
- Equal-piece trades (e.g. $B \times N$) and losing captures ($B \times P$ defended) are interspersed. Searching losing captures before equal trades delays finding beta cutoffs and increases quiescence node explosion.

### 3.3 Indirect Interactions with Late Move Reductions (LMR)
Under N5's LMR specification:
```cpp
bool is_lmr_eligible = g_use_lmr &&
                       (ply > 0) &&
                       (depth >= g_lmr_min_depth) &&
                       (moves_searched >= g_lmr_move_threshold) &&
                       !in_check &&
                       (undo.captured_piece == NO_PIECE) &&
                       (move_flag(m) != 3) &&
                       (m != tt_move) &&
                       (native_is_check(b) == 0);
```
- Captures themselves are **never reduced**.
- However, if 2 or 3 losing captures are searched upfront at moves 2, 3, 4, they increment `moves_searched`. Consequently, the subsequent quiet moves cross the `g_lmr_move_threshold` (threshold = 4) earlier than they otherwise would, indirectly changing the reduction depth of subsequent quiet moves.

---

## 4. Call Graph & Execution Paths

```
negamax(...)
  |-- TT Probe -> tt_move (Score = 10,000,000)
  |-- native_generate_legal_moves(...) -> moves[0..n-1]
  |-- for each move:
  |     score_move_for_ordering(...)
  |       |-- Promo Check -> 900,000 / 800,000
  |       |-- Capture Check -> MVV-LVA [99,995 .. 100,050]
  |       |-- Killer Check -> 90,000 / 80,000
  |       |-- History Check -> min(16,384, history)
  |       +-- Quiet Fallback -> 0
  |-- std::sort(scored_moves, scored_moves + n)
  +-- Move loop (search with LMR and PVS)
        |
        +-- Leaf Node (depth <= 0)
              |
              +-- quiescence(...)
                    |-- Stand-pat evaluate
                    |-- Delta pruning check (stand_pat + 1100 < alpha)
                    |-- Filter captures & promotions
                    |-- Score captures via score_move_for_ordering(...)
                    |-- std::sort(caps, caps + n_caps)
                    +-- Quiescence move loop
```

---

## 5. Architectural Objectives for Candidate N7

To address the limitations of pure MVV-LVA without altering search semantics or pruning captures:
1. **Partition Captures via SEE:**
   - **SEE-Winning / SEE-Neutral ($\text{SEE} \ge 0$):** Retain high priority ahead of killer moves. Sub-order by MVV-LVA or net SEE value.
   - **SEE-Losing ($\text{SEE} < 0$):** Demote below killer moves and high-scoring history moves, but keep them ahead of unranked quiet moves.
2. **Quiescence Search Ordering:**
   - Search winning and equal captures first.
   - Delay losing captures to the tail of the quiescence move list, maximizing early cutoffs from stand-pat or equal exchanges.
3. **Strict Non-Pruning Invariant:**
   - Every capture generated as legal in N5 remains fully searched. No moves are omitted or pruned based on SEE.
