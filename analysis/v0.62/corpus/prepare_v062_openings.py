#!/usr/bin/env python3
"""Project Janus v0.62 - Independent Confirmatory Opening Suite Preparation.

Prepares 100 fresh, balanced, independent opening pairs for the v0.62 confirmatory tournament,
ensuring zero overlap with the v0.56 / v0.61 opening suite (independent_openings_v056.json).
"""

from __future__ import annotations

import json
from pathlib import Path
import chess

ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = ROOT / "analysis" / "v0.55" / "corpus" / "independent_openings_v055.json"
V56_PATH = ROOT / "analysis" / "v0.56" / "corpus" / "independent_openings_v056.json"
OUT_DIR = ROOT / "analysis" / "v0.62" / "corpus"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "independent_openings_v062.json"


def prepare_openings():
    print("Loading source openings from v0.55 corpus...")
    with open(SRC_PATH, "r", encoding="utf-8") as f:
        src_openings = json.load(f)

    with open(V56_PATH, "r", encoding="utf-8") as f:
        v56_openings = json.load(f)

    v56_fens = set(x.get("fen", "") for x in v56_openings)

    v62_openings = []
    skipped = 0

    for idx, op in enumerate(src_openings):
        b = chess.Board()
        san_str = op.get("moves", "")
        uci_seq = []
        valid = True

        for san in san_str.split():
            try:
                m = b.parse_san(san)
                uci_seq.append(m.uci())
                b.push(m)
            except Exception as e:
                print(f"Error parsing SAN '{san}' in opening {op.get('name')}: {e}")
                valid = False
                break

        if not valid:
            skipped += 1
            continue

        fen = b.fen()
        if fen in v56_fens:
            print(f"Skipping opening overlapping with v0.56: {op.get('name')}")
            skipped += 1
            continue

        v62_openings.append({
            "pair_id": len(v62_openings) + 1,
            "id": op.get("id", f"opening_{len(v62_openings)+1}"),
            "eco": op.get("eco", "A00"),
            "category": op.get("category", "Uncategorized"),
            "name": op.get("name", f"Opening {len(v62_openings)+1}"),
            "ply_depth": len(uci_seq),
            "san_sequence": san_str,
            "uci_sequence": uci_seq,
            "fen": fen,
        })

    print(f"Successfully processed {len(v62_openings)} independent openings (skipped {skipped}).")
    assert len(v62_openings) == 100, f"Expected exactly 100 openings, got {len(v62_openings)}"

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(v62_openings, f, indent=2)

    print(f"Saved {len(v62_openings)} openings to {OUT_PATH}")


if __name__ == "__main__":
    prepare_openings()
