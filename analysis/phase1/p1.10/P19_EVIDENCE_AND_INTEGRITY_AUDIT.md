# Phase 0: P1.9 Scientific Evidence and Integrity Audit

**Milestone:** Phase 1, Milestone P1.10  
**Charter:** Classical Strength Regression Forensics & Independent Reproducibility Audit  
**Auditor:** Principal Computer Chess Engineer & Independent Statistical Auditor  
**Raw Audit Summary:** [`analysis/phase1/p1.10/raw/p19_audit_summary.json`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.10/raw/p19_audit_summary.json)  
**Verification Script:** [`analysis/phase1/p1.10/tests/reconcile_p19_evidence.py`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.10/tests/reconcile_p19_evidence.py)

---

## 1. Executive Summary & Audit Mandate

In accordance with the governing charter of Milestone P1.10, an independent verification and reproducibility audit was conducted on all historical tournament records, game files, and systems claims produced during Milestone P1.9. 

The audit team:
1. Re-parsed all 540 tournament games directly from raw PGN files.
2. Verified the SHA-256 cryptographic hashes and byte sizes of all executable binaries.
3. Re-calculated paired opening differences, exact Student's t-distributions, and binomial probabilities.
4. Audited the mathematical artifact that generated a misleading $p = 0.931724$ report for the 0/40 Stockfish benchmark.
5. Scanned the local filesystem and determined that zero `.rtbw` or `.rtbz` tablebase files exist, requiring formal reclassification of P1.9 tablebase claims.

---

## 2. Cryptographic Binary & Execution Environment Verification

| Binary ID | Lineage Role | File Path | Byte Size | SHA-256 Checksum | Audit Status |
| :--- | :--- | :--- | :---: | :--- | :---: |
| **X7** | Qualified 1T Baseline | `analysis/phase1/p1.3/control/janus_classical_x7.exe` | 370,176 | `86392a2f4bd4182a4d7dc21e32940bd7939f6816794d5e1ab02f4082431ca28b` | **VERIFIED** |
| **X10** | Handcrafted Eval Ref | `analysis/phase1/p1.5/control/janus_classical_x10.exe` | 382,464 | `1ef060f89cb156b798cd2fbe67539d088c6c0fb3842006b734f07a03808b0f20` | **VERIFIED** |
| **X12** | Qualified 4T Baseline | `analysis/phase1/p1.7/control/janus_classical_x12.exe` | 2,874,368 | `00b4f5fedea02a392a1af9713a96512e5199a0e3ae55c295ad1c7cfff1b47059` | **VERIFIED** |
| **X13** | Frozen Research Platform | `analysis/phase1/p1.8/control/janus_classical_x13.exe` | 1,303,040 | `a980cc08cd7cc99ae54a75c21f38dc9d65e568107a7fb79a31dd49fbe2533a29` | **VERIFIED** |
| **X14** | Evaluated Research Platform | `analysis/phase1/p1.9/control/janus_classical_x14.exe` | 1,304,576 | `c85374a96de4d26f774421526f1e5126bd89487b08787b5b78780ca27d6e116f` | **VERIFIED** |
| **SF19** | External Benchmark | `E:/ChessXML/tools/stockfish/stockfish.exe` | 103,046,300 | `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0` | **VERIFIED** |

All binaries are present, bit-exact, and match their preregistered hashes.

---

## 3. Independent Game-Level Tournament Reconciliation

All 540 tournament games were re-parsed move-by-move from the original PGN archives:

| Match ID | Pairing | Time Control | Games | Openings | Recomputed Score (W - D - L) | Score (%) | Paired Diff Mean ($\bar{d}$) | Paired Variance ($s_d^2$) | Paired $t$-stat | Degrees of Freedom | Recomputed Two-Tailed $p$-value |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Match A** | X14 1T vs X7 1T | 1.0s + 50ms | 200 | 100 pairs | 49W – 63D – 88L | **40.25%** | $-0.1950$ | $0.353005$ | **$-3.2820$** | 99 | **$0.001424$** |
| **Match B** | X14 4T vs X12 4T | 1.0s + 50ms | 200 | 100 pairs | 61W – 73D – 66L | **48.75%** | $-0.0250$ | $0.304924$ | **$-0.4527$** | 99 | **$0.651807$** |
| **Match C** | X14 4T vs X12 4T | 3.0s + 100ms | 100 | 50 pairs | 42W – 17D – 41L | **50.50%** | $+0.0100$ | $0.280510$ | **$+0.1335$** | 49 | **$0.898126$** |
| **Match SF**| X14 4T vs SF19 4T | 2.0s + 50ms | 40 | 20 pairs | 0W – 0D – 40L | **0.00%** | $-1.0000$ | **$0.000000$** | **$0.0000$** | 19 | **$0.931724$** *(Artifact)* |

---

## 4. Mandatory Corrections Ledger

The following corrections are formally established for the Project Janus archives:

### Correction 1: Single-Thread Result is a Confirmed Strength Regression
- **Raw Finding:** In Match A, Candidate X14 scored $40.25\%$ ($-68.6\text{ Elo}$) against Janus Classical X7.
- **Statistical Fact:** $t = -3.282$, $df = 99$, $p = 0.001424 < 0.01$. The null hypothesis of equal strength is rejected with $99.85\%$ confidence.
- **Correction:** This result is formally classified as a **detected, statistically confirmed single-thread regression**. Adding the Refined E11 handcrafted evaluation to the search pipeline severely degrades playing strength when running on a single core.

### Correction 2: Four-Thread Results are Inconclusive, Not Proof of Equivalence
- **Raw Finding:** In Match B, Candidate X14 scored $48.75\%$ ($p = 0.652$) against X12. In Match C, X14 scored $50.50\%$ ($p = 0.898$) against X12.
- **Methodological Correction:** In statistical inference, **failing to reject $H_0$ ($p > 0.05$) does not prove the null hypothesis ($H_0: \Delta\text{Elo} = 0$)**. A $p$-value of $0.652$ indicates that the match was insufficiently powered or the effect size was too small to detect. It is scientifically invalid to assert that X14 and X12 are proven "mathematically equivalent." The four-thread tournament evidence must be documented as **inconclusive**.

### Correction 3: The Time-Control Generalization is an Unresolved Hypothesis
- **Audit:** While expanding Match C from 40 games in P1.8 to 100 games in P1.9 showed that the $41.25\%$ score in P1.8 was within sampling error of an even score, this single 100-game match does not prove that evaluation scaling is invariant across all time controls. It remains an **unresolved hypothesis** requiring controlled ablation at both fixed depths and longer time controls.

### Correction 4: The 137/216 Multi-Causal Failure Atlas is Sample-Derived
- **Audit:** The finding that $63.4\%$ ($137 / 216$) of failures are multi-causal ($F7$) is an empirical characteristic of the specific 240 positions selected in the P1.9 Atlas. It is a diagnostic tool, not an immutable, universal law governing all chess engine mistakes.

### Correction 5: Dissection and Nullification of the Match SF $p = 0.931724$ Artifact
- **Audit of Calculation:** In Match SF, Janus Classical X14 lost all 40 games (0W–0D–40L across 20 opening pairs). In every opening pair $i$, Engine A scored $s_i = 0.0$.
- Consequently, the pair difference relative to even was identical for every single pair:
  $$d_i = s_i - 1.0 = -1.0 \quad \text{for all } i \in \{1, \dots, 20\}$$
- Because every pair had the identical outcome, the sample variance was:
  $$s_d^2 = \frac{1}{n-1} \sum_{i=1}^{20} (d_i - \bar{d})^2 = \frac{1}{19} \sum_{i=1}^{20} (-1.0 - (-1.0))^2 = 0.0$$
- When $s_d^2 = 0.0$, the standard error of the mean $se_d = \sqrt{s_d^2 / n} = 0.0$. The tournament script handled this division by zero with a defensive fallback:
  ```python
  t_stat = (mean_d / se_d) if se_d > 0 else 0.0
  ```
- This forced $t = 0.0$. Evaluating $t = 0.0$ against the Student's t distribution with 19 degrees of freedom yielded $p = 0.931724$.
- **Correction:** Reporting $p = 0.931724$ created the false impression that a 0–40 blowout was "statistically non-significant." In reality, under the true null hypothesis ($H_0: p = 0.5$):
  $$P(\text{0 points in 40 games}) = 0.5^{40} \approx 9.09 \times 10^{-13}$$
  Under paired outcomes ($N = 20$ pairs, all lost):
  $$P(\text{20 pair losses}) = 0.5^{20} \approx 9.54 \times 10^{-7}$$
  The deficit against Stockfish 19 is overwhelmingly statistically significant ($p < 10^{-6}$). The $t$-test output is formally struck from the record as a numerical division-by-zero artifact.

### Correction 6: No Finite Elo Point Estimate for Zero Score
- **Correction:** With 0 points scored out of 40 games, the maximum likelihood logistic Elo point estimate is $-\infty$. Reporting an arbitrary finite Elo (e.g. $-800$ or $-1200$) is mathematically unfounded. The only scientifically valid metric is the Wilson 95% score confidence interval:
  $$\text{Wilson 95\% Score Interval: } [0.0000, 0.0876]$$

### Correction 7: Syzygy Implementation Reclassification (Adapter Only)
- **Filesystem Audit:** A recursive scan of `E:\ChessXML` confirmed that **zero `.rtbw` or `.rtbz` tablebase files exist locally**.
- **Audit Verdict:** The 12 test cases executed in P1.9 tested only the UCI command parser, the Fathom C++ adapter structs, and the native alpha-beta search fallback. **No real disk-based tablebase probe was ever performed.**
- **Classification:** Milestone P1.9's Syzygy status is formally classified as **ADAPTER AND FALLBACK VERIFIED ONLY**. Real tablebase qualification remains completely outstanding.

