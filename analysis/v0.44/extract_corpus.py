"""Extract diagnostic positions from v0.43 match data."""
import json
from pathlib import Path
import chess
import chess.pgn

def run():
    with open("analysis/v0.43/match_replication/match_results.json", "r", encoding="utf-8") as f:
        meta_data = json.load(f)
    meta_games = meta_data["games"]

    pgn_path = Path("analysis/v0.43/match_replication/match_results.pgn")
    pgn_games = []
    with open(pgn_path, "r", encoding="utf-8") as f:
        while True:
            g = chess.pgn.read_game(f)
            if g is None:
                break
            pgn_games.append(g)

    print(f"Loaded {len(meta_games)} metadata games and {len(pgn_games)} PGN games.")
    assert len(meta_games) == len(pgn_games)

    # Combine metadata and PGN
    combined_games = []
    for m, g in zip(meta_games, pgn_games):
        combined_games.append({
            "candidate": m["candidate"],
            "game": m["game"],
            "pair": m["pair"],
            "janus_color": m["janus_color"],
            "janus_points": m["janus_points"],
            "opening_name": m["opening_name"],
            "result": m["result"],
            "initial_fen": g.headers.get("FEN", chess.STARTING_FEN),
            "moves": list(g.mainline_moves()),
        })

    # Group by (pair, janus_color)
    by_pc = {}
    for cg in combined_games:
        key = (cg["pair"], cg["janus_color"])
        if key not in by_pc:
            by_pc[key] = {}
        by_pc[key][cg["candidate"]] = cg

    # Target pairs where K0 won and RFP lost
    divergence_target_pairs = [1, 2, 3, 4, 6, 10, 11, 13, 20, 24, 25, 32, 36, 37, 39, 45, 54, 61, 67, 73, 76, 78, 98, 99, 100]
    # Control pairs where both engines scored equally (both won or both drew)
    control_target_pairs = [5, 7, 8, 14, 16, 26, 27, 28, 31, 35, 40, 41]

    diagnostic_corpus = []

    # 1. Divergence extraction
    for p in divergence_target_pairs:
        for col in ["white", "black"]:
            cands = by_pc.get((p, col))
            if not cands or "k0" not in cands or "rfp" not in cands:
                continue
            k0_g = cands["k0"]
            rfp_g = cands["rfp"]
            if k0_g["janus_points"] <= rfp_g["janus_points"]:
                continue  # only look at games where K0 actually scored higher

            init_fen = k0_g["initial_fen"]
            board = chess.Board(init_fen)
            k0_moves = k0_g["moves"]
            rfp_moves = rfp_g["moves"]

            # Step through moves to find first Janus move divergence
            diverged = False
            for ply_idx, (m_k0, m_rfp) in enumerate(zip(k0_moves, rfp_moves)):
                is_janus = (board.turn == chess.WHITE and col == "white") or (board.turn == chess.BLACK and col == "black")
                if is_janus and m_k0 != m_rfp:
                    diagnostic_corpus.append({
                        "id": f"divergence_p{p}_{col}_ply{ply_idx+1}",
                        "category": "divergence",
                        "pair": p,
                        "color": col,
                        "opening": k0_g["opening_name"],
                        "ply": ply_idx + 1,
                        "fen": board.fen(),
                        "k0_move": m_k0.uci(),
                        "rfp_move": m_rfp.uci(),
                        "k0_result": k0_g["result"],
                        "rfp_result": rfp_g["result"],
                        "k0_points": k0_g["janus_points"],
                        "rfp_points": rfp_g["janus_points"],
                    })
                    diverged = True
                    break
                board.push(m_k0)

    # 2. Control extraction (positions where both made identical moves and both scored points)
    for p in control_target_pairs:
        for col in ["white", "black"]:
            cands = by_pc.get((p, col))
            if not cands or "k0" not in cands or "rfp" not in cands:
                continue
            k0_g = cands["k0"]
            rfp_g = cands["rfp"]
            if k0_g["janus_points"] < 0.5 or rfp_g["janus_points"] < 0.5:
                continue

            init_fen = k0_g["initial_fen"]
            board = chess.Board(init_fen)
            k0_moves = k0_g["moves"]
            rfp_moves = rfp_g["moves"]

            # Find early/midgame plies where both made the exact same move
            for ply_idx, (m_k0, m_rfp) in enumerate(zip(k0_moves, rfp_moves)):
                is_janus = (board.turn == chess.WHITE and col == "white") or (board.turn == chess.BLACK and col == "black")
                if is_janus and ply_idx >= 2 and m_k0 == m_rfp:
                    diagnostic_corpus.append({
                        "id": f"control_p{p}_{col}_ply{ply_idx+1}",
                        "category": "control",
                        "pair": p,
                        "color": col,
                        "opening": k0_g["opening_name"],
                        "ply": ply_idx + 1,
                        "fen": board.fen(),
                        "k0_move": m_k0.uci(),
                        "rfp_move": m_rfp.uci(),
                        "k0_result": k0_g["result"],
                        "rfp_result": rfp_g["result"],
                        "k0_points": k0_g["janus_points"],
                        "rfp_points": rfp_g["janus_points"],
                    })
                    break
                board.push(m_k0)

    out_file = Path("analysis/v0.44/diagnostic_positions.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(diagnostic_corpus, f, indent=2)

    n_div = sum(1 for x in diagnostic_corpus if x["category"] == "divergence")
    n_ctrl = sum(1 for x in diagnostic_corpus if x["category"] == "control")
    print(f"Extracted {len(diagnostic_corpus)} total positions: {n_div} divergence, {n_ctrl} control.")
    for x in diagnostic_corpus[:10]:
        print(f"  [{x['category']}] Pair {x['pair']} ({x['color']}) ply {x['ply']}: {x['opening']} | K0={x['k0_move']}, RFP={x['rfp_move']}")

if __name__ == "__main__":
    run()
