# Project Janus — Chess-first ML Engine

Project Janus is a research-driven chess engine project. The first milestone is a reproducible, working baseline:
- legal chess rules via `python-chess`
- custom negamax + alpha-beta search
- iterative deepening, quiescence search, transposition table, move ordering
- UCI protocol support
- fixed-position smoke tests and reproducible configuration

This is intentionally **not yet the ML engine**. We first need a reliable search baseline against which learned evaluators and neural-first approaches can be measured.

## Requirements

- Python 3.10+
- `python-chess`

## Setup

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

python -m pip install -r requirements.txt
```

## Run the engine

```bash
python -m janus.uci
```

The process speaks UCI on stdin/stdout. You can load it in a UCI-compatible GUI (for example, a local chess GUI that supports custom engines).

## Run tests

From the repository root:

```bash
python -m unittest discover -s tests -v
```

## Quick protocol smoke test

```text
uci
isready
position startpos
go depth 3
quit
```

Expected protocol responses include `uciok`, `readyok`, `info ...`, and `bestmove ...`. Search results are deterministic at a fixed depth for a fixed position and configuration, except for any future explicitly enabled randomness.

## Current limitations

- The evaluator is handcrafted and deliberately simple.
- Search is single-threaded.
- The first UCI implementation handles `go depth N` and `go movetime N`; it does not yet implement asynchronous `stop`, ponder, multi-PV, or all UCI options.
- This baseline is not expected to compete with Stockfish yet.
- Search speed and playing strength must be measured, not assumed.

## Project roadmap

1. **Baseline (current):** rules integration, search, UCI, smoke tests.
2. **Benchmark harness:** fixed positions, nodes/time, engine-vs-engine matches.
3. **Learned evaluator:** train a compact model from strong-engine evaluations.
4. **Neural-first path:** policy/value network + MCTS/self-play.
5. **Research:** test specific hypotheses under fixed compute budgets.

## Reproducibility

Keep changes to evaluation, search and training isolated. For every experiment, record:
- git commit
- config
- training data provenance
- hardware and software versions
- time/node budget
- test positions and match results
