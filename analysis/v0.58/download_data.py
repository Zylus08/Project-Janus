import urllib.request
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ZIP_PATH = DATA_DIR / "lichess_elite_2020-06.zip"

URL = "https://database.nikonoel.fr/lichess_elite_2020-06.zip"

def download_with_progress(url, dest):
    print(f"Downloading {url} to {dest}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    t0 = time.time()
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
        total = int(resp.headers.get('content-length', 0))
        downloaded = 0
        chunk_size = 1024 * 1024
        while chunk := resp.read(chunk_size):
            f.write(chunk)
            downloaded += len(chunk)
            pct = (downloaded / total * 100) if total else 0
            mb = downloaded / (1024 * 1024)
            speed = mb / (time.time() - t0 + 1e-6)
            if int(mb) % 10 == 0:
                print(f"  Downloaded: {mb:.1f} MB ({pct:.1f}%) @ {speed:.1f} MB/s", flush=True)
    print(f"Done in {time.time()-t0:.1f}s! Total size: {dest.stat().st_size / (1024*1024):.1f} MB")

if __name__ == "__main__":
    download_with_progress(URL, ZIP_PATH)
