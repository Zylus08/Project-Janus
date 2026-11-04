# Project Janus v0.51.1 — Tournament Controller Forensics Report

## 1. Controller Architecture & Lifecycle Audit

The tournament runner [`analysis/v0.51/tests/run_preregistered_match.py`](file:///e:/ChessXML/project-janus/analysis/v0.51/tests/run_preregistered_match.py) was audited for process lifecycle, configuration integrity, and exception handling.

### 1.1 Engine Identity Verification
- **Candidate N2:** Invoked via `subprocess.Popen([str(ENGINE_EXE)])` using `analysis/v0.51/native/janus_native_engine.exe`.
  - Process standard streams: `stdin=PIPE`, `stdout=PIPE`, `bufsize=1` (line-buffered).
  - Clean handshake: `uci` followed by `isready` waiting for `readyok`.
  - Clean separation: `ucinewgame` dispatched before every game, ensuring complete Transposition Table clearing and history stack resets (`native_reset_history()`).
- **Production Baseline K0:** Invoked via in-process Python `JanusSearch(enable_lazy_move_selection=False, enable_rfp=False)`.
  - Feature flags verify that RFP was disabled (`enable_rfp=False`) and lazy move selection was disabled (`enable_lazy_move_selection=False`).
  - Board representation: Standard `chess.Board`.

---

## 2. Match Integrity & Result Accounting

### 2.1 Result Determination & Move Legality
The controller independently tracks the official game state via `chess.Board`:
- For N2 moves: Parses UCI string from engine `bestmove` token, verifies legality against `board.legal_moves`. If illegal, immediately awards win to opponent.
- For K0 moves: Retrieves `k0_res.best_move`, verifies legality against `board.legal_moves`.
- **Audit Finding:** Across all 200 games, **zero illegal moves** were emitted by either engine.

### 2.2 Game Persistence & Adjudication Flow
- **PGN Stream:** Every game is appended immediately to `analysis/v0.51/pgn/n2_vs_k0_match.pgn` with full headers and flushed.
- **Raw Telemetry:** Every game result, plies, and termination reason is recorded in `analysis/v0.51/raw/match_results_raw.json`.
- **Silent Retries / Dropped Games:** **None.** Exactly 200 game slots were executed in strict sequence from Round 1 to Round 200.

---

## 3. Discrepancies & Controller Deviations

1. **Artificial Horizon Adjudication ($150\text{ plies}$ vs $200\text{ plies}$):**
   - In `run_preregistered_match.py`, line 108 specifies `max_plies: int = 150`.
   - In `MATCH_PREREGISTRATION.md`, Section 4.6 specified a horizon of 200 plies (100 moves).
   - This divergence caused 9 games to terminate prematurely at ply 150 as `draw_max_plies_horizon`.
   - *Impact Analysis:* As established in [`TERMINATION_FORENSICS.md`](file:///e:/ChessXML/project-janus/analysis/v0.51.1/TERMINATION_FORENSICS.md) and [`STATISTICAL_RECONCILIATION.md`](file:///e:/ChessXML/project-janus/analysis/v0.51.1/STATISTICAL_RECONCILIATION.md), N2 was ahead in material in 5 of these games, and conservative rescoring demonstrates zero impact on the tournament verdict.
2. **Missing Per-Move Clock Telemetry:**
   - The controller recorded total game time and move count, but did not store individual move-by-move timestamp arrays in the raw JSON output.
   - Clocks were maintained in variables `wtime` and `btime` during game execution and enforced strictly on each move.

---

## 4. Gate 3 Finding

**Gate 3 Status: PASSED.**  
No systematic controller bias or fatal flaw exists. Both engines were governed by identical, fair rules, and the recorded game outcomes represent genuine chess results.
