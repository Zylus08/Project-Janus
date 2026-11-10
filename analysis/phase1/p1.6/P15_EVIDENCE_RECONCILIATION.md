# Project Janus — Phase 1, Milestone P1.6
## Forensic P1.5 Evidence Reconciliation & Baseline Verification Audit

**Author:** Principal Computer Chess Engineer, Statistical Experimentalist, Independent Systems Auditor  
**Lineage:** Janus Classical X  
**Incumbent Qualified Production Baseline:** Janus Classical X7 (`b34e342`)  
**Frozen Advanced Research Candidate:** Janus Classical X10 (`1ef060f8...`)  
**Target Candidate Lineage:** Janus Classical X11  
**Branch:** `phase1/classical-janus`  
**Date:** November 2026  
**Charter Constraint:** Strictly Non-ML (Zero neural networks, zero NNUE, zero learned weights, zero offline-fitted models)

---

### 1. Executive Summary & Audit Mandate

Before commencing parallel architecture design or algorithmic modifications for Milestone P1.6, this audit reconciles all empirical results, match telemetry, PGN records, cryptographic hashes, and statistical claims produced in Milestone P1.5.

All checks were executed independently using [`analysis/phase1/p1.6/tests/reconcile_p15_evidence.py`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.6/tests/reconcile_p15_evidence.py).

---

### 2. Independent Head-to-Head Tournament Reconciliations

#### Match 1: Primary Strength Qualification Match (Janus Classical X10 vs Janus Classical X7)
- **Time Control:** Fischer 1.0s base + 50ms increment per move.
- **Corpus & Pairing:** 100 balanced opening pairs (200 games) from `independent_openings_v056.json`. Alternating colors (Game 1: X10 White; Game 2: X7 White) to achieve exact opening balance.
- **Audited Game Score:**
  - Candidate X10 Wins: **75 games (37.50%)**
  - Draws: **65 games (32.50%)**
  - Losses (X7 Wins): **60 games (30.00%)**
  - Total Points for X10: **107.5 / 200 (53.75%)**
- **Statistical Significance & Uncertainty:**
  - Point Estimate Elo: $\Delta\text{Elo} = -400 \log_{10}(1 / 0.5375 - 1) = \mathbf{+26.1\text{ Elo}}$
  - Clustered Opening-Pair 95% Confidence Interval: $\mathbf{[-50.1, +105.0]\text{ Elo}}$
  - Paired $t$-Test against Equal Strength ($\mu = 1.0$):
    $$t = 1.3471, \quad p = \mathbf{0.1779}$$
- **Reliability & Adjudication Audit:**
  - Total PGN Games Parsed: exactly 200.
  - Illegal Move Forfeits: **0**.
  - Clock Timeout Forfeits: **0**.
  - Engine Crashes / Stalls: **0**.

#### Match 2: Slower-Time Comparison Match (Janus Classical X10 vs Janus Classical X7)
- **Time Control:** Fischer 3.0s base + 100ms increment per move.
- **Corpus & Pairing:** 20 balanced opening pairs (40 games).
- **Audited Game Score:**
  - Candidate X10 Wins: **14 games (35.00%)**
  - Draws: **17 games (42.50%)**
  - Losses (X7 Wins): **9 games (22.50%)**
  - Total Points for X10: **22.5 / 40 (56.25%)**
- **Statistical Metrics:**
  - Point Estimate Elo: $\Delta\text{Elo} = \mathbf{+43.7\text{ Elo}}$
  - Clustered Opening-Pair 95% Confidence Interval: $\mathbf{[-132.9, +249.1]\text{ Elo}}$
  - Paired $t$-Test against Equal Strength:
    $$t = 1.0000, \quad p = \mathbf{0.3173}$$
- **Reliability Audit:** Zero illegal moves, zero timeouts, zero forfeits across all 40 games.

#### Combined Janus Internal Evidence Ledger
Across all 240 games played in Milestone P1.5:
$$\text{Score: } 89\text{ Wins} - 82\text{ Draws} - 69\text{ Losses} = \mathbf{130.0 / 240 (54.17\%)}, \quad \Delta\text{Elo} = \mathbf{+29.0\text{ Elo}}, \quad t = 1.6738, \quad p = \mathbf{0.0968}$$

---

### 3. External Stockfish 19 Benchmark Reconciliation

Both engines were audited against official, unrestricted **Stockfish 19** (`sf_19`, commit `edb0d9d`, default NNUE active, 1 thread) across 40 games (20 opening pairs) at 2.0s + 50ms:

| Engine Lineage | Games | W / D / L | Points | Score % | Transformed Elo vs SF19 | Draws Held |
|---|---|---|---|---|---|---|
| **Baseline X7** | 40 | 0 / 2 / 38 | 1.0 / 40 | 2.50% | $-636.4$ | 2 |
| **Candidate X10** | 40 | 0 / 5 / 35 | 2.5 / 40 | 6.25% | $-470.4$ | 5 |

#### Scientific Interpretation of the $+166.0$ Elo Stockfish Transformation
- **Calculation:** $\Delta\text{Elo}_{\text{SF}} = -400 \log_{10}(1 / 0.0625 - 1) - (-400 \log_{10}(1 / 0.025 - 1)) = -470.4 - (-636.4) = \mathbf{+166.0\text{ Elo}}$.
- **Mandatory Scientific Warning:** This $+166.0$ Elo figure is strictly a mathematical transformation of the score differential against Stockfish 19 (holding 5 draws vs 2 draws out of 40 games). It **must NOT** be interpreted as established general playing-strength superiority over Baseline X7. The direct head-to-head match between X10 and X7 established an empirical advantage of $+26.1$ Elo ($p = 0.1779$). Head-to-head competition remains the sole gold standard of engine playing strength.

---

### 4. Forensic Audit of Historical Classical C1 Datasets

A critical discrepancy in historical reports was investigated: earlier summaries occasionally listed Classical C1's benchmark against Stockfish 19 as a 40-game match, whereas original Milestone P1.0 records documented a 20-game result.

#### Forensic Repository Investigation:
1. File: `analysis/phase1/p1.0/benchmark/raw/c1_vs_sf19_historical_reproduced_raw.json`
   - Exact games count: **20 games** (10 opening pairs).
   - Outcome: 0 Wins, 0 Draws, 20 Losses = **0.0 / 20 (0.00%)**.
2. File: `analysis/phase1/p1.0/benchmark/raw/c1_vs_sf19_unrestricted_blitz_raw.json`
   - Exact games count: **6 games** (diagnostic pilot).
   - Outcome: 0.0 / 6 (0.00%).
3. **Formal Verification:** Zero 40-game dataset exists for Classical C1 in the repository. Milestone P1.0 established baseline performance on a 20-game reproduced protocol. Milestones P1.3, P1.4, and P1.5 subsequently standardized on 40-game (20-pair) matches for X7, X8, X9, and X10. All documentation in Milestone P1.6 must explicitly cite C1 as a 20-game sample ($0.0/20$) to prevent silent data conflation.

---

### 5. Throughput, Cache Efficiency & Correctness Verification

1. **Pawn Hash Table & NPS Retention:**
   - Raw Baseline X7 Throughput: **1,502,564 NPS**.
   - Raw Candidate X10 Throughput: **1,463,554 NPS**.
   - Throughput Retention: **97.40%** (exceeding the 95% project threshold).
   - Pawn Hash Correctness across en passant and promotions: **PASSED (stable)**.
2. **Correctness Invariants:**
   - 12/12 Perft depths: Startpos (d1-d4), KiwiPete (d1-d4), Pos3 (d1-d4) bit-exact.
   - Deterministic Fallback Parity: 5/5 test positions verified bit-exact vs frozen `janus_classical_x7.exe`.
   - Tactical Mate & Repetition: Scholar's Mate in 1, Back Rank Mate in 1, Légal's Mate in 2, and Threefold Repetition (0 cp) all passed.

---

### 6. Cryptographic Provenance & Frozen Binary Registry

Every historical and reference binary has been verified against its authoritative SHA-256 hash:

| Binary Alias | Relative Path | Size (Bytes) | SHA-256 Digest |
|---|---|---|---|
| **C1** | `analysis/v0.56/native/janus_native_engine.exe` | 341,504 | `a4f9d9d18b549d2932a392815668e16bf16a57c126ec4f933a36db5db78c9354` |
| **X6** | `analysis/phase1/p1.2/control/janus_classical_x6.exe` | 354,816 | `138b43bc318869677569b91ec3efbb4c7821613bc03d154ee42fa4efaa0a20cb` |
| **X7** | `analysis/phase1/p1.5/control/janus_classical_x7.exe` | 370,176 | `86392a2f4bd4182a4d7dc21e32940bd7939f6816794d5e1ab02f4082431ca28b` |
| **X8** | `analysis/phase1/p1.5/control/janus_classical_x8.exe` | 374,784 | `05cd4dc8c38581fd5ee775dc1cea89011c83e6969828caae17ca6e8136fa9429` |
| **X9** | `analysis/phase1/p1.5/control/janus_classical_x9.exe` | 375,296 | `f61376a20acc04e612589ba98e386cc2780974f9ceb0abf5bee075e78355887d` |
| **X10** | `analysis/phase1/p1.5/control/janus_classical_x10.exe` | 382,464 | `1ef060f89cb156b798cd2fbe67539d088c6c0fb3842006b734f07a03808b0f20` |
| **Stockfish 19** | `tools/stockfish/stockfish.exe` | 103,046,300 | `45bc8e4969147db95f850e04e8d2e8b61c47a3a9cf3e0988647c2fa70617300c` |

---

### 7. Phase 0 Audit Sign-Off

The forensic audit is complete. All P1.5 match results, telemetry files, PGN transcripts, NPS throughput records, correctness proofs, and cryptographic hashes are fully reconciled, bit-exact, and verified.

Development of Milestone P1.6 (Lazy SMP Multithreading & Safe Late Move Pruning) may proceed.

**Sign-off:**  
Principal Computer Chess Engineer & Independent Experimental Auditor.

