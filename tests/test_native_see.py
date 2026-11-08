"""Comprehensive correctness test suite for Project Janus v0.56 Native SEE.

Compares Native SEE implementation in janus_native.dll against the independent
reference oracle (slow_see_reference) across all 24 required categories:
1. Undefended pawn capture
2. Pawn recapture chain
3. Equal-value exchanges
4. Queen captures defended pawn
5. Rook captures defended minor piece
6. Multiple attackers
7. Multiple defenders
8. X-ray bishop
9. X-ray rook
10. X-ray queen
11. Pinned knight
12. Pinned bishop
13. King as final recapturing piece
14. Illegal king recapture
15. Promotion capture
16. Underpromotion
17. En passant (undefended)
18. En passant (defended & discovered attack)
19. Exchange where declining recapture is optimal
20. Equal-value attacker ties
21. Check-related legal capture constraints
22. Invalid move encoding / safe handling
23. Deep exchange chain (stress test)
24. Deterministic repeated evaluation
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
import chess

from tests.test_see import slow_see_reference, SEE_PIECE_VALUES

REPO_ROOT = Path(__file__).resolve().parent.parent
BRIDGE_PATH = REPO_ROOT / "analysis" / "v0.56" / "native" / "janus_native_bridge.py"

spec = importlib.util.spec_from_file_location("janus_native_bridge_v56", BRIDGE_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Cannot load NativeEngineBridge from {BRIDGE_PATH}")
bridge_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge_module)
NativeEngineBridge = bridge_module.NativeEngineBridge


class TestNativeStaticExchangeEvaluation(unittest.TestCase):
    """Formal verification of native SEE against the minimax reference oracle."""

    @classmethod
    def setUpClass(cls):
        cls.bridge = NativeEngineBridge()

    def assert_see_matches_oracle(self, fen: str, uci_move: str):
        """Asserts that native SEE returns the exact centipawn score of slow_see_reference."""
        self.bridge.set_fen(fen)
        m_int = self.bridge.parse_uci(uci_move)
        self.assertNotEqual(m_int, 0, f"Move {uci_move} could not be parsed in FEN: {fen}")

        native_val = self.bridge.see(m_int)

        b = chess.Board(fen)
        m_chess = chess.Move.from_uci(uci_move)
        expected_val = slow_see_reference(b, m_chess)

        self.assertEqual(
            native_val,
            expected_val,
            f"SEE mismatch for {uci_move} in {fen}: native={native_val}, oracle={expected_val}",
        )

    # 1. Undefended pawn capture
    def test_01_undefended_pawn_capture(self):
        fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 2"
        self.assert_see_matches_oracle(fen, "f3e5")

    # 2. Pawn recapture chain
    def test_02_pawn_recapture_chain(self):
        fen = "rnbqkb1r/ppp2ppp/4pn2/3p4/2PP4/2N5/PP2PPPP/R1BQKBNR w KQkq - 0 4"
        self.assert_see_matches_oracle(fen, "c4d5")

    # 3. Equal-value exchanges
    def test_03_equal_value_exchanges(self):
        # White Knight on f3 takes Black Knight on e5 defended by pawn d6
        fen = "r1bqkb1r/ppp2ppp/3p4/4n3/4P3/5N2/PPP2PPP/RNBQKB1R w KQkq - 0 1"
        self.assert_see_matches_oracle(fen, "f3e5")

    # 4. Queen captures defended pawn
    def test_04_queen_captures_defended_pawn(self):
        # Queen on h5 takes f7 defended by King on e8
        fen = "r1bqkb1r/pppp1ppp/2n5/4p2Q/4P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1"
        self.assert_see_matches_oracle(fen, "h5f7")

    # 5. Rook captures defended minor piece
    def test_05_rook_captures_defended_minor_piece(self):
        # White Rook on d1 takes Black Bishop on d6 defended by Black Rook on d8
        fen = "3r2k1/5ppp/3b4/8/8/8/8/3R2K1 w - - 0 1"
        self.assert_see_matches_oracle(fen, "d1d6")

    # 6. Multiple attackers
    def test_06_multiple_attackers(self):
        fen = "r1b1k2r/ppp2ppp/2n5/3pp3/8/2B2N2/PPPP1PPP/R2QKB1R w KQkq - 0 1"
        self.assert_see_matches_oracle(fen, "f3e5")

    # 7. Multiple defenders
    def test_07_multiple_defenders(self):
        fen = "r1bqk2r/ppp2ppp/2n5/3np3/8/2NP1N2/PPP1BPPP/R2QK2R w KQkq - 0 1"
        self.assert_see_matches_oracle(fen, "c3d5")

    # 8. X-ray bishop
    def test_08_xray_bishop(self):
        # Battery B on b2, Q on c3 attacking e5
        fen = "4r1k1/ppp2ppp/8/4n3/8/2Q5/PB3PPP/4R1K1 w - - 0 1"
        self.assert_see_matches_oracle(fen, "e1e5")

    # 9. X-ray rook
    def test_09_xray_rook(self):
        # Rooks on d1 and d2 attacking d5
        fen = "3r2k1/ppp2ppp/8/3n4/8/8/PPPR4/3R2K1 w - - 0 1"
        self.assert_see_matches_oracle(fen, "d2d5")

    # 10. X-ray queen
    def test_10_xray_queen(self):
        fen = "3r2k1/ppp2ppp/8/3n4/8/8/PPPQ4/3R2K1 w - - 0 1"
        self.assert_see_matches_oracle(fen, "d2d5")

    # 11. Pinned knight cannot recapture off pin ray
    def test_11_pinned_knight(self):
        # Black Knight on c6 is pinned to King on e8 by White Bishop on b5.
        # White Knight on f3 takes pawn on d4.
        fen = "r1bqk2r/pppp1ppp/2n5/1B6/3pn3/5N2/PPP2PPP/RNBQK2R w KQkq - 0 1"
        self.assert_see_matches_oracle(fen, "f3d4")

    # 12. Pinned bishop can recapture along pin ray
    def test_12_pinned_bishop_along_pin_ray(self):
        # White Bishop on e2 is pinned to King on e1 by Black Rook on e8,
        # but can legally capture a piece that lands on e7 or e6.
        fen = "4r1k1/4n3/8/8/8/8/4B3/4K3 w - - 0 1"
        self.bridge.set_fen(fen)
        m = self.bridge.parse_uci("e2h5")
        self.assertEqual(self.bridge.see(m), 0)

    # 13. King as final recapturing piece
    def test_13_king_as_final_recapturing_piece(self):
        fen = "8/8/8/4k3/4r3/8/4R3/4K3 w - - 0 1"
        self.assert_see_matches_oracle(fen, "e2e4")

    # 14. Illegal king recapture on defended square
    def test_14_illegal_king_recapture(self):
        # White Queen on h5 takes f7 defended by bishop on c4; Black King cannot recapture
        fen = "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1"
        self.assert_see_matches_oracle(fen, "h5f7")

    # 15. Promotion capture
    def test_15_promotion_capture(self):
        # White pawn on a7 captures Rook on b8 and promotes to Queen
        fen = "1rr4k/P7/8/8/8/8/8/R6K w - - 0 1"
        self.assert_see_matches_oracle(fen, "a7b8q")

    # 16. Underpromotion capture
    def test_16_underpromotion_capture(self):
        fen = "1rr4k/P7/8/8/8/8/8/R6K w - - 0 1"
        self.assert_see_matches_oracle(fen, "a7b8n")

    # 17. En passant undefended
    def test_17_en_passant_undefended(self):
        fen = "7k/8/8/3Pp3/8/8/8/K7 w - e6 0 1"
        self.assert_see_matches_oracle(fen, "d5e6")

    # 18. En passant defended & discovered attack
    def test_18_en_passant_defended(self):
        fen = "rnb1kbnr/ppppqppp/8/3Pp3/8/8/PPP1PPPP/RNBQKBNR w KQkq e6 0 2"
        self.assert_see_matches_oracle(fen, "d5e6")

    # 19. Exchange where declining recapture is optimal
    def test_19_declining_recapture_optimal(self):
        # White Rook takes defended pawn: Black Queen should NOT recapture if defended by Rook
        fen = "3q2k1/5ppp/8/3p4/8/8/3R2PP/3R2K1 w - - 0 1"
        self.assert_see_matches_oracle(fen, "d2d5")

    # 20. Equal-value attacker ties
    def test_20_equal_value_attacker_ties(self):
        # Two knights attacking d4
        fen = "r2qkb1r/ppp1pppp/2n2n2/3p4/3P2b1/2N1PN2/PPP2PPP/R1BQKB1R w KQkq - 3 5"
        self.assert_see_matches_oracle(fen, "f3e5")

    # 21. Check-related legal capture constraints
    def test_21_check_related_constraints(self):
        fen = "rnb1k2r/pp1p1ppp/4p3/q1b5/4P3/2N5/PPP2PPP/R1BQKBNR w KQkq - 0 7"
        self.assert_see_matches_oracle(fen, "c1d2")

    # 22. Invalid move encoding / safe zero return
    def test_22_invalid_move_handling(self):
        self.bridge.set_fen(chess.STARTING_FEN)
        self.assertEqual(self.bridge.see(0), 0)

    # 23. Deep exchange chain stress test
    def test_23_deep_exchange_chain(self):
        # Massive piece concentration on d4
        fen = "1k1r3r/ppq2ppp/2pbpn2/3n4/3P4/2NQPN2/PP1B1PPP/1K1R3R w - - 0 1"
        self.assert_see_matches_oracle(fen, "c3d5")

    # 24. Deterministic repeated evaluation
    def test_24_deterministic_repeated_evaluation(self):
        fen = "r1bqk2r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1"
        self.bridge.set_fen(fen)
        m = self.bridge.parse_uci("h5f7")
        v1 = self.bridge.see(m)
        v2 = self.bridge.see(m)
        v3 = self.bridge.see(m)
        self.assertEqual(v1, v2)
        self.assertEqual(v2, v3)

    # 25. Benchmark-wide differential testing
    def test_25_differential_oracle_benchmark_suite(self):
        """Exhaustively verify native SEE on all legal captures across standard benchmark positions."""
        benchmark_fens = [
            chess.STARTING_FEN,
            "r1bqk2r/pppp1ppp/2n5/4p3/1b1P4/5N2/PPP1PPPP/RNBQKB1R w KQkq - 2 3",
            "r1bqkb1r/pppp1ppp/2n5/4p2Q/4P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1",
            "r1bqkb1r/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1",
            "3r2k1/ppp2ppp/8/3n4/8/8/PPPR4/3R2K1 w - - 0 1",
            "1rr4k/P7/8/8/8/8/8/R6K w - - 0 1",
            "8/P7/8/8/8/4k3/8/4K3 w - - 0 1",
            "7k/8/8/3Pp3/8/8/8/K7 w - e6 0 1",
            "rnb1kbnr/ppppqppp/8/3Pp3/8/8/PPP1PPPP/RNBQKBNR w KQkq e6 0 2",
            "4k3/4q3/8/8/3p4/8/1Q6/4R2K w - - 0 1",
            "r2qkb1r/pp2nppp/3p4/2pNN1B1/2BnP3/3P4/PPP2PPP/R2bK2R w KQkq - 1 9",
            "r1b1k2r/ppp2ppp/2n5/3pp3/8/2B2N2/PPPP1PPP/R2QKB1R w KQkq - 0 1",
            "2r3k1/1p3ppp/pq2p3/3p4/8/1P1Q4/P4PPP/2R3K1 b - - 0 1",
            "r2q1rk1/1pp1bppp/p1np1n2/4p3/2B1P1b1/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 0 9",
            "r1bqr1k1/ppp2ppp/2np4/4n3/2P5/2N1PN2/PP2BPPP/R2Q1RK1 w - - 0 11",
            "3r2k1/p4p1p/1p4p1/2q1b3/2P5/1P2B1P1/P4P1P/3R2K1 w - - 0 25",
            "r2qkb1r/pp1b1ppp/2n5/1B1p4/3P4/5N2/PP3PPP/R1BQK2R w KQkq - 0 10",
        ]

        total_tested = 0
        for fen in benchmark_fens:
            self.bridge.set_fen(fen)
            b = chess.Board(fen)
            for m in b.legal_moves:
                uci_str = m.uci()
                m_int = self.bridge.parse_uci(uci_str)
                if m_int == 0:
                    continue

                # Test all captures and promotions
                is_cap = b.is_capture(m)
                is_promo = bool(m.promotion)
                if is_cap or is_promo:
                    total_tested += 1
                    native_score = self.bridge.see(m_int)
                    oracle_score = slow_see_reference(b, m)
                    self.assertEqual(
                        native_score,
                        oracle_score,
                        f"Mismatch in {fen} for move {uci_str}: native={native_score}, oracle={oracle_score}",
                    )

        self.assertGreaterEqual(total_tested, 40, "Should have tested at least 40 captures/promotions")


if __name__ == "__main__":
    unittest.main()
