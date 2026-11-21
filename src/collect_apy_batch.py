"""Watch Windows Downloads and file each DES APY export under its own state name.

Used while the APY report is exported state by state in Chrome (Phase 2).
The state is read from the file itself (first "1. <State>" cell), so files
are never mislabelled even if downloads finish out of order.

Run:  python -m src.collect_apy_batch --expect 36
Stops after --expect files or --idle seconds with no new file.
"""
import argparse
import re
import shutil
import time

from src.collect_download import DOWNLOADS, is_finished
from src.config import RAW

STATE_RE = re.compile(rb"<td[^>]*>\s*1\.\s*([^<]+?)\s*</td>")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect", type=int, default=36)
    ap.add_argument("--idle", type=int, default=1800)
    a = ap.parse_args()
    done, last = 0, time.time()
    while done < a.expect and time.time() - last < a.idle:
        for f in sorted(DOWNLOADS.glob("horizontal_crop_vertical_year_report*.xls"),
                        key=lambda p: p.stat().st_mtime):
            s1 = f.stat().st_size
            time.sleep(1.5)
            if f.stat().st_size != s1 or not is_finished(f):
                continue
            m = STATE_RE.search(f.read_bytes())
            name = slug(m.group(1).decode()) if m else f"unknown_{int(time.time())}"
            dest = RAW / "apy" / f"apy_{name}.xls"
            if dest.exists():
                dest = dest.with_name(dest.stem + f"_dup{int(time.time())}.xls")
            shutil.move(str(f), dest)
            done += 1
            last = time.time()
            print(f"{time.strftime('%H:%M:%S')} {dest.name} {s1:,} bytes", flush=True)
        time.sleep(1)
    print(f"collector finished: {done} files", flush=True)


if __name__ == "__main__":
    main()
