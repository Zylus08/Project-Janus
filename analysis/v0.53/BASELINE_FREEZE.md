# Project Janus v0.53 — Baseline Freeze & Provenance Audit

**Milestone:** v0.53 — Principal Variation Search (PVS), Window Correctness & Controlled Strength Ablation  
**Date:** 2026-11-05  
**Parent Baseline Commit:** `127d0c6318dd88d522048205a115e82c1a658dbe` (v0.52 Final)  
**Branch:** `v0.3-benchmark-harness`  
**Production Reference Baseline:** Janus Native N3 (C++17 native search core, LMR enabled by default)  
**Historical References:** Native N2 (`UseLMR=false`) and Python K0 (preserved immutable)  
**Audit Status:** **VERIFIED, IMMUTABLE & FROZEN**  

---

## 1. System Environment Audit

| Component | Specification | Provenance / Verification |
|---|---|---|
| **Operating System** | Windows 11 Enterprise AMD64 | Architecture: 16 logical cores |
| **Python Environment** | Python 3.13.2 64-bit | Path: `E:\ChessXML\project-janus\.venv\Scripts\python.exe` |
| **C++ Compiler** | Microsoft Visual C++ BuildTools 2022 (v19.43.34809) | Tool: `cl.exe /std:c++17 /O2 /EHsc` |
| **Stockfish Reference** | Stockfish 19 x64 AVX2 | SHA-256: `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0` |
| **Regression Suite** | 541 Unit & Regression Tests | Status: 541 / 541 Passing (100.0%, 290.26s) |

---

## 2. Frozen Cryptographic Checksums (v0.52 Production Baseline)

| Frozen Artifact | Relative Path | SHA-256 Checksum |
|---|---|---|
| **C++17 Engine Source (N3)** | `analysis/v0.52/native/janus_native.cpp` | `ab432160daeefda631350620126fd15a6ee983a792dba78339e0667d0c2fc92b` |
| **Native UCI Engine Binary** | `analysis/v0.52/native/janus_native_engine.exe` | `235630650d7567d90e87b4f817b9f4682e33ed07f501027b25628bdba8d8091c` |
| **Native Shared Library DLL**| `analysis/v0.52/native/janus_native.dll` | `870717c07f86a59f3041d6c19571f2f70fbf1d41fb465d3ebd202dfbe64d7573` |
| **Native Python Bridge** | `analysis/v0.52/native/janus_native_bridge.py` | `cc6b3e813fca11f72466aaf352e6ec40d12684e3f604ab00fc0e59e3e73a3590` |
| **Tournament Controller** | `analysis/v0.52/tests/tournament_controller.py` | `d46f868c8d7789c8593f7a5bf47e3509a7cee53dcc8b1fc78ccb21be10dbc9fe` |
| **LMR Unit Tests** | `tests/test_native_lmr_semantics.py` | `a092edb182225519c018fb5ae6856821ea554b4e4b02b6c5b4b1f76b0eb38d02` |
| **Controller Unit Tests** | `tests/test_tournament_controller.py` | `4a97739e013691745db0e8d1170bc5a172703978efb457711b9e41e9a5614e00` |
| **Opening Suite (100 Pairs)**| `analysis/v0.52/corpus/openings_v052_100.json` | `2f929719ab8377e1682b3c37c6b93c762a8898bca9284aa3797db936391aca3b` |
| **Diagnostic Corpus (37)** | `analysis/v0.52/corpus/diagnostic_corpus.json` | `9f72ea66729cb190163eb6cd4b9dc4309dd25ca384d56533911449f6985ccb36` |
| **Validation Corpus (16)** | `analysis/v0.52/corpus/validation_corpus.json` | `0f1c7a1b3a2350e8db0c29e2e66576b253a93676f153d18a5d06abf86f432cea` |
| **Tactical Regression (12)** | `analysis/v0.52/corpus/tactical_regression_corpus.json` | `a4bbf5b925625d3921ba37a5b745bc3428437ca2543ef985e54fde934da96a46` |
| **v0.52 Milestone Report** | `docs/v0.52_report.md` | `58f36b692554f77d436eadaddb35890219733db9466298f92b40faeb9b9dc173` |

---

## 3. Production Configuration Baseline (N3)

The production configuration inherited from v0.52 has LMR active by default:
- `UseLMR = true`
- `LMRMinDepth = 3`
- `LMRMoveThreshold = 4`
- `LMRBaseReduction = 1`

All historical v0.52 artifacts are preserved immutable. Candidate N4 will be authored in isolated directory `analysis/v0.53/native/` with `UsePVS` as the sole new experimental variable.

