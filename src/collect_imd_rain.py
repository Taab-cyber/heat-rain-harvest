"""Move IMD rainfall files downloaded through the browser into imdlib's layout.

Why: imdlib's scripted download kept failing for rainfall (IMD server drops the
SSL connection), but the same official files download fine from IMD's page
https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html.

Browser saves  Downloads/Rainfall_ind<YEAR>_rfp25.grd
We move it to  data/raw/imd/rain/<YEAR>.grd   (what imd.open_data expects)
only if its size is exactly 135 x 129 x days x 4 bytes (complete float32 grid).

Run: python -m src.collect_imd_rain --years 1997-2023
"""
import argparse
import re
import shutil
import time

from src.collect_download import DOWNLOADS
from src.config import RAW_IMD
from src.download_imd import expected_bytes, is_complete

FNAME = re.compile(r"Rainfall_ind(\d{4})_rfp25\.grd$")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="1997-2023")
    ap.add_argument("--idle", type=int, default=900)
    a = ap.parse_args()
    y0, y1 = map(int, a.years.split("-"))
    wanted = {y for y in range(y0, y1 + 1) if not is_complete("rain", y)}
    print("waiting for", sorted(wanted), flush=True)
    last = time.time()
    while wanted and time.time() - last < a.idle:
        for f in DOWNLOADS.glob("Rainfall_ind*_rfp25*.grd"):
            m = FNAME.search(f.name)
            if not m:
                continue
            y = int(m.group(1))
            size = f.stat().st_size
            if size != expected_bytes("rain", y):
                continue                       # still downloading or truncated
            dest = RAW_IMD / "rain" / f"{y}.grd"
            if dest.exists():
                f.unlink()                     # already have a complete copy
                continue
            shutil.move(str(f), dest)
            wanted.discard(y)
            last = time.time()
            print(f"{time.strftime('%H:%M:%S')} rain {y} ok {size:,} bytes", flush=True)
        time.sleep(2)
    print("missing:", sorted(wanted) or "none", flush=True)


if __name__ == "__main__":
    main()
