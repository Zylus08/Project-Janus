# PROJECT JANUS v0.53 — TOURNAMENT MATCH PREREGISTRATION

**Document Type:** Formal Experimental Preregistration  
**Milestone:** v0.53  
**Date:** 2026-11-05  
**Protocol:** Controlled Head-to-Head Strength Ablation (Candidate N4 vs. Baseline N3)  

---

## 1. Experimental Objective

Evaluate whether Principal Variation Search (PVS) provides a statistically significant playing-strength improvement over the frozen production baseline Janus Native N3 (LMR enabled, PVS disabled) under strict Fischer time controls and verified FIDE adjudication rules.

The match is preregistered to prevent cherry-picking, post-hoc stopping, or metric substitution.

---

## 2. Competing Engine Configurations

Both configurations execute using the identical native binary `janus_native_engine.exe`, parameterized exclusively via UCI options prior to each game:

### Control: Janus Native N3 (Production Baseline)
- **Binary:** `janus_native_engine.exe` (SHA-256: `2822ec90e10bf885c75d8f68ed1e6f82cead8d4eb8650d974eca98db0cf3271a`)
- **UCI Options:**
  - `setoption name UsePVS value false`
  - `setoption name UseLMR value true`
  - `setoption name LMRMinDepth value 3`
  - `setoption name LMRMoveThreshold value 4`
  - `setoption name LMRBaseReduction value 1`

### Candidate: Janus Native N4 (Experimental PVS)
- **Binary:** `janus_native_engine.exe` (SHA-256: `2822ec90e10bf885c75d8f68ed1e6f82cead8d4eb8650d974eca98db0cf3271a`)
- **UCI Options:**
  - `setoption name UsePVS value true`
  - `setoption name UseLMR value true`
  - `setoption name LMRMinDepth value 3`
  - `setoption name LMRMoveThreshold value 4`
  - `setoption name LMRBaseReduction value 1`

---

## 3. Cryptographic Artifact Integrity

| Component | Path | SHA-256 Checksum |
| :--- | :--- | :--- |
| **C++ Search Engine Source** | `analysis/v0.53/native/janus_native.cpp` | `191684be4b96ae878cde775bba82b9f7c49ee82a544c2289cce6484f15299970` |
| **Engine Binary** | `analysis/v0.53/native/janus_native_engine.exe` | `2822ec90e10bf885c75d8f68ed1e6f82cead8d4eb8650d974eca98db0cf3271a` |
| **Engine Shared Library** | `analysis/v0.53/native/janus_native.dll` | `dbaa1826dcb7a87554ebf8618f8ef8a3ec8fc34459dd0d07ed0ba6cf2024e36a` |
| **Opening Suite (100 pairs)** | `analysis/v0.53/corpus/openings_v052_100.json` | `2f929719ab8377e1682b3c37c6b93c762a8898bca9284aa3797db936391aca3b` |
| **Tournament Controller** | `analysis/v0.53/tests/tournament_controller.py` | `d46f868c8d7789c8593f7a5bf47e3509a7cee53dcc8b1fc78ccb21be10dbc9fe` |

---

## 4. Tournament Structure & Rules

- **Total Rounds:** 100 opening pairs (200 total games).
- **Color Inversion:** Strict alternating colors per pair:
  - Game 1: White = N4, Black = N3.
  - Game 2: White = N3, Black = N4.
- **Time Control:** Fischer 3.0s base + 100ms increment (`wtime 3000 btime 3000 winc 100 binc 100`).
- **Opening Corpus:** 100 balanced openings (2 to 4 plies), exactly matching the v0.51 and v0.52 benchmark corpora.
- **Transposition Table:** Reset via `ucinewgame` before every single game.
- **Adjudication Engine:** `tournament_controller.py`:
  - FIDE Checkmate (1-0 / 0-1)
  - FIDE Stalemate (1/2-1/2)
  - FIDE Insufficient Material (1/2-1/2)
  - FIDE Threefold Repetition Claim (1/2-1/2)
  - FIDE Fivefold Repetition Mandatory (1/2-1/2)
  - FIDE 50-Move Rule Claim (1/2-1/2)
  - FIDE 75-Move Rule Mandatory (1/2-1/2)
  - Non-FIDE Safety Circuit Breaker: 300 plies (150 full moves) without termination $\rightarrow$ Draw (flagged as `safety_limit_300_plies`).
- **Parallelization:** 8 worker processes on the 16-thread host architecture.

---

## 5. Statistical Hypotheses & Success Criteria

- **Null Hypothesis ($H_0$):** PVS does not improve playing strength ($\Delta \text{Elo} \le 0$, mean paired difference $\mu_d \le 0$).
- **Alternative Hypothesis ($H_1$):** PVS improves playing strength ($\Delta \text{Elo} > 0$, $\mu_d > 0$).
- **Primary Metric:** Paired opening-difference score:
  $$d_i = \text{Score}_{N4, i} - \text{Score}_{N3, i} \in \{-2, -1.5, -1, -0.5, 0, +0.5, +1, +1.5, +2\}$$
- **Significance Test:** Two-sided Student's paired $t$-test ($df = 99$), with $\alpha = 0.05$.
- **Secondary Evaluation:** 100,000 paired bootstrap resamples to establish the 95% confidence interval of the mean point delta and Elo advantage.

---

## 6. Preregistration Freeze Confirmation

This preregistration document is authored and committed prior to launching the match runner. The tournament controller, binary checksums, and experimental settings will not be altered during the match.

