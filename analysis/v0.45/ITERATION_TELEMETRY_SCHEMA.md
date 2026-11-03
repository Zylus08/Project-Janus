# Iteration-Level Search Telemetry Schema — v0.45

**Milestone:** Project Janus v0.45  
**Date:** 2026-11-03  
**Status:** VALIDATED

---

## 1. Overview

The iteration-level telemetry instrumentation captures detailed search dynamics for every nominal depth iteration during iterative deepening. It records both completed iterations and iterations that were aborted mid-search due to time limits or search stop events.

When disabled (`diagnostic_iterations=False`, the default), overhead is zero (boolean check on iteration boundary).

---

## 2. Iteration Event Record Schema

Each record represents one iterative-deepening attempt and contains the following attributes:

| Field | Type | Description |
|---|---|---|
| `iteration_depth` | `integer` | Nominal target depth of the iteration ($1, 2, \dots$). |
| `iteration_start_time` | `float` | Wall-clock timestamp (`time.monotonic()`) at iteration entry. |
| `iteration_end_time` | `float` | Wall-clock timestamp (`time.monotonic()`) at iteration completion or abort. |
| `iteration_elapsed_s` | `float` | Time elapsed in seconds during this specific iteration. |
| `nodes_consumed` | `integer` | Additional search nodes expanded during this iteration. |
| `cumulative_nodes` | `integer` | Total cumulative search nodes expanded since root search start. |
| `nps` | `integer` | Effective search rate (nodes per second) for this iteration. |
| `best_move` | `string \| null` | UCI representation of the principal variation move found in this iteration. |
| `pv` | `list[string]` | Full principal variation (UCI move strings) discovered by this iteration. |
| `score` | `integer` | Score in centipawns (from side-to-move perspective) returned by this iteration. |
| `aspiration_retries` | `integer` | Number of aspiration window re-searches triggered during this iteration. |
| `completed` | `boolean` | `true` if the iteration ran to completion; `false` if interrupted. |
| `aborted` | `boolean` | `true` if the iteration was terminated prematurely; `false` otherwise. |
| `abort_reason` | `string \| null` | `"timeout"` if halted by deadline; `"stop_event"` if halted by thread event; `null` if completed. |
| `published` | `boolean` | `true` if the result of this iteration was published to the root search result; `false` if discarded. |
| `prev_completed_depth` | `integer` | The highest fully completed depth prior to this iteration. |
| `rfp_enabled` | `boolean` | `true` if Reverse Futility Pruning was active; `false` if baseline K0. |

---

## 3. Storage and Serialization

- **Buffer:** Accumulated in `engine.iteration_records: list[dict]`.
- **Attached to SearchResult:** Populated in `SearchResult.iteration_records` when enabled.
- **JSONL Export:** Flushed via `engine.flush_iteration_telemetry(filepath: str) -> int`.

