"""Project Janus v0.59 - Corpus Preparation Script.

Builds two strictly separated, phase-stratified 50-position corpora:
1. validation_corpus_50.json (Development corpus for Phase 1, Phase 2, and Phase 3)
2. evaluation_corpus_50.json (Held-out evaluation corpus for Phase 4)
"""

import json
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[2]
V56_CORPUS = ROOT / "analysis" / "v0.56" / "corpus"
V53_CORPUS = ROOT / "analysis" / "v0.53" / "corpus"
V52_CORPUS = ROOT / "analysis" / "v0.52" / "corpus"
OUT_DIR = ROOT / "analysis" / "v0.59" / "corpus"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def build_corpora():
    # 1. Build validation_corpus_50.json
    with open(V56_CORPUS / "diagnostic_corpus.json", "r", encoding="utf-8") as f:
        diag = json.load(f)
    with open(V56_CORPUS / "tactical_regression_corpus.json", "r", encoding="utf-8") as f:
        tactical = json.load(f)

    val_50 = []

    # Initial standard board
    val_50.append({
        "id": "val_00_startpos",
        "fen": chess.STARTING_FEN,
        "phase": "opening",
        "description": "Standard initial chess position"
    })

    # Diagnostic positions (37)
    for idx, d in enumerate(diag):
        fen = d["fen"]
        b = chess.Board(fen)
        piece_count = len(b.piece_map())
        ply = d.get("ply", 10)

        # Categorize phase
        if piece_count <= 10:
            phase = "endgame"
        elif ply <= 6:
            phase = "opening"
        elif d.get("nature") == "tactical":
            phase = "tactical"
        else:
            phase = "middlegame"

        val_50.append({
            "id": f"val_diag_{idx+1:02d}_{d['id']}",
            "fen": fen,
            "phase": phase,
            "description": f"Diagnostic position {d['id']} ({d.get('opening', 'general')})"
        })

    # Tactical regression positions (12)
    for idx, t in enumerate(tactical):
        val_50.append({
            "id": f"val_tac_{idx+1:02d}_{t['id']}",
            "fen": t["fen"],
            "phase": "tactical",
            "description": t.get("description", "Tactical regression problem")
        })

    assert len(val_50) == 50, f"Expected 50 validation positions, got {len(val_50)}"

    with open(OUT_DIR / "validation_corpus_50.json", "w", encoding="utf-8") as f:
        json.dump(val_50, f, indent=2)

    # 2. Build evaluation_corpus_50.json (Held-out)
    with open(V53_CORPUS / "independent_tactical_v053.json", "r", encoding="utf-8") as f:
        indep_tac = json.load(f)
    with open(V56_CORPUS / "capture_evaluation_corpus.json", "r", encoding="utf-8") as f:
        cap_eval = json.load(f)
    with open(V52_CORPUS / "openings_v052_100.json", "r", encoding="utf-8") as f:
        openings = json.load(f)

    eval_50 = []
    val_fens = set(p["fen"] for p in val_50)

    # 20 independent tactical positions (filtered against val_fens)
    for idx, it in enumerate(indep_tac):
        if it["fen"] not in val_fens and len(eval_50) < 20:
            eval_50.append({
                "id": f"eval_tac_{len(eval_50)+1:02d}_{it['id']}",
                "fen": it["fen"],
                "phase": "tactical",
                "description": it.get("description", "Independent tactical test")
            })

    # Capture evaluation positions (filtered against val_fens)
    for idx, c in enumerate(cap_eval):
        if c["fen"] not in val_fens and len(eval_50) < 35:
            eval_50.append({
                "id": f"eval_cap_{len(eval_50)+1:02d}_{c['id']}",
                "fen": c["fen"],
                "phase": "middlegame" if c.get("category") != "endgame" else "endgame",
                "description": c.get("description", "Capture evaluation position")
            })

    # Independent opening positions from openings_v052_100 (filtered against val_fens)
    for idx, op in enumerate(openings):
        if op["fen"] not in val_fens and len(eval_50) < 50:
            eval_50.append({
                "id": f"eval_open_{len(eval_50)+1:02d}_{op['id']}",
                "fen": op["fen"],
                "phase": "opening",
                "description": f"Independent opening: {op.get('name', 'Opening')}"
            })

    assert len(eval_50) == 50, f"Expected 50 evaluation positions, got {len(eval_50)}"

    with open(OUT_DIR / "evaluation_corpus_50.json", "w", encoding="utf-8") as f:
        json.dump(eval_50, f, indent=2)

    # Summary
    def summarize(name, corpus):
        print(f"\n{name} ({len(corpus)} positions):")
        phases = {}
        for p in corpus:
            ph = p["phase"]
            phases[ph] = phases.get(ph, 0) + 1
        for ph, cnt in sorted(phases.items()):
            print(f"  {ph:15s}: {cnt}")

    summarize("Validation Corpus (Development)", val_50)
    summarize("Evaluation Corpus (Held-out)", eval_50)

    # Check for leakage
    val_fens = set(p["fen"] for p in val_50)
    eval_fens = set(p["fen"] for p in eval_50)
    overlap = val_fens.intersection(eval_fens)
    print(f"\nOverlap between Development and Held-out Corpora: {len(overlap)} positions")
    assert len(overlap) == 0, f"Leakage detected between val and eval: {overlap}"
    print("Zero leakage confirmed between Development and Held-out Corpora!")


if __name__ == "__main__":
    build_corpora()
