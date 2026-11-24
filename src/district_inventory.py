"""Phase 3 (step 2): inventory of district names in the APY data.

For every (state, district) we record the first and last year it has any data,
the number of years present, and a normalised name used for matching later.
A district whose series starts after 1997 is usually a post-1997 split and must
be mapped back to its Census 2011 parent (DECISIONS D6).

Output: data/interim/apy_district_inventory.csv
"""
import re

import pandas as pd

from src.config import INTERIM


def norm_name(s: str) -> str:
    """Lower-case, drop punctuation and common suffixes so spellings can be compared."""
    s = s.lower().replace("&amp;", "and").replace("&", "and")
    s = re.sub(r"\b(district|dist)\b", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def main() -> None:
    apy = pd.read_parquet(INTERIM / "apy_long.parquet")
    inv = (apy.groupby(["state", "district"])["year"]
              .agg(first_year="min", last_year="max", n_years="nunique")
              .reset_index())
    inv["name_norm"] = inv["district"].map(norm_name)
    inv["starts_late"] = inv["first_year"] > 1997          # candidate post-1997 new district
    inv["ends_early"] = inv["last_year"] < 2022            # candidate renamed/merged/discontinued
    out = INTERIM / "apy_district_inventory.csv"
    inv.to_csv(out, index=False)
    print(f"districts={len(inv)}  starts_late={inv.starts_late.sum()}  ends_early={inv.ends_early.sum()}  "
          f"full_1997_2022={(~inv.starts_late & ~inv.ends_early).sum()}")
    print(f"saved {out}")


if __name__ == "__main__":
    main()
