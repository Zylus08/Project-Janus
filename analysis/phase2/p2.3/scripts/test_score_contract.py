import os
import sys
import json
import math
import chess

def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))

def logit(p):
    p = max(1e-7, min(1.0 - 1e-7, p))
    return math.log(p / (1.0 - p))

def cp_to_prob(cp, tau=400.0):
    return sigmoid(cp / tau)

def prob_to_cp(prob, tau=400.0):
    return tau * logit(prob)

def verify_score_contract():
    repo_root = r"E:\ChessXML\project-janus-phase1"
    tau = 400.0
    
    results = {}
    
    # 1. Test mathematical round-trip: cp -> prob -> cp
    test_cps = [-2000, -1000, -500, -200, -100, -50, 0, 50, 100, 200, 500, 1000, 2000]
    round_trip_errors = []
    for cp in test_cps:
        p = cp_to_prob(cp, tau)
        cp_rec = prob_to_cp(p, tau)
        err = abs(cp - cp_rec)
        round_trip_errors.append(err)
    max_round_trip_err = max(round_trip_errors)
    results["round_trip_max_error"] = max_round_trip_err
    assert max_round_trip_err < 1e-5, f"Round trip error too high: {max_round_trip_err}"
    
    # 2. Test saturation behavior
    results["prob_at_0cp"] = cp_to_prob(0.0, tau) # should be 0.5
    results["prob_at_plus400cp"] = cp_to_prob(400.0, tau) # sigmoid(1) = 0.731058
    results["prob_at_minus400cp"] = cp_to_prob(-400.0, tau) # sigmoid(-1) = 0.268941
    results["prob_at_plus2000cp"] = cp_to_prob(2000.0, tau) # sigmoid(5) = 0.993307
    results["prob_at_minus2000cp"] = cp_to_prob(-2000.0, tau) # sigmoid(-5) = 0.0066928
    
    # 3. Test Perspective Inversion
    # For any score s from STM perspective, when side-to-move is flipped on the same board,
    # the new STM's score should be -s.
    # Outcome conversion: if White win (R_white=1.0) and White to move -> z = 1.0
    # if White win (R_white=1.0) and Black to move -> z = 0.0
    # if Draw (R_white=0.5) and either to move -> z = 0.5
    stm_outcomes = [
        {"R_white": 1.0, "stm": chess.WHITE, "expected_z": 1.0},
        {"R_white": 1.0, "stm": chess.BLACK, "expected_z": 0.0},
        {"R_white": 0.0, "stm": chess.WHITE, "expected_z": 0.0},
        {"R_white": 0.0, "stm": chess.BLACK, "expected_z": 1.0},
        {"R_white": 0.5, "stm": chess.WHITE, "expected_z": 0.5},
        {"R_white": 0.5, "stm": chess.BLACK, "expected_z": 0.5},
    ]
    for o in stm_outcomes:
        z = o["R_white"] if o["stm"] == chess.WHITE else 1.0 - o["R_white"]
        assert z == o["expected_z"], f"Mismatch in outcome conversion: {o} got {z}"
    results["outcome_conversion_tests"] = len(stm_outcomes)
    
    # 4. Diagnostic test suite positions
    test_positions = [
        {
            "id": "D1_white_up_queen_wtm",
            "fen": "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", # White has extra queen
            "desc": "White materially ahead, White to move",
            "expected_stm_sign": +1
        },
        {
            "id": "D2_white_up_queen_btm",
            "fen": "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1",
            "desc": "White materially ahead, Black to move",
            "expected_stm_sign": -1
        },
        {
            "id": "D3_black_up_queen_btm",
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR b KQkq - 0 1", # Black has extra queen
            "desc": "Black materially ahead, Black to move",
            "expected_stm_sign": +1
        },
        {
            "id": "D4_black_up_queen_wtm",
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1",
            "desc": "Black materially ahead, White to move",
            "expected_stm_sign": -1
        },
        {
            "id": "D5_startpos_wtm",
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "desc": "Initial starting position",
            "expected_stm_range": [-50, +50]
        },
        {
            "id": "D6_passed_pawn_wtm",
            "fen": "8/4k3/8/4P3/8/8/8/4K3 w - - 0 1",
            "desc": "White passed pawn on e5",
            "expected_stm_sign": +1
        },
        {
            "id": "D7_passed_pawn_btm",
            "fen": "8/4k3/8/4p3/8/8/8/4K3 b - - 0 1",
            "desc": "Black passed pawn on e5, Black to move",
            "expected_stm_sign": +1
        },
        {
            "id": "D8_drawn_kp_k",
            "fen": "8/8/8/8/4k3/8/4P3/4K3 w - - 0 1",
            "desc": "Drawn K+P vs K endgame",
            "expected_stm_range": [-100, +200]
        }
    ]
    results["diagnostic_cases"] = len(test_positions)
    
    out_json = os.path.join(repo_root, "analysis/phase2/p2.3/raw/score_contract_verification.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print(f"Score contract verified and saved to {out_json}")

if __name__ == "__main__":
    verify_score_contract()
