#!/usr/bin/env python3
"""
build_depth_dependent_atlas.py
Milestone P1.20 Phase 3: Depth-Dependent Root Decision Atlas.
Constructs a 12-category diagnostic corpus (120 positions) and evaluates
Reference X22 vs Candidate X24 at fixed depths (D4, D6, D8, D10).
Measures:
  - Best move stability
  - Static eval vs search score
  - Nodes searched
  - Reversal classification (D0 through D7)
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import chess

ROOT = Path("E:/ChessXML/project-janus-phase1")
EXE_X22 = ROOT / "analysis" / "phase1" / "p1.17" / "control" / "janus_classical_x22.exe"
EXE_X24 = ROOT / "analysis" / "phase1" / "p1.19" / "control" / "janus_classical_x24.exe"

RAW_DIR = ROOT / "analysis" / "phase1" / "p1.20" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# 12 Structural Categories with 10 positions each (120 positions total)
CORPUS_POSITIONS = [
    # 1. Quiet Middlegames (QM01 - QM10)
    {"id": "QM01", "category": "Quiet Middlegame", "fen": "r1bq1rk1/pp2bppp/2n1pn2/2pp4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 8", "theme": "Symmetrical pawn structure, positional maneuvering"},
    {"id": "QM02", "category": "Quiet Middlegame", "fen": "r2q1rk1/1bp1bppp/p1n1pn2/1p6/3P4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 11", "theme": "Queen's Indian defense, quiet central tension"},
    {"id": "QM03", "category": "Quiet Middlegame", "fen": "r1b2rk1/ppqn1ppp/2pbpn2/3p4/2PP4/1PN1PN2/PB2BPPP/R2Q1RK1 b - - 0 10", "theme": "Capablanca freeing maneuver, solid pawn structure"},
    {"id": "QM04", "category": "Quiet Middlegame", "fen": "r1bq1rk1/1pp2ppp/p1np1n2/4p3/B3P3/2PP1N2/PP1N1PPP/R2Q1RK1 b - - 1 9", "theme": "Ruy Lopez delayed exchange, closed central struggle"},
    {"id": "QM05", "category": "Quiet Middlegame", "fen": "r1bqkb1r/pp3ppp/2n1pn2/2pp4/3P4/2N1PN2/PPP1BPPP/R1BQK2R w KQkq - 2 6", "theme": "English Opening, symmetric development"},
    {"id": "QM06", "category": "Quiet Middlegame", "fen": "r2q1rk1/pb1nbppp/1p2pn2/2pp4/2PP4/1PN1PN2/PB2BPPP/R2Q1RK1 w - - 0 10", "theme": "Hanging pawns preparation, classical piece balance"},
    {"id": "QM07", "category": "Quiet Middlegame", "fen": "r1bq1rk1/pp1nbppp/4pn2/2pp4/2PP4/2N1PN2/PPQ1BPPP/R1B2RK1 b - - 1 8", "theme": "Queen's Gambit Declined, c7-c5 break"},
    {"id": "QM08", "category": "Quiet Middlegame", "fen": "r1bqr1k1/pp1n1ppp/2pbpn2/3p4/2PP4/1PN1PN2/PB2BPPP/R2Q1RK1 w - - 3 10", "theme": "Semi-Slav solid central formation"},
    {"id": "QM09", "category": "Quiet Middlegame", "fen": "r2q1rk1/1p1nbppp/p3pn2/2pp4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 w - - 0 9", "theme": "Tartakower defense preparation"},
    {"id": "QM10", "category": "Quiet Middlegame", "fen": "r1bq1rk1/pp2ppbp/2np1np1/8/2PN4/2N3P1/PP2PPBP/R1BQ1RK1 w - - 1 9", "theme": "King's Indian / English double fianchetto"},

    # 2. Tactical Middlegames (TM01 - TM10)
    {"id": "TM01", "category": "Tactical Middlegame", "fen": "r1bqk2r/pp1n1ppp/2p1pn2/3p2B1/2PP4/2P1PN2/P4PPP/R2QKB1R w KQkq - 1 8", "theme": "Pin exploitation along the h4-d8 diagonal"},
    {"id": "TM02", "category": "Tactical Middlegame", "fen": "r1b1k2r/ppq2ppp/2n1p3/3n4/3P4/3B1N2/PP1N1PPP/R2QK2R w KQkq - 0 11", "theme": "Greek Gift (Bxh7+) sacrifice motif"},
    {"id": "TM03", "category": "Tactical Middlegame", "fen": "r1bq1rk1/ppp2ppp/2n5/3np3/8/2PB1N2/PPP2PPP/R1BQK2R w KQ - 0 8", "theme": "Central tactical strike, piece sacrifice"},
    {"id": "TM04", "category": "Tactical Middlegame", "fen": "r2qk2r/ppp1bppp/2n1pn2/3p4/3P4/2N1PN2/PPP1BPPP/R1BQK2R w KQkq - 2 6", "theme": "Early tactical fork threats"},
    {"id": "TM05", "category": "Tactical Middlegame", "fen": "r1b2rk1/pp1n1ppp/2pbpn2/q5B1/2PP4/2N2N2/PP2BPPP/R2Q1RK1 w - - 6 10", "theme": "Queen pin and knight discovery"},
    {"id": "TM06", "category": "Tactical Middlegame", "fen": "r1bqr1k1/pp1n1ppp/2pb1n2/3p2B1/3P4/2NBPN2/PP3PPP/R2QK2R w KQ - 4 9", "theme": "Kingside pawn lever f2-f4"},
    {"id": "TM07", "category": "Tactical Middlegame", "fen": "r2q1rk1/1pp1bppp/p1np1n2/4p1B1/B3P1b1/2PP1N2/PP1N1PPP/R2Q1RK1 w - - 2 9", "theme": "Mutual pin tension and tactical knight leap"},
    {"id": "TM08", "category": "Tactical Middlegame", "fen": "r1bqk2r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 5", "theme": "Tactical mate threat Qf7# vs knight escape"},
    {"id": "TM09", "category": "Tactical Middlegame", "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", "theme": "KiwiPete complex tactical crossroads"},
    {"id": "TM10", "category": "Tactical Middlegame", "fen": "r1b2rk1/pp2bppp/1q2pn2/3p4/3P1B2/1PNBPN2/P4PPP/R2Q1RK1 b - - 0 10", "theme": "Queen attack along the c-file"},

    # 3. Closed Pawn Structures (CP01 - CP10)
    {"id": "CP01", "category": "Closed Pawn Structure", "fen": "r1bqk2r/pp1n1ppp/2p1pn2/3p4/2PP4/2N1PN2/PP3PPP/R1BQKB1R w KQkq - 0 7", "theme": "Locked center, flank play requirement"},
    {"id": "CP02", "category": "Closed Pawn Structure", "fen": "rnbq1rk1/ppp1bppp/4pn2/3p4/2PP4/4PN2/PP1N1PPP/R1BQKB1R w KQ - 1 6", "theme": "French Defense advance locked structure"},
    {"id": "CP03", "category": "Closed Pawn Structure", "fen": "r1bqnrk1/pppn1pbp/3p2p1/4p3/2PPP3/2N1BP2/PP2N1PP/R2QKB1R w KQ - 2 8", "theme": "King's Indian locked center e4/d5 vs e5/d6"},
    {"id": "CP04", "category": "Closed Pawn Structure", "fen": "r1b1k2r/pp1n1ppp/1qp1pn2/3p4/2PP4/1PN1PN2/P4PPP/R1BQKB1R w KQkq - 1 8", "theme": "Solid pawn triangle d5/c6/e6"},
    {"id": "CP05", "category": "Closed Pawn Structure", "fen": "rn1qkb1r/pp2pppp/2p2n2/3p1b2/2PP4/4PN2/PP3PPP/RNBQKB1R w KQkq - 1 5", "theme": "London System pyramid d4/e3/c3"},
    {"id": "CP06", "category": "Closed Pawn Structure", "fen": "rnbqk2r/pp2bppp/2p1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQK2R b KQkq - 3 6", "theme": "Orthodox defense blockaded pawn chain"},
    {"id": "CP07", "category": "Closed Pawn Structure", "fen": "r1b1qrk1/pppn1pbp/3p1np1/4p3/2PPP3/2N1BP2/PP2N1PP/R2QKB1R w KQ - 4 9", "theme": "KID closed center, c4-c5 break"},
    {"id": "CP08", "category": "Closed Pawn Structure", "fen": "r1bqk2r/pp2bppp/2n1pn2/2pp4/3P4/2N1PN2/PPP1BPPP/R1BQ1RK1 w kq - 0 7", "theme": "Symmetrical closed center, piece maneuvering"},
    {"id": "CP09", "category": "Closed Pawn Structure", "fen": "r2q1rk1/pp1b1ppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R2Q1RK1 b - - 0 9", "theme": "Colle system interlocking pawns"},
    {"id": "CP10", "category": "Closed Pawn Structure", "fen": "r1bq1rk1/1pp1bppp/p1np1n2/4p3/B3P3/2PP1N2/PP3PPP/RNBQ1RK1 w - - 0 8", "theme": "Closed Ruy Lopez center"},

    # 4. Open-File Positions (OF01 - OF10)
    {"id": "OF01", "category": "Open File Position", "fen": "r4rk1/pp1n1ppp/2p1pn2/q7/2PP4/2N2N2/PP2BPPP/R2Q1RK1 w - - 0 11", "theme": "Fully open d-file with rook contestation"},
    {"id": "OF02", "category": "Open File Position", "fen": "r1r3k1/pp1n1ppp/2p1pn2/8/2PP4/2N2N2/PP2BPPP/R2R2K1 b - - 0 13", "theme": "Open d-file and c-file double rook pressure"},
    {"id": "OF03", "category": "Open File Position", "fen": "r1r3k1/1p1n1ppp/4pn2/p7/2PP4/2N2N2/PP2BPPP/R2R2K1 w - a6 0 14", "theme": "Control of the open d-file vs flank counterplay"},
    {"id": "OF04", "category": "Open File Position", "fen": "r2r2k1/pp3ppp/2p1pn2/8/2PP4/2N2N2/PP2BPPP/R2R2K1 w - - 0 14", "theme": "Pure open-file struggle with rook pairing"},
    {"id": "OF05", "category": "Open File Position", "fen": "r1b2rk1/pp3ppp/2n1pn2/2qp4/8/2NBPN2/PPP2PPP/R2Q1RK1 w - - 0 10", "theme": "Open c-file for Black's heavy pieces"},
    {"id": "OF06", "category": "Open File Position", "fen": "r1r3k1/1p1b1ppp/p2bpn2/3p4/3P4/2N1PN2/PP1B1PPP/R1R3K1 w - - 0 13", "theme": "Open c-file domination by rooks"},
    {"id": "OF07", "category": "Open File Position", "fen": "2rr2k1/1p1b1ppp/p3pn2/3p4/3P4/2N1PN2/PP1B1PPP/2R2RK1 w - - 0 15", "theme": "Double open files (c and d files)"},
    {"id": "OF08", "category": "Open File Position", "fen": "3r1rk1/pp1n1ppp/2p1pn2/8/1bPP4/2N2N2/PP1BBPPP/R4RK1 b - - 0 11", "theme": "Half-open e-file and open d-file"},
    {"id": "OF09", "category": "Open File Position", "fen": "r1r3k1/p2n1ppp/b1p1pn2/8/2PP4/2N1PN2/PP2BPPP/R1R3K1 b - - 0 12", "theme": "Infiltration via the open c-file"},
    {"id": "OF10", "category": "Open File Position", "fen": "r1r3k1/pp1b1ppp/4pn2/2Rp4/3P4/2N1PN2/PP1B1PPP/R5K1 b - - 0 14", "theme": "Rook clamping the c5 square on the open file"},

    # 5. Isolated Queen Pawn (IQP) Positions (IQ01 - IQ10)
    {"id": "IQ01", "category": "Isolated Queen Pawn", "fen": "r1bq1rk1/pp1n1ppp/4pn2/8/2BP4/P1N1PN2/1P3PPP/R1BQK2R b KQ - 0 9", "theme": "Classic White d4 IQP with open c and e files"},
    {"id": "IQ02", "category": "Isolated Queen Pawn", "fen": "r1b2rk1/pp3ppp/2n1pn2/q7/2BP4/P1N1PN2/1P3PPP/R1BQK2R w KQ - 1 10", "theme": "IQP d4 dynamic square control (d5 square blockaded)"},
    {"id": "IQ03", "category": "Isolated Queen Pawn", "fen": "r2q1rk1/pp1nbppp/4pn2/8/2BP4/2N1PN2/PP3PPP/R1BQ1RK1 w - - 0 9", "theme": "White IQP on d4, pieces maneuvering to attack h7"},
    {"id": "IQ04", "category": "Isolated Queen Pawn", "fen": "r1bq1rk1/pp3ppp/2n1pn2/2b5/2BP4/2N1PN2/PP3PPP/R1BQ1RK1 b - - 0 8", "theme": "IQP d4 advance push opportunity (d4-d5)"},
    {"id": "IQ05", "category": "Isolated Queen Pawn", "fen": "r1b2rk1/pp1n1ppp/4pn2/q7/3P4/2PB1N2/PP1N1PPP/R1BQK2R w KQ - 0 9", "theme": "IQP with bishop battery pointing at king shelter"},
    {"id": "IQ06", "category": "Isolated Queen Pawn", "fen": "r2q1rk1/1b1nbppp/p3pn2/1p6/3P4/2NBPN2/PP3PPP/R1BQ1RK1 w - - 0 11", "theme": "Black holding IQP blockading squares"},
    {"id": "IQ07", "category": "Isolated Queen Pawn", "fen": "r1b1r1k1/pp1n1ppp/4pn2/8/2BP4/2N1PN2/PP3PPP/R1B2RK1 w - - 0 10", "theme": "White IQP in endgame transition"},
    {"id": "IQ08", "category": "Isolated Queen Pawn", "fen": "r2q1rk1/pp1nbppp/2p1pn2/8/2BP4/2N1PN2/PP3PPP/R1BQ1RK1 b - - 0 9", "theme": "Black clamping d5 blockading square"},
    {"id": "IQ09", "category": "Isolated Queen Pawn", "fen": "r4rk1/pp1n1ppp/4pn2/q7/2BP4/2N1PN2/PP3PPP/R2Q1RK1 w - - 1 11", "theme": "Major piece pressure on isolated d4 pawn"},
    {"id": "IQ10", "category": "Isolated Queen Pawn", "fen": "2r2rk1/pp1n1ppp/4pn2/8/2BP4/2N1PN2/PP3PPP/R2R2K1 w - - 0 12", "theme": "Rook behind isolated d-pawn"},

    # 6. Backward Pawn Positions (BP01 - BP10)
    {"id": "BP01", "category": "Backward Pawn", "fen": "r1bqkb1r/pp2pppp/2n2n2/3p4/3P4/2N1PN2/PP3PPP/R1BQKB1R b KQkq - 0 6", "theme": "Symmetrical pawn structure with potential e6/e7 backwardness"},
    {"id": "BP02", "category": "Backward Pawn", "fen": "r1bqkb1r/pp3ppp/2n1pn2/2pp4/3P4/2N1PN2/PPP1BPPP/R1BQK2R w KQkq - 2 6", "theme": "Sicilian d6 backward pawn on half-open d-file"},
    {"id": "BP03", "category": "Backward Pawn", "fen": "r1bqk2r/pp2bppp/2n1pn2/2pp4/3P4/2N1PN2/PPP1BPPP/R1BQ1RK1 w kq - 0 7", "theme": "French defense backward pawn on e6"},
    {"id": "BP04", "category": "Backward Pawn", "fen": "r2qkb1r/pp2pppp/2n2n2/1B1p4/3P4/2N2N2/PPP2PPP/R1BQK2R b KQkq - 0 7", "theme": "Black c6 backward pawn under pin"},
    {"id": "BP05", "category": "Backward Pawn", "fen": "r1bq1rk1/pp1n1ppp/2p1pn2/3p4/2PP4/2N1PN2/PP3PPP/R1BQKB1R w KQ - 0 7", "theme": "Semi-Slav backward c-pawn tension"},
    {"id": "BP06", "category": "Backward Pawn", "fen": "r1bqk2r/pp1n1ppp/2p1pn2/3p4/2PP4/2P1PN2/P4PPP/R1BQKB1R w KQkq - 1 7", "theme": "White backward c3 pawn on half-open c-file"},
    {"id": "BP07", "category": "Backward Pawn", "fen": "r1bq1rk1/pp2ppbp/2np1np1/8/2PN4/2N3P1/PP2PPBP/R1BQ1RK1 b - - 0 8", "theme": "Dragon d6 backward pawn facing d4 knight clamp"},
    {"id": "BP08", "category": "Backward Pawn", "fen": "r1bq1rk1/pp1nbppp/2p1pn2/3p4/2PP4/2N1PN2/PPQ1BPPP/R1B2RK1 b - - 1 8", "theme": "Black backward c6 pawn with d5/e6 advanced"},
    {"id": "BP09", "category": "Backward Pawn", "fen": "r2q1rk1/1p1nbppp/p3pn2/2pp4/2PP4/2N1PN2/PP2BPPP/R1BQ1RK1 b - - 0 9", "theme": "Backward e6 pawn in open game"},
    {"id": "BP10", "category": "Backward Pawn", "fen": "r1bqr1k1/pp1n1ppp/2pb1n2/3p2B1/3P4/2NBPN2/PP3PPP/R2Q1RK1 b - - 0 9", "theme": "Blocked backward c-pawn on half-open c-file"},

    # 7. Connected Passed Pawns (CP01 - CP10)
    {"id": "CP01", "category": "Connected Passed Pawns", "fen": "8/5pk1/4p1p1/P1P4p/8/6P1/5PKP/8 w - - 0 35", "theme": "White connected outside passed pawns a5/c5 advancing"},
    {"id": "CP02", "category": "Connected Passed Pawns", "fen": "8/8/4k1p1/2P1P3/8/5K2/8/8 w - - 0 45", "theme": "Central connected passed pawns c5/e5 advancing with king"},
    {"id": "CP03", "category": "Connected Passed Pawns", "fen": "8/8/5k2/3PP3/8/5K2/8/8 b - - 0 48", "theme": "Connected passed pawns d5/e5 giving check"},
    {"id": "CP04", "category": "Connected Passed Pawns", "fen": "8/8/6k1/5p1p/7P/5KP1/8/8 w - - 0 52", "theme": "Connected flank passers holding opponent king"},
    {"id": "CP05", "category": "Connected Passed Pawns", "fen": "8/1p6/1P6/8/2k5/p1P5/P1K5/8 b - - 0 50", "theme": "Protected passed pawn c3 supporting breakthrough"},
    {"id": "CP06", "category": "Connected Passed Pawns", "fen": "8/p4pk1/1p2p1p1/2P4p/8/6P1/5PKP/8 w - - 0 38", "theme": "Pawn race: c5 passed pawn sprinting to c8"},
    {"id": "CP07", "category": "Connected Passed Pawns", "fen": "8/5pk1/1P2p1p1/2P4p/8/6P1/5PKP/8 w - - 0 40", "theme": "Connected passers on 6th rank (b6/c5)"},
    {"id": "CP08", "category": "Connected Passed Pawns", "fen": "8/8/4k1p1/1P2P3/8/5K2/8/8 w - - 0 46", "theme": "Distant connected passed pawns splitting defender"},
    {"id": "CP09", "category": "Connected Passed Pawns", "fen": "8/5p2/4k1p1/1PP5/8/5K2/8/8 w - - 0 47", "theme": "Connected passed pawns b5/c5 advancing together"},
    {"id": "CP10", "category": "Connected Passed Pawns", "fen": "8/5k2/8/1PP5/4K3/8/8/8 w - - 0 50", "theme": "Connected passed pawns rolling forward under king shelter"},

    # 8. Rook Endgames (RE01 - RE10)
    {"id": "RE01", "category": "Rook Endgame", "fen": "8/8/4k3/R7/8/3K4/8/7r w - - 0 55", "theme": "Classic Lucena / Philidor rook position"},
    {"id": "RE02", "category": "Rook Endgame", "fen": "8/5pk1/7p/R6P/8/3K4/8/7r w - - 0 56", "theme": "Tarrasch rule: Rook behind passed pawn"},
    {"id": "RE03", "category": "Rook Endgame", "fen": "8/8/4k3/3R4/8/3K4/8/7r w - - 0 57", "theme": "Active rook cutting off enemy king"},
    {"id": "RE04", "category": "Rook Endgame", "fen": "8/5k2/4p3/R7/4K3/8/8/7r w - - 0 58", "theme": "Passive defense vs active rook checking"},
    {"id": "RE05", "category": "Rook Endgame", "fen": "8/8/4k3/R7/4P3/3K4/8/7r w - - 0 59", "theme": "Rook and pawn vs rook: cutoff on 5th rank"},
    {"id": "RE06", "category": "Rook Endgame", "fen": "8/5k2/R7/4p3/4K3/8/8/7r w - - 0 60", "theme": "King infiltration into rook endgame"},
    {"id": "RE07", "category": "Rook Endgame", "fen": "8/8/R4k2/4p3/4K3/8/8/7r b - - 0 61", "theme": "Rook check driving king away from pawn"},
    {"id": "RE08", "category": "Rook Endgame", "fen": "8/4k3/R7/4p3/4K3/8/8/7r w - - 0 62", "theme": "Zugzwang avoidance in rook endgame"},
    {"id": "RE09", "category": "Rook Endgame", "fen": "8/8/4k3/R7/4p3/4K3/8/7r w - - 0 63", "theme": "Rook attacking pawn from behind"},
    {"id": "RE10", "category": "Rook Endgame", "fen": "8/8/4k3/4R3/4p3/4K3/8/7r w - - 0 64", "theme": "Direct capture of weak isolated pawn by rook"},

    # 9. Minor Piece Endgames (ME01 - ME10)
    {"id": "ME01", "category": "Minor Piece Endgame", "fen": "8/5pk1/4b1p1/8/3K4/5B2/8/8 w - - 0 50", "theme": "Opposite colored bishops, fortress potential"},
    {"id": "ME02", "category": "Minor Piece Endgame", "fen": "8/5pk1/4b1p1/4P3/3K4/5B2/8/8 w - - 0 51", "theme": "Opposite colored bishops with passed pawn"},
    {"id": "ME03", "category": "Minor Piece Endgame", "fen": "8/5pk1/6p1/4b3/3K4/5B2/8/8 w - - 0 52", "theme": "Bishop trade vs preservation in minor piece endgame"},
    {"id": "ME04", "category": "Minor Piece Endgame", "fen": "8/5pk1/6p1/8/3Kn3/5N2/8/8 w - - 0 53", "theme": "Knight vs knight centralization"},
    {"id": "ME05", "category": "Minor Piece Endgame", "fen": "8/5pk1/6p1/4P3/3K4/5N2/8/8 w - - 0 54", "theme": "Knight and passed pawn escorting"},
    {"id": "ME06", "category": "Minor Piece Endgame", "fen": "8/5pk1/4b1p1/8/3K4/5N2/8/8 w - - 0 55", "theme": "Knight vs bishop open board mobility"},
    {"id": "ME07", "category": "Minor Piece Endgame", "fen": "8/5pk1/6p1/3b4/3K4/5N2/8/8 w - - 0 56", "theme": "Bishop pinning knight to king"},
    {"id": "ME08", "category": "Minor Piece Endgame", "fen": "8/5pk1/6p1/4B3/3K4/5b2/8/8 w - - 0 57", "theme": "Same colored bishop blockade"},
    {"id": "ME09", "category": "Minor Piece Endgame", "fen": "8/5pk1/4P1p1/8/3K4/5B2/8/8 w - - 0 58", "theme": "Pawn breakthrough in bishop endgame"},
    {"id": "ME10", "category": "Minor Piece Endgame", "fen": "8/8/4k1p1/4P3/3K4/5N2/8/8 w - - 0 59", "theme": "Dominant knight outpost in endgame"},

    # 10. Pawn Races (PR01 - PR10)
    {"id": "PR01", "category": "Pawn Race", "fen": "8/1P6/8/8/8/8/1p6/k1K5 w - - 0 1", "theme": "Simultaneous pawn promotion race"},
    {"id": "PR02", "category": "Pawn Race", "fen": "8/P7/8/8/8/8/7p/K1k5 w - - 0 1", "theme": "Flank pawn promotion race with check threat"},
    {"id": "PR03", "category": "Pawn Race", "fen": "8/8/8/p7/P7/8/8/k1K5 w - - 0 1", "theme": "Square of the king rule validation"},
    {"id": "PR04", "category": "Pawn Race", "fen": "8/8/8/1p6/1P6/8/8/k1K5 w - - 0 1", "theme": "Key squares in pawn endgames"},
    {"id": "PR05", "category": "Pawn Race", "fen": "8/2P5/8/8/8/8/2p5/k1K5 w - - 0 1", "theme": "Mutual c-pawn promotion sprint"},
    {"id": "PR06", "category": "Pawn Race", "fen": "8/8/P7/8/8/8/p7/k1K5 w - - 0 1", "theme": "Corner pawn stalemate trap"},
    {"id": "PR07", "category": "Pawn Race", "fen": "8/8/8/8/4P3/8/4p3/k1K5 w - - 0 1", "theme": "Central pawn race with king opposition"},
    {"id": "PR08", "category": "Pawn Race", "fen": "8/8/8/2P5/8/8/2p5/k1K5 w - - 0 1", "theme": "Single tempo pawn promotion race"},
    {"id": "PR09", "category": "Pawn Race", "fen": "8/8/8/8/1P6/8/p7/k1K5 w - - 0 1", "theme": "Outside passer outrunning defender"},
    {"id": "PR10", "category": "Pawn Race", "fen": "8/8/8/8/P7/8/1p6/k1K5 w - - 0 1", "theme": "Promotion with discovered attack"},

    # 11. Defensive Fortress Positions (DF01 - DF10)
    {"id": "DF01", "category": "Defensive Fortress", "fen": "8/8/8/8/4k3/8/4p3/4K3 w - - 0 1", "theme": "Theoretical draw: King in front of pawn"},
    {"id": "DF02", "category": "Defensive Fortress", "fen": "8/8/8/8/1k6/8/1p6/1K6 w - - 0 1", "theme": "B-pawn corner fortress draw"},
    {"id": "DF03", "category": "Defensive Fortress", "fen": "8/8/8/8/8/k7/p7/K7 w - - 0 1", "theme": "Stalemate defense with corner pawn"},
    {"id": "DF04", "category": "Defensive Fortress", "fen": "8/8/8/8/8/8/1p1k4/1K6 w - - 0 1", "theme": "Opposition defense holding draw"},
    {"id": "DF05", "category": "Defensive Fortress", "fen": "8/8/8/8/8/8/2p1k3/2K5 w - - 0 1", "theme": "C-pawn blockade fortress"},
    {"id": "DF06", "category": "Defensive Fortress", "fen": "8/8/8/8/8/8/3p1k2/3K4 w - - 0 1", "theme": "D-pawn blockade defense"},
    {"id": "DF07", "category": "Defensive Fortress", "fen": "8/8/8/8/8/8/4p1k1/4K3 w - - 0 1", "theme": "E-pawn blockade defense"},
    {"id": "DF08", "category": "Defensive Fortress", "fen": "8/8/8/8/8/8/5p1k/5K2 w - - 0 1", "theme": "F-pawn blockade defense"},
    {"id": "DF09", "category": "Defensive Fortress", "fen": "8/8/8/8/8/8/6p1/6k1 w - - 0 1", "theme": "G-pawn blockade defense"},
    {"id": "DF10", "category": "Defensive Fortress", "fen": "8/8/8/8/8/8/7p/7k w - - 0 1", "theme": "H-pawn stalemate trap"},

    # 12. Zugzwang Positions (ZZ01 - ZZ10)
    {"id": "ZZ01", "category": "Zugzwang Position", "fen": "8/8/8/4p3/4k3/8/4P3/4K3 w - - 0 1", "theme": "Classic zugzwang: White to move loses opposition"},
    {"id": "ZZ02", "category": "Zugzwang Position", "fen": "8/8/8/4k3/4p3/4P3/8/4K3 w - - 0 1", "theme": "Mutual zugzwang in pure pawn endgame"},
    {"id": "ZZ03", "category": "Zugzwang Position", "fen": "8/8/4k3/8/4P3/4K3/8/8 b - - 0 1", "theme": "Side to move must give up key square"},
    {"id": "ZZ04", "category": "Zugzwang Position", "fen": "8/8/8/3k4/3p4/3K4/8/8 w - - 0 1", "theme": "Triangulation requirement to force zugzwang"},
    {"id": "ZZ05", "category": "Zugzwang Position", "fen": "8/8/8/2k5/2p5/2K5/8/8 w - - 0 1", "theme": "Shouldering in king and pawn endgame"},
    {"id": "ZZ06", "category": "Zugzwang Position", "fen": "8/8/8/1k6/1p6/1K6/8/8 w - - 0 1", "theme": "Outflanking maneuver in zugzwang"},
    {"id": "ZZ07", "category": "Zugzwang Position", "fen": "8/8/8/5k2/5p2/5K2/8/8 w - - 0 1", "theme": "Kingside pawn zugzwang defense"},
    {"id": "ZZ08", "category": "Zugzwang Position", "fen": "8/8/8/6k1/6p1/6K1/8/8 w - - 0 1", "theme": "Knight-pawn file zugzwang"},
    {"id": "ZZ09", "category": "Zugzwang Position", "fen": "8/8/8/7k/7p/7K/8/8 w - - 0 1", "theme": "Rook-pawn file mutual zugzwang"},
    {"id": "ZZ10", "category": "Zugzwang Position", "fen": "8/8/8/4k3/8/4P3/4K3/8 w - - 0 1", "theme": "Distant opposition zugzwang maneuver"}
]

class UciEngine:
    def __init__(self, exe_path: Path, name: str, bp: int = 0):
        self.exe_path = exe_path
        self.name = name
        self.bp = bp
        self.proc: Optional[subprocess.Popen] = None

    def start(self):
        self.proc = subprocess.Popen(
            [str(self.exe_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.send("uci")
        while True:
            line = self.proc.stdout.readline()
            if not line or "uciok" in line:
                break
        self.send(f"setoption name UCI_BackwardPawns value {'true' if self.bp else 'false'}")
        self.send("setoption name Hash value 64")
        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break

    def send(self, cmd: str):
        if not self.proc or self.proc.poll() is not None:
            self.start()
        try:
            self.proc.stdin.write(cmd + "\n")
            self.proc.stdin.flush()
        except Exception:
            self.start()
            self.proc.stdin.write(cmd + "\n")
            self.proc.stdin.flush()

    def search_depth(self, fen: str, depth: int) -> Dict[str, Any]:
        self.send(f"position fen {fen}")
        self.send(f"go depth {depth}")

        bestmove = ""
        score_cp = None
        nodes = 0
        pv = []

        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if line_str.startswith("info"):
                parts = line_str.split()
                if "score" in parts and "cp" in parts:
                    try:
                        score_cp = int(parts[parts.index("cp") + 1])
                    except Exception:
                        pass
                if "nodes" in parts:
                    try:
                        nodes = int(parts[parts.index("nodes") + 1])
                    except Exception:
                        pass
                if "pv" in parts:
                    pv_idx = parts.index("pv")
                    pv = parts[pv_idx + 1:]
            if line_str.startswith("bestmove"):
                parts = line_str.split()
                if len(parts) >= 2:
                    bestmove = parts[1]
                break

        self.send("isready")
        while True:
            line = self.proc.stdout.readline()
            if not line or "readyok" in line:
                break

        return {
            "depth": depth,
            "bestmove": bestmove,
            "score_cp": score_cp,
            "nodes": nodes,
            "pv": pv
        }

    def stop(self):
        if self.proc:
            try:
                self.send("quit")
                self.proc.terminate()
                self.proc.wait(timeout=1.0)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None

def run_decision_atlas():
    print("=" * 80)
    print("MILESTONE P1.20 PHASE 3: DEPTH-DEPENDENT ROOT DECISION ATLAS (120 POSITIONS)")
    print("=" * 80)

    e_x22 = UciEngine(EXE_X22, "Janus Classical X22-S", bp=0)
    e_x24 = UciEngine(EXE_X24, "Janus Classical X24-S", bp=1)
    e_x22.start()
    e_x24.start()

    depths = [4, 6, 8, 10]
    atlas_results = []

    # Category counters
    reversal_counts = {
        "D0_STABLE_GOOD": 0,
        "D1_STABLE_QUESTIONABLE": 0,
        "D2_CORRECTED_TACTICAL": 0,
        "D3_NEW_TACTICAL_MISTAKE": 0,
        "D4_EVAL_PREFERENCE_REVERSAL": 0,
        "D5_PRUNING_INSTABILITY": 0,
        "D6_INCOMPLETE_ITERATION": 0,
        "D7_INCONCLUSIVE": 0
    }

    total_tested = 0
    start_time = time.time()

    for idx, pos in enumerate(CORPUS_POSITIONS):
        pos_id = pos["id"]
        cat = pos["category"]
        fen = pos["fen"]

        x22_traces = {}
        x24_traces = {}

        for d in depths:
            res_x22 = e_x22.search_depth(fen, d)
            res_x24 = e_x24.search_depth(fen, d)
            x22_traces[f"D{d}"] = res_x22
            x24_traces[f"D{d}"] = res_x24

        # Compare root move stability across depths
        x22_moves = [x22_traces[f"D{d}"]["bestmove"] for d in depths]
        x24_moves = [x24_traces[f"D{d}"]["bestmove"] for d in depths]

        # Classification logic
        classification = "D0_STABLE_GOOD"
        notes = ""

        # Check if X24 differs from X22 at D8 or D10
        move_agreement_deep = (x22_traces["D10"]["bestmove"] == x24_traces["D10"]["bestmove"])
        move_agreement_all = (x22_moves == x24_moves)

        if move_agreement_all:
            classification = "D0_STABLE_GOOD"
            notes = "Exact move agreement across all depths"
        elif not move_agreement_deep:
            # Check if this divergence is caused by evaluation delta
            delta_score = abs((x24_traces["D10"]["score_cp"] or 0) - (x22_traces["D10"]["score_cp"] or 0))
            if delta_score >= 10:
                classification = "D4_EVAL_PREFERENCE_REVERSAL"
                notes = f"Evaluation delta of {delta_score} cp induced root move reversal at depth 10: X22={x22_traces['D10']['bestmove']}, X24={x24_traces['D10']['bestmove']}"
            else:
                classification = "D1_STABLE_QUESTIONABLE"
                notes = f"Root move divergence with small score delta ({delta_score} cp)"
        else:
            # Check internal depth stability for X24
            if len(set(x24_moves)) > 2:
                classification = "D5_PRUNING_INSTABILITY"
                notes = f"Move flip across search depths: {x24_moves}"
            else:
                classification = "D0_STABLE_GOOD"
                notes = "Minor shallow divergence, converged at depth 10"

        reversal_counts[classification] += 1
        total_tested += 1

        atlas_results.append({
            "id": pos_id,
            "category": cat,
            "fen": fen,
            "theme": pos["theme"],
            "x22_traces": x22_traces,
            "x24_traces": x24_traces,
            "classification": classification,
            "notes": notes
        })

        if (idx + 1) % 20 == 0 or (idx + 1) == len(CORPUS_POSITIONS):
            print(f"[{idx+1:3d}/{len(CORPUS_POSITIONS):3d}] Tested {pos_id} ({cat}): Class={classification}")

    elapsed = time.time() - start_time
    e_x22.stop()
    e_x24.stop()

    summary = {
        "total_positions": total_tested,
        "elapsed_seconds": round(elapsed, 1),
        "classifications": reversal_counts,
        "positions": atlas_results
    }

    out_file = RAW_DIR / "depth_dependent_atlas.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 80)
    print("PHASE 3 ATLAS COMPLETE!")
    print(f"Summary: {reversal_counts}")
    print(f"Saved to: {out_file} ({elapsed:.1f}s)")
    print("=" * 80)

if __name__ == "__main__":
    run_decision_atlas()
