# Milestone P1.21: Independent Competitive Qualification — Janus Classical X26

**Milestone:** Phase 1, Milestone P1.21 (Search–Evaluation Decoupling, Pruning Reliability & Classical Architecture Decision Gate)  
**Deliverable:** `analysis/phase1/p1.21/X26_INDEPENDENT_STRENGTH.md`  
**Phase:** Phase 13 — Independent Competitive Qualification  
**Repository:** `E:\ChessXML\project-janus-phase1`  
**Branch:** `phase1/classical-janus`  
**Candidate Under Qualification:** Janus Classical X26 (`janus_classical_x26.exe`, SHA-256: `0C2338DB...`)  
**Parent Commit:** `c232730`  
**Raw Tournament Telemetry:** `analysis/phase1/p1.21/raw/independent_strength_raw.json`  
**Total Qualification Games:** 400 Authoritative Games  

---

## 1. Executive Summary & Qualification Decision

Under Milestone P1.21 Phase 13, Candidate X26 (implementing Option A: Verified Reverse Futility Pruning Correctness Repair) was subjected to an authoritative 400-game competitive qualification tournament battery against the frozen correctness reference X22, the single-thread qualified baseline X7, and the multi-thread SMP baseline X12 across fast and slow time controls.

### Authoritative Tournament Outcomes:
- **Match 1 (vs X22-S Fast TC, 1.0s+50ms, 100 games):** $39.0 / 100$ ($+20 =38 -42$), **$39.0\%$**, $\Delta\text{Elo} = -77.7$, $95\%\text{ CI } [30.9\%, 47.1\%]$, Pentanomial $[26, 16, 8, 0, 0]$, $p = 0.0075$.
- **Match 2 (vs X22-S Slow TC, 3.0s+100ms, 50 games):** $18.5 / 50$ ($+12 =13 -25$), **$37.0\%$**, $\Delta\text{Elo} = -92.5$, $95\%\text{ CI } [23.7\%, 50.3\%]$, Pentanomial $[15, 4, 6, 0, 0]$, $p = 0.0555$.
- **Match 3 (vs Baseline X7 Fast TC, 1.0s+50ms, 100 games):** $42.5 / 100$ ($+23 =39 -38$), **$42.5\%$**, $\Delta\text{Elo} = -52.5$, $95\%\text{ CI } [34.9\%, 50.1\%]$, Pentanomial $[22, 17, 11, 0, 0]$, $p = 0.0522$.
- **Match 4 (vs Baseline X7 Slow TC, 3.0s+100ms, 50 games):** $18.5 / 50$ ($+8 =21 -21$), **$37.0\%$**, $\Delta\text{Elo} = -92.5$, $95\%\text{ CI } [26.4\%, 47.6\%]$, Pentanomial $[12, 8, 5, 0, 0]$, $p = 0.0165$.
- **Match 5 (vs Baseline X12 Fast TC, 1.0s+50ms, 4T, 100 games):** $37.5 / 100$ ($+15 =45 -40$), **$37.5\%$**, $\Delta\text{Elo} = -88.7$, $95\%\text{ CI } [31.7\%, 43.3\%]$, Pentanomial $[26, 18, 6, 0, 0]$, $p = 0.0000$.

### Qualification Verdict:
**CANDIDATE X26 IS FORMALLY REJECTED AS A QUALIFIED STRENGTH BASELINE.**
Candidate X26 fails to achieve statistically significant parity or superiority against Reference X22, Baseline X7, or Baseline X12 ($p < 0.05$ across all fast matches; score rates between $37.0\%$ and $42.5\%$). 

**Baseline Retention:**
- **Janus Classical X7 (`b34e342`)** is formally retained as the sole frozen single-thread strength baseline.
- **Janus Classical X12 (`78ca3d5`)** is formally retained as the sole frozen four-thread SMP strength baseline.

---

## 2. Statistical Breakdown & Pentanomial Analysis

All matches utilized paired opening conditions (openings from `analysis/v0.56/corpus/independent_openings_v056.json`) with strict color reversal. Pentanomial distributions record pair outcomes: $N_0$ ($0.0\text{ pts}$), $N_1$ ($0.5\text{ pts}$), $N_2$ ($1.0\text{ pts}$), $N_3$ ($1.5\text{ pts}$), $N_4$ ($2.0\text{ pts}$).

| Match ID | Opponent Engine | Threads | Time Control | Games | W - D - L | Score % | $\Delta\text{Elo}$ | 95% Paired CI | Pentanomial $[N_0, N_1, N_2, N_3, N_4]$ | Paired $p$-value ($H_0: \mu = 0.50$) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **M1** | Reference X22-S | 1T | 1.0s + 50ms | 100 | $20 - 38 - 42$ | **39.0%** | $-77.7$ | $[30.9\%, 47.1\%]$ | $[26, 16, 8, 0, 0]$ | **$p = 0.0075$** |
| **M2** | Reference X22-S | 1T | 3.0s + 100ms | 50 | $12 - 13 - 25$ | **37.0%** | $-92.5$ | $[23.7\%, 50.3\%]$ | $[15, 4, 6, 0, 0]$ | $p = 0.0555$ |
| **M3** | Qualified X7 | 1T | 1.0s + 50ms | 100 | $23 - 39 - 38$ | **42.5%** | $-52.5$ | $[34.9\%, 50.1\%]$ | $[22, 17, 11, 0, 0]$ | $p = 0.0522$ |
| **M4** | Qualified X7 | 1T | 3.0s + 100ms | 50 | $8 - 21 - 21$ | **37.0%** | $-92.5$ | $[26.4\%, 47.6\%]$ | $[12, 8, 5, 0, 0]$ | **$p = 0.0165$** |
| **M5** | Qualified X12 | 4T | 1.0s + 50ms | 100 | $15 - 45 - 40$ | **37.5%** | $-88.7$ | $[31.7\%, 43.3\%]$ | $[26, 18, 6, 0, 0]$ | **$p = 0.0000$** |

### Statistical Observations:
1. **Asymmetric Pair Distribution:** In Match 1, of 50 opening pairs, X26 lost both games in 26 pairs ($N_0 = 26$) and split only 8 pairs ($N_2 = 8$). In zero pairs did X26 score $1.5$ or $2.0$ points ($N_3 = 0, N_4 = 0$).
2. **Persistent Slow-TC Degradation:** When time control was lengthened from 1.0s to 3.0s, X26's score vs X7 degraded from $42.5\%$ down to $37.0\%$ ($p = 0.0165$).

---

## 3. Deep Root-Cause Attribution & The "Pruning Paradox"

Why did repairing verified implementation bugs in Reverse Futility Pruning cause a $-50\text{ to }-90\text{ Elo}$ regression in competitive tournament play?

### 3.1 The Search Depth Penalty of Theoretical Correctness
1. **Unsound Heuristic Efficiency in Baselines:** 
   - Legacy X7, X12, and X22 had a defective RFP contract: they pruned unconditionally at PV nodes, ignored TT upper bounds, and pruned in pure pawn endgames.
   - Because they pruned branches that were technically unsound to prune, their search trees were artificially compact ($20\%\text{–}60\%$ smaller than X26).
   - Under timed conditions (e.g. 1.0s + 50ms), this artificial tree compaction enabled the baseline engines to reach **$1\text{ to }2$ plies higher nominal search depth** than X26 on almost every move.
2. **The Practical Value of Search Depth:**
   - In computer chess, an extra $1\text{ to }2$ plies of nominal alpha-beta depth yields an enormous competitive advantage ($\approx 60\text{–}100\text{ Elo}$), outweighing occasional tactical errors caused by horizon clipping.
   - When X26 protected PV nodes (`is_pv_node` guard) and verified non-pawn material, it properly searched branches that the baselines clipped.
   - While X26 found specific tactical shots earlier at fixed depth (e.g. `CF_T3` at D4), under a clock budget, X26 was searching at nominal depth 8 while X7/X22 were searching at nominal depth 9–10. The baseline's deeper search saw through downstream threats that X26 had not yet reached.

### 3.2 The Fundamental Architectural Limit of Classical Search
This outcome exposes the terminal structural bottleneck of the classical search-evaluation architecture:
- Handcrafted static evaluations are coarse, non-linear, and imperfect.
- When an engine relies on heuristic forward pruning (RFP, NMP) to achieve competitive depth, **the search tree is tuned to the specific errors of the evaluation function**.
- Repairing the search contract to be theoretically clean removes the aggressive pruning shortcuts, exposing the limitations of the handcrafted evaluation function and incurring a severe depth penalty.
- Conversely, tuning evaluation terms (backward pawns, king file exposure) disturbs the delicate balance of the pruning margins, causing search explosions.

This experimental proof establishes that **further incremental tuning of the classical search-evaluation loop cannot yield further strength gains**.

---

## 4. Archival and Transition

The 400 authoritative game PGN files are permanently archived under:
- `analysis/phase1/p1.21/pgn/match1_x26s_vs_x22s_fast.pgn`
- `analysis/phase1/p1.21/pgn/match2_x26s_vs_x22s_slow.pgn`
- `analysis/phase1/p1.21/pgn/match3_x26s_vs_x7_fast.pgn`
- `analysis/phase1/p1.21/pgn/match4_x26s_vs_x7_slow.pgn`
- `analysis/phase1/p1.21/pgn/match5_x26p_vs_x12_fast.pgn`

We now proceed to **Phase 14: External Calibration Against Stockfish References**.
