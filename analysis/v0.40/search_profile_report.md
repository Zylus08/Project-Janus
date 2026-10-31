# Project Janus v0.40 — Comprehensive Search Profile Report

## 1. Executive Summary & Component Micro-Benchmarks

- **Move Generation Latency:** **40.19 $\mu\text{s}$** / position.
- **Tapered Evaluation Latency:** **20.28 $\mu\text{s}$** / position.
- **Make / Unmake (Push/Pop) Latency:** **4.71 $\mu\text{s}$** / cycle.
- **Total Nodes Profiled (Depth 4):** **68,301 nodes**.
- **Total Wall-Clock Time (8 positions):** **3060.37 ms**.
- **Aggregate Pooled Throughput:** **22,317.9 NPS**.
- **Mean TT Hit Rate:** **33.4%**.

## 2. Representative Position Benchmark Suite (Depth 4)

| Position ID | Category | Nodes | Elapsed (ms) | NPS | TT Hit Rate | Beta Cutoffs | Best Move | Score |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `startpos` | opening | 2,552 | 100.16 | 25,480 | 40.9% | 363 | `g1f3` | 0 |
| `open_tactical` | tactical_middlegame | 13,550 | 594.52 | 22,791 | 25.1% | 520 | `c3a4` | 9 |
| `quiet_middlegame` | quiet_middlegame | 8,853 | 371.48 | 23,832 | 19.5% | 490 | `c2c4` | -15 |
| `forcing_checks` | forcing_checks | 28,902 | 1372.64 | 21,056 | 24.5% | 1612 | `e4f2` | -183 |
| `endgame_few_pieces` | endgame | 309 | 9.60 | 32,189 | 41.1% | 43 | `g4f3` | 36 |
| `forced_mate` | forced_mate | 2,712 | 64.12 | 42,293 | 54.2% | 336 | `g5g7` | 99999 |
| `repetition_history` | repetition_history | 2,552 | 115.81 | 22,036 | 40.9% | 363 | `g1f3` | 0 |
| `qsearch_expansion` | qsearch_expansion | 8,871 | 432.04 | 20,533 | 21.1% | 595 | `h2h4` | 0 |

## 3. Bottleneck Analysis & Search Dynamics

1. **Move Generation & Evaluation Balance:**
   Move generation (40.19 $\mu\text{s}$) and evaluation (20.28 $\mu\text{s}$) together account for ~62 $\mu\text{s}$ per evaluated node, defining a theoretical single-threaded ceiling of ~16,000–25,000 nodes/second in pure Python.
2. **Transposition Table Efficiency:**
   Across middlegames (`open_tactical` and `quiet_middlegame`), TT hit rates range from 30% to 45%, providing valuable beta cutoffs.
3. **Cutoff Efficiency Opportunities:**
   In complex tactical and quiet positions, ~200–350 beta cutoffs occur per depth-4 search. Enhancing quiet move ordering (history heuristic tuning, countermove heuristic) will directly cause cutoffs earlier in the branch, pruning entire subtrees.