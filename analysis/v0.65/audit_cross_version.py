"""Project Janus v0.65 - Cross-Version Reproducibility Auditor.

Audits source hashes, model hashes, executable hashes, and experimental claims
across v0.56, v0.58, v0.59, v0.60, v0.61, v0.62, v0.63, and v0.64.
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parents[2]


def get_sha256(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def audit_artifacts() -> Dict[str, Any]:
    tracked_artifacts = {
        # Baseline C1 (v0.56)
        "c1_engine_exe": ROOT / "analysis" / "v0.56" / "native" / "janus_native_engine.exe",
        "c1_source_cpp": ROOT / "analysis" / "v0.56" / "native" / "janus_native.cpp",
        # Policy N8 (v0.58 / v0.59)
        "n8_policy_pt": ROOT / "analysis" / "v0.58" / "models" / "best_policy_model.pt",
        "n8_policy_bin": ROOT / "analysis" / "v0.58" / "models" / "janus_policy_v1.bin",
        "n8_policy_manifest": ROOT / "analysis" / "v0.58" / "experiment_manifest.json",
        "v059_ablation_manifest": ROOT / "analysis" / "v0.59" / "experiment_manifest.json",
        # Neural Value V1 (v0.60)
        "v1_model_jnnue": ROOT / "analysis" / "v0.60" / "models" / "janus_nnue_v1_small.jnnue",
        "v1_manifest": ROOT / "analysis" / "v0.60" / "experiment_manifest.json",
        # Neural Baseline N1 (v0.61 / v0.62)
        "n1_engine_exe": ROOT / "analysis" / "v0.61" / "native" / "janus_native_engine.exe",
        "n1_model_jnnue": ROOT / "analysis" / "v0.61" / "models" / "janus_nnue_v2_small.jnnue",
        "v061_manifest": ROOT / "analysis" / "v0.61" / "experiment_manifest.json",
        "v062_manifest": ROOT / "analysis" / "v0.62" / "experiment_manifest.json",
        "v062_match_raw": ROOT / "analysis" / "v0.62" / "raw" / "v062_confirmatory_match_raw.json",
        # Diagnostics (v0.63)
        "v063_manifest": ROOT / "analysis" / "v0.63" / "experiment_manifest.json",
        "v063_cross_milestone_audit": ROOT / "analysis" / "v0.63" / "cross_milestone_audit.json",
        # Neural Baseline N2 (v0.64)
        "n2_engine_exe": ROOT / "analysis" / "v0.64" / "native" / "janus_native_engine.exe",
        "n2_model_jnnue": ROOT / "analysis" / "v0.64" / "models" / "janus_nnue_v3.jnnue",
        "n2_sef_header": ROOT / "analysis" / "v0.64" / "native" / "sef_features.h",
        "v064_manifest": ROOT / "analysis" / "v0.64" / "experiment_manifest.json",
        "v064_primary_raw": ROOT / "analysis" / "v0.64" / "raw" / "v064_confirmatory_match_raw.json",
        "v064_secondary_raw": ROOT / "analysis" / "v0.64" / "raw" / "v064_secondary_v3_vs_n1_raw.json",
    }

    results = {}
    for name, p in tracked_artifacts.items():
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        exists = p.exists()
        size = p.stat().st_size if exists else 0
        sha = get_sha256(p) if exists else "MISSING"
        results[name] = {
            "path": rel,
            "exists": exists,
            "size_bytes": size,
            "sha256": sha,
        }
    return results


def audit_historical_matches() -> Dict[str, Any]:
    matches = {}

    # v0.61 Tournament
    v61_raw = ROOT / "analysis" / "v0.61" / "raw" / "v061_v2_vs_c1_match_raw.json"
    if v61_raw.exists():
        with open(v61_raw) as f:
            d = json.load(f)
            matches["v0.61_v2_vs_c1"] = {
                "games": d.get("total_games", len(d.get("games", []))),
                "score": d.get("score"),
                "elo": d.get("elo"),
                "paired": d.get("paired_statistics"),
            }

    # v0.62 Tournament
    v62_raw = ROOT / "analysis" / "v0.62" / "raw" / "v062_confirmatory_match_raw.json"
    if v62_raw.exists():
        with open(v62_raw) as f:
            d = json.load(f)
            matches["v0.62_confirmatory_v2_vs_c1"] = {
                "games": d.get("total_games", len(d.get("games", []))),
                "score": d.get("score"),
                "elo": d.get("elo"),
                "paired": d.get("paired_statistics"),
            }

    # v0.64 Primary Match (V3 vs C1)
    v64_raw = ROOT / "analysis" / "v0.64" / "raw" / "v064_confirmatory_match_raw.json"
    if v64_raw.exists():
        with open(v64_raw) as f:
            d = json.load(f)
            matches["v0.64_primary_v3_vs_c1"] = {
                "games": d.get("total_games", len(d.get("games", []))),
                "score": d.get("score"),
                "elo": d.get("elo"),
                "paired": d.get("paired_statistics"),
                "endgame_le_16": d.get("endgame_performance"),
                "volume_perf": d.get("volume_performance"),
            }

    # v0.64 Secondary Match (V3 vs N1)
    v64_sec = ROOT / "analysis" / "v0.64" / "raw" / "v064_secondary_v3_vs_n1_raw.json"
    if v64_sec.exists():
        with open(v64_sec) as f:
            d = json.load(f)
            matches["v0.64_secondary_v3_vs_n1"] = {
                "games": d.get("total_games", len(d.get("games", []))),
                "score": d.get("score"),
                "elo": d.get("elo"),
                "paired": d.get("paired_statistics"),
                "endgame_le_16": d.get("endgame_performance"),
                "volume_perf": d.get("volume_performance"),
            }

    return matches


def main():
    artifacts = audit_artifacts()
    matches = audit_historical_matches()

    report = {
        "audit_version": "v0.65",
        "artifacts": artifacts,
        "matches": matches,
    }

    out_p = ROOT / "analysis" / "v0.65" / "raw" / "cross_version_audit_raw.json"
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Audited {len(artifacts)} tracked core artifacts across milestones.")
    print(f"Audited {len(matches)} historical tournament datasets.")
    for k, v in matches.items():
        print(f"  {k}: Score = {v['score']['points']}/{v['games']} ({v['score']['percentage']}%), Elo = {v['elo']['delta_elo']}")


if __name__ == "__main__":
    main()
