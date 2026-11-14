#include <iostream>
#include <cstdint>

struct NativeBoard {
    uint64_t pieces[2][6];
    uint64_t occupancy[3];
    uint8_t side_to_move;
    uint8_t castling_rights;
    uint8_t ep_square;
    uint16_t halfmove_clock;
    uint16_t fullmove_number;
    uint64_t zobrist_key;
};

extern "C" {
    __declspec(dllimport) int native_init();
    __declspec(dllimport) int native_set_fen(const char* fen, NativeBoard* b);
    __declspec(dllimport) int native_evaluate_detail(const NativeBoard* b, int emode);
    __declspec(dllimport) void native_set_backward_pawns_mode(int mode);
    __declspec(dllimport) int native_get_backward_pawns_mode();
    __declspec(dllimport) void native_set_pawn_hash(int mode);
}

int main() {
    native_init();
    native_set_pawn_hash(0);

    NativeBoard b;
    // Black backward d6, White has e4 and f2 (f2 supports e4, so White has NO backward pawn!)
    const char* fen = "8/8/3p4/2p1p3/4P3/8/5P2/4K2k w - - 0 1";
    native_set_fen(fen, &b);

    native_set_backward_pawns_mode(0);
    std::cout << "--- EVALUATION WITH BP = 0 ---" << std::endl;
    int off_score = native_evaluate_detail(&b, 1);
    std::cout << "Computed off_score: " << off_score << std::endl;

    native_set_backward_pawns_mode(1);
    std::cout << "--- EVALUATION WITH BP = 1 ---" << std::endl;
    int on_score = native_evaluate_detail(&b, 1);
    std::cout << "Computed on_score: " << on_score << std::endl;

    std::cout << "Difference (on - off): " << (on_score - off_score) << " cp" << std::endl;
    return 0;
}
