import re
from pathlib import Path

pgn_path = Path(r"E:\ChessXML\project-janus-phase1\analysis\phase1\p1.2\pgn\x7_vs_x6.pgn")
if not pgn_path.exists():
    print("PGN does not exist yet.")
    exit(0)

with open(pgn_path, "r", encoding="utf-8") as f:
    text = f.read()

games = [g for g in text.split("[Event ") if g.strip()]
w7, w6, dr = 0, 0, 0

for g in games:
    white = re.search(r'\[White "(.*?)"\]', g)
    res = re.search(r'\[Result "(.*?)"\]', g)
    if not white or not res:
        continue
    w_name = white.group(1)
    r = res.group(1)
    is_x7_white = ("X7" in w_name)
    if r == "1-0":
        if is_x7_white:
            w7 += 1
        else:
            w6 += 1
    elif r == "0-1":
        if is_x7_white:
            w6 += 1
        else:
            w7 += 1
    elif r == "1/2-1/2":
        dr += 1

tot = w7 + w6 + dr
print(f"Total Completed Games: {tot}")
if tot > 0:
    pts = w7 + 0.5 * dr
    pct = (pts / tot) * 100.0
    print(f"X7: +{w7} ={dr} -{w6} | Points: {pts:.1f}/{tot} ({pct:.2f}%)")

