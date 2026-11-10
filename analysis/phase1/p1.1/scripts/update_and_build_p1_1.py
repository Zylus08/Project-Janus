#!/usr/bin/env python3
"""
Project Janus — Phase 1 Milestone P1.1
Script to implement P1.1 Search Modernizations in Janus Classical X.

Features:
  1. Staged Move Generation (native_generate_captures, native_generate_quiets, MovePicker)
  2. Quiescence SEE Filtering (Q0=off, Q1=ordering, Q2=prune SEE<0, Q3=prune SEE<-50)
  3. Null-Move Pruning (NMP, R=3, zugzwang/non-pawn protection)
  4. Reverse Futility Pruning (RFP, d<=3, margin=80*d)
  5. Aspiration Windows (delta=25 cp with widening on fail-low/high)
  6. Variant switching: X0, X1, X2, X3, X4, X5, X6
"""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC_CPP = ROOT / "engine" / "classical_x" / "janus_classical_x.cpp"
TARGET_DIR = ROOT / "engine" / "classical_x"
VCVARS = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

def main():
    with open(SRC_CPP, "r", encoding="utf-8") as f:
        code = f.read()

    print(f"Read existing janus_classical_x.cpp ({len(code):,} bytes).")

    # 1. Add P1.1 Search Options and Telemetry Flags AFTER g_see_ordering_inversions declaration
    options_decl = """
// ============================================================================
// Search Modernization Configuration Options (Milestone P1.1)
// ============================================================================
static bool g_use_staged_movegen = true;       // Phase 1: Staged move generation / MovePicker
static int  g_quiescence_see_mode = 2;         // Phase 2: 0=Q0 (Off), 1=Q1 (Ordering only), 2=Q2 (Prune SEE < 0), 3=Q3 (Prune SEE < -50)
static bool g_use_null_move_pruning = true;    // Phase 3: Null-Move Pruning (R=3, zugzwang protection)
static int  g_nmp_reduction = 3;               // Base NMP reduction R=3
static bool g_use_reverse_futility = true;     // Phase 4: Reverse Futility Pruning (d <= 3, margin = 80 * d)
static int  g_rfp_margin_per_depth = 80;       // Margin per ply
static bool g_use_aspiration_window = true;    // Phase 5: Aspiration Windows (delta = 25 cp)
static int  g_aspiration_delta = 25;           // Aspiration delta
static std::string g_search_variant = "X6";    // Active variant identifier

// P1.1 Telemetry Counters
static uint64_t g_telemetry_movegen_calls = 0;
static uint64_t g_telemetry_captures_gen = 0;
static uint64_t g_telemetry_quiets_gen = 0;
static uint64_t g_telemetry_moves_scored = 0;
static uint64_t g_telemetry_moves_searched = 0;
static uint64_t g_telemetry_first_move_cutoffs = 0;
static uint64_t g_telemetry_total_cutoffs = 0;
static uint64_t g_telemetry_nmp_probes = 0;
static uint64_t g_telemetry_nmp_cutoffs = 0;
static uint64_t g_telemetry_rfp_probes = 0;
static uint64_t g_telemetry_rfp_cutoffs = 0;
static uint64_t g_telemetry_aspiration_researches = 0;
static uint64_t g_telemetry_qmoves_pruned = 0;

EXPORT void native_apply_search_variant(const char* var_str) {
    if (!var_str) return;
    std::string var(var_str);
    g_search_variant = var;
    if (var == "X0") { // C1 Frozen Baseline Equivalent
        g_use_staged_movegen = false;
        g_quiescence_see_mode = 0;
        g_use_see_in_quiescence = false;
        g_use_null_move_pruning = false;
        g_use_reverse_futility = false;
        g_use_aspiration_window = false;
    } else if (var == "X1") { // Staged Movegen Only
        g_use_staged_movegen = true;
        g_quiescence_see_mode = 0;
        g_use_see_in_quiescence = false;
        g_use_null_move_pruning = false;
        g_use_reverse_futility = false;
        g_use_aspiration_window = false;
    } else if (var == "X2") { // Quiescence SEE Only
        g_use_staged_movegen = false;
        g_quiescence_see_mode = 2;
        g_use_see_in_quiescence = true;
        g_use_null_move_pruning = false;
        g_use_reverse_futility = false;
        g_use_aspiration_window = false;
    } else if (var == "X3") { // NMP Only
        g_use_staged_movegen = false;
        g_quiescence_see_mode = 0;
        g_use_see_in_quiescence = false;
        g_use_null_move_pruning = true;
        g_use_reverse_futility = false;
        g_use_aspiration_window = false;
    } else if (var == "X4") { // RFP Only
        g_use_staged_movegen = false;
        g_quiescence_see_mode = 0;
        g_use_see_in_quiescence = false;
        g_use_null_move_pruning = false;
        g_use_reverse_futility = true;
        g_use_aspiration_window = false;
    } else if (var == "X5") { // Aspiration Windows Only
        g_use_staged_movegen = false;
        g_quiescence_see_mode = 0;
        g_use_see_in_quiescence = false;
        g_use_null_move_pruning = false;
        g_use_reverse_futility = false;
        g_use_aspiration_window = true;
    } else if (var == "X6") { // Full Integrated Candidate
        g_use_staged_movegen = true;
        g_quiescence_see_mode = 2;
        g_use_see_in_quiescence = true;
        g_use_null_move_pruning = true;
        g_use_reverse_futility = true;
        g_use_aspiration_window = true;
    }
}

EXPORT void native_reset_p11_telemetry() {
    g_telemetry_movegen_calls = 0;
    g_telemetry_captures_gen = 0;
    g_telemetry_quiets_gen = 0;
    g_telemetry_moves_scored = 0;
    g_telemetry_moves_searched = 0;
    g_telemetry_first_move_cutoffs = 0;
    g_telemetry_total_cutoffs = 0;
    g_telemetry_nmp_probes = 0;
    g_telemetry_nmp_cutoffs = 0;
    g_telemetry_rfp_probes = 0;
    g_telemetry_rfp_cutoffs = 0;
    g_telemetry_aspiration_researches = 0;
    g_telemetry_qmoves_pruned = 0;
}
"""
    anchor_flag = "static uint64_t g_see_ordering_inversions = 0;"
    assert anchor_flag in code, "anchor_flag not found in janus_classical_x.cpp"
    code = code.replace(anchor_flag, anchor_flag + "\n" + options_decl, 1)

    # 2. Add native_generate_captures, native_generate_quiets, is_pseudo_legal_move, is_legal_move, and MovePicker
    staged_helpers = """
// ============================================================================
// Specialized Capture & Promotion Generation (Phase 1 / Phase 2)
// ============================================================================
EXPORT int native_generate_captures(NativeBoard* b, uint16_t* out_moves) {
    g_telemetry_movegen_calls++;
    uint16_t pseudo_moves[MAX_MOVES];
    int p_count = 0;

    int us = b->side_to_move;
    int them = 1 - us;
    uint64_t occ = b->occupancy[2];
    uint64_t enemies = b->occupancy[them];

    // 1. Pawn Captures & Promotions
    uint64_t pawns = b->pieces[us][PAWN];
    int forward = (us == WHITE) ? 8 : -8;
    int promo_rank = (us == WHITE) ? 7 : 0;

    while (pawns) {
        int sq = bitscan_forward(pawns);
        pawns &= pawns - 1;

        // Push promotion
        int to = sq + forward;
        if (to >= 0 && to < 64 && !(occ & (1ULL << to))) {
            if (to / 8 == promo_rank) {
                for (int pr = 0; pr < 4; pr++) pseudo_moves[p_count++] = encode_move(sq, to, 3, pr);
            }
        }

        // Capture promotions & normal captures
        uint64_t att = pawn_attacks[us][sq];
        uint64_t caps = att & enemies;
        while (caps) {
            int cap_to = bitscan_forward(caps);
            caps &= caps - 1;
            if (cap_to / 8 == promo_rank) {
                for (int pr = 0; pr < 4; pr++) pseudo_moves[p_count++] = encode_move(sq, cap_to, 3, pr);
            } else {
                pseudo_moves[p_count++] = encode_move(sq, cap_to, 0);
            }
        }

        // En Passant
        if (b->ep_square <= 63 && (att & (1ULL << b->ep_square))) {
            pseudo_moves[p_count++] = encode_move(sq, b->ep_square, 2);
        }
    }

    // 2. Knights
    uint64_t knights = b->pieces[us][KNIGHT];
    while (knights) {
        int sq = bitscan_forward(knights);
        knights &= knights - 1;
        uint64_t att = knight_attacks[sq] & enemies;
        while (att) {
            int to = bitscan_forward(att);
            att &= att - 1;
            pseudo_moves[p_count++] = encode_move(sq, to);
        }
    }

    // 3. Bishops / Queens diagonal
    uint64_t diags = b->pieces[us][BISHOP] | b->pieces[us][QUEEN];
    while (diags) {
        int sq = bitscan_forward(diags);
        diags &= diags - 1;
        uint64_t att = bishop_attacks_bb(sq, occ) & enemies;
        while (att) {
            int to = bitscan_forward(att);
            att &= att - 1;
            pseudo_moves[p_count++] = encode_move(sq, to);
        }
    }

    // 4. Rooks / Queens straight
    uint64_t straights = b->pieces[us][ROOK] | b->pieces[us][QUEEN];
    while (straights) {
        int sq = bitscan_forward(straights);
        straights &= straights - 1;
        uint64_t att = rook_attacks_bb(sq, occ) & enemies;
        while (att) {
            int to = bitscan_forward(att);
            att &= att - 1;
            pseudo_moves[p_count++] = encode_move(sq, to);
        }
    }

    // 5. King
    int k_sq = bitscan_forward(b->pieces[us][KING]);
    uint64_t k_att = king_attacks[k_sq] & enemies;
    while (k_att) {
        int to = bitscan_forward(k_att);
        k_att &= k_att - 1;
        pseudo_moves[p_count++] = encode_move(k_sq, to);
    }

    // Legality filter
    int legal_count = 0;
    UndoInfo undo;
    for (int i = 0; i < p_count; i++) {
        uint16_t m = pseudo_moves[i];
        if (!native_make_move(b, m, &undo)) continue;

        int king_sq = bitscan_forward(b->pieces[us][KING]);
        bool in_check = is_square_attacked(b, king_sq, them);
        native_unmake_move(b, m, &undo);

        if (!in_check) {
            out_moves[legal_count++] = m;
        }
    }

    g_telemetry_captures_gen += legal_count;
    return legal_count;
}

// ============================================================================
// Specialized Quiet Move Generation (Phase 1)
// ============================================================================
EXPORT int native_generate_quiets(NativeBoard* b, uint16_t* out_moves) {
    g_telemetry_movegen_calls++;
    uint16_t pseudo_moves[MAX_MOVES];
    int p_count = 0;

    int us = b->side_to_move;
    int them = 1 - us;
    uint64_t occ = b->occupancy[2];
    uint64_t empty = ~occ;

    // 1. Pawn Moves (non-promotions, non-captures)
    uint64_t pawns = b->pieces[us][PAWN];
    int forward = (us == WHITE) ? 8 : -8;
    int start_rank = (us == WHITE) ? 1 : 6;
    int promo_rank = (us == WHITE) ? 7 : 0;

    while (pawns) {
        int sq = bitscan_forward(pawns);
        pawns &= pawns - 1;
        int r = sq / 8;

        // Single push
        int to = sq + forward;
        if (to >= 0 && to < 64 && !(occ & (1ULL << to))) {
            if (to / 8 != promo_rank) {
                pseudo_moves[p_count++] = encode_move(sq, to, 0);
                // Double push
                if (r == start_rank) {
                    int to2 = to + forward;
                    if (!(occ & (1ULL << to2))) {
                        pseudo_moves[p_count++] = encode_move(sq, to2, 0);
                    }
                }
            }
        }
    }

    // 2. Knights (empty squares)
    uint64_t knights = b->pieces[us][KNIGHT];
    while (knights) {
        int sq = bitscan_forward(knights);
        knights &= knights - 1;
        uint64_t att = knight_attacks[sq] & empty;
        while (att) {
            int to = bitscan_forward(att);
            att &= att - 1;
            pseudo_moves[p_count++] = encode_move(sq, to);
        }
    }

    // 3. Bishops / Queens diagonal (empty squares)
    uint64_t diags = b->pieces[us][BISHOP] | b->pieces[us][QUEEN];
    while (diags) {
        int sq = bitscan_forward(diags);
        diags &= diags - 1;
        uint64_t att = bishop_attacks_bb(sq, occ) & empty;
        while (att) {
            int to = bitscan_forward(att);
            att &= att - 1;
            pseudo_moves[p_count++] = encode_move(sq, to);
        }
    }

    // 4. Rooks / Queens straight (empty squares)
    uint64_t straights = b->pieces[us][ROOK] | b->pieces[us][QUEEN];
    while (straights) {
        int sq = bitscan_forward(straights);
        straights &= straights - 1;
        uint64_t att = rook_attacks_bb(sq, occ) & empty;
        while (att) {
            int to = bitscan_forward(att);
            att &= att - 1;
            pseudo_moves[p_count++] = encode_move(sq, to);
        }
    }

    // 5. King (empty squares)
    int k_sq = bitscan_forward(b->pieces[us][KING]);
    uint64_t k_att = king_attacks[k_sq] & empty;
    while (k_att) {
        int to = bitscan_forward(k_att);
        k_att &= k_att - 1;
        pseudo_moves[p_count++] = encode_move(k_sq, to);
    }

    // 6. Castling
    if (us == WHITE) {
        if ((b->castling_rights & CASTLE_W_OO) && !(occ & (1ULL << 5)) && !(occ & (1ULL << 6))) {
            if (!is_square_attacked(b, 4, BLACK) && !is_square_attacked(b, 5, BLACK) && !is_square_attacked(b, 6, BLACK)) {
                pseudo_moves[p_count++] = encode_move(4, 6, 1);
            }
        }
        if ((b->castling_rights & CASTLE_W_OOO) && !(occ & (1ULL << 1)) && !(occ & (1ULL << 2)) && !(occ & (1ULL << 3))) {
            if (!is_square_attacked(b, 4, BLACK) && !is_square_attacked(b, 3, BLACK) && !is_square_attacked(b, 2, BLACK)) {
                pseudo_moves[p_count++] = encode_move(4, 2, 1);
            }
        }
    } else {
        if ((b->castling_rights & CASTLE_B_OO) && !(occ & (1ULL << 61)) && !(occ & (1ULL << 62))) {
            if (!is_square_attacked(b, 60, WHITE) && !is_square_attacked(b, 61, WHITE) && !is_square_attacked(b, 62, WHITE)) {
                pseudo_moves[p_count++] = encode_move(60, 62, 1);
            }
        }
        if ((b->castling_rights & CASTLE_B_OOO) && !(occ & (1ULL << 57)) && !(occ & (1ULL << 58)) && !(occ & (1ULL << 59))) {
            if (!is_square_attacked(b, 60, WHITE) && !is_square_attacked(b, 59, WHITE) && !is_square_attacked(b, 58, WHITE)) {
                pseudo_moves[p_count++] = encode_move(60, 58, 1);
            }
        }
    }

    // Legality filter
    int legal_count = 0;
    UndoInfo undo;
    for (int i = 0; i < p_count; i++) {
        uint16_t m = pseudo_moves[i];
        if (!native_make_move(b, m, &undo)) continue;

        int king_sq = bitscan_forward(b->pieces[us][KING]);
        bool in_check = is_square_attacked(b, king_sq, them);
        native_unmake_move(b, m, &undo);

        if (!in_check) {
            out_moves[legal_count++] = m;
        }
    }

    g_telemetry_quiets_gen += legal_count;
    return legal_count;
}

// Helper: check if arbitrary encoded move is pseudo-legal
static bool is_pseudo_legal_move(const NativeBoard* b, uint16_t m) {
    if (m == 0) return false;
    int from = move_from(m);
    int to = move_to(m);
    int flag = move_flag(m);
    int us = b->side_to_move;
    int them = 1 - us;
    uint64_t occ = b->occupancy[2];

    int piece = NO_PIECE;
    for (int p = 0; p < 6; p++) {
        if (b->pieces[us][p] & (1ULL << from)) {
            piece = p;
            break;
        }
    }
    if (piece == NO_PIECE) return false;

    if (flag == 1) { // Castling
        if (piece != KING) return false;
        if (us == WHITE) {
            if (from == 4 && to == 6) {
                return (b->castling_rights & CASTLE_W_OO) && !(occ & (1ULL << 5)) && !(occ & (1ULL << 6)) &&
                       !is_square_attacked(b, 4, BLACK) && !is_square_attacked(b, 5, BLACK) && !is_square_attacked(b, 6, BLACK);
            }
            if (from == 4 && to == 2) {
                return (b->castling_rights & CASTLE_W_OOO) && !(occ & (1ULL << 1)) && !(occ & (1ULL << 2)) && !(occ & (1ULL << 3)) &&
                       !is_square_attacked(b, 4, BLACK) && !is_square_attacked(b, 3, BLACK) && !is_square_attacked(b, 2, BLACK);
            }
        } else {
            if (from == 60 && to == 62) {
                return (b->castling_rights & CASTLE_B_OO) && !(occ & (1ULL << 61)) && !(occ & (1ULL << 62)) &&
                       !is_square_attacked(b, 60, WHITE) && !is_square_attacked(b, 61, WHITE) && !is_square_attacked(b, 62, WHITE);
            }
            if (from == 60 && to == 58) {
                return (b->castling_rights & CASTLE_B_OOO) && !(occ & (1ULL << 57)) && !(occ & (1ULL << 58)) && !(occ & (1ULL << 59)) &&
                       !is_square_attacked(b, 60, WHITE) && !is_square_attacked(b, 59, WHITE) && !is_square_attacked(b, 58, WHITE);
            }
        }
        return false;
    }

    if (b->occupancy[us] & (1ULL << to)) return false;

    if (piece == PAWN) {
        int forward = (us == WHITE) ? 8 : -8;
        int start_rank = (us == WHITE) ? 1 : 6;
        int promo_rank = (us == WHITE) ? 7 : 0;
        int r = from / 8;

        if (flag == 2) { // En passant
            return (b->ep_square == to && (pawn_attacks[us][from] & (1ULL << to)));
        }

        if (to == from + forward) {
            if (occ & (1ULL << to)) return false;
            if (to / 8 == promo_rank) return flag == 3;
            return flag == 0;
        }
        if (r == start_rank && to == from + 2 * forward) {
            return !(occ & (1ULL << (from + forward))) && !(occ & (1ULL << to)) && flag == 0;
        }
        if (pawn_attacks[us][from] & (1ULL << to)) {
            if (!(b->occupancy[them] & (1ULL << to))) return false;
            if (to / 8 == promo_rank) return flag == 3;
            return flag == 0;
        }
        return false;
    } else if (piece == KNIGHT) {
        return (knight_attacks[from] & (1ULL << to)) != 0;
    } else if (piece == BISHOP) {
        return (bishop_attacks_bb(from, occ) & (1ULL << to)) != 0;
    } else if (piece == ROOK) {
        return (rook_attacks_bb(from, occ) & (1ULL << to)) != 0;
    } else if (piece == QUEEN) {
        return ((bishop_attacks_bb(from, occ) | rook_attacks_bb(from, occ)) & (1ULL << to)) != 0;
    } else if (piece == KING) {
        return (king_attacks[from] & (1ULL << to)) != 0;
    }
    return false;
}

// Helper: check if move is pseudo-legal AND does not leave king in check
static bool is_legal_move(NativeBoard* b, uint16_t m) {
    if (!is_pseudo_legal_move(b, m)) return false;
    int us = b->side_to_move;
    int them = 1 - us;
    UndoInfo undo;
    if (!native_make_move(b, m, &undo)) return false;
    int k_sq = bitscan_forward(b->pieces[us][KING]);
    bool in_chk = is_square_attacked(b, k_sq, them);
    native_unmake_move(b, m, &undo);
    return !in_chk;
}

// ============================================================================
// Staged MovePicker Architecture (Phase 1)
// ============================================================================
enum MovePickerStage {
    STAGE_TT = 0,
    STAGE_GEN_CAPTURES,
    STAGE_CAPTURES,
    STAGE_KILLERS,
    STAGE_GEN_QUIETS,
    STAGE_QUIETS,
    STAGE_DONE
};

struct MovePicker {
    NativeBoard* board;
    uint16_t tt_move;
    int ply;
    int depth;
    bool in_check;
    MovePickerStage stage;

    uint16_t caps[MAX_MOVES];
    int caps_scores[MAX_MOVES];
    int num_caps;
    int cur_cap;

    uint16_t quiets[MAX_MOVES];
    int quiets_scores[MAX_MOVES];
    int num_quiets;
    int cur_quiet;

    uint16_t killer1;
    uint16_t killer2;
    int cur_killer;

    uint16_t evasions[MAX_MOVES];
    int evasion_scores[MAX_MOVES];
    int num_evasions;
    int cur_evasion;

    uint16_t yielded[MAX_MOVES];
    int num_yielded;

    void init(NativeBoard* b, uint16_t tt_m, int p, int d, bool chk) {
        board = b;
        tt_move = tt_m;
        ply = p;
        depth = d;
        in_check = chk;
        num_yielded = 0;
        cur_cap = 0;
        num_caps = 0;
        cur_quiet = 0;
        num_quiets = 0;
        cur_killer = 0;
        num_evasions = 0;
        cur_evasion = 0;

        killer1 = (ply >= 0 && ply < MAX_PLY) ? g_killer_moves[ply][0] : 0;
        killer2 = (ply >= 0 && ply < MAX_PLY) ? g_killer_moves[ply][1] : 0;

        if (in_check) {
            stage = STAGE_DONE;
            num_evasions = native_generate_legal_moves(board, evasions);
            for (int i = 0; i < num_evasions; i++) {
                evasion_scores[i] = score_move_for_ordering(board, evasions[i], tt_move, ply);
            }
            for (int i = 0; i < num_evasions - 1; i++) {
                int best_idx = i;
                for (int j = i + 1; j < num_evasions; j++) {
                    if (evasion_scores[j] > evasion_scores[best_idx]) best_idx = j;
                }
                std::swap(evasions[i], evasions[best_idx]);
                std::swap(evasion_scores[i], evasion_scores[best_idx]);
            }
        } else {
            stage = (tt_move != 0 && is_legal_move(board, tt_move)) ? STAGE_TT : STAGE_GEN_CAPTURES;
        }
    }

    uint16_t next_move() {
        if (in_check) {
            if (cur_evasion < num_evasions) {
                return evasions[cur_evasion++];
            }
            return 0;
        }

        while (stage != STAGE_DONE) {
            switch (stage) {
                case STAGE_TT: {
                    stage = STAGE_GEN_CAPTURES;
                    yielded[num_yielded++] = tt_move;
                    return tt_move;
                }
                case STAGE_GEN_CAPTURES: {
                    num_caps = native_generate_captures(board, caps);
                    for (int i = 0; i < num_caps; i++) {
                        caps_scores[i] = score_move_for_ordering(board, caps[i], 0, ply);
                    }
                    for (int i = 0; i < num_caps - 1; i++) {
                        int best_idx = i;
                        for (int j = i + 1; j < num_caps; j++) {
                            if (caps_scores[j] > caps_scores[best_idx]) best_idx = j;
                        }
                        std::swap(caps[i], caps[best_idx]);
                        std::swap(caps_scores[i], caps_scores[best_idx]);
                    }
                    stage = STAGE_CAPTURES;
                    cur_cap = 0;
                }
                case STAGE_CAPTURES: {
                    while (cur_cap < num_caps) {
                        uint16_t m = caps[cur_cap++];
                        if (!has_been_yielded(m)) {
                            yielded[num_yielded++] = m;
                            return m;
                        }
                    }
                    stage = STAGE_KILLERS;
                    cur_killer = 0;
                }
                case STAGE_KILLERS: {
                    if (cur_killer == 0) {
                        cur_killer++;
                        if (killer1 != 0 && !has_been_yielded(killer1) && is_legal_move(board, killer1)) {
                            yielded[num_yielded++] = killer1;
                            return killer1;
                        }
                    }
                    if (cur_killer == 1) {
                        cur_killer++;
                        if (killer2 != 0 && killer2 != killer1 && !has_been_yielded(killer2) && is_legal_move(board, killer2)) {
                            yielded[num_yielded++] = killer2;
                            return killer2;
                        }
                    }
                    stage = STAGE_GEN_QUIETS;
                }
                case STAGE_GEN_QUIETS: {
                    num_quiets = native_generate_quiets(board, quiets);
                    for (int i = 0; i < num_quiets; i++) {
                        quiets_scores[i] = score_move_for_ordering(board, quiets[i], 0, ply);
                    }
                    for (int i = 0; i < num_quiets - 1; i++) {
                        int best_idx = i;
                        for (int j = i + 1; j < num_quiets; j++) {
                            if (quiets_scores[j] > quiets_scores[best_idx]) best_idx = j;
                        }
                        std::swap(quiets[i], quiets[best_idx]);
                        std::swap(quiets_scores[i], quiets_scores[best_idx]);
                    }
                    stage = STAGE_QUIETS;
                    cur_quiet = 0;
                }
                case STAGE_QUIETS: {
                    while (cur_quiet < num_quiets) {
                        uint16_t m = quiets[cur_quiet++];
                        if (!has_been_yielded(m)) {
                            yielded[num_yielded++] = m;
                            return m;
                        }
                    }
                    stage = STAGE_DONE;
                    break;
                }
                default:
                    stage = STAGE_DONE;
                    break;
            }
        }
        return 0;
    }

    bool has_been_yielded(uint16_t m) const {
        for (int i = 0; i < num_yielded; i++) {
            if (yielded[i] == m) return true;
        }
        return false;
    }
};
"""
    quiescence_anchor = "static int quiescence(NativeBoard* b, int alpha, int beta, uint64_t& nodes, std::chrono::steady_clock::time_point deadline, bool& aborted) {"
    assert quiescence_anchor in code, "quiescence_anchor not found"
    code = code.replace(quiescence_anchor, staged_helpers + "\n" + quiescence_anchor, 1)

    # 3. Clean replacement of the move generation & scoring loop in quiescence()
    old_q_block = """    uint16_t moves[MAX_MOVES];
    int n = native_generate_legal_moves(b, moves);

    struct ScoredMove {
        uint16_t m;
        int score;
    };
    ScoredMove caps[MAX_MOVES];
    int n_caps = 0;

    for (int i = 0; i < n; i++) {
        uint16_t m = moves[i];
        int to = move_to(m);
        int them = 1 - b->side_to_move;
        bool is_cap = (b->occupancy[them] & (1ULL << to)) || (move_flag(m) == 2);
        if (is_cap || move_flag(m) == 3) {
            int score = 0;
            if (move_flag(m) == 3) {
                int promo = move_promo(m);
                score = (promo == 3) ? 900000 : 800000;
            } else if (g_use_see_in_quiescence) {
                int victim = NO_PIECE;
                if (move_flag(m) == 2) {
                    victim = PAWN;
                } else {
                    for (int p = 0; p < 6; p++) {
                        if (b->pieces[them][p] & (1ULL << to)) {
                            victim = p;
                            break;
                        }
                    }
                }
                int attacker = NO_PIECE;
                int from = move_from(m);
                for (int p = 0; p < 6; p++) {
                    if (b->pieces[b->side_to_move][p] & (1ULL << from)) {
                        attacker = p;
                        break;
                    }
                }
                int mvv_lva = (victim * 10) - attacker;
                int see_val = janus_see(b, m);
                g_see_total_evaluations++;
                if (see_val > 0) {
                    g_see_positive_captures++;
                    score = 100000 + mvv_lva;
                } else if (see_val == 0) {
                    g_see_neutral_captures++;
                    score = 95000 + mvv_lva;
                } else {
                    g_see_negative_captures++;
                    score = 10000 + std::max(-10000, see_val) + mvv_lva;
                }
            } else {
                score = score_move_for_ordering(b, m, 0, 0);
            }
            caps[n_caps++] = { m, score };
        }
    }

    std::sort(caps, caps + n_caps, [](const ScoredMove& a, const ScoredMove& b) {
        return a.score > b.score;
    });"""

    new_q_block = """    struct ScoredMove {
        uint16_t m;
        int score;
    };
    ScoredMove caps[MAX_MOVES];
    int n_caps = 0;

    uint16_t raw_caps[MAX_MOVES];
    int n_raw = 0;

    if (g_use_staged_movegen) {
        n_raw = native_generate_captures(b, raw_caps);
    } else {
        uint16_t all_m[MAX_MOVES];
        int n_all = native_generate_legal_moves(b, all_m);
        int them_side = 1 - b->side_to_move;
        for (int i = 0; i < n_all; i++) {
            int to = move_to(all_m[i]);
            bool is_c = (b->occupancy[them_side] & (1ULL << to)) || (move_flag(all_m[i]) == 2);
            if (is_c || move_flag(all_m[i]) == 3) {
                raw_caps[n_raw++] = all_m[i];
            }
        }
    }

    for (int i = 0; i < n_raw; i++) {
        uint16_t m = raw_caps[i];
        int to = move_to(m);
        int them = 1 - b->side_to_move;
        int score = 0;

        if (move_flag(m) == 3) {
            int promo = move_promo(m);
            score = (promo == 3) ? 900000 : 800000;
        } else if (g_quiescence_see_mode > 0 || g_use_see_in_quiescence) {
            int see_val = janus_see(b, m);
            g_see_total_evaluations++;
            if (g_quiescence_see_mode >= 2 && see_val < 0 && move_flag(m) != 3) {
                g_telemetry_qmoves_pruned++;
                continue;
            }
            if (g_quiescence_see_mode == 3 && see_val < -50 && move_flag(m) != 3) {
                g_telemetry_qmoves_pruned++;
                continue;
            }
            int victim = NO_PIECE;
            if (move_flag(m) == 2) {
                victim = PAWN;
            } else {
                for (int p = 0; p < 6; p++) {
                    if (b->pieces[them][p] & (1ULL << to)) { victim = p; break; }
                }
            }
            int attacker = NO_PIECE;
            int from = move_from(m);
            for (int p = 0; p < 6; p++) {
                if (b->pieces[b->side_to_move][p] & (1ULL << from)) { attacker = p; break; }
            }
            int mvv_lva = (victim * 10) - attacker;
            if (see_val > 0) {
                g_see_positive_captures++;
                score = 100000 + mvv_lva;
            } else if (see_val == 0) {
                g_see_neutral_captures++;
                score = 95000 + mvv_lva;
            } else {
                g_see_negative_captures++;
                score = 10000 + std::max(-10000, see_val) + mvv_lva;
            }
        } else {
            score = score_move_for_ordering(b, m, 0, 0);
        }
        caps[n_caps++] = { m, score };
    }

    std::sort(caps, caps + n_caps, [](const ScoredMove& a, const ScoredMove& b) {
        return a.score > b.score;
    });"""

    assert old_q_block in code, "old_q_block not found in janus_classical_x.cpp"
    code = code.replace(old_q_block, new_q_block, 1)

    # 4. Update negamax() for RFP and NMP
    old_negamax_tt = """        if (entry.depth >= depth && ply > 0) {
            int tt_score = score_from_tt(entry.score, ply);
            if (entry.flag == TT_EXACT) return tt_score;
            if (entry.flag == TT_LOWER && tt_score >= beta) return tt_score;
            if (entry.flag == TT_UPPER && tt_score <= alpha) return tt_score;
        }
    }"""

    new_negamax_tt_and_pruning = """        if (entry.depth >= depth && ply > 0) {
            int tt_score = score_from_tt(entry.score, ply);
            if (entry.flag == TT_EXACT) return tt_score;
            if (entry.flag == TT_LOWER && tt_score >= beta) return tt_score;
            if (entry.flag == TT_UPPER && tt_score <= alpha) return tt_score;
        }
    }

    bool in_check = (native_is_check(b) != 0);

    // ========================================================================
    // Reverse Futility Pruning (RFP / Static Null Move Pruning, Phase 4)
    // ========================================================================
    if (g_use_reverse_futility && depth <= 3 && ply > 0 && !in_check && std::abs(beta) < MATE_SCORE - 100) {
        g_telemetry_rfp_probes++;
        int static_eval = native_evaluate(b);
        int rfp_margin = g_rfp_margin_per_depth * depth;
        if (static_eval - rfp_margin >= beta) {
            g_telemetry_rfp_cutoffs++;
            return static_eval;
        }
    }

    // ========================================================================
    // Null-Move Pruning (NMP, Phase 3)
    // ========================================================================
    int us_side = b->side_to_move;
    int them_side = 1 - us_side;
    uint64_t non_pawn_mat = b->pieces[us_side][KNIGHT] | b->pieces[us_side][BISHOP] | 
                            b->pieces[us_side][ROOK]   | b->pieces[us_side][QUEEN];
    if (g_use_null_move_pruning && depth >= 3 && ply > 0 && !in_check && non_pawn_mat != 0 && std::abs(beta) < MATE_SCORE - 100) {
        g_telemetry_nmp_probes++;
        int R = g_nmp_reduction;

        b->side_to_move = them_side;
        int saved_ep = b->ep_square;
        b->ep_square = 64;
        b->zobrist_key ^= zobrist_side;
        if (saved_ep <= 63) b->zobrist_key ^= zobrist_ep[saved_ep % 8];
        native_push_history(b->zobrist_key);

        int null_score = -negamax(b, depth - 1 - R, -beta, -beta + 1, ply + 1, nodes, deadline, aborted, nullptr);

        b->side_to_move = us_side;
        b->ep_square = saved_ep;
        b->zobrist_key ^= zobrist_side;
        if (saved_ep <= 63) b->zobrist_key ^= zobrist_ep[saved_ep % 8];
        native_pop_history();

        if (aborted) return 0;
        if (null_score >= beta) {
            g_telemetry_nmp_cutoffs++;
            return (null_score >= MATE_SCORE - 100) ? beta : null_score;
        }
    }"""
    assert old_negamax_tt in code, "old_negamax_tt not found"
    code = code.replace(old_negamax_tt, new_negamax_tt_and_pruning, 1)

    # Move loop in negamax
    old_negamax_loop = """    uint16_t moves[MAX_MOVES];
    int n = native_generate_legal_moves(b, moves);

    bool in_check = (native_is_check(b) != 0);

    // Terminal state check
    if (n == 0) {
        if (in_check) {
            return -(MATE_SCORE - ply); // Checkmate
        }
        return 0; // Stalemate
    }

    // Move ordering
    struct ScoredMove {
        uint16_t m;
        int score;
    };
    ScoredMove scored_moves[MAX_MOVES];
    for (int i = 0; i < n; i++) {
        scored_moves[i] = { moves[i], score_move_for_ordering(b, moves[i], tt_move, ply) };
    }

    std::sort(scored_moves, scored_moves + n, [](const ScoredMove& a, const ScoredMove& b) {
        return a.score > b.score;
    });

    int orig_alpha = alpha;
    uint16_t best_move = scored_moves[0].m;
    int best_score = -INF;
    UndoInfo undo;
    int moves_searched = 0;

    for (int i = 0; i < n; i++) {
        uint16_t m = scored_moves[i].m;"""

    new_negamax_loop = """    int orig_alpha = alpha;
    uint16_t best_move = 0;
    int best_score = -INF;
    UndoInfo undo;
    int moves_searched = 0;
    int legal_moves_count = 0;

    MovePicker picker;
    if (g_use_staged_movegen) {
        picker.init(b, tt_move, ply, depth, in_check);
    }

    uint16_t legacy_moves[MAX_MOVES];
    int legacy_n = 0;
    struct ScoredMove {
        uint16_t m;
        int score;
    };
    ScoredMove legacy_scored[MAX_MOVES];
    if (!g_use_staged_movegen) {
        legacy_n = native_generate_legal_moves(b, legacy_moves);
        if (legacy_n == 0) {
            return in_check ? -(MATE_SCORE - ply) : 0;
        }
        for (int i = 0; i < legacy_n; i++) {
            legacy_scored[i] = { legacy_moves[i], score_move_for_ordering(b, legacy_moves[i], tt_move, ply) };
        }
        std::sort(legacy_scored, legacy_scored + legacy_n, [](const ScoredMove& a, const ScoredMove& b) {
            return a.score > b.score;
        });
        best_move = legacy_scored[0].m;
    }

    int legacy_idx = 0;
    while (true) {
        uint16_t m = 0;
        if (g_use_staged_movegen) {
            m = picker.next_move();
            if (m == 0) break;
        } else {
            if (legacy_idx >= legacy_n) break;
            m = legacy_scored[legacy_idx++].m;
        }
        legal_moves_count++;
        if (best_move == 0) best_move = m;"""

    assert old_negamax_loop in code, "old_negamax_loop not found"
    code = code.replace(old_negamax_loop, new_negamax_loop, 1)

    # Move loop end in negamax
    old_loop_end = """            if (g_use_pvs) {
                g_pvs_cutoffs++;
            }
            break; // Beta cutoff
        }
    }

    if (out_best_move) *out_best_move = best_move;"""

    new_loop_end = """            if (g_use_pvs) {
                g_pvs_cutoffs++;
            }
            g_telemetry_total_cutoffs++;
            if (moves_searched == 1) g_telemetry_first_move_cutoffs++;
            break; // Beta cutoff
        }
    }

    if (legal_moves_count == 0) {
        return in_check ? -(MATE_SCORE - ply) : 0;
    }

    if (out_best_move) *out_best_move = best_move;"""
    assert old_loop_end in code, "old_loop_end not found"
    code = code.replace(old_loop_end, new_loop_end, 1)

    # 5. Aspiration Windows in native_search()
    old_search_loop = """    for (int d = 1; d <= max_depth; d++) {
        uint16_t iter_best_move = 0;
        int score = negamax(b, d, -INF, INF, 0, total_nodes, deadline, aborted, &iter_best_move);

        if (aborted) break;"""

    new_search_loop = """    for (int d = 1; d <= max_depth; d++) {
        uint16_t iter_best_move = 0;
        int score = 0;

        if (g_use_aspiration_window && d >= 4) {
            int prev_score = out_res->score;
            int asp_alpha = prev_score - g_aspiration_delta;
            int asp_beta = prev_score + g_aspiration_delta;
            int delta = g_aspiration_delta;

            while (true) {
                score = negamax(b, d, asp_alpha, asp_beta, 0, total_nodes, deadline, aborted, &iter_best_move);
                if (aborted) break;

                if (score <= asp_alpha) {
                    g_telemetry_aspiration_researches++;
                    asp_alpha = std::max(-INF, asp_alpha - delta * 2);
                    delta *= 2;
                } else if (score >= asp_beta) {
                    g_telemetry_aspiration_researches++;
                    asp_beta = std::min(INF, asp_beta + delta * 2);
                    delta *= 2;
                } else {
                    break; // Inside window!
                }
                if (asp_alpha <= -INF && asp_beta >= INF) {
                    break;
                }
            }
        } else {
            score = negamax(b, d, -INF, INF, 0, total_nodes, deadline, aborted, &iter_best_move);
        }

        if (aborted) break;"""
    assert old_search_loop in code, "old_search_loop not found"
    code = code.replace(old_search_loop, new_search_loop, 1)

    # 6. Add UCI options and setoption handlers
    old_uci_opts = """            std::cout << "option name UseSEEInQuiescence type check default false" << std::endl;
            std::cout << "uciok" << std::endl;"""

    new_uci_opts = """            std::cout << "option name UseSEEInQuiescence type check default false" << std::endl;
            std::cout << "option name UCI_Variant type combo default X6 var X0 var X1 var X2 var X3 var X4 var X5 var X6" << std::endl;
            std::cout << "option name UCI_StagedMovegen type check default true" << std::endl;
            std::cout << "option name UCI_QuiescenceSEE type spin default 2 min 0 max 3" << std::endl;
            std::cout << "option name UCI_NullMovePruning type check default true" << std::endl;
            std::cout << "option name UCI_RFP type check default true" << std::endl;
            std::cout << "option name UCI_AspirationWindow type check default true" << std::endl;
            std::cout << "uciok" << std::endl;"""
    assert old_uci_opts in code, "old_uci_opts not found"
    code = code.replace(old_uci_opts, new_uci_opts, 1)

    old_setopt = """                } else if (opt_name == "LMRBaseReduction" && !opt_val.empty()) {
                    g_lmr_base_reduction = std::stoi(opt_val);
                }"""

    new_setopt = """                } else if (opt_name == "LMRBaseReduction" && !opt_val.empty()) {
                    g_lmr_base_reduction = std::stoi(opt_val);
                } else if (opt_name == "UCI_Variant" && !opt_val.empty()) {
                    native_apply_search_variant(opt_val.c_str());
                } else if (opt_name == "UCI_StagedMovegen") {
                    g_use_staged_movegen = (opt_val.empty() || opt_val == "true" || opt_val == "1");
                } else if (opt_name == "UCI_QuiescenceSEE" && !opt_val.empty()) {
                    g_quiescence_see_mode = std::stoi(opt_val);
                    g_use_see_in_quiescence = (g_quiescence_see_mode > 0);
                } else if (opt_name == "UCI_NullMovePruning") {
                    g_use_null_move_pruning = (opt_val.empty() || opt_val == "true" || opt_val == "1");
                } else if (opt_name == "UCI_RFP") {
                    g_use_reverse_futility = (opt_val.empty() || opt_val == "true" || opt_val == "1");
                } else if (opt_name == "UCI_AspirationWindow") {
                    g_use_aspiration_window = (opt_val.empty() || opt_val == "true" || opt_val == "1");
                }"""
    assert old_setopt in code, "old_setopt not found"
    code = code.replace(old_setopt, new_setopt, 1)

    # 7. Add telemetry dump command in UCI
    old_uci_cmd = '} else if (cmd == "ucinewgame") {'
    new_uci_cmd = """        } else if (cmd == "telemetry_report") {
            std::cout << "TELEMETRY_START" << std::endl;
            std::cout << "variant " << g_search_variant << std::endl;
            std::cout << "movegen_calls " << g_telemetry_movegen_calls << std::endl;
            std::cout << "captures_gen " << g_telemetry_captures_gen << std::endl;
            std::cout << "quiets_gen " << g_telemetry_quiets_gen << std::endl;
            std::cout << "moves_scored " << g_telemetry_moves_scored << std::endl;
            std::cout << "moves_searched " << g_telemetry_moves_searched << std::endl;
            std::cout << "first_move_cutoffs " << g_telemetry_first_move_cutoffs << std::endl;
            std::cout << "total_cutoffs " << g_telemetry_total_cutoffs << std::endl;
            std::cout << "nmp_probes " << g_telemetry_nmp_probes << std::endl;
            std::cout << "nmp_cutoffs " << g_telemetry_nmp_cutoffs << std::endl;
            std::cout << "rfp_probes " << g_telemetry_rfp_probes << std::endl;
            std::cout << "rfp_cutoffs " << g_telemetry_rfp_cutoffs << std::endl;
            std::cout << "aspiration_researches " << g_telemetry_aspiration_researches << std::endl;
            std::cout << "qmoves_pruned " << g_telemetry_qmoves_pruned << std::endl;
            std::cout << "TELEMETRY_END" << std::endl;
        } else if (cmd == "telemetry_reset") {
            native_reset_p11_telemetry();
            std::cout << "telemetry_reset_ok" << std::endl;
        } else if (cmd == "ucinewgame") {"""
    assert old_uci_cmd in code, "old_uci_cmd not found"
    code = code.replace(old_uci_cmd, new_uci_cmd, 1)

    with open(SRC_CPP, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"Successfully updated {SRC_CPP} ({len(code):,} bytes).")

    # Now compile EXE and DLL
    print("\n[BUILD] Compiling janus_classical_x.exe...")
    cmd_exe = f'cmd.exe /c ""{VCVARS}" && cl /O2 /Ot /Oi /std:c++17 /EHsc janus_classical_x.cpp /Fe:janus_classical_x.exe"'
    res = subprocess.run(cmd_exe, cwd=str(TARGET_DIR), capture_output=True, text=True)
    if res.returncode != 0:
        print("[BUILD ERROR EXE]:", res.stderr, res.stdout)
        raise RuntimeError("EXE compilation failed")
    print(f"[BUILD] Success! Size: {(TARGET_DIR / 'janus_classical_x.exe').stat().st_size:,} bytes")

    print("\n[BUILD] Compiling janus_classical_x.dll...")
    cmd_dll = f'cmd.exe /c ""{VCVARS}" && cl /O2 /Ot /Oi /std:c++17 /EHsc /LD janus_classical_x.cpp /Fe:janus_classical_x.dll"'
    res = subprocess.run(cmd_dll, cwd=str(TARGET_DIR), capture_output=True, text=True)
    if res.returncode != 0:
        print("[BUILD ERROR DLL]:", res.stderr, res.stdout)
        raise RuntimeError("DLL compilation failed")
    print(f"[BUILD] Success! Size: {(TARGET_DIR / 'janus_classical_x.dll').stat().st_size:,} bytes")

if __name__ == "__main__":
    main()
