# Comprehensive MovePicker & Move-Ordering Architecture Audit
**Milestone:** Phase 1, Milestone P1.14  
**Date:** November 13, 2026  
**Auditor:** Principal Computer Chess Engine Architect & C++17 Search Specialist  
**Governing Standard:** JCTS v2 Classical Testing Protocol  
**Repository Branch:** `phase1/classical-janus`  
**Inspected Source:** `engine/classical_x/janus_classical_x.cpp` (Qualified Baselines X7 & X12)  

---

## 1. Executive Summary & Core Architectural Defect Discovery

An exhaustive line-by-line inspection of the MovePicker and move-ordering subsystem in `janus_classical_x.cpp` was conducted to map the exact sequence of candidate moves, scoring ranges, update rules, and stage transitions.

### The Major Architectural Defect: The "Staged Capture Leak"
The audit revealed a severe structural disconnect between the numerical scoring design in `score_move_for_ordering()` and the state-machine execution in `MovePicker::next_move()`:

1. **Intended Numerical Hierarchy:**  
   In `score_move_for_ordering()`, moves receive scores structured to enforce a strict precedence:
   - Transposition Table Move: `10,000,000`
   - Queen Promotion: `900,000`
   - Underpromotion: `800,000`
   - Winning Captures ($\text{SEE} > 0$): $100,000 + \text{MVV/LVA}$
   - Equal Captures ($\text{SEE} == 0$): $95,000 + \text{MVV/LVA}$
   - Killer Move 1: `90,000`
   - Killer Move 2: `80,000`
   - Countermove: `75,000`
   - **Losing Captures ($\text{SEE} < 0$): $20,000 + \text{SEE} + \text{MVV/LVA}$**
   - High-History Quiet Moves: up to `50,000`
   - Unscored Quiet Moves: `0`
2. **Actual Staged Execution in `MovePicker`:**  
   In `MovePicker::next_move()`, non-check nodes transition strictly between stages:
   $$\text{STAGE\_TT} \longrightarrow \text{STAGE\_CAPTURES} \longrightarrow \text{STAGE\_KILLERS} \longrightarrow \text{STAGE\_QUIETS}$$
   `STAGE_CAPTURES` yields **every single capture** returned by `native_generate_captures()`, including suicidal/losing captures (e.g. $Q \times P$, $\text{SEE} = -800$, score $\approx 19,200$), **before `STAGE_KILLERS` is ever reached**.
3. **Tactical Consequence:**  
   Suicidal and heavily losing captures are searched *ahead* of Killer 1, Killer 2, Countermoves, and high-history quiet moves! Even though the scoring function assigned losing captures a score of 20,000 (well below killers at 90,000), the stage machine forcefully drains all captures first. This causes unnecessary subtree explosions in tactical positions.

---

## 2. Complete Inventory of Move-Ordering Stages & Scoring Rules

### 2.1 Candidate Move Precedence Matrix

| Category | Generation Function | Scoring Formula in `score_move_for_ordering` | Theoretical Priority Range | Actual Search Stage in `MovePicker` |
| :--- | :--- | :--- | :---: | :---: |
| **TT Move** | Transposition Table probe | Exact match: $m == \text{tt\_move}$ | $10,000,000$ | `STAGE_TT` (1st) |
| **Queen Promotion** | `native_generate_captures` | Flag 3, Promo Queen | $900,000$ | `STAGE_CAPTURES` |
| **Underpromotion** | `native_generate_captures` | Flag 3, Promo Rook/Bishop/Knight | $800,000$ | `STAGE_CAPTURES` |
| **Winning Capture** | `native_generate_captures` | $\text{SEE} > 0$: $100,000 + \text{MVV/LVA} + \text{CapHist}$ | $100,000\text{--}102,550$ | `STAGE_CAPTURES` |
| **Equal Capture** | `native_generate_captures` | $\text{SEE} == 0$: $95,000 + \text{MVV/LVA} + \text{CapHist}$ | $95,000\text{--}97,550$ | `STAGE_CAPTURES` |
| **Losing Capture** | `native_generate_captures` | $\text{SEE} < 0$: $20,000 + \text{SEE} + \text{MVV/LVA} + \text{CapHist}$ | $10,000\text{--}20,000$ | **`STAGE_CAPTURES` (Prematurely Yielded!)** |
| **Killer Move 1** | `g_killer_moves[ply][0]` | Exact match | $90,000$ | `STAGE_KILLERS` |
| **Killer Move 2** | `g_killer_moves[ply][1]` | Exact match ($m \neq \text{killer1}$) | $80,000$ | `STAGE_KILLERS` |
| **Countermove** | `g_countermove_table` | Exact match against `[prev_from][prev_to]` | $75,000$ | `STAGE_QUIETS` (Top of quiets) |
| **High History Quiet**| `native_generate_quiets` | $H(s, from, to) + \text{ContHist}$ | $1\text{--}50,000$ | `STAGE_QUIETS` |
| **Unscored Quiet** | `native_generate_quiets` | Base quiet move | $0$ | `STAGE_QUIETS` |
| **Negative History** | `native_generate_quiets` | Fails alpha frequently | $-20,000\text{--}0$ | `STAGE_QUIETS` |

---

## 3. Move Scoring Term Behavior & Update Mechanics

### 3.1 Transposition Table Move
* **Condition:** Probed at node entry. If TT hit is valid and the move is pseudo-legal and legal in the current board, it is yielded at `STAGE_TT`.
* **Deduplication:** Added to `yielded[num_yielded++]`. If encountered later in capture or quiet generation, `has_been_yielded(m)` discards it in $O(K)$ time.

### 3.2 Captures & SEE
* **Classification:** Evaluated using `janus_see(b, m)`.
* **MVV/LVA:** Calculated as `(victim_piece * 10) - attacker_piece`, ranging from $-5$ (Pawn takes Queen impossible, King takes Pawn) to $+50$ (Pawn takes Queen).
* **Capture History:** `g_capture_history[attacker][to][victim]`, bounded to $[-2500, +2500]$.

### 3.3 Killer Moves
* **Storage:** `thread_local uint16_t g_killer_moves[MAX_PLY][2]`.
* **Update Rule:** When a quiet move causes a beta-cutoff:
  ```cpp
  if (m != g_killer_moves[ply][0]) {
      g_killer_moves[ply][1] = g_killer_moves[ply][0];
      g_killer_moves[ply][0] = m;
  }
  ```
* **Aging/Reset:** Cleared via `std::memset` at the beginning of each iterative deepening root search.

### 3.4 Butterfly History
* **Storage:** `thread_local int g_history_table[2][64][64]`.
* **Bonus Update:** On quiet beta-cutoff:
  $$\Delta H = \text{depth} \times \text{depth}$$
  Bounded by `MAX_HISTORY_SCORE = 70,000`.
* **Gravity Decay:** In X12/X17:
  $$H_{\text{new}} = H_{\text{old}} + \Delta H - \frac{H_{\text{old}} \times |\Delta H|}{16384}$$
* **SMP Synchronization:** In multithreaded searches, helper threads copy `g_master_history_table` at the start of search, and Thread 0 writes back to master upon search completion. Thread-local access is completely race-free.

---

## 4. Verification of Search Invariants

| Invariant Requirement | Audit Verification | Status |
| :--- | :--- | :---: |
| **Unique Return** | Every yielded move is checked against `yielded[num_yielded]` array. | **PASS** |
| **Move Set Completeness**| `native_generate_captures` generates all captures + promotions + EP. `native_generate_quiets` generates all non-capturing pawn pushes, piece moves, castling. Union covers 100% legal moves. | **PASS** |
| **Promotion Safety** | All 4 promotions (Queen, Rook, Bishop, Knight) generated in `native_generate_captures`. | **PASS** |
| **Capture Classification**| SEE evaluates static exchange; MVV/LVA correctly distinguishes attacker/victim. | **PASS** |
| **History Boundedness** | Clamped to `[-20000, +70000]`. No integer overflow possible. | **PASS** |
| **Thread-Safety** | All search stacks, killer tables, history tables, and MovePicker structs are `thread_local`. | **PASS** |
| **Interruption Correctness**| Search deadline checked every 2048 nodes. When aborted, unwinds safely without corrupting MovePicker state. | **PASS** |

---

## 5. Architectural Recommendations for Phase 6 Intervention

1. **Split `STAGE_CAPTURES` into Good Captures and Bad Captures:**  
   During `STAGE_GEN_CAPTURES`, classify captures:
   - Captures with $\text{SEE} \ge 0$ (Good Captures) are yielded immediately in `STAGE_GOOD_CAPTURES`.
   - Captures with $\text{SEE} < 0$ (Bad Captures) are deferred to `STAGE_BAD_CAPTURES`, searched **after** Killers, Countermoves, and high-history quiet moves!
2. **Promote Countermoves to a First-Class Stage:**  
   Introduce `STAGE_COUNTERMOVE` immediately after `STAGE_KILLERS`. This avoids generating and sorting 30+ quiet moves if the countermove produces an immediate beta-cutoff.
3. **Incremental Selection Sort for Quiets:**  
   Replace full array sorting ($O(N^2)$ across all 40 quiets) with on-demand incremental selection sort, finding the next highest-scoring quiet move only when the previous move fails to produce a cutoff.

