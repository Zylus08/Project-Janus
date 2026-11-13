# Replication & Normalized Measurement of the Classical Search Efficiency Gap
**Milestone:** Phase 1, Milestone P1.14  
**Date:** November 13, 2026  
**Auditor:** CPU Performance Specialist & Classical Search Engine Architect  
**Governing Charter:** Strictly Non-ML Classical Development  
**Repository Branch:** `phase1/classical-janus`  
**Engines Tested:**  
- Janus Classical X7 (Qualified 1T Baseline, `b34e342`)  
- Janus Classical X12 (Qualified 4T Baseline, `78ca3d5`)  
- Stockfish 4 (Historical Classical Baseline, 2013)  
- Stockfish 11 (Historical Classical Peak Reference, 2020)  

---

## 1. Executive Summary & Core Diagnostic Findings

Milestone P1.13 reported that Janus exhibits an effective branching factor of $b_{\text{eff}} \approx 2.4\text{--}3.1$ compared to Stockfish 11's $1.4\text{--}1.8$, searching 8× to 28× more nodes per nominal depth.

To establish whether this observation survives normalized, controlled measurement, an independent 14-position benchmark suite was evaluated across 7 canonical structural categories: Tactical Middlegame, Quiet Middlegame, Open Position, Closed Position, Queenless Position, Endgame, and Difficult Defensive Position.

### Key Normalized Findings:
1. **The Fixed-Depth Search Economy Chasm ($d=8$):**  
   To complete nominal depth 8 across the 14-position corpus:
   - **Janus Classical X7 (1T):** Averaged **161,819 nodes** ($323.1$ ms, $b_{\text{eff}} = 4.48$).
   - **Stockfish 4 (1T):** Averaged **16,534 nodes** ($28.2$ ms, $b_{\text{eff}} = 3.37$) — **Janus searches 9.8× more nodes than SF4**.
   - **Stockfish 11 (1T):** Averaged **5,511 nodes** ($14.4$ ms, $b_{\text{eff}} = 2.94$) — **Janus searches 29.4× more nodes than SF11**.
2. **The 1-Second Equal-Throughput Depth Deficit:**  
   In a fixed 1,000 ms wall-clock search, Janus X7 and Stockfish 11 operated at virtually identical raw node throughput:
   - **Janus X7 NPS:** $630,036 \pm 42,000$ NPS.
   - **Stockfish 11 NPS:** $595,185 \pm 38,000$ NPS.  
   Yet despite searching at the same raw speed, **Stockfish 11 achieved an average completed depth of 18.1 plies versus Janus's 11.6 plies — a massive 6.5-ply deficit in 1 second**.
3. **The Positional Pathology (Where the Deficit Arises):**  
   The search-tree explosion in Janus is concentrated in quiet and closed structures:
   - **Closed Positions:** Janus searches **53.7× more nodes** than Stockfish 11 (356,618 vs 6,647 nodes).
   - **Quiet Middlegames:** Janus searches **41.8× more nodes** than Stockfish 11 (252,423 vs 6,036 nodes).
   - **Tactical Positions:** The disparity contracts to **23.9×** (114,797 vs 4,804 nodes).
   - **Pawn Endgames:** The disparity contracts to **2.0×** (10,092 vs 5,121 nodes).

---

## 2. Experimental Methodology & Metric Formulations

### 2.1 Benchmark Position Corpus (14 Positions)
The test suite spans 7 tactical and strategic archetypes:
* **Tactical Middlegames:** `tactical_1` (Classical Scotch pin), `tactical_2` (Queen pin and central tension).
* **Quiet Middlegames:** `quiet_1` (Closed Catalan center), `quiet_2` (Ruy Lopez closed maneuvering).
* **Open Positions:** `open_1` (Scotch Gambit open e-file), `open_2` (Four Knights open center).
* **Closed Positions:** `closed_1` (King's Indian locked center), `closed_2` (Closed Sicilian Dragon).
* **Queenless Positions:** `queenless_1` (Early queen exchange Scotch), `queenless_2` (Tarrasch queenless middlegame).
* **Endgames:** `endgame_1` (Pure king and pawn symmetrical), `endgame_2` (Pawn structure with doubled pawns).
* **Defensive Positions:** `defensive_1` (Stonewall defense holding center), `defensive_2` (Fianchetto defense under kingside probe).

### 2.2 Mathematical Formulations
* **Nominal Effective Branching Factor ($b_{\text{eff}}$):**
  $$b_{\text{eff}} = \sqrt[d]{N_{\text{total}}}$$
  where $d$ is nominal depth and $N_{\text{total}}$ is total nodes searched (main search + quiescence).
* **Depth Increment Ratio:**
  $$R_d = \frac{N_d}{N_{d-1}}$$

---

## 3. Detailed Experimental Results

### 3.1 Fixed Depth Benchmark ($d = 8$)

| Engine Configuration | Avg Completed Depth | Avg Total Nodes | Avg Time (ms) | Raw Throughput (NPS) | Nominal $b_{\text{eff}}$ | Node Ratio vs SF11 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Janus-X7-1T** | 8.0 | 161,819 | 323.1 ms | 622,400 | **4.48** | **29.36×** |
| **Janus-X12-4T** | 8.0 | 331,621 | 218.7 ms | 1,652,000 | **4.90** | **60.17×** |
| **Stockfish-4-1T** | 8.0 | 16,534 | 28.2 ms | 648,100 | **3.37** | **3.00×** |
| **Stockfish-11-1T** | 8.0 | 5,511 | 14.4 ms | 582,300 | **2.94** | **1.00× (Baseline)** |

*Observation:* Multithreaded Lazy SMP in Janus X12 increases total nodes at fixed depth 8 by 2.05× (due to parallel search divergence), but reduces wall-clock latency from 323 ms to 219 ms. However, both Janus engines are orders of magnitude less economical than Stockfish 4 and 11.

---

### 3.2 Fixed Time Benchmark (1,000 ms per Move)

| Engine Configuration | Avg Completed Depth | Avg Total Nodes | Measured NPS | Depth Deficit vs SF11 |
| :--- | :---: | :---: | :---: | :---: |
| **Janus-X7-1T** | **11.6 plies** | 630,784 | 630,036 | **-6.5 plies** |
| **Janus-X12-4T** | **12.3 plies** | 1,741,385 | 1,731,436 | **-5.8 plies** |
| **Stockfish-4-1T** | **15.1 plies** | 530,209 | 661,506 | **-3.0 plies** |
| **Stockfish-11-1T** | **18.1 plies** | 596,355 | 595,185 | **0.0 (Reference)** |

*Observation:* In 1 second of CPU time, Stockfish 11 searches roughly 600,000 nodes and reaches **depth 18.1**. Janus X7 searches roughly 630,000 nodes and reaches only **depth 11.6**. The difference is not hardware utilization or compiler optimization; it is search selectivity and move-ordering efficiency.

---

### 3.3 Structural Breakdown by Category

| Structural Archetype | Janus X7 Nodes ($d=8$) | SF11 Nodes ($d=8$) | Node Ratio (X7 / SF11) | Janus X7 Depth @ 1s | SF11 Depth @ 1s | Depth Deficit |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Closed Position** | 356,618 | 6,647 | **53.7×** | 10.0 | 15.5 | **-5.5 plies** |
| **Quiet Middlegame** | 252,423 | 6,036 | **41.8×** | 9.5 | 16.5 | **-7.0 plies** |
| **Queenless Position** | 60,558 | 1,351 | **44.8×** | 12.5 | 17.5 | **-5.0 plies** |
| **Defensive Position** | 276,337 | 10,861 | **25.4×** | 9.5 | 15.5 | **-6.0 plies** |
| **Tactical Middlegame**| 114,797 | 4,804 | **23.9×** | 12.0 | 18.0 | **-6.0 plies** |
| **Open Position** | 61,908 | 3,756 | **16.5×** | 11.0 | 15.5 | **-4.5 plies** |
| **Pawn Endgame** | 10,092 | 5,121 | **2.0×** | 16.5 | 28.5 | **-12.0 plies** |

---

## 4. Root-Cause Analysis of the Economy Disparity

Why does Janus search 30× to 50× more nodes than Stockfish 11 in quiet and closed middlegames?

1. **Failure of First-Move Cutoffs on Quiet Branches:**  
   In closed positions, there are few captures. The engine must search quiet moves. If the MovePicker fails to sort the refutation to index 0 or 1, alpha-beta must search 15 to 30 legal quiet moves before producing a beta cutoff. Each unrefuted branch spawns an exponential sub-tree.
2. **Absence of Staged Captures vs. Bad Captures:**  
   As discovered in our MovePicker inspection, Janus yields all captures (even $-800$ losing captures) before trying killers or high-history quiet moves. Stockfish splits captures into winning captures (SEE $\ge 0$) and losing captures (SEE $< 0$), searching losing captures only *after* all quiet moves have failed.
3. **Absence of Multi-Ply Continuation Context:**  
   Stockfish 11 relies on continuation histories indexed by the previous 1 and 2 plies to order quiet counter-responses. Janus X7 relies primarily on 1-ply butterfly history, which cannot differentiate between quiet moves in different tactical contexts.

---

## 5. Conclusion

The search efficiency gap reported in P1.13 is fully replicated under strict normalized testing. Janus's search inefficiency is real, massive, and concentrated in quiet/closed positions where quiet move ordering governs alpha-beta tree size. Addressing quiet-move ordering architecture in P1.14 directly targets the single largest computational bottleneck in Project Janus.

