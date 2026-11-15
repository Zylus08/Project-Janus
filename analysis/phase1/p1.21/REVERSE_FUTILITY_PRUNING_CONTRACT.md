# Reverse Futility Pruning (RFP) Contract: Mathematical Specification & Correctness Audit

**Milestone:** Phase 1, Milestone P1.21 — Phase 2  
**Auditor:** Principal Computer Chess Engine Architect, C++17 Search Engineer, and Tactical Search Specialist  
**Repository:** `E:\ChessXML\project-janus-phase1`  
**Current HEAD:** `c232730`  

---

## 1. Mathematical Specification of the RFP Contract

Reverse Futility Pruning (also known as Static Null-Move Pruning) is an alpha-beta search selectivity heuristic designed to prune shallow non-PV subtrees when the static evaluation of the current position exceeds the $\beta$ bound by a safety margin so large that a fail-high is virtually guaranteed even without searching candidate moves.

In `engine/classical_x/janus_classical_x.cpp` (lines 4765–4778), the exact controlling condition is:

$$\text{RFP Cutoff Condition} \iff \begin{cases}
\text{depth} \le 3 \\
\text{ply} > 0 \\
\neg\text{in\_check} \\
|\beta| < \text{MATE\_SCORE} - 100 \\
\text{StaticEval} - \text{Margin}(\text{depth}) \ge \beta
\end{cases}$$

Where the evaluation margin function $\text{Margin}(d)$ is defined as:

$$\text{Margin}(d) = M_{\text{depth}} \times d + \Delta_{\text{safety}}(d)$$

With configuration parameters:
- **1-Thread ($T=1$):** $M_{\text{depth}} = 120\text{ cp}$ per ply ($d=1 \implies 120$, $d=2 \implies 240$, $d=3 \implies 360$).
- **4-Thread SMP ($T=4$):** $M_{\text{depth}} = 90\text{ cp}$ per ply ($d=1 \implies 90$, $d=2 \implies 180$, $d=3 \implies 270$).
- **Safety Delta:** $\Delta_{\text{safety}}(d) = 40 \times d$ if `g_use_pruning_safety` is enabled and `!improving` (disabled in Reference X22/X24/X25).
- **Execution Point:** Executed at lines 4765–4778 of `negamax()`, immediately after leaf evaluation ($d \le 0$) and TT probing, and immediately *before* Null-Move Pruning ($d \ge 3$).

---

## 2. In-Depth Subsystem Contract Audit

### 2.1 Node Eligibility & PV Status
- **Audit Finding:** The RFP contract in Janus Classical checks `depth <= 3 && ply > 0 && !in_check`, but **fails to check whether the current node is a PV node** ($\beta - \alpha > 1$).
- **Architectural Risk:** In modern computer chess (e.g. Stockfish, Ethereal, Berserk), RFP is strictly confined to **Non-PV / Zero-Window nodes** ($\beta = \alpha + 1$). Pruning inside an open aspiration or PV window ($\beta - \alpha > 1$) risks returning an inaccurate static evaluation directly to the principal variation without exploring tactical moves that could change the best move or refine the exact minimax bound.

### 2.2 Return-Value Semantics & Transposition Table Omission
- **Audit Finding:** When the inequality holds, line 4776 executes:
  ```cpp
  g_telemetry_rfp_cutoffs++;
  return static_eval;
  ```
- **Architectural Risk 1 (Fail-Soft Discrepancy):** The function returns `static_eval` rather than $\beta$ or $\text{static\_eval} - \text{Margin}$. If `static_eval` is $+900$ (e.g. up a queen) while $\beta$ is $+200$, returning $+900$ can distort score bounds at higher tree levels.
- **Architectural Risk 2 (TT Bound Omission):** Upon triggering an RFP cutoff, `negamax()` immediately returns **without storing a `TT_LOWER` entry in the transposition table**. Consequently:
  1. The parent node receives a fail-high, but the transposition table contains no depth-bounded record that this position was verified $\ge \beta$.
  2. Subsequent searches reaching this position via move transpositions must re-evaluate the board and re-execute RFP, losing transposition-table reuse efficiency.

### 2.3 Mate-Score Exclusions & Tactical Horizon Blindness
- **Audit Finding:** The check `std::abs(beta) < MATE_SCORE - 100` prevents cutoffs when $\beta$ represents a forced checkmate.
- **Vulnerability:** It checks $\beta$, but does **not** check whether `static_eval` itself is near mate. More critically, if the side to move is ahead in material ($\text{static\_eval} = +600$), but the opponent has an unstoppable tactical checkmating attack on the next ply (e.g. $Q\times h2\#$), the position is currently `!in_check`. Because $\text{static\_eval} - 120 \gg \beta$, RFP cuts off and declares the position won, completely blind to the opponent's immediate mating refutation!

### 2.4 Zugzwang & Material Preconditions
- **Audit Finding:** Unlike Null-Move Pruning (which explicitly checks `non_pawn_mat != 0` at line 4787), **RFP has zero material preconditions**.
- **Vulnerability:** In pure King & Pawn endgames, positions frequently arise where the side to move is in reciprocal zugzwang. Any legal move loses opposition or surrenders a key square. Because static evaluation measures pawn structure statically without simulating the forced pawn advance, RFP can prune the node, assuming the position is easily winning when in reality any legal move leads to a loss or draw.

### 2.5 Transposition-Table Bound Conflicts
- **Audit Finding:** In lines 4701–4713, a TT probe occurs. If a TT entry exists with `entry.depth < depth` (e.g. searched at depth 1 or 2) and `entry.flag == TT_UPPER` with `entry.score < beta`, this constitutes strong historical evidence that the true minimax score is less than $\beta$.
- **Vulnerability:** The RFP check does not inspect `has_entry` or `entry.flag`. If $\text{static\_eval} - \text{margin} \ge \beta$, RFP overrides the TT upper bound and prunes anyway.

---

## 3. Classification: Heuristic Selectivity Risk vs Contract Violation

We classify the audited behaviors into two distinct categories:

| Category | Description | Severity | Classification |
| :--- | :--- | :---: | :--- |
| **Missing PV Guard** | RFP executing when $\beta - \alpha > 1$ | Medium | **Search Contract Flaw** |
| **Missing TT Write** | Returning `static_eval` without updating TT with `TT_LOWER` | Medium | **Search-State Inefficiency** |
| **Pawn-Race Blindness** | Static eval lagging 7th-rank passer promotions | Low–Med | Heuristic Selectivity Risk |
| **Zugzwang Pruning** | Pruning in K+P endgames without non-pawn material check | Low–Med | Heuristic Selectivity Risk |
| **Mate Threat Blindness**| Pruning positions facing multi-piece mate in 1–2 | High | Heuristic Selectivity Risk |
| **TT Upper Conflict** | Pruning when TT upper bound proves score $< \beta$ | Low–Med | **Search Contract Flaw** |

---

## 4. Empirical Validation via 8 Diagnostic Suites

The empirical audit in `test_rfp_contract_audit.py` revealed:
1. **Middlegame Quiet Positions:** 100% root move agreement with $1.0\times$ node ratio (RFP rarely fires at depth 2–3 on quiet root lines where static eval is close to 0).
2. **Tactical Mate & Penetration:** Move agreement maintained because tactical lines rapidly deliver check (`in_check == true`), which safely disables RFP.
3. **Passed Pawn Race (CAT4_RACE_2):**
   - At depth 2 in a Rook vs 2nd-rank pawn position (`8/4k3/8/8/8/4K3/1p6/1R6 w - - 0 1`):
     - **RFP ON:** Played `b1b2` (score $+519$, 66 nodes).
     - **RFP OFF:** Played `e3e2` (score $+527$, 239 nodes).
   - This confirmed that RFP can alter root move choice at shallow depths, pruning the search by $72.4\%$ ($0.276\times$ nodes). At depth 3, both variants converged on `b1b2` ($+547$).

---

## 5. Phase 2 Conclusion

The contract governing Reverse Futility Pruning is formally documented:
1. The inequality $\text{StaticEval} - (M \times d) \ge \beta$ is strictly enforced.
2. Three specific search-contract defects have been identified:
   - Absence of Non-PV guard (`beta - alpha == 1`).
   - Absence of TT lower-bound write before return.
   - Absence of TT upper-bound contradiction guard.
3. These findings provide the precise technical foundation for **Phase 3: Counterfactual Pruning Instrumentation** and **Phase 8: Architectural Decision Gate**.
