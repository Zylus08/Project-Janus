import subprocess
import time
import json
import os
import re

def run_uci_search(exe, commands, timeout_sec=10):
    p = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate(commands, timeout=timeout_sec)
    return out

def main():
    exe = "E:/ChessXML/project-janus-phase1/engine/classical_x/janus_classical_x.exe"
    results = {}

    print("Auditing Phase 5 Dynamic Time Management...")

    # 1. Test Low-Clock Emergency Handling (500ms clock, 50ms increment)
    cmd_low = "uci\nisready\nposition startpos\ngo wtime 500 btime 500 winc 50 binc 50\nquit\n"
    t0 = time.time()
    out_low = run_uci_search(exe, cmd_low, timeout_sec=5)
    elapsed_low = time.time() - t0
    
    bestmove_low = None
    depth_low = None
    for line in out_low.splitlines():
        if "bestmove" in line: bestmove_low = line.split()[1]
        if "info depth" in line and "score cp" in line:
            m_d = re.search(r'depth (\d+)', line)
            if m_d: depth_low = int(m_d.group(1))

    results["low_clock_safety"] = {
        "wtime_ms": 500,
        "winc_ms": 50,
        "elapsed_sec": elapsed_low,
        "bestmove": bestmove_low,
        "depth": depth_low,
        "no_forfeit": (elapsed_low < 0.50),
        "valid_move": bool(bestmove_low and len(bestmove_low) >= 4)
    }
    print("Low Clock Safety:", results["low_clock_safety"])

    # 2. Test movestogo scaling
    # Case A: movestogo 5 (imminent time control -> allocate more time)
    cmd_mtg5 = "uci\nisready\nposition startpos\ngo wtime 10000 btime 10000 winc 100 binc 100 movestogo 5\nquit\n"
    t0 = time.time()
    out_mtg5 = run_uci_search(exe, cmd_mtg5, timeout_sec=10)
    dur_mtg5 = time.time() - t0

    # Case B: movestogo 40 (distant time control -> conserve time)
    cmd_mtg40 = "uci\nisready\nposition startpos\ngo wtime 10000 btime 10000 winc 100 binc 100 movestogo 40\nquit\n"
    t0 = time.time()
    out_mtg40 = run_uci_search(exe, cmd_mtg40, timeout_sec=10)
    dur_mtg40 = time.time() - t0

    results["movestogo_adaptation"] = {
        "movestogo_5_duration_sec": dur_mtg5,
        "movestogo_40_duration_sec": dur_mtg40,
        "allocates_more_on_imminent_tc": (dur_mtg5 > dur_mtg40)
    }
    print("Movestogo Adaptation:", results["movestogo_adaptation"])

    # 3. Test Periodic Hard Deadline Check
    # Even if infinite search or long time is given, hard deadline or quick search works cleanly
    cmd_fast = "uci\nisready\nposition startpos\ngo movetime 200\nquit\n"
    t0 = time.time()
    out_fast = run_uci_search(exe, cmd_fast, timeout_sec=5)
    dur_fast = time.time() - t0

    results["movetime_hard_cap"] = {
        "requested_ms": 200,
        "actual_elapsed_sec": dur_fast,
        "cap_adherence": (0.15 <= dur_fast <= 0.35)
    }
    print("Movetime Cap:", results["movetime_hard_cap"])

    out_file = "E:/ChessXML/project-janus-phase1/analysis/phase1/p1.5/raw/time_management_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {out_file}")

if __name__ == "__main__":
    main()

