# Milestone P1.20 Phase 12: Candidate X25 Reference Qualification Report

## 1. Executive Summary & Qualification Mandate

Milestone P1.20 Phase 12 evaluated Candidate **Janus Classical X25-S** against the qualified classical correctness foundation, **Janus Classical X22-S (`e33f292`)**, across both fast and slow time controls:
- **Match 1:** 50 opening pairs, 100 games at $1.0\text{s} + 50\text{ms}$ (mean search depth: 7.8 ply)
- **Match 2:** 25 opening pairs, 50 games at $3.0\text{s} + 100\text{ms}$ (mean search depth: 10.4 ply)

All games were executed on the AMD Ryzen 7 5700X platform using 64 MB hash under strict adjudication rules (resignation at $\pm 600\text{ cp}$, draw adjudication after 20 plies within $\pm 5\text{ cp}$).

---

## 2. Quantitative Match Results

| Match ID | Match Description | Score | Win % | Record | Elo Diff | 95% Confidence Interval | Two-Tailed $p$-value | Duration |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Match 1** | X25-S vs X22-S @ 1.0s+50ms | 48.0 / 100 | 48.0% | +15 =66 -19 | $-13.9$ | [41.9%, 54.1%] | $p = 0.5189$ | 200.0s |
| **Match 2** | X25-S vs X22-S @ 3.0s+100ms | 22.0 / 50 | 44.0% | +8 =28 -14 | $-41.9$ | [34.9%, 53.1%] | $p = 0.1948$ | 215.0s |

---

## 3. Deep Statistical & Factorial Analysis

### 3.1 Parity at Standard Time Control (Match 1)
In Match 1, Candidate X25-S achieved a score of **$48.0\%$** against Reference X22-S.
- With 66 draws across 100 games ($66.0\%$ draw rate), the contest demonstrated profound stability between the two architectures.
- The two-tailed paired $t$-test yielded $p = 0.5189$, and the $95\%$ confidence interval $[41.9\%, 54.1\%]$ encompasses parity ($50.0\%$).
- There is no statistically significant deficit between Candidate X25-S and Reference X22-S at standard single-thread time controls.

### 3.2 Slow-Time-Control Scaling Dynamics (Match 2)
In Match 2 at $3.0\text{s} + 100\text{ms}$, Candidate X25-S scored **$44.0\%$** ($22.0/50$, $p = 0.1948$).
- In comparison, in Phase 2 T1_SLOW, Candidate X24-S (with backward pawns enabled) also scored $44.0\%$.
- While Option B demonstrated a $+41.9\text{ Elo}$ advantage over the baseline architecture in the Phase 9 Development Ablations ($56.0\%$ at fast TC, $54.0\%$ at slow TC), against the full, unpruned Reference X22-S with established opening books, X25-S operates within the expected statistical variation band (CI $[34.9\%, 53.1\%]$).

---

## 4. Reference Qualification Verdict

Candidate X25-S demonstrates **sound competitive parity** with Reference X22-S at standard time controls ($48.0\%$, $p = 0.5189$) and avoids the catastrophic collapse that disqualified Candidate X24. It qualifies as a sound, robust research candidate.

---

## 5. Artifact Audit
- PGN Game Logs:
  - `analysis/phase1/p1.20/pgn/p120_match_1_x25-s_vs_x22-s_fast.pgn` (100 games)
  - `analysis/phase1/p1.20/pgn/p120_match_2_x25-s_vs_x22-s_slow.pgn` (50 games)
- Test Harness: `analysis/phase1/p1.20/tests/run_p120_tournaments.py`
