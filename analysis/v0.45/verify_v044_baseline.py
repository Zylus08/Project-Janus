"""Verify v0.44 baseline artifacts and write v0.45 reference manifest."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

def get_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def run():
    v044_manifest_path = Path("analysis/v0.44/sha256_manifest.json")
    with open(v044_manifest_path, "r", encoding="utf-8") as f:
        v044_manifest = json.load(f)

    mismatches = []
    verified_entries = {}

    for rel_path, expected_hash in v044_manifest.items():
        p = Path(rel_path)
        if not p.exists():
            mismatches.append({"path": rel_path, "status": "MISSING", "expected": expected_hash})
            continue
        actual_hash = get_sha256(p)
        if actual_hash != expected_hash:
            mismatches.append({"path": rel_path, "status": "MISMATCH", "expected": expected_hash, "actual": actual_hash})
        else:
            verified_entries[rel_path] = {
                "sha256": actual_hash,
                "size_bytes": p.stat().st_size,
            }

    # Stockfish 19
    sf_p = Path("E:/ChessXML/tools/stockfish/stockfish.exe")
    sf_hash = get_sha256(sf_p) if sf_p.exists() else None

    # Git commit
    res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    head_commit = res.stdout.strip()

    reference_manifest = {
        "milestone": "v0.45",
        "parent_milestone": "v0.44",
        "baseline_commit": head_commit,
        "stockfish_path": str(sf_p),
        "stockfish_sha256": sf_hash,
        "engine_configuration": {
            "production_default": {"enable_rfp": False, "diagnostic_rfp": False},
            "experimental_rfp": {"enable_rfp": True, "rfp_max_depth": 2, "rfp_margin_per_depth": 120},
        },
        "v044_verified_artifacts_count": len(verified_entries),
        "v044_mismatches": mismatches,
        "artifacts": verified_entries,
    }

    out_path = Path("analysis/v0.45/v044_reference_manifest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(reference_manifest, f, indent=2)

    print(f"Verified {len(verified_entries)} v0.44 artifacts. Mismatches: {len(mismatches)}")
    if mismatches:
        for m in mismatches:
            print("  Mismatch:", m)
    print("Wrote analysis/v0.45/v044_reference_manifest.json successfully.")

if __name__ == "__main__":
    run()

