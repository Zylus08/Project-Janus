"""Run comprehensive forensics on the v0.7 50-game depth-4 baseline match."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import chess
import chess.engine
import chess.pgn

ROOT = Path(r"E:\ChessXML\project-janus")
STOCKFISH_PATH = r"E:\ChessXML\tools\stockfish\stockfish.exe"
PGN_PATH = ROOT / "match-results" / "janus-stockfish-20261014-142638.pgn"
JSON_PATH = ROOT / "match-results" / "janus-stockfish-20261014-142638.json"
ANALYSIS_DIR = ROOT / "analysis"
ANALYSIS_DIR.mkdir(exist_ok=True)


def parse_score(score: chess.engine.Score, turn: chess.Color, janus_color: chess.Color) -> dict[str, Any]:
    """Normalize score to Janus's perspective in centipawns and mate distances."""
    score_janus = score.white() if janus_color == chess.WHITE else score.black()
    if score_janus.is_mate():
        mate_plies = score_janus.mate()
        # Cap centipawn representation for numerical comparison
        cp_val = 100_000 if mate_plies > 0 else -100_000
        return {"type": "mate", "mate_in": mate_plies, "cp": cp_val}
    else:
        cp_val = score_janus.score()
        return {"type": "cp", "mate_in": None, "cp": cp_val}


def main():
    print(f"Starting Forensics Analysis using Stockfish 19...")
    t0 = time.time()

    # Load baseline JSON report
    with JSON_PATH.open(encoding="utf-8") as f:
        meta_json = json.load(f)
    games_meta = {g["game"]: g for g in meta_json["games"]}

    # Step 1: Reconstruct tournament index
    print("Reconstructing game index from PGN...")
    game_index = []
    games = []
    with PGN_PATH.open(encoding="utf-8") as f:
        while True:
            g = chess.pgn.read_game(f)
            if g is None:
                break
            games.append(g)

    assert len(games) == 50, f"Expected 50 games, got {len(games)}"

    losses = []
    draws = []
    wins = []

    for i, g in enumerate(games, 1):
        m = games_meta[i]
        janus_color = chess.WHITE if m["janus_color"] == "white" else chess.BLACK
        result = m["result"]
        if result == "1/2-1/2":
            outcome = "draw"
            draws.append(i)
        elif (result == "1-0" and janus_color == chess.WHITE) or (result == "0-1" and janus_color == chess.BLACK):
            outcome = "win"
            wins.append(i)
        else:
            outcome = "loss"
            losses.append(i)

        game_index.append({
            "game_number": i,
            "pair_number": m["pair"],
            "opening_id": m["opening_id"],
            "janus_color": m["janus_color"],
            "result": result,
            "outcome": outcome,
            "termination": m["termination"],
            "plies": m["plies"],
            "duration_seconds": m["duration_seconds"],
            "start_fen": m["start_fen"],
        })

    print(f"Tournament reconstructed: {len(wins)} Win, {len(draws)} Draws, {len(losses)} Losses.")
    assert len(losses) == 23
    assert len(draws) == 26
    assert len(wins) == 1

    with (ANALYSIS_DIR / "v0.8_game_index.json").open("w", encoding="utf-8") as f:
        json.dump(game_index, f, indent=2)

    # Launch Stockfish engine for analysis
    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as sf:
        sf.configure({"Threads": 1, "Hash": 128})
        print(f"Connected to {sf.id.get('name')}")

        # Step 2: Loss Forensics (Screening + Deep Analysis)
        print("\n=== Track A2: Analyzing 23 Losses ===")
        loss_analysis = []
        critical_moments_all = []

        for idx, g_num in enumerate(losses, 1):
            g = games[g_num - 1]
            m = games_meta[g_num]
            janus_color = chess.WHITE if m["janus_color"] == "white" else chess.BLACK
            board = g.board()
            mainline = list(g.mainline_moves())

            print(f"[{idx}/23] Analyzing Game {g_num} (Pair {m['pair']}, {m['opening_id']}, Janus {m['janus_color']})...")

            game_critical = []
            prev_eval_cp = None

            for ply_idx, move in enumerate(mainline):
                ply = ply_idx + 1
                is_janus_turn = (board.turn == janus_color)

                if is_janus_turn:
                    fen_before = board.fen()
                    # Screen before move: Stockfish eval at depth 10
                    res_before = sf.analyse(board, chess.engine.Limit(depth=10))
                    score_before = parse_score(res_before["score"], board.turn, janus_color)
                    sf_best_before = res_before.get("pv", [None])[0]

                    # Push Janus's move
                    board.push(move)

                    # Screen after move: Stockfish eval at depth 10
                    res_after = sf.analyse(board, chess.engine.Limit(depth=10))
                    score_after = parse_score(res_after["score"], board.turn, janus_color)

                    drop_cp = score_before["cp"] - score_after["cp"]

                    # Check for significant deterioration:
                    # Drop >= 150 cp, or entering a lost mate, or dropping from non-losing to clearly losing (<-250 cp)
                    is_candidate = (
                        drop_cp >= 150
                        or (score_before["cp"] > -200 and score_after["cp"] <= -350)
                        or (score_before["type"] != "mate" and score_after["type"] == "mate" and score_after["mate_in"] < 0)
                    )

                    if is_candidate:
                        # Deep analysis at depth 16 with MultiPV=3
                        board.pop()  # restore position before move
                        deep_res = sf.analyse(board, chess.engine.Limit(depth=16), multipv=3)
                        top_moves = []
                        for entry in deep_res:
                            pv_moves = entry.get("pv", [])
                            m_pv = pv_moves[0] if pv_moves else None
                            top_moves.append({
                                "move": m_pv.uci() if m_pv else None,
                                "score": parse_score(entry["score"], board.turn, janus_color),
                                "pv": [x.uci() for x in pv_moves[:8]],
                            })

                        # Deep eval of the actual Janus move played
                        board.push(move)
                        deep_played = sf.analyse(board, chess.engine.Limit(depth=16))
                        deep_played_score = parse_score(deep_played["score"], board.turn, janus_color)

                        # Failure categorization
                        deep_drop = (top_moves[0]["score"]["cp"] if top_moves else score_before["cp"]) - deep_played_score["cp"]

                        category = "Unclear / positional concession"
                        # Inspect board conditions for category
                        board_before = chess.Board(fen_before)
                        if deep_played_score["type"] == "mate" and deep_played_score["mate_in"] < 0:
                            category = "King-safety failure"
                        elif board_before.is_capture(move) or (sf_best_before and board_before.is_capture(sf_best_before)):
                            category = "Hanging material or failed material gain"
                        elif board_before.is_check():
                            category = "Missed tactical defence"
                        elif len(board_before.piece_map()) <= 10:
                            category = "Endgame technique"
                        elif deep_drop >= 300:
                            category = "Missed tactical defence"
                        elif deep_drop >= 150:
                            category = "Poor move ordering or inadequate search horizon"

                        crit_item = {
                            "game_number": g_num,
                            "pair_number": m["pair"],
                            "opening_id": m["opening_id"],
                            "janus_color": m["janus_color"],
                            "ply": ply,
                            "fen_before": fen_before,
                            "janus_move": move.uci(),
                            "sf_best_move": sf_best_before.uci() if sf_best_before else None,
                            "screen_score_before": score_before,
                            "screen_score_after": score_after,
                            "screen_drop_cp": drop_cp,
                            "deep_score_best": top_moves[0]["score"] if top_moves else None,
                            "deep_score_played": deep_played_score,
                            "deep_drop_cp": deep_drop,
                            "top_3_moves": top_moves,
                            "category": category,
                        }
                        game_critical.append(crit_item)
                        critical_moments_all.append(crit_item)
                else:
                    board.push(move)

            loss_analysis.append({
                "game_number": g_num,
                "pair_number": m["pair"],
                "opening_id": m["opening_id"],
                "janus_color": m["janus_color"],
                "termination": m["termination"],
                "plies": m["plies"],
                "critical_moments_count": len(game_critical),
                "critical_moments": game_critical,
            })

        print(f"Identified {len(critical_moments_all)} critical deterioration moments across 23 losses.")
        with (ANALYSIS_DIR / "v0.8_loss_analysis.json").open("w", encoding="utf-8") as f:
            json.dump({
                "total_losses": len(losses),
                "total_critical_moments": len(critical_moments_all),
                "games": loss_analysis,
                "critical_moments": critical_moments_all,
            }, f, indent=2)

        # Step 3: Draw Forensics
        print("\n=== Track A3: Analyzing 26 Draws ===")
        draw_analysis = []
        for idx, g_num in enumerate(draws, 1):
            g = games[g_num - 1]
            m = games_meta[g_num]
            janus_color = chess.WHITE if m["janus_color"] == "white" else chess.BLACK
            board = g.board()
            mainline = list(g.mainline_moves())

            max_janus_advantage = -99999
            min_janus_advantage = 99999
            max_adv_ply = 0
            min_adv_ply = 0

            # Sample every 4th ply for screening draw swings
            for ply_idx, move in enumerate(mainline):
                ply = ply_idx + 1
                board.push(move)
                if ply % 4 == 0 or ply == len(mainline):
                    eval_res = sf.analyse(board, chess.engine.Limit(depth=10))
                    sc = parse_score(eval_res["score"], board.turn, janus_color)
                    cp = sc["cp"]
                    if cp > max_janus_advantage:
                        max_janus_advantage = cp
                        max_adv_ply = ply
                    if cp < min_janus_advantage:
                        min_janus_advantage = cp
                        min_adv_ply = ply

            draw_type = "Tactical balance maintained"
            if max_janus_advantage >= 200:
                draw_type = "Possible missed win opportunity"
            elif min_janus_advantage <= -250:
                draw_type = "Successful defence from lost position"

            draw_analysis.append({
                "game_number": g_num,
                "pair_number": m["pair"],
                "opening_id": m["opening_id"],
                "janus_color": m["janus_color"],
                "termination": m["termination"],
                "plies": m["plies"],
                "max_janus_advantage_cp": max_janus_advantage,
                "max_advantage_ply": max_adv_ply,
                "min_janus_advantage_cp": min_janus_advantage,
                "min_advantage_ply": min_adv_ply,
                "classification": draw_type,
            })

        print(f"Analyzed {len(draws)} draws.")
        with (ANALYSIS_DIR / "v0.8_draw_analysis.json").open("w", encoding="utf-8") as f:
            json.dump({"total_draws": len(draws), "draws": draw_analysis}, f, indent=2)

        # Step 4: Win Forensics (Game 32)
        print("\n=== Track A4: Analyzing Game 32 (Janus Win) ===")
        win_game_num = 32
        g_win = games[win_game_num - 1]
        m_win = games_meta[win_game_num]
        board = g_win.board()
        win_plies = []

        for ply_idx, move in enumerate(g_win.mainline_moves()):
            ply = ply_idx + 1
            fen_before = board.fen()
            is_janus = (board.turn == chess.BLACK)

            # Deep eval before move
            res_before = sf.analyse(board, chess.engine.Limit(depth=14), multipv=2)
            top_moves = []
            for entry in res_before:
                pv = entry.get("pv", [])
                top_moves.append({
                    "move": pv[0].uci() if pv else None,
                    "score": parse_score(entry["score"], board.turn, chess.BLACK),
                })

            board.push(move)

            res_after = sf.analyse(board, chess.engine.Limit(depth=14))
            score_after = parse_score(res_after["score"], board.turn, chess.BLACK)

            win_plies.append({
                "ply": ply,
                "side": "Janus (Black)" if is_janus else "Stockfish (White)",
                "move": move.uci(),
                "fen_before": fen_before,
                "best_move": top_moves[0]["move"] if top_moves else None,
                "score_before": top_moves[0]["score"] if top_moves else None,
                "score_after": score_after,
            })

        with (ANALYSIS_DIR / "v0.8_win_analysis.json").open("w", encoding="utf-8") as f:
            json.dump({
                "game_number": 32,
                "pair_number": m_win["pair"],
                "opening_id": m_win["opening_id"],
                "janus_color": "black",
                "termination": "checkmate",
                "plies_count": len(win_plies),
                "plies": win_plies,
            }, f, indent=2)

        print(f"Game 32 win analysis complete.")

    elapsed = time.time() - t0
    print(f"\nAll forensics completed successfully in {elapsed:.1f}s.")


if __name__ == "__main__":
    main()
