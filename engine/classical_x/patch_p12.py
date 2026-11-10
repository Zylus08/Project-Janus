#!/usr/bin/env python3
"""
Project Janus — Phase 1, Milestone P1.2 Engine Transformation Script
Applies Continuation History, Dynamic LMR, and Handcrafted Positional Evaluation to janus_classical_x.cpp.
"""

from pathlib import Path
import re

CPP_PATH = Path(r"E:\ChessXML\project-janus-phase1\engine\classical_x\janus_classical_x.cpp")

def patch_engine():
    with open(CPP_PATH, "r", encoding="utf-8") as f:
        src = f.read()

    print(f"Original source length: {len(src):,} bytes")

    # 1. Update Configuration section around line 200
    p11_config_target = """static int  g_aspiration_delta = 25;           // Aspiration delta
static std::string g_search_variant = "X6";    // Active variant identifier

// P1.1 Telemetry Counters"""

    p12_config_replacement = """static int  g_aspiration_delta = 25;           // Aspiration delta
static std::string g_search_variant = "X7";    // Active variant identifier (Default Candidate X7)

// ============================================================================
// Search Modernization & Positional Evaluation Options (Milestone P1.2)
// ============================================================================
static int g_conthist_mode = 3;       // 0=H0 (Off), 1=H1 (1-ply), 2=H2 (2-ply), 3=H3 (1-ply+2-ply)
static int g_dynamic_lmr_mode = 3;     // 0=L0 (Static base), 1=L1 (Log table), 2=L2 (Hist mod), 3=L3 (Conthist mod)
static int g_eval_mode = 5;            // 0=E0 (Base), 1=E1 (Pawn), 2=E2 (Mobility), 3=E3 (King), 4=E4 (Endgame), 5=E5 (Combined)

// Search stack for continuation history tracking
struct SearchStackEntry {
    uint16_t current_move;
    int piece;
};
static SearchStackEntry g_ss[MAX_SEARCH_PLY];

// Continuation History tables: [prev_piece 0..5][prev_to 0..63][curr_piece 0..5][curr_to 0..63]
static int16_t g_conthist_1ply[6][64][6][64];
static int16_t g_conthist_2ply[6][64][6][64];

// Dynamic Logarithmic LMR table: [depth][move_count]
static int g_lmr_table[MAX_SEARCH_PLY][MAX_MOVES];

// Precomputed passed pawn masks
static uint64_t white_passed_pawn_mask[64];
static uint64_t black_passed_pawn_mask[64];

// P1.2 Telemetry Counters
static uint64_t g_telemetry_conthist_probes = 0;
static uint64_t g_telemetry_conthist_cutoffs = 0;
static uint64_t g_telemetry_dynamic_lmr_reduced = 0;
static uint64_t g_telemetry_dynamic_lmr_researches = 0;
static uint64_t g_telemetry_eval_calls = 0;

// P1.1 Telemetry Counters"""

    assert p11_config_target in src, "Failed to find p11_config_target"
    src = src.replace(p11_config_target, p12_config_replacement)

    # 2. Update native_apply_search_variant
    variant_target = """    } else if (var == "X6") { // Full Integrated Candidate
        g_use_staged_movegen = true;
        g_quiescence_see_mode = 2;
        g_use_see_in_quiescence = true;
        g_use_null_move_pruning = true;
        g_use_reverse_futility = true;
        g_use_aspiration_window = true;
    }"""

    variant_replacement = """    } else if (var == "X6") { // P1.1 Integrated Baseline (Strict Bit-Exact Invariant)
        g_use_staged_movegen = true;
        g_quiescence_see_mode = 2;
        g_use_see_in_quiescence = true;
        g_use_null_move_pruning = true;
        g_use_reverse_futility = true;
        g_use_aspiration_window = true;
        g_conthist_mode = 0; // H0 Off
        g_dynamic_lmr_mode = 0; // L0 Static Base
        g_eval_mode = 0; // E0 Base Classical Eval
    } else if (var == "X7") { // P1.2 Integrated Candidate
        g_use_staged_movegen = true;
        g_quiescence_see_mode = 2;
        g_use_see_in_quiescence = true;
        g_use_null_move_pruning = true;
        g_use_reverse_futility = true;
        g_use_aspiration_window = true;
        g_conthist_mode = 3; // H3 1-ply + 2-ply
        g_dynamic_lmr_mode = 3; // L3 Dynamic Log + Conthist
        g_eval_mode = 5; // E5 Combined Positional Eval
    }"""

    assert variant_target in src, "Failed to find variant_target"
    src = src.replace(variant_target, variant_replacement)

    # 3. Update init_attacks to precompute passed pawn masks and initialize logarithmic LMR table
    init_attacks_target = """        // Black Pawn Attacks (moves down: -9, -7)
        uint64_t bp = 0;
        if (r > 0 && f > 0) bp |= (1ULL << ((r - 1) * 8 + f - 1));
        if (r > 0 && f < 7) bp |= (1ULL << ((r - 1) * 8 + f + 1));
        pawn_attacks[BLACK][sq] = bp;
    }"""

    init_attacks_replacement = """        // Black Pawn Attacks (moves down: -9, -7)
        uint64_t bp = 0;
        if (r > 0 && f > 0) bp |= (1ULL << ((r - 1) * 8 + f - 1));
        if (r > 0 && f < 7) bp |= (1ULL << ((r - 1) * 8 + f + 1));
        pawn_attacks[BLACK][sq] = bp;

        // Passed pawn masks (P1.2 Handcrafted Eval)
        uint64_t w_mask = 0;
        for (int rr = r + 1; rr <= 7; rr++) {
            for (int ff = std::max(0, f - 1); ff <= std::min(7, f + 1); ff++) {
                w_mask |= (1ULL << (rr * 8 + ff));
            }
        }
        white_passed_pawn_mask[sq] = w_mask;

        uint64_t b_mask = 0;
        for (int rr = 0; rr < r; rr++) {
            for (int ff = std::max(0, f - 1); ff <= std::min(7, f + 1); ff++) {
                b_mask |= (1ULL << (rr * 8 + ff));
            }
        }
        black_passed_pawn_mask[sq] = b_mask;
    }

    // Dynamic LMR logarithmic table initialization
    for (int d = 0; d < MAX_SEARCH_PLY; d++) {
        for (int m = 0; m < MAX_MOVES; m++) {
            if (d >= 1 && m >= 1) {
                double r_val = 0.75 + std::log((double)d) * std::log((double)m) / 2.25;
                g_lmr_table[d][m] = (int)r_val;
            } else {
                g_lmr_table[d][m] = 0;
            }
        }
    }"""

    assert init_attacks_target in src, "Failed to find init_attacks_target"
    src = src.replace(init_attacks_target, init_attacks_replacement)

    # 4. Replace native_evaluate with full modular positional evaluation
    eval_target_block = """EXPORT int native_evaluate(const NativeBoard* b) {
    int mg_score[2] = { 0, 0 };
    int eg_score[2] = { 0, 0 };
    int game_phase = 0;

    for (int c = 0; c < 2; c++) {
        // Pawns
        uint64_t pawns = b->pieces[c][PAWN];
        while (pawns) {
            int sq = bitscan_forward(pawns);
            pawns &= pawns - 1;
            int psq = (c == WHITE) ? mirror_sq(sq) : sq;
            mg_score[c] += MG_PIECE_VALUES[PAWN] + MG_PAWN_TABLE[psq];
            eg_score[c] += EG_PIECE_VALUES[PAWN] + MG_PAWN_TABLE[psq];
        }

        // Knights
        uint64_t knights = b->pieces[c][KNIGHT];
        while (knights) {
            int sq = bitscan_forward(knights);
            knights &= knights - 1;
            int psq = (c == WHITE) ? mirror_sq(sq) : sq;
            mg_score[c] += MG_PIECE_VALUES[KNIGHT] + MG_KNIGHT_TABLE[psq];
            eg_score[c] += EG_PIECE_VALUES[KNIGHT] + MG_KNIGHT_TABLE[psq];
            game_phase += 1;
        }

        // Bishops
        uint64_t bishops = b->pieces[c][BISHOP];
        while (bishops) {
            int sq = bitscan_forward(bishops);
            bishops &= bishops - 1;
            int psq = (c == WHITE) ? mirror_sq(sq) : sq;
            mg_score[c] += MG_PIECE_VALUES[BISHOP] + MG_BISHOP_TABLE[psq];
            eg_score[c] += EG_PIECE_VALUES[BISHOP] + MG_BISHOP_TABLE[psq];
            game_phase += 1;
        }

        // Rooks
        uint64_t rooks = b->pieces[c][ROOK];
        while (rooks) {
            int sq = bitscan_forward(rooks);
            rooks &= rooks - 1;
            int psq = (c == WHITE) ? mirror_sq(sq) : sq;
            mg_score[c] += MG_PIECE_VALUES[ROOK] + MG_ROOK_TABLE[psq];
            eg_score[c] += EG_PIECE_VALUES[ROOK] + MG_ROOK_TABLE[psq];
            game_phase += 2;
        }

        // Queens
        uint64_t queens = b->pieces[c][QUEEN];
        while (queens) {
            int sq = bitscan_forward(queens);
            queens &= queens - 1;
            int psq = (c == WHITE) ? mirror_sq(sq) : sq;
            mg_score[c] += MG_PIECE_VALUES[QUEEN] + MG_QUEEN_TABLE[psq];
            eg_score[c] += EG_PIECE_VALUES[QUEEN] + MG_QUEEN_TABLE[psq];
            game_phase += 4;
        }

        // King
        uint64_t king = b->pieces[c][KING];
        if (king) {
            int sq = bitscan_forward(king);
            int psq = (c == WHITE) ? mirror_sq(sq) : sq;
            mg_score[c] += MG_PIECE_VALUES[KING] + MG_KING_TABLE[psq];
            eg_score[c] += EG_PIECE_VALUES[KING] + MG_KING_TABLE[psq];
        }
    }

    if (game_phase > 24) game_phase = 24;
    int mg_diff = mg_score[WHITE] - mg_score[BLACK];
    int eg_diff = eg_score[WHITE] - eg_score[BLACK];

    int score = (mg_diff * game_phase + eg_diff * (24 - game_phase)) / 24;

    // Castling rights bonus (+15 cp per right)
    int castling_diff = 0;
    if (b->castling_rights & CASTLE_W_OO) castling_diff++;
    if (b->castling_rights & CASTLE_W_OOO) castling_diff++;
    if (b->castling_rights & CASTLE_B_OO) castling_diff--;
    if (b->castling_rights & CASTLE_B_OOO) castling_diff--;
    score += 15 * castling_diff;

    return (b->side_to_move == WHITE) ? score : -score;
}"""

    eval_replacement_block = """// ============================================================================
// Handcrafted Positional Evaluation Modules (Milestone P1.2)
// Strictly Non-ML Handcrafted Terms with Middle-Game and Endgame Tapering
// ============================================================================

constexpr uint64_t FILE_A_MASK = 0x0101010101010101ULL;
constexpr uint64_t FILE_MASKS[8] = {
    FILE_A_MASK, FILE_A_MASK << 1, FILE_A_MASK << 2, FILE_A_MASK << 3,
    FILE_A_MASK << 4, FILE_A_MASK << 5, FILE_A_MASK << 6, FILE_A_MASK << 7
};

constexpr uint64_t RANK_1_MASK = 0x00000000000000FFULL;
constexpr uint64_t RANK_MASKS[8] = {
    RANK_1_MASK, RANK_1_MASK << 8, RANK_1_MASK << 16, RANK_1_MASK << 24,
    RANK_1_MASK << 32, RANK_1_MASK << 40, RANK_1_MASK << 48, RANK_1_MASK << 56
};

inline uint64_t adjacent_files_mask(int f) {
    uint64_t m = 0;
    if (f > 0) m |= FILE_MASKS[f - 1];
    if (f < 7) m |= FILE_MASKS[f + 1];
    return m;
}

static const int PASSED_PAWN_BONUS_MG[8] = { 0, 5, 10, 20, 35, 60, 100, 0 };
static const int PASSED_PAWN_BONUS_EG[8] = { 0, 10, 20, 35, 60, 100, 150, 0 };

static void eval_pawn_structure(const NativeBoard* b, int mg[2], int eg[2]) {
    for (int c = 0; c < 2; c++) {
        uint64_t my_pawns = b->pieces[c][PAWN];
        uint64_t enemy_pawns = b->pieces[1 - c][PAWN];

        // 1. Passed Pawns
        uint64_t p = my_pawns;
        while (p) {
            int sq = bitscan_forward(p);
            p &= p - 1;
            int f = sq % 8;
            int r = (c == WHITE) ? (sq / 8) : (7 - (sq / 8));
            bool is_passed = (c == WHITE) ? ((enemy_pawns & white_passed_pawn_mask[sq]) == 0)
                                          : ((enemy_pawns & black_passed_pawn_mask[sq]) == 0);
            if (is_passed) {
                mg[c] += PASSED_PAWN_BONUS_MG[r];
                eg[c] += PASSED_PAWN_BONUS_EG[r];

                // Connected passer bonus: friendly pawn on adjacent file within +/- 1 rank
                uint64_t adj = my_pawns & adjacent_files_mask(f);
                int act_r = sq / 8;
                uint64_t near_ranks = RANK_MASKS[act_r] | (act_r > 0 ? RANK_MASKS[act_r - 1] : 0) | (act_r < 7 ? RANK_MASKS[act_r + 1] : 0);
                if (adj & near_ranks) {
                    mg[c] += 15;
                    eg[c] += 25;
                }

                // Supported passer bonus
                uint64_t defenders = (c == WHITE) ? pawn_attacks[BLACK][sq] : pawn_attacks[WHITE][sq];
                if (defenders & my_pawns) {
                    mg[c] += 10;
                    eg[c] += 20;
                }
            }
        }

        // 2. Isolated & Doubled Pawns
        for (int f = 0; f < 8; f++) {
            uint64_t f_pawns = my_pawns & FILE_MASKS[f];
            if (f_pawns) {
                // Isolated
                if ((my_pawns & adjacent_files_mask(f)) == 0) {
                    mg[c] -= 12;
                    eg[c] -= 20;
                }
                // Doubled
                int cnt = popcount64(f_pawns);
                if (cnt > 1) {
                    mg[c] -= 15 * (cnt - 1);
                    eg[c] -= 25 * (cnt - 1);
                }
            }
        }
    }
}

static void eval_mobility_and_coordination(const NativeBoard* b, int mg[2], int eg[2]) {
    for (int c = 0; c < 2; c++) {
        // Bishop pair
        if (popcount64(b->pieces[c][BISHOP]) >= 2) {
            mg[c] += 30;
            eg[c] += 50;
        }

        // Rooks on open & semi-open files, 7th rank
        uint64_t rooks = b->pieces[c][ROOK];
        int seventh = (c == WHITE) ? 6 : 1;
        while (rooks) {
            int sq = bitscan_forward(rooks);
            rooks &= rooks - 1;
            int f = sq % 8;
            int r = sq / 8;
            bool my_p = (b->pieces[c][PAWN] & FILE_MASKS[f]) != 0;
            bool en_p = (b->pieces[1 - c][PAWN] & FILE_MASKS[f]) != 0;
            if (!my_p && !en_p) {
                mg[c] += 20; eg[c] += 25;
            } else if (!my_p && en_p) {
                mg[c] += 10; eg[c] += 15;
            }
            if (r == seventh) {
                mg[c] += 20; eg[c] += 35;
            }
        }

        // Knight outposts
        uint64_t knights = b->pieces[c][KNIGHT];
        while (knights) {
            int sq = bitscan_forward(knights);
            knights &= knights - 1;
            int r = (c == WHITE) ? (sq / 8) : (7 - (sq / 8));
            if (r >= 3 && r <= 5) {
                uint64_t def = (c == WHITE) ? pawn_attacks[BLACK][sq] : pawn_attacks[WHITE][sq];
                if (def & b->pieces[c][PAWN]) {
                    mg[c] += 15; eg[c] += 10;
                }
            }
        }

        // Safe Mobility
        uint64_t enemy_pawn_attacks_bb = 0;
        uint64_t ep = b->pieces[1 - c][PAWN];
        while (ep) {
            int sq = bitscan_forward(ep);
            ep &= ep - 1;
            enemy_pawn_attacks_bb |= pawn_attacks[1 - c][sq];
        }
        uint64_t safe_mask = ~(b->occupancy[c] | enemy_pawn_attacks_bb);

        // Knights
        uint64_t kn = b->pieces[c][KNIGHT];
        while (kn) {
            int sq = bitscan_forward(kn);
            kn &= kn - 1;
            int mob = popcount64(knight_attacks[sq] & safe_mask);
            mg[c] += (mob - 4) * 4;
            eg[c] += (mob - 4) * 4;
        }
        // Bishops
        uint64_t bi = b->pieces[c][BISHOP];
        while (bi) {
            int sq = bitscan_forward(bi);
            bi &= bi - 1;
            int mob = popcount64(bishop_attacks_bb(sq, b->occupancy[2]) & safe_mask);
            mg[c] += (mob - 7) * 4;
            eg[c] += (mob - 7) * 4;
        }
        // Rooks
        uint64_t ro = b->pieces[c][ROOK];
        while (ro) {
            int sq = bitscan_forward(ro);
            ro &= ro - 1;
            int mob = popcount64(rook_attacks_bb(sq, b->occupancy[2]) & safe_mask);
            mg[c] += (mob - 7) * 2;
            eg[c] += (mob - 7) * 2;
        }
    }
}

static void eval_king_safety(const NativeBoard* b, int mg[2], int eg[2]) {
    for (int c = 0; c < 2; c++) {
        uint64_t kbb = b->pieces[c][KING];
        if (!kbb) continue;
        int ksq = bitscan_forward(kbb);
        int kf = ksq % 8;
        int kr = ksq / 8;

        // Pawn shield
        int shield_missing = 0;
        for (int f = std::max(0, kf - 1); f <= std::min(7, kf + 1); f++) {
            uint64_t f_pawns = b->pieces[c][PAWN] & FILE_MASKS[f];
            if (!f_pawns) {
                shield_missing++;
            } else {
                if (c == WHITE) {
                    int psq = bitscan_forward(f_pawns);
                    if (psq / 8 > kr + 2) shield_missing++;
                } else {
                    int psq = bitscan_reverse(f_pawns);
                    if (psq / 8 < kr - 2) shield_missing++;
                }
            }
        }
        mg[c] -= shield_missing * 15;

        // King ring enemy attackers
        uint64_t king_ring = king_attacks[ksq];
        int them = 1 - c;
        int attack_units = 0;
        int attackers = 0;

        uint64_t att_kn = b->pieces[them][KNIGHT];
        while (att_kn) {
            int sq = bitscan_forward(att_kn);
            att_kn &= att_kn - 1;
            if (knight_attacks[sq] & king_ring) { attack_units += 2; attackers++; }
        }
        uint64_t att_bi = b->pieces[them][BISHOP];
        while (att_bi) {
            int sq = bitscan_forward(att_bi);
            att_bi &= att_bi - 1;
            if (bishop_attacks_bb(sq, b->occupancy[2]) & king_ring) { attack_units += 2; attackers++; }
        }
        uint64_t att_ro = b->pieces[them][ROOK];
        while (att_ro) {
            int sq = bitscan_forward(att_ro);
            att_ro &= att_ro - 1;
            if (rook_attacks_bb(sq, b->occupancy[2]) & king_ring) { attack_units += 3; attackers++; }
        }
        uint64_t att_qu = b->pieces[them][QUEEN];
        while (att_qu) {
            int sq = bitscan_forward(att_qu);
            att_qu &= att_qu - 1;
            if (queen_attacks_bb(sq, b->occupancy[2]) & king_ring) { attack_units += 5; attackers++; }
        }
        if (attackers >= 2) {
            int danger = attack_units * attack_units;
            mg[c] -= std::min(200, danger * 2);
        }
    }
}

static void eval_endgame_positional(const NativeBoard* b, int mg[2], int eg[2]) {
    uint64_t kw = b->pieces[WHITE][KING];
    uint64_t kb = b->pieces[BLACK][KING];
    if (!kw || !kb) return;
    int w_ksq = bitscan_forward(kw);
    int b_ksq = bitscan_forward(kb);

    for (int c = 0; c < 2; c++) {
        int my_ksq = (c == WHITE) ? w_ksq : b_ksq;
        int en_ksq = (c == WHITE) ? b_ksq : w_ksq;
        int kr = my_ksq / 8;
        int kf = my_ksq % 8;
        int en_kr = en_ksq / 8;
        int en_kf = en_ksq % 8;

        // King centralization
        int center_dist = std::abs(2 * kr - 7) + std::abs(2 * kf - 7);
        eg[c] += (14 - center_dist) * 2;

        // Passed pawn escort
        uint64_t pawns = b->pieces[c][PAWN];
        uint64_t en_pawns = b->pieces[1 - c][PAWN];
        while (pawns) {
            int psq = bitscan_forward(pawns);
            pawns &= pawns - 1;
            bool is_passed = (c == WHITE) ? ((en_pawns & white_passed_pawn_mask[psq]) == 0)
                                          : ((en_pawns & black_passed_pawn_mask[psq]) == 0);
            if (is_passed) {
                int pr = psq / 8;
                int pf = psq % 8;
                int my_dist = std::max(std::abs(kr - pr), std::abs(kf - pf));
                int en_dist = std::max(std::abs(en_kr - pr), std::abs(en_kf - pf));
                eg[c] += (en_dist - my_dist) * 6;
            }
        }
    }
}

EXPORT int native_evaluate_internal(const NativeBoard* b, int emode) {
    g_telemetry_eval_calls++;
    int mg_score[2] = { 0, 0 };
    int eg_score[2] = { 0, 0 };
    int game_phase = 0;

    for (int c = 0; c < 2; c++) {
        // Pawns
        uint64_t pawns = b->pieces[c][PAWN];
        while (pawns) {
            int sq = bitscan_forward(pawns);
            pawns &= pawns - 1;
            int psq = (c == WHITE) ? mirror_sq(sq) : sq;
            mg_score[c] += MG_PIECE_VALUES[PAWN] + MG_PAWN_TABLE[psq];
            eg_score[c] += EG_PIECE_VALUES[PAWN] + MG_PAWN_TABLE[psq];
        }

        // Knights
        uint64_t knights = b->pieces[c][KNIGHT];
        while (knights) {
            int sq = bitscan_forward(knights);
            knights &= knights - 1;
            int psq = (c == WHITE) ? mirror_sq(sq) : sq;
            mg_score[c] += MG_PIECE_VALUES[KNIGHT] + MG_KNIGHT_TABLE[psq];
            eg_score[c] += EG_PIECE_VALUES[KNIGHT] + MG_KNIGHT_TABLE[psq];
            game_phase += 1;
        }

        // Bishops
        uint64_t bishops = b->pieces[c][BISHOP];
        while (bishops) {
            int sq = bitscan_forward(bishops);
            bishops &= bishops - 1;
            int psq = (c == WHITE) ? mirror_sq(sq) : sq;
            mg_score[c] += MG_PIECE_VALUES[BISHOP] + MG_BISHOP_TABLE[psq];
            eg_score[c] += EG_PIECE_VALUES[BISHOP] + MG_BISHOP_TABLE[psq];
            game_phase += 1;
        }

        // Rooks
        uint64_t rooks = b->pieces[c][ROOK];
        while (rooks) {
            int sq = bitscan_forward(rooks);
            rooks &= rooks - 1;
            int psq = (c == WHITE) ? mirror_sq(sq) : sq;
            mg_score[c] += MG_PIECE_VALUES[ROOK] + MG_ROOK_TABLE[psq];
            eg_score[c] += EG_PIECE_VALUES[ROOK] + MG_ROOK_TABLE[psq];
            game_phase += 2;
        }

        // Queens
        uint64_t queens = b->pieces[c][QUEEN];
        while (queens) {
            int sq = bitscan_forward(queens);
            queens &= queens - 1;
            int psq = (c == WHITE) ? mirror_sq(sq) : sq;
            mg_score[c] += MG_PIECE_VALUES[QUEEN] + MG_QUEEN_TABLE[psq];
            eg_score[c] += EG_PIECE_VALUES[QUEEN] + MG_QUEEN_TABLE[psq];
            game_phase += 4;
        }

        // King
        uint64_t king = b->pieces[c][KING];
        if (king) {
            int sq = bitscan_forward(king);
            int psq = (c == WHITE) ? mirror_sq(sq) : sq;
            mg_score[c] += MG_PIECE_VALUES[KING] + MG_KING_TABLE[psq];
            eg_score[c] += EG_PIECE_VALUES[KING] + MG_KING_TABLE[psq];
        }
    }

    // Positional evaluation terms based on active eval mode
    if (emode == 1) { // E1: Pawn Structure only
        eval_pawn_structure(b, mg_score, eg_score);
    } else if (emode == 2) { // E2: Mobility only
        eval_mobility_and_coordination(b, mg_score, eg_score);
    } else if (emode == 3) { // E3: King Safety only
        eval_king_safety(b, mg_score, eg_score);
    } else if (emode == 4) { // E4: Endgame only
        eval_endgame_positional(b, mg_score, eg_score);
    } else if (emode == 5) { // E5: Full combined positional evaluation
        eval_pawn_structure(b, mg_score, eg_score);
        eval_mobility_and_coordination(b, mg_score, eg_score);
        eval_king_safety(b, mg_score, eg_score);
        eval_endgame_positional(b, mg_score, eg_score);
    }

    if (game_phase > 24) game_phase = 24;
    int mg_diff = mg_score[WHITE] - mg_score[BLACK];
    int eg_diff = eg_score[WHITE] - eg_score[BLACK];

    int score = (mg_diff * game_phase + eg_diff * (24 - game_phase)) / 24;

    // Castling rights bonus (+15 cp per right)
    int castling_diff = 0;
    if (b->castling_rights & CASTLE_W_OO) castling_diff++;
    if (b->castling_rights & CASTLE_W_OOO) castling_diff++;
    if (b->castling_rights & CASTLE_B_OO) castling_diff--;
    if (b->castling_rights & CASTLE_B_OOO) castling_diff--;
    score += 15 * castling_diff;

    return (b->side_to_move == WHITE) ? score : -score;
}

EXPORT int native_evaluate(const NativeBoard* b) {
    return native_evaluate_internal(b, g_eval_mode);
}

EXPORT int native_evaluate_detail(const NativeBoard* b, int emode) {
    return native_evaluate_internal(b, emode);
}"""

    assert eval_target_block in src, "Failed to find eval_target_block"
    src = src.replace(eval_target_block, eval_replacement_block)

    # 5. Update score_move_for_ordering to use continuation history
    ordering_target = """    // History Heuristic (Quiet moves only)
    if (g_use_history_ordering) {
        int side = b->side_to_move;
        int h = g_history_table[side][from][to];
        if (h > 0) {
            return std::min(MAX_HISTORY_SCORE, h);
        }
    }

    return 0; // Quiet moves"""

    ordering_replacement = """    // History & Continuation History Heuristic (Quiet moves only)
    if (g_use_history_ordering) {
        int side = b->side_to_move;
        int h = g_history_table[side][from][to];
        if (g_conthist_mode == 0) {
            // Strict legacy X6 history scoring
            if (h > 0) {
                return std::min(MAX_HISTORY_SCORE, h);
            }
        } else {
            // Continuation history augmented scoring (P1.2)
            g_telemetry_conthist_probes++;
            int piece = NO_PIECE;
            for (int p = 0; p < 6; p++) {
                if (b->pieces[side][p] & (1ULL << from)) {
                    piece = p;
                    break;
                }
            }
            int score = h;
            if ((g_conthist_mode == 1 || g_conthist_mode == 3) && ply >= 1 && g_ss[ply - 1].current_move != 0) {
                int p1_piece = g_ss[ply - 1].piece;
                int p1_to = move_to(g_ss[ply - 1].current_move);
                if (p1_piece >= 0 && p1_piece < 6 && piece >= 0 && piece < 6) {
                    score += g_conthist_1ply[p1_piece][p1_to][piece][to];
                }
            }
            if ((g_conthist_mode == 2 || g_conthist_mode == 3) && ply >= 2 && g_ss[ply - 2].current_move != 0) {
                int p2_piece = g_ss[ply - 2].piece;
                int p2_to = move_to(g_ss[ply - 2].current_move);
                if (p2_piece >= 0 && p2_piece < 6 && piece >= 0 && piece < 6) {
                    score += g_conthist_2ply[p2_piece][p2_to][piece][to];
                }
            }
            return std::max(-20000, std::min(MAX_HISTORY_SCORE, score));
        }
    }

    return 0; // Quiet moves"""

    assert ordering_target in src, "Failed to find ordering_target"
    src = src.replace(ordering_target, ordering_replacement)

    # 6. Update negamax:
    # A) stack tracking before move execution and unmake
    # B) dynamic LMR calculation
    # C) quiet beta cutoff continuation history & gravity updates

    # Search stack tracking around make/unmake
    search_make_target = """        moves_searched++;

        // Push to game history stack for tree repetition detection
        native_push_history(b->zobrist_key);"""

    search_make_replacement = """        moves_searched++;

        // Track move in search stack for continuation history
        int move_from_sq = move_from(m);
        int moved_piece = NO_PIECE;
        for (int p = 0; p < 6; p++) {
            if (b->pieces[us_side][p] & (1ULL << move_from_sq)) {
                moved_piece = p;
                break;
            }
        }
        g_ss[ply].current_move = m;
        g_ss[ply].piece = moved_piece;

        // Push to game history stack for tree repetition detection
        native_push_history(b->zobrist_key);"""

    assert search_make_target in src, "Failed to find search_make_target"
    src = src.replace(search_make_target, search_make_replacement)

    search_unmake_target = """        native_pop_history();
        native_unmake_move(b, m, &undo);"""

    search_unmake_replacement = """        native_pop_history();
        native_unmake_move(b, m, &undo);
        g_ss[ply].current_move = 0;
        g_ss[ply].piece = NO_PIECE;"""

    assert search_unmake_target in src, "Failed to find search_unmake_target"
    src = src.replace(search_unmake_target, search_unmake_replacement)

    # Dynamic LMR calculation
    lmr_calc_target = """        // LMR Eligibility Check (10 Invariants)
        bool is_lmr_eligible = g_use_lmr &&
                               (ply > 0) &&
                               (depth >= g_lmr_min_depth) &&
                               (moves_searched >= g_lmr_move_threshold) &&
                               !in_check &&
                               (undo.captured_piece == NO_PIECE) &&
                               (move_flag(m) != 3) && // Non-promotion
                               (m != tt_move) &&
                               (native_is_check(b) == 0); // Non-checking move

        if (moves_searched == 1 || !g_use_pvs) {
            // PV Move (or PVS disabled): search with full window [-beta, -alpha]
            if (is_lmr_eligible) {
                // If PVS disabled but LMR enabled
                g_lmr_eligible_moves++;
                int reduction = g_lmr_base_reduction;
                int reduced_depth = std::max(1, child_depth - reduction);
                g_lmr_reduced_moves++;"""

    lmr_calc_replacement = """        // LMR Eligibility Check (10 Invariants)
        bool is_lmr_eligible = g_use_lmr &&
                               (ply > 0) &&
                               (depth >= g_lmr_min_depth) &&
                               (moves_searched >= g_lmr_move_threshold) &&
                               !in_check &&
                               (undo.captured_piece == NO_PIECE) &&
                               (move_flag(m) != 3) && // Non-promotion
                               (m != tt_move) &&
                               (native_is_check(b) == 0); // Non-checking move

        int dynamic_reduction = g_lmr_base_reduction;
        if (is_lmr_eligible) {
            if (g_dynamic_lmr_mode == 1) { // L1: Logarithmic table
                int d_idx = std::min(depth, MAX_SEARCH_PLY - 1);
                int m_idx = std::min(moves_searched, MAX_MOVES - 1);
                dynamic_reduction = g_lmr_table[d_idx][m_idx];
                if (dynamic_reduction < 1) dynamic_reduction = 1;
            } else if (g_dynamic_lmr_mode == 2) { // L2: History modulated
                int d_idx = std::min(depth, MAX_SEARCH_PLY - 1);
                int m_idx = std::min(moves_searched, MAX_MOVES - 1);
                dynamic_reduction = g_lmr_table[d_idx][m_idx];
                int h = g_history_table[us_side][move_from(m)][move_to(m)];
                if (h > 8000) dynamic_reduction -= 1;
                else if (h < -4000) dynamic_reduction += 1;
                if (dynamic_reduction < 1) dynamic_reduction = 1;
            } else if (g_dynamic_lmr_mode == 3) { // L3: Dynamic + Conthist modulated
                int d_idx = std::min(depth, MAX_SEARCH_PLY - 1);
                int m_idx = std::min(moves_searched, MAX_MOVES - 1);
                dynamic_reduction = g_lmr_table[d_idx][m_idx];
                int h = g_history_table[us_side][move_from(m)][move_to(m)];
                int ch1 = 0, ch2 = 0;
                int p_cur = moved_piece;
                if (p_cur >= 0 && p_cur < 6) {
                    if (ply >= 1 && g_ss[ply - 1].current_move != 0) {
                        int p1_piece = g_ss[ply - 1].piece;
                        int p1_to = move_to(g_ss[ply - 1].current_move);
                        if (p1_piece >= 0 && p1_piece < 6) ch1 = g_conthist_1ply[p1_piece][p1_to][p_cur][move_to(m)];
                    }
                    if (ply >= 2 && g_ss[ply - 2].current_move != 0) {
                        int p2_piece = g_ss[ply - 2].piece;
                        int p2_to = move_to(g_ss[ply - 2].current_move);
                        if (p2_piece >= 0 && p2_piece < 6) ch2 = g_conthist_2ply[p2_piece][p2_to][p_cur][move_to(m)];
                    }
                }
                int tot_h = h + ch1 + ch2;
                if (tot_h > 10000) dynamic_reduction -= 1;
                else if (tot_h < -5000) dynamic_reduction += 1;
                if (dynamic_reduction < 1) dynamic_reduction = 1;
            }
            if (child_depth - dynamic_reduction < 1) dynamic_reduction = child_depth - 1;
            if (dynamic_reduction <= 0) is_lmr_eligible = false;
        }

        if (moves_searched == 1 || !g_use_pvs) {
            // PV Move (or PVS disabled): search with full window [-beta, -alpha]
            if (is_lmr_eligible) {
                // If PVS disabled but LMR enabled
                g_lmr_eligible_moves++;
                int reduction = dynamic_reduction;
                int reduced_depth = std::max(1, child_depth - reduction);
                g_lmr_reduced_moves++;
                g_telemetry_dynamic_lmr_reduced++;"""

    assert lmr_calc_target in src, "Failed to find lmr_calc_target"
    src = src.replace(lmr_calc_target, lmr_calc_replacement)

    lmr_pvs_target = """            if (is_lmr_eligible) {
                g_lmr_eligible_moves++;
                int reduction = g_lmr_base_reduction;
                int reduced_depth = std::max(1, child_depth - reduction);
                g_lmr_reduced_moves++;"""

    lmr_pvs_replacement = """            if (is_lmr_eligible) {
                g_lmr_eligible_moves++;
                int reduction = dynamic_reduction;
                int reduced_depth = std::max(1, child_depth - reduction);
                g_lmr_reduced_moves++;
                g_telemetry_dynamic_lmr_reduced++;"""

    assert lmr_pvs_target in src, "Failed to find lmr_pvs_target"
    src = src.replace(lmr_pvs_target, lmr_pvs_replacement)

    # Beta cutoff update in negamax:
    cutoff_target = """                // History update
                if (g_use_history_ordering) {
                    int side = b->side_to_move;
                    int from = move_from(m);
                    int to = move_to(m);
                    if (g_history_table[side][from][to] > 0) {
                        g_ordering_cutoff_history++;
                    }
                    int bonus = depth * depth;
                    g_history_table[side][from][to] += bonus;
                    if (g_history_table[side][from][to] > MAX_HISTORY_SCORE) {
                        g_history_table[side][from][to] = MAX_HISTORY_SCORE;
                    }
                }"""

    cutoff_replacement = """                // History & Continuation History Update (P1.2)
                if (g_use_history_ordering) {
                    int side = b->side_to_move;
                    int from = move_from(m);
                    int to = move_to(m);
                    if (g_history_table[side][from][to] > 0) {
                        g_ordering_cutoff_history++;
                    }
                    if (g_conthist_mode == 0) {
                        // Strict legacy X6 history update
                        int bonus = depth * depth;
                        g_history_table[side][from][to] += bonus;
                        if (g_history_table[side][from][to] > MAX_HISTORY_SCORE) {
                            g_history_table[side][from][to] = MAX_HISTORY_SCORE;
                        }
                    } else {
                        // Gravity history update
                        g_telemetry_conthist_cutoffs++;
                        int bonus = std::min(300, depth * depth);
                        int cur_h = g_history_table[side][from][to];
                        g_history_table[side][from][to] = cur_h + bonus - (cur_h * std::abs(bonus)) / 16384;

                        // Continuation history updates
                        int p_cur = moved_piece;
                        if (p_cur >= 0 && p_cur < 6) {
                            if ((g_conthist_mode == 1 || g_conthist_mode == 3) && ply >= 1 && g_ss[ply - 1].current_move != 0) {
                                int p1_piece = g_ss[ply - 1].piece;
                                int p1_to = move_to(g_ss[ply - 1].current_move);
                                if (p1_piece >= 0 && p1_piece < 6) {
                                    int cur1 = g_conthist_1ply[p1_piece][p1_to][p_cur][to];
                                    g_conthist_1ply[p1_piece][p1_to][p_cur][to] = (int16_t)(cur1 + bonus - (cur1 * std::abs(bonus)) / 16384);
                                }
                            }
                            if ((g_conthist_mode == 2 || g_conthist_mode == 3) && ply >= 2 && g_ss[ply - 2].current_move != 0) {
                                int p2_piece = g_ss[ply - 2].piece;
                                int p2_to = move_to(g_ss[ply - 2].current_move);
                                if (p2_piece >= 0 && p2_piece < 6) {
                                    int cur2 = g_conthist_2ply[p2_piece][p2_to][p_cur][to];
                                    g_conthist_2ply[p2_piece][p2_to][p_cur][to] = (int16_t)(cur2 + bonus - (cur2 * std::abs(bonus)) / 16384);
                                }
                            }
                        }
                    }
                }"""

    assert cutoff_target in src, "Failed to find cutoff_target"
    src = src.replace(cutoff_target, cutoff_replacement)

    # 7. Update native_search to clear/age continuation history and reset search stack
    native_search_target = """    init_attacks();
    std::memset(g_killer_moves, 0, sizeof(g_killer_moves));
    if (g_use_history_ordering) {
        for (int s = 0; s < SIDES; s++) {
            for (int f = 0; f < SQUARES; f++) {
                for (int t = 0; t < SQUARES; t++) {
                    g_history_table[s][f][t] /= 2;
                }
            }
        }
    }"""

    native_search_replacement = """    init_attacks();
    std::memset(g_killer_moves, 0, sizeof(g_killer_moves));
    std::memset(g_ss, 0, sizeof(g_ss));
    if (g_use_history_ordering) {
        for (int s = 0; s < SIDES; s++) {
            for (int f = 0; f < SQUARES; f++) {
                for (int t = 0; t < SQUARES; t++) {
                    g_history_table[s][f][t] /= 2;
                }
            }
        }
        if (g_conthist_mode > 0) {
            for (int p1 = 0; p1 < 6; p1++) {
                for (int s1 = 0; s1 < 64; s1++) {
                    for (int p2 = 0; p2 < 6; p2++) {
                        for (int s2 = 0; s2 < 64; s2++) {
                            g_conthist_1ply[p1][s1][p2][s2] /= 2;
                            g_conthist_2ply[p1][s1][p2][s2] /= 2;
                        }
                    }
                }
            }
        }
    }"""

    assert native_search_target in src, "Failed to find native_search_target"
    src = src.replace(native_search_target, native_search_replacement)

    # 8. Add P1.2 Exports
    export_target = """EXPORT void native_get_see_telemetry(uint64_t* out_arr) {
    if (out_arr) {
        out_arr[0] = g_see_total_evaluations;
        out_arr[1] = g_see_positive_captures;
        out_arr[2] = g_see_neutral_captures;
        out_arr[3] = g_see_negative_captures;
        out_arr[4] = g_see_ordering_inversions;
    }
}"""

    export_replacement = """EXPORT void native_get_see_telemetry(uint64_t* out_arr) {
    if (out_arr) {
        out_arr[0] = g_see_total_evaluations;
        out_arr[1] = g_see_positive_captures;
        out_arr[2] = g_see_neutral_captures;
        out_arr[3] = g_see_negative_captures;
        out_arr[4] = g_see_ordering_inversions;
    }
}

// ============================================================================
// Milestone P1.2 Control & Telemetry Exports
// ============================================================================
EXPORT void native_set_conthist_mode(int mode) { g_conthist_mode = mode; }
EXPORT void native_set_dynamic_lmr_mode(int mode) { g_dynamic_lmr_mode = mode; }
EXPORT void native_set_eval_mode(int mode) { g_eval_mode = mode; }
EXPORT void native_clear_conthist() {
    std::memset(g_conthist_1ply, 0, sizeof(g_conthist_1ply));
    std::memset(g_conthist_2ply, 0, sizeof(g_conthist_2ply));
}
EXPORT void native_reset_p12_telemetry() {
    native_reset_p11_telemetry();
    g_telemetry_conthist_probes = 0;
    g_telemetry_conthist_cutoffs = 0;
    g_telemetry_dynamic_lmr_reduced = 0;
    g_telemetry_dynamic_lmr_researches = 0;
    g_telemetry_eval_calls = 0;
}
EXPORT void native_get_p12_telemetry(uint64_t* out_arr) {
    if (out_arr) {
        out_arr[0] = g_telemetry_conthist_probes;
        out_arr[1] = g_telemetry_conthist_cutoffs;
        out_arr[2] = g_telemetry_dynamic_lmr_reduced;
        out_arr[3] = g_telemetry_dynamic_lmr_researches;
        out_arr[4] = g_telemetry_eval_calls;
    }
}"""

    assert export_target in src, "Failed to find export_target"
    src = src.replace(export_target, export_replacement)

    # 9. Update UCI loop options and telemetry
    uci_id_target = '            std::cout << "id name Janus Classical X (P1.0 Development)" << std::endl;'
    uci_id_replacement = '            std::cout << "id name Janus Classical X (P1.2 Candidate X7)" << std::endl;'
    assert uci_id_target in src, "Failed to find uci_id_target"
    src = src.replace(uci_id_target, uci_id_replacement)

    uci_opts_target = """            std::cout << "option name UCI_Variant type combo default X6 var X0 var X1 var X2 var X3 var X4 var X5 var X6" << std::endl;
            std::cout << "option name UCI_StagedMovegen type check default true" << std::endl;
            std::cout << "option name UCI_QuiescenceSEE type spin default 2 min 0 max 3" << std::endl;
            std::cout << "option name UCI_NullMovePruning type check default true" << std::endl;
            std::cout << "option name UCI_RFP type check default true" << std::endl;
            std::cout << "option name UCI_AspirationWindow type check default true" << std::endl;"""

    uci_opts_replacement = """            std::cout << "option name UCI_Variant type combo default X7 var X0 var X1 var X2 var X3 var X4 var X5 var X6 var X7" << std::endl;
            std::cout << "option name UCI_ContinuationHistory type combo default H3 var H0 var H1 var H2 var H3" << std::endl;
            std::cout << "option name UCI_DynamicLMR type combo default L3 var L0 var L1 var L2 var L3" << std::endl;
            std::cout << "option name UCI_ClassicalEval type combo default E5 var E0 var E1 var E2 var E3 var E4 var E5" << std::endl;
            std::cout << "option name UCI_StagedMovegen type check default true" << std::endl;
            std::cout << "option name UCI_QuiescenceSEE type spin default 2 min 0 max 3" << std::endl;
            std::cout << "option name UCI_NullMovePruning type check default true" << std::endl;
            std::cout << "option name UCI_RFP type check default true" << std::endl;
            std::cout << "option name UCI_AspirationWindow type check default true" << std::endl;"""

    assert uci_opts_target in src, "Failed to find uci_opts_target"
    src = src.replace(uci_opts_target, uci_opts_replacement)

    setoption_target = """                } else if (opt_name == "UCI_AspirationWindow") {
                    g_use_aspiration_window = (opt_val.empty() || opt_val == "true" || opt_val == "1");
                }"""

    setoption_replacement = """                } else if (opt_name == "UCI_AspirationWindow") {
                    g_use_aspiration_window = (opt_val.empty() || opt_val == "true" || opt_val == "1");
                } else if (opt_name == "UCI_ContinuationHistory" && !opt_val.empty()) {
                    if (opt_val == "H0") g_conthist_mode = 0;
                    else if (opt_val == "H1") g_conthist_mode = 1;
                    else if (opt_val == "H2") g_conthist_mode = 2;
                    else if (opt_val == "H3") g_conthist_mode = 3;
                } else if (opt_name == "UCI_DynamicLMR" && !opt_val.empty()) {
                    if (opt_val == "L0") g_dynamic_lmr_mode = 0;
                    else if (opt_val == "L1") g_dynamic_lmr_mode = 1;
                    else if (opt_val == "L2") g_dynamic_lmr_mode = 2;
                    else if (opt_val == "L3") g_dynamic_lmr_mode = 3;
                } else if (opt_name == "UCI_ClassicalEval" && !opt_val.empty()) {
                    if (opt_val == "E0") g_eval_mode = 0;
                    else if (opt_val == "E1") g_eval_mode = 1;
                    else if (opt_val == "E2") g_eval_mode = 2;
                    else if (opt_val == "E3") g_eval_mode = 3;
                    else if (opt_val == "E4") g_eval_mode = 4;
                    else if (opt_val == "E5") g_eval_mode = 5;
                }"""

    assert setoption_target in src, "Failed to find setoption_target"
    src = src.replace(setoption_target, setoption_replacement)

    telemetry_rep_target = """            std::cout << "qmoves_pruned " << g_telemetry_qmoves_pruned << std::endl;
            std::cout << "TELEMETRY_END" << std::endl;"""

    telemetry_rep_replacement = """            std::cout << "qmoves_pruned " << g_telemetry_qmoves_pruned << std::endl;
            std::cout << "conthist_mode " << g_conthist_mode << std::endl;
            std::cout << "dynamic_lmr_mode " << g_dynamic_lmr_mode << std::endl;
            std::cout << "eval_mode " << g_eval_mode << std::endl;
            std::cout << "conthist_probes " << g_telemetry_conthist_probes << std::endl;
            std::cout << "conthist_cutoffs " << g_telemetry_conthist_cutoffs << std::endl;
            std::cout << "dynamic_lmr_reduced " << g_telemetry_dynamic_lmr_reduced << std::endl;
            std::cout << "eval_calls " << g_telemetry_eval_calls << std::endl;
            std::cout << "TELEMETRY_END" << std::endl;"""

    assert telemetry_rep_target in src, "Failed to find telemetry_rep_target"
    src = src.replace(telemetry_rep_target, telemetry_rep_replacement)

    ucinewgame_target = """        } else if (cmd == "ucinewgame") {
            native_reset_history();"""

    ucinewgame_replacement = """        } else if (cmd == "ucinewgame") {
            native_reset_history();
            native_clear_conthist();"""

    assert ucinewgame_target in src, "Failed to find ucinewgame_target"
    src = src.replace(ucinewgame_target, ucinewgame_replacement)

    # Write patched source
    with open(CPP_PATH, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"Successfully patched {CPP_PATH} ({len(src):,} bytes).")

if __name__ == "__main__":
    patch_engine()

