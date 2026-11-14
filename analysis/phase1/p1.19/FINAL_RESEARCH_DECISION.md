# Final Research Decision: Milestone P1.19 Candidate Adjudication

## 1. Formal Milestone Decision

Based on the rigorous empirical evidence compiled across 570 games (100 development games and 470 authoritative tournament games), the independent statistical audit and computer chess evaluation panel issues the following formal verdict:

### **VERDICT: CATEGORY C — REJECTED CANDIDATE**

1. **Janus Classical X24 is REJECTED for Category A (Full Baseline Replacement).**
   - **Janus Classical X7 (`b34e342`)** remains the permanent, immutable qualified single-thread strength baseline.
   - **Janus Classical X12 (`78ca3d5`)** remains the permanent, immutable qualified four-thread SMP strength baseline.
2. **Janus Classical X24 is REJECTED for Category B (Research Reference Promotion).**
   - **Janus Classical X22 (`e33f292`)** is retained as the sole, active, authoritative research reference for Project Janus.
3. **Architectural Disposition of Milestone P1.19 Innovations:**
   - **Track A (Backward Pawns):** Deactivated by default in the engine base (`g_use_backward_pawns = 0`). The term is preserved in the codebase behind the UCI option `UCI_BackwardPawns` for historical research and regression testing.
   - **Track B (King-File Exposure):** Permanently excised and locked at `g_use_king_file_exposure = 0`.
   - **Pawn-Hash Architecture:** Preserved and active. The 64K-entry direct-mapped pawn hash table provides a proven $+13.58\%$ evaluation speedup with $100\%$ cache invariance.
   - **Quiescence Search (Q1):** Preserved and active. Full check-evasion generation, stand-pat suppression in check, and negative-SEE capture pruning exemption remain certified.

---

## 2. Statistical Evidence Summary & Gate Analysis

The adjudication is grounded in seven independent authoritative matches:

| Match Designation | Match Purpose | Candidate | Opponent | Games | Score | Win Rate (%) | Elo Delta | Paired 95% CI | Two-Sided $p$-value | Gate Result |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Match 1** | Primary Research Gate | X24-S (1T) | Reference X22-S | 100 | 48.0 | 48.0% | -13.9 | [39.62%, 56.38%] | $p = 0.6400$ | **FAIL** |
| **Match 2** | 1T Baseline Promotion | X24-S (1T) | Baseline X7 | 100 | 48.0 | 48.0% | -13.9 | [41.46%, 54.54%] | $p = 0.5491$ | **FAIL** |
| **Match 3** | 4T SMP Baseline Promotion | X24-P (4T) | Baseline X12 | 100 | 47.0 | 47.0% | -20.9 | [38.76%, 55.24%] | $p = 0.4755$ | **FAIL** |
| **Match 4** | Slow TC Robustness | X24-S (1T) | Baseline X7 | 50 | 18.5 | 37.0% | -92.5 | [26.75%, 47.25%] | $p = 0.0129$ | **REGRESSION** |
| **Match 5** | Historical Benchmark | X24-S (1T) | Stockfish 4 | 40 | 0.0 | 0.0% | $-\infty$ | [0.00%, 0.00%] | $p = 0.0000$ | External |
| **Match 6** | Classical Benchmark | X24-S (1T) | Stockfish 11 | 40 | 1.0 | 2.5% | -636.4 | [0.00%, 5.87%] | $p = 0.0000$ | External |
| **Match 7** | Modern SOTA Benchmark | X24-S (1T) | Stockfish 19 | 40 | 2.5 | 6.25% | -470.4 | [1.38%, 11.12%] | $p = 0.0000$ | External |

---

## 3. Detailed Justification for Category C Verdict

### 3.1 Failure of the Primary Research Gate (Match 1)
To qualify as a new Research Reference (Category B), Candidate X24 was required to establish statistically significant superiority over Reference X22 ($p < 0.05$ and win rate $> 50.0\%$).
- Result: Score was 48.0% (-13.9 Elo, $p = 0.6400$).
- Statistical interpretation: The observed win rate of 48.0% is completely consistent with random noise around parity ($\mu = 0.50$). There is zero statistical evidence that isolated backward pawns improve playing strength over Reference X22.

### 3.2 Failure of Baseline Promotion (Matches 2 & 3)
To displace the long-standing Baselines X7 and X12, Candidate X24 was required to achieve a paired 95% confidence interval lower bound strictly above $50.0\%$ with $p < 0.05$.
- Result vs X7 (1T): Score was 48.0% with CI lower bound of 41.46% ($p = 0.5491$).
- Result vs X12 (4T): Score was 47.0% with CI lower bound of 38.76% ($p = 0.4755$).
- Candidate X24 fails to replace either baseline.

### 3.3 Disqualification by Slow Time Control Regression (Match 4)
In Match 4 (3.0s + 100ms), Candidate X24-S collapsed to **37.0%** against Baseline X7, with a statistically significant two-sided p-value of **0.0129** ($p < 0.05$) and an upper CI bound of only 47.25%.
- This demonstrates that backward-pawn penalties introduce static positional bias that harms deep search trees in complex endgames.
- Under the Project Janus charter, any candidate exhibiting statistically significant regression at slow time controls is disqualified from adoption.

---

## 4. Preservation & Repository State

1. **Source Code State:**
   - Candidate X24's source changes are cleanly incorporated into `engine/classical_x/janus_classical_x.cpp` under compile-time and runtime option control.
   - Default configuration maintains `g_use_backward_pawns = 0` and `g_use_king_file_exposure = 0`, matching the proven Reference X22 evaluation profile while retaining the 64K pawn-hash performance acceleration.
2. **Archival Assets:**
   - Executables, DLLs, and source for X24 are permanently preserved in `analysis/phase1/p1.19/control/` under verified SHA-256 checksums.
   - All 570 PGN games and raw JSON telemetry are permanently archived in `analysis/phase1/p1.19/pgn/` and `analysis/phase1/p1.19/raw/`.
3. **Branch Integrity:**
   - The milestone concludes on branch `phase1/classical-janus` via a single atomic commit, with zero remote git push.
