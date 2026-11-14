# Scientific Reconciliation & Statistical Audit of Milestone P1.19

## 1. Executive Summary & Verification of Repository State

Milestone P1.20 opens with an exhaustive independent audit of repository integrity, cryptographic provenance, tournament data reconstruction, and causal claims from Milestone P1.19.

### Repository & Provenance Invariants:
- **Repository Path:** `E:\ChessXML\project-janus-phase1`
- **Active Branch:** `phase1/classical-janus`
- **Starting HEAD Commit:** `bcf8f4c` (`feat(p1.19): isolate backward-pawn eval, verify pawn-hash integrity, and adjudicate Candidate X24`)
- **Parent Commit:** `bb87254`
- **Working Tree State:** Clean, zero uncommitted modifications, zero unstaged changes.
- **Remote Push Status:** Strictly zero remote push.

---

## 2. Cryptographic Checksum Audit of Frozen Binaries

All frozen control binaries, libraries, and source references were re-hashed using SHA-256:

| Binary / Asset Identifier | Role in Janus Research | File Path | SHA-256 Checksum | Verification Status |
| :--- | :--- | :--- | :--- | :---: |
| **Janus Classical X7** | Qualified 1T Strength Baseline | `analysis/phase1/p1.3/control/janus_classical_x7.exe` | `86392A2F4BD4182A4D7DC21E32940BD7939F6816794D5E1AB02F4082431CA28B` | **EXACT MATCH** |
| **Janus Classical X12** | Qualified 4T Strength Baseline | `analysis/phase1/p1.7/control/janus_classical_x12.exe` | `00B4F5FEDEA02A392A1AF9713A96512E5199A0E3AE55C295AD1C7CFFF1B47059` | **EXACT MATCH** |
| **Janus Classical X22** | Certified Research Reference | `analysis/phase1/p1.17/control/janus_classical_x22.exe` | `35D095CFFE8A2EDA412171803C09BE52A74DFB3F9744C04F573D2A7FFB1C2F1C` | **EXACT MATCH** |
| **Janus Classical X23** | Rejected Milestone P1.18 Candidate | `analysis/phase1/p1.18/control/janus_classical_x23.exe` | `39E875841B36AC82F464ABC7F31DB19D7CF5ABCD0F15B0A923B086A5BB393E39` | **EXACT MATCH** |
| **Janus Classical X24 (EXE)** | Frozen Milestone P1.19 Candidate | `analysis/phase1/p1.19/control/janus_classical_x24.exe` | `FBEAF9072680A4DDD172615C56E7A42B2EE472C16FBF04AC9C36D4BF35D80C40` | **FROZEN / VALID** |
| **Janus Classical X24 (DLL)** | Frozen Milestone P1.19 Native Lib | `analysis/phase1/p1.19/control/janus_classical_x24.dll` | `E56E8687C9E680BE57FDAA3CC1D5070EB40BDCFF52A1EB2A203FF97182786168` | **FROZEN / VALID** |
| **Janus Classical X24 (CPP)** | Frozen Milestone P1.19 Source Code | `analysis/phase1/p1.19/control/janus_classical_x24.cpp` | `3A1A5C854C836AAEE9A5EC586983D0A46A2A28C588A986FC412915079023F9D8` | **FROZEN / VALID** |

---

## 3. Independent Reconstruction of P1.19 Tournament Archives

Using `reconcile_p119.py`, all 570 games from P1.19 were parsed from raw PGN files, validated move-by-move using `python-chess`, and re-analyzed across pairwise opening outcomes:

| Tournament Dataset | Opponents | Time Control | Games | W / D / L | Score (%) | Pentanomial $[2.0, 1.5, 1.0, 0.5, 0.0]$ | Paired 95% CI | Two-Sided $p$-value | Elo Delta | Reconstructed Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Match Dev** | X24-S vs Reference X22-S | 0.5s + 20ms | 100 | +31 =29 -40 | 45.5% | $[7, 7, 15, 12, 9]$ | [36.57%, 54.43%] | $p = 0.3233$ | -31.4 | **100% Match** |
| **Match 1 (Primary Gate)** | X24-S vs Reference X22-S | 1.0s + 50ms | 100 | +29 =38 -33 | 48.0% | $[5, 13, 11, 15, 6]$ | [39.62%, 56.38%] | $p = 0.6400$ | -13.9 | **100% Match** |
| **Match 2 (1T Baseline)** | X24-S vs Baseline X7 | 1.0s + 50ms | 100 | +27 =42 -31 | 48.0% | $[2, 11, 21, 13, 3]$ | [41.46%, 54.54%] | $p = 0.5491$ | -13.9 | **100% Match** |
| **Match 3 (4T Baseline)** | X24-P vs Baseline X12 | 1.0s + 50ms | 100 | +29 =36 -35 | 47.0% | $[4, 12, 16, 10, 8]$ | [38.76%, 55.24%] | $p = 0.4755$ | -20.9 | **100% Match** |
| **Match 4 (Slow TC Check)** | X24-S vs Baseline X7 | 3.0s + 100ms | 50 | +6 =25 -19 | 37.0% | $[1, 3, 7, 10, 4]$ | [26.75%, 47.25%] | $p = 0.0129$ | -92.5 | **100% Match** |
| **Match 5 (Historical 2014)** | X24-S vs Stockfish 4 | 1.5s + 50ms | 40 | +0 =0 -40 | 0.0% | $[0, 0, 0, 0, 20]$ | [0.00%, 0.00%] | $p = 0.0000$ | $-\infty$ | **100% Match** |
| **Match 6 (Classical 2020)** | X24-S vs Stockfish 11 | 1.5s + 50ms | 40 | +0 =2 -38 | 2.5% | $[0, 0, 0, 2, 18]$ | [0.00%, 5.87%] | $p = 0.0000$ | -636.4 | **100% Match** |
| **Match 7 (SOTA NNUE)** | X24-S vs Stockfish 19 | 1.5s + 50ms | 40 | +0 =5 -35 | 6.25% | $[0, 0, 0, 5, 15]$ | [1.38%, 11.12%] | $p = 0.0000$ | -470.4 | **100% Match** |
| **Total Reconstructed** | All 8 Matches | - | **570** | - | - | - | - | - | - | **570 / 570 Games** |

### Audit of the Slow-Time Control $p$-value:
- The reported p-value of **0.0129** in Match 4 was recomputed from the 25 independent opening-pair scores:
  $$\text{Pair Scores} = [0.0, 0.5, 0.5, 1.0, 0.5, 0.0, 0.5, 0.5, 0.5, 1.0, 0.0, 0.5, 1.5, 0.5, 0.5, 0.0, 1.0, 1.5, 0.5, 1.0, 1.0, 1.0, 1.0, 1.5, 2.0] / 2.0$$
  $$\bar{x} = 0.3700, \quad s = 0.2615, \quad SE = \frac{0.2615}{\sqrt{25}} = 0.05230$$
  $$t = \frac{0.3700 - 0.5000}{0.05230} = -2.4856$$
  $$p_{\text{two-sided}} = 2 \times \Phi(-2.4856) = 0.0129$$
- **Verification Result:** The p-value was calculated from the correct paired-opening sample. The statistical rejection of $H_0: \mu = 0.50$ is mathematically sound.

---

## 4. Rigorous Audit of P1.19 Causal Claims

Milestone P1.19 advanced several explanatory assertions to interpret the experimental results. Each claim was subjected to formal epistemological classification:

| Claim Statement | P1.19 Narrative Context | Audit Classification | Epistemological Justification |
| :--- | :--- | :---: | :--- |
| **Claim 1: "Track B was the sole cause of X23's weakness."** | Excising Track B recovered +28.1 Elo in Dev play. | **CONTRADICTED** | While Track B caused severe tactical instability, Track A itself failed to beat Reference X22 (48.0%), failed to beat Baseline X7 (48.0%), and collapsed at slow TC (37.0%). Track B was a major factor, but not the *sole* cause of underperformance. |
| **Claim 2: "Track A fundamentally harms longer-time-control chess."** | In Match 4 at 3.0s, X24 collapsed to 37.0% ($p = 0.0129$). | **SUPPORTED BUT NOT CAUSAL** | The empirical regression at 3.0s is statistically verified, but asserting that Track A *fundamentally* harms slow chess conflates an observed correlation with an unproven causal mechanism. Deep-search interactions, pruning thresholds, or time allocation could be responsible. |
| **Claim 3: "Backward-pawn penalties directly cause passive rook play."** | Qualitative review showed X24 defending weak pawns passively. | **HYPOTHESIS** | This is a plausible explanatory hypothesis, but has not been verified via counterfactual position replays where the evaluation term is isolated while holding search trees constant. |
| **Claim 4: "SF19's higher draw count results specifically from locked-position strategy."** | X24 drew 5 games vs SF19 in closed pawn structures. | **SUPPORTED BUT NOT CAUSAL** | The draws occurred in closed French/Caro-Kann structures, but this is a consequence of very fast blitz time controls (1.5s) where SF19 has insufficient time to calculate deep speculative piece sacrifices, not a deliberate "strategy". |
| **Claim 5: "Static pawn penalties have been definitively disproven as a category."** | Handcrafted backward-pawn terms failed across all matches. | **UNSUPPORTED** | One specific parameterization ($-10\text{ mg} / -15\text{ eg}$) failing to outperform Baseline X7 does not disprove static pawn evaluation. Mature engines (SF11) use backward pawn terms successfully when balanced with piece mobility and dynamic king safety. |

---

## 5. Clarification of Evaluation Latency vs Search Throughput

Milestone P1.19 occasionally blurred the distinction between evaluation latency and search throughput:
- **Evaluation Latency:** The execution time of a single call to `evaluate()`. Measured at $1187.7\text{ ns}$ (warm cache) vs $1374.3\text{ ns}$ (disabled hash), representing a $+13.58\%$ micro-optimization.
- **Search Throughput (NPS):** The total alpha-beta nodes searched per second across the entire search tree.
- **Critical Distinction:** A 13.58% reduction in evaluation latency does not translate into a 13.58% increase in playing strength if the evaluated terms distort alpha-beta move ordering or cause aspiration-window re-searches. Search throughput must always be evaluated in conjunction with branch pruning efficiency.

---

## 6. Phase 0 Conclusion

Milestone P1.19's data archive is 100% verified and mathematically sound. The slow-time-control regression is real, but its causal attribution remains an open question. Milestone P1.20 proceeds to Phase 1 (Engine Lineage & Feature Matrix) and Phase 2 (Time-Control Regression Replication) with zero unverified assumptions.
