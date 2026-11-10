import subprocess
import json
import time
import os
import re

CORPUS = [
    # 1. Open Tactical Middlegames
    {
        "id": "POS_01_OPEN_TAC_DEV",
        "category": "OPEN_TAC",
        "split": "dev",
        "fen": "r1bqk2r/pppp1ppp/2n5/1B2p3/3Pn3/5N2/PPP2PPP/RNBQ1RK1 b kq - 0 6",
        "provenance": "Ruy Lopez Open Berlin Defense, move 6",
        "key_theme": "Center tension, piece activity, tactical pins"
    },
    {
        "id": "POS_02_OPEN_TAC_HELD",
        "category": "OPEN_TAC",
        "split": "heldout",
        "fen": "r1b2rk1/pp1p1ppp/2n1pn2/q5B1/1bPP4/2N2N2/PP2BPPP/R2QK2R w KQ - 3 9",
        "provenance": "Nimzo-Indian Rubinstein, tactical pressure on c3",
        "key_theme": "Tactical pins, counter-attack on queen"
    },
    # 2. Closed Positional Middlegames
    {
        "id": "POS_03_CLOSED_POS_DEV",
        "category": "CLOSED_POS",
        "split": "dev",
        "fen": "r1b1qrk1/ppp2pbp/3p1np1/3Pp3/2P1P3/2N1BP2/PP2N1PP/R2Q1RK1 b - - 0 11",
        "provenance": "King's Indian Classical closed pawn center (d5/e4 vs d6/e5)",
        "key_theme": "Pawn-locked center, flank maneuvering"
    },
    {
        "id": "POS_04_CLOSED_POS_HELD",
        "category": "CLOSED_POS",
        "split": "heldout",
        "fen": "r2q1rk1/1pp1bppp/p1n1pn2/3p4/2PP4/2N1PN2/PPQ2PPP/R1B2RK1 w - - 4 10",
        "provenance": "Queen's Gambit Declined, closed central pawn structure",
        "key_theme": "Middlegame space control, minority attack preparation"
    },
    # 3. Isolated Queen's Pawn Structures (IQP)
    {
        "id": "POS_05_IQP_DEV",
        "category": "IQP",
        "split": "dev",
        "fen": "r1bq1rk1/pp1n1ppp/4pn2/2pp4/3P4/2NBPN2/PPP2PPP/R1BQ1RK1 w - - 0 9",
        "provenance": "Classical IQP position (Tarrasch Defense)",
        "key_theme": "Dynamic piece activity vs long-term structural weakness"
    },
    {
        "id": "POS_06_IQP_HELD",
        "category": "IQP",
        "split": "heldout",
        "fen": "r1bq1rk1/pp2bppp/2n1pn2/3p4/3P1B2/P1NBPN2/1P3PPP/R2Q1RK1 b - - 1 10",
        "provenance": "Queen's Gambit Isolated d4 pawn middlegame",
        "key_theme": "Blockade of d5 square, piece centralization"
    },
    # 4. Pawn Majorities
    {
        "id": "POS_07_PAWN_MAJ_DEV",
        "category": "PAWN_MAJ",
        "split": "dev",
        "fen": "2r2rk1/1p1q1ppp/p3pn2/3p4/3P4/bP1BP3/P2B1PPP/R2Q1RK1 w - - 0 15",
        "provenance": "Queen's Gambit Accepted 3-vs-2 Queenside Majority",
        "key_theme": "Creating an outside passed pawn on queenside"
    },
    {
        "id": "POS_08_PAWN_MAJ_HELD",
        "category": "PAWN_MAJ",
        "split": "heldout",
        "fen": "r4rk1/pp1n1ppp/2p1pn2/8/2PP4/P1N1BB2/1P3PPP/R4RK1 b - - 0 14",
        "provenance": "Slav Defense central pawn majority (White e4/d4)",
        "key_theme": "Central pawn roller vs flank majority"
    },
    # 5. Opposite-Side Castling Attacks
    {
        "id": "POS_09_OPP_CAST_DEV",
        "category": "OPP_CAST",
        "split": "dev",
        "fen": "r1b2rk1/pp2ppbp/2np1np1/q7/3NP3/1BN1BP2/PPP3PP/R2QK2R w KQ - 1 10",
        "provenance": "Sicilian Dragon Yugoslav Attack, White 0-0-0 vs Black 0-0",
        "key_theme": "Opposite-side king attack race"
    },
    {
        "id": "POS_10_OPP_CAST_HELD",
        "category": "OPP_CAST",
        "split": "heldout",
        "fen": "r1bq1rk1/1p2bppp/p1np1n2/4p3/4P3/1NN1BP2/PPPQ2PP/2KR1B1R b - - 0 10",
        "provenance": "Sicilian Najdorf English Attack, sharp kingside storm",
        "key_theme": "Pawn storm vs queen-flank counterplay"
    },
    # 6. Weak Kings
    {
        "id": "POS_11_WEAK_KING_DEV",
        "category": "WEAK_KING",
        "split": "dev",
        "fen": "r1b2rk1/ppp2ppp/2n5/3pP3/3P1qn1/2PB1N2/P1P3PP/R2Q1RK1 w - - 0 12",
        "provenance": "French Defense broken king shield, heavy piece attack",
        "key_theme": "Shattered kingside pawn shield, dark square weakness"
    },
    {
        "id": "POS_12_WEAK_KING_HELD",
        "category": "WEAK_KING",
        "split": "heldout",
        "fen": "r4rk1/1b1n1ppp/pq1bpn2/1p1p4/3P4/PPNBPN2/5PPP/R1BQR1K1 w - - 1 13",
        "provenance": "Queen's Indian Defense, kingside pressure against h7/g7",
        "key_theme": "Complex king-zone defenses and escape routes"
    },
    # 7. Passed-Pawn Races
    {
        "id": "POS_13_PASSED_RACE_DEV",
        "category": "PASSED_RACE",
        "split": "dev",
        "fen": "8/5p2/1p2k1p1/p1p1P2p/P1P1KP1P/1P6/8/8 w - - 0 35",
        "provenance": "Classic Pawn Endgame, key square breakthrough",
        "key_theme": "Pawn breakthrough timing and outside passers"
    },
    {
        "id": "POS_14_PASSED_RACE_HELD",
        "category": "PASSED_RACE",
        "split": "heldout",
        "fen": "8/4k3/1p2P3/p1p2P2/P1P5/1P2K3/8/8 b - - 0 45",
        "provenance": "Mutual advancing passed pawns in king-and-pawn endgame",
        "key_theme": "Promotion tempo calculation"
    },
    # 8. Blockaded Pawns
    {
        "id": "POS_15_BLOCKADE_DEV",
        "category": "BLOCKADE",
        "split": "dev",
        "fen": "r2q1rk1/pp1b1ppp/2n1pn2/3p4/2PP4/1PN1PN2/P4PPP/R2QKB1R w KQ - 0 9",
        "provenance": "Blockaded d5 square with knight coordination",
        "key_theme": "Paralyzing an enemy isolated or backward pawn"
    },
    {
        "id": "POS_16_BLOCKADE_HELD",
        "category": "BLOCKADE",
        "split": "heldout",
        "fen": "r1b2rk1/pp1n1ppp/4pn2/q1pp4/2PP4/P1N1PN2/1P1Q1PPP/R3KB1R w KQ - 2 10",
        "provenance": "Nimzo-Indian blockaded c4/c5 pawn pair",
        "key_theme": "Exploiting pawn chain paralysis"
    },
    # 9. Knight Outposts
    {
        "id": "POS_17_KNIGHT_OUT_DEV",
        "category": "KNIGHT_OUT",
        "split": "dev",
        "fen": "r1bq1rk1/pp2bppp/2n1pn2/3p4/2PN4/1PN1P3/PB2BPPP/R2Q1RK1 b - - 0 10",
        "provenance": "Boleslavsky hole on d5 square for Knight",
        "key_theme": "Permanent hole exploitation vs temporary outpost"
    },
    {
        "id": "POS_18_KNIGHT_OUT_HELD",
        "category": "KNIGHT_OUT",
        "split": "heldout",
        "fen": "r1b1qrk1/pp1n1ppp/2p1pn2/3p4/2PP4/1PN1PN2/P2B1PPP/R2QKB1R w KQ - 3 9",
        "provenance": "Queen's Gambit outposts on e5 vs d4",
        "key_theme": "Defended outpost square immune to enemy pawn kicks"
    },
    # 10. Weak Colour Complexes
    {
        "id": "POS_19_COL_COMPLEX_DEV",
        "category": "COL_COMPLEX",
        "split": "dev",
        "fen": "r1b2rk1/pp1p1ppp/2n1pn2/8/2P1P3/2N1BN2/PP3PPP/R3KB1R b KQ - 0 9",
        "provenance": "Light square complex weakness after exchange of light bishops",
        "key_theme": "Infiltration along weak color diagonals"
    },
    {
        "id": "POS_20_COL_COMPLEX_HELD",
        "category": "COL_COMPLEX",
        "split": "heldout",
        "fen": "r1bqr1k1/pp1n1pbp/2p1p1p1/3p4/2PP4/1PN1PN2/PB1Q1PPP/R3KB1R w KQ - 2 11",
        "provenance": "King's Indian dark square complex with Fianchetto",
        "key_theme": "Dark square blockade and piece coordination"
    },
    # 11. Rook Endgames
    {
        "id": "POS_21_ROOK_EG_DEV",
        "category": "ROOK_EG",
        "split": "dev",
        "fen": "8/8/5k2/R7/4r3/8/5K2/8 w - - 0 60",
        "provenance": "Basic Rook Endgame cut-off drawing technique",
        "key_theme": "Rook activity, checking distance, passive vs active defense"
    },
    {
        "id": "POS_22_ROOK_EG_HELD",
        "category": "ROOK_EG",
        "split": "heldout",
        "fen": "2r5/8/8/3k4/1R6/8/4K3/8 b - - 0 65",
        "provenance": "Philidor defense configuration",
        "key_theme": "Cutting off the king on rank or file"
    },
    # 12. Bishop Endgames
    {
        "id": "POS_23_BISHOP_EG_DEV",
        "category": "BISHOP_EG",
        "split": "dev",
        "fen": "8/8/4k3/1b6/4K3/5B2/8/8 w - - 0 50",
        "provenance": "Opposite-colored bishop fortress",
        "key_theme": "Unbreakable color barrier draw"
    },
    {
        "id": "POS_24_BISHOP_EG_HELD",
        "category": "BISHOP_EG",
        "split": "heldout",
        "fen": "8/8/3k4/p1b5/P7/2B2K2/8/8 w - - 0 55",
        "provenance": "Same-colored bishop outside passed pawn",
        "key_theme": "Creating an unstoppable outside passer"
    },
    # 13. Zugzwang-Sensitive Positions
    {
        "id": "POS_25_ZUGZWANG_DEV",
        "category": "ZUGZWANG",
        "split": "dev",
        "fen": "8/8/p1k5/Pp6/1P1K4/8/8/8 w - - 0 60",
        "provenance": "Trebuchet / mutual zugzwang king-and-pawn endgame",
        "key_theme": "Triangulation, key squares, opposition"
    },
    {
        "id": "POS_26_ZUGZWANG_HELD",
        "category": "ZUGZWANG",
        "split": "heldout",
        "fen": "8/5p2/4k1p1/7p/4KP1P/6P1/8/8 w - - 0 50",
        "provenance": "Symmetrical king and pawn opposition",
        "key_theme": "Losing the move, square reservation"
    },
    # 14. Queenless Middlegames
    {
        "id": "POS_27_QUEENLESS_DEV",
        "category": "QUEENLESS",
        "split": "dev",
        "fen": "r1b1kb1r/ppp2ppp/2p5/4Pn2/8/5N2/PPP2PPP/RNB2RK1 w kq - 0 9",
        "provenance": "Berlin Defense Queenless Middlegame (Berlin Wall)",
        "key_theme": "Minor piece activity, king safety irrelevance without queens"
    },
    {
        "id": "POS_28_QUEENLESS_HELD",
        "category": "QUEENLESS",
        "split": "heldout",
        "fen": "r1b1k2r/pp3ppp/2n1pn2/3p4/3P4/2N1PN2/PP3PPP/R3KB1R b KQkq - 0 10",
        "provenance": "Exchange French Queenless Middlegame",
        "key_theme": "Open file rook control, piece coordination"
    }
]

def run_engine_uci(engine_path, fen, movetime_ms=1000):
    p = subprocess.Popen([engine_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    def send(cmd):
        p.stdin.write(cmd + "\n")
        p.stdin.flush()
        
    send("uci")
    while True:
        line = p.stdout.readline()
        if "uciok" in line: break
        
    send("isready")
    while True:
        line = p.stdout.readline()
        if "readyok" in line: break
        
    send(f"position fen {fen}")
    send(f"go movetime {movetime_ms}")
    
    bestmove = None
    score = None
    depth = None
    nodes = None
    
    while True:
        line = p.stdout.readline()
        if not line: break
        line = line.strip()
        if line.startswith("bestmove"):
            parts = line.split()
            if len(parts) >= 2:
                bestmove = parts[1]
            break
        elif "info depth" in line and "score cp" in line:
            m_depth = re.search(r'depth (\d+)', line)
            m_score = re.search(r'score cp (-?\d+)', line)
            m_nodes = re.search(r'nodes (\d+)', line)
            if m_depth: depth = int(m_depth.group(1))
            if m_score: score = int(m_score.group(1))
            if m_nodes: nodes = int(m_nodes.group(1))
        elif "info depth" in line and "score mate" in line:
            m_depth = re.search(r'depth (\d+)', line)
            m_mate = re.search(r'score mate (-?\d+)', line)
            if m_depth: depth = int(m_depth.group(1))
            if m_mate: score = 10000 if int(m_mate.group(1)) > 0 else -10000
            
    send("quit")
    p.wait()
    
    return {
        "bestmove": bestmove,
        "score": score,
        "depth": depth,
        "nodes": nodes
    }

def main():
    x7_path = "E:/ChessXML/project-janus-phase1/analysis/phase1/p1.3/control/janus_classical_x7.exe"
    sf19_path = "E:/ChessXML/tools/stockfish/stockfish.exe"
    
    from x7_evaluation_tracer import X7EvaluationTracer
    tracer = X7EvaluationTracer()
    
    results = []
    category_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0}

    print(f"Profiling {len(CORPUS)} positions across 14 failure archetypes...")

    for pos in CORPUS:
        fen = pos["fen"]
        pid = pos["id"]
        cat = pos["category"]
        
        # 1. Static trace
        trace = tracer.trace(fen)
        x7_static = trace["actual_total_eval"]
        
        # 2. X7 search (500ms)
        x7_res = run_engine_uci(x7_path, fen, movetime_ms=500)
        
        # 3. Stockfish 19 reference search (500ms)
        sf_res = run_engine_uci(sf19_path, fen, movetime_ms=500)
        
        sf_score = sf_res["score"] if sf_res["score"] is not None else 0
        x7_score = x7_res["score"] if x7_res["score"] is not None else x7_static
        eval_gap = abs(x7_score - sf_score)
        tactical_gap = abs(x7_score - x7_static)
        moves_match = (x7_res["bestmove"] == sf_res["bestmove"])
        
        classification = "F"
        rationale = ""
        
        if cat in ["ROOK_EG", "BISHOP_EG", "ZUGZWANG", "PASSED_RACE"]:
            if (sf_score == 0 and abs(x7_score) > 80) or (abs(sf_score) > 200 and abs(x7_score) < 50) or not moves_match:
                classification = "E"
                rationale = f"Endgame outcome misjudged: X7={x7_score} cp vs SF={sf_score} cp; moves: X7={x7_res['bestmove']}, SF={sf_res['bestmove']}"
            else:
                classification = "F"
                rationale = f"Endgame agreement: X7={x7_score} cp, SF={sf_score} cp"
        elif tactical_gap > 150:
            classification = "D"
            rationale = f"Tactical instability: static eval {x7_static} cp vs search score {x7_score} cp (delta = {tactical_gap} cp)"
        elif eval_gap > 100 or (sf_score > 60 and x7_score < -30) or (sf_score < -60 and x7_score > 30):
            classification = "A"
            rationale = f"Incorrect positional evaluation: X7 evaluates {x7_score} cp vs SF reference {sf_score} cp (gap = {eval_gap} cp)"
        elif not moves_match:
            classification = "B"
            rationale = f"Evaluation acceptable but search missed SF move: X7={x7_res['bestmove']} (d={x7_res['depth']}) vs SF={sf_res['bestmove']} (d={sf_res['depth']})"
        else:
            classification = "F"
            rationale = f"Sufficient alignment: both select {x7_res['bestmove']}; eval gap = {eval_gap} cp"

        category_counts[classification] += 1
        
        entry = {
            "id": pid,
            "category": cat,
            "split": pos["split"],
            "fen": fen,
            "provenance": pos["provenance"],
            "key_theme": pos["key_theme"],
            "x7_static_eval": x7_static,
            "x7_trace": {
                "material": trace["material"],
                "pst": trace["piece_square_tables"],
                "pawn": trace["pawn_structure"],
                "mobility": trace["mobility_and_coordination"],
                "king_safety": trace["king_safety"],
                "endgame": trace["endgame_terms"]
            },
            "x7_search": x7_res,
            "sf19_search": sf_res,
            "eval_gap": eval_gap,
            "moves_match": moves_match,
            "classification": classification,
            "rationale": rationale
        }
        results.append(entry)
        print(f"[{pid}] Class {classification}: X7={x7_res['bestmove']} ({x7_score}cp, d={x7_res['depth']}) | SF={sf_res['bestmove']} ({sf_score}cp, d={sf_res['depth']}) - {rationale[:50]}")

    out_json = "E:/ChessXML/project-janus-phase1/analysis/phase1/p1.5/raw/positional_failure_taxonomy_raw.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "corpus_size": len(CORPUS),
            "classification_counts": category_counts,
            "results": results
        }, f, indent=2)
    print("Taxonomy results saved to", out_json)
    print("Summary:", category_counts)

if __name__ == "__main__":
    main()
