import argparse
import argparse
import csv
from pathlib import Path
import sys
import chess
import chess.engine


POSITIONS = [
    {
        "id": "hanging_queen",
        "fen": "4k3/8/8/3q4/8/8/8/3QK3 w - - 0 1",
        "expected": "d1d5",
    },
    {
        "id": "hanging_rook",
        "fen": "4k3/8/8/3r4/8/8/8/3RK3 w - - 0 1",
        "expected": "d1d5",
    },
    {
        "id": "mate_in_one",
        "fen": "8/7k/5K2/6Q1/8/8/8/8 w - - 0 1",
        "expected": "g5g7",
    },
    {
        "id": "promotion",
        "fen": "8/P7/8/8/8/4k3/8/4K3 w - - 0 1",
        "expected": "a7a8q",
    },
    {
        "id": "promotion_threat_defense",
        "fen": "r2qk3/pp2pp2/2P2n1Q/1B2p2b/4P2p/2N5/PPP3PP/2K4R b q - 0 19",
        "expected": "e7e6",
    },
]


MATE_SCORE = 100_000


def score_cp(info, perspective):
    score = info["score"].pov(perspective)
    return score.score(mate_score=MATE_SCORE)


def main():
    parser = argparse.ArgumentParser(
        description="Compare Janus tactical decisions against Stockfish."
    )
    parser.add_argument("--janus-depth", type=int, default=4)
    parser.add_argument("--stockfish-depth", type=int, default=12)
    parser.add_argument(
        "--stockfish",
        default=r"E:\ChessXML\tools\stockfish\stockfish.exe",
    )
    parser.add_argument(
        "--max-loss-cp",
        type=int,
        default=100,
        help="Maximum tolerated Stockfish-estimated centipawn loss.",
    )
    args = parser.parse_args()

    if args.janus_depth < 1 or args.stockfish_depth < 1:
        parser.error("Search depths must be positive.")

    stockfish_path = Path(args.stockfish)
    if not stockfish_path.is_file():
        parser.error(f"Stockfish executable not found: {stockfish_path}")

    janus = None
    stockfish = None
    rows = []

    try:
        janus = chess.engine.SimpleEngine.popen_uci(
            [sys.executable, "-m", "janus.uci"],
            timeout=120,
        )
        stockfish = chess.engine.SimpleEngine.popen_uci(
            [str(stockfish_path)],
            timeout=120,
        )
        stockfish.configure({"Threads": 1, "Hash": 128})

        for case in POSITIONS:
            board = chess.Board(case["fen"])
            expected = chess.Move.from_uci(case["expected"])

            if not board.is_valid():
                raise ValueError(f"{case['id']}: invalid FEN")
            if expected not in board.legal_moves:
                raise ValueError(
                    f"{case['id']}: expected move {expected} is illegal"
                )

            janus_info = janus.analyse(
                board,
                chess.engine.Limit(depth=args.janus_depth),
            )
            pv = janus_info.get("pv", [])
            if not pv:
                raise RuntimeError(
                    f"{case['id']}: Janus returned no principal variation"
                )

            janus_move = pv[0]
            if janus_move not in board.legal_moves:
                raise RuntimeError(
                    f"{case['id']}: Janus returned an illegal move"
                )

            # Stockfish's best unrestricted root search.
            reference = stockfish.analyse(
                board,
                chess.engine.Limit(depth=args.stockfish_depth),
            )
            reference_move = reference["pv"][0]
            reference_score = score_cp(reference, board.turn)

            # Evaluate Janus's actual choice from the same root position,
            # restricting Stockfish to that move.
            chosen_info = stockfish.analyse(
                board,
                chess.engine.Limit(depth=args.stockfish_depth),
                root_moves=[janus_move],
            )
            chosen_score = score_cp(chosen_info, board.turn)

            raw_score_delta = reference_score - chosen_score
            same_as_stockfish = janus_move == reference_move

            # Identical root move means zero move-selection regret.
            # Keep the raw score delta separately to track search instability.
            loss = 0 if same_as_stockfish else raw_score_delta

            expected_ok = janus_move == expected
            score_ok = same_as_stockfish or loss <= args.max_loss_cp
            passed = expected_ok and score_ok

            row = {
                "position": case["id"],
                "janus_move": janus_move.uci(),
                "expected_move": expected.uci(),
                "stockfish_best": reference_move.uci(),
                "janus_move_matches_expected": expected_ok,
                "stockfish_best_score_cp": reference_score,
                "stockfish_score_after_janus_move_cp": chosen_score,
                "janus_matches_stockfish": same_as_stockfish,
                "raw_score_delta_cp": raw_score_delta,
                "estimated_loss_cp": loss,
                "within_loss_threshold": score_ok,
                "passed": passed,
            }
            rows.append(row)

            print(
                f"{case['id']:27} "
                f"Janus={janus_move.uci():5} "
                f"Expected={expected.uci():5} "
                f"SF={reference_move.uci():5} "
                f"Loss={loss:6} cp "
                f"{'PASS' if passed else 'REVIEW'}"
            )

    finally:
        if janus is not None:
            janus.quit()
        if stockfish is not None:
            stockfish.quit()

    output = Path("benchmark-results") / "human_robustness.csv"
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    passed_count = sum(row["passed"] for row in rows)
    print(f"\nResults: {passed_count}/{len(rows)} passed")
    print(f"CSV: {output.resolve()}")


if __name__ == "__main__":
    main()
