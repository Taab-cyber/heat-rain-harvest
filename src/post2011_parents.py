"""Phase 3 (step 6): 2011 parent district(s) of districts created after Census 2011.

Official, reproducible route (DECISIONS D6c):
  LGD sub-district list:  current tehsil -> current district (LGD code) + Census 2011 sub-district code
  SHRUG PC11 sub-districts: Census 2011 sub-district code -> Census 2011 district (pc11_d_id)
For each current district we count its tehsils by 2011 parent district.
  * one parent  -> clean mapping
  * >1 parents  -> "split_parent": the new district took tehsils from several 2011
                   districts; we assign the parent holding most of its tehsils and
                   record the share, so the choice is visible (D6a)
  * no tehsil with a 2011 code -> no parent (left out, listed)

Tehsils with Census 2011 code 0 were themselves created after 2011 and cannot vote.
Output: data/interim/post2011_parents.csv
"""
import pandas as pd
import pyogrio

from src.config import INTERIM, RAW


def load_lgd_subdistricts() -> pd.DataFrame:
    path = next((RAW / "boundaries").glob("lgd_all_subdistricts_*.xlsx"))
    d = pd.read_excel(path, header=1)
    d = d[pd.to_numeric(d["S.No."], errors="coerce").notna()].copy()
    d["lgd_district_code"] = d["District Code"].astype(int)
    d["pc11_sd_id"] = pd.to_numeric(d["Census 2011 Code"], errors="coerce").fillna(0).astype(int)
    return d[["lgd_district_code", "District Name", "Sub-district Name", "pc11_sd_id"]]


def load_pc11_subdistricts() -> pd.DataFrame:
    z = RAW / "boundaries" / "shrug-pc11subdist-poly-shp.zip"
    sd = pyogrio.read_dataframe(f"zip://{z}!subdistrict.shp", read_geometry=False)
    sd["pc11_sd_id"] = sd["pc11_sd_id"].astype(int)
    sd["pc11_d_id"] = sd["pc11_d_id"].astype(int)
    return sd[sd["pc11_sd_id"] > 0][["pc11_sd_id", "pc11_d_id"]].drop_duplicates()


def main() -> None:
    lgd_sd = load_lgd_subdistricts()
    pc11_sd = load_pc11_subdistricts()
    j = lgd_sd[lgd_sd.pc11_sd_id > 0].merge(pc11_sd, on="pc11_sd_id", how="left")
    print(f"LGD tehsils with a 2011 code: {len(j):,}; of which found in PC11 sub-districts: {j.pc11_d_id.notna().sum():,}")
    j = j.dropna(subset=["pc11_d_id"])
    counts = (j.groupby(["lgd_district_code", "pc11_d_id"]).size().rename("n_tehsils").reset_index())
    tot = counts.groupby("lgd_district_code")["n_tehsils"].transform("sum")
    counts["share"] = counts["n_tehsils"] / tot
    # Most tehsils first; on an exact tie the lower PC11 code wins (fixed rule, flagged below).
    counts = counts.sort_values(["lgd_district_code", "n_tehsils", "pc11_d_id"],
                                ascending=[True, False, True], kind="stable")
    best = counts.groupby("lgd_district_code").head(1).copy()
    top2 = counts.groupby("lgd_district_code")["n_tehsils"].apply(lambda s: len(s) > 1 and s.iloc[0] == s.iloc[1])
    best["tie"] = best["lgd_district_code"].map(top2)
    n_par = counts.groupby("lgd_district_code").size()
    best["n_parents"] = best["lgd_district_code"].map(n_par)
    best["parent_type"] = best["n_parents"].map(lambda k: "single_parent" if k == 1 else "split_parent")
    best["all_parents"] = best["lgd_district_code"].map(
        counts.groupby("lgd_district_code").apply(
            lambda g: "; ".join(f"{int(p)}:{n}" for p, n in zip(g.pc11_d_id, g.n_tehsils)), include_groups=False))
    best = best.rename(columns={"pc11_d_id": "pc11_parent_code", "share": "parent_share"})
    best["pc11_parent_code"] = best["pc11_parent_code"].astype(int)
    best.to_csv(INTERIM / "post2011_parents.csv", index=False)
    print(best.parent_type.value_counts().to_string())
    print(f"saved {INTERIM / 'post2011_parents.csv'}")


if __name__ == "__main__":
    main()
