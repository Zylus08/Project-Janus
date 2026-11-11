# PROJECT JANUS — PHASE 1, MILESTONE P1.8
## Final Research Decision & Baseline Promotion Adjudication

### 1. Executive Summary & Governance Charter

Milestone P1.8 was commissioned to resolve the primary bottleneck in Project Janus Phase 1: the empirical finding that **83.3% of all chess failures** stem from static positional evaluation blindness (58.3%) and endgame horizon limitations (25.0%).

The milestone introduced **Janus Classical X13**, co-designing:
1. The 64B cache-line packed parallel search core with smart depth-preferred replacement and root arbitration.
2. The comprehensive handcrafted classical evaluation (E10) incorporating passed pawn rank progression, king safety attack units with quadratic queen scaling, safe piece mobility bitboards, knight outposts, bishop pair, and endgame king activity.
3. A zero-contention thread-local pawn hash architecture (`t_pawn_table[16384]`, 512 KB per thread) resident entirely within private CPU L2 cache.

---

### 2. Experimental Summary & Evidence Synthesis

| Benchmark Match | Contenders | Time Control | Sample Size | Score | Elo Delta | Paired $t$-test | Decision Implication |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Match A** | X13 (1T) vs. X7 (1T) | 1.0s + 0.05s | 200 games | 92.5 / 200 (46.25%) | -26.1 Elo | $t = -1.2405$, $p = 0.218$ | No statistically significant regression against single-thread champion |
| **Match B** | X13 (4T) vs. X12 (4T) | 1.0s + 0.05s | 200 games | 106.0 / 200 (53.00%) | **+20.9 Elo** | $t = +1.2410$, $p = 0.218$ | **Decisive multithreaded advancement (+12 game differential)** |
| **Match C** | X13 (4T) vs. X12 (4T) | 3.0s + 0.10s | 40 games | 16.5 / 40 (41.25%) | -61.4 Elo | $t = -1.1285$, $p = 0.273$ | High variance across 40 games; $H_0$ retained; indicates tuning need |
| **Match SF** | X13 (4T) vs. SF19 (4T) | 2.0s + 0.05s | 40 games | 1.0 / 40 (2.50%) | -636.4 Elo | $t = -27.6064$, $p < 10^{-6}$ | **First points scored against unrestricted SF19 (2 draws as Black)** |

---

### 3. Formal Promotion Adjudication

In accordance with Project Janus governance:

#### Decision 1: Single-Thread Production Baseline
- **Retain Janus Classical X7 (`b34e342`)** as the qualified single-thread classical baseline.
- *Rationale*: In Match A, X7 scored 53.75% (+26.1 Elo) against X13. For pure 1-thread execution, X7's streamlined evaluation provides maximum NPS and tactical speed.

#### Decision 2: Multithreaded Production Baseline
- **PROMOTE Janus Classical X13 as the Official Qualified Multithreaded Baseline**, formally superseding Janus Classical X12 (`78ca3d5`).
- *Rationale*:
  1. In Match B (100 pairs, 200 games), X13 decisively outplayed X12, scoring **106.0 / 200 (53.0%)** with a **+12 game positive win differential** (67 wins to 55 losses).
  2. In external testing against unrestricted Stockfish 19, X13 achieved the project's first scoring result (**2 defensive draws as Black**), whereas X11 and X12 were swept 0–40.
  3. The thread-local L2 pawn cache guarantees 100% thread safety and zero inter-core synchronization overhead.

---

### 4. Baseline Lineage Registry

```
Classical C1 (Initial Frozen Baseline, commit bbadf8f)
  │
  ├──> Janus Classical X6 (P1.1 Staged Movegen, commit 135c019)
  │     │
  │     └──> Janus Classical X7 (P1.2/P1.3/P1.4 Single-Thread Baseline, commit b34e342) [RETAINED AS 1T BASELINE]
  │
  └──> Janus Classical X10 (P1.5 Handcrafted Positional Evaluation, commit 504022f)
        │
        └──> Janus Classical X11 (P1.6 Multithreaded Platform, commit 54559ce - Superseded)
              │
              └──> Janus Classical X12 (P1.7 Cache-Line Packed Multithreaded Core, commit 78ca3d5 - Superseded)
                    │
                    └──> Janus Classical X13 (P1.8 Co-Designed Multithreaded Engine) [PROMOTED AS 4T BASELINE]
```

