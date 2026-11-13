# Milestone P1.11 Scientific Reconciliation and Integrity Audit

## 1. Executive Summary & Audit Scope

As mandated by Milestone P1.12, an independent, rigorous audit of the Milestone P1.11 experimental dataset was conducted. This audit includes:
1. Verification of Git ancestry, working-tree state, and cryptographic SHA-256 hashes of all control and candidate binaries.
2. Full parsing and independent mathematical reconstruction of all games directly from the five archived raw PGN files (`analysis/phase1/p1.11/pgn/`).
3. Forensic audit of the total game count discrepancy ("540" reported in summary prose vs 580 actual games).
4. Critical audit of the comparative Stockfish resilience claims between X15 (P1.10) and X16 (P1.11).
5. Recalculation of all pentanomial counts, paired Student's $t$-statistics, and Two One-Sided Tests (TOST) equivalence metrics.

---

## 2. Git Ancestry, Working Tree & Executable Hashes

### 2.1 Git Repository Ancestry
- **Repository:** `E:\ChessXML\project-janus-phase1`
- **Current Branch:** `phase1/classical-janus`
- **Expected Parent HEAD:** `50c06e6` (with docs sync `34324f5`)
- **Working Tree State:** Completely clean, zero uncommitted or unstaged modifications.

### 2.2 Cryptographic Hash Manifest

| Engine Identifier | Architecture / Role | Binary Path | Size (Bytes) | Cryptographic SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- |
| **Janus Classical X7** | Qualified 1T Baseline | `analysis/phase1/p1.3/control/janus_classical_x7.exe` | 370,176 | `86392a2f4bd4182a4d7dc21e32940bd7939f6816794d5e1ab02f4082431ca28b` |
| **Janus Classical X12** | Qualified 4T Baseline | `analysis/phase1/p1.7/control/janus_classical_x12.exe` | 2,874,368 | `00b4f5fedea02a392a1af9713a96512e5199a0e3ae55c295ad1c7cfff1b47059` |
| **Janus Classical X15** | Frozen Platform Ref | `analysis/phase1/p1.10/control/janus_classical_x15.exe` | 1,596,416 | `5b3cfcfe85b81ca03acd85f65196fb6599d29a100f272d2c1fbd66af26374e28` |
| **Janus Classical X16** | Archived Candidate | `analysis/phase1/p1.11/control/janus_classical_x16.exe` | 1,598,464 | `97e69fa99c708400c33e95b2bb32e3db79d8467970e1a895927a459f34061ab9` |
| **Stockfish 19** | External Benchmark | `tools/stockfish/stockfish.exe` | 103,046,300 | `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0` |
| **Stockfish 11** | Historical Reference | `tools/stockfish_11/stockfish_11.exe` | 687,616 | `b004c03bd71bb84e8bc1832c580e72a7e883f121e1834ea6da2802d1575e8048` |

---

## 3. Audit of the Total Game Count Discrepancy (540 vs 580)

### 3.1 Empirical Verification
Direct parsing of all five archived PGN files in `analysis/phase1/p1.11/pgn/` confirms the following exact game inventory:
- `x16_1t_vs_x7_1t.pgn`: **200 games** (100 opening pairs)
- `x16_4t_vs_x12_4t.pgn`: **200 games** (100 opening pairs)
- `x16_4t_vs_x12_4t_slow.pgn`: **100 games** (50 opening pairs)
- `x16_1t_vs_sf19_1t.pgn`: **40 games** (20 opening pairs)
- `x16_4t_vs_sf19_4t.pgn`: **40 games** (20 opening pairs)
- **Total Games Across PGN Archives:** **580 games**.

### 3.2 Root Cause Analysis of the Discrepancy
In Milestone P1.10, the tournament program comprised four matches totaling exactly **540 games** (Match A: 200, Match B: 200, Match C: 100, Match SF: 40). In Milestone P1.11, the experimental design was expanded by splitting the external Stockfish benchmark into two separate thread-count tracks: Match SF-1T (40 games) and Match SF-4T (40 games), bringing the true tournament total to $200 + 200 + 100 + 40 + 40 = 580\text{ games}$.

During documentation assembly for Milestone P1.11, a clerical error occurred where summary text inadvertently cited the P1.10 total of "540 tournament games" in two introductory paragraphs instead of 580. 
**Audit Finding:** Zero games were omitted, dropped, or corrupted. The entire 580-game corpus is completely preserved, valid, and accounted for in the raw PGN files and JSON telemetry.

---

## 4. Forensic Audit of Stockfish Resilience Claims (X15 vs X16)

### 4.1 Comparative Data Under Matched Conditions
In Milestone P1.11's report (`MATCHED_STOCKFISH19_PROGRESS.md`), Section 4 and Section 5 contained a claim that Candidate X16 demonstrated "improved tactical resilience over X15". A forensic audit against the original P1.10 experimental data (`analysis/phase1/p1.10/raw/x15_vs_sf19_raw.json` and `x15_4t_vs_sf19_4t.pgn`) refutes this claim:

| Candidate Platform | Opponent Configuration | Games (Pairs) | Score (Pct) | Draws Held | Elo Delta [95% CI] | Paired $t$-stat ($p$-value) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Janus Classical X15** (P1.10) | Stockfish 19 (4T vs 4T) | 40 (20) | 2.5 / 40 (**6.25%**) | **5 / 40 (12.5%)** | **-470.4** [-679.9, -261.0] | $t = -14.226$ ($p = 1.39 \times 10^{-11}$) |
| **Janus Classical X16-P** (P1.11) | Stockfish 19 (4T vs 4T) | 40 (20) | 0.5 / 40 (**1.25%**) | **1 / 40 (2.5%)** | **-759.1** [-1153.3, -364.8]| $t = -39.000$ ($p = 1.34 \times 10^{-19}$) |
| **Janus Classical X16-S** (P1.11) | Stockfish 19 (1T vs 1T) | 40 (20) | 1.0 / 40 (**2.50%**) | **2 / 40 (5.0%)** | **-636.4** [-940.8, -332.1] | $t = -27.606$ ($p = 8.49 \times 10^{-17}$) |

### 4.2 Forensic Audit Conclusion
In P1.11's documentation, an erroneous historical summary row incorrectly listed P1.10's score as 0.0% (0 draws), leading to the false conclusion that X16's 3 cumulative draws across two matches represented improved resilience. Under matched 4T conditions, **Candidate X16 actually regressed from 5 draws down to 1 draw, and its score dropped from 6.25% to 1.25%**. 

**Auditor Mandate:** Comparative strength claims between engine candidates must only be made under strictly matched experimental conditions. Candidate X16 demonstrated no external resilience advantage over X15.

---

## 5. Mathematical & Statistical Re-Verification

Every game, pair outcome, pentanomial distribution, and statistical test was independently recomputed from raw PGN records using `analysis/phase1/p1.12/tests/audit_p111_reconciliation.py`:

```
========================================================================================================================
Independent Reconstructed Tournament Statistics (JCTS v1.11 Standard)
========================================================================================================================
Match ID     Contestants        TC & Cores    Games  Score (Pct)       Elo Delta [95% CI]    Pentanomial (2..0)   Paired t   p-value    TOST p
------------------------------------------------------------------------------------------------------------------------
Match A      X16-S vs X7        1.0s+50ms 1T  200    67.5/200 (33.75%) -117.2 [-167.9, -66.4] [4, 13, 24, 32, 27]  -5.7446    1.02e-07   0.9999
Match B      X16-P vs X12       1.0s+50ms 4T  200    91.0/200 (45.50%)  -31.4 [ -79.5, +16.8] [6, 24, 31, 24, 15]  -1.5783    1.18e-01   0.4342
Match C      X16-P vs X12 (Slow)3.0s+100ms 4T 100    45.5/100 (45.50%)  -31.4 [ -99.3, +36.6] [3,  4, 30,  7,  6]  -1.3226    1.92e-01   0.4432
Match SF-1T  X16-S vs SF19      2.0s+50ms 1T   40     1.0/40  ( 2.50%) -636.4 [-940.8, -332.1] [0,  0,  0,  2, 18] -27.6064    8.49e-17   1.0000
Match SF-4T  X16-P vs SF19      2.0s+50ms 4T   40     0.5/40  ( 1.25%) -759.1 [-1153.3, -364.8] [0,  0,  0,  1, 19] -39.0000    1.34e-19   1.0000
========================================================================================================================
```

---

## 6. Interpretation of Statistical Tests: The Duality of Parity and Inferiority

Milestone P1.12 formalizes the statistical interpretation rules governing all future project evaluations:
1. **The Superiority Null Hypothesis ($H_0: \mu_d \le 0$):**
   A two-tailed $p$-value $p \ge 0.05$ indicates that the observed score difference is not statistically distinguishable from random chance. **A failed superiority test does NOT prove equivalence or "parity"**; it merely proves that superiority has not been established.
2. **The Equivalence Null Hypothesis ($H_{01}: \mu_d \le -\Delta_{\text{eq}}$ or $H_{02}: \mu_d \ge +\Delta_{\text{eq}}$):**
   Under Two One-Sided Tests (TOST) with equivalence margin $\Delta_{\text{eq}} = 0.10$ ($\pm 35$ Elo), statistical equivalence is only established when $p_{\text{TOST}} < 0.05$. If $p_{\text{TOST}} \ge 0.05$, **equivalence is formally unproven**.
3. **The Non-Inferiority Principle:**
   A failed equivalence test ($p_{\text{TOST}} \ge 0.05$) does not automatically prove that an engine is inferior, unless the lower bound of the confidence interval excludes the equivalence region or $p_{\text{sup}} < 0.05$ with negative mean difference. In Match B and Match C, X16 is **inconclusive with a negative tilt** (the sample size is insufficient to prove equivalence within $\pm 35$ Elo, while the point estimate reflects a -31.4 Elo deficit). In Match A, X16 is **definitively and significantly inferior** ($p = 1.02 \times 10^{-7}$).

