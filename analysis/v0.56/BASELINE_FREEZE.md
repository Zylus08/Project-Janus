# Project Janus v0.56 — Baseline Freeze & Environmental Audit

**Milestone:** v0.56  
**Auditor:** Principal Chess Engine Architect, C++17 Search Engineer & Reproducibility Auditor  
**Date:** 2026-11-05  
**Repository:** `E:\ChessXML\project-janus`  
**Parent Baseline Commit:** `a80ba2a`  
**Active HEAD Commit:** `f6025c3`  
**Production Reference Engine:** Janus Native N5 (C++17 Standalone UCI Engine)  
**Experimental Candidate:** Janus Native N7 (N5 + Static Exchange Evaluation Capture Ordering)  

---

## 1. System Environment Freeze

The experimental environment for Milestone v0.56 is frozen with the following toolchain and operating system specifications:

| Component | Specification / Version | Verification Method |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 Enterprise (Build 26100), 64-bit | `systeminfo` |
| **CPU Architecture** | AMD Ryzen 7 7840HS (16 logical cores @ 3.80GHz) | Hardware probe |
| **Host Memory** | 16 GB DDR5 | System info |
| **C/C++ Compiler** | Microsoft Visual C++ BuildTools 2022 (v19.43.34809 for x64) | `cl.exe` |
| **Compilation Flags** | `/O2 /std:c++17 /EHsc /arch:AVX2` | Compiler invocation |
| **Python Environment**| Python 3.13.2 64-bit (project `.venv`) | `sys.version` |
| **External Oracle** | Stockfish 19 x64 AVX2 | Bit-exact executable verification |
| **Stockfish Hash** | `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0` | SHA-256 |
| **Inherited Tests** | 608 / 608 Passed (100% pass rate in 319.9s) | `unittest discover -s tests` |

---

## 2. Frozen Production Engine Artifacts (Janus N5)

The production baseline engine (Janus N5) is frozen bit-for-bit from v0.55:

| Artifact Path | SHA-256 Digest | Size (Bytes) | Role |
| :--- | :--- | :--- | :--- |
| `analysis/v0.55/native/janus_native.cpp` | `e101ad17d459771d65d046e67ca54dc233fcfca4e2e978128162bb85a5008c6d` | 70,859 | Frozen C++17 source code |
| `analysis/v0.55/native/janus_native.dll` | `aa924af8b08d54c46d4379b2482b621037127cad32ddda99a06c83aa53362597` | 256,512 | Frozen shared library for bridges |
| `analysis/v0.55/native/janus_native_engine.exe` | `f3a54517c2704cfc73c1d8e3b9b50c634f52e1cead2604b13cc942ceff708998` | 338,432 | Frozen standalone UCI binary |

### 2.1 Production UCI Option Defaults
The production engine boots with the following frozen search configuration:
```text
option name Hash type spin default 16 min 1 max 1024
option name UseLMR type check default true
option name LMRMinDepth type spin default 3 min 1 max 10
option name LMRMoveThreshold type spin default 4 min 1 max 20
option name LMRBaseReduction type spin default 1 min 1 max 4
option name UseKillerOrdering type check default true
option name UseHistoryOrdering type check default true
option name UsePVS type check default false
```

---

## 3. Milestone Objective & Scope Constraints

The objective of Milestone v0.56 is to formulate, implement, verify, and empirically evaluate a native C++17 **Static Exchange Evaluation (SEE)** mechanism for **capture move ordering** in the Janus search core.

### Explicit Scope Constraints:
1. **Ordering Only:** SEE is evaluated exclusively as a move-ordering heuristic.
2. **Pruning Strictly Prohibited:** SEE-based capture pruning, delta pruning modifications, or move omission are **strictly out of scope**. Every capture eligible for search in N5 must remain eligible in N7.
3. **No Side Modifications:** No alterations to legal move generation, piece-square tables, material weights, static evaluation, null-move pruning, aspiration windows, or dynamic LMR.
4. **Preservation of N5 Defaults:** Production configuration remains N5 (`UseSEEOrdering=false`) until candidate N7 qualifies across correctness, tactical safety, and preregistered strength gates.
