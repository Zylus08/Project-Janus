# Candidate Selection & Architecture Freeze: Janus Classical X21 (P1.16 Phase 10)

## Executive Summary

Following the completion of Phases 4 through 9 of Milestone P1.16, the engineering evidence decisively justifies the creation, freezing, and formal competitive evaluation of **Janus Classical X21**.

Unlike speculative or regression-prone predecessors, Janus Classical X21 directly repairs the root cause of historical classical tactical failures—the quiescence search in-check blindness defect—while integrating high-speed thread-local pawn hash caching, stage-reformed move generation, and near-even capture ordering.

---

## 1. Candidate Justification Matrix

| Phase & Dimension | Engineering Intervention | Measured Empirical Verification | Gate Status |
| :--- | :--- | :--- | :---: |
| **Phase 4 (Quiescence Repairs)** | Q1 Architecture: in-check evasions, stand-pat suppression under check, mate/stalemate resolution. | 100.0% pass rate (40/40) on verification suite. Terminal checkmate recognition at leaf nodes. | **PASSED** |
| **Phase 5 (Selective Checks)** | Controlled evaluation of Q0, Q1, Q2, Q3 checking policies across 30 tactical positions. | Q1 selected. Quiet checks (Q2/Q3) breached gating criteria with zero accuracy gain and $-27.8\%$ NPS drop. | **PASSED** |
| **Phase 6 (Evaluation Repairs)** | 64K-entry Thread-Local Pawn Hash Table integration on single-thread E5 evaluation. | $+52.1\%$ search throughput gain (1.92M vs 1.26M NPS). 100% color symmetry preserved. | **PASSED** |
| **Phase 7 (Factorial Ablation)** | Factorial matrix (B0–B7) isolating Q-mode, eval mode, and thread interactions. | Candidate X21-S (B4) and X21-P (B6) achieve deepest search trees, 100% mate rate, and top tactical solve rates. | **PASSED** |
| **Phase 8 (Search Economics)** | Latency profiling and Game 12 forensic reconciliation. | Demonstrated that the P1.15 $18.7\times$ node reduction was an artifact of mate blindness, resolved by Q1. | **PASSED** |
| **Phase 9 (Systems Correctness)** | Full Perft, movegen, UCI compliance, determinism, and SMP thread-safety testing. | 100.0% match on Perft (Startpos D1–D4, KiwiPete D1–D3), 100% bitwise single-thread determinism. | **PASSED** |

---

## 2. Dual-Track Candidate Architecture Specifications

### Track S: Janus Classical X21-S (Single-Thread Promotion Benchmark)
- **Target Baseline:** Qualified 1-Thread Baseline Janus Classical X7 (`b34e342`).
- **Core Search Parameters:**
  - `Threads = 1`
  - `UCI_Variant = X21`
  - `UCI_QuiescenceMode = Q1` (Corrected Quiescence Search)
  - `UCI_AdaptiveCapture = C1` (Near-Even Capture Promotion)
  - `UCI_StagedMovegen = true` (Stage-Reformed MovePicker)
  - `UCI_ClassicalEval = E5` (Combined Classical Positional Evaluation)
  - `UCI_PawnHash = true` (64K-Entry Thread-Local Pawn Hash Table)
  - `UCI_ContinuationHistory = H3` (In-Search History Gravity)
  - `UCI_DynamicLMR = L3` (Calibrated Depth/Move Reductions)

### Track P: Janus Classical X21-P (Multi-Thread Promotion Benchmark)
- **Target Baseline:** Qualified 4-Thread Baseline Janus Classical X12 (`78ca3d5`).
- **Core Search Parameters:**
  - `Threads = 4`
  - `UCI_Variant = X21`
  - `UCI_QuiescenceMode = Q1` (Corrected Quiescence Search)
  - `UCI_AdaptiveCapture = C1` (Near-Even Capture Promotion)
  - `UCI_StagedMovegen = true` (Stage-Reformed MovePicker)
  - `UCI_ClassicalEval = E10` (Full Enhanced Classical Positional Evaluation)
  - `UCI_PawnHash = true` (64K-Entry Direct-Mapped Pawn Hash Table)
  - `UCI_LMP = L1` (Safe Late Move Pruning)
  - `UCI_DynamicTime = true` (Dynamic Move-Time Allocation)

---

## 3. Cryptographic Freeze Manifest

All frozen developmental candidate artifacts have been deployed to the authoritative control directory `analysis/phase1/p1.16/control/` and cryptographically locked:

| Artifact Name | Relative Repository Path | File Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :---: | :--- |
| **X21 Engine Executable** | `analysis/phase1/p1.16/control/janus_classical_x21.exe` | 1,610,240 | `AD1E1F0598D0CA016267CA4F03DC771346CEE9D0D563A36AB6B6590D7F4731FD` |
| **X21 Engine Dynamic Library** | `analysis/phase1/p1.16/control/janus_classical_x21.dll` | 1,513,472 | `B8A930BC9302788E06533B7A04B318E0AEB7E64A04BD7C0F52564F77EB253A60` |
| **X21 Source Implementation** | `analysis/phase1/p1.16/control/janus_classical_x21.cpp` | 240,157 | `AF67D06809A0E4FF3BBA4E55C1C8CF6B0B9BCA5A9BEB06AAED70C57A1806B2D2` |

---

## 4. Frozen Immutable Opponent & Baseline Manifest

| Opponent Role | Target Version & Commit | Executable Path | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| **Qualified 1T Baseline** | Janus Classical X7 (`b34e342`) | `analysis/phase1/p1.3/control/janus_classical_x7.exe` | `86392A2FE44C09B167664B29DA928D1FE25CE0E0B19BD8CE4751433F62D38B28` |
| **Qualified 4T Baseline** | Janus Classical X12 (`78ca3d5`) | `analysis/phase1/p1.7/control/janus_classical_x12.exe` | `00B4F5FE9CE137E749845B0A80509E2B2B498C0B29E3065DE78CCFE573F4B52F` |
| **Leading Reference** | Janus Classical X19 (`bcfdecd`) | `analysis/phase1/p1.14/control/janus_classical_x19.exe` | `CBB7785A47E5F9EC64C51C20B8387DE3EFE782F42BDFCEA38008F6450E534629` |
| **Archived Reference** | Janus Classical X20 (`563f1db`) | `analysis/phase1/p1.15/control/janus_classical_x20.exe` | `AF126A4D0F838561C1F2B5277322F2669BC4375A7A0A9C1286C3EDFF6BD5F5B3` |
| **Historical Classical 1** | Stockfish 4 (Official) | `E:/ChessXML/tools/stockfish_4/stockfish_4.exe` | Verified Release Binary |
| **Historical Classical 2** | Stockfish 11 (Official) | `E:/ChessXML/tools/stockfish_11/stockfish_11.exe` | Verified Release Binary |
| **Modern Non-Classical** | Stockfish 19 (`edb0d9d`) | `E:/ChessXML/tools/stockfish/stockfish.exe` | Unrestricted NNUE Release |
