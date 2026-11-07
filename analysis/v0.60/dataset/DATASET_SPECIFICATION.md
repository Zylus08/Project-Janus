# PROJECT JANUS v0.60 — VALUE DATASET SPECIFICATION
**Author:** Principal Chess Engine Research Architect, ML Systems Engineer & Independent Scientific Reproducibility Auditor  
**Date:** 2026-11-07  
**Repository:** `E:\ChessXML\project-janus`  
**Dataset Directory:** `analysis/v0.60/dataset/`  
**Teacher Engine:** Stockfish 19 (`E:\ChessXML\tools\stockfish\stockfish.exe`)

---

## 1. Dataset Origin & Licensing
- **Primary Source:** Lichess Elite Database (June 2020), archived at `analysis/v0.58/data/lichess_elite_2020-06.zip`.
- **Game Criteria:** Standard chess games played by FIDE titled masters and high-rated Lichess players ($\ge 2300$ Blitz/Classical Elo).
- **Licensing:** Open Data Commons / CC0 Public Domain.
- **Deduplication:** Strict position-level deduplication across the entire corpus. No game or position appears in more than one split partition.

---

## 2. Teacher Labeling Configuration
- **Engine:** Stockfish 19 64-bit modern SSE4.2/AVX2.
- **Executable SHA-256:** `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`
- **Protocol:** UCI with strict evaluation constraints:
  - `setoption name Threads value 1`
  - `setoption name Hash value 16`
  - `go nodes 5000`
- **Search Budget Rationale:** Fixed nodes ($N = 5,000$) provides consistent search depth ($\approx \text{depth } 8 - 12$) independent of machine CPU load, while delivering $\approx 100\ \text{pos/s}$ labeling throughput.
- **Score Semantics:**
  - Standard centipawns: relative to side to move (`score_cp`).
  - Mate scores: $\pm 30,000$ centipawns, with mate depth explicitly recorded.
  - Normalized White perspective: $+1 \times \text{score}$ if White to move, $-1 \times \text{score}$ if Black to move.
  - WDL Target: $P(\text{Win}_{\text{stm}}) = \frac{1}{1 + 10^{-\text{score\_cp} / 400.0}}$ (or standard logistic $\frac{1}{1 + e^{-\text{score\_cp} / 400.0}}$).

---

## 3. Classical Control Baseline (Janus C1)
- For every position, Janus C1 handcrafted static evaluation is computed simultaneously via `NativeEngineBridgeC1`.
- Enables direct head-to-head empirical comparison between:
  - **E0:** Handcrafted classical static evaluation.
  - **E1:** V1-Small neural evaluator.
  - **E2:** V1-Compact neural evaluator.

---

## 4. Split Structure & Isolation Protocol
- **Partitions:**
  - **Train Partition:** 80% of positions.
  - **Validation Partition:** 10% of positions (for early stopping and hyperparameter monitoring).
  - **Held-Out Test Partition:** 10% of positions (strictly sequestered; never observed during training or model selection).
- **Leakage Prevention:** Position core FENs ($[0..3]$ tokens, ignoring clocks) are verified to have zero intersection between Train, Validation, and Test.

