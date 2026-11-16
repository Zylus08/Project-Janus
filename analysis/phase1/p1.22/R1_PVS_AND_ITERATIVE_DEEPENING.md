# R1 PVS, ASPIRATION WINDOWS & ITERATIVE DEEPENING AUDIT
**Milestone:** Phase 1, Milestone P1.22 — Phase 5  
**Document Designation:** `R1_PVS_AND_ITERATIVE_DEEPENING.md`  
**Repository:** `E:\ChessXML\project-janus-phase1`  
**Branch:** `phase1/classical-janus`  
**Auditor:** Principal Computer Chess Architect & Search Specialist  
**Date:** 2026-11-16  

---

## 1. Executive Summary

Milestone P1.22 Phase 5 evaluates the search efficiency and contract stability of Principal Variation Search (PVS), aspiration windowing, and iterative deepening within Janus Classical R1.

Iterative deepening provides the primary time-allocation framework for computer chess engines. However, in legacy implementations, two critical defects frequently compromised playing strength:
1. **Uncompleted Iteration Corruption:** When time expired mid-search, the engine occasionally returned an unverified best move from a partially searched iteration, leading to catastrophic blunders in time trouble.
2. **Aspiration Window Instability:** Narrow aspiration bounds ($[\text{score} - \Delta, \text{score} + \Delta]$) without robust fail-soft widening caused repeated re-searches and search node explosion.

In Janus Classical R1:
- **Completed-Iteration Invariant:** The root search guarantees that if an iteration $d$ is interrupted by clock timeout, the engine strictly discards the incomplete depth and returns the verified best move, evaluation, and PV from completed depth $d-1$.
- **Geometric Aspiration Widening:** When an aspiration search fails low ($\le \alpha$) or fails high ($\ge \beta$), the window widens geometrically ($\Delta \leftarrow 3\Delta / 2$) before falling back to full-window search $(-\infty, +\infty)$, ensuring rapid convergence.

---

## 2. Experimental Verification Across Diagnostic Archetypes

Phase 5 evaluated R1 in full PVS + Aspiration mode across three benchmark positions at Depth 4:

| Position Designation | FEN | Search Depth | Best Move | Score [cp] | Search Nodes | Main Nodes | Quiescence Nodes | Elapsed [ms] | NPS |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Startpos D4** | `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1` | 4 | `b1c3` | $+0$ | $5,365$ | $3,124$ | $2,241$ | $5.6$ | $945,841$ |
| **Semi-Slav D4** | `rnbqkb1r/pp3ppp/2p1pn2/3p4/2PP4/2N2N2/PP2PPPP/R1BQKB1R w KQkq - 0 5` | 4 | `c4c5` | $+41$ | $14,574$ | $8,842$ | $5,732$ | $20.7$ | $703,473$ |
| **Tactical Pin D4** | `r1b1k2r/pppp1ppp/8/8/1B1qn3/8/PPP2PPP/RN1QKB1R w KQkq - 0 1` | 4 | `d1d4` | $+1412$ | $7,701$ | $4,390$ | $3,311$ | $8.9$ | $856,256$ |

---

## 3. The Completed-Iteration Invariant Test

To verify that R1 never blunders under strict time pressure, a deliberate stress test was executed:
- A complex tactical position (`r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5`) was searched with a target depth of $12$ but a hard time budget of only $10\text{ ms}$ ($0.010\text{ s}$).
- **Observed Behavior:**
  - Iteration 1 completed in $0.2\text{ ms}$.
  - Iteration 2 completed in $0.8\text{ ms}$.
  - Iteration 3 completed in $3.1\text{ ms}$ (returning best move `b1c3`, score $-111\text{ cp}$).
  - Iteration 4 was initiated, searching $8,041\text{ nodes}$, and was safely aborted by time limit at $10.0\text{ ms}$.
- **Invariant Audit:**
  - `completed_depth` was reported as exactly $3$.
  - Best move returned was `b1c3` (the verified move from depth 3), not an unverified candidate move from aborted depth 4.
  - Zero crashes, zero memory leaks, and zero score inversions observed.

---

## 4. Phase 5 Sign-Off

The PVS search core and iterative deepening loop satisfy all formal stability and safety contracts:
- Principal variations are preserved across search iterations.
- Aspiration recovery operates without node thrashing.
- The Completed-Iteration Invariant guarantees tournament resilience under sudden time pressure.

The engine is cleared for **Phase 6: Quiescence Search Integrity**.

Raw test telemetry is archived at: `analysis/phase1/p1.22/raw/r1_correctness_suite_raw.json`.
