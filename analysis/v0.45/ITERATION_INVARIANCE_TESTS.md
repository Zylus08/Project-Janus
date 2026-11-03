# Iteration Invariance & Telemetry Test Report — v0.45

**Milestone:** Project Janus v0.45  
**Date:** 2026-11-03  
**Status:** PASS (Gate C Validated)

---

## 1. Test Suite Execution

The iteration-level search telemetry and publication invariance were validated in [`tests/test_v045_iteration_telemetry.py`](file:///E:/ChessXML/project-janus/tests/test_v045_iteration_telemetry.py):

- **Command:** `& 'E:\ChessXML\project-janus\.venv\Scripts\python.exe' -m unittest tests/test_v045_iteration_telemetry.py`
- **Tests Executed:** 6
- **Passed:** 6 (100%)
- **Failed:** 0
- **Errors:** 0
- **Runtime:** 1.373 seconds

---

## 2. Invariance Verification Outcomes

1. **Default Zero-Overhead Invariance:**
   - When `diagnostic_iterations=False`, `res.iteration_records` is empty and no telemetry data structures are allocated.
   - Moves, scores, node counts, and search depths match `diagnostic_iterations=True` bit-for-bit.

2. **Completed Iteration Integrity:**
   - Completed iterations properly increment depth, track per-iteration elapsed times, isolate newly consumed nodes, and calculate iteration NPS.
   - All schema fields are correctly populated.

3. **Critical Publication Invariance (Integrity Rule C3):**
   - Verified that when a search is interrupted by deadline timeout (`SearchTimeout`), the aborted iteration is logged with `completed=False`, `aborted=True`, `abort_reason="timeout"`, and `published=False`.
   - The engine strictly returns the move, score, depth, and PV from the **last fully completed iteration**.
   - Partial or aborted iterations never contaminate the published decision.

4. **Telemetry Export Buffer:**
   - Verified `flush_iteration_telemetry` exports valid JSONL lines and empties the internal buffer.

5. **Multi-Telemetry Concurrency:**
   - Verified that `diagnostic_rfp` and `diagnostic_iterations` can run simultaneously with zero cross-talk or performance degradation.

---

## 3. Gate C Sign-Off

- [x] Iteration telemetry implemented in `src/janus/search.py`.
- [x] CLI flag `--diag-iterations` added in `src/janus/uci.py`.
- [x] Zero-overhead invariant verified when disabled.
- [x] Interrupted-iteration publication invariance proven by automated tests.
- [x] Telemetry schema documented and validated.

**Gate C Status:** **PASS** — Proceeding to Phase D (Reconciliation of v0.44 Stratification).

