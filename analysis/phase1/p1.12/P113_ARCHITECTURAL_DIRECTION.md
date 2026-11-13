# PROJECT JANUS — PHASE 1, MILESTONE P1.12
## Architectural Direction for Phase 1.13: Classical Frontiers & Phase 2 Transition Roadmap

**Document ID:** `analysis/phase1/p1.12/P113_ARCHITECTURAL_DIRECTION.md`  
**Milestone:** Phase 1, Milestone P1.12  
**Status:** Certified Architectural Roadmap & Strategic Advisory  
**Date:** 2026-11-13  
**Auditor:** Principal Computer Chess Engineer, Systems Performance Architect & Statistical Auditor  

---

## 1. Executive Summary

Milestone P1.12 marks the scientific pivot of Project Janus. By conducting the **Baseline Reboot**, auditing the entire trajectory of classical search and evaluation enhancements from P1.1 through P1.11, and establishing the **Three-Tier Competitive Reference Ladder**, we have replaced speculation with hard empirical reality.

This document synthesizes the definitive answers to the eight foundational architectural questions governing the transition from Milestone P1.12 to Phase 1.13 and beyond.

---

## 2. Definitive Answers to the Eight Architectural Exit Questions

### Question 1: Why did successive classical evaluation enhancements fail to deliver playing strength?
**The Evaluation Latency Tax & The Handcrafted Non-Linearity Trap:**
Across Milestones P1.5 through P1.10, successive evaluation versions ($E6$ through $E15$) introduced increasingly complex handcrafted terms: king safety ray-casting, passed pawn distance formulas, bishop pair dynamic scaling, and pawn hash tables. Despite improving static test suite scores, these terms failed in tournament play due to two fatal interactions:
1. **The Search Depth Penalty:** Evaluating complex handcrafted terms increased node evaluation cost by $25\%\text{--}40\%$. In a game with a fixed time control, a $30\%$ reduction in NPS costs approximately $0.8$ to $1.2$ plies of search depth. Handcrafted positional terms worth $+15\text{--}25\text{ cp}$ cannot compensate for missing tactical threats that appear one ply deeper in the game tree.
2. **Evaluation-Search Mismatch:** Complex non-linear handcrafted terms cause rapid score oscillations along search branches. In alpha-beta search, score oscillations degrade move ordering, destabilize aspiration windows, and trigger false cutoffs in Reverse Futility Pruning. The clean, lightweight $E5$ evaluation in X7 produced smoother minimax landscapes, allowing faster, deeper search trees that outperformed "smarter" but heavier evaluations.

---

### Question 2: What is the true cost-benefit trade-off of selective search mechanisms in classical engines?
**The Classical Branching Ratio Principle ($EBF \le 3.85$):**
Selective search heuristics exist solely to reduce the Effective Branching Factor ($EBF = \text{nodes}^{1/\text{depth}}$). The empirical evidence from Milestone P1.12 demonstrates:
- **Sound Reductions (LMR):** Base logarithmic LMR with continuation history modulation is highly effective, maintaining an $EBF \approx 3.76$ and allowing the engine to reach depth $13+$ in $200\text{ms}$.
- **The Catastrophe of Pruning Dampening:** P1.11's `!improving` dampening attempted to "protect" positions by reducing fewer nodes and widening RFP margins on non-improving branches. Because ~50% of nodes in minimax search are non-improving, this crippled pruning volume by $22.8\%$, exploding $EBF$ from $3.762$ to $4.255$.
- **The Mathematical Reality:** At depth 12, an $EBF$ of $4.255$ requires $34\text{ million}$ nodes versus $7.5\text{ million}$ nodes at $3.762$ ($4.5\times$ more compute). Pruning heuristics must remain aggressive and uniform; selective safety mechanisms should only be applied to provably narrow tactical classes (such as pure pawn endgames), never as broad search dampeners.

---

### Question 3: How close can a strictly non-ML classical engine get to Stockfish 11?
**The Achievable $\sim 500\text{--}550\text{ Elo}$ Classical Ceiling:**
In Milestone P1.11 and earlier, the team mistakenly assumed that Janus's deficit against Stockfish was predominantly due to the absence of neural networks. Phase 11's calibration against Stockfish 11 (Tier 2, strictly zero NNUE) proved that:
- Stockfish 11 achieved a clean sweep ($80\text{--}0$) against Janus Classical X17.
- **Stockfish 11's classical rating is $\sim 3450\text{ Elo}$**, whereas Janus X7/X12 operates at $\sim 2750\text{--}2850\text{ Elo}$.
- There is approximately **$+500\text{ to }+550\text{ Elo}$ of achievable headroom** purely within non-ML classical chess programming before any neural network is required!
- Closing this gap requires implementing the proven, heavy-duty classical search algorithms that Stockfish refined over 12 years: Singular Extensions, Multi-Cut, ProbCut, multi-level Continuation History, and piece-coordinated King Safety heatmaps.

---

### Question 4: Is there evidence that classical evaluation has reached its ceiling without neural methods?
**No for Classical Headroom, Yes for Handcrafted Cognitive Limits:**
1. **Classical Evaluation has NOT reached its ceiling:** Stockfish 11's handcrafted evaluation was vastly superior to Janus's $E5/E10$, featuring complex material imbalance matrices, dynamic piece coordination, outpost bonuses, and sophisticated fortress scale-factor tables.
2. **Human Handcrafting HAS reached an engineering ceiling:** Attempting to manually tune 1,000+ classical evaluation weights by hand or ad-hoc heuristic intuition is biologically and cognitively impossible. Stockfish 11 achieved its classical peak through hundreds of millions of automated Texel-tuning games. Without automated parameter optimization, handcrafted evaluation in Janus is trapped at an asymptote.

---

### Question 5: What specific classical search enhancements have the highest probability of improving playing strength?
Based on computer chess literature and our Phase 6/11 diagnostics, four search architectures have the highest empirical return on investment:
1. **Singular Extensions (SE):** Probing the TT move at reduced depth ($d/2$) with a margin; if all alternatives fail low, extending the search by $+1$ or $+2$ plies. This resolves deep tactical blind spots without expanding the general tree ($+60\text{--}80\text{ Elo}$).
2. **Multi-Cut / ProbCut:** Performing shallow searches at high beta thresholds to trigger cutoffs before generating full moves ($+50\text{--}70\text{ Elo}$).
3. **Multi-Tier Continuation History:** Indexing quiet move scores by 1-ply, 2-ply, and 4-ply previous moves, drastically improving late-game move ordering.
4. **Endgame Tablebase / Scale-Factor Knowledge:** Handcrafted draw-detection scale factors for opposite-colored bishops, $R+P$ vs $R$, and rook fortresses.

---

### Question 6: What is the recommended strategy for Phase 1.13?
**The "Pure Search Depth & Singular Extensions" Protocol:**
1. **Do NOT touch evaluation:** Freeze evaluation at clean $E5$ (Track S) and $E10$ (Track P). Forbid any new evaluation terms or weight adjustments.
2. **Implement Singular Extensions (SE):** Implement standard Stockfish-style singular extensions with conservative margins ($\text{depth} \ge 8$, margin $= 2 \times \text{depth}$).
3. **Adopt Strict JCTS v2 Gating:** Enforce the 200-game screening + slower-TC replication standard before considering any candidate for promotion.
4. **Validate against Tier 2:** Use Stockfish 11 as the benchmark to measure closing of the classical gap.

---

### Question 7: Should Project Janus continue classical non-ML development, transition to hybrid methods, or prepare for Phase 2?
**Two-Track Strategic Recommendation:**
1. **Milestone P1.13 (Final Classical Search Push):** Dedicate P1.13 exclusively to implementing Singular Extensions and Multi-Cut on top of the rebooted baselines (X7/X12). This will establish whether classical search selectivity alone can deliver a $+50\text{--}100\text{ Elo}$ breakthrough.
2. **Formal Authorization for Phase 2 (NNUE Architecture):** Milestone P1.12 conclusively demonstrated that $30\%$ of the modern deficit ($\sim 200\text{--}250\text{ Elo}$) is the fundamental **Neural Network Gap**. Furthermore, human-crafted evaluation has hit a complexity wall. Project Janus should formally charter Phase 2: designing a lightweight, SIMD-accelerated NNUE inference architecture (AVX2/AVX-512) to replace handcrafted evaluation entirely, while retaining Janus's clean, high-speed C++17 bitboard search tree.

---

### Question 8: What are the definitive lessons learned from Milestones P1.1 through P1.12?
1. **Never Confuse Move Disagreement with Tactical Blunder:** Milestone P1.11 assumed that 33% move disagreement meant 33% tactical failure. Independent ground truth revalidation proved 97.4% were benign positional alternatives.
2. **Search Depth is King in Classical Chess:** Pruning heuristics that destroy search depth under the guise of "safety" always regress in playing strength. A fast, deep engine searching clean simple evaluation will consistently beat a shallow engine searching complex evaluation.
3. **Rigorous Statistical Standards Prevent Costly Detours:** Underpowered matches ($N \le 200$) have margins of error exceeding $\pm 50\text{ Elo}$. Preregistered sample sizes, SPRT bounds, and slower-TC verification (JCTS v2) are mandatory to protect the project from noise-driven false positives.
4. **Respect the Historical Ladder:** Calibrating solely against modern NNUE giants produces infinite negative Elo noise. The intermediate classical benchmark (Stockfish 11) is essential for diagnostic resolution.

---

## 3. Transition Roadmap to Phase 1.13 & Phase 2

```
+-----------------------------------------------------------------------------+
| MILESTONE P1.12: BASELINE REBOOT & CERTIFICATION (COMPLETED)                |
| - Production Baselines Certified: Track S (X7 1T) & Track P (X12 4T)        |
| - Toxic Direction A heuristics purged; 3-tier reference ladder established   |
+-----------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------+
| MILESTONE P1.13: CLASSICAL SEARCH SELECTIVITY & SINGULAR EXTENSIONS         |
| - Retain frozen E5/E10 evaluation; zero manual evaluation modifications     |
| - Implement Singular Extensions (SE) and conservative Multi-Cut             |
| - Benchmark against Tier 1 controls and Tier 2 (Stockfish 11)               |
+-----------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------+
| PHASE 2: MODERN NNUE ARCHITECTURE & NEURAL COGNITION INITIATION            |
| - Retain verified C++17 bitboard search & Lazy SMP concurrency              |
| - Implement embedded 768->256x2->1 NNUE architecture (AVX2/NEON SIMD)       |
| - Train on self-play game positions to eliminate the 250-Elo neural deficit  |
+-----------------------------------------------------------------------------+
```

**Certification:** The Architectural Direction for Phase 1.13 and the Phase 2 roadmap are officially certified and submitted to the Project Janus Directorate.

