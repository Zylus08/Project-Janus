# Reverse Futility Pruning (RFP) Telemetry Schema — v0.44

**Milestone:** Project Janus v0.44  
**Date:** 2026-11-03  
**Status:** VALIDATED

---

## 1. Overview

The RFP telemetry instrumentation provides position-level diagnostic logging of all frontier-node pruning evaluations in `JanusSearch`. It supports both active search logging (`enable_rfp=True, diagnostic_rfp=True`) and passive counterfactual observation (`enable_rfp=False, diagnostic_rfp=True`).

When disabled (`diagnostic_rfp=False`, the default), overhead is virtually zero (a single boolean check per frontier node).

---

## 2. Event Record Schema

Each event is serialized as a JSON object with the following fields:

| Field | Type | Description |
|---|---|---|
| `fen` | `string` | The FEN representation of the board state at the evaluation node. |
| `ply` | `integer` | Distance from the search root ($ply > 0$). |
| `depth` | `integer` | Remaining nominal search depth ($1 \le depth \le rfp\_max\_depth$). |
| `static_eval` | `integer` | Static evaluation in centipawns from the perspective of the side to move (`evaluate_side_to_move`). |
| `beta` | `integer` | Upper bound of the alpha-beta search window. |
| `alpha` | `integer` | Lower bound of the alpha-beta search window. |
| `margin` | `integer` | Pruning margin in centipawns ($depth \times rfp\_margin\_per\_depth$). |
| `cutoff` | `boolean` | `true` if $static\_eval - margin \ge \beta$, else `false`. |
| `reason` | `string` | `"static_eval_ge_beta_plus_margin"` if cutoff condition satisfied; `"below_margin"` otherwise. |
| `best_move` | `string \| null` | UCI representation of the probed TT move or move returned. |
| `rfp_enabled` | `boolean` | `true` if RFP pruning was actively executed; `false` if passive observation. |

---

## 3. Storage and Export API

### In-Memory Collection
- Stored in `engine.rfp_events: list[dict]`.
- Attached to `SearchResult.rfp_events` upon completion of `search()`.
- Cleared at the beginning of each root search iteration.

### File Serialization
- Method: `engine.flush_rfp_telemetry(filepath: str) -> int`
- Appends each event as a newline-delimited JSON line (`.jsonl`).
- Empties internal buffer and returns count of flushed events.

