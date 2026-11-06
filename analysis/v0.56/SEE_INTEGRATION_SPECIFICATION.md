# Project Janus v0.56 — SEE Integration & Feature Isolation Specification

**Milestone:** v0.56  
**Architect:** Principal Chess Engine Architect & C++17 Search Systems Engineer  
**Date:** 2026-11-05  
**Candidate Architecture:** Janus Native N7  
**Control Baseline:** Janus Native N5  

---

## 1. Feature Isolation Matrix

Milestone v0.56 isolates the capture-ordering impact of Static Exchange Evaluation in main alpha-beta search and quiescence search via two orthogonal UCI configuration options:

$$\begin{array}{|l|c|c|l|}
\hline
\textbf{Ablation Arm} & \textbf{UseSEEOrdering} & \textbf{UseSEEInQuiescence} & \textbf{Architectural Description} \\
\hline
S_0\text{ (Baseline N5)} & \text{false} & \text{false} & \text{Pure MVV-LVA in main search and quiescence (Frozen Baseline)} \\
S_1\text{ (Main Search Only)} & \text{true} & \text{false} & \text{SEE in Alpha-Beta main search; quiescence unchanged} \\
S_2\text{ (Quiescence Only)} & \text{false} & \text{true} & \text{Quiescence search ordered by SEE; main search unchanged} \\
S_3\text{ (Candidate N7)} & \mathbf{true} & \mathbf{true} & \mathbf{Combined \ SEE \ in \ both \ Main \ Search \ and \ Quiescence} \\
\hline
\end{array}$$

### 1.1 UCI Options
```text
option name UseSEEOrdering type check default false
option name UseSEEInQuiescence type check default false
```
By default, both flags are `false`, ensuring that Janus boots bit-exact to the production baseline N5 (`UseKillerOrdering=true`, `UseHistoryOrdering=true`, `UsePVS=false`, `UseLMR=true`).

---

## 2. Main Search Move-Scoring Policy ($S_1$ and $S_3$)

When `UseSEEOrdering=true`, moves in `negamax(...)` are scored by `score_move_for_ordering(...)` according to the following tiered priority schedule:

$$\begin{array}{|c|l|c|l|}
\hline
\textbf{Tier} & \textbf{Move Category} & \textbf{Score Range} & \textbf{Scoring Formula \& Tie-Breaking} \\
\hline
1 & \text{TT / Hash Move} & 10,000,000 & \text{Exact match with Transposition Table best move} \\
2 & \text{Queen Promotion} & 900,000 & \text{Pawn promotion to Queen} \\
3 & \text{Underpromotion} & 800,000 & \text{Pawn promotion to Knight, Bishop, or Rook} \\
4 & \mathbf{SEE-Winning \ Captures \ (SEE > 0)} & \mathbf{100,000 \dots 100,050} & \mathbf{100,000 + (10 \times \text{Victim}) - \text{Attacker}} \\
5 & \mathbf{SEE-Neutral \ Captures \ (SEE == 0)} & \mathbf{95,000 \dots 95,050} & \mathbf{95,000 + (10 \times \text{Victim}) - \text{Attacker}} \\
6 & \text{Killer Move 1} & 90,000 & \text{Primary quiet cutoff at current search ply} \\
7 & \text{Killer Move 2} & 80,000 & \text{Secondary quiet cutoff at current search ply} \\
8 & \mathbf{SEE-Losing \ Captures \ (SEE < 0)} & \mathbf{10,000 \dots 20,050} & \mathbf{20,000 + \max(-10000, \text{SEE}) + (10 \times \text{Victim}) - \text{Attacker}} \\
9 & \text{History Quiet Moves} & 1 \dots 16,384 & \min(16384, \text{history score}) \\
10 & \text{Unranked Quiet Moves} & 0 & \text{Default fallback for non-cutoff quiets} \\
\hline
\end{array}$$

### 2.1 Demotion of Bad Captures
- In baseline N5, a losing capture such as $Q \times P$ defended is scored $99,996$, placing it above Killer 1 ($90,000$) and Killer 2 ($80,000$).
- In Candidate N7 ($S_1 / S_3$), $Q \times P$ has $\text{SEE} = -800$, scoring $20,000 - 800 - 4 = 19,196$.
- This places $Q \times P$ **below Killer 1 and Killer 2**, but **above unranked quiet moves ($0$)**. If Killer 1 refutes the position with a beta cutoff, the suicidal queen sacrifice is never searched!

---

## 3. Quiescence Search Policy ($S_2$ and $S_3$)

In `quiescence(...)`:
```cpp
if (g_use_see_in_quiescence) {
    int see_val = janus_see(b, m);
    if (see_val > 0) score = 100000 + (victim * 10) - attacker;
    else if (see_val == 0) score = 95000 + (victim * 10) - attacker;
    else score = 10000 + std::max(-10000, see_val) + (victim * 10) - attacker;
} else {
    score = score_move_for_ordering(b, m, 0, 0); // Pure MVV-LVA
}
```

### 3.1 Non-Pruning Invariant
**SEE-based pruning is explicitly prohibited.**
- Every capture generated as legal in quiescence remains searched.
- No captures are discarded or pruned on the basis of negative SEE.
- Only the order in which captures are visited by alpha-beta traversal is altered.

---

## 4. Preservation of Late Move Reductions (LMR)

Under N7, the LMR eligibility condition remains strictly unchanged:
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
- Captures are **never reduced**.
- Because losing captures are searched later (after killer moves), quiet killer moves are searched earlier (at lower `moves_searched`), ensuring that killer moves are searched at full depth before quiet move reduction thresholds are reached.
