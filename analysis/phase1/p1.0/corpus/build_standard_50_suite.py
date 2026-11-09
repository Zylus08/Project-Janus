#!/usr/bin/env python3
"""
Project Janus Phase 1 — Milestone P1.0
Standard 50-Position Diagnostic Corpus for Search & Evaluation Gap Analysis.

Categories (50 positions total):
1. Tactical combinations (10 positions)
2. Quiet positional middlegames (5 positions)
3. Closed pawn structures (5 positions)
4. Open middlegames (5 positions)
5. King attacks (5 positions)
6. Endgames (10 positions: pawn, rook, minor-piece, opposite bishops)
7. Mate threats & defensive resources (5 positions)
8. Multiple candidate moves / decision dilemmas (5 positions)
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CORPUS_DIR = ROOT / "analysis" / "phase1" / "p1.0" / "corpus"
CORPUS_DIR.mkdir(parents=True, exist_ok=True)

POSITIONS = [
    # -------------------------------------------------------------
    # Category 1: Tactical Combinations (10 positions)
    # -------------------------------------------------------------
    {"id": "TAC_01", "cat": "Tactics", "fen": "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 5", "desc": "Fork trick in Italian/Four Knights", "theme": "fork_trick"},
    {"id": "TAC_02", "cat": "Tactics", "fen": "r1b2rk1/pp1nbppp/2p1pn2/q5B1/2BP4/2N1PN2/PP3PPP/R2Q1RK1 w - - 3 10", "desc": "Pin and Greek gift threat", "theme": "pin_pressure"},
    {"id": "TAC_03", "cat": "Tactics", "fen": "r2q1rk1/1pp1bppp/p1np1nb1/4p3/B3P1P1/2PP1N1P/PP3P2/RNBQR1K1 w - - 1 11", "desc": "Lopez tactical knight sacrifice setup", "theme": "piece_sacrifice"},
    {"id": "TAC_04", "cat": "Tactics", "fen": "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPPQ2PP/R3KB1R w KQ - 1 9", "desc": "Yugoslav Attack pawn storm / Bh6", "theme": "opposite_castling"},
    {"id": "TAC_05", "cat": "Tactics", "fen": "r3k2r/pb1n1ppp/1p1bp3/3p4/2PP4/1P1B1N2/PB1N1PPP/R4RK1 w kq - 1 13", "desc": "Hanging pawns tactical break", "theme": "pawn_break"},
    {"id": "TAC_06", "cat": "Tactics", "fen": "2r2rk1/1bqnbppp/p2ppn2/1p6/3NPPP1/P1N1B3/1PPQB2P/2KR3R w - - 1 14", "desc": "Sicilian Scheveningen g4-g5 breakthrough", "theme": "flank_pawn_storm"},
    {"id": "TAC_07", "cat": "Tactics", "fen": "r2qk2r/pb1nbppp/1pn1p3/2ppP3/3P4/2PB1NN1/PP3PPP/R1BQK2R w KQkq - 1 10", "desc": "French Defense h4-h5 attack vector", "theme": "king_attack"},
    {"id": "TAC_08", "cat": "Tactics", "fen": "r1b1k2r/ppppqppp/2n5/b3P3/2B5/1Q3N2/PB3PPP/R4RK1 w kq - 3 12", "desc": "Evans Gambit open lines vs uncastled king", "theme": "gambit_pressure"},
    {"id": "TAC_09", "cat": "Tactics", "fen": "r2q1rk1/pp1b1ppp/2n1p3/2b5/8/2NB1N2/PPP2PPP/R2Q1RK1 w - - 0 12", "desc": "Bxh7+ sacrifice motive (Greek Gift)", "theme": "greek_gift"},
    {"id": "TAC_10", "cat": "Tactics", "fen": "r1b1k2r/ppqn1ppp/2pbpn2/3p4/2PP4/2N1PN2/PPQ2PPP/R1B1KB1R w KQkq - 3 8", "desc": "c4-c5 pawn push trapping or dislodging bishop", "theme": "trapping_piece"},

    # -------------------------------------------------------------
    # Category 2: Quiet Positional Middlegames (5 positions)
    # -------------------------------------------------------------
    {"id": "QPOS_01", "cat": "Quiet", "fen": "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 0 7", "desc": "Quiet Italian Giuoco Pianissimo", "theme": "maneuvering"},
    {"id": "QPOS_02", "cat": "Quiet", "fen": "r2q1rk1/1pp1bppp/p1np1n2/4p3/2B1P1b1/2NP1N2/PPP2PPP/R1BQR1K1 w - - 1 9", "desc": "Ruy Lopez closed maneuvering", "theme": "subtle_coordination"},
    {"id": "QPOS_03", "cat": "Quiet", "fen": "r1bq1rk1/pp1nbppp/4pn2/2pp4/2PP4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 8", "desc": "Queen's Gambit Declined positional balance", "theme": "center_control"},
    {"id": "QPOS_04", "cat": "Quiet", "fen": "r1bq1rk1/pp2bppp/2n1pn2/2pp4/2PP4/1PN1PN2/P3BPPP/R1BQ1RK1 b - - 0 8", "desc": "Nimzo-Indian quiet central tension", "theme": "tension_maintenance"},
    {"id": "QPOS_05", "cat": "Quiet", "fen": "r1bq1rk1/pp1n1pbp/2p1pnp1/3p4/2PP4/1P3NP1/PB1NPPBP/R2Q1RK1 b - - 2 9", "desc": "King's Indian / Reti positional fianchetto", "theme": "fianchetto_harmony"},

    # -------------------------------------------------------------
    # Category 3: Closed Pawn Structures (5 positions)
    # -------------------------------------------------------------
    {"id": "CLSD_01", "cat": "Closed", "fen": "rnbq1rk1/ppp1bppp/4pn2/3p4/2PP4/2N1PN2/PP3PPP/R1BQKB1R w KQ - 0 6", "desc": "Colle System locked central triangle", "theme": "locked_center"},
    {"id": "CLSD_02", "cat": "Closed", "fen": "r1bq1rk1/pp1n1pbp/2pp1np1/4p3/2PPP3/2N1BP2/PP2N1PP/R2QKB1R w KQ - 0 9", "desc": "King's Indian Classical closed center", "theme": "locked_chains"},
    {"id": "CLSD_03", "cat": "Closed", "fen": "r2q1rk1/1p1nbppp/p1p1pn2/3p4/2PP4/1PN1PN2/PB2BPPP/R2Q1RK1 b - - 2 10", "desc": "Slav / Stonewall locked pawn wedges", "theme": "stonewall_pawns"},
    {"id": "CLSD_04", "cat": "Closed", "fen": "r1bq1rk1/pp1n1ppp/2p1pn2/3p2B1/2PP4/2N1PN2/PP3PPP/R2QKB1R w KQ - 1 8", "desc": "Closed Catalan structures", "theme": "locked_bishops"},
    {"id": "CLSD_05", "cat": "Closed", "fen": "rnbqk2r/pp1p1ppp/2p1pn2/8/1bPP4/2N1P3/PP3PPP/R1BQKBNR w KQkq - 0 5", "desc": "Nimzo doubled pawn blockade on c3/c4", "theme": "doubled_blockade"},

    # -------------------------------------------------------------
    # Category 4: Open Middlegames (5 positions)
    # -------------------------------------------------------------
    {"id": "OPEN_01", "cat": "Open", "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/3PP3/2N2N2/PPP2PPP/R1BQKB1R b KQkq d3 0 4", "desc": "Scotch Game open center liquidations", "theme": "center_break"},
    {"id": "OPEN_02", "cat": "Open", "fen": "r1b1k2r/pp1p1ppp/1qn1pn2/2b5/4P3/2NB1N2/PPP2PPP/R1BQ1RK1 w kq - 4 8", "desc": "Open Sicilian complex open c-file", "theme": "open_file"},
    {"id": "OPEN_03", "cat": "Open", "fen": "r1bq1rk1/ppp2ppp/2n5/3np3/8/2PP1N2/P1P1BPPP/R1BQ1RK1 w - - 0 9", "desc": "Liquidated e-file and d-file open board", "theme": "central_liquidation"},
    {"id": "OPEN_04", "cat": "Open", "fen": "r1b2rk1/pp3ppp/2n1pn2/q1b5/8/2NBPN2/PP3PPP/R1BQ1RK1 w - - 4 10", "desc": "Isolated Queen Pawn (IQP) dynamic open lines", "theme": "iqp_dynamics"},
    {"id": "OPEN_05", "cat": "Open", "fen": "r4rk1/pp1q1ppp/2np1n2/2p1p3/2P1P3/2NP1N2/PP3PPP/R2Q1RK1 b - - 1 10", "desc": "Symmetrical English open files", "theme": "flank_dynamics"},

    # -------------------------------------------------------------
    # Category 5: King Attacks (5 positions)
    # -------------------------------------------------------------
    {"id": "KATK_01", "cat": "KingAttack", "fen": "r1b2rk1/ppqn1ppp/2p1p3/8/2PP2n1/2NB1N2/PP3PPP/R2QR1K1 w - - 2 13", "desc": "Threat of Bxh7+ king hunt", "theme": "h7_vulnerability"},
    {"id": "KATK_02", "cat": "KingAttack", "fen": "r4rk1/pp1q1ppp/2n1p3/3p2B1/3P4/2N2B2/PPP2PPP/R2QR1K1 w - - 0 13", "desc": "Major piece battery aimed at kingside", "theme": "kingside_battery"},
    {"id": "KATK_03", "cat": "KingAttack", "fen": "r2q1rk1/1bp2ppp/p1np4/1p2p3/4P1n1/P1NP1N2/BPP2PPP/R2Q1RK1 w - - 0 12", "desc": "Pawn shelter erosion on g2/h2", "theme": "shelter_erosion"},
    {"id": "KATK_04", "cat": "KingAttack", "fen": "r1b1k2r/pp3ppp/2n1p3/3p4/2PP4/2N2N2/PP3PPP/R3KB1R b KQkq - 0 10", "desc": "King stuck in center under open e-file attack", "theme": "uncastled_king"},
    {"id": "KATK_05", "cat": "KingAttack", "fen": "r4rk1/pp1b1ppp/1qn1pn2/2bp4/8/2NBPN2/PPPB1PPP/R2Q1RK1 w - - 6 10", "desc": "Long castling pawn storm race", "theme": "opposite_attacks"},

    # -------------------------------------------------------------
    # Category 6: Endgames (10 positions)
    # -------------------------------------------------------------
    {"id": "ENDG_01", "cat": "Endgame", "fen": "8/5pk1/4p1p1/7p/7P/4r1P1/R4PK1/8 b - - 1 42", "desc": "Classic 4v3 single rook endgame", "theme": "rook_endgame"},
    {"id": "ENDG_02", "cat": "Endgame", "fen": "8/8/4k3/3p4/3K4/5B2/8/8 w - - 0 1", "desc": "Bishop vs Pawn endgame", "theme": "minor_piece_endgame"},
    {"id": "ENDG_03", "cat": "Endgame", "fen": "8/pk6/8/8/8/8/6KP/8 w - - 0 1", "desc": "Pure passed pawn race", "theme": "pawn_race"},
    {"id": "ENDG_04", "cat": "Endgame", "fen": "8/8/4k3/8/4K3/8/8/8 w - - 0 1", "desc": "King opposition key squares", "theme": "king_opposition"},
    {"id": "ENDG_05", "cat": "Endgame", "fen": "8/8/5k2/3p4/3P1K2/8/8/8 w - - 0 1", "desc": "Mutual zugzwang trebuchet position", "theme": "zugzwang"},
    {"id": "ENDG_06", "cat": "Endgame", "fen": "8/1b3k2/8/4B3/8/5K2/8/8 w - - 0 1", "desc": "Opposite coloured bishops theoretical draw", "theme": "opposite_bishops"},
    {"id": "ENDG_07", "cat": "Endgame", "fen": "8/8/2k5/8/8/1K6/1R6/r7 w - - 0 1", "desc": "Lucena / Philidor rook endgame defense", "theme": "lucena_philidor"},
    {"id": "ENDG_08", "cat": "Endgame", "fen": "8/8/3k4/p1pP4/P1P5/3K4/8/8 w - - 0 1", "desc": "Locked pawn endgame breakthrough", "theme": "locked_endgame"},
    {"id": "ENDG_09", "cat": "Endgame", "fen": "8/8/4k3/8/8/4K3/4P3/8 w - - 0 1", "desc": "K+P vs K fundamental endgame", "theme": "kp_vs_k"},
    {"id": "ENDG_10", "cat": "Endgame", "fen": "r4rk1/pp3ppp/2n1p3/3p4/3P4/2N2B2/PPP2PPP/R4RK1 w - - 0 14", "desc": "Queenless middlegame control", "theme": "queenless_middlegame"},

    # -------------------------------------------------------------
    # Category 7: Mate Threats & Defensive Resources (5 positions)
    # -------------------------------------------------------------
    {"id": "MATE_01", "cat": "Defensive", "fen": "6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1", "desc": "Back rank mate in 1 (Re8#)", "theme": "back_rank_mate"},
    {"id": "MATE_02", "cat": "Defensive", "fen": "r1b2rk1/pp3ppp/8/2p1N3/2B1n3/4P3/PP3PPP/R4RK1 w - - 0 14", "desc": "Defending against f7 mate pressure", "theme": "mate_defense"},
    {"id": "MATE_03", "cat": "Defensive", "fen": "5rk1/5ppp/8/8/8/8/4qPPP/5RK1 b - - 0 1", "desc": "Back rank perpetual check threat", "theme": "perpetual_threat"},
    {"id": "MATE_04", "cat": "Defensive", "fen": "r2q1rk1/pp1b1ppp/2n1pn2/3p4/2PP4/1PNBPN2/P4PPP/R2Q1RK1 b - - 0 10", "desc": "Preventing kingside Greek gift (h6/g6)", "theme": "prophylactic_defense"},
    {"id": "MATE_05", "cat": "Defensive", "fen": "8/8/8/8/8/1k6/p7/K7 w - - 0 1", "desc": "Corner stalemate defensive escape", "theme": "stalemate_resource"},

    # -------------------------------------------------------------
    # Category 8: Plausible Candidate Moves / Dilemmas (5 positions)
    # -------------------------------------------------------------
    {"id": "CAND_01", "cat": "Candidates", "fen": "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R b KQkq - 0 4", "desc": "Italian d6 vs O-O choice", "theme": "opening_branch"},
    {"id": "CAND_02", "cat": "Candidates", "fen": "r1bq1rk1/pp2ppbp/2np1np1/8/3NP3/2N1BP2/PPPQ2PP/2KR1B1R b - - 0 9", "desc": "Dragon d5 break vs Bd7 vs Be6", "theme": "critical_branch"},
    {"id": "CAND_03", "cat": "Candidates", "fen": "r1bqk2r/pp2bppp/2n1pn2/2pp4/2PP4/2N1PN2/PP2BPPP/R1BQK2R w KQkq - 4 7", "desc": "QGD cxd5 vs O-O vs b3", "theme": "center_decision"},
    {"id": "CAND_04", "cat": "Candidates", "fen": "r2q1rk1/1pp1bppp/p1np1nb1/4p3/B3P1P1/2PP1N1P/PP3P2/RNBQR1K1 b - - 0 11", "desc": "Lopez h5 vs Nd7 vs b5", "theme": "flank_vs_center"},
    {"id": "CAND_05", "cat": "Candidates", "fen": "r4rk1/pp1b1ppp/2n1pn2/2qp4/8/2PBPN2/PP1N1PPP/R2Q1RK1 w - - 0 11", "desc": "Catalan e4 vs c4 vs Nb3", "theme": "plan_selection"}
]

def main():
    out_file = CORPUS_DIR / "standard_50_evaluation_suite.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(POSITIONS, f, indent=2)
    print(f"Built standard 50-position suite: {len(POSITIONS)} positions saved to {out_file}")

if __name__ == "__main__":
    main()
