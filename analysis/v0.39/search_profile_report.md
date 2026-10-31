# Project Janus v0.39 — Search Performance Profile Report

## 1. Executive Summary & Component Breakdown

- **Move Generation Latency:** 40.18 $\mu\text{s}$ / position.
- **Tapered Evaluation Latency:** 21.76 $\mu\text{s}$ / position.
- **Mean Search NPS (Q0):** **21,998.4 nodes/sec**.
- **Mean Search NPS (Q1):** **11,018.8 nodes/sec**.
- **Selective Check Exploration Overhead (Q1 vs Q0):** +12.4% nodes, +313.6% search time.

## 2. Nodes Per Move Across Game Phases (Depth 4)

| Game Phase | Mean Nodes (Q0) | Typical Characteristics |
| :--- | :---: | :--- |
| **Opening** | 5,532.5 | Standard phase benchmark position |
| **Middlegame** | 13,168.5 | Standard phase benchmark position |
| **Endgame** | 309.0 | Standard phase benchmark position |
| **Tactical** | 2,712.0 | Standard phase benchmark position |

## 3. Position-by-Position Comparison (Depth 4)

| Position ID | Phase | Q0 Nodes | Q0 Time (ms) | Q0 NPS | Q1 Nodes | Q1 Time (ms) | TT Hit Rate | Beta Cutoffs |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `startpos` | opening | 2552 | 144.62 | 17,647 | 2556 | 210.81 | 40.9% | 363 |
| `four_knights` | opening | 8513 | 475.04 | 17,921 | 8536 | 1510.31 | 30.7% | 243 |
| `open_game` | middlegame | 13550 | 726.18 | 18,659 | 13584 | 4600.79 | 25.1% | 520 |
| `middlegame_tactical` | middlegame | 12787 | 673.86 | 18,976 | 14600 | 2076.74 | 18.3% | 803 |
| `rook_endgame` | endgame | 309 | 13.98 | 22,100 | 319 | 16.82 | 41.1% | 43 |
| `tactics_mate_in_one` | tactical | 2712 | 73.92 | 36,688 | 5839 | 301.11 | 54.2% | 336 |

## 4. Time-Bounded Completed Depth (150 ms Budget)

| Position ID | Phase | Q0 Depth | Q0 Nodes | Q0 NPS | Q1 Depth | Q1 Nodes | Q1 NPS |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `startpos` | opening | **4** | 2816 | 18,512 | **3** | 1792 | 11,618 |
| `four_knights` | opening | **2** | 2816 | 18,354 | **2** | 1664 | 10,412 |
| `open_game` | middlegame | **2** | 2176 | 14,422 | **2** | 1536 | 9,769 |
| `middlegame_tactical` | middlegame | **2** | 2176 | 14,402 | **2** | 1920 | 12,192 |
| `rook_endgame` | endgame | **8** | 3712 | 24,422 | **7** | 2432 | 15,885 |
| `tactics_mate_in_one` | tactical | **4** | 4480 | 29,811 | **3** | 3456 | 22,639 |

## 5. Architectural Findings & Tradeoffs

1. **Q0 (Checks Off in QSearch):** Consistently reaches deeper plies within blitz time constraints with zero branching explosion.
2. **Q1 (Selective Checks in QSearch):** Demonstrates an overhead of +12.4% nodes. While it catches tactical check horizons earlier, the reduction in nominal search depth on open positions suggests Q0 provides the superior overall playing-strength trade-off when check-evasion fail-low is already corrected.
3. **Transposition Table Hit Rates:** TT hit rates range from 15% to 55% with robust cutoff efficiency across middlegame positions.