# Phase 0: P1.10 Scientific Evidence Reconciliation & Integrity Audit

**Milestone:** Phase 1, Milestone P1.11  
**Charter:** Classical Search Architecture Decision, Counterfactual Pruning Verification & Competitive Strength Recovery  
**Auditor:** Principal Computer Chess Engineer & Independent Reproducibility Auditor  
**Repository:** `E:\ChessXML\project-janus-phase1`  
**Expected HEAD:** `24c663c`  
**Raw Data Reference:** [`analysis/phase1/p1.11/raw/p110_reconciliation_raw.json`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.11/raw/p110_reconciliation_raw.json)  

---

## 1. Executive Summary & Verification Mandate

Milestone P1.11 begins with a strict forensic re-examination of the experimental evidence, statistical claims, binary identities, and infrastructure classifications reported in Milestone P1.10.

All 540 games from the four P1.10 tournament archives were independently parsed, verified move-by-move, and subjected to paired opening difference re-analysis, Two One-Sided Tests (TOST) for equivalence, compiler-workload verification, and filesystem tablebase audits.

---

## 2. Tournament Reconstruction & Statistical Audit

Every game result reported in Milestone P1.10 was reconstructed bit-for-bit from the source PGN archives:

| Match Identifier | Pairing & Config | TC | Reported Result | Reconstructed Result | Score (%) | Mean Pair Diff ($\bar{d}$) | Std Error ($SE$) | Paired $t$-stat | Two-Tailed $p$-value | TOST Equivalence ($p_{\text{TOST}}$) | Statistical Reality |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Match A** | X15 (1T) vs X7 (1T) | 1.0s + 50ms | 61W / 62D / 77L | 61W / 62D / 77L | 92.0 / 200 (**46.00%**) | $-0.0800$ | $0.0598$ | $-1.3386$ | $0.183766$ | $p = 0.3695$ (Fail) | **Inconclusive** ($H_0$ not rejected; Equivalence unproven) |
| **Match B** | X15 (4T) vs X12 (4T) | 1.0s + 50ms | 58W / 72D / 70L | 58W / 72D / 70L | 94.0 / 200 (**47.00%**) | $-0.0600$ | $0.0543$ | $-1.1059$ | $0.271441$ | $p = 0.2313$ (Fail) | **Inconclusive** ($H_0$ not rejected; Equivalence unproven) |
| **Match C** | X15 (4T) vs X12 (4T) | 3.0s + 100ms | 36W / 21D / 43L | 36W / 21D / 43L | 46.5 / 100 (**46.50%**) | $-0.0700$ | $0.0821$ | $-0.8529$ | $0.397892$ | $p = 0.3582$ (Fail) | **Inconclusive** ($H_0$ not rejected; Equivalence unproven) |
| **Match SF** | X15 (4T) vs SF19 (4T) | 2.0s + 50ms | 0W / 5D / 35L | 0W / 5D / 35L | 2.5 / 40 (**6.25%**) | $-0.8750$ | $0.0615$ | $-14.2264$ | $1.39 \times 10^{-11}$ | $p = 1.0000$ (Fail) | **Significant Deficit** (5 Draws confirmed) |

### 2.1 Critical Statistical Correction: "Parity" vs "Equivalence"
In Milestone P1.10, the phrase "statistical parity" was repeatedly used to describe results where $p > 0.05$.
- **Scientific Correction:** In formal hypothesis testing, failure to reject the null hypothesis ($H_0: \mu_d = 0$) **does not prove that two engines are of equal strength**.
- Under Two One-Sided Tests (TOST) with an equivalence bound of $\pm 5\%$ score ($\pm 0.10$ pair difference, corresponding to $\approx \pm 35$ Elo), all three internal matches fail to establish equivalence ($p_{\text{TOST}} = 0.37, 0.23, 0.36 > 0.05$).
- **Rigorous Verdict:** Candidate X15 failed to demonstrate superiority ($p < 0.05$) over X7 and X12, and the sample size ($N=100$ and $N=50$ pairs) is underpowered to establish formal equivalence. Candidate X15 is strictly **inconclusive and non-superior**, justifying the strict retention of X7 and X12 as baselines.

### 2.2 Indirect Comparison Clarification: X15 vs X14
- In P1.10, it was reported that X15 gained $+40.7$ Elo over X14 ($46.00\%$ vs $40.25\%$).
- **Experimental Clarification:** This comparison was **not a direct head-to-head match** between X15 and X14. It is an indirect comparison of two separate experiments against the common opponent Janus Classical X7:
  - P1.9 Match A: X14 vs X7 scored $40.25\%$ ($N=200$, $p = 0.0014$).
  - P1.10 Match A: X15 vs X7 scored $46.00\%$ ($N=200$, $p = 0.1838$).
- While this indicates that the severe regression suffered by X14 was resolved in X15, it does not constitute a direct paired measurement of X15 against X14.

---

## 3. Workload, Throughput & Compiler Parity Audit

The throughput improvements reported in P1.10 (750K NPS on 1T, 1.73M NPS on 4T) were audited for methodological rigor:
1. **Compiler Parity:** Both `janus_classical_x12.exe` and `janus_classical_x15.exe` were built using identical MSVC 2022 toolchain flags (`/O2 /Ot /Oi /std:c++17 /EHsc`) on the same host architecture.
2. **Workload Parity:** Throughput benchmarking used an identical 12-position diagnostic suite at fixed 800ms budgets under identical thread allocations (`Threads=1` and `Threads=4`).
3. **Hardware Alignment:** Measurements ran on the host Intel Core i9-13900HX processor (24 logical cores, 2048 KB L2 cache per core slice).
4. **Conclusion:** The $+17.16\%$ throughput improvement of Candidate P over X12 is a legitimate algorithmic speedup arising from thread-local 16K pawn hashing (512 KB, 25% L2 cache) and branchless evaluation logic, rather than a benchmarking artifact.

---

## 4. Cryptographic Binary Audit & Lineage Registry

The binary identities and SHA-256 checksums of all control executables were re-verified:

| Engine Name | File Path | File Size (Bytes) | SHA-256 Checksum | Lineage Status |
| :--- | :--- | :---: | :--- | :--- |
| `janus_classical_x7.exe` | `analysis/phase1/p1.3/control/janus_classical_x7.exe` | 370,176 | `86392a2f4bd4182a4d7dc21e32940bd7939f6816794d5e1ab02f4082431ca28b` | **QUALIFIED 1T BASELINE** |
| `janus_classical_x12.exe` | `analysis/phase1/p1.7/control/janus_classical_x12.exe` | 2,874,368 | `00b4f5fedea02a392a1af9713a96512e5199a0e3ae55c295ad1c7cfff1b47059` | **QUALIFIED 4T BASELINE** |
| `janus_classical_x14.exe` | `analysis/phase1/p1.9/control/janus_classical_x14.exe` | 1,304,576 | `c85374a96de4d26f774421526f1e5126bd89487b08787b5b78780ca27d6e116f` | Frozen Platform (P1.9) |
| `janus_classical_x15.exe` | `analysis/phase1/p1.10/control/janus_classical_x15.exe` | 1,596,416 | `5b3cfcfe85b81ca03acd85f65196fb6599d29a100f272d2c1fbd66af26374e28` | Advanced Research Reference |
| `stockfish.exe` (`sf_19`) | `E:/ChessXML/tools/stockfish/stockfish.exe` | 103,046,300 | `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0` | External Official Benchmark |

All checksums match bit-for-bit with prior milestone manifests.

---

## 5. Tablebase Subsystem Status: Formal Reclassification

A thorough recursive scan of all local workspace drives (`E:\ChessXML`, `E:\ChessXML\project-janus-phase1`) confirmed:
- **Total `.rtbw` files found:** 0
- **Total `.rtbz` files found:** 0
- **Classification Verdict:** The Syzygy tablebase code in Janus is **Adapter and Fallback Verified Only**.
- It must **NEVER** be described as an active endgame oracle or playing-strength contributor until actual tablebase files (e.g. 3-4-5 piece Syzygy files) are ingested and qualified through live probing.

---

## 6. Audit Conclusion & Phase 1 Authorization

The scientific integrity audit of Milestone P1.10 is complete:
1. Reconstructed tournament scores are 100% accurate.
2. Unsupported "equivalence" claims have been formally corrected to "inconclusive / non-superior".
3. Throughput gains of Candidate X15 are confirmed genuine.
4. Baseline governance holds: **Janus Classical X7 (1T)** and **Janus Classical X12 (4T)** are the sole qualified baselines.
5. Milestone P1.11 is authorized to proceed to Phase 1 (Classical Search Architecture Reconstruction).

