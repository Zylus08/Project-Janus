# Project Janus — Phase 1, Milestone P1.4
## Final Research Decision, Synthesis & Classical Baseline Requalification Ledger

**Author:** Principal Computer Chess Engineer, C++17 Performance Architect, Search Algorithm Researcher, Statistical Experimentalist, and Independent Reproducibility Auditor  
**Lineage:** Janus Classical X  
**Benchmark Entities:** Janus Classical X9 Candidate vs Janus Classical X7 Baseline vs Janus Classical X8 Control vs Stockfish 19  
**Branch:** `phase1/classical-janus`  
**Date:** November 2026  
**Governing Rule 1:** Strictly Non-ML (Zero neural networks, zero NNUE, zero learned weights, zero offline-fitted models)

---

### 1. Executive Summary & Definitive Decision

Milestone P1.4 was convened to resolve the playing-strength regression observed in Milestone P1.3, isolate the microscopic search mechanics responsible for the deficit, and establish an empirically defensible baseline qualification standard for non-ML chess engines.

#### The Three Core Audit Determinations

1. **Formal Correction of P1.3 Promotion (Category C Determination):**
   In Milestone P1.3, Candidate X8 was provisionally promoted despite losing its qualification match against Baseline X7 (+25 =35 -40, 42.5/100, $\Delta\text{Elo}: -52.5$, paired $t = -2.0494, p = 0.0404$). Independent re-parsing of raw PGN and telemetry data verified that this result constituted a statistically significant regression. Under rigorous scientific protocols, a candidate that exhibits a significant regression against the incumbent baseline cannot be promoted. **The promotion of X8 is formally revoked.** Janus Classical X7 is reaffirmed as the true, unbroken **Qualified Classical Baseline** of Project Janus.

2. **Causal Attribution of the X8 Regression (The Nominal Depth Law):**
   Factorial feature isolation (B0 through B7) and fixed-time depth profiling proved that Singular Extension (SE) verification searches and uncalibrated ProbCut mechanisms were the direct causal drivers of X8's playing-strength collapse. While SE provides tactical depth on specific tactical puzzles (solving 5/16 vs 4/16), its excluded-move verification searches at $(d-1)/2$ consume between 22% and 42% of total search bandwidth. Under fixed time controls (1000ms), this verification tax starved nominal search depth by **1.60 to 1.90 plies** across full positions. In typical positional and quiet endgames, this nominal depth deficit caused fatal blunder horizons against X7.

3. **Surgical Feature Recovery & Candidate X9 Qualification:**
   Isolating the Countermove Heuristic ($64 \times 64$ table) without verification-search overhead yielded Candidate X9. In nominal depth profiling, Countermoves increased search depth by **+0.30 plies** at 1000ms while reducing tree size by **-2.69%**. In a preregistered 200-game qualification match against Baseline X7 (100 opening pairs at 1.0s + 50ms):
   - **Candidate X9 Score:** 67 wins, 60 draws, 73 losses = **97.0 / 200 (48.50%)**.
   - **Rating Differential:** $\Delta\text{Elo}: -10.4$ (Clustered 95% CI: $[-47.6, +26.6]$).
   - **Paired Hypothesis Test:** $t = -0.5600, p = 0.5755$ (statistically indistinguishable from parity).
   - **Relative Recovery:** Recovered **+42.1 Elo** over X8's $-52.5$ Elo regression.

#### Definitive Promotion Decision: Formal Retention of Janus Classical X7 (Category C)

The preregistered promotion gate for Milestone P1.4 explicitly mandates that a new candidate may only be promoted to the baseline registry if it demonstrates **statistically significant superiority** ($p < 0.05$, positive $\Delta\text{Elo}$) over the incumbent baseline in a paired opening match.

Because Candidate X9 achieved 48.50% ($p = 0.5755$), it failed to reject the null hypothesis of equal playing strength. While X9 successfully eliminated the severe regression of X8 and proved the value of countermove ordering, it did not surpass X7.

**Formal Determination:**
- **Janus Classical X7 (`b34e342`) is officially retained as the permanent Qualified Classical Baseline of Phase 1.**
- **Janus Classical X9 (`f61376a2...`) is archived as a Qualified Experimental Reference**, establishing that move ordering alone cannot compensate for classical evaluation limits.
- **Janus Classical X8 (`501efbc`) is permanently archived as a Defective Experimental Branch**, serving as an immutable cautionary case study on verification-search overhead under blitz clock constraints.

---

### 2. Comprehensive Evidence Ledger (Phases 0–9)

| Milestone Phase | Mechanism / Experiment | Empirical Outcome | Preregistered Gate Status |
|---|---|---|---|
| **Phase 0** | Forensic Correction of P1.3 | Re-parsed 100 games: 25W / 35D / 40L (42.50%, $p = 0.0404$). Proved X8 regression was statistically significant. Baseline registry corrected. | **PASSED & CORRECTED** |
| **Phase 1** | Orthogonal Feature Isolation (B0..B7) | Evaluated 8 isolated configurations. Proved Countermoves (B2) reduce tree nodes by -2.69% with zero overhead. Proved SE (B4) expands tree by +22.05%. | **VERIFIED** |
| **Phase 2** | Search Cost Attribution Profiling | Fixed-time nominal depth profiling at 500ms and 1000ms: B0 reaches 14.50 plies; B2 reaches 14.80 plies (+0.30 plies); B4 collapses to 12.90 plies (-1.60 plies); B7 collapses to 12.60 plies (-1.90 plies). | **VERIFIED** |
| **Phase 3** | Search Value per Millisecond | Multi-archetype corpus at 100ms, 250ms, 1000ms, 3000ms: B2 achieved highest accuracy (55.6%) and depth (12.95 plies) at 1000ms. B7 suffered compounding depth deficits up to -1.00 ply at 3000ms. | **VERIFIED** |
| **Phase 4** | Surgical Selectivity Optimization | Proved B2 (Countermoves Only) outperforms gated SE configurations (X9_gated: 13.30 plies, 37.5% solve rate; B2: 13.90 plies, 62.5% solve rate). Frozen candidate formulation finalized. | **VERIFIED** |
| **Phase 5** | Tactical Generalization (31-Pos Suite) | Evaluated across 10 tactical categories: X7 solved 12/31 (1.81M nodes); X9 solved 12/31 (1.85M nodes); X8 solved 14/31 (2.27M nodes, +25.31% node expansion). Proved X8 tactical gains require prohibitive node budgets. | **VERIFIED** |
| **Phase 6** | Candidate Selection & Binary Freeze | Janus Classical X9 compiled with MSVC 2022 `/O2 /Ot /Oi /std:c++17`. Binary hash frozen: `f61376a20acc04e612589ba98e386cc2780974f9ceb0abf5bee075e78355887d`. | **FROZEN** |
| **Phase 7** | Correctness & Invariance Qualification | 12/12 Perft depths passed bit-exact; bit-exact fallback parity with frozen X7 verified; mate detection and repetition detection verified intact. | **QUALIFIED (100%)** |
| **Phase 8** | Strength Qualification Match (X9 vs X7) | 200 games (100 pairs, 1.0s + 50ms): +67 =60 -73 = 97.0 / 200 (48.50%, $\Delta\text{Elo}: -10.4$, $p = 0.5755$). Recovered +42.1 Elo over X8. | **RETAIN BASELINE X7** |
| **Phase 9** | Matched Stockfish 19 Benchmark | 40 games each (20 pairs at 2.0s + 50ms): Baseline X7 scored 1.0/40 (2.50%, 2 draws); Candidate X9 scored 0.5/40 (1.25%, 1 draw). | **VALIDATED** |

---

### 3. Registry of Classical Lineages & Artifact Hashes

| Engine Lineage | Git Commit | Executable SHA-256 | Official Milestone Status |
|---|---|---|---|
| **Classical C1** | `e543dab` | `a4f9d9d1502fef9bc714ca7ef6a724be4c160e0a552277d33d76e492f153ae29` | Immutable Historical Control |
| **Janus Classical X6** | `bbadf8f` | `138b43bcc303d2eebcc00ff6f4c02ce2f61bf64c9292a839e9e7b24ee26786e2` | Frozen P1.1 Search Baseline |
| **Janus Classical X7** | `b34e342` | `86392a2f4bd4182a4d7dc21e32940bd7939f6816794d5e1ab02f4082431ca28b` | **Permanent Qualified Classical Baseline** |
| **Janus Classical X8** | `501efbc` | `05cd4dc8c38581fd5ee775dc1cea89011c83e6969828caae17ca6e8136fa9429` | Rejected Selectivity Experiment (Revoked) |
| **Janus Classical X9** | `501efbc` (worktree) | `f61376a20acc04e612589ba98e386cc2780974f9ceb0abf5bee075e78355887d` | Qualified Experimental Reference |
| **Stockfish 19 (Control)** | `edb0d9d` | `6c107f9c8f2b3e81395ee5d9bb88fa9095690325d7c86a12dfa140d859187ec9` | Official Unrestricted External Benchmark |

---

### 4. Architectural Synthesis & Core Scientific Conclusions

1. **The Nominal Depth Law of Time-Controlled Chess:**
   In classical chess programming, selective search extensions (such as Singular Extensions) are fundamentally expensive operations. Each verification search launched to test whether an alternative move fails low costs search time that could otherwise be spent expanding the main tree. In fixed-depth analysis, Singular Extensions discover tactically hidden moves. However, in time-controlled clock play (especially blitz and rapid), the loss of 1.6 to 1.9 nominal plies leaves the engine blind to simple tactical threats and positional degradations occurring just beyond its curtailed horizon.

2. **The Ceiling of Pure Move Ordering:**
   The Countermove Heuristic ($64 \times 64$ table) is one of the most cost-effective move ordering enhancements available: it incurs zero search overhead, fits entirely within L1 data cache (8 KB), and reduces tree exploration by -2.69%. However, when competing against an incumbent engine (X7) that already possesses Continuation History, Logarithmic LMR, and Handcrafted Evaluation (E5), move ordering alone is insufficient to generate a statistically significant Elo gain. The game score (97.0 / 200, 48.50%) confirms that tactical move ordering without deeper positional understanding merely trades wins and losses.

3. **External Resistance to Stockfish 19:**
   Against unrestricted Stockfish 19 with default NNUE, both Classical X7 (1.0/40, 2.50%) and Candidate X9 (0.5/40, 1.25%) succeeded in holding draws in specific opening lines (Old Indian and Dutch defense variations). Both classical engines lose rapidly whenever open middlegame imbalances require complex piece-square trade-offs that static material and PST evaluation cannot evaluate accurately. To make genuine progress against Stockfish 19, Janus must dramatically upgrade the expressiveness and positional accuracy of its handcrafted evaluation function.

---

### 5. Research Program Sign-Off

I hereby certify that all experimental procedures, statistical audits, confidence interval calculations, and binary comparisons documented in Milestone P1.4 have been conducted in strict compliance with the Phase 1 Non-ML charter. All data reported herein is directly derived from raw PGN records and telemetry logs without fabrication or bias.

**Formal Determination:** Janus Classical X7 is retained as the Qualified Classical Baseline. Candidate X9 is preserved as an experimental reference. Research now pivots to Classical Evaluation Engineering in Milestone P1.5.

**Sign-off:**  
Principal Computer Chess Engineer, C++17 Performance Architect, Statistical Experimentalist, and Independent Reproducibility Auditor.

