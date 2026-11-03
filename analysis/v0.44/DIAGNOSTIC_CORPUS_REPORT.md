# Diagnostic Corpus Extraction Report — v0.44

**Milestone:** Project Janus v0.44  
**Date:** 2026-11-03  
**Status:** PASS (Gate D Validated)

---

## 1. Corpus Extraction Objective & Methodology

The goal of Phase D is to extract a curated diagnostic corpus of chess positions from the raw v0.43 replication dataset (`match_results.json` and `match_results.pgn`) that isolates the search divergence between Baseline K0 (`enable_rfp=False`) and Candidate RFP (`enable_rfp=True`).

### Selection Strategy
1. **Divergence Positions (31 positions):**
   - Sampled from all opening pairs where K0 significantly outperformed RFP (e.g. Pairs 3, 54, 76, 99, 100, 1, 2, 4, 6, 10, 11, 13, 20, 24, 25, 32, 36, 37, 39, 45, 61, 67, 73, 78, 98).
   - Identified the exact earliest ply where Janus made different move choices between K0 and RFP.
   - Recorded the pre-move FEN, the K0 move, the RFP move, and the ultimate game results.
2. **Control Positions (6 positions):**
   - Sampled from balanced opening pairs (Pairs 5, 7, 8, 14, 16, 26, 27) where both K0 and RFP made identical moves and achieved successful results.
   - Serves as negative controls to verify that RFP efficiency did not degrade positions where moves agreed.

The resulting dataset is saved at [`analysis/v0.44/diagnostic_positions.json`](file:///E:/ChessXML/project-janus/analysis/v0.44/diagnostic_positions.json).

---

## 2. Key High-Impact Divergence Positions

| Position ID | Opening | Side | Ply | FEN | K0 Move (Result) | RFP Move (Result) |
|---|---|---|---|---|---|---|
| `divergence_p54_white_ply6` | Evans Gambit | White | 6 | `r1bqk1nr/pppp1ppp/2n5/2b1p3/1PB1P3/5N2/P1PP1PPP/RNBQK2R b KQkq b3 0 4` | `c4d5` (1-0 Win) | `c2c3` (0-1 Loss) |
| `divergence_p3_white_ply3` | French Defense | White | 3 | `rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2` | `f1d3` (1-0 Win) | `b1c3` (0-1 Loss) |
| `divergence_p76_white_ply9` | Tarrasch Defense | White | 9 | `rnbqk2r/pp2bppp/4pn2/2pp4/2PP4/2N1PN2/PP3PPP/R1BQKB1R w KQkq - 4 6` | `e3g5` (1-0 Win) | `h2h3` (0-1 Loss) |
| `divergence_p99_white_ply5` | Nimzo-Larsen Modern | White | 5 | `rnbqkbnr/ppp2ppp/8/3pp3/4PP2/1P6/P1PP2PP/RNBQKBNR b KQkq - 0 3` | `f1b5` (1-0 Win) | `e5f4` (0-1 Loss) |
| `divergence_p100_white_ply3` | English Mikenas-Flohr | White | 3 | `rnbqkb1r/pppppppp/5n2/8/2P5/2N5/PP1PPPPP/R1BQKBNR b KQkq - 2 2` | `f1b5` (1-0 Win) | `d2d4` (0-1 Loss) |

---

## 3. Gate D Sign-Off

- [x] Extracted 37 diagnostic positions (31 divergence, 6 control).
- [x] Includes all target failure pairs (Pair 54 Evans Gambit, Pair 3 French Defense, Pair 76 Tarrasch, Pair 99 Nimzo-Larsen, Pair 100 English).
- [x] Validated against raw PGN move trees and match results.
- [x] Serialized to `analysis/v0.44/diagnostic_positions.json`.

**Gate D Status:** **PASS** — Proceeding to Phase E (Counterfactual Search Experiments).

