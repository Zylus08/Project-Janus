import json
import chess
import chess.pgn

pgn_path = "match-results/janus-stockfish-20261014-223949.pgn"
json_path = "match-results/janus-stockfish-20261014-223949.json"
prev_json_path = "match-results/janus-stockfish-20261014-141412.json"

with open(json_path) as f:
    curr = json.load(f)
with open(prev_json_path) as f:
    prev = json.load(f)

print("=== PILOT MATCH COMPARISON ===")
print("v0.6C Pilot (Pre-killer):")
print(f"  Elapsed: {prev['elapsed_seconds']:.1f}s")
for r in prev["games"]:
    print(f"  Game {r['game']} ({r['janus_color']}): {r['result']}, {r['plies']} plies, {r['duration_seconds']}s, {r['termination']}")

print("\nv0.9 Pilot (Post-killer):")
print(f"  Elapsed: {curr['elapsed_seconds']:.1f}s")
for r in curr["games"]:
    print(f"  Game {r['game']} ({r['janus_color']}): {r['result']}, {r['plies']} plies, {r['duration_seconds']}s, {r['termination']}")

# Audit PGN moves legality
total_plies = 0
with open(pgn_path) as f:
    game_idx = 0
    while True:
        game = chess.pgn.read_game(f)
        if game is None:
            break
        game_idx += 1
        board = game.board()
        ply_count = 0
        for move in game.mainline_moves():
            if move not in board.legal_moves:
                raise ValueError(f"Illegal move {move} in game {game_idx}")
            board.push(move)
            ply_count += 1
        total_plies += ply_count
        print(f"Game {game_idx} audited: {ply_count} plies replayed legally. Final fen: {board.fen()}")

print(f"\nAll {game_idx} games and {total_plies} plies independently verified legal!")
