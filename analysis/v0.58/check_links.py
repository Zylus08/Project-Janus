import urllib.request
import re

req = urllib.request.Request('https://database.nikonoel.fr/', headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        links = re.findall(r'href=[\'"]([^\'"]+)', html)
        pgn_links = [l for l in links if any(ext in l.lower() for ext in ['.zip', '.pgn', '.zst', '.bz2', '.torrent'])]
        print("Found links:", len(pgn_links))
        for l in pgn_links:
            print(l)
except Exception as e:
    print("Error:", e)
