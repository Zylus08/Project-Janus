"""Run reproducible fixed-position benchmarks for Project Janus."""
from __future__ import annotations

import argparse
import csv
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chess

# Permit running directly from the repository root without an editable install.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from janus.search import JanusSearch  # noqa: E402


def git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
            stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def load_positions(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError(f"Expected a non-empty JSON list in {path}")
    seen: set[str] = set()
    for item in data:
        for field in ("id", "category", "description", "fen"):
            if not isinstance(item.get(field), str) or not item[field]:
                raise ValueError(f"Each position needs a non-empty {field!r}: {item}")
        if item["id"] in seen:
            raise ValueError(f"Duplicate position id: {item['id']}")
        seen.add(item["id"])
        board = chess.Board(item["fen"])
        if not board.is_valid():
            raise ValueError(f"Invalid chess position {item['id']}: {item['fen']}")
        expected = item.get("expected_best_moves")
        if expected is not None and not isinstance(expected, list):
            raise ValueError(f"expected_best_moves must be a list for {item['id']}")
    return data


def _validate_pv(board: chess.Board, pv: list[chess.Move]) -> bool:
    """Return True if every PV move is legal when played in sequence."""
    verify = board.copy()
    for move in pv:
        if move not in verify.legal_moves:
            return False
        verify.push(move)
    return True


def run_benchmark(
    positions: list[dict[str, Any]],
    depth: int,
    time_limit: float | None,
    enable_history: bool = True,
) -> dict[str, Any]:
    engine = JanusSearch(enable_history=enable_history)
    rows: list[dict[str, Any]] = []
    for position in positions:
        board = chess.Board(position["fen"])
        # Cold-start measurement: no information carried over from prior positions.
        engine.tt.clear()
        result = engine.search(board, max_depth=depth, time_limit=time_limit)
        best_move = None if result.best_move is None else result.best_move.uci()
        pv = " ".join(move.uci() for move in result.pv)
        expected = position.get("expected_best_moves")
        expected_match = None if expected is None else (best_move in expected if expected else best_move is None)
        rows.append({
            "id": position["id"],
            "category": position["category"],
            "description": position["description"],
            "fen": position["fen"],
            "requested_depth": depth,
            "completed_depth": result.depth,
            "score_from_side_to_move": result.score,
            "best_move_uci": best_move or "",
            "pv_uci": pv,
            "nodes": result.nodes,
            "elapsed_seconds": round(result.elapsed, 6),
            "nodes_per_second": round(result.nodes / result.elapsed, 2) if result.elapsed > 0 else 0.0,
            "expected_move_match": expected_match,
            "legal_best_move": result.best_move is None or result.best_move in board.legal_moves,
            "pv_legal": _validate_pv(board, result.pv),
        })

    return {
        "metadata": {
            "engine": "Project Janus",
            "engine_version": "0.2.0",
            "git_commit": git_commit(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "python_version": platform.python_version(),
            "python_chess_version": getattr(chess, "__version__", "unknown"),
            "requested_depth": depth,
            "time_limit_seconds": time_limit,
            "history_heuristic_enabled": enable_history,
            "transposition_table_policy": "cleared before each position (cold start)",
            "score_convention": "score_from_side_to_move is from the side-to-move perspective; mate scores remain encoded near +/-100000",
        },
        "summary": {
            "positions": len(rows),
            "legal_best_moves": sum(bool(row["legal_best_move"]) for row in rows),
            "pv_legal_count": sum(bool(row["pv_legal"]) for row in rows),
            "expected_move_checks": sum(row["expected_move_match"] is not None for row in rows),
            "expected_move_matches": sum(row["expected_move_match"] is True for row in rows),
            "total_nodes": sum(row["nodes"] for row in rows),
            "total_elapsed_seconds": round(sum(row["elapsed_seconds"] for row in rows), 6),
        },
        "results": rows,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--positions", type=Path, default=ROOT / "benchmarks" / "positions.json")
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--time-limit", type=float, default=None,
                        help="Optional per-position time limit in seconds")
    parser.add_argument("--no-history", action="store_true",
                        help="Disable quiet-move history heuristic")
    parser.add_argument("--out", type=Path, default=ROOT / "benchmark-results")
    args = parser.parse_args()

    if args.depth < 1:
        parser.error("--depth must be >= 1")
    if args.time_limit is not None and args.time_limit <= 0:
        parser.error("--time-limit must be > 0")

    try:
        positions = load_positions(args.positions)
        report = run_benchmark(
            positions, args.depth, args.time_limit, enable_history=not args.no_history
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Benchmark error: {exc}", file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = args.out / f"janus-benchmark-{stamp}.json"
    csv_path = args.out / f"janus-benchmark-{stamp}.csv"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_csv(csv_path, report["results"])

    print(f"Janus benchmark complete: {report['summary']['positions']} positions")
    print(f"Requested depth: {args.depth}; time limit: {args.time_limit}")
    print(f"Legal best moves: {report['summary']['legal_best_moves']}/{report['summary']['positions']}")
    print(f"Total nodes: {report['summary']['total_nodes']}")
    print(f"Total search time: {report['summary']['total_elapsed_seconds']:.3f}s")
    print(f"JSON: {json_path}")
    print(f"CSV:  {csv_path}")
    print("\nPer-position results:")
    for row in report["results"]:
        print(
            f"  {row['id']:<18} depth={row['completed_depth']:<2} "
            f"nodes={row['nodes']:<8} time={row['elapsed_seconds']:.3f}s "
            f"best={row['best_move_uci'] or '(none)':<6} "
            f"expected_match={row['expected_move_match']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
