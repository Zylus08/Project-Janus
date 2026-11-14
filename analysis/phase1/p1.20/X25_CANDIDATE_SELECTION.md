# Milestone P1.20 Phase 11: Candidate X25 Architecture & Checksum Sealing

## 1. Candidate Specification & Provenance

Janus Classical X25 is the officially designated candidate architecture for Milestone P1.20, developed to address the time-control stability and endgame passivity issues identified in Milestones P1.18–P1.19.

### 1.1 Architectural Lineage
- **Direct Ancestor:** Janus Classical X22 (`e33f292`, P1.17)
- **Experimental Divergence:**
  - **Rejected Candidate X24 (`bcf8f4c`, P1.19):** Introduced static backward-pawn detection ($-10\text{ mg} / -15\text{ eg}$), which caused an empirical collapse to $37.0\%$ ($p = 0.0129$) at slow time controls ($3.0\text{s} + 100\text{ms}$).
  - **Candidate X25 (`project-janus-phase1`, P1.20):** Completely strips backward-pawn penalties, restores search-tree stability, and introduces **Option B: Dynamic Connected & Supported Passed Pawn Architecture**.

### 1.2 Non-ML Governance
In accordance with the non-negotiable Project Janus Charter:
- Strictly non-ML; zero neural networks, zero NNUE inference.
- Zero learned parameters, zero Texel tuning, zero SPSA or automated gradient descent.
- Handcrafted classical chess geometric terms, fully documented and bitwise verifiable.

---

## 2. Frozen Candidate X25 Artifacts & Cryptographic Checksums

All binaries were compiled with **Microsoft (R) C/C++ Optimizing Compiler Version 19.43.34809 for x64** with flags `/O2 /Oi /Ot /std:c++17 /EHsc` and sealed in the `analysis/phase1/p1.20/control/` directory:

| Artifact Name | Relative Path | Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :---: | :--- |
| **Engine Binary** | `analysis/phase1/p1.20/control/janus_classical_x25.exe` | 338,432 | `2C163B4AD5B976C81D5A54992E42C97828E5EDCF14CC4BAC84ABDD543E72E20E` |
| **Shared Library** | `analysis/phase1/p1.20/control/janus_classical_x25.dll` | 275,968 | `23389DA4922E2B496D577D7EB3B8C4AD9B26C4125FFC49FFD9E19DFF1A1BAB4E` |
| **Source Snapshot** | `analysis/phase1/p1.20/control/janus_classical_x25.cpp` | 309,692 | `14FCA2D49EA7F031D40FC520BB26AC351B6928CD36990DD7DAE892D8888A0095` |

---

## 3. Detailed Parameter Matrix

| Parameter / Feature | Baseline X7 (`b34e342`) | Baseline X12 (`78ca3d5`) | Reference X22 (`e33f292`) | Rejected X24 (`bcf8f4c`) | **Candidate X25 (P1.20)** |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Evaluation Mode** | E5 (Legacy) | E10 (Enhanced) | E5 (1T) / E10 (4T) | E5 (1T) / E10 (4T) | **E5 (1T) / E10 (4T)** |
| **Pawn Hash Table** | Disabled | Disabled | **64K Direct-Mapped** | **64K Direct-Mapped** | **64K Direct-Mapped** |
| **Quiescence Search** | Q0 (Legacy) | Q0 (Legacy) | **Q1 (Corrected)** | **Q1 (Corrected)** | **Q1 (Corrected)** |
| **Outpost Bonus** | Legacy E5 | Legacy E5 | **True Outposts** | **True Outposts** | **True Outposts** |
| **Backward Pawns** | 0 (Disabled) | 0 (Disabled) | 0 (Disabled) | 1 (Enabled) | **0 (STRICTLY DISABLED)** |
| **King File Exposure** | 0 (Disabled) | 0 (Disabled) | 0 (Disabled) | 0 (Disabled) | **0 (STRICTLY DISABLED)** |
| **Connected Passers** | Legacy (+15/+25) | Legacy (+15/+25) | Legacy (+15/+25) | Legacy (+15/+25) | **Option B (+20/+35, Adv +30/+55)** |
| **Supported Passers** | Legacy (+10/+20) | Legacy (+15/+25) | Legacy (+10/+20) | Legacy (+10/+20) | **Option B (+15/+25)** |
| **Staged Movegen** | Disabled | Disabled | Enabled | Enabled | **Enabled** |
| **Capture Ordering** | C0 (Legacy) | C0 (Legacy) | C1 (Near-Even) | C1 (Near-Even) | **C1 (Near-Even)** |
| **Continuation History** | H0 (Disabled) | H0 (Disabled) | H3 (Active) | H3 (Active) | **H3 (Active)** |
| **Dynamic LMR** | L0 (Static) | L0 (Static) | L3 (Calibrated) | L3 (Calibrated) | **L3 (Calibrated)** |
| **Singular Extensions** | S0 (Disabled) | S0 (Disabled) | S0 (Disabled) | S0 (Disabled) | **S0 (Disabled)** |
| **Multi-Cut** | C0 (Disabled) | C0 (Disabled) | C0 (Disabled) | C0 (Disabled) | **C0 (Disabled)** |
| **ProbCut** | P0 (Disabled) | P0 (Disabled) | P0 (Disabled) | P0 (Disabled) | **P0 (Disabled)** |

---

## 4. Verification Protocol

Candidate X25 is evaluated across two deployment configurations:
- **Janus Classical X25-S:** Single-threaded configuration (`Threads = 1`), matching Baseline X7 qualification conditions.
- **Janus Classical X25-P:** 4-thread SMP configuration (`Threads = 4`), matching Baseline X12 qualification conditions.

Promotion requires satisfying all qualification gates:
1. Significant gain over Reference X22 at fast TC ($p < 0.05$).
2. Non-regression over Reference X22 at slow TC ($3.0\text{s} + 100\text{ms}$).
3. Competitive parity/superiority against Single-Thread Baseline X7.
4. Competitive parity/superiority against 4-Thread SMP Baseline X12.
5. Absolute non-regression against Baseline X7 at slow TC ($3.0\text{s} + 100\text{ms}$).
