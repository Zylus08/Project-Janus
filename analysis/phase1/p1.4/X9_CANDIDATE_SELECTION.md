# Project Janus — Phase 1, Milestone P1.4
## Candidate Selection & Architecture Freeze: Janus Classical X9

**Author:** Principal Computer Chess Engineer, C++17 Search Architect, Independent Experimental Auditor  
**Lineage:** Janus Classical X  
**Selected Candidate:** Janus Classical X9  
**Baseline Control:** Janus Classical X7 (Qualified Baseline)  
**Branch:** `phase1/classical-janus`  
**Date:** 2026-11-10  
**Phase 1 Constraint:** Strictly Non-ML (Zero neural evaluation, zero learned weights, zero offline-fitted models)

---

### 1. Executive Summary & Selection Decision

Milestone P1.4 systematically evaluated eight feature-isolated configurations (B0 through B7) and four surgical optimization variants across fixed-depth suites, 4 distinct time controls (100ms, 250ms, 1000ms, 3000ms), and an expanded 31-position tactical corpus.

The empirical evidence established two foundational principles:
1. **The Singular Extension Liability:** Singular extensions and unpruned verification subtrees consume excessive search bandwidth under match time controls, causing a devastating $-1.0$ to $-1.9$ ply collapse in completed nominal depth that directly caused X8's $-52.5$ Elo regression.
2. **The Countermove Heuristic Superiority:** The Countermove Heuristic ($64 \times 64$ table) is the sole mechanism that delivers **Pareto-superior performance**:
   - Prunes 41,256 nodes (-2.69%) on standard diagnostic suites.
   - Extends completed nominal depth by **$+0.30$ plies** under 1000ms clock limits.
   - Boosts fixed-time solution accuracy to **62.5%** (highest of any engine tested).
   - Incurs zero verification latency and occupies only 8 KB in CPU L1 data cache.

**Formal Determination:**
The candidate selected for formal qualification testing is **Janus Classical X9**, configured as:
- **Baseline Foundation:** 100% of Classical X7's qualified algorithms (Staged Movegen, Quiescence SEE, NMP, RFP, Aspiration Windows, Continuation History H3, Dynamic LMR L3, Positional Evaluation E5).
- **Modernization Addition:** **Countermove Heuristic (M2)** active for all quiet moves.
- **Selectivity Exclusion:** Singular Extensions (S0), Multi-Cut (C0), and ProbCut (P0) disabled to protect nominal search depth.

---

### 2. Frozen Candidate Specifications & Artifact Hashes

| Artifact Path | File Size | SHA-256 Hash |
|---|---|---|
| `analysis/phase1/p1.4/control/janus_classical_x9.exe` | 375,296 bytes | `f61376a20acc04e612589ba98e386cc2780974f9ceb0abf5bee075e78355887d` |
| `analysis/phase1/p1.4/control/janus_classical_x9.dll` | 284,672 bytes | `947732bf88317e230e7e2351d18ae5a66cdd6cb60c1527a63cdcba69520e9a1f` |
| `analysis/phase1/p1.4/control/janus_classical_x9.cpp` | 152,770 bytes | `14c84f1a77715ea74f066af299e587dcc6e34b35133ac4d1061d2c42ffaa9a19` |

#### Exact UCI Variant Configuration
```
UCI_Variant: X9
UCI_ContinuationHistory: H3 (1-ply + 2-ply conthist)
UCI_DynamicLMR: L3 (Depth-scaling threshold)
UCI_ClassicalEval: E5 (Tapered positional evaluation)
UCI_TacticalOrdering: M2 (Countermove Heuristic Only)
UCI_SingularExtensions: S0 (Off)
UCI_MultiCut: C0 (Off)
UCI_ProbCut: P0 (Off)
```

**Candidate Status:** **FROZEN & SUBMITTED FOR PHASE 7 QUALIFICATION**.

