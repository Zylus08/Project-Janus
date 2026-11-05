# Project Janus v0.55 — Baseline Freeze & Verification Report

**Milestone:** v0.55  
**Date:** 2026-11-05  
**Role:** Principal Chess Engine Research Architect & Independent Reproducibility Auditor  
**Repository:** `E:\ChessXML\project-janus`  
**Branch:** `v0.3-benchmark-harness`  
**Parent Commit HEAD:** `165c7a5` (containing `181f3f8` v0.54 promotion plus trailing newline documentation)  
**Historical Production Baseline:** Janus Native N5 (C++17, LMR + Killer + History enabled, PVS disabled)  

---

## 1. Environmental Freeze & System Architecture

```text
Host OS              : Windows 11 Enterprise (x64, Build 26100)
Architecture         : AMD64 (16 logical cores, AMD Ryzen 7 7840HS)
Compiler             : Microsoft Visual C++ BuildTools 2022 (v19.43.34809 for x64)
Optimization Flags   : /O2 /std:c++17 /EHsc
Python Runtime       : 3.13.2 (64-bit, AMD64) in virtual environment (.venv)
Reference Engine     : Stockfish 19 x64 AVX2
Stockfish SHA-256    : 45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0
```

---

## 2. Cryptographic Checksums & Source Files

### 2.1 Frozen v0.54 Production Binaries
```text
File: analysis/v0.54/native/janus_native.cpp
Size: 70,859 bytes
SHA256: 8ec9c03e5ab1bf67d32255475b240e2a601a12e311293bf8a514f9b68734ed1e

File: analysis/v0.54/native/janus_native.dll
Size: 256,512 bytes
SHA256: df6664d9ef1708fd3be46307fbf4908ade31e01d3e1007993e323d30c886fc07

File: analysis/v0.54/native/janus_native_engine.exe
Size: 338,432 bytes
SHA256: 1aeda488f3cf5c417c9c5b2fea8afafc423857371c63ea79bc0d3dbe7142c941

File: analysis/v0.54/native/janus_native_bridge.py
Size: 12,960 bytes
SHA256: 5ce16e2f2fa6a3208026f6ca4308de0ee4bc5741b04540cb0e955c24c738c586
```

### 2.2 Frozen v0.55 Milestone Binaries
```text
File: analysis/v0.55/native/janus_native.cpp
Size: 70,859 bytes
SHA256: e101ad17d459771d65d046e67ca54dc233fcfca4e2e978128162bb85a5008c6d

File: analysis/v0.55/native/janus_native.dll
Size: 256,512 bytes
SHA256: aa924af8b08d54c46d4379b2482b621037127cad32ddda99a06c83aa53362597

File: analysis/v0.55/native/janus_native_engine.exe
Size: 338,432 bytes
SHA256: f3a54517c2704cfc73c1d8e3b9b50c634f52e1cead2604b13cc942ceff708998

File: analysis/v0.55/native/janus_native_bridge.py
Size: 12,960 bytes
SHA256: 5ce16e2f2fa6a3208026f6ca4308de0ee4bc5741b04540cb0e955c24c738c586
```

---

## 3. Production UCI Defaults Verification

The compiled executable `analysis/v0.55/native/janus_native_engine.exe` was interrogated via pipe communication with the `uci` handshake command:

```text
id name Janus 0.55 Native
id author Project Janus Team
option name UseKillerOrdering type check default true
option name UseHistoryOrdering type check default true
option name UsePVS type check default false
option name UseLMR type check default true
option name LMRMinDepth type spin default 3 min 2 max 8
option name LMRMoveThreshold type spin default 4 min 2 max 16
option name LMRBaseReduction type spin default 1 min 1 max 3
uciok
```

All 7 production defaults strictly match the v0.54 Category A promotion mandate:
- `UseKillerOrdering = true`
- `UseHistoryOrdering = true`
- `UsePVS = false`
- `UseLMR = true`
- `LMRMinDepth = 3`
- `LMRMoveThreshold = 4`
- `LMRBaseReduction = 1`

---

## 4. Full Inherited Test Suite Verification

The complete regression test harness was executed prior to undertaking experimental modifications:

```text
Command: .venv\Scripts\python.exe -m unittest discover -s tests
Result : Ran 601 tests in 79.834s
Status : OK (0 failures, 0 errors, 0 skips)
```

All 601 tests, including all native search core semantics, UCI protocol handlers, and move-ordering tests pass unconditionally.

---

## 5. Baseline Freeze Verdict

**GATE 0 STATUS: PASSED**

The working environment is clean, deterministic, reproducible, and fully verified against cryptographic and behavioural controls. Proceeding to Phase 0.1 / 0.2 evidence audits.

