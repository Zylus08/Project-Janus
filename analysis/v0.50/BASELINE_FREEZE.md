# Project Janus v0.50 — Baseline Freeze & Reference Verification

**Milestone:** Project Janus v0.50  
**Parent Baseline Commit:** `d037f77` (v0.49 Final)  
**Evaluated Reference Configurations:**
- **Python K0 (Production Reference):** `enable_lazy_move_selection=False`, `enable_rfp=False`
- **Python L1 (Experimental Reference):** `enable_lazy_move_selection=True`, `enable_rfp=False`
**Reference Engine:** Stockfish 19 (`E:\ChessXML\tools\stockfish\stockfish.exe`)

---

## 1. Provenance and Environment Freeze (Phase A1)

- **Repository Path:** `E:\ChessXML\project-janus`
- **Branch:** `v0.3-benchmark-harness`
- **HEAD Commit:** `d037f77`
- **Parent Relationship:** Exact match to v0.49 final commit.
- **Working-Tree Status:** Clean (0 uncommitted modifications, 0 untracked files).
- **Python Version:** Python 3.13.2 64-bit (`tags/v3.13.2:4f8bb39`, MSC v.1942 64 bit AMD64)
- **Host OS:** Windows 11 Enterprise AMD64 (10.0.26200-SP0)
- **Processor:** Intel64 Family 6 Model 154 Stepping 3, GenuineIntel (16 logical cores)
- **Compiler Availability:** Microsoft (R) C/C++ Optimizing Compiler Version 19.43.34809 for x64 (MSVC BuildTools 2022 v17.13.5).
- **Compiler Script:** `C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat`
- **Reference Engine Hash:** Stockfish 19 verified via SHA-256:
  `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`

---

## 2. Regression Test Baseline (Phase A2)

- **Command:** `python -m unittest discover -s tests -p "test_*.py"`
- **Test Count:** 473 tests
- **Results:** **473 PASSED**, 0 failed, 0 skipped
- **Execution Time:** 293.215 seconds
- **Exit Status:** 0 (Clean)

---

## 3. Python Reference Search & Rule Freeze (Phase A3)

The production reference K0 engine components are formally frozen:
1. **Search Implementation (`src/janus/search.py`):**
   - Alpha-Beta Negamax with Iterative Deepening, Aspiration Windows ($\pm 50$ cp), Null Move Pruning (with verification search on endgames), Late Move Reductions (LMR), Quiescence Search with delta pruning and SEE capture ordering.
   - RFP remains strictly disabled (`enable_rfp = False`).
   - Move selection is eager full-list sorting (`enable_lazy_move_selection = False`).
2. **Move Ordering Policy:**
   - 1. TT move (`10,000,000`)
   - 2. Queen promotions (`900,000`), underpromotions (`800,000`)
   - 3. Captures scored by SEE and MVV-LVA (`100,000 + (victim * 10) - attacker`)
   - 4. Killer move slot 0 (`700,000`), slot 1 (`600,000`)
   - 5. Countermove (`550,000`)
   - 6. Quiet moves scored by history heuristic (`0` to `10,000`)
3. **Transposition Table (`TTEntry`):**
   - 2,097,152 entries with `depth_preferred` replacement policy. Mate score normalization relative to search ply.
4. **Draw and Repetition Semantics:**
   - Threefold repetition: Claimable draw in match play, terminal evaluation 0 in search.
   - Fivefold repetition: Automatic draw.
   - Fifty-move rule: Claimable draw.
   - Seventy-five-move rule: Automatic draw.
   - Insufficient material: Checked via `board.is_insufficient_material()`.
5. **Experimental Reference L1:**
   - Retained identically: `enable_lazy_move_selection = True`, which yields the legal TT move immediately and defers full move sorting unless the TT move fails to produce a beta cutoff.

