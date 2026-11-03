# Controlled Optimization Proposals for Future Milestones (v0.46)

> [!IMPORTANT]
> In accordance with the v0.46 Governing Constraints, these proposals are strictly descriptive research designs for future milestones. **No optimization heuristics or search rewrites are implemented in v0.46.**

---

## Proposal 1: Staged / Lazy Move Selection (Stage-Based Move Picker)
- **Target Bottleneck:** Bottleneck Priority 1 (Eager Full Move-List Sorting).
- **Core Mechanism:** Replace `moves.sort()` eager sorting with a staged generator (`MovePicker`):
  - **Stage 0:** Yield TT move immediately (if legal). If it causes a cutoff ($21.15\%$ of nodes), 0 other moves are generated or scored.
  - **Stage 1:** Generate and yield captures ordered by MVV-LVA (and winning SEE if enabled). If a capture causes a cutoff ($56.86\%$ of cutoffs), 0 quiet moves are scored.
  - **Stage 2:** Yield killer moves (Primary, Secondary).
  - **Stage 3:** Yield countermoves.
  - **Stage 4:** Score and yield remaining quiet moves by history.
- **Risk Assessment:** Minimal risk of search divergence. When all moves are explored, the evaluation order remains identical to the current hierarchy.
- **Expected Benefit:** $5\%\text{--}15\%$ NPS increase across all search depths with zero move decision divergence.
- **Validation Criteria:** 100% best-move and score invariance against K0 on fixed-depth benchmarks; measurable NPS increase.

---

## Proposal 2: Decayed / Scaled History Heuristic with Aging
- **Target Bottleneck:** Bottleneck Priority 2 (Quiet Move Discrimination).
- **Core Mechanism:**
  - Introduce gravity/aging to the butterfly history table (`history[color][from_sq][to_sq] += bonus - history * abs(bonus) / 512`) to prevent early search biases from dominating later iterations.
  - Scale quiet move history bonuses by search depth squared ($d^2$).
- **Risk Assessment:** Moderate risk of regression if history parameters are miscalibrated.
- **Expected Benefit:** Improved move ordering in quiet positions, lifting late-move cutoff positions from $\sim 54\%$ toward $\ge 70\%$ first-move cutoff rate.
- **Validation Criteria:** Statistically significant node reduction on the 37-position diagnostic corpus without degradation in Stockfish 14 agreement.

---

## Proposal 3: Soft-Bound Time Management with Best-Move Stability Scaling
- **Target Bottleneck:** Bottleneck Priority 3 (Iteration Boundary Quantization).
- **Core Mechanism:**
  - Extend the soft time budget when the best move changes late in iteration $d$, or terminate search early when the best move has remained invariant across $\ge 3$ iterations and commands $> 80\%$ of root node effort.
- **Risk Assessment:** High risk if hard time limits are exceeded. Must maintain strict hard deadline aborts.
- **Expected Benefit:** Better utilization of search budget; avoiding wasted cycles on stable single-reply positions.
- **Validation Criteria:** Zero time forfeiture across 200+ games at blitz time control (e.g., 5s+0.1s).
