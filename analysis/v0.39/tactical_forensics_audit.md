# Project Janus v0.39 — Corrected Tactical Forensics Audit

## 1. Denominator & Sampling Disclosures

- **Total Match Population:** 100 games in Primary Fischer benchmark.
- **Forensic Sample:** Exactly 30 games analyzed (sequential prefix: Games 1 through 30).
- **Mate Sentinel Separation:** Forced mates are explicitly separated from centipawn drops. Mate concessions are not treated as arbitrary ±30,000 centipawn swings.
- **Total Blunder Events Detected:** **120** (comprising 96 centipawn drops $\ge 150\text{ cp}$ and 24 forced mate concessions).

## 2. Corrected Failure Mode Taxonomy

| Failure Mode Category | Count in Sample | Share of Blunders (%) | Mean Pure Centipawn Drop | Mean Ply | Root Cause |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Shallow Search Horizon (Depth <= 1)** | 48 | 40.0% | −278.6 cp | Ply 22.6 | Evidence-based forensic classification |
| **Piece Coordination / Passivity** | 32 | 26.7% | −335.2 cp | Ply 20.9 | Evidence-based forensic classification |
| **King Safety / Central Exposure** | 18 | 15.0% | −246.1 cp | Ply 32.8 | Evidence-based forensic classification |
| **Pawn Structure Degradation** | 12 | 10.0% | −330.3 cp | Ply 22.8 | Evidence-based forensic classification |
| **Tactical Pins & Checks** | 8 | 6.7% | −272.1 cp | Ply 12.9 | Evidence-based forensic classification |
| **Hanging Pieces** | 2 | 1.7% | −211.0 cp | Ply 22.0 | Evidence-based forensic classification |

## 3. Top Forensic Case Studies

### Case 1: Game 1 (Ply 16 White) — Shallow Search Horizon (Depth <= 1)
- **Position FEN:** `r1b1k2r/p1p3pp/2p2q2/3p4/1b3Bn1/2NB4/PPP2PPP/R2QK2R w KQkq - 0 11`
- **Move Played:** `f4c7` (Depth: 0.0, Clock: 2339 ms)
- **Stockfish 19 Best Move:** `f4g3`
- **Consequence:** Forced Mate in 1 plies conceded

### Case 2: Game 2 (Ply 5 Black) — Tactical Pins & Checks
- **Position FEN:** `r1bqkb1r/pppp1ppp/2n5/4P3/4n3/5N2/PPP1QPPP/RNB1KB1R b KQkq - 1 5`
- **Move Played:** `f8b4` (Depth: 2.0, Clock: 2731 ms)
- **Stockfish 19 Best Move:** `e4c5`
- **Consequence:** −301 cp drop

### Case 3: Game 2 (Ply 7 Black) — Piece Coordination / Passivity
- **Position FEN:** `r1bqk2r/pppp1ppp/2n5/4P3/1b2n3/2P2N2/PP2QPPP/RNB1KB1R b KQkq - 0 6`
- **Move Played:** `e4f2` (Depth: 2.0, Clock: 2643 ms)
- **Stockfish 19 Best Move:** `d7d5`
- **Consequence:** −226 cp drop

### Case 4: Game 2 (Ply 15 Black) — King Safety / Central Exposure
- **Position FEN:** `r1bqk2r/ppp2Bpp/2nb4/8/8/2P2N2/PP3QPP/RNB1K2R b KQkq - 0 10`
- **Move Played:** `e8f7` (Depth: 3.0, Clock: 2347 ms)
- **Stockfish 19 Best Move:** `e8f8`
- **Consequence:** −172 cp drop

### Case 5: Game 2 (Ply 23 Black) — Shallow Search Horizon (Depth <= 1)
- **Position FEN:** `r1bq3r/ppp2Q1p/2nb3k/6N1/8/2P5/PP4PP/RNB1K2R b KQ - 0 14`
- **Move Played:** `d8g5` (Depth: 1.0, Clock: 2063 ms)
- **Stockfish 19 Best Move:** `d6e7`
- **Consequence:** Forced Mate in 2 plies conceded
