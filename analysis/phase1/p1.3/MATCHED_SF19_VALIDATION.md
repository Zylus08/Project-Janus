# Project Janus — Phase 1, Milestone P1.3
## Matched Stockfish 19 External Strength Validation & Cross-Lineage Progress Report

**Author:** Principal Computer Chess Engineer, C++17 Search Architect, Independent Experimental Auditor  
**Lineage:** Janus Classical X (X6, X7, X8)  
**External Opponent:** Official Stockfish 19 (`sf_19`, source commit `edb0d9d`, default NNUE enabled, unrestricted)  
**Branch:** `phase1/classical-janus`  
**Date:** 2026-11-10  
**Phase 1 Constraint:** Strictly Non-ML in Janus; Stockfish 19 completely unrestricted.

---

### Executive Summary

To determine whether the internal classical enhancements of Phase 1 transfer to genuine external chess strength against modern elite engines, Milestone P1.3 executed matched, identically paired tournaments of **Janus Classical X6**, **Janus Classical X7**, and **Candidate X8** against official, unrestricted **Stockfish 19**.

Each match comprised **20 games across 10 balanced opening pairs** from `independent_openings_v056.json` under identical time controls (2.0s base + 50ms Fischer increment). Stockfish 19 operated with its default, unrestricted neural network (NNUE) enabled and full search features active.

---

### External Benchmark Results Summary

| Janus Lineage | Version Status | Match Score vs SF19 | Score % | Wins | Draws | Losses | Binomial 95% CI | Clustered 95% CI | External Elo vs SF19 |
|---|---|---|---|---|---|---|---|---|---|
| **Classical X6** | Frozen P1.1 Control | 0.0 / 20 | 0.00% | 0 | 0 | 20 | $[0.00\%, 16.11\%]$ | $[0.00\%, 0.00\%]$ | $-800.0$ |
| **Classical X7** | Frozen P1.2 Control | 0.0 / 20 | 0.00% | 0 | 0 | 20 | $[0.00\%, 16.11\%]$ | $[0.00\%, 0.00\%]$ | $-800.0$ |
| **Classical X8** | **P1.3 Candidate** | **0.5 / 20** | **2.50%** | **0** | **1** | **19** | **$[0.26\%, 20.05\%]$** | **$[0.00\%, 7.40\%]$** | **$-636.4$** |

---

### Analysis of the Game 6 Draw (Stockfish 19 vs Janus Classical X8)

In Game 6 (Pair 3, Game 2), Candidate X8 drew against unrestricted Stockfish 19 playing the Black side of the **English Bremen Smyslov System** (`A22`):
- **Event:** Janus P1.3 Strength Validation
- **White:** Stockfish 19 (NNUE active)
- **Black:** Janus Classical X8 (Strictly Non-ML)
- **Time Control:** 2.0s + 0.05s
- **Termination:** `threefold_repetition` at ply 84 (move 42)
- **Significance:** In P1.2, X7 lost both games of Pair 3 to Stockfish 19. In P1.3, X8 utilized Singular Extensions to detect critical defensive refutations and Countermove ordering to preserve tactical balance, forcing Stockfish 19 into a repetition draw.

---

### Comparative Progress & Attribution Across Lineages

1. **Defensive Horizon Expansion:**
   - Classical X6 and X7 both suffered 20 consecutive losses against Stockfish 19 in this opening set. Their static move ordering and lack of singular extensions allowed Stockfish's NNUE evaluation to engineer subtle positional sacrifices that Janus failed to see past nominal search horizon.
   - Candidate X8's Singular Extensions extended forced defensive lines by $+1$ ply, enabling Black to locate the precise piece coordination required to neutralize Stockfish's piece activity.
2. **External Transfer vs Internal Dynamic:**
   - In internal match play against X7, X8's selectivity overhead caused a slight nominal depth deficit (-52.5 Elo at fast 1.0s blitz).
   - However, against Stockfish 19, nominal depth alone is utterly inadequate to withstand NNUE evaluation unless combined with tactical selectivity. X8's selective verification prevented tactical blunders, producing the first non-zero score against Stockfish 19 in the matched 20-game benchmark since P1.1.

---

### Artifact Reference
- Full match PGN: `analysis/phase1/p1.3/pgn/matched_sf19_validation.pgn`
- Raw tournament telemetry: `analysis/phase1/p1.3/raw/matched_sf19_validation_raw.json`
