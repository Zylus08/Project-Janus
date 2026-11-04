# PROJECT JANUS v0.54 — BASELINE RECONNAISSANCE & FREEZE REPORT

**Milestone:** Project Janus v0.54  
**Date:** 2026-11-05  
**Repository Branch:** `v0.3-benchmark-harness`  
**Parent Baseline Commit:** `c90b6736e4fe30c2ce8fad38564b7c1484e03dd8` (v0.53 Final)  
**Production Reference:** Janus Native N3 (C++17 native search core, LMR enabled, PVS disabled)  
**Experimental Candidate:** Janus Native N5 (Native N3 + Improved Move Ordering)  
**Classification:** Controlled Move-Ordering Research  
**Remote Git Operations:** Strictly Prohibited  

---

## 1. Baseline Environment Verification

### 1.1 Hardware and Host Environment
- **CPU:** AMD64 (16 logical execution cores)
- **Host OS:** Windows 11 Enterprise AMD64
- **C/C++ Compiler:** Microsoft Visual C++ BuildTools 2022 (v19.43.34809 x64)
- **Compilation Flags:** `/O2 /std:c++17 /EHsc`
- **Python Environment:** Python 3.13.2 64-bit (`project-janus/.venv`)
- **External Diagnostic Reference:** Stockfish 19 x64 AVX2 (`45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`)

### 1.2 Git Repository State
- **Branch:** `v0.3-benchmark-harness`
- **HEAD Commit:** `c90b673`
- **Working Tree:** Verified clean (`nothing to commit, working tree clean`)
- **Inherited Unit Tests:** 546 / 546 tests passing

---

## 2. Frozen Production Baseline (Janus Native N3) Checksums

The frozen production reference is Janus Native N3 from v0.53, configured with:
- `UseLMR = true` (`LMRMinDepth=3`, `LMRMoveThreshold=4`, `LMRBaseReduction=1`)
- `UsePVS = false` (Category B qualification retained `false` as production default)

| File | Relative Path | Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :---: | :--- |
| **C++ Search Engine Source** | `analysis/v0.53/native/janus_native.cpp` | 64,020 | `191684be4b96ae878cde775bba82b9f7c49ee82a544c2289cce6484f15299970` |
| **Standalone UCI Engine Binary** | `analysis/v0.53/native/janus_native_engine.exe` | 335,872 | `2822ec90e10bf885c75d8f68ed1e6f82cead8d4eb8650d974eca98db0cf3271a` |
| **FFI Shared Library DLL** | `analysis/v0.53/native/janus_native.dll` | 254,976 | `dbaa1826dcb7a87554ebf8618f8ef8a3ec8fc34459dd0d07ed0ba6cf2024e36a` |
| **Python FFI Bridge** | `analysis/v0.53/native/janus_native_bridge.py` | 8,944 | `1fcf9e31d4576395b8744046dcf80f195d2ad9fcf1cb9f32b85e0ff5eeea3b11` |

---

## 3. Subsystem Audit

### 3.1 Transposition Table
- Size: 1,048,576 entries (1M entries, 24 bytes per entry = 24.0 MB).
- Entry format: Zobrist key (64-bit), score (16-bit, mate-normalized), depth (8-bit), flag (8-bit: Exact/Upper/Lower), age (8-bit), best move (16-bit).
- Replacement policy: Depth-preferred with generational aging (`g_tt_age`).

### 3.2 Time Management
- Polling frequency: Checked every 2048 nodes in `negamax()` and `quiescence()`.
- Abort deadline: Wall-clock expiration via `std::chrono::steady_clock`.

### 3.3 Static Evaluation
- Midgame and Endgame piece-square tables (Pawns, Knights, Bishops, Rooks, Queens, Kings).
- Simplified tapered evaluation based on phase.

---

## 4. Phase 0 Gate Clearance

- [x] Repository HEAD is clean at `c90b673`.
- [x] Baseline N3 source and binary checksums recorded.
- [x] Toolchain verified and operational.
- [x] Subsystems audited and confirmed immutable.

**Disposition:** Gate 0 is **PASSED**. Proceed to Phase 1 (Move Ordering Architecture Audit).

