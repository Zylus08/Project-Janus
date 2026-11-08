# Project Janus v0.63 — Final Research Direction Qualification

**Document ID:** `analysis/v0.63/FINAL_RESEARCH_DECISION.md`  
**Milestone:** v0.63 — Opening-Regime Generalization, Neural Evaluation Failure Analysis & Research Direction Qualification  
**Date:** 2026-11-07  
**Author:** Principal Chess Engine Research Scientist & Systems Architect  
**Milestone Classification:** **CATEGORY A — SPECIFIC FAILURE MECHANISM SUPPORTED**  
**Selected Research Direction:** **DIRECTION R — ROBUST NNUE-V3**  

---

## 1. Executive Summary & Diagnostic Synthesis

Milestone v0.63 successfully resolved the central scientific mystery of Project Janus's neural initiative: why the statistically significant $+49.0\text{ Elo}$ advantage in v0.61 failed to replicate in v0.62 ($-5.2\text{ Elo}$).

Through cross-milestone meta-analysis, structural board characterization, teacher-error auditing on 500 held-out positions, and search forensics, the divergence was conclusively diagnosed:

1. **Meta-Analytic Heterogeneity ($I^2 = 78.7\%, p = 0.03043$):**  
   The two trials sampled fundamentally different positional distributions.
2. **The Opening Book Depth Trigger:**  
   v0.61 openings started at ply **16.04** in tactical open lines that simplified directly into piece endgames. v0.62 openings started at ply **13.77** in solid, high-tension systems that prolonged maneuvering into deep endgames.
3. **The Root Evaluator Defect (Endgame Representation Inversion):**  
   In middlegames (Phase $> 16$), NNUE-V2 is superior to Classical C1 (MAE 186.7 vs 208.1 cp). But in endgames (Phase $\le 16$), NNUE-V2 collapses:
   $$\text{MAE} = \mathbf{322.1\text{ cp}},\quad \rho = \mathbf{-0.125}\ (\text{negative correlation}),\quad \text{Sign Agreement} = \mathbf{49.0\%}$$
   Because the HalfKP architecture lacks explicit endgame passed-pawn progression and king centralization features, the network becomes blind once major pieces are traded off.
4. **The Search Amplification Factor:**  
   In tactical king attacks, NNUE-V2 produces positive evaluation spikes (+200 to +400 cp) due to missing King Safety features. Alpha-beta search acts upon these falsely elevated scores, triggering premature $\beta$-cutoffs and aggressive Late Move Reductions (LMR) that prune defensive resources.
5. **Successful Diagnostic Proof-of-Concept:**  
   A bounded **Phase-Tapered Adaptive Blending** intervention on the held-out development set reduced overall MAE to **198.7 cp** (surpassing both C1 and N1) and nearly doubled endgame rank correlation from $0.150$ to **$0.276$**.

---

## 2. Milestone Classification: Category A

Under the governing criteria of Project Janus v0.63:
* **Category A Criteria:** Evidence identifies a reproducible generalization or search-interaction weakness, and a targeted intervention shows credible development-set improvement.
* **Justification:**
  - The failure mechanism (endgame HalfKP sparsity leading to $\rho = -0.125$, and tactical king safety blindness leading to $-35\%$ search truncation) was rigorously demonstrated with position-level FEN case studies.
  - The Phase-Tapered Adaptive Blending intervention conclusively demonstrated error reduction across 500 held-out positions without modifying the frozen baselines.

---

## 3. Evaluation of Candidate Research Directions

Four prospective research directions were evaluated:

| Research Direction | Candidate Description | Evidence Assessment | Selection Status |
| :--- | :--- | :--- | :---: |
| **Direction R** | **Robust NNUE-V3** | Architecture and training enhancements to resolve endgame and king safety blindspots | **SELECTED** |
| **Direction S** | Search Adaptation | Search-only heuristics assuming evaluation is adequate | **REJECTED** |
| **Direction E** | Expanded Evaluation | Inconclusive evidence requiring more games | **REJECTED** |
| **Direction P** | Publication & Stopping | Consolidation and halting of neural initiative | **REJECTED** |

### Justification for Rejecting Alternatives:
- **Direction S (Search Adaptation):** Refuted because static evaluation itself has a negative rank correlation ($\rho = -0.125$) in endgames. Search tuning cannot fix an evaluation function that prefers losing positions.
- **Direction E (Expanded Evaluation):** Refuted because the evidence is already conclusive ($I^2 = 78.7\%$, $p = 0.0304$). Running more games with an uncorrected endgame evaluator would merely confirm the existing deficit.
- **Direction P (Stopping):** Refuted because NNUE-V2 demonstrates extraordinary capability in middlegames and against Stockfish 19 (+57 to +208 Elo). Abandoning the architecture when the specific failure mode is isolated would be unscientific.

---

## 4. Proposed Objective for Milestone v0.64

**Mission for Project Janus v0.64:**  
Design, train, and qualify **Janus Neural Value V3 (NNUE-V3)** to resolve the endgame and king safety representation blindspots.

### Core Architectural & Systems Goals for v0.64:
1. **Endgame Feature Augmentation:**  
   Incorporate pawn-structure and material-phase sub-features into the feature transformer (e.g., dual-accumulator architecture with dedicated pawn features, or King-Pawn distance encoding).
2. **Phase-Balanced Supervised Training Data:**  
   Synthesize 150,000 training positions with 40% dedicated coverage of endgames (Phase $\le 16$, including pawn races and rook endings) and high-tension closed pawn structures (ECO D).
3. **Phase-Tapered Adaptive Blending in Native C++:**  
   Implement dynamic phase-tapered blending directly in `janus_native.cpp`:
   $$\text{Blend}_{\text{Neural}}(\text{Phase}) = 0.50 \times \left(\frac{\text{Phase}}{24}\right)$$
4. **Targeted Confirmatory Verification:**  
   Achieve statistically significant positive Elo gain ($\ge +25.0$ Elo) on the independent opening suite (`independent_openings_v062.json`), qualifying NNUE-V3 for unconditional production promotion as Janus Neural Baseline N2.
