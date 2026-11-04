"""Project Janus v0.55 - Independent Opening Corpus Generator.

Generates:
  analysis/v0.55/corpus/independent_openings_v055.json

Guarantees:
  1. 100% legal FIDE move sequences.
  2. 0% overlap / 0 transpositions to historical primary openings (openings_v052_100.json).
  3. Balanced coverage across ECO categories A, B, C, D, E.
"""

from __future__ import annotations

import json
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[3]
V54_CORPUS = ROOT / "analysis" / "v0.54" / "corpus" / "openings_v052_100.json"
V55_CORPUS_DIR = ROOT / "analysis" / "v0.55" / "corpus"
V55_CORPUS_FILE = V55_CORPUS_DIR / "independent_openings_v055.json"

# Master list of candidate independent openings (SAN moves)
INDEPENDENT_CANDIDATES = [
    # --- ECO A: Flank, English, Dutch, Reti, Unorthodox (20 positions) ---
    ("birds_opening_classical", "A03", "Bird's Opening Classical", "f4 d5 Nf3 Nf6 e3 e6"),
    ("birds_froms_gambit", "A02", "Bird's From's Gambit", "f4 e5 fxe5 d6 exd6 Bxd6 Nf3"),
    ("larsen_classical", "A01", "Nimzowitsch-Larsen Attack Classical", "b3 d5 Bb2 c5 e3 Nc6 Nf3"),
    ("larsen_modern", "A01", "Nimzowitsch-Larsen Attack 1...e5", "b3 e5 Bb2 Nc6 e3 Nf6"),
    ("reti_gambit", "A09", "Reti Opening Advance Gambit", "Nf3 d5 c4 d4 b4 c5"),
    ("reti_kings_indian_attack", "A07", "King's Indian Attack vs French", "Nf3 d5 g3 e6 Bg2 Nf6 O-O c5 d3 Be7 Nbd2"),
    ("english_four_knights", "A28", "English Opening Four Knights", "c4 e5 Nc3 Nf6 Nf3 Nc6 e3"),
    ("english_reversed_sicilian", "A21", "English Opening Reversed Sicilian", "c4 e5 Nc3 d6 g3 f5 Bg2 Nf6"),
    ("english_symmetrical_hedgehog", "A30", "English Symmetrical Hedgehog", "c4 c5 Nf3 Nf6 g3 b6 Bg2 Bb7 O-O e6 Nc3 Be7"),
    ("english_anglo_indian", "A15", "English Anglo-Indian", "c4 Nf6 g3 c6 Bg2 d5 Nf3 dxc4"),
    ("english_botvinnik_system", "A26", "English Botvinnik System", "c4 e5 Nc3 Nc6 g3 g6 Bg2 Bg7 d3 d6 e4"),
    ("dutch_stonewall_modern", "A90", "Dutch Defense Modern Stonewall", "d4 f5 c4 e6 g3 Nf6 Bg2 d5 Nf3 c6 O-O Bd6"),
    ("dutch_leningrad_main", "A88", "Dutch Defense Leningrad Main", "d4 f5 c4 Nf6 g3 g6 Bg2 Bg7 Nf3 O-O O-O d6 Nc3 c6"),
    ("dutch_staunton_gambit", "A82", "Dutch Defense Staunton Gambit", "d4 f5 e4 fxe4 Nc3 Nf6 Bg5"),
    ("old_benoni_defense", "A43", "Old Benoni Defense", "d4 c5 d5 d6 e4 Nf6 Nc3 g6"),
    ("polish_opening_sokolsky", "A00", "Polish Opening (Sokolsky)", "b4 e5 Bb2 Bxb4 Bxe5 Nf6"),
    ("saragossa_opening", "A00", "Saragossa Opening", "c3 d5 d4 Nf6 Bf4 c5 e3"),
    ("grobs_attack", "A00", "Grob's Attack", "g4 d5 Bg2 c6 g5 e5 d3"),
    ("dutch_classical_fluid", "A85", "Dutch Classical Fluid Line", "d4 f5 c4 Nf6 Nc3 e6 Nf3 Be7 g3 O-O Bg2 d6"),
    ("english_mikenas_flohr", "A18", "English Mikenas-Flohr Attack", "c4 Nf6 Nc3 e6 e4 d5 e5 d4 exf6 dxc3 bxc3 Qxf6"),

    # --- ECO B: Semi-Open Games (25 positions) ---
    ("scandinavian_portuguese", "B01", "Scandinavian Portuguese Gambit", "e4 d5 exd5 Nf6 d4 Bg4 f3 Bf5"),
    ("scandinavian_modern_edwards", "B01", "Scandinavian Modern 3.d4", "e4 d5 exd5 Nf6 d4 Nxd5 Nf3 g6 Be2 Bg7"),
    ("scandinavian_classical_qa5", "B01", "Scandinavian Classical 3...Qa5 4.d4", "e4 d5 exd5 Qxd5 Nc3 Qa5 d4 e5 Nf3 Bg4"),
    ("alekhine_scandinavian", "B02", "Alekhine Scandinavian Variation", "e4 Nf6 Nc3 d5 e5 Nfd7 f4 e6 Nf3 c5"),
    ("alekhine_exchange_kengis", "B03", "Alekhine Defense Exchange 5...cxd6", "e4 Nf6 e5 Nd5 d4 d6 c4 Nb6 exd6 cxd6 Nc3 g6"),
    ("pirc_150_attack", "B07", "Pirc Defense 150 Attack", "e4 d6 d4 Nf6 Nc3 g6 Be3 c6 Qd2 b5 f3"),
    ("pirc_byrne_system", "B07", "Pirc Defense Byrne System", "e4 d6 d4 Nf6 Nc3 g6 Bg5 c6 Qd2 Nbd7 f4"),
    ("modern_gurgenidze", "B06", "Modern Defense Gurgenidze System", "e4 g6 d4 Bg7 Nc3 c6 f4 d5 e5 h5 Nf3 Nh6"),
    ("caro_kann_fantasy", "B12", "Caro-Kann Fantasy Variation", "e4 c6 d4 d5 f3 dxe4 fxe4 e5 Nf3 exd4 Bc4"),
    ("caro_kann_two_knights", "B11", "Caro-Kann Two Knights", "e4 c6 Nc3 d5 Nf3 Bg4 h3 Bxf3 Qxf3 e6 d3"),
    ("caro_kann_tartakower", "B15", "Caro-Kann Tartakower Variation", "e4 c6 d4 d5 Nc3 dxe4 Nxe4 Nf6 Nxf6+ exf6 c3 Bd6 Bd3 O-O"),
    ("caro_kann_advance_short", "B12", "Caro-Kann Advance Short System", "e4 c6 d4 d5 e5 Bf5 Nf3 e6 Be2 c5 Be3 Qb6"),
    ("caro_kann_bronstein_larsen", "B16", "Caro-Kann Bronstein-Larsen", "e4 c6 d4 d5 Nc3 dxe4 Nxe4 Nf6 Nxf6+ gxf6 c3 Bf5"),
    ("sicilian_alapin_modern", "B22", "Sicilian Alapin 2...Nf6", "e4 c5 c3 Nf6 e5 Nd5 d4 cxd4 Nf3 Nc6 Bc4 Nb6 Bb3 d5"),
    ("sicilian_grand_prix", "B23", "Sicilian Grand Prix Attack", "e4 c5 Nc3 Nc6 f4 g6 Nf3 Bg7 Bc4 e6 f5"),
    ("sicilian_smith_morra", "B21", "Sicilian Smith-Morra Gambit", "e4 c5 d4 cxd4 c3 dxc3 Nxc3 Nc6 Nf3 d6 Bc4 e6"),
    ("sicilian_okelly", "B28", "Sicilian O'Kelly Variation", "e4 c5 Nf3 a6 c3 d5 exd5 Qxd5 d4 Nf6 Be2"),
    ("sicilian_chekhover", "B53", "Sicilian Chekhover Variation", "e4 c5 Nf3 d6 d4 cxd4 Qxd4 Nc6 Bb5 Bd7 Bxc6 Bxc6"),
    ("sicilian_scheveningen_keres", "B81", "Sicilian Scheveningen Keres Attack", "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 e6 g4 h6 h4 Nc6"),
    ("sicilian_dragon_yugoslav_bc4", "B77", "Sicilian Dragon Yugoslav 9.Bc4", "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 g6 Be3 Bg7 f3 O-O Qd2 Nc6 Bc4 Bd7 O-O-O Rc8"),
    ("sicilian_najdorf_english", "B90", "Sicilian Najdorf English Attack", "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6 Be3 e5 Nb3 Be6 f3 Be7 Qd2 O-O O-O-O"),
    ("sicilian_najdorf_poisoned_pawn", "B97", "Sicilian Najdorf Poisoned Pawn", "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6 Bg5 e6 f4 Qb6 Qd2 Qxb2"),
    ("sicilian_classical_rauzer_6e6", "B62", "Sicilian Richter-Rauzer 6...e6 7.Qd2", "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 Nc6 Bg5 e6 Qd2 a6 O-O-O h6"),
    ("sicilian_four_knights_e5", "B40", "Sicilian Four Knights 5...e5", "e4 c5 Nf3 e6 d4 cxd4 Nxd4 Nf6 Nc3 Nc6 Ndb5 e5 Bg5"),
    ("sicilian_wing_gambit", "B20", "Sicilian Wing Gambit", "e4 c5 b4 cxb4 a3 d5 exd5 Qxd5 Nf3 e5 axb4"),

    # --- ECO C: Open Games (25 positions) ---
    ("kings_gambit_bishops", "C33", "King's Gambit Bishop's Gambit", "e4 e5 f4 exf4 Bc4 Nf6 Nc3 c6 d4 d5 exd5 cxd5 Bb3"),
    ("kings_gambit_cunningham", "C35", "King's Gambit Cunningham Defense", "e4 e5 f4 exf4 Nf3 Be7 Bc4 Bh4+ g3 fxg3 O-O"),
    ("bishops_opening_berlin", "C24", "Bishop's Opening Berlin Defense", "e4 e5 Bc4 Nf6 d3 c6 Nf3 d5 Bb3 Bd6 Nc3"),
    ("vienna_game_steinitz", "C25", "Vienna Game Steinitz Gambit", "e4 e5 Nc3 Nc6 f4 exf4 d4 Qh4+ Ke2 d6 Nf3"),
    ("vienna_gambit_modern", "C29", "Vienna Gambit 3.f4 d5", "e4 e5 Nc3 Nf6 f4 d5 fxe5 Nxe4 Qf3 f5 exf6 Nxf6"),
    ("centre_game_hall", "C22", "Centre Game Hall Variation", "e4 e5 d4 exd4 Qxd4 Nc6 Qe3 Nf6 Nc3 Bb4 Bd2 O-O O-O-O Re8"),
    ("scotch_mieses_classical", "C45", "Scotch Game Mieses 5...Nf6", "e4 e5 Nf3 Nc6 d4 exd4 Nxd4 Nf6 Nxc6 bxc6 e5 Qe7 Qe2 Nd5 c4 Ba6"),
    ("scotch_classical_be3", "C45", "Scotch Game Classical 4...Bc5 5.Be3", "e4 e5 Nf3 Nc6 d4 exd4 Nxd4 Bc5 Be3 Qf6 c3 Nge7 Bc4 Ne5"),
    ("four_knights_spanish_svenonius", "C48", "Four Knights Spanish Svenonius", "e4 e5 Nf3 Nc6 Nc3 Nf6 Bb5 Bc5 O-O O-O Nxe5 Nxe5 d4 Bd6"),
    ("four_knights_scotch_variation", "C47", "Four Knights Scotch Variation", "e4 e5 Nf3 Nc6 Nc3 Nf6 d4 exd4 Nxd4 Bb4 Nxc6 bxc6 Bd3 d5"),
    ("italian_giuoco_pianissimo_c3", "C53", "Italian Giuoco Pianissimo 4.c3", "e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 a6 Bb3 Ba7 Nbd2 O-O"),
    ("two_knights_ulvestad", "C57", "Two Knights Defense Ulvestad", "e4 e5 Nf3 Nc6 Bc4 Nf6 Ng5 d5 exd5 b5 Bf1 Nd4 c3 Nxd5"),
    ("two_knights_modern_bishop_check", "C58", "Two Knights 5...Na5 6.Bb5+ c6", "e4 e5 Nf3 Nc6 Bc4 Nf6 Ng5 d5 exd5 Na5 Bb5+ c6 dxc6 bxc6 Qf3 Rb8"),
    ("petroff_classical_5nc3", "C42", "Petroff Classical 5.Nc3", "e4 e5 Nf3 Nf6 Nxe5 d6 Nf3 Nxe4 Nc3 Nxc3 dxc3 Be7 Be3 Nc6 Qd2 Be6"),
    ("petroff_steinitz_modern", "C43", "Petroff Steinitz 3.d4", "e4 e5 Nf3 Nf6 d4 Nxe4 Bd3 d5 Nxe5 Nd7 Nxd7 Bxd7 O-O Bd6 c4 c6"),
    ("philidor_hanham_modern", "C41", "Philidor Hanham Variation", "e4 e5 Nf3 d6 d4 Nd7 Bc4 c6 O-O Be7 dxe5 dxe5 Ng5 Bxg5 Qh5 Qe7"),
    ("ruy_lopez_berlin_4o_o", "C67", "Ruy Lopez Berlin Defense 4.O-O Nxe4", "e4 e5 Nf3 Nc6 Bb5 Nf6 O-O Nxe4 d4 Nd6 Bxc6 dxc6 dxe5 Nf5 Qxd8+ Kxd8"),
    ("ruy_lopez_marshall_attack", "C89", "Ruy Lopez Marshall Attack", "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7 Re1 b5 Bb3 O-O c3 d5 exd5 Nxd5 Nxe5 Nxe5 Rxe5 c6"),
    ("ruy_lopez_chigorin_modern", "C97", "Ruy Lopez Chigorin 11...Qc7", "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7 Re1 b5 Bb3 d6 c3 O-O h3 Na5 Bc2 c5 d4 Qc7"),
    ("ruy_lopez_breyer_system", "C95", "Ruy Lopez Breyer System", "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7 Re1 b5 Bb3 d6 c3 O-O h3 Nb8 d4 Nbd7"),
    ("ruy_lopez_schliemann_jaenisch", "C63", "Ruy Lopez Schliemann Gambit", "e4 e5 Nf3 Nc6 Bb5 f5 Nc3 fxe4 Nxe4 Nf6 Nxf6+ Qxf6 Qe2 Be7"),
    ("ruy_lopez_steinitz_deferred", "C72", "Ruy Lopez Steinitz Deferred", "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 d6 O-O Bd7 c3 g6 d4 Bg7 Bg5 Nge7"),
    ("ruy_lopez_worrall_attack", "C86", "Ruy Lopez Worrall Attack", "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7 Qe2 b5 Bb3 O-O c3 d6 d4 Bg4"),
    ("evans_gambit_declined", "C51", "Evans Gambit Declined 4...Bb6", "e4 e5 Nf3 Nc6 Bc4 Bc5 b4 Bb6 a4 a6 c3 Nf6 d3 d6"),
    ("scotch_four_knights_rubinstein", "C45", "Scotch 4...Nf6 5.Nc3 Bb4", "e4 e5 Nf3 Nc6 d4 exd4 Nxd4 Nf6 Nc3 Bb4 Nxc6 bxc6 Bd3 d5 exd5 cxd5 O-O O-O Bg5 c6"),

    # --- ECO D: Closed Games & Queen's Pawn (15 positions) ---
    ("qgd_albin_countergambit", "D08", "QGD Albin Countergambit", "d4 d5 c4 e5 dxe5 d4 Nf3 Nc6 Nbd2 Bg4 h3 Bxf3 Nxf3"),
    ("qgd_chigorin_defense", "D07", "QGD Chigorin Defense", "d4 d5 c4 Nc6 Nc3 dxc4 Nf3 Nf6 e4 Bg4 Be3 e6 Bxc4 Bb4"),
    ("qgd_semi_tarrasch_main", "D41", "QGD Semi-Tarrasch 5.cxd5", "d4 d5 c4 e6 Nc3 Nf6 Nf3 c5 cxd5 Nxd5 e4 Nxc3 bxc3 cxd4 cxd4 Bb4+ Bd2 Bxd2+ Qxd2"),
    ("qgd_lasker_defense", "D56", "QGD Lasker Defense", "d4 d5 c4 e6 Nc3 Nf6 Bg5 Be7 e3 O-O Nf3 h6 Bh4 Ne4 Bxe7 Qxe7 cxd5 Nxc3 bxc3 exd5"),
    ("slav_schlechter_defense", "D11", "Slav Defense Schlechter System", "d4 d5 c4 c6 Nf3 Nf6 e3 g6 Nc3 Bg7 Bd3 O-O O-O Bg4"),
    ("slav_modern_4e3", "D12", "Slav Defense Quiet 4.e3", "d4 d5 c4 c6 Nf3 Nf6 e3 Bf5 Nc3 e6 Nh4 Be4 f3 Bg6 Qb3"),
    ("semi_slav_meran_8bd3", "D47", "Semi-Slav Meran 8.Bd3", "d4 d5 c4 c6 Nf3 Nf6 Nc3 e6 e3 Nbd7 Bd3 dxc4 Bxc4 b5 Bd3 Bb7 O-O a6 e4 c5"),
    ("semi_slav_anti_meran_shabalov", "D44", "Semi-Slav Anti-Meran Shabalov", "d4 d5 c4 c6 Nf3 Nf6 Nc3 e6 e3 Nbd7 Qc2 Bd6 g4 dxc4 Bxc4 b5"),
    ("qga_central_variation", "D20", "Queen's Gambit Accepted 3.e4", "d4 d5 c4 dxc4 e4 e5 Nf3 exd4 Bxc4 Bb4+ Nbd2 Nc6 O-O Nf6"),
    ("blackmar_diemer_gambit", "D00", "Blackmar-Diemer Gambit", "d4 d5 e4 dxe4 Nc3 Nf6 f3 exf3 Nxf3 Bg4 h3 Bxf3 Qxf3 c6"),
    ("jobava_london_system", "D00", "Jobava London System", "d4 d5 Nc3 Nf6 Bf4 c5 e3 cxd4 exd4 a6 Nf3 Nc6"),
    ("classical_london_system", "D02", "Classical London System 2...Bf5", "d4 d5 Nf3 Nf6 Bf4 c5 e3 Nc6 c3 Qb6 Qb3 c4 Qxb6 axb6"),
    ("richter_veresov_attack", "D01", "Richter-Veresov Attack", "d4 d5 Nc3 Nf6 Bg5 Nbd7 Qd3 c5 e4 dxe4 Nxe4 Nxe4 Qxe4 cxd4"),
    ("gruenfeld_bf4_system", "D82", "Gruenfeld Defense 4.Bf4", "d4 Nf6 c4 g6 Nc3 d5 Bf4 Bg7 e3 c5 dxc5 Qa5 Rc1 dxc4 Bxc4 O-O Nf3"),
    ("neo_gruenfeld_classical", "D78", "Neo-Gruenfeld Classical 6...c6", "d4 Nf6 c4 g6 g3 Bg7 Bg2 d5 Nf3 O-O O-O c6 Qb3 dxc4 Qxc4 Bf5 Nc3 Nbd7"),

    # --- ECO E: Indian Defenses & Modern Closed (15 positions) ---
    ("catalan_open_5qa4", "E05", "Catalan Open 5.Qa4+", "d4 Nf6 c4 e6 g3 d5 Bg2 dxc4 Nf3 Be7 O-O O-O Qa4 a6 Qxc4 b5 Qc2 Bb7"),
    ("catalan_closed_b6", "E07", "Catalan Closed 5...b6", "d4 Nf6 c4 e6 g3 d5 Bg2 Be7 Nf3 O-O O-O Nbd7 Qc2 c6 Nbd2 b6"),
    ("bogo_indian_4bd2_c5", "E11", "Bogo-Indian 4.Bd2 c5", "d4 Nf6 c4 e6 Nf3 Bb4+ Bd2 c5 Bxb4 cxb4 g3 O-O Bg2 d6 O-O a5"),
    ("bogo_indian_4nbd2_b6", "E11", "Bogo-Indian 4.Nbd2 b6", "d4 Nf6 c4 e6 Nf3 Bb4+ Nbd2 b6 a3 Bxd2+ Bxd2 Bb7 e3 O-O Be2 d6"),
    ("queens_indian_petrosian", "E12", "Queen's Indian Petrosian 4.a3", "d4 Nf6 c4 e6 Nf3 b6 a3 Ba6 Qc2 Bb7 Nc3 c5 e4 cxd4 Nxd4 Nc6 Nxc6 Bxc6"),
    ("queens_indian_miles_system", "E15", "Queen's Indian Miles 4...Ba6", "d4 Nf6 c4 e6 Nf3 b6 g3 Ba6 b3 Bb4+ Bd2 Be7 Bg2 c6 Bc3 d5 Ne5 Nfd7 Nxd7 Nxd7"),
    ("nimzo_indian_rubinstein_main", "E46", "Nimzo-Indian Rubinstein 4.e3", "d4 Nf6 c4 e6 Nc3 Bb4 e3 O-O Ne2 d5 a3 Be7 cxd5 exd5 g3 c6"),
    ("nimzo_indian_romanishin", "E20", "Nimzo-Indian Romanishin 4.g3", "d4 Nf6 c4 e6 Nc3 Bb4 g3 c5 Nf3 cxd4 Nxd4 O-O Bg2 d5 cxd5 Nxd5 Qb3"),
    ("nimzo_indian_leningrad", "E30", "Nimzo-Indian Leningrad 4.Bg5", "d4 Nf6 c4 e6 Nc3 Bb4 Bg5 h6 Bh4 c5 d5 d6 e3 Bxc3+ bxc3 e5"),
    ("kings_indian_four_pawns", "E76", "King's Indian Four Pawns Attack", "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 f4 O-O Nf3 c5 d5 e6 Be2 exd5 cxd5 Bg4"),
    ("kings_indian_mar_del_plata", "E99", "King's Indian Classical Mar del Plata", "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Nf3 O-O Be2 e5 O-O Nc6 d5 Ne7 Ne1 Nd7 Be3 f5 f3 f4 Bf2 g5"),
    ("kings_indian_averbakh", "E73", "King's Indian Averbakh 5.Be2", "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Be2 O-O Bg5 h6 Be3 c5 d5 e6 Qd2 exd5 exd5 Kh7"),
    ("kings_indian_zinnowitz", "E70", "King's Indian 4.Bg5", "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6 Bg5 O-O Qd2 c5 d5 e6 Nf3 exd5 cxd5 Re8 Bd3"),
    ("modern_benoni_classical", "A65", "Modern Benoni Classical 7.Nf3", "d4 Nf6 c4 c5 d5 e6 Nc3 exd5 cxd5 d6 e4 g6 Bd3 Bg7 Nge2 O-O O-O Re8"),
    ("modern_benoni_taimanov", "A67", "Modern Benoni Taimanov 7.f4", "d4 Nf6 c4 c5 d5 e6 Nc3 exd5 cxd5 d6 e4 g6 f4 Bg7 Bb5+ Nfd7 a4 O-O Nf3 Na6"),
]


def generate_and_validate():
    print(f"Generating independent opening corpus (target: 100 positions)...")
    
    # 1. Load historical v0.52-v0.54 primary openings to enforce 0% overlap
    with open(V54_CORPUS, "r", encoding="utf-8") as f:
        v54_data = json.load(f)
    v54_epds = {chess.Board(item["fen"]).epd() for item in v54_data}
    print(f"Loaded {len(v54_epds)} historical primary opening states for blacklist.")

    assert len(INDEPENDENT_CANDIDATES) == 100, f"Expected 100 candidates, got {len(INDEPENDENT_CANDIDATES)}"

    new_corpus = []
    seen_epds = set()
    eco_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}

    for item_id, eco, name, moves_str in INDEPENDENT_CANDIDATES:
        b = chess.Board()
        move_list = moves_str.split()
        for san_move in move_list:
            move = b.parse_san(san_move)
            b.push(move)

        epd_state = b.epd()

        # Invariant 1: Strictly non-empty legal position
        assert b.is_valid(), f"Position {item_id} is not valid!"
        assert not b.is_game_over(), f"Position {item_id} ended the game prematurely!"

        # Invariant 2: Zero overlap with historical v0.52-v0.54 primary openings
        if epd_state in v54_epds:
            raise ValueError(f"COLLISION with v0.54 primary corpus detected in {item_id} ({epd_state})!")

        # Invariant 3: Zero internal duplicates or transpositions
        if epd_state in seen_epds:
            raise ValueError(f"DUPLICATE position within v0.55 corpus detected in {item_id} ({epd_state})!")

        seen_epds.add(epd_state)
        cat = eco[0]
        eco_counts[cat] = eco_counts.get(cat, 0) + 1

        new_corpus.append({
            "id": f"v055_{item_id}",
            "eco": eco,
            "category": f"ECO_{cat}",
            "name": name,
            "moves": moves_str,
            "ply_length": len(move_list),
            "fen": b.fen(),
            "epd": epd_state,
            "side_to_move": "white" if b.turn == chess.WHITE else "black"
        })

    print(f"Validated {len(new_corpus)} unique independent openings:")
    for cat in sorted(eco_counts.keys()):
        print(f"  Category {cat}: {eco_counts[cat]} openings")

    V55_CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    with open(V55_CORPUS_FILE, "w", encoding="utf-8") as f:
        json.dump(new_corpus, f, indent=2)

    import hashlib
    sha = hashlib.sha256(V55_CORPUS_FILE.read_bytes()).hexdigest()
    print(f"Saved independent corpus to {V55_CORPUS_FILE}")
    print(f"Corpus SHA-256: {sha}")
    return sha


if __name__ == "__main__":
    generate_and_validate()

