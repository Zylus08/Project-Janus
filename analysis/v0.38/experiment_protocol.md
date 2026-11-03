# Project Janus v0.38 — Experiment Protocol: External Engine Strength Benchmark

## 1. Objective and Research Questions

The primary objective of milestone v0.38 is to establish an authoritative, reproducible external playing-strength baseline for Project Janus against Stockfish 19, identify systemic chess weaknesses through quantitative loss forensics, and formulate evidence-based recommendations for future strength development.

### Research Questions
1. **Primary Question:** Under standard Fischer increment time controls ($3000\text{ ms} + 100\text{ ms}$), what match score and Elo differential does Janus v0.38 achieve against unconstrained Stockfish 19?
2. **Historical Progression Question:** In a direct reproduction of the v0.5 fixed search depth 3 benchmark (25 opening pairs, 50 games), does Janus v0.38 demonstrate measurable strength progression over the v0.5 baseline (historical score: $7.5 / 50.0 = 15.0\%$)?
3. **Calibrated Opponent Question:** Against Stockfish 19 calibrated to entry-level club strength (`UCI_LimitStrength=true, UCI_Elo=1320`), what is Janus's performance and rating deficit?
4. **Diagnostic Weakness Question:** What are the most frequent tactical, positional, and time-management causes of Janus's losses against external opposition?

---

## 2. Experimental Architecture

Three distinct benchmark experiments are executed:

### Experiment 1: Primary Benchmark (Fischer Time Control)
- **Candidate:** Janus v0.38 (`Janus-v0.38-Adaptive`, `--eval-all`, `--time-policy arm_c`)
- **Opponent:** Stockfish 19 (`Threads=1, Hash=64, Skill Level=20, UCI_LimitStrength=false`)
- **Time Control:** $3000\text{ ms}$ initial clock $+ 100\text{ ms}$ increment per move (Fischer)
- **Target Games:** 100 valid games (50 complete colour-reversed opening pairs)
- **Opening Suite:** `benchmarks/openings.json` (50 positions, seed 42)

### Experiment 2: Historical Progression Benchmark (Fixed Depth 3)
- **Candidate:** Janus v0.38 (`--eval-all`, `go depth 3`)
- **Opponent:** Stockfish 19 (`Threads=1, Hash=64, go depth 3`)
- **Search Limits:** Fixed depth 3 per move for both engines (`max_plies=240`)
- **Target Games:** 50 valid games (25 complete colour-reversed opening pairs)
- **Opening Suite:** `benchmarks/openings.json` (25 positions, seed 42, matching v0.5)

### Experiment 3: Calibrated Opponent Benchmark (Stockfish Elo 1320)
- **Candidate:** Janus v0.38 (`Janus-v0.38-Adaptive`, `--eval-all`, `--time-policy arm_c`)
- **Opponent:** Stockfish 19 (`Threads=1, Hash=64, UCI_LimitStrength=true, UCI_Elo=1320`)
- **Time Control:** $3000\text{ ms}$ initial clock $+ 100\text{ ms}$ increment per move (Fischer)
- **Target Games:** 50 valid games (25 complete colour-reversed opening pairs)
- **Opening Suite:** `benchmarks/openings.json` (25 positions, seed 42)

---

## 3. Pairing, Supervision, and Exclusion Rules

1. **Colour Balance:** Every opening position is played as a pair: Game 1 with Janus as White, Game 2 with Janus as Black.
2. **Subprocess Lifecycles:** Each game runs in isolated, freshly spawned subprocesses managed by `SupervisedEngineSession`.
3. **Move Legality:** All moves are verified against python-chess board rules before being accepted.
4. **Failure Classification:** Process crashes, pipe hangs, or timeouts are categorized as infrastructure failures and automatically retried (up to 3 attempts per slot) with identical starting FEN and colour assignment. Infrastructure failures are never counted as chess losses.
5. **Adjudication:** Conforms to FIDE checkmate, stalemate, 3-fold repetition, 50-move rule, or 200-ply draw cutoff.

---

## 4. Statistical Inference and Endpoints

- **Primary Endpoint:** Janus's match score $S = \frac{W + 0.5D}{N}$ and paired mean difference $\bar{\Delta} = \frac{1}{M}\sum (P_i - 0.5)$.
- **Hypothesis Testing:** Two-sided paired Student's $t$-test with $df = M - 1$ on opening pairs.
- **Uncertainty Estimation:** 10,000-resample opening-pair bootstrap 95% confidence interval (seed 42).
- **Non-Parametric Verification:** Paired sign test on decisive pairs ($P_i \neq 0.5$) with ties explicitly recorded.
- **Elo Conversion:** $E = -400 \log_{10}(1/S - 1)$ with non-linear uncertainty interval transformation.

---

## 5. Loss Forensics Protocol

All losses suffered by Janus are analyzed through a systematic automated pipeline:
1. Replay each game and evaluate positions using Stockfish 19 at search depth 12.
2. Detect evaluation swings $\ge 150\text{ cp}$ (1.50 pawns) or tactical blunders.
3. Classify critical mistakes into standardized categories:
   - Tactical oversights (hanging pieces, basic pins/forks)
   - Missed defensive moves (failing to meet threats)
   - King safety (pawn shield compromises, open king attacks)
   - Pawn structure (weak pawns, doubled pawns, isolated pawns)
   - Piece activity (passive pieces, trapped rooks/bishops)
   - Endgame conversion (king activity, passed pawns)
   - Time management (time pressure, rush moves)
   - Search instability / horizon effects
   - Opening-related problems
4. Generate a ranked quantitative breakdown of the most promising areas for future improvement.
