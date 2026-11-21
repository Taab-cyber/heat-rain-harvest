"""Move a finished browser download from Windows Downloads into data/raw/ (Phase 2).

The DES portal exports are made by hand-driven browser clicks; this helper only
moves the delivered file, byte-for-byte, and names it consistently.

Usage:
    python -m src.collect_download apy apy_punjab.xls [--pattern 'horizontal_crop_vertical_year_report*']

Waits up to --timeout seconds for a matching file that is (a) complete
(ends with </table> for the HTML-based DES "Excel" export) and (b) no longer
growing, then moves it. Refuses to overwrite an existing file.
"""
import argparse
import shutil
import sys
import time
from pathlib import Path

from src.config import RAW

DOWNLOADS = Path("/mnt/c/Users/HP/Downloads")


def is_finished(f: Path) -> bool:
    with f.open("rb") as fh:
        fh.seek(max(0, f.stat().st_size - 400))
        return b"</table>" in fh.read()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("subdir", choices=["apy", "lus", "boundaries"])
    ap.add_argument("name")
    ap.add_argument("--pattern", default="horizontal_crop_vertical_year_report*")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--no-table-check", action="store_true", help="for ZIP/CSV downloads")
    a = ap.parse_args()

    dest = RAW / a.subdir / a.name
    if dest.exists():
        sys.exit(f"refusing to overwrite {dest}")
    t0 = time.time()
    while time.time() - t0 < a.timeout:
        hits = sorted(DOWNLOADS.glob(a.pattern), key=lambda p: p.stat().st_mtime)
        hits = [h for h in hits if not h.name.endswith((".crdownload", ".tmp"))]
        if hits:
            f = hits[-1]
            s1 = f.stat().st_size
            time.sleep(1.5)
            if f.stat().st_size == s1 and (a.no_table_check or is_finished(f)):
                shutil.move(str(f), dest)
                print(f"{dest.relative_to(RAW)} {s1:,} bytes")
                return
        time.sleep(1)
    sys.exit(f"TIMEOUT waiting for {a.pattern}")


if __name__ == "__main__":
    main()
