# Milestone P1.21: Final Research Decision & Baseline Adjudication

**Milestone:** Phase 1, Milestone P1.21 (Search–Evaluation Decoupling, Pruning Reliability & Classical Architecture Decision Gate)  
**Deliverable:** `analysis/phase1/p1.21/FINAL_RESEARCH_DECISION.md`  
**Phase:** Phase 15 — Final Research Decision  
**Repository:** `E:\ChessXML\project-janus-phase1`  
**Branch:** `phase1/classical-janus`  
**Date:** 2026-11-15  

---

## 1. Executive Summary & Adjudication Verdict

Milestone P1.21 was designed to determine whether search–evaluation coupling is preventing the Janus Classical engine from converting valid positional knowledge and additional computational resources into stronger chess, and to test whether repairing demonstrated defects in the search contract could recover competitive strength.

Across sixteen phases of rigorous empirical investigation—comprising full source diff analysis, counterfactual pruning audits, evaluation perturbation studies, depth-dependent reliability profiling, shallow exact reference verification, search-cost microbenchmarking, controlled ablations, full perft/referee correctness verification, and an authoritative 500-game tournament battery—the evidence is definitive.

### Formal Milestone Decisions:
1. **Candidate X26 Adjudication:** **REJECTED.**  
   Candidate X26 (implementing Option A: Verified Reverse Futility Pruning Correctness Repair) achieved only **$39.0\%$** against Reference X22 at fast TC ($p = 0.0075$), **$37.0\%$** at slow TC ($p = 0.0555$), **$42.5\%$** against Baseline X7 at fast TC ($p = 0.0522$), **$37.0\%$** against X7 at slow TC ($p = 0.0165$), and **$37.5\%$** against Baseline X12 on 4 threads ($p = 0.0000$). Candidate X26 is formally rejected as a qualified strength successor.
2. **Strength Baselines Maintained:**  
   - **Janus Classical X7 (`b34e342`)** is formally reaffirmed as the sole frozen single-thread strength baseline.
   - **Janus Classical X12 (`78ca3d5`)** is formally reaffirmed as the sole frozen four-thread SMP strength baseline.
3. **Correctness Reference Maintained:**  
   - **Janus Classical X22 (`e33f292`)** is formally maintained as the non-regressing correctness and tactical quiescence research reference.
4. **Classical Search Paradigm Status:** **DECLARED EXHAUSTED.**  
   Incremental handcrafted tuning of the classical alpha-beta search and evaluation architecture has reached a hard asymptotic ceiling. No further incremental modifications within this paradigm will be pursued.
5. **Phase 16 Architecture Pivot:** **MANDATED.**  
   Milestone P1.22 will execute a comprehensive architectural pivot away from incremental heuristic patching toward a modern, decoupled search architecture.

---

## 2. Definitive Scientific Attribution: The Pruning Paradox & Hard Coupling

Across Milestones P1.15 through P1.21, a recurring pattern emerged:
- Milestone P1.18 introduced backward-pawn and king-safety evaluations (X23). Result: slow TC regression.
- Milestone P1.19 isolated backward pawns (X24). Result: severe search tree expansion and slow TC regression (-6.0% vs X22).
- Milestone P1.20 ablated backward pawns and introduced connected passed pawns (X25). Result: recovered parity against X7 ($49.0\%$, $p = 0.8380$), but failed to achieve any positive Elo gain.
- Milestone P1.21 audited the search contract, proved four major bugs in Reverse Futility Pruning, and implemented the verified repair (Option A / X26). Result: scored $37.0\%\text{–}42.5\%$ against legacy baselines.

### The Mechanism of the Pruning Paradox:
1. **Unsound Heuristic Compression in Legacy Baselines:**
   - In Janus Classical X7, X12, and X22, the RFP contract was buggy: it pruned PV nodes, failed to store TT bounds, ignored TT upper bounds, and pruned in pure pawn endgames.
   - However, because it pruned so aggressively, it compressed the search tree by $20\%\text{–}60\%$, allowing the engine to reach nominally higher search depths (1–2 plies deeper) under a chess clock.
2. **The Cost of Theoretical Soundness:**
   - When Option A repaired the RFP contract in X26 (protecting PV nodes, checking non-pawn material, verifying TT conflicts), the search tree expanded to its correct full-width selective size.
   - While X26 found specific tactical shots earlier at fixed depth (e.g. `1. Nxe6!` at D4 in `CF_T3`), under match play with a clock, X26 reached nominal depth 8 when X7 reached depth 10.
   - In computer chess, a 1–2 ply depth deficit is fatal ($\approx 60\text{–}100\text{ Elo}$ loss), because tactical depth trumps selective purity.
3. **The Trap of Search-Evaluation Coupling:**
   - An engine with a handcrafted classical evaluation cannot afford to search a mathematically pure tree because its NPS ($\approx 1.3\text{M NPS}$) and evaluation accuracy are insufficient to prune safely without shortcuts.
   - But when heuristic forward pruning is used as a shortcut, the search tree becomes brittle: any change to evaluation weights (backward pawns, outposts) disrupts the pruning cutoffs, causing search explosions or tactical blindness.
   - This mutual dependency is a dead end.

---

## 3. Formal Adjudication Ledger

| Candidate / Baseline | Git SHA / Archive | Single-Thread Role | Multi-Thread Role | Empirical Elo vs X7 (Fast) | Empirical Elo vs X7 (Slow) | Formal Milestone Status |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| **Janus Classical X7** | `b34e342` | **Qualified Baseline** | — | $0.0$ (Control) | $0.0$ (Control) | **RETAINED AS 1T BASELINE** |
| **Janus Classical X12** | `78ca3d5` | — | **Qualified Baseline** | — | — | **RETAINED AS 4T BASELINE** |
| **Janus Classical X22** | `e33f292` | Research Reference | — | $+0.0$ ($50.0\%$) | $+0.0$ ($50.0\%$) | **RETAINED AS RESEARCH REF** |
| **Janus Classical X23** | `39E87584...` | Candidate | Candidate | $-45.0$ | $-78.0$ | **REJECTED (P1.18)** |
| **Janus Classical X24** | `FBEAF907...` | Candidate | — | $-35.0$ | $-69.0$ | **REJECTED (P1.19)** |
| **Janus Classical X25** | `2C163B4A...` | Candidate | Candidate | $-14.0$ ($48.0\%$) | $-7.0$ ($49.0\%$) | **ARCHIVED (P1.20)** |
| **Janus Classical X26** | `0C2338DB...` | Candidate | Candidate | $-52.5$ ($42.5\%$) | $-92.5$ ($37.0\%$) | **REJECTED (P1.21)** |

---

## 4. Authorization

The Principal Computer Chess Engine Architect, Search Engineer, and Statistical Auditor hereby formally close Candidate X26 development and authorize immediate execution of **Phase 16: Classical Architecture Pivot Decision**.
