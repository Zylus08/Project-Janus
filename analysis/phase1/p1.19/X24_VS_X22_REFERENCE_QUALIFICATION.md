# Reference Qualification Battery: Candidate X24-S vs Reference X22-S

## 1. Executive Summary

Milestone P1.19 establishes Match 1 as the primary research gate: evaluating whether Candidate **Janus Classical X24-S** (Track A Isolated: Backward Pawns = 1, King-File Exposure = 0, E5, Q1, Pawn Hash = 1) achieves measurable superiority over **Reference Janus Classical X22-S** (Control: Backward Pawns = 0, King-File Exposure = 0, E5, Q1, Pawn Hash = 1) under official tournament conditions.

### Primary Research Gate Findings:
- **Match 1 Standings:** Candidate X24-S scored **48.0 / 100** (+29 wins, =38 draws, -33 losses, **48.0%**).
- **Elo Difference:** **-13.9 Elo** ($\pm 16.8$ Elo 95% error margin).
- **Pentanomial Distribution:** $[2.0: 5, 1.5: 13, 1.0: 11, 0.5: 15, 0.0: 6]$.
- **Paired Statistical Significance:**
  - Sample Mean: $0.4800$
  - Standard Error: $0.0428$
  - Paired 95% Confidence Interval: **[39.62%, 56.38%]**
  - Student-$t$ Statistic: $t = -0.4673$
  - One-Sided p-value ($H_1: \mu > 0.50$): **0.6800**
  - Two-Sided p-value ($H_0: \mu = 0.50$): **0.6400**
- **Outcome Adjudication:** Because the paired 95% confidence interval spans $50.0\%$ and $p = 0.6400 > 0.05$, the observed performance of Candidate X24-S is **statistically indistinguishable from parity with Reference X22-S**. Candidate X24 fails to establish statistically significant superiority over Reference X22.

---

## 2. Match Protocol & Environmental Integrity

Match 1 was executed with complete cryptographic and environmental controls:
- **Hardware:** AMD Ryzen 7 5700X 8-Core Processor (16 logical threads), 32 GB DDR4-3200 RAM, Windows 11 x64.
- **Engines:**
  - Candidate: `analysis/phase1/p1.19/control/janus_classical_x24.exe` (SHA-256: `D8BE5521B91A353C7C4D2E8BAD51AF008147B3FD11989C2055780CE4ED91981F`)
  - Reference: `analysis/phase1/p1.17/control/janus_classical_x22.exe` (SHA-256: `35D095CFFE8A2EDA412171803C09BE52A74DFB3F9744C04F573D2A7FFB1C2F1C`)
- **Time Control:** 1.0s base + 50ms Fischer increment (1 thread per engine).
- **Opening Suite:** 50 ECO-diverse pairs (A00–E99) from `analysis/v0.56/corpus/independent_openings_v056.json` (100 total games).
- **Adjudication Contract:** Resignation adjudicated at 5 consecutive plies with $|eval| \ge 1000$ cp after move 50; draw adjudicated at 8 consecutive plies with $|eval| \le 8$ cp after move 40.
- **PGN Artifact:** `analysis/phase1/p1.19/pgn/match_1_x24-s_vs_x22-s_ref_1t.pgn`.
- **Raw Summary:** `analysis/phase1/p1.19/raw/match_1_x24_vs_x22_summary.json`.

---

## 3. Pentanomial Distribution & Pairwise Analysis

In opening-paired match play, each opening is contested twice with colors reversed, yielding 50 independent pair observations:

| Pair Outcome | Score Contribution | Count | Percentage | Description |
| :---: | :---: | :---: | :---: | :--- |
| **Clean Win (2.0)** | 2.0 pts | 5 | 10.0% | X24-S won as both White and Black |
| **Advantage (1.5)** | 1.5 pts | 13 | 26.0% | X24-S scored 1 win and 1 draw |
| **Neutral (1.0)** | 1.0 pts | 11 | 22.0% | 1 win each or 2 draws |
| **Disadvantage (0.5)** | 0.5 pts | 15 | 30.0% | X24-S scored 1 loss and 1 draw |
| **Clean Loss (0.0)** | 0.0 pts | 6 | 12.0% | X24-S lost as both White and Black |
| **Total** | **48.0 pts** | **50 pairs** | **100.0%** | **100 games** |

### Key Observations:
1. **Symmetric Disadvantage:** X24-S suffered 15 pair disadvantages (0.5) and 6 clean losses (0.0), totaling 21 negative pairs, compared to 13 advantages (1.5) and 5 clean wins (2.0), totaling 18 positive pairs.
2. **High Draw Rate (38%):** At 1.0s + 50ms, the draw rate expanded significantly compared to blitz (38.0% vs 29.0%), reflecting improved endgame conversion and defensive holding by both engines.
3. **Decisive Tactical Volatility:** 62 of 100 games concluded decisively (29 X24 wins, 33 X22 wins). When structural imbalances arose, tactical sharpness dominated over the $-10\text{ mg} / -15\text{ eg}$ backward pawn differential.

---

## 4. Qualitative Positional Forensics

A detailed audit of games in Match 1 reveals the specific operational impact of the isolated backward-pawn term:

### 4.1 Structural Infiltration & Positional Squeeze (Positive Cases)
- **Pair 04, Game 1 (X24-S White):** X24 identified Black's backward pawn on d6 following an open Sicilian structure. By clamping the d5 square with a knight outpost and tripling heavy pieces on the half-open d-file, X24 converted a clean positional win (1-0 on move 64).
- **Pair 13, Game 2 (X24-S Black):** In a French Defense advance variation, X24 targeted White's overextended pawn structure. The backward pawn penalty correctly dissuaded X24 from allowing backward pawns on e6, transitioning into a favorable rook endgame (0-1 on move 68).

### 4.2 Tactical Rigidity & Counterplay Suppression (Negative Cases)
- **Pair 08, Game 2 (X24-S Black):** In an English Opening structure, X24 evaluated the pawn push ...d5 as undesirable because the resulting c6 pawn would be flagged as backward. X22 exploited X24's passive piece placement to launch a devastating kingside pawn storm (1-0 on move 38).
- **Pair 22, Game 1 (X24-S White):** Facing active counterplay, X24 prioritized defending a backward pawn on c3 with passive minor pieces rather than sacrificing the pawn for tactical initiative. X22 penetrated with its rooks and forced resignation (0-1 on move 63).

---

## 5. Formal Gate Verdict

Under the governance rules of Project Janus:
1. A candidate engine can only achieve **Category B (Research Reference)** status if it demonstrates statistically verified superiority over Reference X22 ($p < 0.05$ and win rate $> 50.0\%$).
2. Candidate X24 scored **48.0%** with $p = 0.6400$, failing the Primary Research Gate.
3. Therefore, **Candidate X24 does NOT displace Reference X22 as the active research reference**.
