# Baseline Freeze & Provenance Audit (v0.48 Phase A)

## 1. Environment & Repository Provenance

- **Repository Root:** `E:\ChessXML\project-janus`
- **Current Branch:** `v0.3-benchmark-harness`
- **HEAD Commit:** `0446ae3` (`feat(v0.47): lazy move selection qualification and ordering efficiency validation`)
- **Parent Commit:** `9858aacad01692c0119c58ec8c740f66cb75527c` (v0.46 Final)
- **Working Tree:** Clean (verified via `git status`)
- **Remote Push Policy:** Zero remote pushes permitted; local tracking branch only
- **Python Runtime:** Python 3.13.2 (64-bit, AMD64, MSC v.1942)
- **Operating System:** Windows 11 (build 10.0.26200-SP0)
- **Host CPU Hardware:** 16 logical cores

## 2. Test Suite Baseline

- **Inherited Test Discovery:** 473 tests across `tests/test_*.py`
- **Inherited Test Execution Result:** **473 / 473 PASSED** in 296.950s (commit `0446ae3`)
- **Test Integrity:** Zero regressions, zero skips, zero errors.

## 3. Configuration Freeze

| Parameter | Baseline Production (K0) | Experimental Candidate (L1) | Notes |
|---|---|---|---|
| `enable_lazy_move_selection` | `False` (immutable default) | `True` (active candidate) | Lazy move ordering flag |
| `enable_rfp` | `False` | `False` | RFP remains disabled |
| `enable_see_ordering` | `False` | `False` | MVV-LVA capture ordering active |
| `enable_history` | `True` | `True` | Butterfly history heuristic active |
| `max_killers_ply` | `64` | `64` | Two killer slots per ply |
| `enable_countermoves` | `False` | `False` | Production default |
| `enable_lmr` | `True` | `True` | Late Move Reductions active |
| `enable_nmp` | `True` | `True` | Null Move Pruning active |
| `enable_aspiration` | `True` | `True` | Aspiration search active |
| `time_policy` | `"arm_c"` | `"arm_c"` | Identical time allocation |

Both configurations share identical search extensions, evaluation functions, transposition table policies, and pruning thresholds. L1 differs exclusively by deferring candidate move sorting until after the TT move is evaluated.

## 4. Reference Engine Provenance

- **Binary Path:** `E:\ChessXML\tools\stockfish\stockfish.exe`
- **Reported Version:** Stockfish 19
- **SHA-256 Digest:** `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`
- **Integrity Status:** Verified exact match to v0.46 and v0.47 inherited reference digest.
- **Reference Corpus:** 37-position diagnostic corpus copied to `analysis/v0.48/corpus/diagnostic_corpus.json` (SHA-256: `9f72ea66729cb190163eb6cd4b9dc4309dd25ca384d56533911449f6985ccb36`).

