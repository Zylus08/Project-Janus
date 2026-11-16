# JANUS CLASSICAL R1 — SEARCH ARCHITECTURE REBOOT
## Formal Architecture Decision Record (ADR) & Modular Search Specification

**Milestone:** Phase 1, Milestone P1.22 — Phase 2  
**Document Designation:** `JANUS_R1_SEARCH_ARCHITECTURE.md`  
**Architect:** Principal Computer Chess Architect & C++17 Systems Engineer  
**Repository:** `E:\ChessXML\project-janus-phase1`  
**Branch:** `phase1/classical-janus`  
**Date:** 2026-11-16  

---

## 1. Context & Architectural Rationale

### 1.1 The Failure Mode of Evolutionary Search Patching
Throughout Phase 1 (Milestones P1.0 through P1.21), the Janus Classical engine evolved through successive incremental modifications of a single monolithic C++ file (`janus_classical_x.cpp`, exceeding 6,300 lines of entangled code). Within this legacy codebase:
- Search flow, iterative deepening, root move handling, transposition table probing, aspiration windows, move generation, move ordering, history tables, pruning heuristics (NMP, RFP, LMP, FP, SE, Multi-Cut), quiescence search, and parallel SMP synchronization were intermingled inside a single recursive function (`negamax()`).
- State management depended on dozens of global variables (`g_ss`, `g_tt`, `g_parallel_tt`, `g_history`, `g_rfp_repair_mode`, `g_search_variant`, etc.), introducing hidden coupling and subtle side-effects across search depth and time controls.
- When an individual selectivity heuristic was "repaired" in isolation—such as Option A's RFP repair in P1.21—the search tree experienced unexpected explosive growth (e.g., $2.8\times$ node expansion in pawn endgames), causing severe time-management failures and competitive rating collapse against earlier baselines (X26 losing $-17.4$ Elo to X7 and $-52.5$ Elo to X22).

### 1.2 Executive Architectural Mandate
To establish an enduring, high-performance, strictly non-ML computer chess architecture for Project Janus, Milestone P1.22 executes a **Clean-Sheet Search Core Reboot: Janus Classical R1**.
The R1 architecture decouples search responsibilities into eight isolated, contract-governed modules:
1. `SearchController`: Multi-thread orchestration, UCI dispatch, clock allocation, cooperative abort handling, telemetry accumulation.
2. `RootSearch`: Iterative deepening, aspiration windows, root move scoring, fail-soft fallbacks, PV line preservation.
3. `AlphaBetaCore`: Pure recursive negamax with strict node-type partitioning (PV vs Cut vs All).
4. `QuiescenceCore`: Tactical quiescence search enforcing corrected Q1 semantics, stand-pat delta margins, and SEE pruning.
5. `TranspositionStore`: High-performance, cache-aligned, 3-slot clustered transposition table with formal replacement policies (TT0, TT1, TT2) and strict generation aging.
6. `MoveOrdering`: Staged, state-machine move picker (TT move $\to$ Good Captures $\to$ Killers $\to$ Countermoves $\to$ History Quiets $\to$ Bad Captures).
7. `SearchTelemetry`: Zero-overhead telemetry counters measuring main nodes, qsearch nodes, probe hits, cutoffs by heuristic, and effective branching factor.
8. `SelectivityPolicy`: Formal safety-bounded interfaces for Null-Move Pruning, Reverse Futility Pruning, Late Move Reductions, and Late Move Pruning.

---

## 2. Architectural Blueprint & Component Decomposition

```
                           +---------------------------+
                           |     UCI / GUI Client      |
                           +---------------------------+
                                         |
                                         v
                           +---------------------------+
                           |     SearchController      |
                           | (Clock & Thread Manager)  |
                           +---------------------------+
                                         |
                                         v
                           +---------------------------+
                           |        RootSearch         |
                           |   (Iterative Deepening)   |
                           +---------------------------+
                                         |
                     +-------------------+-------------------+
                     |                                       |
                     v                                       v
         +-----------------------+               +-----------------------+
         |     AlphaBetaCore     | <-----------> |  TranspositionStore   |
         | (PV / Cut / All Nodes)|               |  (Cluster-3, Lockless)|
         +-----------------------+               +-----------------------+
              |             |                                |
              |             +---------------+                |
              v                             v                v
   +--------------------+         +--------------------+     |
   | QuiescenceCore     |         |    MoveOrdering    | <---+
   | (Q1 Stand-Pat, SEE)|         |  (Staged Picker)   |
   +--------------------+         +--------------------+
              |                             |
              v                             v
   +--------------------+         +--------------------+
   | Classical Evaluator|         | Classical Board    |
   | (Material & PST)   |         | (Movegen & State)  |
   +--------------------+         +--------------------+
```

---

## 3. Subsystem Specifications & Contracts

### 3.1 SearchController & Time Manager
- **Ownership:** Owns search execution, thread lifecycles, and UCI interaction.
- **Clock Allocation:**
  $$\text{Target Time} = \frac{\text{Time Left}}{\text{Moves Remaining}} + \text{Increment}$$
  Enforces hard cutoff boundaries ($\text{Hard Max} = 0.6 \times \text{Time Left}$) to prevent flag falls.
- **Stop Contract:** Implements an `std::atomic<bool> stop_flag`. Worker threads check this flag every 2048 nodes. When set, all recursive frames immediately unwind without modifying the completed iteration's root results.

### 3.2 RootSearch & Iterative Deepening
- **Loop Semantics:**
  - Starts at $d = 1$, incrementing to $d_{\max}$.
  - At each depth $d \ge 4$, employs aspiration windows: $[\text{score}_{d-1} - \Delta, \text{score}_{d-1} + \Delta]$ with $\Delta = 25\text{ cp}$.
  - Upon fail-low or fail-high, iteratively widens window ($\Delta \leftarrow 3\Delta / 2$) until re-search succeeds, falling back to $(-\infty, +\infty)$ if necessary.
- **Completed-Iteration Invariant:**  
  If depth $d$ search is interrupted before completion, RootSearch discards the partial iteration and returns the best move and score from completed depth $d-1$. The engine never plays an unverified move from an aborted iteration.

### 3.3 AlphaBetaCore (Recursive Negamax)
- **Node Classification Contract:**
  1. **PV Nodes:** $\beta - \alpha > 1$. Must search the expected best move with open window $(\alpha, \beta)$ and subsequent moves with null-window $(\alpha, \alpha+1)$. Zero heuristic pruning (NMP, RFP, LMP) is permitted.
  2. **Cut Nodes:** $\beta - \alpha = 1$. The search expects to produce a fail-high ($\ge \beta$). Selectivity heuristics are strictly active.
  3. **All Nodes:** $\beta - \alpha = 1$. The search expects all moves to fail low ($\le \alpha$).
- **Transposition Probing Contract (TT0/TT1/TT2):**
  - **TT0 (Cutoff Contract):** If a matching TT entry has $\text{depth} \ge \text{search\_depth}$:
    - If $\text{flag} == \text{TT\_EXACT}$: Return `tt_score`.
    - If $\text{flag} == \text{TT\_LOWER} \land \text{tt\_score} \ge \beta$: Return `tt_score`.
    - If $\text{flag} == \text{TT\_UPPER} \land \text{tt\_score} \le \alpha$: Return `tt_score`.
  - **TT1 (Bound Precedence):** A static evaluation must never trigger an RFP cutoff if an existing TT entry has $\text{flag} == \text{TT\_UPPER}$ with $\text{tt\_score} < \beta$.
  - **TT2 (Authoritative Storage):** On node exit, every search must store an entry:
    - If $\text{score} \le \alpha$: Store $\text{TT\_UPPER}$.
    - If $\text{score} \ge \beta$: Store $\text{TT\_LOWER}$ and record `best_move`.
    - If $\alpha < \text{score} < \beta$: Store $\text{TT\_EXACT}$ and record `best_move`.

### 3.4 QuiescenceCore (Tactical Search)
- **Corrected Q1 Semantics:**
  - Evaluates static stand-pat score $S = \text{Evaluate}(B)$.
  - If $S \ge \beta$: Returns $S$ immediately (fail-high stand-pat).
  - Updates $\alpha = \max(\alpha, S)$.
  - Generates legal captures and queen promotions only.
  - **Delta Pruning:** If $S + \text{Val}(P_{\text{captured}}) + 200\text{ cp} < \alpha$, skips move (unless in check or pawn promotion).
  - **SEE Filtering:** In mode Q1, captures with $\text{SEE} < 0$ are pruned.
  - Returns $\alpha$ if all tactical moves fail low.

### 3.5 TranspositionStore
- **Layout:** Cache-line aligned (64 bytes per cluster). Each cluster contains 3 entries (20 bytes each) plus 4 bytes of padding.
- **Replacement Policy:**
  1. Slot 0: Always replace if same key, or if new entry has greater depth.
  2. Slot 1: Replace entry with oldest generation age (`g_age`).
  3. Slot 2: Always replace (shallowest / leaf cache).
- **Mate Score Normalization:** Scores $\ge \text{MATE\_SCORE} - 100$ are adjusted by ply:
  $$\text{score\_to\_tt}(s, \text{ply}) = \begin{cases} s + \text{ply} & \text{if } s > \text{MATE\_THRESHOLD} \\ s - \text{ply} & \text{if } s < -\text{MATE\_THRESHOLD} \\ s & \text{otherwise} \end{cases}$$

### 3.6 MoveOrdering (Staged Move Picker)
The move generator yields moves through discrete stages without allocating intermediate candidate lists:
1. **Stage 1 (TT Move):** If the transposition table provided a legal move, test it first.
2. **Stage 2 (Good Captures):** Generate captures; order by MVV-LVA score. Filter with $\text{SEE} \ge 0$.
3. **Stage 3 (Killers):** Killer move 1, then Killer move 2 (quiet moves that caused fail-high at current ply).
4. **Stage 4 (Countermove):** Move that refuted the previous opponent move.
5. **Stage 5 (History Quiets):** Generate quiet moves; sort using butterfly history heuristics ($[12][64]$ table).
6. **Stage 6 (Bad Captures):** Remaining captures with $\text{SEE} < 0$.

### 3.7 SelectivityPolicy & Safety Invariants
- **Null-Move Pruning (NMP):**
  - Requires: $\text{depth} \ge 3 \land \neg\text{in\_check} \land \text{non\_pawn\_mat} > 0 \land \text{ply} > 0 \land \neg\text{is\_pv\_node}$.
  - Reduction: $R = 2 + \frac{\text{depth}}{6}$.
  - Evaluates: $-\text{negamax}(B_{\text{null}}, d - 1 - R, -\beta, -\beta + 1)$.
- **Reverse Futility Pruning (RFP):**
  - Requires: $\text{depth} \le 3 \land \neg\text{in\_check} \land \neg\text{is\_pv\_node} \land |\beta| < \text{MATE\_THRESHOLD}$.
  - Requires: $\neg(\text{has\_tt\_entry} \land \text{tt\_flag} == \text{TT\_UPPER} \land \text{tt\_score} < \beta)$.
  - Prunes if: $\text{static\_eval} - (120 \times \text{depth}) \ge \beta$.
  - Stores: `TT_LOWER` bound before return.
- **Late Move Reductions (LMR):**
  - Active only for quiet moves searched at move index $\ge 4$ with $\text{depth} \ge 3$.
  - Never reduces tactical captures, checks, killer moves, or root moves.

---

## 4. Implementation Layout

The R1 search core is organized into modular C++17 headers in `engine/classical_x/r1/`:
- `engine/classical_x/r1/r1_types.hpp`: Core types, search bounds, move structures, and mate score utilities.
- `engine/classical_x/r1/r1_tt.hpp`: Transposition table cluster, entry layout, probe and store contracts.
- `engine/classical_x/r1/r1_telemetry.hpp`: Telemetry accumulators and atomic metrics.
- `engine/classical_x/r1/r1_movepicker.hpp`: Staged move ordering state machine and history tables.
- `engine/classical_x/r1/r1_quiescence.hpp`: Quiescence search engine with Q1 SEE semantics.
- `engine/classical_x/r1/r1_search.hpp`: AlphaBetaCore and RootSearch implementation.
- `engine/classical_x/r1/r1_controller.hpp`: SearchController and time management.
- `engine/classical_x/r1/r1_uci.cpp`: UCI command interface and standalone executable entry point.

This architecture establishes a clean, auditable, and modular foundation that eliminates monolithic technical debt while upholding strictly non-ML classical search contracts.
