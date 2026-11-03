# Baseline Freeze & Environment Verification — v0.44

**Milestone:** Project Janus v0.44  
**Date:** 2026-11-03  
**Status:** PASS (Gate A Validated)

---

## 1. Environment & Version Baseline

| Parameter | Recorded Value |
|---|---|
| **Repository Root** | `E:\ChessXML\project-janus` |
| **Git Branch** | `v0.3-benchmark-harness` |
| **Git HEAD** | `e30a48ee7e8be5a073f32ee7839ec52857ce79c6` |
| **Parent Milestone Commit** | `605a0899bb18579d479152345517172821dddf6f` (v0.43 Final) |
| **Diff `605a089..e30a48e` in `src/`** | Empty (0 changes to engine source code) |
| **Working Tree Status** | Clean |
| **Python Environment** | Python 3.13.2 (64-bit AMD64) |
| **Python Executable** | `E:\ChessXML\project-janus\.venv\Scripts\python.exe` |
| **Stockfish Executable** | `E:\ChessXML\tools\stockfish\stockfish.exe` |
| **Stockfish SHA-256** | `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0` |

---

## 2. v0.43 Replication Artifact Verification

All critical raw data files and report artifacts from the v0.43 independent replication were indexed and verified.
Digest catalog stored at [`analysis/v0.44/v043_reference_manifest.json`](file:///E:/ChessXML/project-janus/analysis/v0.44/v043_reference_manifest.json).

### Key Artifact Hashes

| Artifact Path | SHA-256 Digest | Status |
|---|---|---|
| `analysis/v0.43/match_replication/match_results.json` | `dc4b03634c4b2d2dbc1ed5d70be47aab6a603013a8a9abe3b381d55e7727efc0` | Verified Match |
| `analysis/v0.43/match_replication/match_results.pgn` | `3c966e1d687f14952b45f994987320454742643dec8b883f19e70b39db60e7ed` | Verified Match |
| `analysis/v0.43/match_replication/match_moves.csv` | `f4afbe616275e90d66b003927f0af6a817dfcdda2efd47b4dc7aa3ee42df4ddb` | Verified Match |
| `analysis/v0.43/match_replication/match_results.csv` | `cae97d82cdd71b82d3b214c423731d94cd23c019670b87235c00710a79e8f574` | Verified Match |
| `analysis/v0.43/match_replication/attempt_log.json` | `f85f29293e19f5145943eb63d70dd0e8ef60166c08c509fa0197fa07c23845f7` | Verified Match |
| `analysis/v0.43/openings_v043_100.json` | `2f929719ab8377e1682b3c37c6b93c762a8898bca9284aa3797db936391aca3b` | Verified Match |
| `docs/v0.43_report.md` | `0b7774136fc167e4dd336fe7127e909a8047915525287f39d679632832ee1057` | Indexed |

*Note on markdown hashes:* Six markdown and json summary files in `analysis/v0.43/` received trailing newline normalization in commit `e30a48e` (`FINAL_DECISION.md`, `INDEPENDENT_AUDIT.md`, `RFP_REPLICATION_EXECUTION_REPORT.md`, `RFP_REPLICATION_STATISTICAL_REPORT.md`, `SEARCH_STRENGTH_ATTRIBUTION.md`, `independent_audit.json`). The raw experimental dataset (all CSV, JSON, PGN files under `match_replication/` and `openings_v043_100.json`) remained completely byte-identical.

---

## 3. Baseline Unit Test Suite Execution

- **Command:** `& 'E:\ChessXML\project-janus\.venv\Scripts\python.exe' -m unittest discover -s tests -p 'test_*.py'`
- **Total Tests:** 451
- **Passed:** 451
- **Failed:** 0
- **Errors:** 0
- **Execution Time:** 406.267 seconds
- **Pass Rate:** 100.0%

---

## 4. Gate A Verification & Sign-off

- [x] Clean working tree confirmed.
- [x] Python virtual environment validated.
- [x] Stockfish 19 binary digest validated.
- [x] v0.43 replication artifacts locked and digested.
- [x] Complete test suite executed with 100% pass rate (451/451).

**Gate A Status:** **PASS** — Proceeding to Phase B (RFP Implementation Audit).

