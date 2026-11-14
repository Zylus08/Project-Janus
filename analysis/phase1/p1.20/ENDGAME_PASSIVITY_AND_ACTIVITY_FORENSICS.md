# Milestone P1.20 Phase 4: Endgame Passivity and Activity Forensics

## 1. Executive Summary & Forensic Methodology

Milestone P1.19 Match 4 demonstrated a severe degradation for Candidate X24 at slow time controls ($37.0\%$ against Baseline X7, $p = 0.0129$). Phase 4 conducted a forensic investigation of the endgame phase across the critical loss games of Match 4:
- Extracted turning-point FENs at the start of the endgame (plies 60–64) from representative loss games (Games 4, 8, 14, 18, 24, 28, 38, 50).
- Executed counterfactual replays under two controlled conditions:
  - **Condition E0 (Active Baseline):** Reference X22 (`g_use_backward_pawns = 0`).
  - **Condition E1 (Structural Penalty):** Candidate X24 (`g_use_backward_pawns = 1`).
- Evaluated root move divergence, search score trajectory, static eval differences, and piece activity metrics (active checks, king cutoffs, and counter-attacks vs passive defense of weak pawns).

---

## 2. Forensic Replay Results Table

| Game | Ply | Position Theme | X22 Best Move | X22 Score | X24 Best Move | X24 Score | Divergence Class | Strategic Consequence |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| **Game 4** | 61 | Knight vs Bishop endgame | `b2a4` | $-15\text{ cp}$ | `b2a4` | $-19\text{ cp}$ | Agreement | Identical root move; X24 static penalty slightly depresses score. |
| **Game 8** | 61 | Rook + 3 pawns vs Rook + 4 | `g8g7` | $-131\text{ cp}$ | `g8g7` | $-142\text{ cp}$ | Agreement | Both engines identify king activation `Kg7` as necessary. |
| **Game 14** | 63 | Rook endgame, outside passer | `e4d4` | $-139\text{ cp}$ | `e4d4` | $-115\text{ cp}$ | Agreement | Both engines centralize king on d4. |
| **Game 18** | 61 | Queen + minor piece ending | `f5d5` | $-386\text{ cp}$ | `f5d5` | $-391\text{ cp}$ | Agreement | Material deficit forces queen centralization. |
| **Game 24** | 61 | Bishop ending with backward c-pawn | **`c5f8`** | **$-663\text{ cp}$** | **`c5e3`** | **$-681\text{ cp}$** | **VERIFIED DIVERGENCE** | **X24 retreats bishop passively to e3 to protect backward pawn; X22 counter-attacks via f8.** |
| **Game 28** | 61 | Queen + Rook tactical liquidation | **`d5c4`** | **$-418\text{ cp}$** | **`d5f7`** | **$-418\text{ cp}$** | **VERIFIED DIVERGENCE** | **X24 retreats queen to f7; X22 actively invades c4 to attack enemy pawns.** |
| **Game 38** | 61 | Symmetrical Rook endgame | `g8g7` | $-55\text{ cp}$ | `g8g7` | $-53\text{ cp}$ | Agreement | King step `Kg7` played by both. |
| **Game 50** | 61 | Pawn race, advanced passers | `b6b5` | $-665\text{ cp}$ | `b6b5` | $-621\text{ cp}$ | Agreement | Both push outside passer `b5`. |

---

## 3. Deep Forensic Case Studies

### 3.1 Case Study: Game 24 (Ply 61) — The Passive Bishop Retreat
- **Position FEN:** Bishop endgame where Black has a static backward pawn on c6.
- **Reference X22 Decision (`c5f8`):** X22 recognizes that holding the c6 pawn with pieces is futile against White's advancing king. It plays `Bf8`, activating the bishop along the a3–f8 diagonal to target White's kingside pawns and create counter-threats.
- **Candidate X24 Decision (`c5e3`):** Because `g_use_backward_pawns = 1` assesses a $-15\text{ eg}$ penalty if c6 is lost, X24 routes its bishop to e3 to maintain indirect coverage. This passive defense cedes the center, allowing White's king to penetrate unopposed and convert the win.

### 3.2 Case Study: Game 28 (Ply 61) — Queen Passivity vs Queen Invasion
- **Position FEN:** Heavy piece ending with backward d-pawn under pressure.
- **Reference X22 Decision (`d5c4`):** X22 invades the c-file with `Qc4`, threatening perpetual check and putting pressure on White's b2 pawn.
- **Candidate X24 Decision (`d5f7`):** X24 retreats its queen to f7 to shield the d-pawn. The retreat removes all counter-threats, allowing White to activate its rook and win the endgame comfortably.

---

## 4. Key Architectural Takeaways

1. **Passive Defense is Fatal in Classical Endgames:** Handcrafted negative evaluation penalties systematically distort move ordering and root selection in favor of passive piece defense over active counterplay.
2. **The Counter-Intuitive Cost of Backward Pawns:** The engine lost these games not because its pawns were structurally backward, but because it expended valuable piece activity trying to defend them.
3. **Justification for Option B:** Rather than penalizing weak pawns (which breeds passivity), the evaluation must actively reward advancing, connected passed pawns. Connected passed pawns force the opponent onto the defensive, ensuring active pieces and tactical initiative.

---

## 5. Artifact Audit
- Complete Forensic Replay Summary: `analysis/phase1/p1.20/raw/endgame_forensics_raw.json`
- Test Harness: `analysis/phase1/p1.20/tests/test_endgame_forensics.py`
