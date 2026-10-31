# Project Janus v0.39 — King-Safety Evaluation Audit & Calibration Report

**Milestone:** v0.39 King-Safety Audit & Calibration  
**Subject:** Evaluation Function King Shelter, Open File Exposure, and Castling Incentives  
**Status:** **`VERIFIED_CALIBRATED`**  

---

## 1. Resolution of the v0.34 vs v0.38 Discrepancy

A primary question in the mission specification was resolving the conflicting historical accounts:
> *"The historical v0.34 work reportedly included tapered-evaluation terms for castled-king pawn shields and open-file exposure. The v0.38 report subsequently describes the absence of dedicated king-safety terms as a root cause. Resolve this discrepancy before implementing additional evaluation terms."*

### Exhaustive Code & Provenance Audit
Inspection of `src/janus/evaluation.py` and `src/janus/uci.py` revealed the exact technical truth:
1. **Terms Were Present in Code and Active:** `enable_king_safety` existed in `EvaluationConfig` and was set to `True` in `CONFIG_V034_TAPERED`. When `--eval-all` was passed in the v0.38 benchmarks, `cfg.enable_king_safety` was actively enabled and called inside `_evaluate_white_tapered`.
2. **Defective and Overly Narrow Guard Condition:**
   The implementation in lines 590–630 of `src/janus/evaluation.py` was guarded by strict king-square checks:
   ```python
   if w_king in (chess.G1, chess.H1):
     ...  # Kingside castled
   elif w_king in (chess.B1, chess.C1):
     ...  # Queenside castled
```
3. **The Uncastled King Blindspot:**
   If White's king was on **e1, d1, e2, d2, f1, f2** (i.e. uncastled in the center, or walking out of check), **the condition evaluated to False and executed literally nothing**.
   An uncastled king on an open central e- or d-file received **0 penalty** from the king safety function!
   In Game 27 (Ply 45) of the v0.38 primary match (`N2k1b2/pp3np1/2p5/6p1/3pP3/3P2q1/PP1P1R2/R1BQK2r w - - 1 24`), White's king was on e1/e2 with queens and rooks attacking down open files. Because the king was on e1/e2, the king safety term contributed $0\text{ cp}$, leading the forensic analyst in v0.38 to infer that king-safety terms were entirely missing.
4. **Asymmetric File Coverage:**
   Even when castled kingside (`G1/H1`), the code checked `not g_pawn` and `not h_pawn` for open file penalties, but completely omitted `not f_pawn`. A missing f-pawn opened the king's diagonal and file without penalty.

---

## 2. Refined King Safety Formulation (Candidate K0)

The king safety evaluation was unified and modularized into `_compute_king_safety_mg(...)` in `src/janus/evaluation.py`:

1. **Castled Kingside (`G1`, `H1` / `G8`, `H8`):**
   - Intact shield pawns on f, g, h each grant `+king_shield_bonus_mg` (+8 cp).
   - Missing f, g, or h pawns each incur `-king_open_file_penalty_mg` (−12 cp).
2. **Castled Queenside (`B1`, `C1` / `B8`, `C8`):**
   - Intact shield pawns on a, b, c each grant `+king_shield_bonus_mg` (+8 cp).
   - Missing a, b, or c pawns each incur `-king_open_file_penalty_mg` (−12 cp).
3. **Uncastled Central King (`E1/E8`, `D1/D8`, `F1/F8`, etc.):**
   - In middlegame (`phase > 0`):
     - Semi-open king file (no friendly pawns on file): `-king_open_file_penalty_mg` (−12 cp).
     - Fully open king file (no pawns on file): additional `-king_open_file_penalty_mg` (−12 cp, total −24 cp).
     - Stranded in center without castling rights: `-15 cp` penalty.
4. **Tapering Dynamics:**
   - Evaluated strictly within `mg_score`.
   - As pieces are exchanged and game phase transitions to endgame (`phase -> 0`), shelter penalties smoothly scale to 0.
   - At `phase = 0`, the endgame king centralization term (`king_center_bonus_eg = +12 cp`) takes over, encouraging king activity.

---

## 3. Quantitative Verification Matrix

All 6 test cases in `tests/test_v039_king_safety.py` passed:
- `test_1_castled_solid_shield_bonus`: Solid castled shield yields full bonus.
- `test_2_missing_f_pawn_penalty`: Missing f-pawn penalizes position by $\ge 110\text{ cp}$ (material + shelter).
- `test_3_uncastled_open_central_file_penalty`: Uncastled king on open e-file penalized significantly ($> 30\text{ cp}$) compared to closed e-file.
- `test_4_stranded_central_king_penalty`: Lost castling rights in center penalized by 15 cp.
- `test_5_black_white_symmetry`: Color inversion verified symmetric within 20 cp.
- `test_6_endgame_tapering`: In pure endgame ($phase = 0$), king shelter penalties vanish completely.

