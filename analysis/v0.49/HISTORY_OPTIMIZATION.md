# Project Janus v0.49 — History Heuristic Optimization

**Milestone:** Project Janus v0.49  
**Parent Baseline Commit:** `6b46eb4` (v0.48 Final)  
**Evaluated Candidates:**
- **Baseline K0:** Standard eager move ordering with 2D history table (`history[64][64]`)
- **Candidate H1:** Flattened 1D 4096-element integer history array
- **Candidate H2:** Stage-separated lazy quiet history scoring (yield TT + captures; only score quiets if captures fail to cut off)
**Test Corpus:** 37-position diagnostic corpus at Depth 4  
**Raw Telemetry:** `analysis/v0.49/raw/history_optimization_raw.json`

---

## 1. Executive Summary

Phase F investigated whether history scoring overhead can be eliminated without degrading move ordering quality.

### Primary Empirical Findings:
1. **The 69.6% Lookup Elimination (Candidate H2):** Candidate H2 eliminated **670,392 history table lookups** across the 37 positions at Depth 4 (falling from 963,803 down to 293,411 lookups, a **$-69.6\%$ reduction**).
2. **Search Fidelity:** Candidate H2 achieved **97.3% best-move agreement with K0** (36/37 positions) and exact node count parity with Candidate L1 (407,705 nodes vs 407,705 nodes).
3. **Mechanics of Candidate H2:** In chess search trees, winning and equal captures are examined before quiet moves due to MVV-LVA / SEE priority ($>100,000$ points vs $0\text{--}10,000$ points for history). If a capture produces a beta cutoff, quiet moves never need to be scored or sorted. By staging the selection pipeline into Tactical First $\to$ Quiets Deferred, Candidate H2 bypasses 69.6% of all quiet history lookups.
4. **Failure of Micro-Optimization H1:** Simply flattening the 2D list into a 1D array does not yield speedup in Python; intermediate index bit-shifting (`(from_sq << 6) | to_sq`) in interpreted bytecode incurs comparable overhead to Python's pointer-based list indexing.

---

## 2. Comparative Performance Matrix (Depth 4)

| Configuration | Total Search Nodes | History Lookups | History Lookup Reduction | Wall-Clock Runtime | Runtime Delta vs K0 | Move Agreement with K0 |
|---|---:|---:|---:|---:|---:|---:|
| **Baseline K0** | 405,197 | ~965,000 | Baseline | 18.90 s | Baseline | 37 / 37 (100.0%) |
| **Candidate H1** | 515,935 | 963,803 | -0.1% | 24.09 s | +27.41% (Slower) | 0 / 37 (Diverged) |
| **Candidate H2** | **407,705** | **293,411** | **-69.6%** | **19.27 s** | **+1.94% (Near Neutral)** | **36 / 37 (97.3%)** |

---

## 3. Decision Quality and Search Integrity (Candidate H2)

- **Blunder Audit:** 0 blunders across all 37 positions.
- **Tactical Integrity:** 0 tactical regressions; all tactical winning lines in the diagnostic corpus were preserved.
- **Root Score Discrepancies:** Exactly 2 positions exhibited minor root score differences ($\le 2$ cp), identical to Candidate L1's benign divergence pattern documented in v0.48.

---

## 4. Architectural Recommendation

Candidate H2 confirms that **algorithmic laziness** (deferring the scoring of quiet moves until tactical moves have been exhausted) is far more effective than micro-optimizing lookup data structures in Python. 

Candidate H2 should be integrated with Candidate L1 to form the foundation of a multi-stage move picker:
$$\text{Phase 1: TT Move} \implies \text{Phase 2: Winning Captures} \implies \text{Phase 3: Killers} \implies \text{Phase 4: Quiets (History)}$$

