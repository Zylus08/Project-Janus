# Project Janus v0.51 — Baseline Freeze & Provenance Record

**Milestone:** Project Janus v0.51  
**Repository:** `E:\ChessXML\project-janus`  
**Branch:** `v0.3-benchmark-harness`  
**HEAD Commit:** `238b85b84d2f67a64db2049dbb530e527c9db051`  
**Parent Commit:** `d037f77` (v0.49 Final)  
**Production Reference:** Python K0 (`enable_lazy_move_selection=False`, `enable_rfp=False`)  
**Experimental Native Candidate:** C++17 N2 Prototype  
**Evaluation Reference:** Stockfish 19 x64 AVX2  

---

## 1. System Platform & Environment Freeze

- **Operating System:** Windows 11 Enterprise AMD64 (Version 10.0.26200-SP0)
- **CPU Architecture:** Intel64 Family 6 Model 154 Stepping 3, GenuineIntel (16 logical cores)
- **Python Version:** Python 3.13.2 64-bit (`E:\ChessXML\project-janus\.venv\Scripts\python.exe`)
- **C/C++ Compiler:** Microsoft (R) C/C++ Optimizing Compiler Version 19.44.35222 for x64 (MSVC BuildTools 2022)
- **Compilation Toolchain Script:** `C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat`
- **Working Tree State:** Clean (verified prior to v0.51 work, 0 uncommitted modifications)

---

## 2. Core Cryptographic Hash Registry (SHA-256)

| Artifact Description | File Path | SHA-256 Hash |
|---|---|---|
| **Stockfish Reference Engine** | `../tools/stockfish/stockfish.exe` | `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0` |
| **v0.50 Native Source Core** | `analysis/v0.50/native/janus_native.cpp` | `a10af9d88744d2c8e81afc34ada9c98f9ad4ba220e81bae873f2c482ff71edc9` |
| **v0.50 Native Compiled DLL** | `analysis/v0.50/native/janus_native.dll` | `5f2cbb4bd8c3e708b8066200b4e8e3f2d5a3d5622dcfd397ff67d7501784ab4e` |
| **v0.50 Python ctypes Bridge**| `analysis/v0.50/native/janus_native_bridge.py` | `07f6ae13d8095bc1bb9356d2ee01579344445695028c119560f64be81f969eb2` |
| **37-Pos Diagnostic Corpus** | `analysis/v0.50/corpus/diagnostic_corpus.json` | `5ef81bf16fa06fbcf7ae4fb16ef207572d424b953835678ebfd314787f76634b` |
| **12-Pos Tactical Corpus** | `analysis/v0.50/corpus/tactical_regression_corpus.json` | `f085189eb814bfb904df86576856012ceaa140f7f3cbef17296213768fb3a0c4` |

---

## 3. Inherited Regression Test Suite Verification

- **Command:** `python -m unittest discover -s tests -p "test_*.py"`
- **Test Count:** 473 tests
- **Result:** **473 PASSED**, 0 failed, 0 skipped
- **Execution Time:** 301.171 seconds
- **Exit Status:** 0 (Clean)

---

## 4. Reference Configurations

1. **Production Reference (Python K0):**
   - Pure Python / python-chess alpha-beta negamax implementation in `src/janus/search.py`.
   - RFP disabled (`enable_rfp = False`).
   - Move selection is eager full-list sorting (`enable_lazy_move_selection = False`).
   - Production default configuration since v0.45.
2. **Experimental Candidate (Native N2):**
   - Monolithic C++17 bitboard engine (`janus_native.cpp`).
   - Bitboard move generation, 1M-entry transposition table, alpha-beta negamax with iterative deepening and quiescence search.
   - Starting point for standalone UCI engine integration in v0.51.

