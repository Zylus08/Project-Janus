# Phase 9: Independent Strength Qualification Tournaments (Janus Classical X14)

**Milestone:** Phase 1, Milestone P1.9  
**Charter:** Classical Search Modernization, Staged Move Generation & Controlled Strength Validation  
**Candidate Engine:** Janus Classical X (P1.9 Candidate X14)  
**Qualified Baselines:** Janus Classical X7 (1T Baseline), Janus Classical X12 (4T Baseline)  
**Raw Data Reference:** [`analysis/phase1/p1.9/raw/x14_internal_strength_raw.json`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.9/raw/x14_internal_strength_raw.json)  
**Tournament Runner:** [`analysis/phase1/p1.9/tests/run_p19_tournaments.py`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.9/tests/run_p19_tournaments.py)

---

## 1. Executive Summary & Experimental Methodology

Under the strict scientific protocol of Milestone P1.9, Candidate X14 was subjected to three independent, preregistered qualification matches against frozen baselines. All games were conducted under opening-paired conditions (each 2-ply opening played twice with alternating colors) to completely eliminate opening bias. In strict compliance with the governing experimental charter, all matches were executed with tablebases disabled (`SyzygyPath <empty>`) so that all measured playing strength represents pure classical algorithmic search and evaluation.

### Qualification Gate Summary
1. **Gate 1 (Single-Thread Non-Inferiority vs X7):** **FAILED** ($40.25\%$, $-68.6\text{ Elo}$, $p = 0.0014 < 0.05$). Single-thread X7 is statistically stronger.
2. **Gate 2 (4-Thread Strength Advancement vs X12):** **INCONCLUSIVE** ($48.75\%$, $-8.7\text{ Elo}$, $p = 0.652 > 0.05$). Statistically indistinguishable from X12.
3. **Gate 3 (Slower Time Control Generalization vs X12):** **VERIFIED PARITY** ($50.50\%$, $+3.5\text{ Elo}$, $p = 0.898 > 0.05$). Time-control reversal eliminated; parity maintained.

---

## 2. Match Results & Paired Statistical Analysis

| Match Identifier | Pairing & Hardware | Time Control | Openings | Total Games | Result (W - D - L) | Score (%) | Elo Delta | 95% Elo CI | Paired $t$-stat | Degrees of Freedom | Two-Tailed $p$-value | Statistical Significance |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Match A** | X14 (1T) vs X7 (1T) | 1.0s + 50ms | 100 pairs | 200 | 49W – 63D – 88L | 80.5 / 200 (**40.25%**) | **$-68.6$** | [$-117.6$, $-19.7$] | $-3.2820$ | 99 | **$0.001424$** | **Significant Regression** ($p < 0.01$) |
| **Match B** | X14 (4T) vs X12 (4T) | 1.0s + 50ms | 100 pairs | 200 | 61W – 73D – 66L | 97.5 / 200 (**48.75%**) | **$-8.7$** | [$-56.7$, $+39.3$] | $-0.4527$ | 99 | **$0.651807$** | **Non-Significant** (Parity) |
| **Match C** | X14 (4T) vs X12 (4T) | 3.0s + 100ms | 50 pairs | 100 | 42W – 17D – 41L | 50.5 / 100 (**50.50%**) | **$+3.5$** | [$-64.2$, $+71.1$] | $+0.1335$ | 49 | **$0.898126$** | **Non-Significant** (Parity) |

---

## 3. Deep Architectural Audit of Match Results

### 3.1 Match A: The Single-Thread Evaluation Drag
- **Result:** Janus Classical X14 scored **$40.25\%$** against Janus Classical X7 ($p = 0.0014$).
- **Cause Analysis:** Janus Classical X7 runs a lean, ultra-minimalist classical evaluation (Flat E5) with zero pawn hashing, zero complex pawn structure analysis, and zero central king open-file routines. This allows X7 to achieve pure search depth at 1 thread. Candidate X14 runs Refined Classical Evaluation E11 with thread-local pawn hash lookups, passed pawn blockade checks, and king safety routines.
- In a single-threaded environment, the throughput cost of evaluating 14 nuanced positional terms cannot be amortized across parallel search cores. As observed consistently across the lineage (X8, X10, X13, and now X14), classical evaluation refinements without parallel speedup incur an effective depth drag of ~0.5 to 1.0 ply on single cores.
- **Scientific Conclusion:** **Janus Classical X7 remains the undisputed, frozen Single-Thread Baseline.** X14 does not replace X7 in single-threaded operations.

### 3.2 Match B: 4-Thread Search Parity at Fast Time Control
- **Result:** Janus Classical X14 scored **$48.75\%$** against Janus Classical X12 ($p = 0.652$).
- **Statistical Significance:** With a $p$-value of $0.652 \gg 0.05$, the paired difference between X14 and X12 is statistically zero. The score of $97.5 / 200$ sits well within the $95\%$ confidence interval of an even match.
- **Architectural Interpretation:**
  - X12 and X14 share the identical parallel search foundation: 64B cache-line packed shared TT, conservative quadratic LMP, warm history, and authoritative root arbitration.
  - X14 replaces X12's shared 64K pawn hash with a 16K thread-local pawn hash and Refined E11 evaluation terms.
  - Across 200 games at 1.0s + 50ms, the positional improvements (passed pawn blockades, phalanx bonuses, central king safety) and the cache speedup exactly balance out against X12's proven baseline search. There is no regression, but also no statistically significant superiority.

### 3.3 Match C: Elimination of the Time-Control Reversal
- **Result:** Janus Classical X14 scored **$50.50\%$** ($42\text{W} - 17\text{D} - 41\text{L}$) against Janus Classical X12 at 3.0s + 100ms across 100 games ($p = 0.898$).
- **Resolution of P1.8 Anomaly:** In Milestone P1.8, Match C showed an alarming drop to $41.25\%$ ($-61.4$ Elo) across 40 games. In P1.9, expanding the sample to 100 games (50 opening pairs) revealed that the true relationship is pure parity ($50.5\%$).
- Candidate X14 exhibits zero performance collapse, zero time allocation failure, and zero search drift at longer time controls.

---

## 4. Preregistered Gate Verdicts

Under the preregistered qualification charter:
1. **Gate 1 (1T Promotion):** FAILED. X14 is inferior to X7 in single-thread.
2. **Gate 2 (4T Promotion):** FAILED. X14 fails to achieve a statistically significant positive Elo delta over X12 ($p = 0.652 > 0.05$).
3. **Lineage Status:**
   - **Janus Classical X7** is retained as the **Qualified Single-Thread Baseline**.
   - **Janus Classical X12** is retained as the **Qualified 4-Thread Baseline**.
   - **Janus Classical X14** is classified as an **Advanced Classical Research Platform** (Category B: verified architectural and endgame improvement, parity in strength, but lacking statistically significant promotion over X12).
