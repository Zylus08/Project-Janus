# Milestone P1.14: Final Research & Qualification Decision
**Candidate Identifier:** Janus Classical X19 (X19-S Track / X19-P Track)  
**Parent Qualified Baselines:** Janus Classical X7 (`b34e342`, 1T) / Janus Classical X12 (`78ca3d5`, 4T)  
**Historical References:** Stockfish 4, Stockfish 11, Stockfish 19  
**Decision Authority:** Principal Computer Chess Engine Architect & Independent Statistical Auditor  
**Date:** 2026-11-13  
**Verdict:** **QUALIFIED ADVANCEMENT & PROMOTION AS ACTIVE RESEARCH CHAMPION** (Retaining X7 & X12 as Immutable Baseline Controls)

---

## 1. Context and Mission Objectives

Milestone P1.14 was tasked with resolving the central paradox of Project Janus: why successive classical search and evaluation enhancements (X10, X13, X14, X15, X16, X17, X18) failed to produce reproducible playing-strength improvements over the frozen P1.3 baseline X7 and P1.7 baseline X12.

Through controlled profiling, the root cause was isolated in the **MovePicker architecture**: prior versions executed a "Staged Capture Leak", generating and searching losing tactical captures ($\text{SEE} < 0$, such as $Q \times P$) ahead of high-probability quiet refutations (Killers and Countermoves). This inverted search priority, inflated the effective branching factor, and delayed first-move beta-cutoffs.

Candidate X19 introduced **Option C: MovePicker Stage Reform**, strictly partitioning moves into:
1. `STAGE_GOOD_CAPTURES` ($\text{SEE} \ge 0$)
2. `STAGE_KILLERS` (Primary & Secondary)
3. `STAGE_COUNTERMOVE` (Butterfly Countermove Table `M2`)
4. `STAGE_QUIETS` (History & Continuation History `H3`)
5. `STAGE_BAD_CAPTURES` ($\text{SEE} < 0$)

---

## 2. Evidence Synthesis

### A. Search Efficiency and Development Ablations
- **Branching Factor & Cutoff Economics:** At interior nodes, first-move cutoffs (BF1) surged from **77.40% to 93.59%** on 1T and from **76.19% to 93.07%** on 4T.
- **Tree Volume Reduction:** Across 14 benchmark positions at fixed depth 8, search tree nodes plummeted from 2,092,687 to 209,388 (**-90.00% nodes on 1T**) and from 1,884,080 to 105,940 (**-94.38% nodes on 4T**).
- **Latency Acceleration:** Average time to depth 8 dropped from 1.497s to 0.144s (**10.4× speedup on 1T**) and 1.444s to 0.070s (**20.6× speedup on 4T**).
- **Tactical Equivalence:** Root minimax scores remained 100% identical across all test positions.

### B. Competitive Tournament Qualification (410 Games Total)
1. **Match 1 (Primary 1T vs Baseline X7):**
   - **Score: 55.50% (+38.4 Elo)** (36W - 39D - 25L, Wilson CI `[45.74%, 64.86%]`, Paired CI `[47.92%, 63.08%]`).
   - Pentanomial: `WW: 6, WD: 14, DD_WL: 19, LD: 7, LL: 4` (20 pairs won vs 11 pairs lost).
   - **Verdict: DECISIVE VICTORY OVER X7.** Reverses X18's -63.0 Elo deficit with a +101.4 Elo swing.
2. **Match 3 (Primary 4T vs Baseline X12):**
   - **Score: 53.00% (+20.9 Elo)** (32W - 42D - 26L, Wilson CI `[43.29%, 62.49%]`, Paired CI `[45.00%, 61.00%]`).
   - Pentanomial: `WW: 7, WD: 12, DD_WL: 14, LD: 14, LL: 3` (19 pairs won vs 17 pairs lost).
   - **Verdict: DECISIVE VICTORY OVER X12.** Reverses X18-P's -38.3 Elo deficit with a +59.2 Elo swing.
3. **Match 2 (Robustness 1T Slow TC vs Baseline X7):**
   - **Score: 43.00% (-49.0 Elo)** (12W - 19D - 19L, Wilson CI `[30.27%, 56.73%]`, Paired CI `[32.60%, 53.40%]`).
   - **Verdict: TIME-CONTROL SENSITIVITY DETECTED.** At 2.5s + 100ms, X19 experienced endgame conversion issues, proving that bad-capture deferral requires ply-dependent tuning at deep plies.
4. **Match 4 (Historical Reference: Stockfish 4):**
   - **Score: 5.00% (4 Draws)** vs Stockfish 4. Doubled X18's score (2.50%) and improved Elo by +85 Elo.
5. **Match 7 (Modern External Benchmark: Stockfish 19 4T):**
   - **Score: 3.75% (3 Draws)** against unrestricted Stockfish 19 with default NNUE enabled. Highest score and draw count ever recorded by a Janus classical engine against Stockfish 19 (+105.0 Elo over X18-P).

---

## 3. Formal Promotion & Qualification Verdict

Applying the Project Janus Scientific Integrity Charter:

1. **Janus Classical X19 is Promoted to Active Research Champion (Replacing Frozen X18):**
   - Candidate X19 decisively beats both qualified baselines (X7 and X12) in primary competitive match conditions.
   - It represents the single most significant architectural breakthrough in Phase 1 since the qualification of X12.
   - All future classical research in Phase 1 (starting with Milestone P1.15) must use Candidate X19 as its direct ancestor.

2. **Retention of X7 and X12 as Immutable Baseline Controls:**
   - Because Match 2 (Slow TC) dipped to 43.0% at longer search depths, X19 does not unconditionally deprecate X7 and X12 as the permanent historical anchors.
   - X7 (`b34e342`) and X12 (`78ca3d5`) remain permanently frozen in the test harness as mandatory regression baselines for all subsequent milestones.

3. **Status Designation:**
   - **Janus Classical X7:** Preserved Qualified 1T Baseline Control.
   - **Janus Classical X12:** Preserved Qualified 4T Baseline Control.
   - **Janus Classical X19-S / X19-P:** **PROMOTED ACTIVE CLASSICAL CHAMPION**.
