import chess
from janus.search import JanusSearch

FEN = "3qk3/8/8/3r4/8/8/8/3QK3 w - - 0 1"
CANDIDATES = ["d1e2", "d1a4", "d1f3", "d1g4", "d1d5"]

for depth in (2, 3, 4, 5, 6):
    print(f"\n=== DEPTH {depth} ===")

    for uci in CANDIDATES:
        board = chess.Board(FEN)
        move = chess.Move.from_uci(uci)

        if move not in board.legal_moves:
            print(f"{uci}: ILLEGAL")
            continue

        board.push(move)

        # A fresh search instance avoids reusing the root position's TT.
        engine = JanusSearch()
        result = engine.search(board, max_depth=depth)

        # The resulting position has Black to move.
        # Convert the score to White's perspective.
        white_score = -result.score

        print(
            f"{uci}: "
            f"white_score={white_score:+d} cp, "
            f"reply={result.best_move}, "
            f"reply_depth={result.depth}, "
            f"nodes={result.nodes}, "
            f"pv={' '.join(map(str, result.pv[:6]))}"
        )
