# Project Janus — Phase 2, Milestone P2.2
## Phase 4: Neural Evaluation Failure Atlas & Quality Benchmark

**Author:** Principal Computer Chess Architect, Evaluation Specialist & Quantitative Auditor  
**Milestone:** P2.2 — Neural Evaluation Failure Forensics, Score Calibration & Scalable Dataset Readiness  
**Date:** 2026-11-16  
**Subject:** Empirical Quality Benchmark of Classical (R1), Float (H1), Quantized (H1), and Hybrid (H2) Across 36 Curated Positions  

---

### 1. Executive Summary & Benchmark Design

Phase 4 establishes an independent, frozen evaluation benchmark of 36 diagnostic chess positions spanning 10 fundamental categories:
1. Material Imbalances (P, N, B, R, Q, and Exchange).
2. Tactical Sacrifices & Mate Threats.
3. Quiet Middlegames & Central Control.
4. Pawn Structure (Passed, Doubled, Isolated, Connected).
5. Passed-Pawn Races.
6. King Safety & Open King Exposure.
7. Rook Activity (7th Rank & Passive Rooks).
8. Minor-Piece Mobility & Outposts.
9. Endgame Opposition & Zugzwang.
10. Theoretical Draws (Insufficient Material & Opposite-Colored Bishops).

Each position was evaluated across 4 configurations under strictly identical board representations:
- **E0 (Classical R1):** Handcrafted classical evaluation (`native_evaluate`).
- **E1 (H1 PyTorch FP32):** Full-precision 32-bit floating-point neural forward pass.
- **E2 (H1 Quantized C++):** Production INT16 accumulator / INT8 weights engine inference.
- **E3 (H2 Hybrid 50/50):** 50% Classical R1 + 50% Quantized H1 blend.

---

### 2. Full Benchmark Results Matrix

| Position Name | Category | Chess Truth | E0 (Classical) | E1 (PyTorch FP) | E2 (Quant C++) | E3 (Hybrid H2) | Quant Error ($\Delta E1-E2$) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Mat: White +Q** | Material | $+850$ | $+867$ | $+195.9$ | $+203$ | $+535$ | $7.08\text{ cp}$ |
| **Mat: Black +Q** | Material | $+850$ | $+867$ | $+195.9$ | $+203$ | $+535$ | $7.08\text{ cp}$ |
| **Mat: White +R** | Material | $+500$ | $+486$ | $+267.4$ | $+270$ | $+378$ | $2.56\text{ cp}$ |
| **Mat: White +B** | Material | $+325$ | $+325$ | $+192.3$ | $+198$ | $+261$ | $5.66\text{ cp}$ |
| **Mat: White +N** | Material | $+325$ | $+270$ | $+217.7$ | $+226$ | $+248$ | $8.30\text{ cp}$ |
| **Mat: White +P** | Material | $+100$ | $+85$ | $+75.8$ | $+80$ | $+82$ | $4.16\text{ cp}$ |
| **Mat: Exchange +R vs N** | Material | $+175$ | $-56$ | $+2.4$ | $+4$ | $-26$ | $1.56\text{ cp}$ |
| **Tac: Scholar Mate in 1** | Tactical | $+900$ | $+349$ | $+99.5$ | $+103$ | $+226$ | $3.54\text{ cp}$ |
| **Tac: Back Rank Mate in 1** | Tactical | $+900$ | $-1$ | $+254.1$ | $+253$ | $+126$ | $1.09\text{ cp}$ |
| **Tac: Queen Sac for Mate** | Tactical | $+800$ | $+304$ | $+148.6$ | $+164$ | $+234$ | $15.43\text{ cp}$ |
| **Mid: Startpos White** | Quiet Mid | $+20$ | $0$ | $+49.8$ | $+52$ | $+26$ | $2.18\text{ cp}$ |
| **Mid: Startpos Black** | Quiet Mid | $-20$ | $0$ | $+49.8$ | $+52$ | $+26$ | $2.18\text{ cp}$ |
| **Mid: Open e-file Control** | Quiet Mid | $+40$ | $+26$ | $+69.1$ | $+63$ | $+44$ | $6.06\text{ cp}$ |
| **Mid: Symmetrical French** | Quiet Mid | $+15$ | $0$ | $+28.7$ | $+29$ | $+14$ | $0.27\text{ cp}$ |
| **Pawn: Passed d6 Pawn** | Pawn Structure | $+400$ | $+192$ | $+188.3$ | $+177$ | $+184$ | $11.26\text{ cp}$ |
| **Pawn: Doubled c-Pawns** | Pawn Structure | $-20$ | $-18$ | $-121.1$ | $-114$ | $-66$ | $7.13\text{ cp}$ |
| **Pawn: Isolated d-Pawn** | Pawn Structure | $+10$ | $+11$ | $+164.4$ | $+153$ | $+82$ | $11.39\text{ cp}$ |
| **Pawn: Connected Passed e5+f5** | Pawn Structure | $+450$ | $+453$ | $+296.3$ | $+299$ | $+376$ | $2.68\text{ cp}$ |
| **Race: White d7 1 ply promo** | Pawn Race | $+800$ | $+762$ | $+410.7$ | $+418$ | $+590$ | $7.35\text{ cp}$ |
| **Race: Black d2 1 ply promo** | Pawn Race | $+800$ | $+762$ | $+410.7$ | $+418$ | $+590$ | $7.35\text{ cp}$ |
| **Race: Outside Passed Pawn a5** | Pawn Race | $+600$ | $+645$ | $+242.9$ | $+245$ | $+445$ | $2.15\text{ cp}$ |
| **King: Exposed Black King** | King Safety | $+150$ | $+742$ | $+113.7$ | $+125$ | $+433$ | $11.28\text{ cp}$ |
| **King: Stripped Black King** | King Safety | $+900$ | $+3225$ | $+1095.1$ | $+1095$ | $+2160$ | $0.13\text{ cp}$ |
| **King: Solid Fianchetto** | King Safety | $+10$ | $0$ | $+51.9$ | $+55$ | $+27$ | $3.11\text{ cp}$ |
| **Rook: White Rook on 7th** | Rook Activity | $+250$ | $+582$ | $+358.3$ | $+362$ | $+472$ | $3.66\text{ cp}$ |
| **Rook: Doubled Rooks on 7th** | Rook Activity | $+500$ | $+1147$ | $+725.8$ | $+724$ | $+935$ | $1.77\text{ cp}$ |
| **Rook: Passive 1st Rank Rook** | Rook Activity | $-200$ | $-532$ | $-515.4$ | $-519$ | $-526$ | $3.56\text{ cp}$ |
| **Minor: Knight Outpost on d5** | Minor Piece | $+120$ | $-64$ | $-155.6$ | $-153$ | $-109$ | $2.57\text{ cp}$ |
| **Minor: Bad French Bishop c8** | Minor Piece | $+50$ | $+24$ | $+60.9$ | $+59$ | $+41$ | $1.87\text{ cp}$ |
| **Minor: Bishop Pair Advantage** | Minor Piece | $+40$ | $+47$ | $+132.2$ | $+149$ | $+98$ | $16.82\text{ cp}$ |
| **End: Direct Opposition (w)** | Endgame | $0$ | $-52$ | $-69.8$ | $-69$ | $-61$ | $0.77\text{ cp}$ |
| **End: Direct Opposition (b)** | Endgame | $0$ | $-20$ | $+103.2$ | $+104$ | $+42$ | $0.76\text{ cp}$ |
| **End: Trebuchet Zugzwang** | Endgame | $0$ | $0$ | $+33.7$ | $+33$ | $+16$ | $0.72\text{ cp}$ |
| **Draw: K+N vs K** | Drawn | $0$ | $+342$ | $+362.9$ | $+360$ | $+351$ | $2.93\text{ cp}$ |
| **Draw: K+B vs K** | Drawn | $0$ | $+356$ | $+134.0$ | $+132$ | $+244$ | $2.00\text{ cp}$ |
| **Draw: Opposite-Colored Bishops**| Drawn | $0$ | $0$ | $+28.1$ | $+26$ | $+13$ | $2.09\text{ cp}$ |

---

### 3. Quantitative Error Summary by Category

| Category | Positions | Mean Truth (cp) | H1 C++ MAE (cp) | Classical R1 MAE (cp) | Primary Failure Mechanism |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Tactical Sacrifices** | 3 | $+867$ | **$693.3$** | $548.7$ | Extreme score compression; misses mating nets |
| **Pawn Races** | 3 | $+733$ | **$373.0$** | $38.7$ | Severe compression of promotion threats |
| **Material Imbalances** | 7 | $+454$ | **$277.3$** | $40.4$ | Queen under-valuation ($Q=203\text{ cp} < N=226\text{ cp}$) |
| **Rook Activity** | 3 | $+183$ | **$218.3$** | $447.0$ | Over-values 7th rank relative to piece count |
| **Theoretical Draws** | 3 | $0$ | **$172.7$** | $232.7$ | Ignorant of insufficient material ($K+N$ scores $+360$) |
| **Pawn Structure** | 4 | $+210$ | **$152.8$** | $54.3$ | Misinterprets isolated and doubled pawns |
| **Minor Piece Dynamics** | 3 | $+70$ | **$130.3$** | $72.3$ | Inverted outpost score on d5 ($-153\text{ cp}$) |
| **King Safety** | 3 | $+353$ | **$88.3$** | $972.3$ | Cannot measure pawn shield without HalfKP |
| **Endgame Opposition** | 3 | $0$ | **$68.7$** | $24.0$ | Skewed by $+50\text{ cp}$ side-to-move initiative bias |
| **Quiet Middlegames** | 4 | $+14$ | **$35.2$** | $15.5$ | Well-calibrated within training distribution |

---

### 4. Critical Causal Explanations

1. **Why H1 Loses Against Classical R1 (1.5% in M1):**
   - H1's evaluation compresses an entire Queen advantage to $+203\text{ cp}$, while valuing a Knight at $+226\text{ cp}$.
   - In alpha-beta search, pruning heuristics rely on standard centipawn margins. When H1 considers losing a Queen as only an $85\text{ cp}$ loss, it allows tactical sacrifices that lose queen for minor piece. Classical R1 punishes this immediately.
2. **Why Hybrid H2 Dominates Pure H1 (99.0% in M2):**
   - In H2 ($50\%$ Classical $+ 50\%$ NNUE), Classical R1's material evaluation ($+867\text{ cp}$ for Queen) is fused with H1's neural score ($+203\text{ cp}$), producing a blended Queen value of $+535\text{ cp}$ and a Knight value of $+248\text{ cp}$.
   - This restores the correct piece hierarchy ($Q > R > B \approx N > P$) and anchors search pruning, eliminating H1's tactical blunders while preserving neural node compression.
3. **Quantization Integrity:**
   - The mean quantization difference between PyTorch FP32 and Quantized INT16/INT8 C++ across all 36 positions is only **$4.84\text{ cp}$** (maximum $16.82\text{ cp}$).
   - This proves that quantization fidelity is not the cause of H1's weakness; the defect resides in the training objective, label formulation, and feature representation.
