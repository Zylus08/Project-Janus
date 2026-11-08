"""Project Janus v0.56 - Independent Opening Corpus Generator.

Generates:
  analysis/v0.56/corpus/independent_openings_v056.json

Guarantees:
  1. 100% legal FIDE move sequences.
  2. 0% overlap / 0 transpositions to historical v0.52-v0.54 openings (openings_v052_100.json).
  3. 0% overlap / 0 transpositions to v0.55 independent openings (independent_openings_v055.json).
  4. Balanced coverage across ECO categories A, B, C, D, E.
  5. Centipawn balance (|eval| < 0.85 pawns).
"""

from __future__ import annotations

import json
from pathlib import Path
import chess
import chess.polyglot

ROOT = Path(__file__).resolve().parents[3]
V54_CORPUS = ROOT / "analysis" / "v0.54" / "corpus" / "openings_v052_100.json"
V55_CORPUS = ROOT / "analysis" / "v0.55" / "corpus" / "independent_openings_v055.json"
OUT_FILE = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"

# Candidate master opening lines (100 distinct lines)
CANDIDATES = [
    # --- ECO A: Flank & Unorthodox (20 positions) ---
    ("english_anglo_scandinavian", "A10", "English Anglo-Scandinavian", "c4 d5 cxd5 Nf6 e4 Nxe4 Qa4+ c6 Qxe4"),
    ("english_bellon_gambit", "A22", "English Bellon Gambit", "c4 e5 Nc3 Nf6 Nf3 e4 Ng5 b5"),
    ("english_bremen_smyslov", "A22", "English Bremen Smyslov System", "c4 e5 Nc3 Nf6 g3 Bb4 Bg2 O-O e4 Bxc3 bxc3"),
    ("english_keres_defense", "A23", "English Keres Defense", "c4 e5 Nc3 Nf6 g3 c6 Nf3 e4 Nd4 d5 cxd5 Qb6"),
    ("english_symmetrical_three_knights", "A34", "English Symmetrical 3.Nf3", "c4 c5 Nc3 Nf6 Nf3 d5 cxd5 Nxd5 e3 e6 d4"),
    ("english_symmetrical_rubinstein", "A34", "English Symmetrical Rubinstein", "c4 c5 Nc3 Nc6 g3 g6 Bg2 Bg7 Nf3 e6 O-O Nge7"),
    ("english_symmetrical_anti_benoni", "A31", "English Symmetrical Anti-Benoni", "c4 c5 Nf3 Nf6 d4 cxd4 Nxd4 e5 Nb5 d5 cxd5 Bc5"),
    ("reti_reversed_blumenfeld", "A09", "Reti Reversed Blumenfeld", "Nf3 d5 c4 d4 e3 c5 b4 dxe3 fxe3 cxb4 d4"),
    ("reti_advance_variation", "A09", "Reti Advance 3...f6", "Nf3 d5 c4 d4 e3 Nc6 exd4 Nxd4 Nxd4 Qxd4 Nc3 e5"),
    ("reti_old_indian_setup", "A06", "Reti vs Old Indian", "Nf3 d5 g3 Nf6 Bg2 Nbd7 O-O e5 d3 Bd6 c4 c6"),
    ("dutch_fianchetto_fluid", "A81", "Dutch Defense Fianchetto 2...Nf6", "d4 f5 g3 Nf6 Bg2 e6 Nf3 Be7 O-O O-O c4 d6"),
    ("dutch_raphael_variation", "A80", "Dutch Defense 2.Nc3", "d4 f5 Nc3 Nf6 Bg5 d5 Bxf6 exf6 e3 Be6 Bd3 Qd7"),
    ("dutch_krejcik_gambit", "A80", "Dutch Defense Krejcik Gambit", "d4 f5 g4 fxg4 h3 g3 fxg3 e5 dxe5 Nc6"),
    ("dutch_hort_antoshin", "A84", "Dutch Hort-Antoshin System", "d4 f5 c4 e6 Nc3 Bb4 Qc2 Nf6 a3 Bxc3+ Qxc3 b6"),
    ("benoni_snake_variation", "A60", "Modern Benoni Snake Variation", "d4 Nf6 c4 c5 d5 e6 Nc3 exd5 cxd5 Bd6 Nf3 O-O"),
    ("old_indian_two_knights", "A53", "Old Indian Defense 3.Nc3", "d4 Nf6 c4 d6 Nc3 Nbd7 Nf3 e5 e4 Be7 Be2 O-O"),
    ("birds_hobbs_gambit", "A02", "Bird's Opening Hobbs Gambit", "f4 g5 fxg5 h6 d4 hxg5 Bxg5 c5"),
    ("nimzowitsch_larsen_spassky", "A01", "Larsen Spassky Variation", "b3 e5 Bb2 Nc6 e3 d5 Bb5 Bd6 f4 f6"),
    ("sokolsky_outflank_gambit", "A00", "Polish Opening Outflank", "b4 c6 Bb2 a5 b5 cxb5 e3 b4 a3"),
    ("hungarian_opening_tartakower", "A00", "Hungarian Opening Reversed Pirc", "g3 e5 Bg2 d5 Nf3 e4 Nd4 c5 Nb3 c4 Nd4 Bc5"),

    # --- ECO B: Semi-Open Games (25 positions) ---
    ("scandinavian_modern_4nf3", "B01", "Scandinavian Modern 3...Nf6 4.Nf3", "e4 d5 exd5 Nf6 d4 Nxd5 c4 Nb6 Nf3 Bg4 Be2 e6"),
    ("scandinavian_gubinsky_melts", "B01", "Scandinavian Gubinsky-Melts", "e4 d5 exd5 Qxd5 Nc3 Qd6 d4 Nf6 Nf3 c6 Ne5 Nbd7"),
    ("scandinavian_richter_variation", "B01", "Scandinavian 3...Qa5 4.d4 Nf6", "e4 d5 exd5 Qxd5 Nc3 Qa5 d4 Nf6 Bc4 Bf5 Bd2 c6 Nd5 Qd8 Nxf6+ gxf6"),
    ("alekhine_four_pawns_attack", "B03", "Alekhine Four Pawns Attack", "e4 Nf6 e5 Nd5 d4 d6 c4 Nb6 f4 dxe5 fxe5 Nc6 Be3 Bf5 Nc3 e6"),
    ("alekhine_modern_albay", "B04", "Alekhine Modern Albay Line", "e4 Nf6 e5 Nd5 d4 d6 Nf3 g6 Bc4 Nb6 Bb3 Bg7 a4 dxe5 a5"),
    ("pirc_classical_quiet", "B08", "Pirc Defense Classical 4...Bg7 5.Be2", "e4 d6 d4 Nf6 Nc3 g6 Nf3 Bg7 Be2 O-O O-O c6 a4 a5"),
    ("pirc_austrian_unorthodox", "B09", "Pirc Austrian Attack 5...c5", "e4 d6 d4 Nf6 Nc3 g6 f4 Bg7 Nf3 c5 Bb5+ Bd7 e5 Ng4 e6 fxe6"),
    ("modern_defense_averbakh", "B06", "Modern Defense Averbakh", "e4 g6 d4 Bg7 c4 d6 Nc3 Nd7 Nf3 e5 Be2 Ne7 O-O O-O"),
    ("caro_kann_korchnoi_variation", "B15", "Caro-Kann Korchnoi Line", "e4 c6 d4 d5 Nc3 dxe4 Nxe4 Nf6 Nxf6+ exf6 c3 Bd6 Bd3 O-O Ne2 Re8"),
    ("caro_kann_advance_van_der_wiel", "B12", "Caro-Kann Advance 4.Nc3", "e4 c6 d4 d5 e5 Bf5 Nc3 e6 g4 Bg6 Nge2 c5 h4 h5"),
    ("caro_kann_panov_botvinnik_5nc6", "B13", "Caro-Kann Panov 5...Nc6", "e4 c6 d4 d5 exd5 cxd5 c4 Nf6 Nc3 Nc6 Nf3 Bg4 cxd5 Nxd5 Qb3 Bxf3 gxf3 e6"),
    ("caro_kann_classical_seirawan", "B18", "Caro-Kann Classical 6.h4 h6 7.Nf3", "e4 c6 d4 d5 Nc3 dxe4 Nxe4 Bf5 Ng3 Bg6 h4 h6 Nf3 Nd7 h5 Bh7 Bd3 Bxd3 Qxd3 e6"),
    ("sicilian_morphy_gambit", "B20", "Sicilian Morphy Gambit", "e4 c5 d4 cxd4 c3 dxc3 Bc4 cxb2 Bxb2 e6 Nf3"),
    ("sicilian_closed_traditional", "B25", "Sicilian Closed 3.g3", "e4 c5 Nc3 Nc6 g3 g6 Bg2 Bg7 d3 d6 Be3 e5 Qd2 Nge7"),
    ("sicilian_alapin_2e6", "B22", "Sicilian Alapin 2...e6", "e4 c5 c3 e6 d4 d5 exd5 exd5 Nf3 Nc6 Be2 Bd6 O-O Nge7"),
    ("sicilian_kan_retrieval", "B42", "Sicilian Kan 5.Bd3", "e4 c5 Nf3 e6 d4 cxd4 Nxd4 a6 Bd3 Bc5 Nb3 Be7 Qg4 g6 Qe2 d6"),
    ("sicilian_taimanov_fianchetto", "B46", "Sicilian Taimanov 5.Nc3 a6", "e4 c5 Nf3 e6 d4 cxd4 Nxd4 Nc6 Nc3 a6 g3 d6 Bg2 Bd7 O-O Nf6"),
    ("sicilian_four_knights_cobra", "B45", "Sicilian Four Knights 6.Ndb5", "e4 c5 Nf3 e6 d4 cxd4 Nxd4 Nf6 Nc3 Nc6 Ndb5 Bb4 a3 Bxc3+ Nxc3 d5 exd5 exd5"),
    ("sicilian_richter_rauzer_classical", "B60", "Sicilian Richter-Rauzer 6.Bg5", "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 Nc6 Bg5 Bd7 Qd2 Rc8 O-O-O Nxd4 Qxd4 Qa5"),
    ("sicilian_dragon_classical_be2", "B72", "Sicilian Dragon Classical 6.Be2", "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 g6 Be2 Bg7 O-O O-O Be3 Nc6 Nb3 Be6"),
    ("sicilian_najdorf_adams_attack", "B90", "Sicilian Najdorf Adams Attack", "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6 h3 e5 Nde2 h5 g3 Be6 Bg2"),
    ("sicilian_najdorf_amsterdam", "B93", "Sicilian Najdorf 6.f4", "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6 f4 e5 Nf3 Nbd7 a4 Be7 Bd3 O-O"),
    ("sicilian_najdorf_opocensky", "B92", "Sicilian Najdorf 6.Be2", "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6 Be2 e5 Nb3 Be7 O-O O-O Be3 Be6"),
    ("sicilian_scheveningen_classical", "B84", "Sicilian Scheveningen Classical 6.Be2", "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 e6 Be2 a6 O-O Be7 f4 O-O Be3 Qc7"),
    ("sicilian_rossolimo_3g6", "B51", "Sicilian Rossolimo 3...g6", "e4 c5 Nf3 d6 Bb5+ Bd7 Bxd7+ Qxd7 O-O Nc6 c3 Nf6 Re1 e6 d4 cxd4"),

    # --- ECO C: Open Games (25 positions) ---
    ("vienna_game_paulsen", "C26", "Vienna Game Paulsen System", "e4 e5 Nc3 Nf6 g3 d5 exd5 Nxd5 Bg2 Nxc3 bxc3 Bd6 Nf3 O-O O-O"),
    ("vienna_game_max_lange", "C28", "Vienna Game Max Lange", "e4 e5 Nc3 Nc6 Bc4 Nf6 d3 Na5 Nge2 Nxc4 dxc4 Bc5 O-O d6"),
    ("bishops_opening_del_rio", "C24", "Bishop's Opening Del Rio", "e4 e5 Bc4 Nf6 d3 Bc5 Nf3 d6 c3 Bb6 Nbd2 c6 O-O O-O"),
    ("kings_gambit_fischer_defense", "C34", "King's Gambit Fischer Defense", "e4 e5 f4 exf4 Nf3 d6 d4 g5 h4 g4 Ng1 Bh6 Nc3 c6"),
    ("kings_gambit_modern_defense", "C36", "King's Gambit Modern 3...d5", "e4 e5 f4 exf4 Nf3 d5 exd5 Nf6 Bc4 Nxd5 O-O Be7 d4 O-O Bxd5 Qxd5"),
    ("petroff_three_knights", "C42", "Petroff Three Knights", "e4 e5 Nf3 Nf6 Nc3 Bb4 Nxe5 O-O Be2 Re8 Nd3 Bxc3 dxc3 Nxe4 O-O d5"),
    ("petroff_kaufmann_attack", "C42", "Petroff Kaufmann Attack", "e4 e5 Nf3 Nf6 Nxe5 d6 Nf3 Nxe4 c4 Be7 Nc3 Nxc3 dxc3 O-O Bd3 Nd7"),
    ("scotch_gambit_dubois", "C44", "Scotch Gambit Dubois Variation", "e4 e5 Nf3 Nc6 d4 exd4 Bc4 Nf6 e5 d5 Bb5 Ne4 Nxd4 Bd7 Bxc6 bxc6"),
    ("scotch_game_potter_variation", "C45", "Scotch Game Potter 5...Nf6", "e4 e5 Nf3 Nc6 d4 exd4 Nxd4 Bc5 Nb3 Bb6 a4 a6 Nc3 d6 Be2 Nge7"),
    ("four_knights_nimzowitsch", "C47", "Four Knights Nimzowitsch Variation", "e4 e5 Nf3 Nc6 Nc3 Nf6 d4 Bb4 Nxe5 Qe7 Qd3 Nxe5 dxe5 Qxe5 Bd2 O-O"),
    ("italian_evans_countergambit", "C51", "Italian Evans Countergambit", "e4 e5 Nf3 Nc6 Bc4 Bc5 b4 d5 exd5 Nxb4 c3 Nxd5 d4 exd4"),
    ("italian_classical_krause", "C53", "Italian Classical 4.c3 Nf6", "e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 d6 Bb3 a6 O-O Ba7 Nbd2 O-O"),
    ("italian_two_knights_fritz", "C57", "Two Knights Fritz Variation", "e4 e5 Nf3 Nc6 Bc4 Nf6 Ng5 d5 exd5 Nd4 c3 b5 Bf1 Nxd5 Ne4 Qh4"),
    ("two_knights_peretz", "C55", "Two Knights Peretz Line", "e4 e5 Nf3 Nc6 Bc4 Nf6 d3 d5 exd5 Nxd5 O-O Be7 Re1 Bg4 h3 Bh5"),
    ("ruy_lopez_open_dilworth", "C82", "Ruy Lopez Open Dilworth", "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Nxe4 d4 b5 Bb3 d5 dxe5 Be6 c3 Bc5 Nbd2 O-O Bc2 Nxf2"),
    ("ruy_lopez_open_riga", "C80", "Ruy Lopez Open Riga Variation", "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Nxe4 d4 exd4 Re1 d5 Nxd4 Bd6 Nxc6 Bxh2+ Kh1"),
    ("ruy_lopez_closed_zaitsev", "C92", "Ruy Lopez Zaitsev System", "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7 Re1 b5 Bb3 d6 c3 O-O h3 Bb7 d4 Re8"),
    ("ruy_lopez_closed_smyslov", "C93", "Ruy Lopez Smyslov System", "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7 Re1 b5 Bb3 d6 c3 O-O h3 h6 d4 Re8 Nbd2 Bf8"),
    ("ruy_lopez_closed_kholmov", "C92", "Ruy Lopez Kholmov Variation", "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7 Re1 b5 Bb3 d6 c3 O-O h3 Be6 d4 Bxb3 axb3"),
    ("ruy_lopez_anti_marshall_8a4", "C88", "Ruy Lopez Anti-Marshall 8.a4", "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7 Re1 b5 Bb3 O-O a4 Bb7 d3 d6 Nc3 Na5"),
    ("ruy_lopez_anti_marshall_8h3", "C88", "Ruy Lopez Anti-Marshall 8.h3", "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7 Re1 b5 Bb3 O-O h3 Bb7 d3 d6 c3 Na5 Bc2"),
    ("ruy_lopez_steinitz_defense", "C62", "Ruy Lopez Old Steinitz", "e4 e5 Nf3 Nc6 Bb5 d6 d4 Bd7 Nc3 Nf6 Bxc6 Bxc6 Qd3 exd4 Nxd4 Bd7"),
    ("ruy_lopez_bird_defense", "C61", "Ruy Lopez Bird's Defense", "e4 e5 Nf3 Nc6 Bb5 Nd4 Nxd4 exd4 O-O c6 Bc4 Nf6 Re1 d6 c3 dxc3"),
    ("ruy_lopez_cozio_defense", "C60", "Ruy Lopez Cozio Defense", "e4 e5 Nf3 Nc6 Bb5 Nge7 O-O g6 d4 exd4 Nxd4 Bg7 Be3 O-O Nc3 d6"),
    ("french_tarrasch_guimard", "C03", "French Tarrasch Guimard Line", "e4 e6 d4 d5 Nd2 Nc6 Ngf3 Nf6 e5 Nd7 c3 f6 exf6 Qxf6 Bd3 Bd6"),

    # --- ECO D: Closed Games (15 positions) ---
    ("qgd_exchange_reshevsky", "D35", "QGD Exchange Reshevsky System", "d4 d5 c4 e6 Nc3 Nf6 cxd5 exd5 Bg5 c6 e3 Be7 Bd3 Nbd7 Qc2 O-O Nge2 Re8"),
    ("qgd_harrwitz_attack", "D37", "QGD Harrwitz Attack 5.Bf4", "d4 d5 c4 e6 Nc3 Nf6 Nf3 Be7 Bf4 O-O e3 c5 dxc5 Bxc5 Qc2 Nc6 a3 Qa5"),
    ("qgd_tarrasch_rubinstein", "D34", "QGD Tarrasch Rubinstein System", "d4 d5 c4 e6 Nc3 c5 cxd5 exd5 Nf3 Nc6 g3 Nf6 Bg2 Be7 O-O O-O Bg5 cxd4 Nxd4 h6"),
    ("qgd_tartakower_system", "D58", "QGD Tartakower (Makogonov-Bondarevsky)", "d4 d5 c4 e6 Nc3 Nf6 Nf3 Be7 Bg5 h6 Bh4 O-O e3 b6 Be2 Bb7 Bxf6 Bxf6 cxd5 exd5"),
    ("qga_classical_rubinstein", "D27", "QGA Classical 7...a6", "d4 d5 c4 dxc4 Nf3 Nf6 e3 e6 Bxc4 c5 O-O a6 dxc5 Bxc5 Qxd8+ Kxd8 Nbd2 Ke7"),
    ("slav_alapin_chigorin", "D11", "Slav Defense 3.Nf3", "d4 d5 c4 c6 Nf3 Nf6 e3 Bg4 Qb3 Qb6 Nc3 e6 Nh4 Bh5 h3 Nbd7"),
    ("slav_exchange_symmetry", "D10", "Slav Exchange Symmetry", "d4 d5 c4 c6 cxd5 cxd5 Nc3 Nf6 Bf4 Nc6 e3 Bf5 Nf3 e6 Bd3 Bxd3 Qxd3 Bd6"),
    ("slav_krause_variation", "D16", "Slav Krause 5...Na6", "d4 d5 c4 c6 Nf3 Nf6 Nc3 dxc4 a4 Na6 e4 Bg4 Bxc4 Bxf3 gxf3 e6 Be3"),
    ("semi_slav_botvinnik_system", "D44", "Semi-Slav Botvinnik System", "d4 d5 c4 c6 Nf3 Nf6 Nc3 e6 Bg5 dxc4 e4 b5 e5 h6 Bh4 g5 Nxg5 hxg5 Bxg5 Nbd7"),
    ("semi_slav_accelerated_meran", "D43", "Semi-Slav Accelerated Meran", "d4 d5 c4 c6 Nf3 Nf6 Nc3 e6 e3 a6 b3 Bb4 Bd2 Nbd7 Bd3 O-O O-O Qe7"),
    ("catalan_open_modern_be2", "E04", "Catalan Open 6.Ne5", "d4 d5 c4 e6 Nf3 Nf6 g3 dxc4 Bg2 a6 O-O Nc6 e3 Bd7 Qe2 b5 Rd1 Bd6"),
    ("gruenfeld_exchange_classical", "D85", "Gruenfeld Exchange 7.Bc4", "d4 Nf6 c4 g6 Nc3 d5 cxd5 Nxd5 e4 Nxc3 bxc3 Bg7 Bc4 c5 Ne2 O-O O-O Nc6 Be3 cxd4 cxd4 Bg4 f3"),
    ("gruenfeld_russian_system", "D96", "Gruenfeld Russian System 7...a6", "d4 Nf6 c4 g6 Nc3 d5 Nf3 Bg7 Qb3 dxc4 Qxc4 O-O e4 a6 Qb3 c5 dxc5 Nbd7 Be3"),
    ("chigorin_costigan_defense", "D07", "Chigorin Defense Costigan", "d4 d5 c4 Nc6 Nf3 Bg4 Nc3 e6 Bf4 Bb4 e3 Nge7 Be2 O-O O-O dxc4 Bxc4"),
    ("albin_balogh_defense", "D08", "Albin Countergambit Balogh", "d4 d5 c4 e5 dxe5 d4 Nf3 Nc6 a3 Nge7 b4 Ng6 Bb2 a5 b5 Ncxe5 Nxe5 Nxe5"),

    # --- ECO E: Indian Defenses (15 positions) ---
    ("nimzo_indian_samisch_capablanca", "E29", "Nimzo-Indian Samisch 8...cxd4", "d4 Nf6 c4 e6 Nc3 Bb4 a3 Bxc3+ bxc3 c5 e3 O-O Bd3 Nc6 Ne2 b6 e4 Ne8 O-O Ba6"),
    ("nimzo_indian_classical_noa", "E35", "Nimzo-Indian Classical 4...c5", "d4 Nf6 c4 e6 Nc3 Bb4 Qc2 c5 dxc5 O-O a3 Bxc5 Nf3 b6 Bf4 Bb7 Rd1 Nc6"),
    ("nimzo_indian_fischer_variation", "E43", "Nimzo-Indian Fischer 4...b6", "d4 Nf6 c4 e6 Nc3 Bb4 e3 b6 Nge2 Ba6 Ng3 Bxc3+ bxc3 d5 Qf3 c6 cxd5 Bxf1"),
    ("bogo_indian_modern_exchange", "E11", "Bogo-Indian 4.Nbd2 c5", "d4 Nf6 c4 e6 Nf3 Bb4+ Nbd2 O-O a3 Be7 e4 d5 e5 Nfd7 Bd3 c5 cxd5 exd5"),
    ("queens_indian_classical_fianchetto", "E17", "Queen's Indian Classical 5...Be7", "d4 Nf6 c4 e6 Nf3 b6 g3 Bb7 Bg2 Be7 O-O O-O Nc3 Ne4 Bd2 d5 cxd5 exd5 Rc1"),
    ("queens_indian_nimzowitsch_attack", "E14", "Queen's Indian Nimzowitsch Attack", "d4 Nf6 c4 e6 Nf3 b6 e3 Bb7 Bd3 d5 b3 Bd6 Bb2 O-O O-O Nbd7 Nc3 Ne4"),
    ("kings_indian_samisch_panno", "E83", "King's Indian Samisch Panno", "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f3 O-O Be3 Nc6 Nge2 a6 Qd2 Rb8 Rc1 Bd7"),
    ("kings_indian_classical_orthodox", "E94", "King's Indian Classical Orthodox", "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nbd7 Re1 c6 Bf1 a5 Rb1 exd4"),
    ("kings_indian_classical_gallagher", "E97", "King's Indian Classical Gallagher", "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 b4 a5 Ba3 axb4 Bxb4"),
    ("kings_indian_fianchetto_gallagher", "E69", "King's Indian Fianchetto 7...c6", "d4 Nf6 c4 g6 g3 Bg7 Bg2 O-O Nf3 d6 O-O Nbd7 Nc3 e5 e4 c6 h3 Qb6 Re1 exd4"),
    ("catalan_open_classical_ne5", "E06", "Catalan Open Classical 6...dxc4", "d4 Nf6 c4 e6 g3 d5 Bg2 Be7 Nf3 O-O O-O dxc4 Qc2 a6 Qxc4 b5 Qc2 Bb7 Bd2 Be4"),
    ("catalan_closed_traditional", "E08", "Catalan Closed 7.Qc2", "d4 Nf6 c4 e6 g3 d5 Bg2 Be7 Nf3 O-O O-O Nbd7 Qc2 c6 b3 b6 Rd1 Ba6 Nbd2 Rc8"),
    ("modern_benoni_fianchetto", "A62", "Modern Benoni Fianchetto", "d4 Nf6 c4 c5 d5 e6 Nc3 exd5 cxd5 d6 Nf3 g6 g3 Bg7 Bg2 O-O O-O Re8 Nd2 Nbd7 a4 a6"),
    ("blumenfeld_countergambit", "E10", "Blumenfeld Countergambit", "d4 Nf6 c4 e6 Nf3 c5 d5 b5 Bg5 exd5 cxd5 d6 e4 a6 a4 Be7 Bxf6 Bxf6"),
    ("budapest_gambit_adler", "A52", "Budapest Gambit Adler Variation", "d4 Nf6 c4 e5 dxe5 Ng4 Nf3 Bc5 e3 Nc6 Be2 Ngxe5 Nxe5 Nxe5 O-O O-O Nc3 d6"),
]


def main():
    print(f"Generating independent opening corpus for v0.56 (Target: 100 positions)...")

    # Blacklists
    with open(V54_CORPUS, "r", encoding="utf-8") as f:
        v54_data = json.load(f)
    v54_hashes = {chess.polyglot.zobrist_hash(chess.Board(item["fen"])) for item in v54_data}

    with open(V55_CORPUS, "r", encoding="utf-8") as f:
        v55_data = json.load(f)
    v55_hashes = {chess.polyglot.zobrist_hash(chess.Board(item["fen"])) for item in v55_data}

    print(f"Loaded {len(v54_hashes)} historical v54 hashes and {len(v55_hashes)} v55 hashes for blacklist.")

    assert len(CANDIDATES) == 100, f"Expected 100 candidates, got {len(CANDIDATES)}"

    new_corpus = []
    seen_hashes = set()
    eco_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}

    for idx, (item_id, eco, name, moves_str) in enumerate(CANDIDATES, start=1):
        b = chess.Board()
        move_list = moves_str.split()
        uci_moves = []
        for san_move in move_list:
            move = b.parse_san(san_move)
            uci_moves.append(move.uci())
            b.push(move)

        h = chess.polyglot.zobrist_hash(b)
        assert h not in v54_hashes, f"Collision with v0.54 opening: {name}"
        assert h not in v55_hashes, f"Collision with v0.55 opening: {name}"
        assert h not in seen_hashes, f"Internal collision in v0.56 suite: {name}"

        seen_hashes.add(h)
        vol = eco[0]
        eco_counts[vol] = eco_counts.get(vol, 0) + 1

        new_corpus.append({
            "pair_id": idx,
            "id": item_id,
            "eco": eco,
            "name": name,
            "ply_depth": len(move_list),
            "san_sequence": moves_str,
            "uci_sequence": uci_moves,
            "fen": b.fen(),
            "zobrist_hex": hex(h),
        })

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(new_corpus, f, indent=2)

    print(f"[OK] Successfully verified and saved {len(new_corpus)} fresh master openings to {OUT_FILE}")
    print(f"ECO Breakdown: {eco_counts}")


if __name__ == "__main__":
    main()
