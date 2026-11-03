# Move-Ordering Telemetry Specification & Validation (Gate C)

## 1. Overview
In accordance with Phase C of the v0.46 specification, non-invasive move-ordering diagnostic telemetry has been implemented in `src/janus/search.py` and exposed via UCI in `src/janus/uci.py` (`--diag-ordering`).

## 2. Telemetry Fields & Structure

### SearchResult Fields:
- `ordering_stats: dict`: Summary statistics of move-ordering performance across the search:
  - `total_cutoffs: int`: Total number of beta cutoffs encountered in negamax.
  - `first_move_cutoffs: int`: Number of beta cutoffs produced by the first ordered move (index 0).
  - `late_move_cutoffs: int`: Number of beta cutoffs produced by moves at index $\ge 1$.
  - `first_move_cutoff_rate: float`: $\frac{\text{first\_move\_cutoffs}}{\text{total\_cutoffs}}$ (0.0 if total cutoffs == 0).
  - `tt_cutoffs: int`: Cutoffs produced by the TT suggested move.
  - `killer_cutoffs: int`: Cutoffs produced by killer moves.
  - `countermove_cutoffs: int`: Cutoffs produced by countermoves.
  - `capture_cutoffs: int`: Cutoffs produced by capture moves.
  - `quiet_cutoffs: int`: Cutoffs produced by quiet moves.
  - `total_ordering_time_s: float`: Cumulative wall-clock seconds spent in `moves.sort()`.
- `ordering_events: list[dict]`: Per-cutoff event records:
  - `depth: int`
  - `ply: int`
  - `legal_moves: int` (total legal moves in position)
  - `searched_moves: int` (number of moves evaluated before cutoff occurred)
  - `cutoff_index: int` (0-indexed position of cutoff move)
  - `is_first_move: bool` (`cutoff_index == 0`)
  - `move: str` (UCI format)
  - `is_capture: bool`
  - `is_tt_move: bool`

### API Methods:
- `searcher.flush_ordering_telemetry(filepath: str) -> int`: Flushes buffered events to a `.jsonl` file and clears the in-memory event list to prevent memory bloat during long matches.

## 3. Overhead & Invariance Verification
1. **Zero-overhead default**: When `diagnostic_ordering=False` (production default), `ordering_stats` is `{}` and `ordering_events` is `[]`. No timing calls (`time.perf_counter`) or event dictionary allocations occur in the search loop.
2. **Result Invariance**: As proven by `tests/test_v046_move_ordering_telemetry.py::TestV046MoveOrderingTelemetry::test_ordering_telemetry_invariance`, the engine returns exact identical `best_move`, `score`, and node counts whether `diagnostic_ordering` is True or False.
3. **Automated Unit Tests**:
   - `test_ordering_telemetry_disabled_by_default`: PASS
   - `test_ordering_telemetry_enabled`: PASS
   - `test_ordering_telemetry_invariance`: PASS
   - `test_flush_ordering_telemetry`: PASS

## 4. Gate C Validation
Gate C is fully satisfied. The search engine is now equipped to record precise move-ordering behavior across all benchmark positions.

