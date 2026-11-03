"""Generate and validate 100-opening master suite for v0.43 replication."""
from __future__ import annotations

import json
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[2]

with open(ROOT / "benchmarks" / "openings.json", "r", encoding="utf-8") as f:
    base_ops = json.load(f)

additional_data = [
    ("kings_gambit_accepted", "C34", "King's Gambit Accepted", "e4 e5 f4 exf4"),
    ("kings_gambit_declined", "C30", "King's Gambit Declined", "e4 e5 f4 Bc5"),
    ("vienna_game_falkbeer", "C26", "Vienna Game Falkbeer", "e4 e5 Nc3 Nf6"),
    ("evans_gambit", "C51", "Evans Gambit", "e4 e5 Nf3 Nc6 Bc4 Bc5 b4"),
    ("scotch_gambit", "C44", "Scotch Gambit", "e4 e5 Nf3 Nc6 d4 exd4 Bc4"),
    ("ruy_lopez_exchange", "C68", "Ruy Lopez Exchange", "e4 e5 Nf3 Nc6 Bb5 a6 Bxc6 dxc6"),
    ("ruy_lopez_open", "C80", "Ruy Lopez Open", "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Nxe4"),
    ("italian_max_lange", "C55", "Max Lange Attack", "e4 e5 Nf3 Nc6 Bc4 Nf6 d4 exd4 O-O Bc5"),
    ("sicilian_kan", "B42", "Sicilian Kan", "e4 c5 Nf3 e6 d4 cxd4 Nxd4 a6"),
    ("sicilian_taimanov", "B47", "Sicilian Taimanov", "e4 c5 Nf3 e6 d4 cxd4 Nxd4 Nc6"),
    ("sicilian_sveshnikov", "B33", "Sicilian Sveshnikov", "e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 Nf6 Nc3 e5"),
    ("sicilian_accelerated_dragon", "B35", "Sicilian Accelerated Dragon", "e4 c5 Nf3 Nc6 d4 cxd4 Nxd4 g6"),
    ("sicilian_richter_rauzer", "B60", "Sicilian Richter-Rauzer", "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 Nc6 Bg5"),
    ("sicilian_closed", "B23", "Sicilian Closed", "e4 c5 Nc3 Nc6 g3 g6 Bg2 Bg7"),
    ("french_rubinstein", "C10", "French Rubinstein", "e4 e6 d4 d5 Nc3 dxe4 Nxe4"),
    ("french_mccutcheon", "C12", "French McCutcheon", "e4 e6 d4 d5 Nc3 Nf6 Bg5 Bb4"),
    ("caro_kann_panov", "B13", "Caro-Kann Panov Attack", "e4 c6 d4 d5 exd5 cxd5 c4"),
    ("caro_kann_korchnoi", "B16", "Caro-Kann Korchnoi", "e4 c6 d4 d5 Nc3 dxe4 Nxe4 Nf6 Nxf6+ exf6"),
    ("scandinavian_modern", "B01", "Scandinavian Modern", "e4 d5 exd5 Nf6"),
    ("scandinavian_gubinsky", "B01", "Scandinavian 3...Qd6", "e4 d5 exd5 Qxd5 Nc3 Qd6"),
    ("alekhine_modern", "B04", "Alekhine Modern", "e4 Nf6 e5 Nd5 d4 d6 Nf3"),
    ("alekhine_four_pawns", "B03", "Alekhine Four Pawns", "e4 Nf6 e5 Nd5 d4 d6 c4 Nb6 f4"),
    ("pirc_austrian", "B09", "Pirc Austrian Attack", "e4 d6 d4 Nf6 Nc3 g6 f4 Bg7"),
    ("pirc_classical", "B08", "Pirc Classical", "e4 d6 d4 Nf6 Nc3 g6 Nf3 Bg7"),
    ("modern_avrukh", "B06", "Modern Defense 3.Nc3 c6", "e4 g6 d4 Bg7 Nc3 c6"),
    ("qgd_tarrasch", "D32", "Tarrasch Defense", "d4 d5 c4 e6 Nc3 c5"),
    ("qgd_semi_slav", "D43", "Semi-Slav Defense", "d4 d5 c4 c6 Nf3 Nf6 Nc3 e6"),
    ("qgd_tartakower", "D58", "Tartakower Defense", "d4 d5 c4 e6 Nc3 Nf6 Bg5 Be7 e3 O-O Nf3 h6 Bh4 b6"),
    ("qgd_cambridge_springs", "D52", "Cambridge Springs Defense", "d4 d5 c4 e6 Nc3 Nf6 Bg5 Nbd7 e3 c6 Nf3 Qa5"),
    ("qgd_exchange", "D35", "Queen's Gambit Declined Exchange", "d4 d5 c4 e6 Nc3 Nf6 cxd5 exd5"),
    ("slav_czech", "D15", "Slav Czech", "d4 d5 c4 c6 Nf3 Nf6 Nc3 dxc4 a4 Bf5"),
    ("slav_exchange", "D13", "Slav Exchange", "d4 d5 c4 c6 Nf3 Nf6 cxd5 cxd5"),
    ("qga_classical", "D27", "Queen's Gambit Accepted Classical", "d4 d5 c4 dxc4 Nf3 Nf6 e3 e6 Bxc4 c5 O-O a6"),
    ("catalan_closed", "E06", "Catalan Closed", "d4 Nf6 c4 e6 g3 d5 Bg2 Be7 Nf3 O-O"),
    ("kings_indian_saemisch", "E80", "King's Indian Saemisch", "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f3"),
    ("kings_indian_fianchetto", "E62", "King's Indian Fianchetto", "d4 Nf6 c4 g6 g3 Bg7 Bg2 O-O Nc3 d6 Nf3"),
    ("gruenfeld_exchange_main", "D85", "Gruenfeld Exchange Main", "d4 Nf6 c4 g6 Nc3 d5 cxd5 Nxd5 e4 Nxc3 bxc3 Bg7"),
    ("gruenfeld_russian", "D96", "Gruenfeld Russian System", "d4 Nf6 c4 g6 Nc3 d5 Nf3 Bg7 Qb3 dxc4 Qxc4 O-O e4"),
    ("nimzo_indian_classical", "E32", "Nimzo-Indian Classical 4.Qc2", "d4 Nf6 c4 e6 Nc3 Bb4 Qc2"),
    ("nimzo_indian_saemisch", "E24", "Nimzo-Indian Saemisch", "d4 Nf6 c4 e6 Nc3 Bb4 a3 Bxc3+ bxc3"),
    ("queens_indian_fianchetto", "E15", "Queen's Indian Fianchetto", "d4 Nf6 c4 e6 Nf3 b6 g3 Ba6"),
    ("benko_gambit", "A57", "Benko Gambit", "d4 Nf6 c4 c5 d5 b5"),
    ("benoni_czech", "A56", "Czech Benoni", "d4 Nf6 c4 c5 d5 e5 Nc3 d6 e4"),
    ("budapest_gambit", "A52", "Budapest Gambit", "d4 Nf6 c4 e5 dxe5 Ng4"),
    ("trompowsky_attack", "A45", "Trompowsky Attack", "d4 Nf6 Bg5"),
    ("torre_attack", "A46", "Torre Attack", "d4 Nf6 Nf3 e6 Bg5"),
    ("colle_system", "D05", "Colle System", "d4 d5 Nf3 Nf6 e3 e6 Bd3 c5 c3"),
    ("birds_opening", "A02", "Bird's Opening", "f4 d5 Nf3 Nf6 e3 g6"),
    ("nimzo_larsen_modern", "A01", "Nimzo-Larsen Modern 1.b3 d5", "b3 d5 Bb2 Nf6 e3 e6"),
    ("english_mikenas_flohr", "A18", "English Mikenas-Flohr", "c4 Nf6 Nc3 e6 e4 d5"),
]

all_100 = list(base_ops)

for oid, eco, name, moves_str in additional_data:
    board = chess.Board()
    for m in moves_str.split():
        board.push_san(m)
    all_100.append({
        "id": oid,
        "eco": eco,
        "name": name,
        "moves": moves_str,
        "fen": board.fen()
    })

assert len(all_100) == 100, f"Expected 100, got {len(all_100)}"

out_path = ROOT / "analysis" / "v0.43" / "openings_v043_100.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(all_100, f, indent=2)

print(f"Generated and validated 100-opening master suite at: {out_path}")

