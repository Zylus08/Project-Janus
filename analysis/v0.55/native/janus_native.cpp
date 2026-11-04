/*
 * Project Janus v0.51 - Native Search Core & Standalone UCI Engine (Candidate N2)
 *
 * Full C++17 native chess engine implementing:
 * - 64-bit bitboard state representation (pieces, occupancies, castling, EP)
 * - Polyglot-compatible 64-bit Zobrist hashing with incremental make/unmake
 * - FIDE Legal Move Generation (pins, checks, double checks, castling, en passant, promotions)
 * - FIDE Draw & Repetition History: 1,024-ply game history stack
 * - Explicit distinction between Claimable Draws (Threefold, 50-move) and Automatic Draws (Fivefold, 75-move, Insufficient Material)
 * - Intended-move draw claim detection
 * - Alpha-Beta Negamax search with Iterative Deepening
 * - 1M-entry Transposition Table with depth-preferred aging and normalized mate scores
 * - Quiescence Search with delta pruning and MVV-LVA capture ordering
 * - Triangular PV Table for exact principal variation tracking
 * - Standalone UCI Protocol loop (uci, isready, ucinewgame, position, go, stop, quit)
 * - Time management with Fischer increment support and safety margins
 */

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#ifdef _MSC_VER
#include <intrin.h>
#define EXPORT extern "C" __declspec(dllexport)
#else
#define EXPORT extern "C"
#endif

// ============================================================================
// Constants & Configuration
// ============================================================================

constexpr int WHITE = 0;
constexpr int BLACK = 1;
constexpr int NO_COLOR = 2;

constexpr int PAWN = 0;
constexpr int KNIGHT = 1;
constexpr int BISHOP = 2;
constexpr int ROOK = 3;
constexpr int QUEEN = 4;
constexpr int KING = 5;
constexpr int NO_PIECE = 6;

constexpr int INF = 30000;
constexpr int MATE_SCORE = 29000;
constexpr int MATE_THRESHOLD = 28000;

constexpr uint8_t CASTLE_W_OO = 1;
constexpr uint8_t CASTLE_W_OOO = 2;
constexpr uint8_t CASTLE_B_OO = 4;
constexpr uint8_t CASTLE_B_OOO = 8;

constexpr int MAX_SEARCH_PLY = 128;
constexpr int MAX_MOVES = 256;
constexpr int MAX_GAME_HISTORY = 1024;

// Move encoding (uint16_t):
// bits 0..5: from
// bits 6..11: to
// bits 12..13: flag (0=normal, 1=castle, 2=ep, 3=promo)
// bits 14..15: promo piece (0=N, 1=B, 2=R, 3=Q)
inline uint16_t encode_move(int from, int to, int flag = 0, int promo = 0) {
    return (from & 0x3F) | ((to & 0x3F) << 6) | ((flag & 3) << 12) | ((promo & 3) << 14);
}
inline int move_from(uint16_t m) { return m & 0x3F; }
inline int move_to(uint16_t m) { return (m >> 6) & 0x3F; }
inline int move_flag(uint16_t m) { return (m >> 12) & 3; }
inline int move_promo(uint16_t m) { return (m >> 14) & 3; }

// ============================================================================
// Core Structs
// ============================================================================

struct NativeBoard {
    uint64_t pieces[2][6];    // [color][piece]
    uint64_t occupancy[3];    // 0=white, 1=black, 2=both
    uint8_t side_to_move;     // 0=white, 1=black
    uint8_t castling_rights;  // 4-bit mask
    uint8_t ep_square;        // 0..63, or 64 if none
    uint16_t halfmove_clock;
    uint16_t fullmove_number;
    uint64_t zobrist_key;
};

struct UndoInfo {
    uint8_t captured_piece;   // 0..5, or 6 if none
    uint8_t castling_rights;
    uint8_t ep_square;
    uint16_t halfmove_clock;
    uint64_t zobrist_key;
};

struct NativeSearchResult {
    uint16_t best_move;
    int score;
    int depth;
    uint64_t nodes;
    double elapsed_seconds;
    int pv_length;
    uint16_t pv[MAX_SEARCH_PLY];
};

// ============================================================================
// Transposition Table Layout & Mate Normalization
// ============================================================================

constexpr uint8_t TT_EXACT = 0;
constexpr uint8_t TT_LOWER = 1;
constexpr uint8_t TT_UPPER = 2;

struct TTEntry {
    uint64_t key;
    int16_t score;
    int8_t depth;
    uint8_t flag;
    uint8_t age;
    uint16_t best_move;
};

constexpr size_t TT_SIZE = 1 << 20; // 1,048,576 entries (~24 MB)
static TTEntry g_tt[TT_SIZE];
static uint8_t g_tt_age = 0;

inline int score_to_tt(int score, int ply) {
    if (score >= MATE_SCORE - MAX_SEARCH_PLY) return score + ply;
    if (score <= -MATE_SCORE + MAX_SEARCH_PLY) return score - ply;
    return score;
}

inline int score_from_tt(int score, int ply) {
    if (score >= MATE_SCORE - MAX_SEARCH_PLY) return score - ply;
    if (score <= -MATE_SCORE + MAX_SEARCH_PLY) return score + ply;
    return score;
}

// ============================================================================
// Game History & Repetition Stack (Phase B)
// ============================================================================

static uint64_t g_game_history[MAX_GAME_HISTORY];
static int g_game_history_len = 0;

// PV Table (Phase C)
static uint16_t g_pv_table[MAX_SEARCH_PLY][MAX_SEARCH_PLY];
static int g_pv_len[MAX_SEARCH_PLY];

// LMR Configuration & Telemetry (Phase 3 v0.52 - Category A Promoted)
static bool g_use_lmr = true;
static int g_lmr_min_depth = 3;
static int g_lmr_move_threshold = 4;
static int g_lmr_base_reduction = 1;

static uint64_t g_lmr_eligible_moves = 0;
static uint64_t g_lmr_reduced_moves = 0;
static uint64_t g_lmr_researches = 0;
static uint64_t g_lmr_cutoffs = 0;

// PVS Configuration & Telemetry (Phase 3 v0.53)
static bool g_use_pvs = false;

static uint64_t g_pvs_full_window_searches = 0;
static uint64_t g_pvs_null_window_searches = 0;
static uint64_t g_pvs_researches = 0;
static uint64_t g_pvs_cutoffs = 0;

// Move Ordering Configuration & Telemetry (Phase 2 & 3 v0.54)
static bool g_use_killer_ordering = true;
static bool g_use_history_ordering = true;

constexpr int MAX_PLY = 64;
constexpr int KILLER_SLOTS = 2;
static uint16_t g_killer_moves[MAX_PLY][KILLER_SLOTS];

constexpr int SIDES = 2;
constexpr int SQUARES = 64;
constexpr int MAX_HISTORY_SCORE = 70000;
static int g_history_table[SIDES][SQUARES][SQUARES];

static uint64_t g_ordering_total_cutoffs = 0;
static uint64_t g_ordering_sum_cutoff_index = 0;
static uint64_t g_ordering_cutoff_move_1 = 0;
static uint64_t g_ordering_cutoff_move_2 = 0;
static uint64_t g_ordering_cutoff_move_3 = 0;
static uint64_t g_ordering_cutoff_move_4plus = 0;
static uint64_t g_ordering_cutoff_tt = 0;
static uint64_t g_ordering_cutoff_killer1 = 0;
static uint64_t g_ordering_cutoff_killer2 = 0;
static uint64_t g_ordering_cutoff_history = 0;
static uint64_t g_ordering_cutoff_captures = 0;
static uint64_t g_ordering_cutoff_quiet = 0;

// ============================================================================
// Attack Tables and Zobrist Keys
// ============================================================================

static uint64_t knight_attacks[64];
static uint64_t king_attacks[64];
static uint64_t pawn_attacks[2][64];

static uint64_t zobrist_pieces[2][6][64];
static uint64_t zobrist_castling[16];
static uint64_t zobrist_ep[65];
static uint64_t zobrist_side;
static bool tables_initialized = false;

// PRNG for Zobrist (Polyglot compatible LCG)
static uint64_t lcg_rand64() {
    static uint64_t seed = 1070372;
    seed = seed * 6364136223846793005ULL + 1442695040888963407ULL;
    return seed;
}

// Bit manipulation primitives
inline int popcount64(uint64_t b) {
#ifdef _MSC_VER
    return (int)__popcnt64(b);
#else
    return __builtin_popcountll(b);
#endif
}

inline int bitscan_forward(uint64_t b) {
#ifdef _MSC_VER
    unsigned long idx;
    _BitScanForward64(&idx, b);
    return (int)idx;
#else
    return __builtin_ctzll(b);
#endif
}

inline int bitscan_reverse(uint64_t b) {
#ifdef _MSC_VER
    unsigned long idx;
    _BitScanReverse64(&idx, b);
    return (int)idx;
#else
    return 63 - __builtin_clzll(b);
#endif
}

// Ray-casting sliding attacks
static uint64_t rook_attacks_bb(int sq, uint64_t occ) {
    uint64_t att = 0;
    int r = sq / 8, f = sq % 8;
    for (int i = r + 1; i <= 7; i++) { int s = i * 8 + f; att |= (1ULL << s); if (occ & (1ULL << s)) break; }
    for (int i = r - 1; i >= 0; i--) { int s = i * 8 + f; att |= (1ULL << s); if (occ & (1ULL << s)) break; }
    for (int j = f + 1; j <= 7; j++) { int s = r * 8 + j; att |= (1ULL << s); if (occ & (1ULL << s)) break; }
    for (int j = f - 1; j >= 0; j--) { int s = r * 8 + j; att |= (1ULL << s); if (occ & (1ULL << s)) break; }
    return att;
}

static uint64_t bishop_attacks_bb(int sq, uint64_t occ) {
    uint64_t att = 0;
    int r = sq / 8, f = sq % 8;
    for (int i = r + 1, j = f + 1; i <= 7 && j <= 7; i++, j++) { int s = i * 8 + j; att |= (1ULL << s); if (occ & (1ULL << s)) break; }
    for (int i = r + 1, j = f - 1; i <= 7 && j >= 0; i++, j--) { int s = i * 8 + j; att |= (1ULL << s); if (occ & (1ULL << s)) break; }
    for (int i = r - 1, j = f + 1; i >= 0 && j <= 7; i--, j++) { int s = i * 8 + j; att |= (1ULL << s); if (occ & (1ULL << s)) break; }
    for (int i = r - 1, j = f - 1; i >= 0 && j >= 0; i--, j--) { int s = i * 8 + j; att |= (1ULL << s); if (occ & (1ULL << s)) break; }
    return att;
}

inline uint64_t queen_attacks_bb(int sq, uint64_t occ) {
    return rook_attacks_bb(sq, occ) | bishop_attacks_bb(sq, occ);
}

static void init_attacks() {
    if (tables_initialized) return;

    for (int sq = 0; sq < 64; sq++) {
        int r = sq / 8, f = sq % 8;
        // Knight
        uint64_t b = 0;
        int dr[8] = { 2, 1, -1, -2, -2, -1, 1, 2 };
        int df[8] = { 1, 2, 2, 1, -1, -2, -2, -1 };
        for (int i = 0; i < 8; i++) {
            int nr = r + dr[i], nf = f + df[i];
            if (nr >= 0 && nr < 8 && nf >= 0 && nf < 8) b |= (1ULL << (nr * 8 + nf));
        }
        knight_attacks[sq] = b;

        // King
        b = 0;
        int kr[8] = { 1, 1, 1, 0, 0, -1, -1, -1 };
        int kf[8] = { -1, 0, 1, -1, 1, -1, 0, 1 };
        for (int i = 0; i < 8; i++) {
            int nr = r + kr[i], nf = f + kf[i];
            if (nr >= 0 && nr < 8 && nf >= 0 && nf < 8) b |= (1ULL << (nr * 8 + nf));
        }
        king_attacks[sq] = b;

        // White Pawn Attacks (moves up: +7, +9)
        uint64_t wp = 0;
        if (r < 7 && f > 0) wp |= (1ULL << ((r + 1) * 8 + f - 1));
        if (r < 7 && f < 7) wp |= (1ULL << ((r + 1) * 8 + f + 1));
        pawn_attacks[WHITE][sq] = wp;

        // Black Pawn Attacks (moves down: -9, -7)
        uint64_t bp = 0;
        if (r > 0 && f > 0) bp |= (1ULL << ((r - 1) * 8 + f - 1));
        if (r > 0 && f < 7) bp |= (1ULL << ((r - 1) * 8 + f + 1));
        pawn_attacks[BLACK][sq] = bp;
    }

    // Zobrist initialization
    for (int c = 0; c < 2; c++) {
        for (int p = 0; p < 6; p++) {
            for (int s = 0; s < 64; s++) {
                zobrist_pieces[c][p][s] = lcg_rand64();
            }
        }
    }
    for (int i = 0; i < 16; i++) zobrist_castling[i] = lcg_rand64();
    for (int i = 0; i < 65; i++) zobrist_ep[i] = lcg_rand64();
    zobrist_side = lcg_rand64();

    tables_initialized = true;
}

// Compute 64-bit Zobrist key from scratch
static uint64_t compute_zobrist(const NativeBoard* b) {
    uint64_t key = 0;
    for (int c = 0; c < 2; c++) {
        for (int p = 0; p < 6; p++) {
            uint64_t bb = b->pieces[c][p];
            while (bb) {
                int sq = bitscan_forward(bb);
                key ^= zobrist_pieces[c][p][sq];
                bb &= bb - 1;
            }
        }
    }
    key ^= zobrist_castling[b->castling_rights & 15];
    key ^= zobrist_ep[b->ep_square <= 63 ? b->ep_square : 64];
    if (b->side_to_move == BLACK) key ^= zobrist_side;
    return key;
}

// Square attacked query
static bool is_square_attacked(const NativeBoard* b, int sq, int attacker_color) {
    uint64_t occ = b->occupancy[2];
    int defender_color = 1 - attacker_color;

    if (pawn_attacks[defender_color][sq] & b->pieces[attacker_color][PAWN]) return true;
    if (knight_attacks[sq] & b->pieces[attacker_color][KNIGHT]) return true;
    if (king_attacks[sq] & b->pieces[attacker_color][KING]) return true;
    if (bishop_attacks_bb(sq, occ) & (b->pieces[attacker_color][BISHOP] | b->pieces[attacker_color][QUEEN])) return true;
    if (rook_attacks_bb(sq, occ) & (b->pieces[attacker_color][ROOK] | b->pieces[attacker_color][QUEEN])) return true;

    return false;
}

EXPORT int native_is_check(const NativeBoard* b) {
    int k_sq = bitscan_forward(b->pieces[b->side_to_move][KING]);
    return is_square_attacked(b, k_sq, 1 - b->side_to_move) ? 1 : 0;
}

// ============================================================================
// FEN Parsing and Export
// ============================================================================

EXPORT int native_init() {
    init_attacks();
    std::memset(g_tt, 0, sizeof(g_tt));
    std::memset(g_killer_moves, 0, sizeof(g_killer_moves));
    std::memset(g_history_table, 0, sizeof(g_history_table));
    g_game_history_len = 0;
    return 1;
}

EXPORT int native_set_fen(const char* fen, NativeBoard* out_b) {
    init_attacks();
    std::memset(out_b, 0, sizeof(NativeBoard));
    out_b->ep_square = 64;

    int r = 7, f = 0;
    int idx = 0;

    // 1. Piece placement
    while (fen[idx] && fen[idx] != ' ') {
        char c = fen[idx++];
        if (c == '/') {
            r--;
            f = 0;
            if (r < 0) return 0;
        } else if (c >= '1' && c <= '8') {
            f += (c - '0');
        } else {
            int color = (c >= 'a' && c <= 'z') ? BLACK : WHITE;
            char upper = (color == BLACK) ? (c - 32) : c;
            int piece = NO_PIECE;
            switch (upper) {
                case 'P': piece = PAWN; break;
                case 'N': piece = KNIGHT; break;
                case 'B': piece = BISHOP; break;
                case 'R': piece = ROOK; break;
                case 'Q': piece = QUEEN; break;
                case 'K': piece = KING; break;
                default: return 0; // Malformed char
            }
            if (f > 7 || r < 0) return 0;
            int sq = r * 8 + f;
            out_b->pieces[color][piece] |= (1ULL << sq);
            f++;
        }
    }

    // Validation: Exactly 1 king per side
    if (popcount64(out_b->pieces[WHITE][KING]) != 1 || popcount64(out_b->pieces[BLACK][KING]) != 1) {
        return 0;
    }

    out_b->occupancy[WHITE] = 0;
    out_b->occupancy[BLACK] = 0;
    for (int p = 0; p < 6; p++) {
        out_b->occupancy[WHITE] |= out_b->pieces[WHITE][p];
        out_b->occupancy[BLACK] |= out_b->pieces[BLACK][p];
    }
    out_b->occupancy[2] = out_b->occupancy[WHITE] | out_b->occupancy[BLACK];

    if (!fen[idx]) return 0;
    idx++; // Skip space

    // 2. Side to move
    if (fen[idx] == 'w') out_b->side_to_move = WHITE;
    else if (fen[idx] == 'b') out_b->side_to_move = BLACK;
    else return 0;
    idx++;

    if (!fen[idx]) return 0;
    idx++; // Skip space

    // 3. Castling rights
    out_b->castling_rights = 0;
    if (fen[idx] == '-') {
        idx++;
    } else {
        while (fen[idx] && fen[idx] != ' ') {
            if (fen[idx] == 'K') out_b->castling_rights |= CASTLE_W_OO;
            else if (fen[idx] == 'Q') out_b->castling_rights |= CASTLE_W_OOO;
            else if (fen[idx] == 'k') out_b->castling_rights |= CASTLE_B_OO;
            else if (fen[idx] == 'q') out_b->castling_rights |= CASTLE_B_OOO;
            idx++;
        }
    }

    if (!fen[idx]) return 0;
    idx++; // Skip space

    // 4. En passant square
    if (fen[idx] == '-') {
        out_b->ep_square = 64;
        idx++;
    } else {
        char f_char = fen[idx++];
        char r_char = fen[idx++];
        int ep_f = f_char - 'a';
        int ep_r = r_char - '1';
        if (ep_f >= 0 && ep_f <= 7 && (ep_r == 2 || ep_r == 5)) {
            out_b->ep_square = (uint8_t)(ep_r * 8 + ep_f);
        } else {
            return 0; // Malformed en passant square
        }
    }

    // 5. Halfmove clock
    out_b->halfmove_clock = 0;
    if (fen[idx] == ' ') {
        idx++;
        char* end;
        out_b->halfmove_clock = (uint16_t)std::strtol(fen + idx, &end, 10);
        idx = (int)(end - fen);
    }

    // 6. Fullmove number
    out_b->fullmove_number = 1;
    if (fen[idx] == ' ') {
        idx++;
        char* end;
        out_b->fullmove_number = (uint16_t)std::strtol(fen + idx, &end, 10);
    }

    out_b->zobrist_key = compute_zobrist(out_b);
    return 1;
}

EXPORT void native_get_fen(const NativeBoard* b, char* out_fen) {
    int idx = 0;
    const char piece_chars[2][6] = {
        { 'P', 'N', 'B', 'R', 'Q', 'K' },
        { 'p', 'n', 'b', 'r', 'q', 'k' }
    };

    for (int r = 7; r >= 0; r--) {
        int empty = 0;
        for (int f = 0; f < 8; f++) {
            int sq = r * 8 + f;
            int found_piece = NO_PIECE;
            int found_color = NO_COLOR;

            for (int c = 0; c < 2; c++) {
                for (int p = 0; p < 6; p++) {
                    if (b->pieces[c][p] & (1ULL << sq)) {
                        found_piece = p;
                        found_color = c;
                        break;
                    }
                }
                if (found_piece != NO_PIECE) break;
            }

            if (found_piece == NO_PIECE) {
                empty++;
            } else {
                if (empty > 0) {
                    out_fen[idx++] = '0' + empty;
                    empty = 0;
                }
                out_fen[idx++] = piece_chars[found_color][found_piece];
            }
        }
        if (empty > 0) out_fen[idx++] = '0' + empty;
        if (r > 0) out_fen[idx++] = '/';
    }

    out_fen[idx++] = ' ';
    out_fen[idx++] = (b->side_to_move == WHITE) ? 'w' : 'b';
    out_fen[idx++] = ' ';

    if (b->castling_rights == 0) {
        out_fen[idx++] = '-';
    } else {
        if (b->castling_rights & CASTLE_W_OO) out_fen[idx++] = 'K';
        if (b->castling_rights & CASTLE_W_OOO) out_fen[idx++] = 'Q';
        if (b->castling_rights & CASTLE_B_OO) out_fen[idx++] = 'k';
        if (b->castling_rights & CASTLE_B_OOO) out_fen[idx++] = 'q';
    }

    out_fen[idx++] = ' ';
    if (b->ep_square > 63) {
        out_fen[idx++] = '-';
    } else {
        out_fen[idx++] = 'a' + (b->ep_square % 8);
        out_fen[idx++] = '1' + (b->ep_square / 8);
    }

    std::sprintf(out_fen + idx, " %u %u", b->halfmove_clock, b->fullmove_number);
}

// ============================================================================
// State Transitions: Make / Unmake Move
// ============================================================================

EXPORT int native_make_move(NativeBoard* b, uint16_t m, UndoInfo* undo) {
    int from = move_from(m);
    int to = move_to(m);
    int flag = move_flag(m);
    int promo = move_promo(m);

    int us = b->side_to_move;
    int them = 1 - us;

    undo->captured_piece = NO_PIECE;
    undo->castling_rights = b->castling_rights;
    undo->ep_square = b->ep_square;
    undo->halfmove_clock = b->halfmove_clock;
    undo->zobrist_key = b->zobrist_key;

    // Identify moving piece
    int piece = NO_PIECE;
    for (int p = 0; p < 6; p++) {
        if (b->pieces[us][p] & (1ULL << from)) {
            piece = p;
            break;
        }
    }
    if (piece == NO_PIECE) return 0; // Illegal: no piece on from sq

    // Identify captured piece
    if (flag == 2) { // En Passant
        undo->captured_piece = PAWN;
        int cap_sq = (us == WHITE) ? (to - 8) : (to + 8);
        b->pieces[them][PAWN] &= ~(1ULL << cap_sq);
        b->occupancy[them] &= ~(1ULL << cap_sq);
        b->zobrist_key ^= zobrist_pieces[them][PAWN][cap_sq];
    } else {
        for (int p = 0; p < 6; p++) {
            if (b->pieces[them][p] & (1ULL << to)) {
                undo->captured_piece = p;
                b->pieces[them][p] &= ~(1ULL << to);
                b->occupancy[them] &= ~(1ULL << to);
                b->zobrist_key ^= zobrist_pieces[them][p][to];
                break;
            }
        }
    }

    // Move piece from -> to
    b->pieces[us][piece] &= ~(1ULL << from);
    b->zobrist_key ^= zobrist_pieces[us][piece][from];

    int place_piece = piece;
    if (flag == 3) { // Promotion
        place_piece = promo + 1; // 0=N(1), 1=B(2), 2=R(3), 3=Q(4)
    }

    b->pieces[us][place_piece] |= (1ULL << to);
    b->zobrist_key ^= zobrist_pieces[us][place_piece][to];

    // Castling move: shift rook
    if (flag == 1) {
        if (to == 6) { // White O-O
            b->pieces[WHITE][ROOK] &= ~(1ULL << 7);
            b->pieces[WHITE][ROOK] |= (1ULL << 5);
            b->zobrist_key ^= zobrist_pieces[WHITE][ROOK][7] ^ zobrist_pieces[WHITE][ROOK][5];
        } else if (to == 2) { // White O-O-O
            b->pieces[WHITE][ROOK] &= ~(1ULL << 0);
            b->pieces[WHITE][ROOK] |= (1ULL << 3);
            b->zobrist_key ^= zobrist_pieces[WHITE][ROOK][0] ^ zobrist_pieces[WHITE][ROOK][3];
        } else if (to == 62) { // Black O-O
            b->pieces[BLACK][ROOK] &= ~(1ULL << 63);
            b->pieces[BLACK][ROOK] |= (1ULL << 61);
            b->zobrist_key ^= zobrist_pieces[BLACK][ROOK][63] ^ zobrist_pieces[BLACK][ROOK][61];
        } else if (to == 58) { // Black O-O-O
            b->pieces[BLACK][ROOK] &= ~(1ULL << 56);
            b->pieces[BLACK][ROOK] |= (1ULL << 59);
            b->zobrist_key ^= zobrist_pieces[BLACK][ROOK][56] ^ zobrist_pieces[BLACK][ROOK][59];
        }
    }

    // Rebuild occupancies
    b->occupancy[WHITE] = 0;
    b->occupancy[BLACK] = 0;
    for (int p = 0; p < 6; p++) {
        b->occupancy[WHITE] |= b->pieces[WHITE][p];
        b->occupancy[BLACK] |= b->pieces[BLACK][p];
    }
    b->occupancy[2] = b->occupancy[WHITE] | b->occupancy[BLACK];

    // Invalidate castling rights if king or rook moved / captured
    b->zobrist_key ^= zobrist_castling[b->castling_rights & 15];
    if (piece == KING) {
        if (us == WHITE) b->castling_rights &= ~(CASTLE_W_OO | CASTLE_W_OOO);
        else b->castling_rights &= ~(CASTLE_B_OO | CASTLE_B_OOO);
    }
    if (from == 0 || to == 0) b->castling_rights &= ~CASTLE_W_OOO;
    if (from == 7 || to == 7) b->castling_rights &= ~CASTLE_W_OO;
    if (from == 56 || to == 56) b->castling_rights &= ~CASTLE_B_OOO;
    if (from == 63 || to == 63) b->castling_rights &= ~CASTLE_B_OO;
    b->zobrist_key ^= zobrist_castling[b->castling_rights & 15];

    // Reset EP square in hash
    b->zobrist_key ^= zobrist_ep[b->ep_square <= 63 ? b->ep_square : 64];
    b->ep_square = 64;
    if (piece == PAWN && std::abs(to - from) == 16) {
        b->ep_square = (uint8_t)((from + to) / 2);
    }
    b->zobrist_key ^= zobrist_ep[b->ep_square <= 63 ? b->ep_square : 64];

    // Update halfmove clock
    b->halfmove_clock++;
    if (piece == PAWN || undo->captured_piece != NO_PIECE) {
        b->halfmove_clock = 0;
    }

    if (us == BLACK) b->fullmove_number++;
    b->side_to_move = them;
    b->zobrist_key ^= zobrist_side;

    return 1;
}

EXPORT void native_unmake_move(NativeBoard* b, uint16_t m, const UndoInfo* undo) {
    int from = move_from(m);
    int to = move_to(m);
    int flag = move_flag(m);
    int promo = move_promo(m);

    int them = b->side_to_move;
    int us = 1 - them;

    b->side_to_move = us;
    if (us == BLACK) b->fullmove_number--;

    int placed_piece = NO_PIECE;
    if (flag == 3) {
        placed_piece = promo + 1;
    } else {
        for (int p = 0; p < 6; p++) {
            if (b->pieces[us][p] & (1ULL << to)) {
                placed_piece = p;
                break;
            }
        }
    }

    b->pieces[us][placed_piece] &= ~(1ULL << to);
    int orig_piece = (flag == 3) ? PAWN : placed_piece;
    b->pieces[us][orig_piece] |= (1ULL << from);

    // Restore captured piece
    if (flag == 2) { // En Passant
        int cap_sq = (us == WHITE) ? (to - 8) : (to + 8);
        b->pieces[them][PAWN] |= (1ULL << cap_sq);
    } else if (undo->captured_piece != NO_PIECE) {
        b->pieces[them][undo->captured_piece] |= (1ULL << to);
    }

    // Unmake castling move: restore rook
    if (flag == 1) {
        if (to == 6) {
            b->pieces[WHITE][ROOK] &= ~(1ULL << 5);
            b->pieces[WHITE][ROOK] |= (1ULL << 7);
        } else if (to == 2) {
            b->pieces[WHITE][ROOK] &= ~(1ULL << 3);
            b->pieces[WHITE][ROOK] |= (1ULL << 0);
        } else if (to == 62) {
            b->pieces[BLACK][ROOK] &= ~(1ULL << 61);
            b->pieces[BLACK][ROOK] |= (1ULL << 63);
        } else if (to == 58) {
            b->pieces[BLACK][ROOK] &= ~(1ULL << 59);
            b->pieces[BLACK][ROOK] |= (1ULL << 56);
        }
    }

    b->castling_rights = undo->castling_rights;
    b->ep_square = undo->ep_square;
    b->halfmove_clock = undo->halfmove_clock;
    b->zobrist_key = undo->zobrist_key;

    b->occupancy[WHITE] = 0;
    b->occupancy[BLACK] = 0;
    for (int p = 0; p < 6; p++) {
        b->occupancy[WHITE] |= b->pieces[WHITE][p];
        b->occupancy[BLACK] |= b->pieces[BLACK][p];
    }
    b->occupancy[2] = b->occupancy[WHITE] | b->occupancy[BLACK];
}

// ============================================================================
// Legal Move Generation
// ============================================================================

EXPORT int native_generate_legal_moves(NativeBoard* b, uint16_t* out_moves) {
    uint16_t pseudo_moves[MAX_MOVES];
    int p_count = 0;

    int us = b->side_to_move;
    int them = 1 - us;
    uint64_t occ = b->occupancy[2];
    uint64_t enemies = b->occupancy[them];
    uint64_t empty = ~occ;

    // 1. Pawn Moves
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
            if (to / 8 == promo_rank) {
                for (int pr = 0; pr < 4; pr++) pseudo_moves[p_count++] = encode_move(sq, to, 3, pr);
            } else {
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

        // Captures
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
        uint64_t att = knight_attacks[sq] & ~b->occupancy[us];
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
        uint64_t att = bishop_attacks_bb(sq, occ) & ~b->occupancy[us];
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
        uint64_t att = rook_attacks_bb(sq, occ) & ~b->occupancy[us];
        while (att) {
            int to = bitscan_forward(att);
            att &= att - 1;
            pseudo_moves[p_count++] = encode_move(sq, to);
        }
    }

    // 5. King
    int k_sq = bitscan_forward(b->pieces[us][KING]);
    uint64_t k_att = king_attacks[k_sq] & ~b->occupancy[us];
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

    // 7. Legality filter (ensure moving king is not in check)
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

    return legal_count;
}

// Perft function for qualification
EXPORT uint64_t native_perft(NativeBoard* b, int depth) {
    if (depth <= 0) return 1ULL;

    uint16_t moves[MAX_MOVES];
    int n = native_generate_legal_moves(b, moves);
    if (depth == 1) return (uint64_t)n;

    uint64_t nodes = 0;
    UndoInfo undo;
    for (int i = 0; i < n; i++) {
        native_make_move(b, moves[i], &undo);
        nodes += native_perft(b, depth - 1);
        native_unmake_move(b, moves[i], &undo);
    }
    return nodes;
}

// ============================================================================
// FIDE Draw Semantics & Repetition Implementation (Phase B)
// ============================================================================

EXPORT void native_reset_history() {
    g_game_history_len = 0;
}

EXPORT void native_push_history(uint64_t key) {
    if (g_game_history_len < MAX_GAME_HISTORY) {
        g_game_history[g_game_history_len++] = key;
    }
}

EXPORT void native_pop_history() {
    if (g_game_history_len > 0) {
        g_game_history_len--;
    }
}

EXPORT int native_get_history_len() {
    return g_game_history_len;
}

EXPORT uint64_t native_get_history_key(int idx) {
    if (idx >= 0 && idx < g_game_history_len) {
        return g_game_history[idx];
    }
    return 0;
}

// Count occurrences of position b in history (including current)
static int count_repetition_occurrences(const NativeBoard* b) {
    uint64_t target_key = b->zobrist_key;
    int count = 0;

    // In chess, repetition can only occur back to the last irreversible move
    int lookback = std::min(g_game_history_len, (int)b->halfmove_clock + 1);
    for (int i = g_game_history_len - 1; i >= g_game_history_len - lookback; i--) {
        if (i >= 0 && g_game_history[i] == target_key) {
            count++;
        }
    }

    // If current board is not yet in history (e.g. before push_history), count current
    if (g_game_history_len == 0 || g_game_history[g_game_history_len - 1] != target_key) {
        count++;
    }

    return count;
}

EXPORT int native_is_repetition(const NativeBoard* b, int required_count) {
    return (count_repetition_occurrences(b) >= required_count) ? 1 : 0;
}

EXPORT int native_is_fivefold_repetition(const NativeBoard* b) {
    return (count_repetition_occurrences(b) >= 5) ? 1 : 0;
}

EXPORT int native_can_claim_threefold_repetition(NativeBoard* b) {
    // 1. Current position already occurred >= 3 times
    if (count_repetition_occurrences(b) >= 3) return 1;

    // 2. Intended move: player has a legal move that brings about the 3rd occurrence
    uint16_t moves[MAX_MOVES];
    int n = native_generate_legal_moves(b, moves);
    UndoInfo undo;

    for (int i = 0; i < n; i++) {
        native_make_move(b, moves[i], &undo);
        int child_count = count_repetition_occurrences(b);
        native_unmake_move(b, moves[i], &undo);

        if (child_count >= 3) {
            return 1;
        }
    }
    return 0;
}

EXPORT int native_can_claim_fifty_moves(NativeBoard* b) {
    if (b->halfmove_clock >= 100) return 1;

    // Intended move: if halfmove_clock == 99, any legal non-capture non-pawn move produces 100
    if (b->halfmove_clock >= 99) {
        uint16_t moves[MAX_MOVES];
        int n = native_generate_legal_moves(b, moves);
        UndoInfo undo;
        for (int i = 0; i < n; i++) {
            native_make_move(b, moves[i], &undo);
            int child_hmc = b->halfmove_clock;
            native_unmake_move(b, moves[i], &undo);
            if (child_hmc >= 100) return 1;
        }
    }
    return 0;
}

EXPORT int native_is_seventyfive_moves(const NativeBoard* b) {
    return (b->halfmove_clock >= 150) ? 1 : 0;
}

EXPORT int native_is_insufficient_material(const NativeBoard* b) {
    // If pawns, rooks, or queens exist, checkmate is possible
    if (b->pieces[WHITE][PAWN] || b->pieces[BLACK][PAWN] ||
        b->pieces[WHITE][ROOK] || b->pieces[BLACK][ROOK] ||
        b->pieces[WHITE][QUEEN] || b->pieces[BLACK][QUEEN]) {
        return 0;
    }

    int w_knights = popcount64(b->pieces[WHITE][KNIGHT]);
    int b_knights = popcount64(b->pieces[BLACK][KNIGHT]);
    int w_bishops = popcount64(b->pieces[WHITE][BISHOP]);
    int b_bishops = popcount64(b->pieces[BLACK][BISHOP]);

    // Bare kings (K vs K)
    if (w_knights + b_knights + w_bishops + b_bishops == 0) return 1;

    // King + minor vs King (K+N vs K, K+B vs K)
    if (w_knights + w_bishops == 1 && b_knights + b_bishops == 0) return 1;
    if (b_knights + b_bishops == 1 && w_knights + w_bishops == 0) return 1;

    // King + Bishop vs King + Bishop on the same color
    if (w_knights == 0 && b_knights == 0 && w_bishops == 1 && b_bishops == 1) {
        constexpr uint64_t DARK_SQUARES = 0xAA55AA55AA55AA55ULL;
        bool w_dark = (b->pieces[WHITE][BISHOP] & DARK_SQUARES) != 0;
        bool b_dark = (b->pieces[BLACK][BISHOP] & DARK_SQUARES) != 0;
        if (w_dark == b_dark) return 1; // Same square color: automatic draw
    }

    return 0;
}

EXPORT int native_is_claimable_draw(NativeBoard* b) {
    return (native_can_claim_threefold_repetition(b) || native_can_claim_fifty_moves(b)) ? 1 : 0;
}

EXPORT int native_is_automatic_draw(const NativeBoard* b) {
    return (native_is_fivefold_repetition(b) || native_is_seventyfive_moves(b) || native_is_insufficient_material(b)) ? 1 : 0;
}

// ============================================================================
// Static Evaluation Function (Matching Python Janus Baseline)
// ============================================================================

static const int MG_PIECE_VALUES[6] = { 100, 320, 330, 500, 900, 20000 };
static const int EG_PIECE_VALUES[6] = { 100, 320, 330, 500, 900, 20000 };

static const int MG_PAWN_TABLE[64] = {
      0,   0,   0,   0,   0,   0,   0,   0,
     50,  50,  50,  50,  50,  50,  50,  50,
     10,  10,  20,  30,  30,  20,  10,  10,
      5,   5,  10,  25,  25,  10,   5,   5,
      0,   0,   0,  20,  20,   0,   0,   0,
      5,  -5, -10,   0,   0, -10,  -5,   5,
      5,  10,  10, -20, -20,  10,  10,   5,
      0,   0,   0,   0,   0,   0,   0,   0
};

static const int MG_KNIGHT_TABLE[64] = {
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20,   0,   0,   0,   0, -20, -40,
    -30,   0,  10,  15,  15,  10,   0, -30,
    -30,   5,  15,  20,  20,  15,   5, -30,
    -30,   0,  15,  20,  20,  15,   0, -30,
    -30,   5,  10,  15,  15,  10,   5, -30,
    -40, -20,   0,   5,   5,   0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50
};

static const int MG_BISHOP_TABLE[64] = {
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -10,   0,   5,  10,  10,   5,   0, -10,
    -10,   5,   5,  10,  10,   5,   5, -10,
    -10,   0,  10,  10,  10,  10,   0, -10,
    -10,  10,  10,  10,  10,  10,  10, -10,
    -10,   5,   0,   0,   0,   0,   5, -10,
    -20, -10, -10, -10, -10, -10, -10, -20
};

static const int MG_ROOK_TABLE[64] = {
      0,   0,   0,   0,   0,   0,   0,   0,
      5,  10,  10,  10,  10,  10,  10,   5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
     -5,   0,   0,   0,   0,   0,   0,  -5,
      0,   0,   0,   5,   5,   0,   0,   0
};

static const int MG_QUEEN_TABLE[64] = {
    -20, -10, -10,  -5,  -5, -10, -10, -20,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -10,   0,   5,   5,   5,   5,   0, -10,
     -5,   0,   5,   5,   5,   5,   0,  -5,
      0,   0,   5,   5,   5,   5,   0,  -5,
    -10,   5,   5,   5,   5,   5,   0, -10,
    -10,   0,   5,   0,   0,   0,   0, -10,
    -20, -10, -10,  -5,  -5, -10, -10, -20
};

static const int MG_KING_TABLE[64] = {
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
     20,  20,   0,   0,   0,   0,  20,  20,
     20,  30,  10,   0,   0,  10,  30,  20
};

static inline int mirror_sq(int sq) {
    return (7 - (sq / 8)) * 8 + (sq % 8);
}

EXPORT int native_evaluate(const NativeBoard* b) {
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
}

// Move Ordering Score (K0 / N5 policy)
static int score_move_for_ordering(const NativeBoard* b, uint16_t m, uint16_t tt_move, int ply) {
    if (m == tt_move) return 10000000;

    int flag = move_flag(m);
    if (flag == 3) { // Promotion
        int promo = move_promo(m);
        return (promo == 3) ? 900000 : 800000;
    }

    int to = move_to(m);
    int from = move_from(m);
    int them = 1 - b->side_to_move;

    // Check if capture
    int victim = NO_PIECE;
    if (flag == 2) { // EP
        victim = PAWN;
    } else {
        for (int p = 0; p < 6; p++) {
            if (b->pieces[them][p] & (1ULL << to)) {
                victim = p;
                break;
            }
        }
    }

    if (victim != NO_PIECE) {
        int attacker = NO_PIECE;
        for (int p = 0; p < 6; p++) {
            if (b->pieces[b->side_to_move][p] & (1ULL << from)) {
                attacker = p;
                break;
            }
        }
        return 100000 + (victim * 10) - attacker;
    }

    // Killer Moves (Quiet moves only)
    if (g_use_killer_ordering && ply >= 0 && ply < MAX_PLY) {
        if (m == g_killer_moves[ply][0]) return 90000;
        if (m == g_killer_moves[ply][1]) return 80000;
    }

    // History Heuristic (Quiet moves only)
    if (g_use_history_ordering) {
        int side = b->side_to_move;
        int h = g_history_table[side][from][to];
        if (h > 0) {
            return std::min(MAX_HISTORY_SCORE, h);
        }
    }

    return 0; // Quiet moves
}

// ============================================================================
// Quiescence Search with Delta Pruning
// ============================================================================

static int quiescence(NativeBoard* b, int alpha, int beta, uint64_t& nodes, std::chrono::steady_clock::time_point deadline, bool& aborted) {
    nodes++;

    if ((nodes & 2047) == 0) {
        if (std::chrono::steady_clock::now() >= deadline) {
            aborted = true;
            return 0;
        }
    }

    int stand_pat = native_evaluate(b);
    if (stand_pat >= beta) return beta;
    if (stand_pat > alpha) alpha = stand_pat;

    // Delta pruning margin: 900 (Queen) + 200 safety
    constexpr int DELTA_MARGIN = 1100;
    if (stand_pat + DELTA_MARGIN < alpha) {
        return alpha;
    }

    uint16_t moves[MAX_MOVES];
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
            caps[n_caps++] = { m, score_move_for_ordering(b, m, 0, 0) };
        }
    }

    std::sort(caps, caps + n_caps, [](const ScoredMove& a, const ScoredMove& b) {
        return a.score > b.score;
    });

    UndoInfo undo;
    for (int i = 0; i < n_caps; i++) {
        if (!native_make_move(b, caps[i].m, &undo)) continue;
        int score = -quiescence(b, -beta, -alpha, nodes, deadline, aborted);
        native_unmake_move(b, caps[i].m, &undo);

        if (aborted) return 0;
        if (score >= beta) return beta;
        if (score > alpha) alpha = score;
    }

    return alpha;
}

// ============================================================================
// Alpha-Beta Negamax Search with TT, PV and Draw Detection
// ============================================================================

static int negamax(
    NativeBoard* b,
    int depth,
    int alpha,
    int beta,
    int ply,
    uint64_t& nodes,
    std::chrono::steady_clock::time_point deadline,
    bool& aborted,
    uint16_t* out_best_move
) {
    nodes++;

    if ((nodes & 2047) == 0) {
        if (std::chrono::steady_clock::now() >= deadline) {
            aborted = true;
            return 0;
        }
    }

    g_pv_len[ply] = 0;

    // Draw Adjudication in Search Tree (Phase B)
    if (ply > 0) {
        // 1. Fifty-move rule
        if (b->halfmove_clock >= 100) return 0;

        // 2. Insufficient material
        if (native_is_insufficient_material(b)) return 0;

        // 3. Repetition in tree: if the current position already occurred in game history or search path
        if (native_is_repetition(b, 2)) return 0;
    }

    // Leaf evaluation
    if (depth <= 0 || ply >= MAX_SEARCH_PLY - 1) {
        return quiescence(b, alpha, beta, nodes, deadline, aborted);
    }

    // TT Probe
    uint64_t key = b->zobrist_key;
    size_t tt_idx = key % TT_SIZE;
    TTEntry& entry = g_tt[tt_idx];
    uint16_t tt_move = 0;

    if (entry.key == key) {
        tt_move = entry.best_move;
        if (entry.depth >= depth && ply > 0) {
            int tt_score = score_from_tt(entry.score, ply);
            if (entry.flag == TT_EXACT) return tt_score;
            if (entry.flag == TT_LOWER && tt_score >= beta) return tt_score;
            if (entry.flag == TT_UPPER && tt_score <= alpha) return tt_score;
        }
    }

    uint16_t moves[MAX_MOVES];
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
        uint16_t m = scored_moves[i].m;
        if (!native_make_move(b, m, &undo)) continue;

        moves_searched++;

        // Push to game history stack for tree repetition detection
        native_push_history(b->zobrist_key);

        int child_depth = depth - 1;
        int score = 0;
        uint16_t child_best = 0;

        // LMR Eligibility Check (10 Invariants)
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
                g_lmr_reduced_moves++;

                score = -negamax(b, reduced_depth, -beta, -alpha, ply + 1, nodes, deadline, aborted, &child_best);

                if (score > alpha && !aborted) {
                    g_lmr_researches++;
                    score = -negamax(b, child_depth, -beta, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
                }
            } else {
                score = -negamax(b, child_depth, -beta, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
            }
            g_pvs_full_window_searches++;
        } else {
            // PVS Subsequent moves: Null-window search [-alpha - 1, -alpha]
            if (is_lmr_eligible) {
                g_lmr_eligible_moves++;
                int reduction = g_lmr_base_reduction;
                int reduced_depth = std::max(1, child_depth - reduction);
                g_lmr_reduced_moves++;
                g_pvs_null_window_searches++;

                // Stage 1: Reduced Depth Null-Window Probe
                score = -negamax(b, reduced_depth, -alpha - 1, -alpha, ply + 1, nodes, deadline, aborted, &child_best);

                // Stage 2: Full Depth Null-Window Re-search if reduced probe beat alpha
                if (score > alpha && !aborted) {
                    g_lmr_researches++;
                    g_pvs_null_window_searches++;
                    score = -negamax(b, child_depth, -alpha - 1, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
                }
            } else {
                // Non-LMR move: Full depth null-window probe
                g_pvs_null_window_searches++;
                score = -negamax(b, child_depth, -alpha - 1, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
            }

            // Stage 3: Full-Window PVS Re-Search
            // If the null-window probe returned score > alpha and score < beta, re-search with full window [-beta, -alpha]
            if (score > alpha && score < beta && !aborted) {
                g_pvs_researches++;
                g_pvs_full_window_searches++;
                score = -negamax(b, child_depth, -beta, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
            }
        }

        native_pop_history();
        native_unmake_move(b, m, &undo);

        if (aborted) return 0;

        if (score > best_score) {
            best_score = score;
            best_move = m;
        }
        if (score > alpha) {
            alpha = score;

            // Update PV Table
            g_pv_table[ply][0] = m;
            for (int j = 0; j < g_pv_len[ply + 1]; j++) {
                g_pv_table[ply][j + 1] = g_pv_table[ply + 1][j];
            }
            g_pv_len[ply] = g_pv_len[ply + 1] + 1;
        }
        if (alpha >= beta) {
            g_ordering_total_cutoffs++;
            g_ordering_sum_cutoff_index += moves_searched;
            if (moves_searched == 1) g_ordering_cutoff_move_1++;
            else if (moves_searched == 2) g_ordering_cutoff_move_2++;
            else if (moves_searched == 3) g_ordering_cutoff_move_3++;
            else g_ordering_cutoff_move_4plus++;

            if (m == tt_move) g_ordering_cutoff_tt++;

            bool is_quiet = (undo.captured_piece == NO_PIECE) && (move_flag(m) != 3);
            if (is_quiet) {
                g_ordering_cutoff_quiet++;
                // Killer update
                if (g_use_killer_ordering && ply >= 0 && ply < MAX_PLY) {
                    if (m == g_killer_moves[ply][0]) {
                        g_ordering_cutoff_killer1++;
                    } else if (m == g_killer_moves[ply][1]) {
                        g_ordering_cutoff_killer2++;
                    } else {
                        g_killer_moves[ply][1] = g_killer_moves[ply][0];
                        g_killer_moves[ply][0] = m;
                    }
                }
                // History update
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
                }
            } else {
                g_ordering_cutoff_captures++;
            }

            if (is_lmr_eligible) {
                g_lmr_cutoffs++;
            }
            if (g_use_pvs) {
                g_pvs_cutoffs++;
            }
            break; // Beta cutoff
        }
    }

    if (out_best_move) *out_best_move = best_move;

    // Store TT entry with normalized mate scores and depth-preferred replacement
    if (!aborted) {
        uint8_t flag = TT_EXACT;
        if (best_score <= orig_alpha) flag = TT_UPPER;
        else if (best_score >= beta) flag = TT_LOWER;

        // Depth-preferred replacement with aging
        if (entry.key != key || depth >= entry.depth || entry.age != g_tt_age) {
            entry.key = key;
            entry.score = (int16_t)score_to_tt(best_score, ply);
            entry.depth = (int8_t)depth;
            entry.flag = flag;
            entry.age = g_tt_age;
            entry.best_move = best_move;
        }
    }

    return best_score;
}

// ============================================================================
// Top-Level Iterative Deepening Search
// ============================================================================

EXPORT int native_search(
    NativeBoard* b,
    int max_depth,
    double time_limit_sec,
    NativeSearchResult* out_res
) {
    init_attacks();
    std::memset(g_killer_moves, 0, sizeof(g_killer_moves));
    if (g_use_history_ordering) {
        for (int s = 0; s < SIDES; s++) {
            for (int f = 0; f < SQUARES; f++) {
                for (int t = 0; t < SQUARES; t++) {
                    g_history_table[s][f][t] /= 2;
                }
            }
        }
    }

    auto start_time = std::chrono::steady_clock::now();
    auto deadline = start_time + std::chrono::milliseconds(static_cast<int64_t>(time_limit_sec * 1000.0));

    uint64_t total_nodes = 0;
    out_res->depth = 0;
    out_res->nodes = 0;
    out_res->score = 0;
    out_res->best_move = 0;
    out_res->elapsed_seconds = 0.0;
    out_res->pv_length = 0;

    bool aborted = false;
    g_tt_age++;

    for (int d = 1; d <= max_depth; d++) {
        uint16_t iter_best_move = 0;
        int score = negamax(b, d, -INF, INF, 0, total_nodes, deadline, aborted, &iter_best_move);

        if (aborted) break;

        auto now = std::chrono::steady_clock::now();
        std::chrono::duration<double> dur = now - start_time;

        out_res->depth = d;
        out_res->best_move = iter_best_move;
        out_res->score = score;
        out_res->nodes = total_nodes;
        out_res->elapsed_seconds = dur.count();

        // Copy PV
        out_res->pv_length = g_pv_len[0];
        for (int i = 0; i < g_pv_len[0]; i++) {
            out_res->pv[i] = g_pv_table[0][i];
        }

        if (dur.count() >= time_limit_sec) break;
    }

    auto final_time = std::chrono::steady_clock::now();
    std::chrono::duration<double> total_dur = final_time - start_time;
    out_res->elapsed_seconds = total_dur.count();
    out_res->nodes = total_nodes;

    return 1;
}

// ============================================================================
// LMR Configuration & Telemetry API (Phase 3 v0.52)
// ============================================================================

EXPORT void native_set_lmr_options(bool use_lmr, int min_depth, int move_threshold, int base_reduction) {
    g_use_lmr = use_lmr;
    g_lmr_min_depth = min_depth;
    g_lmr_move_threshold = move_threshold;
    g_lmr_base_reduction = base_reduction;
}

EXPORT void native_reset_lmr_telemetry() {
    g_lmr_eligible_moves = 0;
    g_lmr_reduced_moves = 0;
    g_lmr_researches = 0;
    g_lmr_cutoffs = 0;
}

EXPORT void native_clear_tt() {
    std::memset(g_tt, 0, sizeof(g_tt));
}

EXPORT void native_get_lmr_telemetry(uint64_t* out_arr) {
    if (out_arr) {
        out_arr[0] = g_lmr_eligible_moves;
        out_arr[1] = g_lmr_reduced_moves;
        out_arr[2] = g_lmr_researches;
        out_arr[3] = g_lmr_cutoffs;
    }
}

// ============================================================================
// PVS Configuration & Telemetry API (Phase 3 v0.53)
// ============================================================================

EXPORT void native_set_pvs_options(bool use_pvs) {
    g_use_pvs = use_pvs;
}

EXPORT void native_reset_pvs_telemetry() {
    g_pvs_full_window_searches = 0;
    g_pvs_null_window_searches = 0;
    g_pvs_researches = 0;
    g_pvs_cutoffs = 0;
}

EXPORT void native_get_pvs_telemetry(uint64_t* out_arr) {
    if (out_arr) {
        out_arr[0] = g_pvs_full_window_searches;
        out_arr[1] = g_pvs_null_window_searches;
        out_arr[2] = g_pvs_researches;
        out_arr[3] = g_pvs_cutoffs;
    }
}

// ============================================================================
// Move Ordering Configuration & Telemetry API (Phase 2 & 3 v0.54)
// ============================================================================

EXPORT void native_set_ordering_options(bool use_killer, bool use_history) {
    g_use_killer_ordering = use_killer;
    g_use_history_ordering = use_history;
}

EXPORT void native_clear_killers() {
    std::memset(g_killer_moves, 0, sizeof(g_killer_moves));
}

EXPORT void native_clear_history_heuristic() {
    std::memset(g_history_table, 0, sizeof(g_history_table));
}

EXPORT void native_reset_ordering_telemetry() {
    g_ordering_total_cutoffs = 0;
    g_ordering_sum_cutoff_index = 0;
    g_ordering_cutoff_move_1 = 0;
    g_ordering_cutoff_move_2 = 0;
    g_ordering_cutoff_move_3 = 0;
    g_ordering_cutoff_move_4plus = 0;
    g_ordering_cutoff_tt = 0;
    g_ordering_cutoff_killer1 = 0;
    g_ordering_cutoff_killer2 = 0;
    g_ordering_cutoff_history = 0;
    g_ordering_cutoff_captures = 0;
    g_ordering_cutoff_quiet = 0;
}

EXPORT void native_get_ordering_telemetry(uint64_t* out_arr) {
    if (out_arr) {
        out_arr[0] = g_ordering_total_cutoffs;
        out_arr[1] = g_ordering_sum_cutoff_index;
        out_arr[2] = g_ordering_cutoff_move_1;
        out_arr[3] = g_ordering_cutoff_move_2;
        out_arr[4] = g_ordering_cutoff_move_3;
        out_arr[5] = g_ordering_cutoff_move_4plus;
        out_arr[6] = g_ordering_cutoff_tt;
        out_arr[7] = g_ordering_cutoff_killer1;
        out_arr[8] = g_ordering_cutoff_killer2;
        out_arr[9] = g_ordering_cutoff_history;
        out_arr[10] = g_ordering_cutoff_captures;
        out_arr[11] = g_ordering_cutoff_quiet;
    }
}

EXPORT uint16_t native_get_killer(int ply, int slot) {
    if (ply >= 0 && ply < MAX_PLY && slot >= 0 && slot < KILLER_SLOTS) {
        return g_killer_moves[ply][slot];
    }
    return 0;
}

EXPORT int native_get_history_score(int side, int from, int to) {
    if (side >= 0 && side < SIDES && from >= 0 && from < SQUARES && to >= 0 && to < SQUARES) {
        return g_history_table[side][from][to];
    }
    return 0;
}

// ============================================================================
// Formatting & UCI Helpers
// ============================================================================

EXPORT void native_move_to_uci(uint16_t m, char* out_str) {
    int from = move_from(m);
    int to = move_to(m);
    int flag = move_flag(m);
    int promo = move_promo(m);

    out_str[0] = 'a' + (from % 8);
    out_str[1] = '1' + (from / 8);
    out_str[2] = 'a' + (to % 8);
    out_str[3] = '1' + (to / 8);
    out_str[4] = '\0';

    if (flag == 3) {
        const char pr_chars[4] = { 'n', 'b', 'r', 'q' };
        out_str[4] = pr_chars[promo];
        out_str[5] = '\0';
    }
}

EXPORT uint16_t native_parse_uci(NativeBoard* b, const char* str) {
    if (!str || std::strlen(str) < 4) return 0;
    int f_from = str[0] - 'a';
    int r_from = str[1] - '1';
    int f_to = str[2] - 'a';
    int r_to = str[3] - '1';
    if (f_from < 0 || f_from > 7 || r_from < 0 || r_from > 7 ||
        f_to < 0 || f_to > 7 || r_to < 0 || r_to > 7) {
        return 0;
    }
    int from = r_from * 8 + f_from;
    int to = r_to * 8 + f_to;

    int promo_piece = -1;
    if (str[4] == 'n' || str[4] == 'N') promo_piece = 0;
    else if (str[4] == 'b' || str[4] == 'B') promo_piece = 1;
    else if (str[4] == 'r' || str[4] == 'R') promo_piece = 2;
    else if (str[4] == 'q' || str[4] == 'Q') promo_piece = 3;

    uint16_t moves[MAX_MOVES];
    int n = native_generate_legal_moves(b, moves);
    for (int i = 0; i < n; i++) {
        uint16_t m = moves[i];
        if (move_from(m) == from && move_to(m) == to) {
            if (move_flag(m) == 3) {
                if (move_promo(m) == promo_piece) return m;
            } else {
                return m;
            }
        }
    }
    return 0;
}

// ============================================================================
// Standalone UCI Engine Protocol Loop (Phase E)
// ============================================================================

static void uci_loop() {
    setvbuf(stdin, NULL, _IONBF, 0);
    setvbuf(stdout, NULL, _IONBF, 0);
    std::cout << std::unitbuf;

    native_init();
    NativeBoard board;
    const char* STARTPOS_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
    native_set_fen(STARTPOS_FEN, &board);

    std::string line;
    while (std::getline(std::cin, line)) {
        std::istringstream iss(line);
        std::string cmd;
        iss >> cmd;

        if (cmd == "uci") {
            std::cout << "id name Janus 0.55 Native" << std::endl;
            std::cout << "id author Project Janus Team" << std::endl;
            std::cout << "option name UseKillerOrdering type check default true" << std::endl;
            std::cout << "option name UseHistoryOrdering type check default true" << std::endl;
            std::cout << "option name UsePVS type check default false" << std::endl;
            std::cout << "option name UseLMR type check default true" << std::endl;
            std::cout << "option name LMRMinDepth type spin default 3 min 2 max 8" << std::endl;
            std::cout << "option name LMRMoveThreshold type spin default 4 min 2 max 16" << std::endl;
            std::cout << "option name LMRBaseReduction type spin default 1 min 1 max 3" << std::endl;
            std::cout << "uciok" << std::endl;
        } else if (cmd == "isready") {
            std::cout << "readyok" << std::endl;
        } else if (cmd == "setoption") {
            std::string name_tok, opt_name;
            iss >> name_tok >> opt_name;
            if (name_tok == "name") {
                std::string val_tok, opt_val;
                if (iss >> val_tok) {
                    if (val_tok == "value") {
                        iss >> opt_val;
                    } else {
                        opt_val = val_tok;
                    }
                }
                if (opt_name == "UseKillerOrdering") {
                    if (opt_val.empty() || opt_val == "true" || opt_val == "1") {
                        g_use_killer_ordering = true;
                    } else {
                        g_use_killer_ordering = false;
                    }
                } else if (opt_name == "UseHistoryOrdering") {
                    if (opt_val.empty() || opt_val == "true" || opt_val == "1") {
                        g_use_history_ordering = true;
                    } else {
                        g_use_history_ordering = false;
                    }
                } else if (opt_name == "UsePVS") {
                    if (opt_val.empty() || opt_val == "true" || opt_val == "1") {
                        g_use_pvs = true;
                    } else {
                        g_use_pvs = false;
                    }
                } else if (opt_name == "UseLMR") {
                    if (opt_val.empty() || opt_val == "true" || opt_val == "1") {
                        g_use_lmr = true;
                    } else {
                        g_use_lmr = false;
                    }
                } else if (opt_name == "LMRMinDepth" && !opt_val.empty()) {
                    g_lmr_min_depth = std::stoi(opt_val);
                } else if (opt_name == "LMRMoveThreshold" && !opt_val.empty()) {
                    g_lmr_move_threshold = std::stoi(opt_val);
                } else if (opt_name == "LMRBaseReduction" && !opt_val.empty()) {
                    g_lmr_base_reduction = std::stoi(opt_val);
                }
            }
        } else if (cmd == "ucinewgame") {
            native_reset_history();
            native_clear_killers();
            native_clear_history_heuristic();
            native_reset_ordering_telemetry();
            std::memset(g_tt, 0, sizeof(g_tt));
            native_reset_lmr_telemetry();
            native_reset_pvs_telemetry();
            native_set_fen(STARTPOS_FEN, &board);
        } else if (cmd == "position") {
            std::string type;
            iss >> type;
            if (type == "startpos") {
                native_set_fen(STARTPOS_FEN, &board);
                native_reset_history();
                native_push_history(board.zobrist_key);

                std::string moves_token;
                if (iss >> moves_token && moves_token == "moves") {
                    std::string m_str;
                    while (iss >> m_str) {
                        uint16_t m = native_parse_uci(&board, m_str.c_str());
                        if (m != 0) {
                            UndoInfo undo;
                            native_make_move(&board, m, &undo);
                            native_push_history(board.zobrist_key);
                        }
                    }
                }
            } else if (type == "fen") {
                std::string fen_part, fen;
                while (iss >> fen_part && fen_part != "moves") {
                    if (!fen.empty()) fen += " ";
                    fen += fen_part;
                }
                native_set_fen(fen.c_str(), &board);
                native_reset_history();
                native_push_history(board.zobrist_key);

                if (fen_part == "moves") {
                    std::string m_str;
                    while (iss >> m_str) {
                        uint16_t m = native_parse_uci(&board, m_str.c_str());
                        if (m != 0) {
                            UndoInfo undo;
                            native_make_move(&board, m, &undo);
                            native_push_history(board.zobrist_key);
                        }
                    }
                }
            }
        } else if (cmd == "go") {
            std::string subcmd;
            int max_depth = 64;
            double time_limit = 1000.0;
            int wtime = -1, btime = -1, winc = 0, binc = 0, movetime = -1;

            while (iss >> subcmd) {
                if (subcmd == "depth") iss >> max_depth;
                else if (subcmd == "movetime") { iss >> movetime; time_limit = movetime / 1000.0; }
                else if (subcmd == "wtime") iss >> wtime;
                else if (subcmd == "btime") iss >> btime;
                else if (subcmd == "winc") iss >> winc;
                else if (subcmd == "binc") iss >> binc;
            }

            // Time Management Policy
            if (movetime < 0) {
                int my_time = (board.side_to_move == WHITE) ? wtime : btime;
                int my_inc = (board.side_to_move == WHITE) ? winc : binc;

                if (my_time > 0) {
                    // Fischer time allocation: (time + 40*inc) / 40, safety margin 50ms
                    double alloc_ms = (my_time + 40.0 * my_inc) / 40.0;
                    if (alloc_ms > my_time - 50.0) alloc_ms = std::max(10.0, my_time - 50.0);
                    time_limit = alloc_ms / 1000.0;
                }
            }

            NativeSearchResult res;
            native_search(&board, max_depth, time_limit, &res);

            char best_uci[16] = {0};
            if (res.best_move != 0) {
                native_move_to_uci(res.best_move, best_uci);
            } else {
                // If search aborted before finding move, pick any legal move
                uint16_t lmoves[MAX_MOVES];
                int ln = native_generate_legal_moves(&board, lmoves);
                if (ln > 0) native_move_to_uci(lmoves[0], best_uci);
                else std::strcpy(best_uci, "0000");
            }

            // Print info
            std::cout << "info depth " << res.depth
                      << " score cp " << res.score
                      << " nodes " << res.nodes
                      << " nps " << (res.elapsed_seconds > 0 ? (int)(res.nodes / res.elapsed_seconds) : 0)
                      << " time " << (int)(res.elapsed_seconds * 1000)
                      << " pv";
            for (int pvi = 0; pvi < res.pv_length; pvi++) {
                char pv_str[16];
                native_move_to_uci(res.pv[pvi], pv_str);
                std::cout << " " << pv_str;
            }
            std::cout << std::endl;

            std::cout << "bestmove " << best_uci << std::endl;
        } else if (cmd == "quit") {
            break;
        }
    }
}

#ifndef _WINDLL
int main() {
    uci_loop();
    return 0;
}
#endif
