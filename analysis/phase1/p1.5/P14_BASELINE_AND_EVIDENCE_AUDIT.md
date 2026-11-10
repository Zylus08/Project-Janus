# Project Janus — Phase 1, Milestone P1.5
## Milestone P1.4 Baseline Recovery, Forensic Evidence Audit & Control Verification

**Author:** Principal Computer Chess Engineer, C++17 Performance Architect, Classical Chess Evaluation Researcher, Search-Time Optimization Specialist, and Statistical Experimental Auditor  
**Lineage:** Janus Classical X  
**Incumbent Baseline:** Janus Classical X7 (`b34e342`)  
**Frozen Experimental Controls:** Classical C1, Janus Classical X6, Janus Classical X8, Janus Classical X9  
**Reference Engine:** Stockfish 19 (`sf_19`, unrestricted, default NNUE)  
**Branch:** `phase1/classical-janus`  
**Parent Commit:** `77672cb` (incorporating P1.4 engineering commit `bca971c`)  
**Date:** November 2026  
**Governing Rule 1:** Strictly Non-ML (Zero neural networks, zero NNUE, zero learned weights, zero offline-fitted models)

---

### 1. Executive Baseline Declaration & Phase 1 Protocol

Milestone P1.5 initiates the Classical Evaluation Expressiveness, Evaluation Efficiency, and Dynamic Time Management campaign for Project Janus.

Under the Phase 1 Non-ML charter:
- **Baseline Entity:** **Janus Classical X7 (`b34e342`) is the sole qualified production baseline** against which all new engineering candidates will be compared.
- **Experimental Candidates X8 & X9:** Both X8 (commit `501efbc`) and X9 (commit `bca971c`) remain frozen as experimental controls. Neither is adopted as the baseline.
- **Target Candidate:** **Janus Classical X10**, to be engineered strictly through handcrafted classical evaluation enhancements, evaluation performance engineering, and dynamic clock management.

---

### 2. Worktree Cleanliness & Ancestry Verification

- **Git HEAD:** `77672cb65847cb65c62ea12a8a13baec33c4b6f4`
- **Parent Engineering Commit:** `bca971c` (`feat(classical): selective search economics, feature-level recovery, and strength requalification (P1.4)`)
- **Git Branch:** `phase1/classical-janus`
- **Worktree Path:** `E:\ChessXML\project-janus-phase1`
- **Working Tree State:** Completely clean, zero uncommitted modifications.
- **Primary Research Repository:** `E:\ChessXML\project-janus` remains clean and completely untouched on branch `v0.3-benchmark-harness` at commit `6500b3f`.

---

### 3. Verification of Frozen Control Binaries

The SHA-256 cryptographic hashes of all classical engine binaries and external references have been audited:

| Lineage / Binary | File Path | Executable SHA-256 | Status |
|---|---|---|---|
| **Classical C1** | `analysis/v0.56/native/janus_native_engine.exe` | `a4f9d9d1502fef9bc714ca7ef6a724be4c160e0a552277d33d76e492f153ae29` | Verified |
| **Janus Classical X6** | `analysis/phase1/p1.2/control/janus_classical_x6.exe` | `138b43bcc303d2eebcc00ff6f4c02ce2f61bf64c9292a839e9e7b24ee26786e2` | Verified |
| **Janus Classical X7** | `analysis/phase1/p1.3/control/janus_classical_x7.exe` | `86392a2f4bd4182a4d7dc21e32940bd7939f6816794d5e1ab02f4082431ca28b` | **Verified Baseline** |
| **Janus Classical X8** | `analysis/phase1/p1.4/control/janus_classical_x8.exe` | `05cd4dc8c38581fd5ee775dc1cea89011c83e6969828caae17ca6e8136fa9429` | Verified Defective Control |
| **Janus Classical X9** | `analysis/phase1/p1.4/control/janus_classical_x9.exe` | `f61376a20acc04e612589ba98e386cc2780974f9ceb0abf5bee075e78355887d` | Verified Recovery Control |
| **Stockfish 19** | `E:/ChessXML/tools/stockfish/stockfish.exe` | `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0` | Verified External Benchmark |

---

### 4. Raw Evidence Forensic Reconciliation

Raw match JSON records and game PGNs across Milestones P1.3 and P1.4 were independently re-parsed and statistically verified:

#### A. Candidate X8 vs Baseline X7 (Milestone P1.3 Audit)
- **Source Artifact:** `analysis/phase1/p1.3/raw/x8_vs_x7_tournament_raw.json`
- **Total Games:** 100 games across 50 balanced opening pairs (1.0s + 50ms).
- **Match Record:** 25 Wins, 35 Draws, 40 Losses.
- **Score:** **42.5 / 100 (42.50%)**.
- **Rating Differential:** $\Delta\text{Elo}: -52.51$ Elo.
- **Paired $t$-Test:** Mean pair diff $\bar{d} = -0.3000, s_{\bar{d}} = 0.1464 \implies t = -2.0494, \mathbf{p = 0.0404}$.
- **Determination:** Statistically significant regression ($p < 0.05$). Promotion revoked.

#### B. Candidate X9 vs Baseline X7 (Milestone P1.4 Audit)
- **Source Artifact:** `analysis/phase1/p1.4/raw/x9_vs_x7_tournament_raw.json`
- **Total Games:** 200 games across 100 balanced opening pairs (1.0s + 50ms).
- **Match Record:** 67 Wins, 60 Draws, 73 Losses.
- **Score:** **97.0 / 200 (48.50%)**.
- **Rating Differential:** $\Delta\text{Elo}: -10.43$ Elo (Clustered 95% CI: $[-85.04, +63.22]$ Elo).
- **Paired $t$-Test:** Mean pair diff $\bar{d} = -0.0600, s_{\bar{d}} = 0.1071 \implies t = -0.5600, \mathbf{p = 0.5755}$.
- **Determination:** Statistically indistinguishable from parity ($p = 0.5755$). Promotion gate unmet; Baseline X7 formally retained.

#### C. Matched Benchmark vs Unrestricted Stockfish 19
- **Source Artifact:** `analysis/phase1/p1.4/raw/matched_stockfish19_progress_raw.json`
- **Baseline X7 vs SF19:** 40 games (20 pairs at 2.0s + 50ms): 0 Wins, 2 Draws, 38 Losses = **1.0 / 40 (2.50%)**.
- **Candidate X9 vs SF19:** 40 games (20 pairs at 2.0s + 50ms): 0 Wins, 1 Draw, 39 Losses = **0.5 / 40 (1.25%)**.

---

### 5. Audit of X7's Existing Evaluation & Time Management Implementation

Direct source inspection of `analysis/phase1/p1.3/control/janus_classical_x7.cpp` reveals material divergence between theoretical documentation and production code:

1. **Clock Handling Omissions in UCI:**
   - The UCI command parser handles `wtime`, `btime`, `winc`, `binc`, `depth`, and `movetime`.
   - **`movestogo` is completely ignored** in the parser.
   - Time allocation is hardcoded: $\text{alloc} = (\text{my\_time} + 40 \times \text{inc}) / 40$, with an arbitrary 50ms safety buffer.
   - There is zero awareness of move stability, score volatility, or remaining time pressure.
   - Inside the search tree, time checks only happen at the root between full iterative deepening plies: `if (dur.count() >= time_limit_sec) break;`. A single search iteration that explodes unexpectedly can overrun its budget by hundreds of percent without interrupting.

2. **Evaluation Deficits in E5:**
   - **King Safety:** Computed purely through piece attack units directed at the king ring. It does not scale with queen presence and can inappropriately penalize king centralization in endgames.
   - **Passed Pawns:** Scored purely on rank and immediate friendly support; does not evaluate candidate passers, square-of-the-pawn, backward pawns, or opposing blockades.
   - **Mobility:** Queen mobility is omitted entirely. Rook and bishop mobility do not consider pins or ray obstructions beyond friendly pieces and enemy pawn attacks.
   - **Evaluation Diagnostics:** X7 has no component-level trace mode (`eval_trace`), making it impossible to audit individual feature contributions for a given position.

### Phase 0 Sign-Off

The forensic audit confirms that:
1. Baseline X7 is the legitimate playing-strength standard.
2. X8 suffered from verification search latency ($p = 0.0404$).
3. X9 recovered the latency loss ($+42.1$ Elo) but could not surpass X7 ($p = 0.5755$) due to evaluation limitations.
4. X7's time management and evaluation leave significant headroom for deterministic, non-ML classical engineering.

**Status:** Phase 0 Completed & Verified.

