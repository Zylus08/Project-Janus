import chess.pgn
import json
import csv
from pathlib import Path

ROOT = Path(r"E:\ChessXML\project-janus")
MATCH_ID = "janus-stockfish-20261014-142638"
PGN_PATH = ROOT / "match-results" / f"{MATCH_ID}.pgn"
CSV_PATH = ROOT / "match-results" / f"{MATCH_ID}.csv"
JSON_PATH = ROOT / "match-results" / f"{MATCH_ID}.json"
OPENINGS_PATH = ROOT / "benchmarks" / "openings.json"

print(f"Auditing match {MATCH_ID}...")

# 1. Load JSON report
with JSON_PATH.open(encoding="utf-8") as f:
    json_data = json.load(f)

metadata = json_data["metadata"]
summary = json_data["summary"]
games_json = json_data["games"]

# 2. Load CSV report
with CSV_PATH.open(encoding="utf-8") as f:
    reader = csv.DictReader(f)
    games_csv = list(reader)

# 3. Load Openings
with OPENINGS_PATH.open(encoding="utf-8") as f:
    all_openings = json.load(f)

openings_by_id = {op["id"]: op for op in all_openings}

assert len(games_json) == 50, f"Expected 50 JSON game entries, got {len(games_json)}"
assert len(games_csv) == 50, f"Expected 50 CSV game entries, got {len(games_csv)}"

# 4. Parse and replay all PGN games
pgn_games = []
total_plies = 0
with PGN_PATH.open(encoding="utf-8") as f:
    while True:
        game = chess.pgn.read_game(f)
        if game is None:
            break
        pgn_games.append(game)

assert len(pgn_games) == 50, f"Expected 50 PGN games, got {len(pgn_games)}"

print(f"Replaying all 50 PGN games...")
for i, game in enumerate(pgn_games):
    game_num = i + 1
    gj = games_json[i]
    gc = games_csv[i]

    # Check headers
    assert game.headers["Round"] == str(game_num)
    assert game.headers["Opening"] == gj["opening_id"]
    assert game.headers["TimeControl"] == "depth 4"
    assert game.headers["Result"] == gj["result"]

    janus_color_str = gj["janus_color"]
    expected_white = "Janus" if janus_color_str == "white" else "Stockfish"
    expected_black = "Stockfish" if janus_color_str == "white" else "Janus"
    assert game.headers["White"] == expected_white
    assert game.headers["Black"] == expected_black

    # Replay moves
    board = game.board()
    move_count = 0
    for move in game.mainline_moves():
        assert move in board.legal_moves, f"Illegal move {move} in game {game_num} at ply {board.ply()}"
        board.push(move)
        move_count += 1

    total_plies += move_count
    assert board.ply() == gj["plies"] == int(gc["plies"])
    assert gj["result"] == gc["result"]
    assert gj["termination"] == gc["termination"]
    assert gj["opening_id"] == gc["opening_id"]
    assert gj["pair"] == int(gc["pair"])
    assert gj["duration_seconds"] == float(gc["duration_seconds"])

print(f"All 50 games ({total_plies} plies) replayed with 100% legal moves!")

# 5. Independent W-D-L recomputation
computed_wins = 0
computed_draws = 0
computed_losses = 0
white_stats = {"wins": 0, "draws": 0, "losses": 0, "unfinished": 0, "games": 0}
black_stats = {"wins": 0, "draws": 0, "losses": 0, "unfinished": 0, "games": 0}
pair_results = {}

for gj in games_json:
    color = gj["janus_color"]
    res = gj["result"]
    pair = gj["pair"]
    op_id = gj["opening_id"]
    
    c_stat = white_stats if color == "white" else black_stats
    c_stat["games"] += 1
    
    pair_record = pair_results.setdefault(pair, {"opening_id": op_id, "white_res": None, "black_res": None})
    if color == "white":
        pair_record["white_res"] = res
    else:
        pair_record["black_res"] = res

    if res == "1/2-1/2":
        computed_draws += 1
        c_stat["draws"] += 1
    elif (res == "1-0" and color == "white") or (res == "0-1" and color == "black"):
        computed_wins += 1
        c_stat["wins"] += 1
    else:
        computed_losses += 1
        c_stat["losses"] += 1

computed_points = computed_wins + 0.5 * computed_draws
computed_pct = round(100.0 * computed_points / 50.0, 2)

assert computed_wins == summary["janus_wins"]
assert computed_draws == summary["draws"]
assert computed_losses == summary["janus_losses"]
assert computed_points == summary["janus_score_points"]
assert computed_pct == summary["janus_score_percentage"]
assert white_stats == summary["by_color"]["white"]
assert black_stats == summary["by_color"]["black"]

print(f"Independent W-D-L Verification:")
print(f"  Overall: {computed_wins}W - {computed_draws}D - {computed_losses}L ({computed_points}/50, {computed_pct}%)")
print(f"  As White: {white_stats['wins']}W - {white_stats['draws']}D - {white_stats['losses']}L ({white_stats['games']} games)")
print(f"  As Black: {black_stats['wins']}W - {black_stats['draws']}D - {black_stats['losses']}L ({black_stats['games']} games)")

# 6. Verify 25 pairs and colour parity
assert len(pair_results) == 25, f"Expected 25 pairs, got {len(pair_results)}"
for p_num, p_data in pair_results.items():
    assert p_data["white_res"] is not None, f"Missing White game for pair {p_num}"
    assert p_data["black_res"] is not None, f"Missing Black game for pair {p_num}"

print("All 25 pairs strictly verified with colour-reversed symmetry!")

# 7. Metadata validation
assert metadata["depth_each_move"] == 4
assert metadata["stockfish_threads"] == 1
assert metadata["stockfish_hash_mb"] == 128
assert metadata["stockfish_skill"] is None
assert metadata["stockfish_elo"] is None
assert metadata["seed"] == 42
assert metadata["pairs_count"] == 25
print("Metadata verified accurately.")

# 8. Termination breakdown & duration statistics
terminations = {}
durations = []
plies_list = []
for gj in games_json:
    t = gj["termination"]
    terminations[t] = terminations.get(t, 0) + 1
    durations.append(gj["duration_seconds"])
    plies_list.append(gj["plies"])

import statistics
print(f"Terminations: {terminations}")
print(f"Duration: Total = {sum(durations):.1f}s, Mean = {statistics.mean(durations):.1f}s, Median = {statistics.median(durations):.1f}s, Min = {min(durations):.1f}s, Max = {max(durations):.1f}s")
print(f"Plies: Total = {sum(plies_list)}, Mean = {statistics.mean(plies_list):.1f}, Median = {statistics.median(plies_list):.1f}, Min = {min(plies_list)}, Max = {max(plies_list)}")
print(f"Average time per ply: {sum(durations) / sum(plies_list):.3f}s")

out_summary = {
    "match_id": MATCH_ID,
    "completed_games": 50,
    "total_plies": total_plies,
    "w_d_l": f"{computed_wins}-{computed_draws}-{computed_losses}",
    "points": computed_points,
    "pct": computed_pct,
    "white_w_d_l": f"{white_stats['wins']}-{white_stats['draws']}-{white_stats['losses']}",
    "black_w_d_l": f"{black_stats['wins']}-{black_stats['draws']}-{black_stats['losses']}",
    "terminations": terminations,
    "elapsed_seconds": json_data["elapsed_seconds"],
    "durations": {
        "mean": round(statistics.mean(durations), 1),
        "median": round(statistics.median(durations), 1),
        "min": round(min(durations), 1),
        "max": round(max(durations), 1),
    },
    "plies": {
        "mean": round(statistics.mean(plies_list), 1),
        "median": round(statistics.median(plies_list), 1),
        "min": min(plies_list),
        "max": max(plies_list),
    },
    "pair_results": pair_results,
}

with open(ROOT / "scratch" / "audit_50_depth4_summary.json", "w") as f:
    json.dump(out_summary, f, indent=2)

print("Audit complete and summary written.")
