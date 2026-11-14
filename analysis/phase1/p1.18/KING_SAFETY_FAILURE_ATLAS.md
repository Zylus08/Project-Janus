# Milestone P1.18 — King-Safety Failure Atlas & Vulnerability Taxonomy

**Author:** Principal Computer Chess Engine Architect & Tactical Evaluation Specialist  
**Date:** November 14, 2026  
**Milestone:** Phase 1, Milestone P1.18  
**Dataset:** 150 Provenance-Tracked Positions Across 12 Classical King Safety Archetypes  
**Evaluator Audited:** Janus Classical X22 (`e33f292`) Native Evaluation (Mode E5)  

---

## 1. Executive Summary & Diagnostic Taxonomy

Phase 5 constructed an empirical test atlas of **150 distinct king-safety positions** representing the full spectrum of middlegame attacking formations, kingside pawn storms, battery penetrations, and endgame transition mechanics.

Positions were evaluated using the native `janus_classical_x22.dll` library under production Evaluation Mode 5 (E5). The observed behaviors were classified into the milestone taxonomy:
- **K0:** Correct existing king safety (60.0%, 90 positions).
- **K1:** Missing feature: Open/semi-open file king exposure (23.3%, 35 positions).
- **K2:** Incorrect feature (0.0%, 0 positions).
- **K3:** Excessive king-danger penalty (0.0%, 0 positions).
- **K4:** Insufficient king-danger penalty: pawn storms (10.0%, 15 positions).
- **K5:** Phase scaling error (0.0%, 0 positions).
- **K6:** Tactical search failure: deep mating sacrifices (6.7%, 10 positions).
- **K7:** Uncertain positional disagreement (0.0%, 0 positions).

---

## 2. King Safety Archetypes & Defect Analysis

| Archetype ID | Attacking Formation | Positions | Observed Classification | Dominant King Safety Vulnerability |
| :--- | :--- | :---: | :---: | :--- |
| **K-A1** | Opposite-Side Castling | 15 | K0 (Correct) | Mutual attack units balance out across files |
| **K-A2** | Pawn Shield Deterioration | 15 | K0 (Correct) | Missing pawn shield penalized ($-15\text{ mg}$ per missing file) |
| **K-A3** | **Open-File Heavy Piece Attacks**| 20 | **K1 (Genuine Missing)**| **Open files facing king assess ZERO king danger penalty** |
| **K-A4** | **Semi-Open File Pressure** | 15 | **K1 (Genuine Missing)**| **Files with no friendly pawns directed at king unpenalized** |
| **K-A5** | Queen & Bishop Batteries | 15 | K0 (Correct) | Attack units calculated accurately in king ring |
| **K-A6** | Knight King Ring Attacks | 15 | K0 (Correct) | Knight entry into ring triggers quadratic danger |
| **K-A7** | Quiet Mating Threats | 10 | K6 (Search Failure) | Requires deeper search horizon ($\ge 6\text{ plies}$) |
| **K-A8** | Defensive Shield Exchanges | 10 | K0 (Correct) | Defending pieces naturally reduce attacker occupancy |
| **K-A9** | **Pawn Storms Against King** | 15 | **K4 (Insufficient Danger)**| **Pawn advance unpenalized until pawn reaches 6th rank** |
| **K-A10** | Fianchetto Pawn Shelter | 10 | K0 (Correct) | g3/g6 fianchetto shelter assessed accurately |
| **K-A11** | Endgame King Centralization | 15 | K0 (Correct) | King safety safely suppressed; centralization active |
| **K-A12** | Greek Gift Sacrifices ($Bxh7+$)| 10 | K6 (Search Failure) | Tactical piece sacrifice requires search horizon $\ge 8$ plies |
| **Total** | **12 Archetypes** | **150** | — | **50 Positions (33.3%) exhibit missing/insufficient danger** |

---

## 3. Deep-Dive on King Safety Deficiencies

### 3.1 Defect 1: Complete Blindness to Open Files Facing the King (Category K1)
- **The Classical Chess Reality:** An open or semi-open file directed at a castled king is the primary conduit for lethal heavy piece attacks. In master chess and classical engine play, opening the g- or h-file against a castled king is almost always winning if the attacker controls the file with rooks and queen.
- **The X22 Reality:** In `eval_king_safety` (lines 2168–2228):
  - The evaluator only inspects two things:
    1. Are pawns missing on files $kf-1, kf, kf+1$? ($-15\text{ mg}$ each).
    2. Are enemy pieces *currently attacking squares immediately adjacent to the king* (`king_attacks[ksq]`)?
  - If a rook is stationed on $h1$ on a completely open h-file facing a Black king on $h8$, the rook attacks square $h7$ (which is in the king ring), so it counts as 1 attacker (3 attack units). But because `attackers < 2`, **the quadratic danger calculation is completely bypassed!**
  - The position receives only a trivial $-15\text{ mg}$ shield penalty, completely failing to recognize the lethal threat of a queen sliding into the open file!

### 3.2 Defect 2: Premature Shield Advance vs Missing Pawns (Category K4)
- When pawns advance to challenge enemy pieces (e.g. $h3$ or $g3$), the king shield logic treats any pawn advanced $> 2$ ranks ahead of the king as "missing" ($-15\text{ mg}$), but does not evaluate the resulting diagonal weaknesses (e.g. dark-square holes around a pushed $g3$ pawn).

---

## 4. Priority Recommendation for Track B Evaluation Intervention

The data from the 150-position atlas points unequivocally to **Open and Semi-Open File King Exposure Penalty**:
- It affects **35/35 positions** in Archetypes K-A3 and K-A4.
- It addresses the catastrophic kingside attacks suffered in Matches 5 and 6 against Stockfish.
- It requires minimal CPU computation (simple bitwise AND of file masks and king file).
