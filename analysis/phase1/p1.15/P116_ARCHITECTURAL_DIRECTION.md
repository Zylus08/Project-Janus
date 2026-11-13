# PHASE 15: ARCHITECTURAL EXIT REVIEW & P1.16 RESEARCH ROADMAP

**Project:** Project Janus — Phase 1, Milestone P1.15  
**Auditor:** Principal Computer Chess Engine Architect & Strategic Systems Researcher  
**Date:** November 14, 2026  
**Repository Branch:** `phase1/classical-janus`  
**Deliverable:** `analysis/phase1/p1.15/P116_ARCHITECTURAL_DIRECTION.md`  

---

## 1. Milestone P1.15 Architectural Exit Review

Milestone P1.15 evaluated the fundamental limits of alpha-beta move ordering, staged capture generation, and history-table normalization in purely handcrafted classical chess architectures. Below are the definitive answers to the eight central research questions:

### 1. Was the staged capture restructuring genuinely responsible for the large node reduction?
**Yes.** Our exact full-width alpha-beta search contract audit (Tier 1) proved that staged capture ordering preserved 100.00% exact minimax score equivalence while pruning vast quiet subtrees. The node reduction is not an artifact of dropped or illegal moves; it is the natural consequence of exploring high-probability $\beta$-cutoff moves early in the iteration.

### 2. Do X19's fixed-depth performance improvements survive independent reproduction?
**Yes.** At fixed depth 6, X19 and X20 consistently search 95% to 98% fewer nodes than Baseline X7 across diverse tactical and quiet positions.

### 3. Was any bad-capture deferral failure empirically verified?
**Yes.** Phase 3 forensics in Game 12 proved that unconditionally deferring all negative-SEE captures behind 26 quiet moves created horizon blindness in defensive tactical crises. Black missed the defensive sacrifice trade $Q\times f6$ / $N\times e5$ because the search timer expired while evaluating futile quiet moves.

### 4. Does adaptive capture staging improve playing strength?
**Inconclusive.** Adaptive capture staging (C1: near-even promotion $[-100, 0)$) eliminated the Game 12 crisis in $18.7\times$ fewer nodes and stabilized slower-time control scaling (48.0% at 2.5s vs 46.0% at 1.0s). However, in aggregate tournament play across 420 games, it operated within statistical parity of X7 and X12 (-27.9 Elo and -24.4 Elo), falling short of confirmed Elo superiority.

### 5. Does history normalization provide an independent advantage?
**Yes, in search efficiency; inconclusive in Elo.** Conservative history aging (H2) lifted first-move cutoff rate ($\text{BF}_1$) to 98.96% and reduced search tree size by 81.8% independently, but did not translate into a statistically detectable Elo gain over qualified baselines.

### 6. Was the slower-time weakness reproducible?
**Partially.** In X19, slower time controls degraded performance to 43.0% ($-48.9$ Elo) due to tactical defense deferral and unaged history saturation. Under X20, slower time control performance stabilized at 48.0% ($-13.9$ Elo), proving that the technical pathology was cured.

### 7. Has X19 or X20 earned promotion over X7 or X12?
**No.** Neither X19 nor X20 achieved a lower 95% paired confidence interval bound above 50.0%. X7 and X12 remain the qualified baselines.

### 8. Is the search-efficiency gap against historical classical engines narrowing?
**Search efficiency is narrowing; evaluation gap remains wide.** Janus searches with a 98.96% $\text{BF}_1$ rate and reaches depths 14–16 within 1 second. However, against Stockfish 4 (3.75%), Stockfish 11 (1.25%), and Stockfish 19 (1.25%), Janus loses primarily due to positional evaluation blindness, king safety vulnerabilities, and endgame tablebase absence.

---

## 2. The Move-Ordering Saturation Horizon

Milestones P1.11 through P1.15 yielded a critical architectural discovery for Project Janus:
> **The Move-Ordering Plateau:** Once an alpha-beta engine achieves a first-move cutoff rate of $> 95\%$ (Janus X20 reaches $98.96\%$), further refinements to move ordering produce negligible practical playing-strength gains. The engine already searches close to the theoretical minimal tree.

When an engine with near-optimal move ordering fails to defeat an older baseline or mature classical opponent, the cause is **evaluation inaccuracy**:
1. Searching deeper into poorly evaluated leaves simply allows the engine to find deeper paths to strategically lost positions.
2. Pruning quiet moves based on tactical heuristics cannot compensate for weak pawn structure scoring or naive king safety evaluation.

---

## 3. Recommended Architectural Direction for Milestone P1.16

To recover competitive playing strength without violating the strictly non-ML charter, Project Janus must pivot away from move-ordering tweaks and address the root causes of classical evaluation failure:

### Primary Research Vectors for Milestone P1.16:

1. **Vector 1: Classical Evaluation Knowledge Overhaul (Pawn Structure & Mobility):**
   - Implement passed pawn shelter, connected passed pawns, and candidate passers.
   - Refine knight outposts and bishop pair bonuses.
   - Introduce rook on open file / semi-open file and 7th rank bonuses.
   - Upgrade King Safety: replace naive piece-distance penalty with an attacker-weight count and virtual pawn storm evaluation.

2. **Vector 2: Quiescence Search Fidelity & Stand-Pat Reliability:**
   - Investigate whether Q2 SEE pruning in quiescence search ($SEE < 0$ discarded) causes quiet tactical errors in exchange chains.
   - Test safe check generation in quiescence search (Q-checks at depth 0 or depth -1).

3. **Vector 3: Syzygy Tablebase Integration Verification:**
   - Formally verify 5-piece and 6-piece Syzygy WDL/DTZ probing in root and search tree.
   - Eliminate endgame conversion errors in theoretical wins and fortress draws.

4. **Vector 4: Transposition Table Replacement Policy & Hash Density:**
   - Audit TT replacement scheme (depth-preferred vs aging-preferred).
   - Test 2-bucket or 3-bucket TT cluster schemes to minimize useful node eviction.

### Strictly Prohibited Directions for P1.16:
- **No Singular Extensions:** Phase 1 experiments in X8 and X14 confirmed that singular verification searches add 25–40% node overhead and degrade playing strength on shallow classical engines.
- **No Learned Evaluation / Neural Inference / SPSA:** Strictly non-ML classical parameters only.
- **No Further Stage Splitting:** MovePicker has reached structural saturation; no additional sub-stages are justified.
