# Milestone P1.17 Phase 4: Quiescence Correctness vs Performance Attribution

**Date:** November 14, 2026  
**Status:** Completed & Empirically Attributed  
**Branch:** `phase1/classical-janus`  
**Milestone HEAD:** `abd99c5`  

---

## 1. Executive Summary & Controlled Factorial Matrix

Milestone P1.17 Phase 4 isolated and individually measured the architectural components introduced in Candidate Janus Classical X21:
1. **Quiescence In-Check Evasion Generation & Stand-Pat Suppression (Policy Q1).**
2. **64K Direct-Mapped Pawn Hash Table.**

Using the controlled benchmark harness (`test_quiescence_attribution.py`), all three configurations were tested across 20 representative middlegame and tactical positions under identical fixed-time search budgets (100ms per position):

| Variant ID | Architecture Configuration | Evasions Generated? | Stand-Pat under Check? | Pawn Hash Enabled? | Total Nodes Searched | Average Depth (plies) | Full-Search NPS |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Q0** | Legacy Baseline (X7 / X20) | NO | YES (Illegal) | NO | 3,143,764 | **11.40** | 1,641,879 |
| **Q1** | Corrected Evasions Only | **YES** | **NO (Suppressed)** | NO | 2,570,988 | **10.90** | 1,337,815 |
| **Q2** | Candidate X21 (Q1 + Pawn Hash) | **YES** | **NO (Suppressed)** | **YES (64K)** | 2,834,588 | **11.05** | 1,479,514 |

---

## 2. Forensic Component Attribution

### Finding 1: The Cost of Chess Correctness (Q0 -> Q1)
- **NPS Impact:** $-18.5\%$ (1.64M down to 1.34M NPS).
- **Depth Impact:** $-0.50$ plies (11.40 down to 10.90 plies).
- **Mechanism:** In legacy Q0, when a leaf node was in check, the engine evaluated static `stand_pat`. If `stand_pat >= beta`, it instantly pruned the branch without generating a single move. If it did not cut off, it generated only captures (typically 0 or 1 move), immediately returning `stand_pat`.
- In Q1, the engine correctly recognizes check, suppresses stand-pat, calls `generate_legal_moves()`, and searches all legal evasions. This legitimate chess work increases the leaf branching factor and consumes node budget, resulting in $-0.50$ plies shallower main-search trees.

### Finding 2: The Exact Benefit of the Pawn Hash Table (Q1 -> Q2)
- **NPS Impact:** $+10.6\%$ in full alpha-beta search (1.34M up to 1.48M NPS), with $+52.1\%$ observed in isolated evaluation microbenchmarks.
- **Depth Impact:** $+0.15$ plies recovered (10.90 up to 11.05 plies).
- **Memory Footprint:** 1.0 MB (64K entries $\times$ 16 bytes).
- **Collision Rate:** $< 0.04\%$ across 2.8M nodes.
- **Finding:** Pawn hashing provides an unambiguous, thread-safe computational speedup that partially compensates for the computational cost of in-check evasion generation.

---

## 3. Search Decision & Stability Ledger

| Measurement | Legacy Q0 | Corrected Q1 | Candidate X21 (Q2) |
| :--- | :---: | :---: | :---: |
| **Checkmate Blindness at Leaves** | **Frequent (-84 cp)** | **ZERO (-29,000 cp)** | **ZERO (-29,000 cp)** |
| **Illegal Move Stand-Pat Prunes** | **Active** | **Eliminated** | **Eliminated** |
| **Best Move Agreement vs Depth 14** | 70.0% (14/20) | 80.0% (16/20) | **85.0% (17/20)** |
| **Time Forfeits / Search Timeouts** | 0 | 0 | 0 |
| **Mean Search Latency** | 98.4 ms | 98.6 ms | 98.5 ms |

**Conclusion:** The throughput gain from pawn hashing is real and reproducible. The depth deficit of Candidate X21 relative to Baseline X7 is the direct physical consequence of eliminating illegal stand-pat beta-cutoffs and properly exploring check evasions.
