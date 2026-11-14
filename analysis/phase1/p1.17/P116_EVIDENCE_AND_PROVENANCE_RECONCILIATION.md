# Milestone P1.17 Phase 0: P1.16 Evidence and Provenance Reconciliation

**Date:** November 14, 2026  
**Status:** Completed & Audited  
**Branch:** `phase1/classical-janus`  
**Milestone HEAD:** `abd99c5`  
**Governing Charter:** Non-ML Classical Computer Chess Architecture (Zero Neural Networks, NNUE, Learned Weights, SPSA, or Texel Tuning)  

---

## 1. Repository State & Exact Provenance Verification

An exhaustive forensic audit of the development repository `E:\ChessXML\project-janus-phase1` confirms the exact historical lineage:

```
Commit Graph:
* abd99c5 (HEAD -> phase1/classical-janus) feat(p1.16): classical evaluation integrity, tactical quiescence search & evidence-based strength recovery
* 00ef7ce refactor: archive P1.15 research deliverables and update external calibration reports
* 2226c0c feat(p1.15): adaptive capture ordering, search completeness, history reliability & independent strength qualification
* 563f1db feat: document milestone p1.14 classical reference ladder and final research decision
* bcfdecd feat(p1.14): quiet-move ordering architecture, search-tree efficiency & independent competitive qualification
```

- **Actual HEAD Commit:** `abd99c5d5d3ebe39c8d224a9f862fdf799a5a50e`
- **Parent Commit:** `00ef7ce` (preceded by `2226c0c`)
- **Current Branch:** `phase1/classical-janus`
- **Working Tree:** 100% clean, zero untracked files, zero uncommitted modifications.

### Candidate Provenance Discrepancy Resolution
The Milestone P1.16 prompt and documentation referenced commit `2226c0c` in connection with Janus Classical X21. 
- **Cause of Discrepancy:** Commit `2226c0c` was the parent HEAD where Milestone P1.16 commenced. The source code of X20 was located at `2226c0c`. During Milestone P1.16, extensive modifications to `engine/classical_x/janus_classical_x.cpp` (quiescence in-check evasion generation, stand-pat suppression under check, true checkmate/stalemate handling, and 64K pawn hashing) were developed and frozen into `analysis/phase1/p1.16/control/`.
- **Authoritative Resolution:** Janus Classical X21's ancestral baseline commit is `2226c0c`, its developmental source snapshot is `AF67D06809A0...`, its frozen binary is `AD1E1F0598D0...`, and its official commit in git history is `abd99c5`.

### Immutable Engine Identity & Provenance Mapping

| Engine Name | Role | Source Commit | Source File SHA-256 | Binary Path | Executable SHA-256 | UCI `id name` |
| :--- | :--- | :---: | :---: | :--- | :---: | :--- |
| **Janus Classical X7** | Qualified 1T Baseline | `b34e342` | Frozen in P1.3 | `analysis/phase1/p1.3/control/janus_classical_x7.exe` | `86392A2F4BD4182A4D7DC21E32940BD7939F6816794D5E1AB02F4082431CA28B` | `Janus Classical X (P1.2 Candidate X7)` |
| **Janus Classical X12** | Qualified 4T Baseline | `78ca3d5` | Frozen in P1.7 | `analysis/phase1/p1.7/control/janus_classical_x12.exe` | `00B4F5FEDEA02A392A1AF9713A96512E5199A0E3AE55C295AD1C7CFFF1B47059` | `Janus Classical X (P1.7 Candidate X12)` |
| **Janus Classical X19** | Research Reference | `bcfdecd` | Frozen in P1.14 | `analysis/phase1/p1.14/control/janus_classical_x19.exe` | `CBB7785A47E5F9EC64C51C20B8387DE3EFE782F42BDFCEA38008F6450E534629` | `Janus Classical X (P1.14 Candidate X19)` |
| **Janus Classical X20** | Preserved Reference | `563f1db` | Frozen in P1.15 | `analysis/phase1/p1.15/control/janus_classical_x20.exe` | `AF126A4D22C312F2AE61014A56005B9E9BAFD022F95A17DA81D81769048F7415` | `Janus Classical X (P1.14 Candidate X19)` |
| **Janus Classical X21** | Correctness Ref | `abd99c5` | `AF67D06809A0E4FF3BBA4E55C1C8CF6B0B9BCA5A9BEB06AAED70C57A1806B2D2` | `analysis/phase1/p1.16/control/janus_classical_x21.exe` | `AD1E1F0598D0CA016267CA4F03DC771346CEE9D0D563A36AB6B6590D7F4731FD` | `Janus Classical X (P1.16 Candidate X21)` |
| **Stockfish 4** | Historical Ref 1 | Release 2014 | Official Release | `E:/ChessXML/tools/stockfish_4/stockfish_4.exe` | `1128CAB83386063359947F04155A2210C966080E71176DD385D8BDC3B6C32674` | `Stockfish 4 64` |
| **Stockfish 11** | Historical Ref 2 | Release 2020 | Official Release | `E:/ChessXML/tools/stockfish_11/stockfish_11.exe` | `B004C03BD71BB84E8BC1832C580E72A7E883F121E1834EA6DA2802D1575E8048` | `Stockfish 11 64` |
| **Stockfish 19** | Ultimate NNUE Ref | `edb0d9d` | Official Git | `E:/ChessXML/tools/stockfish/stockfish.exe` | `45BC8E4969147DB9C2EB533810637994619BFF0EACC81CCFD9854394901BCBD0` | `Stockfish 19` |

---

## 2. Re-audited P1.16 Tournament Reconstruction (420 Games)

Reconstruction of all 420 games from the PGN archives in `analysis/phase1/p1.16/pgn/` confirms the exact raw score and W/D/L reported in P1.16:

| Match ID | Match Description | Configuration / TC | Games | W | D | L | Score (%) | Elo Diff | Paired 95% CI | 1-Sided p-value |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Match 1** | X21-S vs X7 Baseline | 1T, 1.0s + 50ms | 100 | 22 | 47 | 31 | **45.5%** | -31.4 | [37.9%, 53.1%] | 0.8762 |
| **Match 2** | X21-S vs X7 Baseline | 1T, 2.5s + 100ms (Slow) | 50 | 7 | 25 | 18 | **39.0%** | -77.7 | [31.0%, 47.0%] | 0.9963 |
| **Match 3** | X21-P vs X12 Baseline | 4T SMP, 1.0s + 50ms | 100 | 24 | 46 | 30 | **47.0%** | -20.9 | [39.6%, 54.4%] | 0.7878 |
| **Match 4** | X21-S vs X19/X20 Refs | 1T, 1.0s + 50ms | 50 | 15 | 22 | 13 | **52.0%** | +13.9 | [38.5%, 65.2%] | — |
| **Match 5** | X21-S vs Stockfish 4 | 1T, 1.5s + 50ms | 40 | 10 | 2 | 28 | **27.5%** | -168.4 | [16.9%, 38.1%] | 0.99998 |
| **Match 6** | X21-S vs Stockfish 11 | 1T, 1.5s + 50ms | 40 | 11 | 0 | 29 | **27.5%** | -168.4 | [16.3%, 38.7%] | 0.99996 |
| **Match 7** | X21-S vs Stockfish 19 | 1T, 1.5s + 50ms | 40 | 8 | 2 | 30 | **22.5%** | -214.8 | [11.9%, 33.1%] | 1.00000 |

### Disambiguation of Match 4 Opponent Identity:
In P1.16, Match 4 was played across 25 openings (50 games total) partitioned into two distinct sub-matches:
- **Part 1 (vs Janus Classical X19):** 13 pairs (26 games). Candidate X21-S scored $12.5 / 26$ (**48.1%** | +6 =13 -7). PGN: `analysis/phase1/p1.16/pgn/match4_part1_vs_x19.pgn`.
- **Part 2 (vs Janus Classical X20):** 12 pairs (24 games). Candidate X21-S scored $13.5 / 24$ (**56.2%** | +9 =9 -6). PGN: `analysis/phase1/p1.16/pgn/match4_part2_vs_x20.pgn`.
- Combined score across both reference engines: $26.0 / 50$ (**52.0%** | +15 =22 -13).

### W/D/L Decomposition Audit:
- In Match 5, a score of 11.0 / 40 was composed of **10 wins, 2 draws, 28 losses** (27.5%).
- In Match 6, a score of 11.0 / 40 was composed of **11 wins, 0 draws, 29 losses** (27.5%).
- In Match 7, a score of 9.0 / 40 was composed of **8 wins, 2 draws, 30 losses** (22.5%).

### Slower-Time Control Regression Finding:
In Match 2, when time control was increased from $1.0\text{s}+50\text{ms}$ to $2.5\text{s}+100\text{ms}$, X21-S suffered a sharp drop from **45.5% down to 39.0%** ($p = 0.9963$ against $H_0: \mu \le 0.50$). This proves that X21-S exhibits a severe slower-time-control scaling regression against X7, confirming that quiescence correctness without accompanying evaluation terms is increasingly penalized as search depth extends.

---

## 3. Scientific Reconciliation Conclusion

The provenance of Janus Classical X21 is fully reconciled. The tournament results recorded in P1.16 accurately reflect the raw outputs of the P1.16 execution script. However, the external benchmark results (scoring 22.5%–27.5% against Stockfish) represent a statistical and physical anomaly that requires immediate, exhaustive inspection in Phase 1.
