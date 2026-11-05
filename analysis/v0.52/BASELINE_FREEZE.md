# Project Janus v0.52 — Baseline Freeze & Provenance Specification

## 1. Governance & Provenance

- **Milestone:** Project Janus v0.52
- **Objective:** Native Late Move Reductions (LMR), Tactical Safety & Controlled Strength Ablation
- **Repository:** `E:\ChessXML\project-janus`
- **Branch:** `v0.3-benchmark-harness`
- **Parent Commit:** `70a148590d96d2a84e96db4e1eec57849c716259` (`70a1485`, v0.51.1 final)
- **Production Reference Baseline:** Janus Native N2 (v0.51.1 audited)
- **Experimental Candidate:** Janus Native N3 (N2 + Late Move Reductions)
- **Historical Production Reference:** Python K0 (preserved immutable)
- **Working Tree State:** Clean; zero uncommitted modifications

---

## 2. Host System & Compilation Environment

| Environment Component | Audited Specification | Verification Source |
|---|---|---|
| **Operating System** | Windows 11 Enterprise/Home 10.0.26200 SP0 (AMD64) | `platform.platform()` |
| **Processor Architecture** | Intel64 Family 6 Model 154 Stepping 3, GenuineIntel (16 logical cores) | `platform.processor()` |
| **Python Runtime** | Python 3.13.2 64-bit (`project-janus\.venv\Scripts\python.exe`) | `sys.version` |
| **C/C++ Compiler** | Microsoft (R) C/C++ Optimizing Compiler Version 19.43.34809 for x64 | `cl.exe` |
| **Compilation Flags** | `/O2 /std:c++17 /EHsc` | Build scripts |
| **Developer Tools** | Microsoft Visual Studio 2022 BuildTools v17.13.5 (`vcvars64.bat`) | MSVC Banner |
| **Stockfish Oracle** | Stockfish 19 x64 AVX2 (`tools/stockfish/stockfish.exe`) | SHA-256 verified |

---

## 3. Cryptographic Signature Registry

### 3.1 Frozen Reference Baseline (N2)
The N2 baseline is immutable and frozen as audited in v0.51.1:

| Artifact Path | Description | SHA-256 Digest | Size (bytes) |
|---|---|---|---|
| `analysis/v0.51/native/janus_native.cpp` | Frozen N2 C++17 Source | `8e719e9b8613c71a96eb5cf2eff4643e1070d6fba6c02df3c2ae7ac5681d0d0e` | 55,274 |
| `analysis/v0.51/native/janus_native_engine.exe` | Frozen N2 UCI Executable | `0611bc59e52073d07b0092b183e6a373783a9e4e6a679177b02ceb4a9900fb9b` | 331,264 |
| `analysis/v0.51/native/janus_native.dll` | Frozen N2 FFI Shared Library | `295aeb21eb4566c507a27eb278fa81ec793d56f6ba4353bb8eb03076722d3e52` | 253,952 |

### 3.2 Evaluation Corpora
| Corpus Path | Purpose | SHA-256 Digest | Count |
|---|---|---|---|
| `analysis/v0.52/corpus/openings_v052_100.json` | 100-pair tournament opening suite | `2f929719ab8377e1682b3c37c6b93c762a8898bca9284aa3797db936391aca3b` | 100 pairs |
| `analysis/v0.52/corpus/diagnostic_corpus.json` | 37-position search diagnostic corpus | `9f72ea66729cb190163eb6cd4b9dc4309dd25ca384d56533911449f6985ccb36` | 37 positions |
| `analysis/v0.52/corpus/validation_corpus.json` | 16-position independent validation corpus | `1275ca82424fe566f1fcb7dbe2671542f7c02bcfb40436440263f35fe8f032aa` | 16 positions |
| `analysis/v0.52/corpus/tactical_regression_corpus.json`| 12-position tactical regression corpus | `a4bbf5b925625d3921ba37a5b745bc3428437ca2543ef985e54fde934da96a46` | 12 positions |

---

## 4. Test Suite Baseline
- Inherited Regression Tests: **473 / 473 passed**
- Native Draw Semantics Tests: **12 / 12 passed**
- Native Memory Safety Tests: **8 / 8 passed**
- Native UCI Protocol Tests: **10 / 10 passed**
- Native Repetition Semantics Tests: **10 / 10 passed**
- **Total Verified Tests at Freeze:** **513 / 513 passed (100.0%)**

