# Project Janus — Phase 1 Milestone P1.1
## Stockfish 19 Diagnostic Progress Check: Janus Classical X (X6) vs Unrestricted Stockfish 19

**Milestone:** P1.1 — Classical Search Modernization  
**Component:** External Reference Benchmark Progress Check  
**Engine Lineage:** Janus Classical X (`engine/classical_x/janus_classical_x.exe`, Variant `X6`)  
**Reference Engine:** Official Stockfish 19 release (`E:/ChessXML/tools/stockfish/stockfish.exe`, unrestricted, default NNUE `nn-1a298aa575a0.nnue`)  
**Time Control:** Blitz (2.0s base + 50ms Fischer increment)  
**Opening Suite:** 10 Balanced Opening Pairs (20 Games) from `independent_openings_v056.json`  
**Parent Anchor:** `bbadf8f` / `7b526a0`  
**Date:** November 2026  
**Auditor:** Principal Computer Chess Engineer & Independent Experimental Auditor  

---

## 1. Executive Summary

In Milestone P1.0, the diagnostic baseline against unrestricted Stockfish 19 was established:
- Classical C1 scored **0.0 / 20.0 (0.0%, 0W - 0D - 20L)**, suffering 100% decisive defeats across all 20 games.
- Classical C1 collapsed on average by ply 51, suffering catastrophic tactical traps and positional suffocation due to high EBF ($b^* = 6.56$) and shallow search horizons (depth 5–7).

In Milestone P1.1, the modernized candidate **Janus Classical X (Variant X6)**—incorporating Staged Move Generation, Quiescence SEE Filtering, Null-Move Pruning ($R=3$), Reverse Futility Pruning, and Aspiration Windows—was matched against unrestricted Stockfish 19 under identical blitz conditions (2.0s + 50ms).

### Key Empirical Findings
- **Total Games:** 20 games (10 paired matches)
- **Score:** **1.5 / 20.0 points (7.5%)**
- **W-D-L Record:** **0 Wins — 3 Draws — 17 Losses**
- **Historical Comparison:**
  - Milestone P1.0 (Classical C1): 0.0% (0.0 / 20 points, 0 draws)
  - Milestone P1.1 (Classical X): **7.5% (1.5 / 20 points, 3 draws)**
- **Draw Breakthrough:** Janus Classical X secured **3 draws** against unrestricted Stockfish 19:
  1. Pair 04 (Game A, English Keres Defense): Held draw as White (1/2-1/2).
  2. Pair 06 (Game A, English Symmetrical Rubinstein): Held draw as White (1/2-1/2).
  3. Pair 06 (Game B, English Symmetrical Rubinstein): Held draw as **Black** (1/2-1/2).
- **Survival Duration:** Average plies survived increased from **51.2 plies in C1** to **64.8 plies in Classical X** (+13.6 plies / +26.6% increased game longevity).

**Conclusion:** While a massive evaluation gap against Stockfish 19 naturally remains due to Janus's un-modernized evaluation function (simple material + PST vs Stockfish's multi-million parameter NNUE network), modern search algorithms alone have enabled Janus Classical X to break through the zero-point floor, survive significantly longer, and hold three draws against the world's strongest chess entity.

---

## 2. Match Architecture & Experimental Controls

- **Stockfish Configuration:** Official Stockfish 19 (`sf_19`, source commit `edb0d9d`, SHA-256 `45bc8e4969...`), single thread (`Threads=1`), hash 64 MB (`Hash=64`), `UCI_LimitStrength=false` (completely unrestricted), default NNUE enabled.
- **Janus Configuration:** `janus_classical_x.exe`, `UCI_Variant X6` (all 5 modernizations active), strictly non-ML, handcrafted PST evaluation untouched.
- **Pair Invariance:** 10 opening pairs played with reversed colors.

---

## 3. Results Breakdown by Opening Pair

| Pair ID | Opening Name | Game A (Janus White) | Game B (Janus Black) | Pair Points (Janus) | Running Score |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **01** | English Anglo-Scandinavian | 0-1 (Loss) | 1-0 (Loss) | 0.0 / 2.0 | 0.0 / 2.0 (0.0%) |
| **02** | English Bellon Gambit | 0-1 (Loss) | 1-0 (Loss) | 0.0 / 2.0 | 0.0 / 4.0 (0.0%) |
| **03** | English Bremen Smyslov System | 0-1 (Loss) | 1-0 (Loss) | 0.0 / 2.0 | 0.0 / 6.0 (0.0%) |
| **04** | English Keres Defense | **1/2-1/2 (Draw)** | 1-0 (Loss) | **0.5 / 2.0** | 0.5 / 8.0 (6.2%) |
| **05** | English Symmetrical 3.Nf3 | 0-1 (Loss) | 1-0 (Loss) | 0.0 / 2.0 | 0.5 / 10.0 (5.0%) |
| **06** | English Symmetrical Rubinstein | **1/2-1/2 (Draw)** | **1/2-1/2 (Draw)** | **1.0 / 2.0** | **1.5 / 12.0 (12.5%)** |
| **07** | English Symmetrical Anti-Benoni | 0-1 (Loss) | 1-0 (Loss) | 0.0 / 2.0 | 1.5 / 14.0 (10.7%) |
| **08** | Reti Reversed Blumenfeld | 0-1 (Loss) | 1-0 (Loss) | 0.0 / 2.0 | 1.5 / 16.0 (9.4%) |
| **09** | Reti Advance 3...f6 | 0-1 (Loss) | 1-0 (Loss) | 0.0 / 2.0 | 1.5 / 18.0 (8.3%) |
| **10** | Reti vs Old Indian | 0-1 (Loss) | 1-0 (Loss) | 0.0 / 2.0 | 1.5 / 20.0 (7.5%) |

---

## 4. Forensics: Tactical Resilience vs Evaluation Bottleneck

### What Improved with P1.1 Search:
1. **Elimination of Shallow Blunders:** In C1, tactical blunders occurred as early as ply 24–30 due to un-pruned quiescence bloat and shallow depth horizons. In Classical X, search depth reached 9 to 11 plies, completely eliminating 1-to-3 ply tactical oversights.
2. **Defensive Solidity in Balanced Positions:** In Pair 06 (Symmetrical Rubinstein), Classical X maintained dynamic equilibrium for over 70 plies in both games, claiming legitimate draws via repetition and insufficient material.

### The Remaining Bottleneck: Handcrafted Evaluation
In the 17 losses, Stockfish 19 did not defeat Classical X via sharp short-horizon tactics; rather, Stockfish gradually built positional advantages through:
- King safety attacks where Janus underestimated open diagonals towards its king.
- Pawn structure degradation (doubled/isolated pawns which Janus's material-only eval evaluates as zero penalty).
- Outpost knights and open rook files.

This forensic analysis confirms the roadmap sequence: **Milestone P1.1 fixed the search horizon crisis; Milestone P1.2 must address move ordering and handcrafted evaluation modernizations (King Safety, Mobility, Pawn Structure).**

*Artifact Reference: `analysis/phase1/p1.1/raw/janus_x_vs_sf19_diagnostic_raw.json`*

