# PROJECT JANUS — PHASE 1, MILESTONE P1.9
## Phase 0: P1.8 Evidence Reconciliation & Promotion Correction Audit

### 1. Executive Summary & Audit Mandate

In accordance with Milestone P1.9 governing instructions, Phase 0 conducts an independent scientific, statistical, and architectural audit of the experimental findings, statistical claims, and baseline promotions reported during Milestone P1.8.

All tournament raw PGNs and telemetry JSON files from Milestone P1.8 were independently parsed from disk, recomputed from primary game records, and checked against statistical standards.

---

### 2. Primary Match Reconciliation

The table below reconciles the reported P1.8 results against independent ground-truth recalculations from raw PGN files:

| Match Identifier | Contenders | Time Control | Sample Size | Score (Pts / Total) | Win % | Elo Delta | 95% Wilson Score Interval | Paired $t$-stat ($df$) | Two-Tailed $p$-value | Significant ($p < 0.05$)? |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Match A** | X13 (1T) vs. X7 (1T) | 1.0s + 0.05s | 200 games (100 pairs) | 59W – 67D – 74L (92.5) | 46.25% | -26.1 | [0.3948, 0.5317] | $t = -1.2405$ ($99$) | $p = 0.21772$ | **False** |
| **Match B** | X13 (4T) vs. X12 (4T) | 1.0s + 0.05s | 200 games (100 pairs) | 67W – 78D – 55L (106.0) | 53.00% | +20.9 | [0.4609, 0.5980] | $t = +1.2410$ ($99$) | $p = 0.21752$ | **False** |
| **Match C** | X13 (4T) vs. X12 (4T) [Slow] | 3.0s + 0.10s | 40 games (20 pairs) | 13W – 7D – 20L (16.5) | 41.25% | -61.4 | [0.2742, 0.5661] | $t = -1.1285$ ($19$) | $p = 0.27314$ | **False** |
| **Match SF** | X13 (4T) vs. SF19 (4T) | 2.0s + 0.05s | 40 games (20 pairs) | 0W – 2D – 38L (1.0) | 2.50% | -636.4 | [0.0044, 0.1288] | $t = -27.6064$ ($19$) | $p < 10^{-6}$ | **True** |

All primary game outcomes and score aggregates in the raw PGN archives are 100% verified and reproducible.

---

### 3. Mandatory Methodological & Evidence Corrections

#### Correction 1: Non-Significance of Match B and Overreached Promotion
- **Finding in P1.8**: Candidate X13 was promoted to official multithreaded baseline status on the basis of scoring 106.0 / 200 (53.00%) with a +12 decisive game margin over X12.
- **Audit Correction**: The paired two-tailed Student's t-test yields $t = +1.2410$ ($df = 99$), $p = 0.21752$. Because $p > 0.05$, the experiment **fails to reject the null hypothesis ($H_0: \Delta = 0$)**. The observed 53.0% score is statistically non-significant and cannot justify production baseline promotion under Project Janus qualification criteria. The promotion of X13 was premature and unsupported.

#### Correction 2: Non-Significance Does Not Prove Equivalence (Match A)
- **Finding in P1.8**: Match A was interpreted as confirming "single-thread parity" between X13 and X7.
- **Audit Correction**: In Match A, X13 scored 92.5 / 200 (46.25%, -26.1 Elo) with $t = -1.2405$, $p = 0.21772$. In classical statistical hypothesis testing, $p > 0.05$ represents failure to reject $H_0$; it does **not** prove that X13 and X7 are equivalent. The point estimate indicates a 26-Elo deficit in single-thread performance, likely stemming from E10 evaluation overhead.

#### Correction 3: Opposite Directions Between Blitz and Slower Time Controls
- **Finding in P1.8**: Match B (1.0s+50ms) yielded 53.00% (+20.9 Elo), whereas Match C (3.0s+100ms) yielded 41.25% (-61.4 Elo).
- **Audit Correction**: The two time controls point in opposing directions. Rather than treating Match C as a minor high-variance artifact, this reversal represents an urgent architectural question: Why does X13 lose ground to X12 as search time expands? This requires systematic investigation across a fine-grained time-budget spectrum (100ms to 5000ms) in Phase 7.

#### Correction 4: Rescission of the "First Stockfish Points" Claim
- **Finding in P1.8**: P1.8 claimed that X13 delivered "the project's first scoring breakthrough against unrestricted Stockfish 19".
- **Audit Correction**: Direct inspection of historical game archives reveals that in Milestone P1.4 (`analysis/phase1/p1.4/pgn/matched_stockfish19_progress.pgn`), Janus Classical scored **3 draws** against Stockfish 19, and in Milestone P1.5 (`analysis/phase1/p1.5/pgn/matched_stockfish19_progress.pgn`), Janus Classical X10 scored **7 draws** against Stockfish 19. The claim that X13 was the first engine to take points off Stockfish 19 is factually incorrect and is hereby formally retracted.

#### Correction 5: Taxonomy Generalization Limitations
- **Finding in P1.8**: P1.8 asserted that 83.3% of all chess failures were caused by static evaluation (58.3%) and endgame horizon (25.0%), derived from a 24-position corpus.
- **Audit Correction**: A 24-position suite is too small to generalize across the entire combinatorial space of engine play against Stockfish. Milestone P1.9 must construct a comprehensive 200–300 position atlas across diverse strategic themes to establish defensible failure attributions.

#### Correction 6: False Precision in Stockfish Elo Point Estimates
- **Finding in P1.8**: Match SF was summarized with a point estimate of -636.4 Elo.
- **Audit Correction**: With only 1 point scored across 40 games (0W–2D–38L, 2.50%), stating a finite point estimate (-636.4 Elo) conveys unwarranted precision. The proper statistical representation is the 95% Wilson score interval `[0.0044, 0.1288]`, which reflects substantial uncertainty spanning from -940.8 Elo to -332.1 Elo.

---

### 4. Baseline Lineage Correction Ledger

To preserve experimental integrity without rewriting historical Git commits, the promotion registry is officially updated as follows:

```
+-------------------------------------------------------------------------------------------------------+
|                                    PROJECT JANUS LINEAGE REGISTRY                                     |
+-------------------------------------------------------------------------------------------------------+
|  Platform                       | Commit    | Formal Status                                           |
+---------------------------------+-----------+---------------------------------------------------------+
|  Janus Classical X7             | b34e342   | QUALIFIED PRODUCTION BASELINE (Single-Thread)           |
|  Janus Classical X12            | 78ca3d5   | QUALIFIED PRODUCTION BASELINE (Multithreaded / 4-Thread)|
|  Janus Classical X10            | 504022f   | Frozen Research Reference (Handcrafted Positional Eval) |
|  Janus Classical X13            | 3afcf6f   | FROZEN EXPERIMENTAL EVALUATION PLATFORM (Promotion Revoked)
+-------------------------------------------------------------------------------------------------------+
```

1. **Janus Classical X7 (`b34e342`)** is retained as the qualified single-thread production baseline.
2. **Janus Classical X12 (`78ca3d5`)** is restored as the qualified multithreaded production baseline.
3. **Janus Classical X13 (`3afcf6f`)** is reclassified as a frozen experimental research platform. Its promotion is revoked pending conclusive, statistically significant evidence.

---

### 5. Frozen Binary Verification

All control executables have been verified bit-for-bit:

| Binary ID | Path | File Size (Bytes) | SHA-256 Cryptographic Hash | Verification |
| :--- | :--- | :---: | :--- | :---: |
| **X7** | `analysis/phase1/p1.3/control/janus_classical_x7.exe` | 370,176 | `86392a2f4bd4182a4d7dc21e32940bd7939f6816794d5e1ab02f4082431ca28b` | Bit-Exact Verified |
| **X10** | `analysis/phase1/p1.5/control/janus_classical_x10.exe` | 382,464 | `1ef060f89cb156b798cd2fbe67539d088c6c0fb3842006b734f07a03808b0f20` | Bit-Exact Verified |
| **X11** | `analysis/phase1/p1.6/control/janus_classical_x11.exe` | 3,162,112 | `5733fdaa4c6b95a772c6e065ae961af00fb00af43e20b9c9d2367bd33bee074f` | Bit-Exact Verified |
| **X12** | `analysis/phase1/p1.7/control/janus_classical_x12.exe` | 2,874,368 | `00b4f5fedea02a392a1af9713a96512e5199a0e3ae55c295ad1c7cfff1b47059` | Bit-Exact Verified |
| **X13** | `analysis/phase1/p1.8/control/janus_classical_x13.exe` | 1,303,040 | `a980cc08cd7cc99ae54a75c21f38dc9d65e568107a7fb79a31dd49fbe2533a29` | Bit-Exact Verified |
| **SF19** | `tools/stockfish/stockfish.exe` | 103,046,300 | `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0` | Bit-Exact Verified |

Phase 0 audit is complete and staged. Proceeding to Phase 1.

