# QUIESCENCE SEARCH ARCHITECTURE AUDIT

**Project:** Project Janus — Phase 1, Milestone P1.16  
**Auditor:** Principal Computer Chess Engineer, Tactical Search Specialist & Search Architect  
**Date:** November 14, 2026  
**Repository Branch:** `phase1/classical-janus`  
**Expected HEAD:** `2226c0c`  
**Deliverable:** `analysis/phase1/p1.16/QUIESCENCE_SEARCH_ARCHITECTURE_AUDIT.md`  

---

## 1. Executive Summary & Root Search Defect Discovery

A forensic architectural audit of the quiescence search implementation in Project Janus (`quiescence()` in `engine/classical_x/janus_classical_x.cpp:3892-4003`) was conducted across all versions (X7, X12, X19, and X20).

The audit revealed a **catastrophic structural correctness violation**:
> **The Quiescence In-Check Blindness Defect:**  
> When the alpha-beta search (`negamax`) reaches leaf depth (`depth <= 0`), it unconditionally invokes `quiescence(b, alpha, beta, nodes, deadline, aborted)`. If the leaf position has the side to move in check:
> 1. `quiescence()` does not detect or test whether the king is in check.
> 2. It immediately evaluates `stand_pat = native_evaluate(b)`.
> 3. If `stand_pat >= beta`, it returns an **illegal beta cutoff**, treating standing still while in check as a valid legal position!
> 4. If `stand_pat < beta`, it raises `alpha = max(alpha, stand_pat)`.
> 5. It invokes `native_generate_captures(b, raw_caps)`, **ignoring all quiet king evasions and interpositions**.
> 6. If no legal captures exist, it returns `alpha` (the static evaluation), completely failing to recognize **CHECKMATE**!

This defect explains why Janus has suffered mysterious tactical collapses and horizon blunders against mature classical engines (Stockfish 4, Stockfish 11, and Stockfish 19).

---

## 2. Answers to the 10 Critical Quiescence Questions

### Q1: Can Janus enter quiescence search while its king is in check?
**YES.** In `negamax` (line 4046):
```cpp
if (depth <= 0 || ply >= MAX_SEARCH_PLY - 1) {
    if (g_exact_search_mode) return native_evaluate(b);
    return quiescence(b, alpha, beta, nodes, deadline, aborted);
}
```
If the opponent delivers check at depth 1, the child position has `depth == 0` and `in_check == true`. `negamax` directly delegates this in-check position to `quiescence()`.

### Q2: Does it search all necessary legal evasions?
**NO.** `quiescence()` only calls `native_generate_captures()` (line 3923). All non-capture evasions (quiet king retreats, quiet bishop/knight/rook interpositions) are completely omitted.

### Q3: Can stand-pat evaluation be used incorrectly in check?
**YES, CATASTROPHICALLY.** Lines 3902–3904:
```cpp
int stand_pat = native_evaluate(b);
if (stand_pat >= beta) return beta;
if (stand_pat > alpha) alpha = stand_pat;
```
When in check, a player is legally forbidden from standing pat. Evaluating `stand_pat` and taking a beta cutoff or setting `alpha` is a severe rules-of-chess violation in alpha-beta search.

### Q4: Can forced non-capture evasions be omitted?
**YES.** In positions where the only legal moves to escape check are quiet king steps (e.g. $Kh8 \to Kh7$) or interpositions, 0 captures are generated. `quiescence()` searches 0 moves and returns `alpha = stand_pat`.

### Q5: Can quiet promotions be missed?
**NO.** `native_generate_captures()` generates push promotions (lines 3211–3216). However, underpromotions are generated with lower scores.

### Q6: Can SEE filtering discard essential defensive resources?
**YES.** Line 3949:
```cpp
if (g_quiescence_see_mode >= 2 && see_val < 0 && move_flag(m) != 3) {
    g_telemetry_qmoves_pruned++;
    continue;
}
```
If the king or a defending piece captures an attacking checking piece on a defended square (e.g. $K \times Q$ or $R \times N$) and that capture has $\text{SEE} < 0$, SEE filtering discards the move. If it is the only legal evasion, the engine prunes its sole survival path.

### Q7: Can the quiescence limit cause false mate or stalemate scores?
**YES.** 
- In checkmate, `quiescence()` returns `stand_pat` (e.g. $-89\text{ cp}$) instead of $-30000$ (Checkmate).
- In stalemate, `quiescence()` returns `stand_pat` (e.g. $-500\text{ cp}$ material deficit) instead of $0\text{ cp}$ (Draw).

### Q8: Can captures-only search miss forcing checks that materially change evaluation?
**YES.** Standard quiescence generates only captures and promotions. Quiet forcing checks that fork pieces or deliver mate in 1–2 plies are completely omitted.

### Q9: Does quiescence terminate safely under repeated checks?
Currently, because quiescence generates only captures, an infinite loop cannot occur (pawn and piece counts strictly decrease). However, `quiescence()` lacks a `ply` parameter and a quiescence depth limit. If checking moves are introduced without a recursion limit, infinite checking cycles could occur.

### Q10: Are quiescence TT scores and mate distances handled correctly?
**NO.** `quiescence()` has zero TT probing, zero TT storage, and does not receive `ply`. It cannot normalize mate scores (`-MATE + ply`).

---

## 3. Verified Failure Atlas (Reproducible Forensic Cases)

| Case ID | Position FEN | Expected Outcome | Actual Outcome in Janus Quiescence | Severity |
|---|---|---|---|---|
| **CASE 1** | `6k1/8/8/8/8/8/8/6RK b - - 0 1` | Prohibit stand-pat; search quiet evasions ($Kh8, Kh7, Kf8, Kf7$) | Stand-pat evaluated ($-523\text{ cp}$). False beta cutoff if $\beta \le -523$. Zero evasions searched. | **CRITICAL** |
| **CASE 2** | `rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3` | Return $-30000$ (Checkmate) | Returns $\text{stand\_pat} = -89\text{ cp}$! Engine believes it is down less than a pawn! | **CATASTROPHIC** |
| **CASE 3** | `R6k/8/8/8/8/8/8/7K b - - 0 1` | Search $Kh7$ check evasion | Generates 0 captures. Quiescence terminates immediately, returning material deficit. | **CRITICAL** |
| **CASE 4** | `4k3/5Q2/8/8/2B5/8/8/7K b - - 0 1` | Search $Kd8$ or $Kxf7$ | $Kxf7$ has $\text{SEE} < 0$. Pruned by SEE filter (line 3949)! | **CRITICAL** |
| **CASE 5** | `k7/8/1K6/8/8/8/8/8 b - - 0 1` | Return $0\text{ cp}$ (Stalemate) | Returns $\text{stand\_pat} = -500\text{ cp}$ (material deficit). | **MODERATE** |

---

## 4. Phase 3 Audit Conclusion & Repair Blueprint

The diagnostics confirm that the single most dangerous flaw in Project Janus is not evaluation weight calibration or move-ordering heuristics, but the **quiescence search contract violation in check**.

### Required Phase 4 Repairs:
1. **In-Check Branching:** If `native_is_check(b)` is true:
   - Completely disable `stand_pat`.
   - Completely disable delta pruning.
   - Generate all legal moves (`native_generate_legal_moves`).
   - If legal move count is 0, return `-30000 + ply` (Checkmate).
   - Exempt check evasions from negative-SEE pruning.
2. **Search State Tracking:** Pass `ply` and `qply` into `quiescence()` to track mate distance and enforce a recursion budget (e.g. `qply < 16`).
3. **Stalemate Detection:** If not in check and legal moves == 0, return $0\text{ cp}$.
