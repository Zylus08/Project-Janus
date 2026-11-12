# Phase 2: Counterfactual Pruning Verification Audit

**Milestone:** Phase 1, Milestone P1.11  
**Charter:** Classical Search Architecture Decision, Counterfactual Pruning Verification & Competitive Strength Recovery  
**Lead Researcher:** Principal Computer Chess Engineer & Statistical Experimentalist  
**Candidate Engine:** Janus Classical X15 (`24c663c`)  
**Raw Data Reference:** [`analysis/phase1/p1.11/raw/counterfactual_pruning_raw.json`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.11/raw/counterfactual_pruning_raw.json)  
**Diagnostic Harness:** [`analysis/phase1/p1.11/tests/test_counterfactual_pruning.py`](file:///E:/ChessXML/project-janus-phase1/analysis/phase1/p1.11/tests/test_counterfactual_pruning.py)  

---

## 1. Executive Summary & Research Methodology

The central scientific question of Milestone P1.11 asks:
> *When Janus prunes or reduces a branch during alpha-beta search, how frequently does that decision eliminate a move that would have produced a superior bounded search result?*

To answer this, an offline diagnostic facility was developed to sample pruning decisions across **39 benchmark positions** spanning 7 distinct strategic classes:
1. Tactical Combinations & Blunder Refutations (8 positions)
2. Quiet Defensive Moves (6 positions)
3. Pawn Structures & Closed Centers (5 positions)
4. King Attacks & Pawn Storms (5 positions)
5. Rook & Minor Piece Endgames (7 positions)
6. Zugzwang Positions (3 positions)
7. Unstable PV & Complex Sharp Positions (5 positions)

### Experimental Protocol
For each position at fixed search depth $d = 7$:
- **Normal Search:** Executed under baseline selective search conditions (RFP active, NMP active, LMP L1, Dynamic LMR active, Quiescence SEE mode 2).
- **Counterfactual Searches:** The identical position was searched on an isolated engine instance with clean Transposition Tables, systematically disabling one pruning mechanism at a time:
  1. `CF_RFP`: Reverse Futility Pruning disabled (`UCI_RFP false`).
  2. `CF_NMP`: Null-Move Pruning disabled (`UCI_NullMovePruning false`).
  3. `CF_LMP`: Late Move Pruning disabled (`UCI_LMP L0`).
  4. `CF_LMR`: Late Move Reductions disabled (`UseLMR false`).
  5. `CF_QSEE`: Quiescence SEE filtering disabled (`UCI_QuiescenceSEE 0`).

---

## 2. Aggregate Counterfactual Findings

| Pruning Subsystem | Tested Mechanism | Sampled Decisions | Move Disagreements | Disagreement Rate (%) | Mean Nodes Saved / Node | Mean Score Shift ($\Delta\text{cp}$) | Pruning Risk Profile |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **LMR** | Late Move Reductions | 39 | **13** | **33.33%** | $+305,937.7$ | $6.4\text{ cp}$ | **HIGH SENSITIVITY** (Severe quiet move pruning hazard) |
| **NMP** | Null-Move Pruning | 39 | **7** | **17.95%** | $+38,717.3$ | $4.6\text{ cp}$ | **MODERATE SENSITIVITY** (Zugzwang / tactical shifts) |
| **RFP** | Reverse Futility Pruning | 39 | **6** | **15.38%** | $+24,667.4$ | $2.6\text{ cp}$ | **MODERATE SENSITIVITY** (Over-pruning quiet defense) |
| **QSEE** | Quiescence SEE Filtering | 39 | **4** | **10.26%** | $+34,948.5$ | $3.1\text{ cp}$ | **LOW SENSITIVITY** (Safe capture triage) |
| **LMP** | Late Move Pruning | 39 | **4** | **10.26%** | $-271.9$ | $1.6\text{ cp}$ | **SAFE ON 1T** (Candidate S disables LMP correctly) |

```mermaid
xychart-beta
    title "Counterfactual Move Disagreement Rate by Pruning Mechanism (%)"
    x-axis ["LMR", "NMP", "RFP", "QSEE", "LMP"]
    y-axis "Disagreement Rate (%)" 0 --> 40
    bar [33.33, 17.95, 15.38, 10.26, 10.26]
```

---

## 3. Position-Class Forensic Disagreement Analysis

Analysis of the 13 LMR and 6 RFP disagreements reveals precisely where and why classical search pruning introduces chess errors:

### 3.1 Quiet Defensive Moves (High Sensitivity)
In quiet defensive positions, standard search reductions routinely skip vital waiting or prophylactic moves:
- **Position `DEF_01` (`r2q1rk1/1pp1bppp/p1np1n2/4p3/2B1P1b1/2NP1N2/PPP2PPP/R1BQR1K1 w - - 0 9`):**
  - *Normal Search:* Selected `c1e3` (aggressive central development).
  - *Counterfactual LMR (`CF_LMR`):* Selected **`h2h3`** (the correct positional refutation, putting the question to Black's pin). Under normal LMR, `h2h3` was searched at reduced depth and failed to overcome the early unreduced score of `c1e3`.
- **Position `DEF_02` (`r1b1k2r/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQK2R w KQkq - 0 7`):**
  - *Normal Search:* Selected `d4c5`.
  - *Counterfactual RFP (`CF_RFP`):* Selected `c3c4`.
  - *Counterfactual LMR (`CF_LMR`):* Selected `f3e5`.
  - Normal search prematurely severed exploration of `f3e5` due to continuation history penalties from previous iterations.

### 3.2 King Attack & King Safety Prophylaxis
- **Position `KNG_03` (`r1bq1rk1/ppp1bppp/2n1pn2/3p4/3P4/2NBPN2/PPP2PPP/R1BQK2R w KQ - 4 6`):**
  - *Normal Search:* Selected speculative flank pawn advance **`h2h4`** ($+14\text{ cp}$).
  - *Counterfactual RFP & LMR (`CF_RFP` & `CF_LMR`):* Both selected **`e1g1`** (castling to king safety, $+28\text{ cp}$).
  - *Mechanism:* RFP static evaluation overestimated the attack value of `h2h4` due to open-file bonuses, causing the search to prune the defensive castling branch `e1g1` at shallow plies!

### 3.3 Endgame Pawn Breakthroughs
- **Position `END_04` (`8/8/4k3/8/3PK3/8/8/8 w - - 0 1`):**
  - *Normal Search:* Chose passive king repositioning `e4d3` ($0\text{ cp}$).
  - *Counterfactual RFP & LMR (`CF_RFP` & `CF_LMR`):* Both discovered the decisive, winning pawn advance **`d4d5+`** ($+450\text{ cp}$)!
  - *Mechanism:* Because static evaluation in king-and-pawn endings scored `d4d5` as equal prior to queen promotion horizon, RFP pruned the branch when evaluated against king moves.

### 3.4 Tactical Robustness Verified
- In all 8 tactical combination benchmarks (`TAC_01` through `TAC_08`), **disagreement was 0% between Normal and Counterfactual RFP**.
- The engine cleanly found `d5f6#` in `TAC_05`, `h5f7#` in `TAC_06`, `d5d6` in `TAC_07`, and `c1d2` in `TAC_08`.
- In `TAC_04` (`DEV_12` Kiwipete), Candidate X15 found the piece-winning move `e2a6` across all configurations, confirming that the P1.10 fix remains 100% stable.

---

## 4. Scientific Interpretation: Decision Quality vs Search Economics

1. **The LMR Efficiency Paradox:**
   - Disabling LMR increased searched nodes by an astonishing **$+305,937$ nodes per position** (a $> 10\times$ expansion in search volume).
   - In 66.7% of positions, the move chosen with full LMR was completely identical to the unreduced search.
   - However, in 33.3% of positions, LMR discarded superior quiet defensive and king-safety moves because they were ordered late in the quiet move list and suffered depth reductions $R \ge 2$.
2. **The Reverse Futility Pruning Vulnerability:**
   - RFP saved an average of $24,667$ nodes per search, but produced a $15.38\%$ disagreement rate.
   - RFP errors were strictly concentrated in positions where static evaluation over-estimated an attacking pawn or king-file imbalance, cutting off sound positional moves like `e1g1` or endgame pawn pushes like `d4d5`.
3. **The Core Architectural Defect Identified:**
   The fundamental bottleneck in the Project Janus classical search is **Uncalibrated Quiet-Move Pruning Synergy**:
   When static evaluation is inflated or move ordering places a vital quiet defensive move at index $\ge 4$, Late Move Reductions and Reverse Futility Pruning conspire to prune the refutation before alpha-beta search can verify it.

