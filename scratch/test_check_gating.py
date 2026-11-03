import sys
from pathlib import Path
import chess

ROOT = Path("e:/ChessXML/project-janus")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from scratch.test_pvs_prototype import PvsSearch

# Let's test a position where side to move is in check
fen_check = "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 5" # e.g. white threatens mate, black king or tactical checks
# Let's test a position with heavy checks
fen_evasion = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"

for fen in [fen_check, fen_evasion]:
    board = chess.Board(fen)
    for check_gated in [False, True]:
        pvs = PvsSearch(enable_pvs=True, pvs_min_depth=2, pvs_in_check_gated=check_gated)
        res = pvs.search(board, max_depth=4)
        print(f"CheckGated={check_gated}: nodes={res.nodes} score={res.score} best={res.best_move} pv={[m.uci() for m in res.pv]}")
