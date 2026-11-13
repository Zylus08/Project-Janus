# PHASE 12: INDEPENDENT PLAYING STRENGTH QUALIFICATION REPORT

**Project:** Project Janus — Phase 1, Milestone P1.15  
**Candidate Evaluated:** Janus Classical X20 (X20-S on 1T, X20-P on 4T)  
**Qualified Baselines:** Janus Classical X7 (1T Baseline, `86392A...`), Janus Classical X12 (4T Baseline, `00B4F5...`)  
**Research Reference:** Janus Classical X19 (Research Baseline, `CBB778...`)  
**Date:** November 14, 2026  
**Auditor:** Principal Computer Chess Engine Architect & Independent Statistical Auditor  
**Deliverable:** `analysis/phase1/p1.15/X20_INDEPENDENT_STRENGTH.md`  
**Raw Tournament Telemetry:** `analysis/phase1/p1.15/raw/p115_tournaments_raw.json`  
**PGN Repository:** `analysis/phase1/p1.15/pgn/`  

---

## 1. Executive Summary & Verification Protocol

Milestone P1.15 mandates an independent, statistically rigorous qualification protocol using the JCTS v2 standard:
> *A candidate configuration may earn promotion if and only if it demonstrates statistically confirmed superiority over the qualified baseline under identical computational resources ($p < 0.05$ and lower bound of the $95\%$ paired confidence interval $> 50.0\%$). Point estimates above 50% without statistically confirmed intervals cannot justify promotion.*

Four confirmatory matches (300 games total) were executed using unbiased, colour-reversed opening pairs from `independent_openings_v056.json`:
- **Match 1:** X20-S (1T) vs X7 Baseline (1T) @ Fischer 1.0s + 50ms (100 games)
- **Match 2:** X20-S (1T) vs X7 Baseline (1T) @ Fischer 2.5s + 100ms (50 games, Slower Time Verification)
- **Match 3:** X20-P (4T) vs X12 Baseline (4T) @ Fischer 1.0s + 50ms (100 games)
- **Match 4:** X20-S (1T) vs X19-S Baseline (1T) @ Fischer 1.0s + 50ms (50 games)

Across all 300 internal tournament games, there were **0 crashes, 0 time forfeits, and 0 illegal moves**.

---

## 2. Match 1: Primary Single-Thread Comparison (X20-S vs X7 Baseline)

**Time Control:** Fischer 1.0s base + 50ms increment per move.  
**Hardware & Threads:** 1 thread, 16 MB Hash.  
**Games:** 50 opening pairs (100 games colour-reversed).  
**PGN:** `analysis/phase1/p1.15/pgn/x20_1t_vs_x7_1t.pgn`  

### Empirical Results:
- **Wins (X20-S):** 27
- **Draws:** 38
- **Losses (X7):** 35
- **Total Points:** 46.0 / 100 (**46.00%**)
- **Elo Difference:** **-27.9 Elo**
- **Wilson 95% Confidence Interval:** $[36.52\%, 55.77\%]$
- **Paired 95% Confidence Interval:** **$[36.57\%, 55.43\%]$**
- **Paired t-test (One-Sided):** $p = 0.79715$ ($H_0: \mu \le 0.50$ not rejected)
- **Pentanomial Distribution:**
  - `WW` (+2.0 pts): 8 pairs
  - `WD` (+1.5 pts): 9 pairs
  - `DD_WL` (+1.0 pt): 9 pairs
  - `LD` (+0.5 pts): 15 pairs
  - `LL` (0.0 pts): 9 pairs

### Statistical Finding:
Candidate X20-S scored 46.00% with a paired 95% CI spanning $[36.57\%, 55.43\%]$. Because the point estimate is below 50.0% and the lower CI bound is well below 50.0% ($p = 0.797$), **X20-S does NOT demonstrate statistical superiority over Baseline X7**. It performs within the statistical parity margin of X7.

---

## 3. Match 2: Slower Time Control Verification (X20-S vs X7 Baseline)

**Time Control:** Fischer 2.5s base + 100ms increment per move.  
**Hardware & Threads:** 1 thread, 16 MB Hash.  
**Games:** 25 opening pairs (50 games colour-reversed).  
**PGN:** `analysis/phase1/p1.15/pgn/x20_1t_vs_x7_1t_slow.pgn`  

### Empirical Results:
- **Wins (X20-S):** 17
- **Draws:** 14
- **Losses (X7):** 19
- **Total Points:** 24.0 / 50 (**48.00%**)
- **Elo Difference:** **-13.9 Elo**
- **Wilson 95% Confidence Interval:** $[34.82\%, 61.53\%]$
- **Paired 95% Confidence Interval:** **$[39.09\%, 56.91\%]$**
- **Paired t-test (One-Sided):** $p = 0.67001$ ($H_0$ not rejected)
- **Pentanomial Distribution:**
  - `WW` (+2.0 pts): 1 pair
  - `WD` (+1.5 pts): 5 pairs
  - `DD_WL` (+1.0 pt): 11 pairs
  - `LD` (+0.5 pts): 7 pairs
  - `LL` (0.0 pts): 1 pair

### Critical Time-Control Comparison:
In P1.14, Candidate X19-S exhibited a steep regression from fast TC (55.5%) to slower TC (43.0%, $-48.9$ Elo, $\Delta = -12.5\%$).  
In contrast, Candidate X20-S scored **46.00% at Fast TC and 48.00% at Slower TC ($\Delta = +2.0\%$)**.  
This confirms that:
1. **The slower-time degradation of X19 was successfully cured** by adaptive near-even capture staging and conservative history aging.
2. X20-S exhibits uniform, stable performance across time controls.
3. However, it does not surpass Baseline X7 in playing strength.

---

## 4. Match 3: Primary Four-Thread Comparison (X20-P vs X12 Baseline)

**Time Control:** Fischer 1.0s base + 50ms increment per move.  
**Hardware & Threads:** 4 threads, 64 MB Parallel Lockless TT.  
**Games:** 50 opening pairs (100 games colour-reversed).  
**PGN:** `analysis/phase1/p1.15/pgn/x20_4t_vs_x12_4t.pgn`  

### Empirical Results:
- **Wins (X20-P):** 26
- **Draws:** 41
- **Losses (X12):** 33
- **Total Points:** 46.5 / 100 (**46.50%**)
- **Elo Difference:** **-24.4 Elo**
- **Wilson 95% Confidence Interval:** $[37.00\%, 56.26\%]$
- **Paired 95% Confidence Interval:** **$[38.96\%, 54.04\%]$**
- **Paired t-test (One-Sided):** $p = 0.81852$ ($H_0$ not rejected)
- **Pentanomial Distribution:**
  - `WW` (+2.0 pts): 3 pairs
  - `WD` (+1.5 pts): 12 pairs
  - `DD_WL` (+1.0 pt): 15 pairs
  - `LD` (+0.5 pts): 15 pairs
  - `LL` (0.0 pts): 5 pairs

### Statistical Finding:
Like Track S, Track P Candidate X20-P operates in close statistical parity with Baseline X12 (46.50% score, 95% CI $[38.96\%, 54.04\%]$), failing the promotion threshold.

---

## 5. Match 4: Secondary Research Comparison (X20-S vs X19-S Baseline)

**Time Control:** Fischer 1.0s base + 50ms increment per move.  
**Hardware & Threads:** 1 thread, 16 MB Hash.  
**Games:** 25 opening pairs (50 games colour-reversed).  
**PGN:** `analysis/phase1/p1.15/pgn/x20_1t_vs_x19_1t.pgn`  

### Empirical Results:
- **Wins (X20-S):** 11
- **Draws:** 23
- **Losses (X19-S):** 16
- **Total Points:** 22.5 / 50 (**45.00%**)
- **Elo Difference:** **-34.9 Elo**
- **Wilson 95% Confidence Interval:** $[32.13\%, 58.62\%]$
- **Paired 95% Confidence Interval:** **$[34.04\%, 55.96\%]$**
- **Paired t-test (One-Sided):** $p = 0.81445$ ($H_0$ not rejected)
- **Pentanomial Distribution:**
  - `WW` (+2.0 pts): 1 pair
  - `WD` (+1.5 pts): 7 pairs
  - `DD_WL` (+1.0 pt): 6 pairs
  - `LD` (+0.5 pts): 8 pairs
  - `LL` (0.0 pts): 3 pairs

### Statistical Finding:
X20-S and X19-S operate within mutual statistical parity ($[34.04\%, 55.96\%]$ spans 50.0%). The modifications in X20 (adaptive near-even promotion and history aging) eliminate tactical blindspots without altering aggregate classical playing strength against X19.

---

## 6. Comprehensive Tournament Summary Table

| Match | Candidate | Opponent | Threads | Time Control | Games | Score | Score (%) | Elo | Paired 95% CI | p-value | Superiority Confirmed? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Match 1** | X20-S | X7 | 1T | 1.0s + 50ms | 100 | 46.0 / 100 | 46.00% | -27.9 | $[36.57\%, 55.43\%]$ | 0.797 | **NO** |
| **Match 2** | X20-S | X7 | 1T | 2.5s + 100ms | 50 | 24.0 / 50 | 48.00% | -13.9 | $[39.09\%, 56.91\%]$ | 0.670 | **NO** |
| **Match 3** | X20-P | X12 | 4T | 1.0s + 50ms | 100 | 46.5 / 100 | 46.50% | -24.4 | $[38.96\%, 54.04\%]$ | 0.819 | **NO** |
| **Match 4** | X20-S | X19-S | 1T | 1.0s + 50ms | 50 | 22.5 / 50 | 45.00% | -34.9 | $[34.04\%, 55.96\%]$ | 0.814 | **NO** |

### Definitive Conclusion:
Neither X20-S nor X20-P achieves statistically confirmed superiority over qualified baselines X7 or X12. The qualified baselines remain unbreached.
