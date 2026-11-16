# Janus Hybrid H1 — Candidate Freeze & Provenance Manifest (Phase 10)

**Milestone:** Phase 2, Milestone P2.1  
**Candidate Designation:** Janus Hybrid H1 (R1 Search + Original NNUE Model H1)  
**Freeze Date:** November 16, 2026  
**Auditor:** Principal Computer Chess Architect & Independent Experimental Auditor  

---

## 1. Candidate Identity & Cryptographic Hashes

Candidate **Janus Hybrid H1** is frozen for formal tournament and benchmark qualification. No model weights, search heuristics, or compiler flags may be modified after this freeze.

| Artifact Component | Relative Path | File Size | SHA-256 Cryptographic Hash |
| :--- | :--- | :---: | :--- |
| **Candidate Executable** | `analysis/phase2/p2.1/control/janus_hybrid_h1.exe` | 1,850,880 B | `755C451D064EA38ECC400274CBCE48D28B6F43F67747BB63C0F4E84F6EA4F97A` |
| **Candidate Shared Lib** | `analysis/phase2/p2.1/control/janus_hybrid_h1.dll` | 1,776,128 B | `D73EB8425F2F875DBD2AB2FFDD616072468955D36820F0F0D604419AAB074ED3` |
| **Quantized Weights** | `analysis/phase2/p2.1/models/janus_nnue_h1.bin` | 213,468 B | `FD4D8105C39FD9A071C48CA1DD2298BC64A13D7023C57C4C34E840D24CBFA616` |
| **Float PyTorch Checkpoint** | `analysis/phase2/p2.1/models/janus_nnue_h1_float.pt` | 430,953 B | `DEBB615462D696C8EBC3685458CE5D9C23D81EC53B83F419BC47DF560F459032` |
| **Compiled Weight Header**| `engine/classical_x/r1/r1_nnue_weights.hpp` | 312,211 B | `11F9E345DFF6E272895697A13C41DDA0527CFBC92C1D42939B54EEF8D279CD9B` |

---

## 2. Training Dataset Provenance & Split Manifest

- **Pipeline Version:** `P2.1_V1`
- **Training Seed:** `42`
- **Total Valid Games Ingested:** 583 games from Phase 1 tournaments
- **Deduplicated Position Volume:** 50,978 canonical positions
  * **Train Split:** 40,736 positions (`janus_nnue_train.jsonl`, SHA-256: `78cce009b2636171...`)
  * **Validation Split:** 5,127 positions (`janus_nnue_val.jsonl`, SHA-256: `a5884bb71d6250dd...`)
  * **Test Split:** 5,115 positions (`janus_nnue_test.jsonl`, SHA-256: `3db745775b8c99c6...`)

---

## 3. Compiler & Hardware Environment

- **Compiler:** Microsoft Visual C++ 19.43.34809 (MSVC 2022 v17.13.5 x64)
- **Compilation Flags:** `/O2 /Ot /Oi /std:c++17 /EHsc`
- **Target Architecture:** x86-64 with AVX2/SSE4.2/POPCNT intrinsics
- **UCI Configuration:** `option name UCI_Variant type combo default R1 var ... var H1 var H2`, `option name UCI_Evaluation type combo default Classical var Classical var NNUE var Hybrid`
