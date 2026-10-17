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
    enable_pvs: bool = True,
    enable_aspiration: bool = True,
    enable_lmr: bool = True,
    enable_nmp: bool = True,
    enable_check_extensions: bool | None = None,
    check_extension_policy: str = "disabled",
    enable_see_ordering: bool = False,
    enable_see_pruning: bool = False,
    tt_replacement_policy: str = "always_replace",
) -> dict[str, Any]:
    if enable_check_extensions is not None:
        if not enable_check_extensions:
            check_extension_policy = "disabled"
        elif check_extension_policy == "disabled":
            check_extension_policy = "bounded_all_checks"

    engine = JanusSearch(
        enable_history=enable_history,
        enable_pvs=enable_pvs,
        enable_aspiration=enable_aspiration,
        enable_lmr=enable_lmr,
        enable_nmp=enable_nmp,
        check_extension_policy=check_extension_policy,
        enable_see_ordering=enable_see_ordering,
        enable_see_pruning=enable_see_pruning,
        tt_replacement_policy=tt_replacement_policy,
    )
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
            "scout_searches": result.scout_searches,
            "scout_fail_highs": result.scout_fail_highs,
            "researches": result.researches,
            "beta_cutoffs": result.beta_cutoffs,
            "aspiration_iterations": result.aspiration_iterations,
            "aspiration_fail_lows": result.aspiration_fail_lows,
            "aspiration_fail_highs": result.aspiration_fail_highs,
            "aspiration_researches": result.aspiration_researches,
            "aspiration_fallbacks": result.aspiration_fallbacks,
            "lmr_considered": result.lmr_considered,
            "lmr_reduced_searches": result.lmr_reduced_searches,
            "lmr_reduced_plies": result.lmr_reduced_plies,
            "lmr_researches": result.lmr_researches,
            "lmr_fail_lows": result.lmr_fail_lows,
            "lmr_fail_highs": result.lmr_fail_highs,
            "lmr_cutoffs": result.lmr_cutoffs,
            "nmp_considered": result.nmp_considered,
            "nmp_attempts": result.nmp_attempts,
            "nmp_fail_highs": result.nmp_fail_highs,
            "nmp_fail_lows": result.nmp_fail_lows,
            "nmp_verifications": result.nmp_verifications,
            "nmp_verification_failures": result.nmp_verification_failures,
            "nmp_cutoffs": result.nmp_cutoffs,
            "check_extensions_eligible": result.check_extensions_eligible,
            "check_extensions_applied": result.check_extensions_applied,
            "check_extension_plies": result.check_extension_plies,
            "check_extensions_suppressed": result.check_extensions_suppressed,
            "check_extensions_multiple_replies": result.check_extensions_multiple_replies,
            "check_extensions_terminal_mates": result.check_extensions_terminal_mates,
            "see_evaluations": result.see_evaluations,
            "captures_ordered_see": result.captures_ordered_see,
            "qsearch_captures_considered": result.qsearch_captures_considered,
            "qsearch_captures_pruned": result.qsearch_captures_pruned,
            "qsearch_captures_exempted": result.qsearch_captures_exempted,
            "see_cache_hits": result.see_cache_hits,
            "tt_replacement_policy": result.tt_replacement_policy,
            "tt_probes": result.tt_probes,
            "tt_hits": result.tt_hits,
            "tt_usable_hits": result.tt_usable_hits,
            "tt_cutoffs": result.tt_cutoffs,
            "tt_stores": result.tt_stores,
            "tt_same_key_updates": result.tt_same_key_updates,
            "tt_same_key_overwrites": result.tt_same_key_overwrites,
            "tt_same_key_rejected": result.tt_same_key_rejected,
            "tt_clears": result.tt_clears,
        })

    return {
        "metadata": {
            "engine": "Project Janus",
            "engine_version": "0.2.3",
            "git_commit": git_commit(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "python_version": platform.python_version(),
            "python_chess_version": getattr(chess, "__version__", "unknown"),
            "requested_depth": depth,
            "time_limit_seconds": time_limit,
            "history_heuristic_enabled": enable_history,
            "pvs_enabled": enable_pvs,
            "aspiration_windows_enabled": enable_aspiration,
            "aspiration_initial_delta": 35,
            "lmr_enabled": enable_lmr,
            "nmp_enabled": enable_nmp,
            "nmp_reduction": 2,
            "nmp_verification_enabled": True,
            "check_extensions_enabled": engine.enable_check_extensions,
            "check_extension_policy": engine.check_extension_policy,
            "max_check_extensions": 2,
            "see_ordering_enabled": enable_see_ordering,
            "see_pruning_enabled": enable_see_pruning,
            "tt_replacement_policy": engine.tt_replacement_policy,
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
            "total_scout_searches": sum(row["scout_searches"] for row in rows),
            "total_scout_fail_highs": sum(row["scout_fail_highs"] for row in rows),
            "total_researches": sum(row["researches"] for row in rows),
            "total_beta_cutoffs": sum(row["beta_cutoffs"] for row in rows),
            "total_aspiration_iterations": sum(row["aspiration_iterations"] for row in rows),
            "total_aspiration_fail_lows": sum(row["aspiration_fail_lows"] for row in rows),
            "total_aspiration_fail_highs": sum(row["aspiration_fail_highs"] for row in rows),
            "total_aspiration_researches": sum(row["aspiration_researches"] for row in rows),
            "total_aspiration_fallbacks": sum(row["aspiration_fallbacks"] for row in rows),
            "total_lmr_considered": sum(row["lmr_considered"] for row in rows),
            "total_lmr_reduced_searches": sum(row["lmr_reduced_searches"] for row in rows),
            "total_lmr_reduced_plies": sum(row["lmr_reduced_plies"] for row in rows),
            "total_lmr_researches": sum(row["lmr_researches"] for row in rows),
            "total_lmr_fail_lows": sum(row["lmr_fail_lows"] for row in rows),
            "total_lmr_fail_highs": sum(row["lmr_fail_highs"] for row in rows),
            "total_lmr_cutoffs": sum(row["lmr_cutoffs"] for row in rows),
            "total_nmp_considered": sum(row["nmp_considered"] for row in rows),
            "total_nmp_attempts": sum(row["nmp_attempts"] for row in rows),
            "total_nmp_fail_highs": sum(row["nmp_fail_highs"] for row in rows),
            "total_nmp_fail_lows": sum(row["nmp_fail_lows"] for row in rows),
            "total_nmp_verifications": sum(row["nmp_verifications"] for row in rows),
            "total_nmp_verification_failures": sum(row["nmp_verification_failures"] for row in rows),
            "total_nmp_cutoffs": sum(row["nmp_cutoffs"] for row in rows),
            "total_check_extensions_eligible": sum(row["check_extensions_eligible"] for row in rows),
            "total_check_extensions_applied": sum(row["check_extensions_applied"] for row in rows),
            "total_check_extension_plies": sum(row["check_extension_plies"] for row in rows),
            "total_check_extensions_suppressed": sum(row["check_extensions_suppressed"] for row in rows),
            "total_check_extensions_multiple_replies": sum(row["check_extensions_multiple_replies"] for row in rows),
            "total_check_extensions_terminal_mates": sum(row["check_extensions_terminal_mates"] for row in rows),
            "total_see_evaluations": sum(row["see_evaluations"] for row in rows),
            "total_captures_ordered_see": sum(row["captures_ordered_see"] for row in rows),
            "total_qsearch_captures_considered": sum(row["qsearch_captures_considered"] for row in rows),
            "total_qsearch_captures_pruned": sum(row["qsearch_captures_pruned"] for row in rows),
            "total_qsearch_captures_exempted": sum(row["qsearch_captures_exempted"] for row in rows),
            "total_see_cache_hits": sum(row["see_cache_hits"] for row in rows),
            "total_tt_probes": sum(row["tt_probes"] for row in rows),
            "total_tt_hits": sum(row["tt_hits"] for row in rows),
            "total_tt_usable_hits": sum(row["tt_usable_hits"] for row in rows),
            "total_tt_cutoffs": sum(row["tt_cutoffs"] for row in rows),
            "total_tt_stores": sum(row["tt_stores"] for row in rows),
            "total_tt_same_key_updates": sum(row["tt_same_key_updates"] for row in rows),
            "total_tt_same_key_overwrites": sum(row["tt_same_key_overwrites"] for row in rows),
            "total_tt_same_key_rejected": sum(row["tt_same_key_rejected"] for row in rows),
            "total_tt_clears": sum(row["tt_clears"] for row in rows),
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
    parser.add_argument("--no-pvs", action="store_true",
                        help="Disable Principal Variation Search (use standard alpha-beta)")
    parser.add_argument("--no-aspiration", action="store_true",
                        help="Disable aspiration windows (use full-window search)")
    parser.add_argument("--no-lmr", action="store_true",
                        help="Disable Late Move Reductions")
    parser.add_argument("--no-nmp", action="store_true",
                        help="Disable Null Move Pruning")
    parser.add_argument("--check-extension-policy", type=str, default="disabled",
                        choices=["disabled", "bounded_all_checks", "single_reply"],
                        help="Check extension policy: disabled, bounded_all_checks, single_reply")
    parser.add_argument("--no-check-extensions", action="store_true",
                        help="Disable Check Extensions (equivalent to --check-extension-policy disabled)")
    parser.add_argument("--enable-see-ordering", action="store_true", default=False,
                        help="Enable SEE-based capture move ordering")
    parser.add_argument("--no-see-ordering", action="store_true", default=False,
                        help="Disable SEE-based capture move ordering (default)")
    parser.add_argument("--enable-see-pruning", action="store_true", default=False,
                        help="Enable conservative SEE-based quiescence pruning")
    parser.add_argument("--no-see-pruning", action="store_true", default=False,
                        help="Disable conservative SEE-based quiescence pruning (default)")
    parser.add_argument("--tt-replacement-policy", type=str, default="always_replace",
                        choices=["always_replace", "depth_preferred", "two_tier"],
                        help="TT replacement policy: always_replace (default), depth_preferred, two_tier")
    parser.add_argument("--out", type=Path, default=ROOT / "benchmark-results")
    args = parser.parse_args()

    if args.depth < 1:
        parser.error("--depth must be >= 1")
    if args.time_limit is not None and args.time_limit <= 0:
        parser.error("--time-limit must be > 0")

    try:
        positions = load_positions(args.positions)
        policy = "disabled" if args.no_check_extensions else args.check_extension_policy
        see_ordering = args.enable_see_ordering and not args.no_see_ordering
        see_pruning = args.enable_see_pruning and not args.no_see_pruning
        report = run_benchmark(
            positions,
            args.depth,
            args.time_limit,
            enable_history=not args.no_history,
            enable_pvs=not args.no_pvs,
            enable_aspiration=not args.no_aspiration,
            enable_lmr=not args.no_lmr,
            enable_nmp=not args.no_nmp,
            check_extension_policy=policy,
            enable_see_ordering=see_ordering,
            enable_see_pruning=see_pruning,
            tt_replacement_policy=args.tt_replacement_policy,
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
