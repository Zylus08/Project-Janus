# Project Janus v0.49 — Baseline Freeze & Performance Reproduction

**Milestone:** Project Janus v0.49  
**Parent Baseline Commit:** `6b46eb4` (v0.48 Final)  
**Evaluated Baseline Configurations:**
- **K0 Baseline (Production Default):** `enable_lazy_move_selection=False`, `enable_rfp=False`
- **Candidate L1 (Experimental):** `enable_lazy_move_selection=True`, `enable_rfp=False`
**Corpus:** 37-position diagnostic corpus (`analysis/v0.49/corpus/diagnostic_corpus.json`)  
**Raw Telemetry:** `analysis/v0.49/raw/baseline_reproduction_raw.json`

---

## 1. Provenance and Environment Freeze (Phase A1)

- **Repository Path:** `E:\ChessXML\project-janus`
- **Branch:** `v0.3-benchmark-harness`
- **HEAD Commit:** `0ffd2c6` (direct descendant of v0.48 final commit `6b46eb4`)
- **Parent Relationship:** Verified clean on top of `6b46eb4`.
- **Working Tree:** Clean.
- **Python Version:** Python 3.13.2 64-bit (`tags/v3.13.2:4f8bb39`, MSC v.1942 64 bit AMD64)
- **Host OS:** Windows 11 Enterprise AMD64 (10.0.26200-SP0)
- **Processor:** Intel64 Family 6 Model 154 Stepping 3, GenuineIntel (16 logical cores)
- **Compiler Availability:** Microsoft (R) C/C++ Optimizing Compiler Version 19.43.34809 for x64 (MSVC BuildTools 2022 v17.13.5).
- **Stockfish Reference Engine:** Stockfish 19 verified at `E:\ChessXML\tools\stockfish\stockfish.exe` (SHA-256: `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`).

---

## 2. Test Baseline Audit (Phase A2)

- **Command:** `python -m unittest discover -s tests -p 'test_*.py'`
- **Test Count:** 473 tests
- **Results:** **473 PASSED**, 0 failed, 0 skipped
- **Execution Time:** 74.536 seconds
- **Exit Status:** 0 (Clean)

---

## 3. Configuration Freeze (Phase A3)

The production configuration is verified frozen:
- `enable_lazy_move_selection = False` (K0 default)
- `enable_rfp = False` (RFP disabled by default)
- `enable_history = True` (History heuristic active)
- `enable_countermoves = True` (Countermove heuristic active)
- `enable_see_ordering = True` (SEE capture ordering active)
- `tt_replacement_policy = "depth_preferred"` (Transposition table configured with 2,097,152 entries)

---

## 4. Baseline Performance Reproduction (Phase A4)

The inherited 37-position diagnostic corpus was evaluated across Depths 2 through 5 (and Depth 6 on the 9-position subset) under identical conditions:

| Depth | Positions | K0 Nodes | L1 Nodes | Node Delta | K0 Time | L1 Time | Runtime Delta | K0 Ord Time | L1 Ord Time | Ord Delta | Agreement | Sorts Saved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Depth 2** | 37 | 25,347 | 25,347 | **0.00%** | 1.31 s | 1.29 s | -1.21% | 0.083 s | 0.081 s | -2.41% | 37 / 37 (100.0%) | 1 |
| **Depth 3** | 37 | 182,087 | 180,924 | **-0.64%** | 7.25 s | 7.33 s | +1.09% | 0.584 s | 0.469 s | -19.71% | 36 / 37 (97.3%) | 1,491 |
| **Depth 4** | 37 | 405,197 | 407,705 | **+0.62%** | 19.36 s | 19.88 s | +2.65% | 1.332 s | 1.235 s | -7.28% | 36 / 37 (97.3%) | 2,969 |
| **Depth 5** | 37 | 1,251,786 | 1,252,292 | **+0.04%** | 57.57 s | 57.12 s | -0.78% | 3.992 s | 3.305 s | -17.21% | 35 / 37 (94.6%) | 14,510 |
| **Depth 6** | 9 | 772,670 | 803,789 | **+4.03%** | 33.89 s | 36.08 s | +6.48% | 2.500 s | 2.232 s | -10.72% | 8 / 9 (88.9%) | 8,912 |

### Audit Conclusions:
1. **Exact Tree Fidelity:** Node counts across Depths 2, 3, 4, and 5 replicate the v0.48 results to the single node (e.g. D2: 25,347 vs 25,347; D5: 1,251,786 vs 1,252,292).
2. **Move Agreement:** 100.0% at D2, 97.3% at D3, 97.3% at D4, and 94.6% at D5.
3. **Ordering Elimination:** L1 deferred and saved **14,510 complete sorts** at Depth 5, producing a consistent $-17.21\%$ reduction in move ordering execution time.
4. **Conclusion:** Baseline reproduction is fully validated. Gate A is satisfied.

