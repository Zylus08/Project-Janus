import os
import json
import ctypes
from pathlib import Path
import chess

ROOT = Path(r"E:\ChessXML\project-janus-phase1")
DLL_PATH = ROOT / "engine" / "classical_x" / "janus_classical_x.dll"
CORPUS_PATH = ROOT / "analysis" / "phase1" / "p1.13" / "raw" / "search_decision_quality_atlas_raw.json"
RAW_OUT = ROOT / "analysis" / "phase1" / "p1.14" / "raw" / "history_reliability_raw.json"

class NativeBoard(ctypes.Structure):
    _fields_ = [
        ('pieces', (ctypes.c_uint64 * 6) * 2),
        ('occupancy', ctypes.c_uint64 * 3),
        ('side_to_move', ctypes.c_uint8),
        ('castling_rights', ctypes.c_uint8),
        ('ep_square', ctypes.c_uint8),
        ('halfmove_clock', ctypes.c_uint16),
        ('fullmove_number', ctypes.c_uint16),
        ('zobrist_key', ctypes.c_uint64)
    ]

class NativeSearchResult(ctypes.Structure):
    _fields_ = [
        ('best_move', ctypes.c_uint16),
        ('score', ctypes.c_int),
        ('depth', ctypes.c_int),
        ('nodes', ctypes.c_uint64),
        ('elapsed_seconds', ctypes.c_double),
        ('pv_length', ctypes.c_int),
        ('pv', ctypes.c_uint16 * 128)
    ]

def uci_to_compact(m_uci):
    from_sq = chess.parse_square(m_uci[:2])
    to_sq = chess.parse_square(m_uci[2:4])
    flag = 0
    promo = 0
    if len(m_uci) == 5:
        flag = 3
        pr_char = m_uci[4].lower()
        if pr_char == 'n': promo = 0
        elif pr_char == 'b': promo = 1
        elif pr_char == 'r': promo = 2
        elif pr_char == 'q': promo = 3
    return (from_sq) | (to_sq << 6) | (flag << 12) | (promo << 14)

def compact_to_uci(m_int):
    from_sq = m_int & 63
    to_sq = (m_int >> 6) & 63
    flag = (m_int >> 12) & 3
    promo = (m_int >> 14) & 3
    uci = chess.square_name(from_sq) + chess.square_name(to_sq)
    if flag == 3:
        p_chars = ['n', 'b', 'r', 'q']
        uci += p_chars[promo]
    return uci

def run_history_audit():
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    dll = ctypes.CDLL(str(DLL_PATH))
    dll.native_init()
    dll.native_search.argtypes = [ctypes.POINTER(NativeBoard), ctypes.c_int, ctypes.c_double, ctypes.POINTER(NativeSearchResult)]
    dll.native_search.restype = ctypes.c_int

    dll.native_apply_search_variant(b"X7")

    audit_records = []

    for pos in corpus["records"]:
        fen = pos["fen"]
        ref_bm = pos["sf11"].get("bestmove", "")
        cat = pos.get("cluster", "")
        pid = pos.get("id", "")
        q_class = pos.get("class_x7", "")

        board = NativeBoard()
        dll.native_set_fen(fen.encode('utf-8'), ctypes.byref(board))
        dll.native_reset_ordering_telemetry()
        dll.native_clear_history_heuristic()
        dll.native_clear_killers()

        res = NativeSearchResult()
        dll.native_search(ctypes.byref(board), 8, 2.0, ctypes.byref(res))

        janus_bm = compact_to_uci(res.best_move)

        # Inspect history scores for all legal quiet moves
        py_b = chess.Board(fen)
        legal_quiets = [m for m in py_b.legal_moves if not py_b.is_capture(m) and not m.promotion]
        
        us_side = 0 if py_b.turn == chess.WHITE else 1
        
        quiet_histories = []
        for m in legal_quiets:
            from_sq = m.from_square
            to_sq = m.to_square
            h_val = dll.native_get_history_score(us_side, from_sq, to_sq)
            quiet_histories.append({
                "move": m.uci(),
                "history": h_val,
                "is_ref_bm": (m.uci() == ref_bm),
                "is_janus_bm": (m.uci() == janus_bm)
            })

        quiet_histories.sort(key=lambda x: x["history"], reverse=True)

        # Failure Taxonomy Classification
        # H0: Reliable ordering (Janus bestmove == ref_bestmove, or ref_bm top 3 in history)
        # H1: Sparse-history (all quiet histories == 0 or ref_bm has 0 observations)
        # H2: Score-scale distortion (ref_bm had negative history due to global penalty, or high move failed)
        # H3: Stale-history interference (not applicable in single position search, but recorded if stale)
        # H4: Tactical ordering error (ref_bm was quiet and had 0/low history, while wrong move was searched first)
        
        taxonomy = "H0"
        ref_entry = next((x for x in quiet_histories if x["is_ref_bm"]), None)
        
        if janus_bm != ref_bm:
            if not quiet_histories or all(x["history"] == 0 for x in quiet_histories):
                taxonomy = "H1_SPARSE_HISTORY"
            elif ref_entry and ref_entry["history"] < 0:
                taxonomy = "H2_SCORE_SCALE_DISTORTION"
            elif ref_entry and ref_entry["history"] == 0 and quiet_histories[0]["history"] > 5000:
                taxonomy = "H4_TACTICAL_ORDERING_ERROR"
            elif cat == "tactical":
                taxonomy = "H4_TACTICAL_ORDERING_ERROR"
            else:
                taxonomy = "H1_SPARSE_HISTORY"

        audit_records.append({
            "id": pid,
            "category": cat,
            "fen": fen,
            "ref_bestmove": ref_bm,
            "janus_bestmove": janus_bm,
            "agrees": (janus_bm == ref_bm),
            "janus_score": res.score,
            "janus_nodes": res.nodes,
            "taxonomy": taxonomy,
            "quiet_histories_count": len(quiet_histories),
            "ref_move_history": ref_entry["history"] if ref_entry else None,
            "top_quiet_moves": quiet_histories[:5]
        })

    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUT, "w", encoding="utf-8") as f:
        json.dump(audit_records, f, indent=2)

    tax_counts = {}
    for r in audit_records:
        t = r["taxonomy"]
        tax_counts[t] = tax_counts.get(t, 0) + 1

    print(f"Audited {len(audit_records)} positions. Taxonomy distribution: {tax_counts}")

if __name__ == "__main__":
    run_history_audit()
