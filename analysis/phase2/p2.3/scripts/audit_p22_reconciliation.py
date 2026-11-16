import os
import sys
import json
import hashlib
import chess
import chess.pgn
import math

def compute_sha256(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()

def main():
    repo_root = r"E:\ChessXML\project-janus-phase1"
    
    print("=== PHASE 0: P2.2 EVIDENCE RECONCILIATION AUDIT ===")
    
    # 1. Cryptographic artifact verification
    artifacts = {
        "H1_EXE": os.path.join(repo_root, "analysis/phase2/p2.1/control/janus_hybrid_h1.exe"),
        "H1_DLL": os.path.join(repo_root, "analysis/phase2/p2.1/control/janus_hybrid_h1.dll"),
        "H1_BIN": os.path.join(repo_root, "analysis/phase2/p2.1/models/janus_nnue_h1.bin"),
        "R1_EXE": os.path.join(repo_root, "analysis/phase1/p1.22/control/janus_classical_r1.exe"),
        "X7_EXE": os.path.join(repo_root, "analysis/phase1/p1.3/control/janus_classical_x7.exe"),
        "X22_EXE": os.path.join(repo_root, "analysis/phase1/p1.17/control/janus_classical_x22.exe"),
    }
    
    hashes = {}
    for name, path in artifacts.items():
        h = compute_sha256(path)
        hashes[name] = {
            "path": os.path.relpath(path, repo_root).replace("\\", "/"),
            "sha256": h,
            "exists": os.path.exists(path)
        }
        print(f"[{name}] {hashes[name]['path']} -> {h}")
        
    # 2. P2.2 Manifests verification
    p22_manifest_path = os.path.join(repo_root, "analysis/phase2/p2.2/experiment_manifest.json")
    p22_sha_path = os.path.join(repo_root, "analysis/phase2/p2.2/sha256_manifest.json")
    
    with open(p22_manifest_path, "r", encoding="utf-8") as f:
        p22_exp = json.load(f)
    with open(p22_sha_path, "r", encoding="utf-8") as f:
        p22_sha = json.load(f)
        
    print(f"P2.2 Experiment Manifest Loaded: Milestone {p22_exp['milestone']}, Decision: {p22_exp['classification']}")
    print(f"P2.2 SHA256 Manifest Entries: {len(p22_sha)}")
    
    # 3. PGN Reconstruction of H2 vs R1 Match (50 games)
    pgn_path = os.path.join(repo_root, "analysis/phase2/p2.2/raw/match_h2_vs_r1.pgn")
    print(f"Reconstructing Match: {pgn_path} ...")
    
    games = []
    h2_wins = 0
    r1_wins = 0
    draws = 0
    total_plies = 0
    illegal_moves = 0
    pair_results = {} # pair_id -> [res_game1, res_game2]
    
    with open(pgn_path, "r", encoding="utf-8") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break
            
            headers = dict(game.headers)
            result = headers.get("Result", "*")
            white = headers.get("White", "")
            black = headers.get("Black", "")
            round_str = headers.get("Round", "")
            
            # Reconstruct board
            board = game.board()
            plies = 0
            for move in game.mainline_moves():
                if move not in board.legal_moves:
                    illegal_moves += 1
                board.push(move)
                plies += 1
            total_plies += plies
            
            # Determine H2 score
            h2_score = 0.0
            if "Hybrid" in white or "H2" in white:
                if result == "1-0":
                    h2_wins += 1
                    h2_score = 1.0
                elif result == "0-1":
                    r1_wins += 1
                    h2_score = 0.0
                elif result == "1/2-1/2":
                    draws += 1
                    h2_score = 0.5
            else:
                if result == "0-1":
                    h2_wins += 1
                    h2_score = 1.0
                elif result == "1-0":
                    r1_wins += 1
                    h2_score = 0.0
                elif result == "1/2-1/2":
                    draws += 1
                    h2_score = 0.5
                    
            # Track pair
            # round is like "1.1", "1.2"
            pair_idx = round_str.split(".")[0] if "." in round_str else str(len(games)//2)
            if pair_idx not in pair_results:
                pair_results[pair_idx] = []
            pair_results[pair_idx].append(h2_score)
            
            games.append({
                "round": round_str,
                "white": white,
                "black": black,
                "result": result,
                "h2_score": h2_score,
                "plies": plies
            })
            
    total_games = len(games)
    h2_pts = h2_wins + 0.5 * draws
    score_pct = (h2_pts / total_games) * 100.0 if total_games > 0 else 0.0
    
    print(f"PGN Games Parsed: {total_games}")
    print(f"H2 Wins: {h2_wins}, Draws: {draws}, R1 Wins: {r1_wins}")
    print(f"H2 Points: {h2_pts}/{total_games} ({score_pct:.2f}%)")
    print(f"Illegal Moves: {illegal_moves}, Total Plies: {total_plies}")
    
    # Calculate Pentanomial distribution across the 25 pairs
    pentanomial = [0, 0, 0, 0, 0] # [LL, LD, DD/LW, WD, WW]
    pair_scores = []
    for p_id, res in pair_results.items():
        if len(res) == 2:
            s = sum(res)
            pair_scores.append(s)
            if s == 0.0:
                pentanomial[0] += 1
            elif s == 0.5:
                pentanomial[1] += 1
            elif s == 1.0:
                pentanomial[2] += 1
            elif s == 1.5:
                pentanomial[3] += 1
            elif s == 2.0:
                pentanomial[4] += 1
                
    n_pairs = len(pair_scores)
    mean_pair = sum(pair_scores) / n_pairs if n_pairs > 0 else 0.0
    # Variance of pair score (range 0 to 2)
    var_pair = sum((x - mean_pair)**2 for x in pair_scores) / (n_pairs - 1) if n_pairs > 1 else 0.0
    se_pair = math.sqrt(var_pair / n_pairs) if n_pairs > 0 else 0.0
    # Mean game score = mean_pair / 2
    mean_game = mean_pair / 2.0
    se_game = se_pair / 2.0
    # 95% CI: mean_game +/- 1.96 * se_game
    ci_low = max(0.0, (mean_game - 1.96 * se_game) * 100.0)
    ci_high = min(100.0, (mean_game + 1.96 * se_game) * 100.0)
    
    # Elo difference
    # s = 1 / (1 + 10^(-elo/400)) => elo = -400 * log10((1-s)/s)
    if 0.0 < mean_game < 1.0:
        elo = -400.0 * math.log10((1.0 - mean_game) / mean_game)
    else:
        elo = -999.0
        
    print(f"Pentanomial Distribution: {pentanomial}")
    print(f"Mean Game Score: {mean_game*100:.2f}%, 95% CI: [{ci_low:.2f}%, {ci_high:.2f}%], Elo: {elo:.1f}")
    
    # Compile full audit record
    out_record = {
        "parent_commit": "aa66937",
        "expected_head": "aa66937",
        "artifacts": hashes,
        "p22_experiment": {
            "milestone": p22_exp["milestone"],
            "decision": p22_exp["classification"],
            "manifest_entries": len(p22_sha)
        },
        "tournament_reconstruction": {
            "pgn_path": os.path.relpath(pgn_path, repo_root).replace("\\", "/"),
            "total_games": total_games,
            "h2_wins": h2_wins,
            "draws": draws,
            "r1_wins": r1_wins,
            "h2_points": h2_pts,
            "score_pct": score_pct,
            "illegal_moves": illegal_moves,
            "total_plies": total_plies,
            "pairs_count": n_pairs,
            "pentanomial": pentanomial,
            "ci_95": [round(ci_low, 2), round(ci_high, 2)],
            "elo": round(elo, 1)
        },
        "scientific_corrections": {
            "quantization_overstatement": "P2.2 verified Pearson r=0.999636 across 500 test positions; this is empirical validation over a sample, not a mathematical guarantee over all reachable positions.",
            "accumulator_overstatement": "P2.2 tested 14,781 legal moves with Delta=0; this confirms accumulator correctness over the sample trace, but full correctness requires formal test suites covering all move classes.",
            "draw_frequency_overstatement": "49.5% draw rate contributed to BCE logit compression, but BCE with unscaled targets and lack of teacher centipawn grounding was equally responsible.",
            "dense_network_overstatement": "Dense feed-forward layers can theoretically approximate higher-order interactions given sufficient parameters/data; the limitation in H1 was capacity (768->128x2->32->1) and sample efficiency.",
            "accumulator_latency_overstatement": "0.11 us accumulator update is only the sparse input layer delta; full forward pass (hidden layers, activation clipping, scalar output) requires ~1.0-1.5 us."
        }
    }
    
    out_json = os.path.join(repo_root, "analysis/phase2/p2.3/raw/p22_reconciliation_audit.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(out_record, f, indent=2)
    print(f"Reconciliation audit written to {out_json}")

if __name__ == "__main__":
    main()
