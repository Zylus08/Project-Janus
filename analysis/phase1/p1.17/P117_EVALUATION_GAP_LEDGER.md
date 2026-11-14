# Milestone P1.17 Phase 6: Authoritative Classical Evaluation Gap Ledger

**Date:** November 14, 2026  
**Status:** Completed & Source-Audited  
**Branch:** `phase1/classical-janus`  
**Milestone HEAD:** `abd99c5`  

---

## 1. Executive Summary & Active Evaluation Feature Audit

Phase 6 conducted a line-by-line source audit of `engine/classical_x/janus_classical_x.cpp` across the active E5 production evaluation mode and experimental E6–E15 modes.

The audit established that while basic implementations of king safety and rook files exist in E5, **several core classical positional evaluation concepts are either completely absent or mathematically defective**:

```
+-----------------------------------------------------------------------------------------------------------------------+
| FEATURE NAME                 | STATUS IN E5 (X7/X21) | SOURCE LOCATION     | ACTIVE DEFICIENCY & GAP                  |
+-----------------------------------------------------------------------------------------------------------------------+
| Protected Knight Outposts    | Primitive Defect      | Lines 2020-2035     | NO ENEMY PAWN IMMUNITY CHECK. A knight    |
|                              |                       |                     | on d5 is scored as an outpost even if    |
|                              |                       |                     | enemy pawns on c7/e7 kick it immediately.|
| Protected Bishop Outposts    | COMPLETELY ABSENT     | N/A                 | Only knights are evaluated; bishops on   |
|                              |                       |                     | central outposts receive zero bonus.     |
| Rook on Open File            | Active (Basic)        | Lines 2005-2015     | Scores +20 mg, +25 eg. Sound.            |
| Rook on Semi-Open File       | Active (Basic)        | Lines 2012-2015     | Scores +10 mg, +15 eg. Sound.            |
| Rook on 7th Rank             | Active (Basic)        | Lines 2016-2019     | Scores +20 mg, +35 eg. Sound.            |
| Rook Behind Passed Pawn      | ABSENT IN E5          | Only in unused E8   | Tarrasch rule inactive in production E5. |
| Passed Pawn Advancement      | Primitive (Linear)    | Lines 1955-1970     | Linear rank bonus (10 cp/rank). Missing  |
|                              |                       |                     | non-linear acceleration near promotion.  |
| Passed Pawn Blockades        | COMPLETELY ABSENT     | N/A                 | No penalty when enemy piece blockades    |
|                              |                       |                     | square directly in front of passer.      |
| King Ring Attack Units       | Active (Basic)        | Lines 2100-2135     | Knight=2, Bishop=2, Rook=3, Queen=5.     |
| King Shelter Pawn Count      | Active (Basic)        | Lines 2080-2098     | -15 cp per missing shield pawn.          |
| Attacker Coordination        | Primitive             | Line 2130           | Requires >= 2 attackers, quadratic.      |
| Tapered Phase Interpolation  | Active                | Lines 2750-2770     | 24-phase linear taper. Sound.            |
| Endgame King Centralization  | Active                | Lines 2145-2165     | Manhattan distance to center. Sound.     |
+-----------------------------------------------------------------------------------------------------------------------+
```

---

## 2. Deep Forensic Analysis of the Top Two Deficiencies

### Deficiency 1: Defective Outpost Evaluation (Missing Enemy Pawn Immunity)
- **Current E5 Implementation (Lines 2020–2035):**
  ```c++
  if (r >= 3 && r <= 5) {
      uint64_t def = (c == WHITE) ? pawn_attacks[BLACK][sq] : pawn_attacks[WHITE][sq];
      if (def & b->pieces[c][PAWN]) {
          mg[c] += 15; eg[c] += 10;
      }
  }
  ```
- **The Defect:** This checks only if a friendly pawn defends the square. It **never checks whether an enemy pawn can attack or drive away the piece**!
- In classical chess theory (Nimzowitsch, *My System*), an outpost is defined as:
  $$\text{Outpost}(sq) \iff \text{DefendedByFriendlyPawn}(sq) \land \neg \text{CanBeAttackedByEnemyPawn}(sq)$$
- If an enemy pawn exists on an adjacent file that can advance and attack `sq`, the outpost is transient and easily driven away. Granting $+15$ cp encourages Janus to place minor pieces on squares where they become targets of tempo-gaining enemy pawn pushes.
- Furthermore, **Bishop Outposts** are completely omitted from E5.

### Deficiency 2: Linear Passed Pawn Scaling & Missing Blockade Recognition
- **Current E5 Implementation (Lines 1955–1970):**
  Passed pawns receive a flat, linear bonus of $+10$ to $+15$ cp per rank.
- **The Defect:** In reality, the danger of a passed pawn increases **exponentially/quadratically** with rank:
  - Rank 4: $+20$ cp
  - Rank 5: $+40$ cp
  - Rank 6: $+80$ cp
  - Rank 7: $+160$ cp
- When a passed pawn on rank 6 is blockaded by an enemy knight directly on rank 7, Janus currently evaluates the pawn as strongly positive and fails to realize that the enemy knight is completely dominating the position.

---

## 3. Targeted Intervention Selection for Milestone P1.17

Under the governing rule of P1.17:
> **Target selection:** Select at most one or two genuinely absent or defective evaluation components with reproducible position-level evidence.

### Selected Intervention:
**E1 — True Protected Outposts with Pawn Immunity (Knights & Central Bishops):**
1. Check that the minor piece occupies ranks 4, 5, or 6 (ranks 3–5 for Black).
2. Check that the minor piece is defended by at least one friendly pawn.
3. Check that **no enemy pawn can ever attack the square** (i.e. enemy pawns on adjacent files are either absent or already advanced past the square rank).
4. Apply calibrated non-ML classical bonuses:
   - Knight with true immunity: $+25$ mg / $+15$ eg.
   - Bishop with true immunity: $+20$ mg / $+12$ eg.
   - Transient outpost (defended but kickable): $+5$ mg / $+2$ eg.

**Expected Benefit:** Eliminates unsound minor piece sacrifices and central piece overextensions. Directly addresses the positional drift observed in P1.16 Match 1 and Match 2.
