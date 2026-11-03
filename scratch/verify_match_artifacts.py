import json
import csv
from pathlib import Path
import chess
import chess.pgn

ROOT = Path("e:/ChessXML/project-janus")
STAMP = "20261015-224750"
PGN_PATH = ROOT / "match-results" / f"janus-stockfish-{STAMP}.pgn"
CSV_PATH = ROOT / "match-results" / f"janus-stockfish-{STAMP}.csv"
JSON_PATH = ROOT / "match-results" / f"janus-stockfish-{STAMP}.json"

def verify():
    print(f"Verifying match artifacts for stamp {STAMP}...")
    
    # 1. JSON
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    json_games = data["games"]
    print(f"JSON games: {len(json_games)}")
    
    # 2. CSV
    with CSV_PATH.open("r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    print(f"CSV games: {len(reader)}")
    assert len(json_games) == len(reader) == 8, "Expected 8 games"

    # 3. PGN
    pgn_games = []
    with PGN_PATH.open("r", encoding="utf-8") as f:
        while True:
            g = chess.pgn.read_game(f)
            if g is None:
                break
            pgn_games.append(g)
    print(f"PGN games parsed: {len(pgn_games)}")
    assert len(pgn_games) == 8, "Expected 8 PGN games"

    # Cross-validate
    for i in range(8):
        jg = json_games[i]
        cg = reader[i]
        pg = pgn_games[i]

        assert jg["game"] == int(cg["game"]) == int(pg.headers["Round"])
        assert jg["result"] == cg["result"] == pg.headers["Result"]
        assert jg["white"] == cg["white"] == pg.headers["White"]
        assert jg["black"] == cg["black"] == pg.headers["Black"]
        assert jg["opening_id"] == cg["opening_id"] == pg.headers["Opening"]
        assert jg["termination"] == cg["termination"] == pg.headers["Termination"]
        assert jg["plies"] == int(cg["plies"])

        # Validate move legality
        board = pg.board()
        move_count = 0
        for move in pg.mainline_moves():
            assert move in board.legal_moves, f"Illegal move {move} in game {i+1} at ply {move_count}"
            board.push(move)
            move_count += 1
        assert board.ply() == jg["plies"], f"Ply mismatch in game {i+1}: {board.ply()} vs {jg['plies']}"
        print(f"Game {i+1}: verified legal ({move_count} moves played, final ply {board.ply()}, result {jg['result']}, {jg['termination']})")

    print("\nALL 8 GAMES FULLY VALIDATED AND CONSISTENT ACROSS PGN, CSV, AND JSON!")

if __name__ == "__main__":
    verify()
