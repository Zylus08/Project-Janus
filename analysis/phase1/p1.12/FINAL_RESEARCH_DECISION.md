# PROJECT JANUS — PHASE 1, MILESTONE P1.12
## Final Research Decision

**Document ID:** `analysis/phase1/p1.12/FINAL_RESEARCH_DECISION.md`  
**Milestone:** Phase 1, Milestone P1.12  
**Date:** 2026-11-13  
**Decision Classification:** **CATEGORY D — BASELINE REBOOT & RE-CERTIFICATION**  
**Authoritative Baselines:**  
- Single-Threaded Production Baseline: **Janus Classical X7** (commit `b34e342`)  
- Four-Threaded Production Baseline: **Janus Classical X12** (commit `78ca3d5`)  
**Archived Experimental Candidate:** **Janus Classical X17** (commit `04c17f6...`)  
**Permanently Retired Experimental Branches:** X8, X9, X10, X11, X13, X14, X15, X16  

---

## 1. Formal Decision Statement

The Project Janus Engineering & Scientific Directorate hereby issues the formal research decision for Milestone P1.12:

1. **Re-Certification of Qualified Classical Baselines:**  
   - **Track S (Single-Threaded Baseline):** **Janus Classical X7** (commit `b34e342`, binary hash `86392a2f4bd4...`) is formally re-certified as the authoritative single-threaded classical baseline.
   - **Track P (Parallel Multithreaded Baseline):** **Janus Classical X12** (commit `78ca3d5`, binary hash `00b4f5fedea0...`) is formally re-certified as the authoritative four-threaded parallel classical baseline.
2. **Permanent Retirement of Intermediate Experimental Branches:**  
   Experimental candidates **X8, X9, X10, X11, X13, X14, X15, and X16** are formally and permanently retired from the active development tree. Forensic analysis confirmed that these branches introduced cumulative evaluation latencies, tree bloat, and ill-conceived pruning dampening that ultimately culminated in the $-117.2\text{ Elo}$ collapse of X16.
3. **Candidate X17 Archival & Status:**  
   Candidate **Janus Classical X17** successfully completed the Baseline Reboot. It purged the toxic Direction A mechanisms, restored baseline search depth, passed $100\%$ of correctness benchmarks, and demonstrated statistical parity across 250 tournament games ($51.5\%$ fast, $50.0\%$ slow on 1T; $50.0\%$ on 4T) with zero regressions. Under JCTS v2, because X17 demonstrates parity rather than statistically significant superiority ($p < 0.05$), it is not promoted to replace X7/X12 as the production baseline. Instead, X17 is archived as a certified sound research baseline with verified pawn endgame protection.

---

## 2. Comprehensive Evidence & Rationale

### 2.1 Resolution of Tournament Reporting Discrepancies (Phase 0)
Independent audit of all P1.11 tournament archives resolved the clerical reporting error: exactly 580 games were played and recorded across all five PGN files. Claims that X16 improved resilience against Stockfish 19 were empirically refuted (X16 scored only 1 draw on 4T in P1.11, compared to X15's 5 draws in P1.10).

### 2.2 Revalidation of Counterfactual LMR Findings (Phase 2)
Auditing all 39 move disagreements from P1.11 against Stockfish 19 depth 14 ground truth proved:
- **$38 / 39$ ($97.44\%$)** were benign positional alternatives with evaluation deltas $\Delta \le 15\text{ cp}$.
- **Only $1 / 39$ ($2.56\%$)** was a genuine tactical blunder (`END_04`, pawn breakthrough).
- **Logical Fallacy Exposed:** P1.11 conflated move disagreement with tactical error. Broad LMR dampening was solving an illusion.

### 2.3 Forensic Causal Decomposition (Phase 6)
Decomposing P1.11's intervention on clean baselines identified the exact mechanism of the X16 collapse:
- Unconditional static evaluation calls (F1) and RFP margin expansion (F2) had negligible standalone impacts ($-3.5\%$ and $-0.03\%$ NPS).
- **The Fatal Trigger:** `!improving` LMR reduction dampening simultaneously crippled both RFP and LMR on ~50% of tree nodes.
- **Consequence:** Effective Branching Factor exploded from $3.76$ to $4.26$, search depth collapsed by **$-2.19$ plies**, tactical solve rate collapsed from $37.5\%$ to $25.0\%$, and basic endgame opposition was blundered (`END_01`, `END_03`).

### 2.4 Competitive Ladder Calibration (Phase 11)
External calibration against Stockfish 11 (Tier 2) and Stockfish 19 (Tier 3) across 160 games revealed:
- **Stockfish 11 Classical Ceiling:** Swept Janus 80-0, proving that peak handcrafted classical chess programming has $\sim 500\text{--}550\text{ Elo}$ of headroom over Janus.
- **The Deficit Split:** **$70\%$** of Janus's gap to modern chess is the **Classical Architecture Gap** (missing singular extensions, multi-cut, ProbCut, king safety heatmaps, and endgame scale factors); only **$30\%$** is the **Neural Network Gap** (NNUE evaluation).

---

## 3. Summary of Milestone Deliverables

| Deliverable ID | Document / Artifact Path | Verification Status |
| :--- | :--- | :---: |
| **Phase 0** | `analysis/phase1/p1.12/P111_SCIENTIFIC_RECONCILIATION.md` | Certified |
| **Phase 1** | `analysis/phase1/p1.12/QUALIFIED_BASELINE_RECONSTRUCTION.md` | Certified |
| **Phase 2** | `analysis/phase1/p1.12/LMR_COUNTERFACTUAL_REVALIDATION.md` | Certified |
| **Phase 3** | `analysis/phase1/p1.12/CLASSICAL_SEARCH_QUALITY_ATLAS.md` | Certified |
| **Phase 4** | `analysis/phase1/p1.12/CLASSICAL_COMPETITIVE_REFERENCE_LADDER.md` | Certified |
| **Phase 5** | `analysis/phase1/p1.12/JCTS_2_COMPETITIVE_VALIDATION.md` | Certified |
| **Phase 6** | `analysis/phase1/p1.12/P111_CAUSAL_FEATURE_DECOMPOSITION.md` | Certified |
| **Phase 7** | `analysis/phase1/p1.12/P112_ARCHITECTURAL_DECISION_AND_IMPLEMENTATION.md` | Certified |
| **Phase 8** | `analysis/phase1/p1.12/P112_CORRECTNESS_AND_REGRESSION.md` | Certified |
| **Phase 9** | `analysis/phase1/p1.12/X17_CANDIDATE_FREEZE.md` | Certified |
| **Phase 10** | `analysis/phase1/p1.12/X17_INDEPENDENT_STRENGTH.md` | Certified |
| **Phase 11** | `analysis/phase1/p1.12/CLASSICAL_EXTERNAL_CALIBRATION.md` | Certified |
| **Phase 12** | `analysis/phase1/p1.12/FINAL_RESEARCH_DECISION.md` | Certified |

---

## 4. Administrative Declaration

The Baseline Reboot of Project Janus is complete. The project is cleansed of speculative, unverified heuristics and re-anchored upon verified empirical foundations.

**Official Certification:**  
Janus Classical X7 (1T) and Janus Classical X12 (4T) are retained as the authoritative classical baselines. Candidate X17 is frozen as an archived research reference. Milestone P1.12 is formally closed.

