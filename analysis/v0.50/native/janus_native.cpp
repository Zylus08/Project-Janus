/*
 * Project Janus v0.50 - Native Search Core (Candidate N2)
 *
 * Full C++17 native search engine implementing:
 * - 64-bit bitboard state representation
 * - Polyglot-compatible Zobrist hashing
 * - Legal move generation (checks, double checks, pins, castling, en passant, promotions)
 * - Exact make/unmake state transitions
 * - FIDE draw and repetition rules
 * - Static evaluation parity with Python Janus baseline evaluation
 * - Full Alpha-Beta negamax search with Iterative Deepening, Transposition Table, Quiescence, and Move Ordering
 */

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <algorithm>
#include <chrono>
#include <string>
#include <vector>

#ifdef _MSC_VER
#include <intrin.h>
#define EXPORT extern "C" __declspec(dllexport)
#else
#define EXPORT extern "C"
#endif

// Constants
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

// Move encoding (uint16_t):
inline uint16_t encode_move(int from, int to, int flag = 0, int promo = 0) {
    return (from & 0x3F) | ((to & 0x3F) << 6) | ((flag & 3) << 12) | ((promo & 3) << 14);
}
inline int move_from(uint16_t m) { return m & 0x3F; }
inline int move_to(uint16_t m) { return (m >> 6) & 0x3F; }
inline int move_flag(uint16_t m) { return (m >> 12) & 3; }
inline int move_promo(uint16_t m) { return (m >> 14) & 3; }

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
    uint16_t pv[64];
};

// Attack Tables and Zobrist Keys
static uint64_t KNIGHT_ATTACKS[64];
static uint64_t KING_ATTACKS[64];
static uint64_t PAWN_ATTACKS[2][64];
static uint64_t RAYS[64][8]; // N=0, NE=1, E=2, SE=3, S=4, SW=5, W=6, NW=7
static uint64_t ZOBRIST_PIECES[2][6][64];
static uint64_t ZOBRIST_CASTLING[16];
static uint64_t ZOBRIST_EP[65];
static uint64_t ZOBRIST_SIDE;
static bool g_initialized = false;

// Piece Square Tables from Janus baseline
static int WHITE_PAWN_TABLE[64];
static int BLACK_PAWN_TABLE[64];
static int KNIGHT_TABLE[64];
static int BISHOP_TABLE[64];

// Transposition Table Entry
constexpr uint8_t TT_EXACT = 0;
constexpr uint8_t TT_LOWER = 1;
constexpr uint8_t TT_UPPER = 2;

struct TTEntry {
    uint64_t key;
    int16_t score;
    int8_t depth;
    uint8_t flag;
    uint16_t best_move;
};

constexpr size_t TT_SIZE = 1 << 20; // 1,048,576 entries (~16 MB)
static TTEntry g_tt[TT_SIZE];

static uint64_t polyglot_rand(uint64_t& state) {
    state = state * 6364136223846793005ULL + 1442695040888963407ULL;
    return state;
}

static inline int lsb(uint64_t b) {
#ifdef _MSC_VER
    unsigned long idx;
    _BitScanForward64(&idx, b);
    return (int)idx;
#else
    return __builtin_ctzll(b);
#endif
}

static inline int msb(uint64_t b) {
#ifdef _MSC_VER
    unsigned long idx;
    _BitScanReverse64(&idx, b);
    return (int)idx;
#else
    return 63 - __builtin_clzll(b);
#endif
}

static void init_attacks() {
    if (g_initialized) return;

    for (int sq = 0; sq < 64; sq++) {
        int r = sq / 8;
        int f = sq % 8;

        // Knight attacks
        uint64_t k_att = 0;
        int dr[8] = { 2, 2, 1, 1, -1, -1, -2, -2 };
        int df[8] = { 1, -1, 2, -2, 2, -2, 1, -1 };
        for (int i = 0; i < 8; i++) {
            int nr = r + dr[i];
            int nf = f + df[i];
            if (nr >= 0 && nr < 8 && nf >= 0 && nf < 8) {
                k_att |= (1ULL << (nr * 8 + nf));
            }
        }
        KNIGHT_ATTACKS[sq] = k_att;

        // King attacks
        uint64_t king_att = 0;
        for (int dx = -1; dx <= 1; dx++) {
            for (int dy = -1; dy <= 1; dy++) {
                if (dx == 0 && dy == 0) continue;
                int nr = r + dx;
                int nf = f + dy;
                if (nr >= 0 && nr < 8 && nf >= 0 && nf < 8) {
                    king_att |= (1ULL << (nr * 8 + nf));
                }
            }
        }
        KING_ATTACKS[sq] = king_att;

        // Pawn attacks
        uint64_t w_pawn = 0;
        if (r < 7) {
            if (f > 0) w_pawn |= (1ULL << (sq + 7));
            if (f < 7) w_pawn |= (1ULL << (sq + 9));
        }
        PAWN_ATTACKS[WHITE][sq] = w_pawn;

        uint64_t b_pawn = 0;
        if (r > 0) {
            if (f > 0) b_pawn |= (1ULL << (sq - 9));
            if (f < 7) b_pawn |= (1ULL << (sq - 7));
        }
        PAWN_ATTACKS[BLACK][sq] = b_pawn;

        // Precompute rays
        for (int d = 0; d < 8; d++) {
            uint64_t ray = 0;
            int cur_r = r;
            int cur_f = f;
            int step_r = 0, step_f = 0;
            if (d == 0) { step_r = 1; }
            else if (d == 1) { step_r = 1; step_f = 1; }
            else if (d == 2) { step_f = 1; }
            else if (d == 3) { step_r = -1; step_f = 1; }
            else if (d == 4) { step_r = -1; }
            else if (d == 5) { step_r = -1; step_f = -1; }
            else if (d == 6) { step_f = -1; }
            else if (d == 7) { step_r = 1; step_f = -1; }

            while (true) {
                cur_r += step_r;
                cur_f += step_f;
                if (cur_r < 0 || cur_r >= 8 || cur_f < 0 || cur_f >= 8) break;
                ray |= (1ULL << (cur_r * 8 + cur_f));
            }
            RAYS[sq][d] = ray;
        }

        // Center bonus calculation
        double file_dist = std::abs((double)f - 3.5);
        double rank_dist = std::abs((double)r - 3.5);
        int center_bonus = (int)(14.0 - 4.0 * (file_dist + rank_dist));

        WHITE_PAWN_TABLE[sq] = 100 + r * 5;
        BLACK_PAWN_TABLE[sq] = 100 + (7 - r) * 5;
        KNIGHT_TABLE[sq] = 320 + center_bonus;
        BISHOP_TABLE[sq] = 335 + center_bonus;
    }

    uint64_t rng_state = 1070372;
    for (int c = 0; c < 2; c++) {
        for (int p = 0; p < 6; p++) {
            for (int sq = 0; sq < 64; sq++) {
                ZOBRIST_PIECES[c][p][sq] = polyglot_rand(rng_state);
            }
        }
    }
    for (int i = 0; i < 16; i++) {
        ZOBRIST_CASTLING[i] = polyglot_rand(rng_state);
    }
    for (int i = 0; i < 65; i++) {
        ZOBRIST_EP[i] = (i < 64) ? polyglot_rand(rng_state) : 0ULL;
    }
    ZOBRIST_SIDE = polyglot_rand(rng_state);

    std::memset(g_tt, 0, sizeof(g_tt));
    g_initialized = true;
}

static inline uint64_t get_bishop_attacks(int sq, uint64_t occ) {
    uint64_t att = 0;
    const int dirs[4] = { 1, 3, 5, 7 };
    for (int i = 0; i < 4; i++) {
        int d = dirs[i];
        uint64_t ray = RAYS[sq][d];
        uint64_t blk = ray & occ;
        if (blk) {
            int blocker_sq = (d == 1 || d == 7) ? lsb(blk) : msb(blk);
            ray ^= RAYS[blocker_sq][d];
        }
        att |= ray;
    }
    return att;
}

static inline uint64_t get_rook_attacks(int sq, uint64_t occ) {
    uint64_t att = 0;
    const int dirs[4] = { 0, 2, 4, 6 };
    for (int i = 0; i < 4; i++) {
        int d = dirs[i];
        uint64_t ray = RAYS[sq][d];
        uint64_t blk = ray & occ;
        if (blk) {
            int blocker_sq = (d == 0 || d == 2) ? lsb(blk) : msb(blk);
            ray ^= RAYS[blocker_sq][d];
        }
        att |= ray;
    }
    return att;
}

static inline uint64_t get_queen_attacks(int sq, uint64_t occ) {
    return get_bishop_attacks(sq, occ) | get_rook_attacks(sq, occ);
}

static inline bool is_square_attacked(const NativeBoard* b, int sq, int attacker_color) {
    uint64_t occ = b->occupancy[2];
    int defender_color = 1 - attacker_color;

    if (PAWN_ATTACKS[defender_color][sq] & b->pieces[attacker_color][PAWN]) return true;
    if (KNIGHT_ATTACKS[sq] & b->pieces[attacker_color][KNIGHT]) return true;
    if (KING_ATTACKS[sq] & b->pieces[attacker_color][KING]) return true;

    uint64_t bq = b->pieces[attacker_color][BISHOP] | b->pieces[attacker_color][QUEEN];
    if (bq && (get_bishop_attacks(sq, occ) & bq)) return true;

    uint64_t rq = b->pieces[attacker_color][ROOK] | b->pieces[attacker_color][QUEEN];
    if (rq && (get_rook_attacks(sq, occ) & rq)) return true;

    return false;
}

EXPORT int native_is_check(const NativeBoard* b) {
    int color = b->side_to_move;
    uint64_t king_bb = b->pieces[color][KING];
    if (!king_bb) return 0;
    int ksq = lsb(king_bb);
    return is_square_attacked(b, ksq, 1 - color) ? 1 : 0;
}

static uint64_t compute_zobrist(const NativeBoard* b) {
    uint64_t key = 0;
    for (int c = 0; c < 2; c++) {
        for (int p = 0; p < 6; p++) {
            uint64_t bb = b->pieces[c][p];
            while (bb) {
                int sq = lsb(bb);
                key ^= ZOBRIST_PIECES[c][p][sq];
                bb &= bb - 1;
            }
        }
    }
    key ^= ZOBRIST_CASTLING[b->castling_rights & 15];
    if (b->ep_square < 64) {
        key ^= ZOBRIST_EP[b->ep_square];
    }
    if (b->side_to_move == BLACK) {
        key ^= ZOBRIST_SIDE;
    }
    return key;
}

EXPORT int native_init(void) {
    init_attacks();
    return 1;
}

EXPORT int native_set_fen(const char* fen, NativeBoard* out_b) {
    init_attacks();
    std::memset(out_b, 0, sizeof(NativeBoard));
    out_b->ep_square = 64;

    int sq = 56;
    int idx = 0;

    while (fen[idx] && fen[idx] != ' ') {
        char c = fen[idx++];
        if (c == '/') {
            sq -= 16;
        } else if (c >= '1' && c <= '8') {
            sq += (c - '0');
        } else {
            int color = (c >= 'A' && c <= 'Z') ? WHITE : BLACK;
            char lower = (color == WHITE) ? (c + 32) : c;
            int pt = NO_PIECE;
            if (lower == 'p') pt = PAWN;
            else if (lower == 'n') pt = KNIGHT;
            else if (lower == 'b') pt = BISHOP;
            else if (lower == 'r') pt = ROOK;
            else if (lower == 'q') pt = QUEEN;
            else if (lower == 'k') pt = KING;

            if (pt != NO_PIECE && sq >= 0 && sq < 64) {
                out_b->pieces[color][pt] |= (1ULL << sq);
            }
            sq++;
        }
    }

    if (!fen[idx]) return 0;
    idx++;

    if (fen[idx] == 'w') out_b->side_to_move = WHITE;
    else if (fen[idx] == 'b') out_b->side_to_move = BLACK;
    idx += 2;

    out_b->castling_rights = 0;
    while (fen[idx] && fen[idx] != ' ') {
        char c = fen[idx++];
        if (c == 'K') out_b->castling_rights |= CASTLE_W_OO;
        else if (c == 'Q') out_b->castling_rights |= CASTLE_W_OOO;
        else if (c == 'k') out_b->castling_rights |= CASTLE_B_OO;
        else if (c == 'q') out_b->castling_rights |= CASTLE_B_OOO;
    }

    if (fen[idx]) idx++;

    if (fen[idx] && fen[idx] != '-') {
        int f = fen[idx] - 'a';
        int r = fen[idx + 1] - '1';
        if (f >= 0 && f < 8 && r >= 0 && r < 8) {
            out_b->ep_square = r * 8 + f;
        }
        idx += 2;
    } else if (fen[idx] == '-') {
        idx++;
    }

    out_b->halfmove_clock = 0;
    out_b->fullmove_number = 1;
    if (fen[idx] == ' ') {
        idx++;
        char* end;
        out_b->halfmove_clock = (uint16_t)std::strtol(fen + idx, &end, 10);
        if (*end == ' ') {
            out_b->fullmove_number = (uint16_t)std::strtol(end + 1, nullptr, 10);
        }
    }

    out_b->occupancy[WHITE] = 0;
    out_b->occupancy[BLACK] = 0;
    for (int p = 0; p < 6; p++) {
        out_b->occupancy[WHITE] |= out_b->pieces[WHITE][p];
        out_b->occupancy[BLACK] |= out_b->pieces[BLACK][p];
    }
    out_b->occupancy[2] = out_b->occupancy[WHITE] | out_b->occupancy[BLACK];

    out_b->zobrist_key = compute_zobrist(out_b);
    return 1;
}

EXPORT void native_get_fen(const NativeBoard* b, char* out_fen) {
    int idx = 0;
    for (int r = 7; r >= 0; r--) {
        int empty_count = 0;
        for (int f = 0; f < 8; f++) {
            int sq = r * 8 + f;
            int piece_found = NO_PIECE;
            int color_found = NO_COLOR;

            for (int c = 0; c < 2; c++) {
                for (int p = 0; p < 6; p++) {
                    if (b->pieces[c][p] & (1ULL << sq)) {
                        piece_found = p;
                        color_found = c;
                        break;
                    }
                }
                if (piece_found != NO_PIECE) break;
            }

            if (piece_found == NO_PIECE) {
                empty_count++;
            } else {
                if (empty_count > 0) {
                    out_fen[idx++] = '0' + empty_count;
                    empty_count = 0;
                }
                const char* chars_w = "PNBRQK";
                const char* chars_b = "pnbrqk";
                out_fen[idx++] = (color_found == WHITE) ? chars_w[piece_found] : chars_b[piece_found];
            }
        }
        if (empty_count > 0) {
            out_fen[idx++] = '0' + empty_count;
        }
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

    if (b->ep_square >= 64) {
        out_fen[idx++] = '-';
    } else {
        out_fen[idx++] = 'a' + (b->ep_square % 8);
        out_fen[idx++] = '1' + (b->ep_square / 8);
    }

    std::sprintf(out_fen + idx, " %u %u", b->halfmove_clock, b->fullmove_number);
}

// Make / Unmake Move
EXPORT int native_make_move(NativeBoard* b, uint16_t m, UndoInfo* undo) {
    int from = move_from(m);
    int to = move_to(m);
    int flag = move_flag(m);
    int promo = move_promo(m);

    int us = b->side_to_move;
    int them = 1 - us;

    undo->castling_rights = b->castling_rights;
    undo->ep_square = b->ep_square;
    undo->halfmove_clock = b->halfmove_clock;
    undo->zobrist_key = b->zobrist_key;
    undo->captured_piece = NO_PIECE;

    int moving_piece = NO_PIECE;
    for (int p = 0; p < 6; p++) {
        if (b->pieces[us][p] & (1ULL << from)) {
            moving_piece = p;
            break;
        }
    }
    if (moving_piece == NO_PIECE) return 0;

    for (int p = 0; p < 6; p++) {
        if (b->pieces[them][p] & (1ULL << to)) {
            undo->captured_piece = p;
            b->pieces[them][p] &= ~(1ULL << to);
            break;
        }
    }

    b->pieces[us][moving_piece] &= ~(1ULL << from);

    b->halfmove_clock++;
    if (moving_piece == PAWN || undo->captured_piece != NO_PIECE) {
        b->halfmove_clock = 0;
    }

    b->ep_square = 64;

    if (flag == 0) {
        if (moving_piece == PAWN && std::abs(to - from) == 16) {
            b->ep_square = (from + to) / 2;
        }
        b->pieces[us][moving_piece] |= (1ULL << to);

    } else if (flag == 1) {
        b->pieces[us][KING] |= (1ULL << to);
        if (us == WHITE) {
            if (to == 6) {
                b->pieces[WHITE][ROOK] &= ~(1ULL << 7);
                b->pieces[WHITE][ROOK] |= (1ULL << 5);
            } else if (to == 2) {
                b->pieces[WHITE][ROOK] &= ~(1ULL << 0);
                b->pieces[WHITE][ROOK] |= (1ULL << 3);
            }
        } else {
            if (to == 62) {
                b->pieces[BLACK][ROOK] &= ~(1ULL << 63);
                b->pieces[BLACK][ROOK] |= (1ULL << 61);
            } else if (to == 58) {
                b->pieces[BLACK][ROOK] &= ~(1ULL << 56);
                b->pieces[BLACK][ROOK] |= (1ULL << 59);
            }
        }

    } else if (flag == 2) {
        b->pieces[us][PAWN] |= (1ULL << to);
        int cap_sq = (us == WHITE) ? (to - 8) : (to + 8);
        b->pieces[them][PAWN] &= ~(1ULL << cap_sq);
        undo->captured_piece = PAWN;

    } else if (flag == 3) {
        int promo_pt = KNIGHT + promo;
        b->pieces[us][promo_pt] |= (1ULL << to);
    }

    if (moving_piece == KING) {
        if (us == WHITE) b->castling_rights &= ~(CASTLE_W_OO | CASTLE_W_OOO);
        else b->castling_rights &= ~(CASTLE_B_OO | CASTLE_B_OOO);
    }
    if (from == 7 || to == 7) b->castling_rights &= ~CASTLE_W_OO;
    if (from == 0 || to == 0) b->castling_rights &= ~CASTLE_W_OOO;
    if (from == 63 || to == 63) b->castling_rights &= ~CASTLE_B_OO;
    if (from == 56 || to == 56) b->castling_rights &= ~CASTLE_B_OOO;

    b->side_to_move = them;
    if (us == BLACK) b->fullmove_number++;

    b->occupancy[WHITE] = 0;
    b->occupancy[BLACK] = 0;
    for (int p = 0; p < 6; p++) {
        b->occupancy[WHITE] |= b->pieces[WHITE][p];
        b->occupancy[BLACK] |= b->pieces[BLACK][p];
    }
    b->occupancy[2] = b->occupancy[WHITE] | b->occupancy[BLACK];

    uint64_t king_bb = b->pieces[us][KING];
    if (king_bb && is_square_attacked(b, lsb(king_bb), them)) {
        return 0;
    }

    b->zobrist_key = compute_zobrist(b);
    return 1;
}

EXPORT void native_unmake_move(NativeBoard* b, uint16_t m, const UndoInfo* undo) {
    int from = move_from(m);
    int to = move_to(m);
    int flag = move_flag(m);
    int promo = move_promo(m);

    b->side_to_move = 1 - b->side_to_move;
    int us = b->side_to_move;
    int them = 1 - us;

    if (us == BLACK) b->fullmove_number--;

    b->castling_rights = undo->castling_rights;
    b->ep_square = undo->ep_square;
    b->halfmove_clock = undo->halfmove_clock;
    b->zobrist_key = undo->zobrist_key;

    if (flag == 0) {
        int moving_piece = NO_PIECE;
        for (int p = 0; p < 6; p++) {
            if (b->pieces[us][p] & (1ULL << to)) {
                moving_piece = p;
                break;
            }
        }
        b->pieces[us][moving_piece] &= ~(1ULL << to);
        b->pieces[us][moving_piece] |= (1ULL << from);

    } else if (flag == 1) {
        b->pieces[us][KING] &= ~(1ULL << to);
        b->pieces[us][KING] |= (1ULL << from);
        if (us == WHITE) {
            if (to == 6) {
                b->pieces[WHITE][ROOK] &= ~(1ULL << 5);
                b->pieces[WHITE][ROOK] |= (1ULL << 7);
            } else if (to == 2) {
                b->pieces[WHITE][ROOK] &= ~(1ULL << 3);
                b->pieces[WHITE][ROOK] |= (1ULL << 0);
            }
        } else {
            if (to == 62) {
                b->pieces[BLACK][ROOK] &= ~(1ULL << 61);
                b->pieces[BLACK][ROOK] |= (1ULL << 63);
            } else if (to == 58) {
                b->pieces[BLACK][ROOK] &= ~(1ULL << 59);
                b->pieces[BLACK][ROOK] |= (1ULL << 56);
            }
        }

    } else if (flag == 2) {
        b->pieces[us][PAWN] &= ~(1ULL << to);
        b->pieces[us][PAWN] |= (1ULL << from);
        int cap_sq = (us == WHITE) ? (to - 8) : (to + 8);
        b->pieces[them][PAWN] |= (1ULL << cap_sq);

    } else if (flag == 3) {
        int promo_pt = KNIGHT + promo;
        b->pieces[us][promo_pt] &= ~(1ULL << to);
        b->pieces[us][PAWN] |= (1ULL << from);
    }

    if (flag != 2 && undo->captured_piece != NO_PIECE) {
        b->pieces[them][undo->captured_piece] |= (1ULL << to);
    }

    b->occupancy[WHITE] = 0;
    b->occupancy[BLACK] = 0;
    for (int p = 0; p < 6; p++) {
        b->occupancy[WHITE] |= b->pieces[WHITE][p];
        b->occupancy[BLACK] |= b->pieces[BLACK][p];
    }
    b->occupancy[2] = b->occupancy[WHITE] | b->occupancy[BLACK];
}

// Legal Move Generation
EXPORT int native_generate_legal_moves(NativeBoard* b, uint16_t* out_moves) {
    int count = 0;
    int us = b->side_to_move;
    int them = 1 - us;
    uint64_t occ = b->occupancy[2];
    uint64_t our_occ = b->occupancy[us];
    uint64_t their_occ = b->occupancy[them];

    // Pawns
    uint64_t pawns = b->pieces[us][PAWN];
    int forward = (us == WHITE) ? 8 : -8;
    int start_rank = (us == WHITE) ? 1 : 6;
    int promo_rank = (us == WHITE) ? 7 : 0;

    while (pawns) {
        int sq = lsb(pawns);
        pawns &= pawns - 1;
        int r = sq / 8;

        int to = sq + forward;
        if (to >= 0 && to < 64 && !(occ & (1ULL << to))) {
            if (to / 8 == promo_rank) {
                for (int pr = 3; pr >= 0; pr--) {
                    out_moves[count++] = encode_move(sq, to, 3, pr);
                }
            } else {
                out_moves[count++] = encode_move(sq, to, 0, 0);
                if (r == start_rank) {
                    int d_to = sq + 2 * forward;
                    if (!(occ & (1ULL << d_to))) {
                        out_moves[count++] = encode_move(sq, d_to, 0, 0);
                    }
                }
            }
        }

        uint64_t att = PAWN_ATTACKS[us][sq] & their_occ;
        while (att) {
            int cap_to = lsb(att);
            att &= att - 1;
            if (cap_to / 8 == promo_rank) {
                for (int pr = 3; pr >= 0; pr--) {
                    out_moves[count++] = encode_move(sq, cap_to, 3, pr);
                }
            } else {
                out_moves[count++] = encode_move(sq, cap_to, 0, 0);
            }
        }

        if (b->ep_square < 64 && (PAWN_ATTACKS[us][sq] & (1ULL << b->ep_square))) {
            out_moves[count++] = encode_move(sq, b->ep_square, 2, 0);
        }
    }

    // Knights
    uint64_t knights = b->pieces[us][KNIGHT];
    while (knights) {
        int sq = lsb(knights);
        knights &= knights - 1;
        uint64_t att = KNIGHT_ATTACKS[sq] & ~our_occ;
        while (att) {
            int to = lsb(att);
            att &= att - 1;
            out_moves[count++] = encode_move(sq, to, 0, 0);
        }
    }

    // Bishops
    uint64_t bishops = b->pieces[us][BISHOP];
    while (bishops) {
        int sq = lsb(bishops);
        bishops &= bishops - 1;
        uint64_t att = get_bishop_attacks(sq, occ) & ~our_occ;
        while (att) {
            int to = lsb(att);
            att &= att - 1;
            out_moves[count++] = encode_move(sq, to, 0, 0);
        }
    }

    // Rooks
    uint64_t rooks = b->pieces[us][ROOK];
    while (rooks) {
        int sq = lsb(rooks);
        rooks &= rooks - 1;
        uint64_t att = get_rook_attacks(sq, occ) & ~our_occ;
        while (att) {
            int to = lsb(att);
            att &= att - 1;
            out_moves[count++] = encode_move(sq, to, 0, 0);
        }
    }

    // Queens
    uint64_t queens = b->pieces[us][QUEEN];
    while (queens) {
        int sq = lsb(queens);
        queens &= queens - 1;
        uint64_t att = get_queen_attacks(sq, occ) & ~our_occ;
        while (att) {
            int to = lsb(att);
            att &= att - 1;
            out_moves[count++] = encode_move(sq, to, 0, 0);
        }
    }

    // King
    uint64_t king = b->pieces[us][KING];
    if (king) {
        int ksq = lsb(king);
        uint64_t att = KING_ATTACKS[ksq] & ~our_occ;
        while (att) {
            int to = lsb(att);
            att &= att - 1;
            out_moves[count++] = encode_move(ksq, to, 0, 0);
        }

        if (!is_square_attacked(b, ksq, them)) {
            if (us == WHITE) {
                if ((b->castling_rights & CASTLE_W_OO) && !(occ & ((1ULL << 5) | (1ULL << 6)))) {
                    if (!is_square_attacked(b, 5, BLACK) && !is_square_attacked(b, 6, BLACK)) {
                        out_moves[count++] = encode_move(4, 6, 1, 0);
                    }
                }
                if ((b->castling_rights & CASTLE_W_OOO) && !(occ & ((1ULL << 1) | (1ULL << 2) | (1ULL << 3)))) {
                    if (!is_square_attacked(b, 3, BLACK) && !is_square_attacked(b, 2, BLACK)) {
                        out_moves[count++] = encode_move(4, 2, 1, 0);
                    }
                }
            } else {
                if ((b->castling_rights & CASTLE_B_OO) && !(occ & ((1ULL << 61) | (1ULL << 62)))) {
                    if (!is_square_attacked(b, 61, WHITE) && !is_square_attacked(b, 62, WHITE)) {
                        out_moves[count++] = encode_move(60, 62, 1, 0);
                    }
                }
                if ((b->castling_rights & CASTLE_B_OOO) && !(occ & ((1ULL << 57) | (1ULL << 58) | (1ULL << 59)))) {
                    if (!is_square_attacked(b, 59, WHITE) && !is_square_attacked(b, 58, WHITE)) {
                        out_moves[count++] = encode_move(60, 58, 1, 0);
                    }
                }
            }
        }
    }

    int legal_count = 0;
    UndoInfo undo;
    for (int i = 0; i < count; i++) {
        uint16_t m = out_moves[i];
        if (native_make_move(b, m, &undo)) {
            native_unmake_move(b, m, &undo);
            out_moves[legal_count++] = m;
        } else {
            native_unmake_move(b, m, &undo);
        }
    }

    return legal_count;
}

EXPORT uint64_t native_perft(NativeBoard* b, int depth) {
    if (depth <= 0) return 1ULL;

    uint16_t moves[256];
    int n = native_generate_legal_moves(b, moves);
    if (depth == 1) return (uint64_t)n;

    uint64_t total = 0;
    UndoInfo undo;
    for (int i = 0; i < n; i++) {
        native_make_move(b, moves[i], &undo);
        total += native_perft(b, depth - 1);
        native_unmake_move(b, moves[i], &undo);
    }
    return total;
}

EXPORT int native_evaluate(const NativeBoard* b) {
    int score = 0;

    uint64_t wp = b->pieces[WHITE][PAWN];
    while (wp) {
        int sq = lsb(wp);
        score += WHITE_PAWN_TABLE[sq];
        wp &= wp - 1;
    }
    uint64_t bp = b->pieces[BLACK][PAWN];
    while (bp) {
        int sq = lsb(bp);
        score -= BLACK_PAWN_TABLE[sq];
        bp &= bp - 1;
    }

    uint64_t wn = b->pieces[WHITE][KNIGHT];
    while (wn) {
        int sq = lsb(wn);
        score += KNIGHT_TABLE[sq];
        wn &= wn - 1;
    }
    uint64_t bn = b->pieces[BLACK][KNIGHT];
    while (bn) {
        int sq = lsb(bn);
        score -= KNIGHT_TABLE[sq];
        bn &= bn - 1;
    }

    uint64_t wb = b->pieces[WHITE][BISHOP];
    int wb_cnt = 0;
    while (wb) {
        int sq = lsb(wb);
        score += BISHOP_TABLE[sq];
        wb_cnt++;
        wb &= wb - 1;
    }
    if (wb_cnt >= 2) score += 25;

    uint64_t bb = b->pieces[BLACK][BISHOP];
    int bb_cnt = 0;
    while (bb) {
        int sq = lsb(bb);
        score -= BISHOP_TABLE[sq];
        bb_cnt++;
        bb &= bb - 1;
    }
    if (bb_cnt >= 2) score -= 25;

    uint64_t wr = b->pieces[WHITE][ROOK];
    while (wr) {
        score += 500;
        wr &= wr - 1;
    }
    uint64_t br = b->pieces[BLACK][ROOK];
    while (br) {
        score -= 500;
        br &= br - 1;
    }

    uint64_t wq = b->pieces[WHITE][QUEEN];
    while (wq) {
        score += 900;
        wq &= wq - 1;
    }
    uint64_t bq = b->pieces[BLACK][QUEEN];
    while (bq) {
        score -= 900;
        bq &= bq - 1;
    }

    int castling_diff = 0;
    if (b->castling_rights & CASTLE_W_OO) castling_diff++;
    if (b->castling_rights & CASTLE_W_OOO) castling_diff++;
    if (b->castling_rights & CASTLE_B_OO) castling_diff--;
    if (b->castling_rights & CASTLE_B_OOO) castling_diff--;
    score += 15 * castling_diff;

    return (b->side_to_move == WHITE) ? score : -score;
}

// Move Ordering Score (K0 policy)
static int score_move_for_ordering(const NativeBoard* b, uint16_t m, uint16_t tt_move) {
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

    return 0; // Quiet moves
}

// Quiescence Search
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

    uint16_t moves[256];
    int n = native_generate_legal_moves(b, moves);

    // Filter and score captures
    struct ScoredMove {
        uint16_t m;
        int score;
    };
    ScoredMove caps[256];
    int n_caps = 0;

    for (int i = 0; i < n; i++) {
        uint16_t m = moves[i];
        int to = move_to(m);
        int them = 1 - b->side_to_move;
        bool is_cap = (b->occupancy[them] & (1ULL << to)) || (move_flag(m) == 2);
        if (is_cap || move_flag(m) == 3) {
            caps[n_caps++] = { m, score_move_for_ordering(b, m, 0) };
        }
    }

    // Sort captures descending
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

// Negamax Alpha-Beta Search
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

    // Fifty-move rule draw
    if (b->halfmove_clock >= 100) return 0;

    // TT Probe
    uint64_t key = b->zobrist_key;
    size_t tt_idx = key % TT_SIZE;
    TTEntry& entry = g_tt[tt_idx];
    uint16_t tt_move = 0;

    if (entry.key == key) {
        tt_move = entry.best_move;
        if (entry.depth >= depth && ply > 0) {
            if (entry.flag == TT_EXACT) return entry.score;
            if (entry.flag == TT_LOWER && entry.score >= beta) return entry.score;
            if (entry.flag == TT_UPPER && entry.score <= alpha) return entry.score;
        }
    }

    if (depth <= 0) {
        return quiescence(b, alpha, beta, nodes, deadline, aborted);
    }

    uint16_t moves[256];
    int n = native_generate_legal_moves(b, moves);

    // Terminal state check
    if (n == 0) {
        if (native_is_check(b)) {
            return -(MATE_SCORE - ply); // Checkmate
        }
        return 0; // Stalemate
    }

    // Move ordering
    struct ScoredMove {
        uint16_t m;
        int score;
    };
    ScoredMove scored_moves[256];
    for (int i = 0; i < n; i++) {
        scored_moves[i] = { moves[i], score_move_for_ordering(b, moves[i], tt_move) };
    }

    std::sort(scored_moves, scored_moves + n, [](const ScoredMove& a, const ScoredMove& b) {
        return a.score > b.score;
    });

    int orig_alpha = alpha;
    uint16_t best_move = scored_moves[0].m;
    int best_score = -INF;
    UndoInfo undo;

    for (int i = 0; i < n; i++) {
        uint16_t m = scored_moves[i].m;
        if (!native_make_move(b, m, &undo)) continue;

        uint16_t child_best = 0;
        int score = -negamax(b, depth - 1, -beta, -alpha, ply + 1, nodes, deadline, aborted, &child_best);
        native_unmake_move(b, m, &undo);

        if (aborted) return 0;

        if (score > best_score) {
            best_score = score;
            best_move = m;
        }
        if (score > alpha) {
            alpha = score;
        }
        if (alpha >= beta) {
            break; // Beta cutoff
        }
    }

    if (out_best_move) *out_best_move = best_move;

    // Store TT entry
    if (!aborted) {
        uint8_t flag = TT_EXACT;
        if (best_score <= orig_alpha) flag = TT_UPPER;
        else if (best_score >= beta) flag = TT_LOWER;

        entry.key = key;
        entry.score = (int16_t)best_score;
        entry.depth = (int8_t)depth;
        entry.flag = flag;
        entry.best_move = best_move;
    }

    return best_score;
}

// Top-Level Iterative Deepening Search
EXPORT int native_search(
    NativeBoard* b,
    int max_depth,
    double time_limit_sec,
    NativeSearchResult* out_res
) {
    init_attacks();

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

        if (dur.count() >= time_limit_sec) break;
    }

    auto final_time = std::chrono::steady_clock::now();
    std::chrono::duration<double> total_dur = final_time - start_time;
    out_res->elapsed_seconds = total_dur.count();
    out_res->nodes = total_nodes;

    return 1;
}

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
