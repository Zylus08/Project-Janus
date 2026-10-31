# Project Janus v0.40 — Controlled Scientific Experiment Protocol

## 1. Governance and Preregistration

This document formalizes the scientific validation protocol, evaluation parameters, and statistical stopping rules governing all controlled experiments conducted in Project Janus milestone v0.40.

### Starting Environment and Provenance
- **Repository:** `E:\ChessXML\project-janus`
- **Branch:** `v0.3-benchmark-harness`
- **Baseline Git Commit:** `790f533` (v0.39 milestone report and audit commit)
- **Stockfish Binary:** `E:\ChessXML\tools\stockfish\stockfish.exe`
  - **Stockfish Version:** Stockfish 19
  - **SHA-256 Digest:** `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`
- **Opening Suite:** `benchmarks/openings.json`
  - **Openings Count:** 50 opening lines
  - **SHA-256 Digest:** `e883cd4908b73df70b4c1363b00b581caec249494aa1a7720d184c68aaf53af3`
  - **Deterministic Sampling Seed:** 42
- **Host Architecture:** AMD64 Windows 11 (Python 3.13.2)
- **Clock Mode:** Real-time monotonic clock (`time.monotonic()`)

---

## 2. Experimental Candidates Under Evaluation

All experiments test isolated search or evaluation modifications against Stockfish 19 configured at calibrated Elo 1320 (`UCI_LimitStrength = True`, `UCI_Elo = 1320`, `Threads = 1`, `Hash = 64`).

| Candidate ID | Name | Configuration Details | Isolated Flag | Target Question |
|:---|:---|:---|:---|:---|
| **K0** | Baseline Reference | Q0 quiescence + v0.39 full tapered evaluation (pawn, rook files, castled & uncastled king safety) + Arm C adaptive time management. | Baseline default | Calibrated baseline against Stockfish 19 Elo 1320. |
| **K1** | King-Safety Ablation | Baseline evaluation minus uncastled king safety penalty terms. | `--disable-uncastled-king-safety` | Does penalizing exposed central uncastled kings provide measurable playing-strength improvement? |
| **ORD1** | Move Ordering Heuristics | Baseline + Countermove Heuristic (score 550,000) + History Malus penalty on failed quiets (`- depth^2`). | `--enable-ord1` (`--enable-countermove`, `--enable-history-penalty`) | Does quiet move ordering discrimination reduce search tree size and improve playing strength? |
| **RFP** | Reverse Futility Pruning | Baseline + Static Null Move Pruning ($d \le 2$, margin $120\text{ cp} \times d$, check-exempt). | `--enable-rfp` | Can aggressive frontier pruning improve search efficiency safely without tactical blindness? |

---

## 3. Match Architecture and Control Mechanics

### Time Control
- **Base Clock:** 3,000 ms (3.0 seconds).
- **Fischer Increment:** 100 ms (0.1 seconds per move).
- **Time Management Policy:** `arm_c` (v0.35/v0.36 adaptive Fischer time manager with emergency reservation, move-to-go scaling, and increment utilization).

### Pairing and Balancing Rule
- **Design:** Colour-reversed opening pairs.
- **Pair Structure:** For each opening $i$, Game $2i - 1$ assigns Janus as White; Game $2i$ assigns Janus as Black.
- **Sample Size:** 50 games (25 complete colour-reversed pairs) per candidate.
- **Stopping Rule:** Fixed sample size of 50 valid games. No optional early stopping based on interim win/loss trajectories.

### Infrastructure Failure and Exclusion Policy
1. **Zero Silent Exclusion:** No game may be discarded due to difficult positions, lost endgames, or low evaluation scores.
2. **Crash & Timeout Handling:** If an engine process crashes or violates UCI protocol during a move, the attempt is logged as an `infrastructure_failure` with stack trace and process return code.
3. **Deterministic Retries:** The failed game slot is replayed using the exact same opening FEN, assigned colors, and time control, up to a maximum of 3 attempts per slot.
4. **Audit Logging:** Every attempt (successful or failed) is permanently preserved in `attempts.json`.

---

## 4. Statistical Analysis Methodology

### Primary Outcomes
1. **Total Score:** $S = W + 0.5 \times D$.
2. **Win Percentage:** $P = S / N$.
3. **Paired Score Difference:** For pair $k \in \{1, \dots, 25\}$,
   $$d_k = s_{k, \text{White}} + s_{k, \text{Black}} - 1.0 \in \{-1.0, -0.5, 0.0, +0.5, +1.0\}$$
   Mean paired difference $\bar{d} = \frac{1}{25} \sum_{k=1}^{25} d_k$.

### Hypothesis Testing
- **Paired Two-Tailed t-test:** Testing null hypothesis $H_0: \bar{d} = 0$ against two-sided alternative $H_1: \bar{d} \ne 0$.
- **p-value Threshold:** Significance assessed at $\alpha = 0.05$.

### Confidence Intervals
- **Pair Bootstrap Interval:** 10,000 paired bootstrap resamples of opening pairs with replacement.
- **Interval Bounds:** 2.5th and 97.5th percentiles of bootstrap distribution for score and Elo difference.
- **Logistic Elo Conversion:**
  $$\Delta \text{Elo} = -400 \log_{10} \left( \frac{1}{P} - 1 \right)$$
  For boundary conditions ($P = 0$ or $P = 1$), Laplace smoothing / continuity correction is applied to prevent infinite limits.

### Multiple Comparison Safeguard
Because multiple experimental candidates (K1, ORD1, RFP) are evaluated against the same Stockfish 1320 benchmark, exploratory comparisons are explicitly distinguished from confirmatory preregistered hypotheses to guard against data dredging.

