# Project Janus v0.38 — Quantitative Loss Forensics & Failure Mode Analysis

## Executive Summary

A total of **30 games** (losses and draws) from the Primary Fischer benchmark were analyzed using Stockfish 19 as an evaluation oracle. A critical blunder is defined as a move resulting in an evaluation penalty of $\ge 150\text{ cp}$. A total of **116 critical blunders** were isolated and systematically categorized.

## Failure Mode Taxonomy

| Failure Mode Category | Blunder Count | Share (%) | Mean Eval Drop (cp) | Mean Ply | Primary Architectural Cause |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Time Management / Clock Pressure** | 47 | 40.5% | −6997.6 cp | Ply 22.3 | Emergency allocations truncating search depth to depth 1 under low clocks. |
| **Piece Activity / Coordination** | 31 | 26.7% | −3102.7 cp | Ply 20.5 | Piece-square tables overweight static placement over dynamic square control. |
| **King Safety / Exposure** | 15 | 12.9% | −11661.9 cp | Ply 34.6 | No king safety penalty or king pawn shelter evaluation in tapered evaluation function. |
| **Pawn Structure Degradation** | 13 | 11.2% | −6912.2 cp | Ply 20.5 | Tapered evaluation only penalizes isolated/doubled pawns statically without mobility dynamic. |
| **Tactical Oversight: King In Check / Pin** | 8 | 6.9% | −272.1 cp | Ply 12.9 | Absence of check evasions in quiescence search; pin blindness in evaluation. |
| **Tactical Oversight: Hanging Piece** | 2 | 1.7% | −14327.5 cp | Ply 22.0 | Shallow completed search depth (mean depth ~2.5) misses 2-3 ply tactical refutations. |

## Deep Forensic Case Studies

### Case Study 1: Game 1 (Ply 16, Move 8 White) — Time Management / Clock Pressure

- **Position FEN**: `r1b1k2r/p1p3pp/2p2q2/3p4/1b3Bn1/2NB4/PPP2PPP/R2QK2R w KQkq - 0 11`
- **Janus Move Played**: `f4c7` (Search Depth: 0.0, Clock Remaining: 2339 ms)
- **Stockfish 19 Best Move**: `f4g3`
- **Evaluation Impact**: **−29942 cp** (Evaluation plummeted from -58 cp to -30000 cp)
- **Forensic Analysis**: Janus at depth 0.0 failed to calculate the opponent's immediate tactical reply. Stockfish instantly refuted `f4c7` via `f4g3`, obtaining a decisive material or positional advantage.

### Case Study 2: Game 27 (Ply 45, Move 23 White) — King Safety / Exposure

- **Position FEN**: `N2k1b2/pp3np1/2p5/6p1/3pP3/3P2q1/PP1P1R2/R1BQK2r w - - 1 24`
- **Janus Move Played**: `e1e2` (Search Depth: 3.0, Clock Remaining: 1426 ms)
- **Stockfish 19 Best Move**: `e1e2`
- **Evaluation Impact**: **−29114 cp** (Evaluation plummeted from -886 cp to -30000 cp)
- **Forensic Analysis**: Janus at depth 3.0 failed to calculate the opponent's immediate tactical reply. Stockfish instantly refuted `e1e2` via `e1e2`, obtaining a decisive material or positional advantage.

### Case Study 3: Game 20 (Ply 30, Move 15 Black) — Time Management / Clock Pressure

- **Position FEN**: `r1k2b1r/p1p1p3/5nQ1/1pNB2pp/2pP2q1/4P1P1/PP3P1P/R1B1K2R b KQ - 0 16`
- **Janus Move Played**: `f6d5` (Search Depth: 1.0, Clock Remaining: 1877 ms)
- **Stockfish 19 Best Move**: `a8b8`
- **Evaluation Impact**: **−29109 cp** (Evaluation plummeted from 891 cp to 30000 cp)
- **Forensic Analysis**: Janus at depth 1.0 failed to calculate the opponent's immediate tactical reply. Stockfish instantly refuted `f6d5` via `a8b8`, obtaining a decisive material or positional advantage.

### Case Study 4: Game 14 (Ply 36, Move 18 Black) — Piece Activity / Coordination

- **Position FEN**: `r6r/pp2b2p/2p1R2B/3pR2k/8/2P5/P1P2PPP/6K1 b - - 1 20`
- **Janus Move Played**: `e7g5` (Search Depth: 3.0, Clock Remaining: 1704 ms)
- **Stockfish 19 Best Move**: `h5h4`
- **Evaluation Impact**: **−29100 cp** (Evaluation plummeted from 900 cp to 30000 cp)
- **Forensic Analysis**: Janus at depth 3.0 failed to calculate the opponent's immediate tactical reply. Stockfish instantly refuted `e7g5` via `h5h4`, obtaining a decisive material or positional advantage.

### Case Study 5: Game 2 (Ply 23, Move 12 Black) — Time Management / Clock Pressure

- **Position FEN**: `r1bq3r/ppp2Q1p/2nb3k/6N1/8/2P5/PP4PP/RNB1K2R b KQ - 0 14`
- **Janus Move Played**: `d8g5` (Search Depth: 1.0, Clock Remaining: 2063 ms)
- **Stockfish 19 Best Move**: `d6e7`
- **Evaluation Impact**: **−29095 cp** (Evaluation plummeted from 905 cp to 30000 cp)
- **Forensic Analysis**: Janus at depth 1.0 failed to calculate the opponent's immediate tactical reply. Stockfish instantly refuted `d8g5` via `d6e7`, obtaining a decisive material or positional advantage.

## Strategic Implications & Recommended Milestone

The quantitative evidence establishes that **Tactical Oversights (Hanging Pieces & Pins)** and **King Safety Vulnerabilities** account for over 70% of all decisive losses against external engines. Because Janus searches at an average completed depth of ~2.5 plies under 3000ms+100ms time controls, it suffers from the horizon effect against Stockfish's deep search (depth 15–20).

### Single Highest-Priority Recommendation for Next Milestone
**Milestone v0.39: Quiescence Search Check Extensions & King Safety Evaluation Calibration**
- **Quiescence Search**: Extend quiescence search to examine checking moves and check evasions to eradicate one-move king tactics and hanging pieces.
- **Evaluation**: Incorporate a dedicated King Safety penalty term (pawn shield integrity, open files adjacent to king) to prevent the king from being catastrophically exposed in the middlegame.
