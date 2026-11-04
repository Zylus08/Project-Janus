# Project Janus v0.51.1 — Independent Audit Baseline & Provenance Freeze

## 1. Audit Identification & Governance

- **Audit Milestone:** Project Janus v0.51.1
- **Role:** Independent Chess Engine Auditor, Statistical Verification Engineer & Tournament Integrity Investigator
- **Repository:** `E:\ChessXML\project-janus`
- **Branch:** `v0.3-benchmark-harness`
- **Audit Target HEAD:** `fd2589ea39152a5964a0a4c73a3ea9283161b598` (`fd2589e`)
- **Parent Baseline Commit:** `238b85b` (v0.50 final)
- **Working Tree State:** Clean; zero uncommitted working tree modifications
- **Remote Operations:** Strictly prohibited (local verification and audit only)

---

## 2. Host System & Compilation Environment

| Component | Audited Specification | Verification Command / Source |
|---|---|---|
| **Operating System** | Windows 11 Enterprise / Home 10.0.26200 SP0 (AMD64) | `platform.platform()` |
| **CPU Architecture** | Intel64 Family 6 Model 154 Stepping 3, GenuineIntel (16 logical cores) | `platform.processor()` |
| **Python Runtime** | Python 3.13.2 (tags/v3.13.2:4f8bb39, Feb 4 2025, 15:23:48) [MSC v.1942 64 bit] | `sys.version` |
| **C/C++ Compiler** | Microsoft (R) C/C++ Optimizing Compiler Version 19.43.34809 for x64 | `cl.exe` via `vcvars64.bat` |
| **Visual Studio Tools** | Visual Studio 2022 Developer Tools v17.13.5 | `vcvarsall.bat` banner |
| **Stockfish Oracle** | Stockfish 19 x64 AVX2 (`E:\ChessXML\tools\stockfish\stockfish.exe`) | SHA-256 verified |

*Audit Observation on Compiler Version:* Milestone v0.51 reports cited `MSVC v19.44.35222` in narrative text; host system probe reveals active compiler is `MSVC v19.43.34809` (VS 2022 v17.13.5). The binary was compiled using this active compiler toolchain.

---

## 3. Cryptographic Evidence Freeze & Verification

Every artifact from Milestone v0.51 was verified against `analysis/v0.51/sha256_manifest.json`:
- **Files Indexed in v0.51 Manifest:** 34
- **Files Matching Bit-Exact on Disk:** 34 / 34 (100.0%)
- **Mismatches / Corrupted Files:** 0

### Key Artifact Cryptographic Signatures

| Artifact Path | SHA-256 Digest | Size (bytes) | Status |
|---|---|---|---|
| `analysis/v0.51/native/janus_native_engine.exe` | `0611bc59e52073d07b0092b183e6a373783a9e4e6a679177b02ceb4a9900fb9b` | 331,264 | Verified Bit-Exact |
| `analysis/v0.51/native/janus_native.dll` | `295aeb21eb4566c507a27eb278fa81ec793d56f6ba4353bb8eb03076722d3e52` | 253,952 | Verified Bit-Exact |
| `analysis/v0.51/native/janus_native.cpp` | `8e719e9b8613c71a96eb5cf2eff4643e1070d6fba6c02df3c2ae7ac5681d0d0e` | 55,274 | Verified Bit-Exact |
| `analysis/v0.51/corpus/openings_v051_100.json` | `2f929719ab8377e1682b3c37c6b93c762a8898bca9284aa3797db936391aca3b` | 27,613 | Verified Bit-Exact |
| `analysis/v0.51/pgn/n2_vs_k0_match.pgn` | `3aa89bfa86cf5742fe0ebaf764c24385be4523fc68ca825db79234b6b8d960f2` | 134,888 | Verified Bit-Exact |
| `analysis/v0.51/raw/match_results_raw.json` | `4c71708170c2a8d3e915006b5275811796d19ef8ea76b92ceb584d9435b89ebc` | 114,849 | Verified Bit-Exact |
| `analysis/v0.51/MATCH_PREREGISTRATION.md` | `a16531d7736468df9f20c43dc2c2c04ae1c1c1f1ec4f67645d9cc079140a3ddb` | 3,923 | Verified Bit-Exact |
| `tools/stockfish/stockfish.exe` | `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0` | 40,022,016 | Verified Bit-Exact |

All 41 tracked files (including unit tests and python search core) have been cataloged in [`analysis/v0.51.1/original_artifact_hashes.json`](file:///e:/ChessXML/project-janus/analysis/v0.51.1/original_artifact_hashes.json).

---

## 4. Audit Non-Interference Mandate

1. The `analysis/v0.51/` directory is strictly immutable; no files therein will be modified or deleted.
2. All audit analysis, recomputations, ledgers, and forensic scripts will reside in `analysis/v0.51.1/` and `docs/v0.51.1_audit_report.md`.
3. No match games will be rerun merely to adjust statistics; existing primary evidence will be evaluated on its own merits.
