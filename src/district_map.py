"""Phase 3 (step 5): map APY / LUS district names to Census 2011 (PC11) district codes.

Route (DECISIONS D6):
  APY/LUS (state, district name)  --name match within state-->  LGD current district
  LGD current district            --"Census 2011 Code" column-->  PC11 district code
LGD gives a Census 2011 code for districts that existed in 2011. Districts created
after 2011 have code 0 in LGD and need a parent from LGD's modification history
(or another documented source); they are listed as unmatched until then.

Matching is exact on a normalised name (lower case, no punctuation, "&" -> "and").
A small, explicit alias table handles spelling differences; every alias is
written out here so it can be checked, nothing is matched fuzzily in secret.

Output: data/interim/district_map.csv
  source, state, district, lgd_state, lgd_district, lgd_district_code, pc11_district_code, match_type
"""
import re

import pandas as pd

from src.config import INTERIM, RAW


def norm(s: str) -> str:
    s = str(s).lower().replace("&amp;", "and").replace("&", "and")
    s = re.sub(r"\b(district|dist)\b", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)


# The DES files keep pre-bifurcation state names for some districts (e.g. Ranchi under
# Bihar, Raipur under Madhya Pradesh). A name is therefore looked up in its own state
# first, then in the states carved out of it. Plain names; normalised at run time.
STATE_FAMILY = {
    "Bihar": ["Jharkhand"],
    "Madhya Pradesh": ["Chhattisgarh"],
    "Uttar Pradesh": ["Uttarakhand"],
    "Andhra Pradesh": ["Telangana"],
    "Jammu and Kashmir": ["Ladakh"],
    "Dadra and Nagar Haveli": ["The Dadra And Nagar Haveli And Daman And Diu"],
    "Daman and Diu": ["The Dadra And Nagar Haveli And Daman And Diu"],
    "The Dadra & Nagar Haveli and Daman and Diu": ["The Dadra And Nagar Haveli And Daman And Diu"],
}

# Renames and spelling differences: source name -> LGD name, both copied exactly as
# they appear in the two files (reviewed side by side, 2026-11-24). Looked up within
# the source state's family. Nothing is matched fuzzily.
DISTRICT_ALIASES = {
    # Andhra Pradesh / Telangana
    "Anantapur": "Ananthapuramu", "Kadapa": "Y.S.R. Kadapa", "Konaseema": "Dr. B.R. Ambedkar Konaseema",
    "Spsr nellore": "Sri Potti Sriramulu Nellore", "Visakhapatanam": "Visakhapatnam",
    "Bhadradri": "Bhadradri Kothagudem", "Jayashankar": "Jayashankar Bhupalapally",
    "Jogulamba": "Jogulamba Gadwal", "Komaram bheem asifabad": "Kumuram Bheem Asifabad",
    "Mahbubnagar": "Mahabubnagar", "Medchal": "Medchal Malkajgiri", "Narayanapet": "Narayanpet",
    "Rajanna": "Rajanna Sircilla", "Rangareddi": "Ranga Reddy", "Yadadri": "Yadadri Bhuvanagiri",
    # Assam (Karimganj renamed Sribhumi, 2024)
    "Karimganj": "Sribhumi",
    # Chhattisgarh
    "Baloda bazar": "Balodabazar-Bhatapara", "Balrampur": "Balrampur-Ramanujganj",
    "Dantewada": "Dakshin Bastar Dantewada", "Gaurella-pendra-marwahi": "Gaurela-Pendra-Marwahi",
    "Kabirdham": "Kabeerdham", "Kanker": "Uttar Bastar Kanker",
    "Khairgarh chhuikhadan gandai": "Khairagarh-Chhuikhadan-Gandai",
    "Manendragarh chirimiri bharatpur": "Manendragarh-Chirmiri-Bharatpur(M C B)",
    # Gujarat
    "Ahmadabad": "Ahmedabad", "Aravalli": "Arvalli", "Dang": "Dangs", "Dohad": "Dahod",
    # Haryana
    "Charki dadri": "Charkhi Dadri", "Gurgaon": "Gurugram", "Mewat": "Nuh",
    # Himachal Pradesh, Jammu and Kashmir, Ladakh
    "Lahul and spiti": "Lahaul And Spiti", "Badgam": "Budgam", "Rajauri": "Rajouri", "Leh ladakh": "Leh",
    # Karnataka (Ramanagara renamed Bengaluru South, 2025)
    "Bagalkot": "Bagalkote", "Bangalore rural": "Bengaluru Rural", "Belgaum": "Belagavi",
    "Bellary": "Ballari", "Bijapur": "Vijayapura", "Chikballapur": "Chikkaballapura",
    "Chikmagalur": "Chikkamagaluru", "Dakshin kannad": "Dakshina Kannada", "Davangere": "Davanagere",
    "Gulbarga": "Kalaburagi", "Mysore": "Mysuru", "Ramanagara": "Bengaluru South",
    "Shimoga": "Shivamogga", "Tumkur": "Tumakuru", "Uttar kannad": "Uttara Kannada",
    "Vijayanagar": "Vijayanagara",
    # Madhya Pradesh
    "Hoshangabad": "Narmadapuram", "Khandwa": "Khandwa (East Nimar)",
    "Khargone": "Khargone (West Nimar)", "Narsinghpur": "Narsimhapur",
    # North-east, Sikkim
    "Saiha": "Siaha", "Nuiland": "Niuland", "Geyzing": "Gyalshing",
    # Odisha
    "Anugul": "Anugola", "Bargarh": "Baragada", "Cuttack": "Kataka", "Deogarh": "Debagada",
    "Jajapur": "Jajpur", "Kandhamal": "Kandhamala", "Kendrapara": "Kendrapada",
    "Nayagarh": "Nayagada", "Sonepur": "Subarnapur", "Sundargarh": "Sundaragada",
    # Puducherry, Punjab
    "Pondicherry": "Puducherry", "Firozepur": "Ferozepur", "Muktsar": "Sri Muktsar Sahib",
    "Nawanshahr": "Shahid Bhagat Singh Nagar",
    # Tamil Nadu
    "Kanchipuram": "Kancheepuram", "Thenkasi": "Tenkasi", "Thoothukudi": "Thoothukkudi",
    "Villupuram": "Viluppuram",
    # Uttar Pradesh / Uttarakhand
    "Allahabad": "Prayagraj", "Faizabad": "Ayodhya", "Maharajganj": "Mahrajganj",
    "Sant kabeer nagar": "Sant Kabir Nagar", "Sant ravidas nagar": "Bhadohi", "Shravasti": "Shrawasti",
    "Udam singh nagar": "Udham Singh Nagar",
    # West Bengal
    "24 paraganas north": "North 24 Parganas", "24 paraganas south": "South 24 Parganas",
    "Dinajpur dakshin": "Dakshin Dinajpur", "Dinajpur uttar": "Uttar Dinajpur", "Maldah": "Malda",
    "Medinipur east": "Purba Medinipur", "Medinipur west": "Paschim Medinipur",
    # Telangana: Warangal Urban was renamed Hanumakonda (2021, with boundary changes);
    # both are post-2011 districts, so the parent comes from post2011_parents anyway.
    "Warangal urban": "Hanumakonda",
}


# Census 2011 districts that LGD no longer lists separately: link the source name
# straight to the PC11 polygon code (code checked in the SHRUG district.dbf).
PC11_DIRECT = {
    ("Puducherry", "Mahe"): 636,
    ("Puducherry", "Yanam"): 634,
}


def load_lgd() -> pd.DataFrame:
    path = next((RAW / "boundaries").glob("lgd_all_districts_*.xlsx"))
    d = pd.read_excel(path, header=1)
    d = d[pd.to_numeric(d["S.No."], errors="coerce").notna()].copy()
    d = d.rename(columns={
        "State Name (In English)": "lgd_state", "District Name(In English)": "lgd_district",
        "District Code": "lgd_district_code", "Census 2011 Code": "pc11_district_code",
    })
    d["s_norm"] = d["lgd_state"].map(norm)
    d["d_norm"] = d["lgd_district"].map(norm)
    d["pc11_district_code"] = d["pc11_district_code"].astype(int).replace(0, pd.NA)
    return d[["lgd_state", "lgd_district", "lgd_district_code", "pc11_district_code", "s_norm", "d_norm"]]


def source_names() -> pd.DataFrame:
    apy = pd.read_parquet(INTERIM / "apy_long.parquet", columns=["state", "district"]).drop_duplicates()
    lus = pd.read_parquet(INTERIM / "lus_wide.parquet", columns=["state", "district"]).drop_duplicates()
    apy["source"], lus["source"] = "apy", "lus"
    return pd.concat([apy, lus], ignore_index=True)


def main() -> None:
    lgd = load_lgd()
    by_key = {(r.s_norm, r.d_norm): r for r in lgd.itertuples()}
    alias = {norm(k): norm(v) for k, v in DISTRICT_ALIASES.items()}
    family = {norm(k): [norm(k)] + [norm(x) for x in v] for k, v in STATE_FAMILY.items()}
    src = source_names()
    rows = []
    for r in src.itertuples():
        s, d = norm(r.state), norm(r.district)
        hit, how = None, "unmatched"
        for cand_d, kind in ((d, "exact"), (alias.get(d), "alias")):
            if cand_d is None:
                continue
            for cand_s in family.get(s, [s]):
                if (cand_s, cand_d) in by_key:
                    hit, how = by_key[(cand_s, cand_d)], kind
                    break
            if hit is not None:
                break
        rec = {"source": r.source, "state": r.state, "district": r.district, "name_match": how}
        if hit is None and (r.state, r.district) in PC11_DIRECT:
            rec.update(name_match="pc11_direct", pc11_district_code=PC11_DIRECT[(r.state, r.district)])
        if hit is not None:
            rec.update(lgd_state=hit.lgd_state, lgd_district=hit.lgd_district,
                       lgd_district_code=hit.lgd_district_code, pc11_district_code=hit.pc11_district_code)
        rows.append(rec)
    m = pd.DataFrame(rows)
    for c in ("lgd_state", "lgd_district", "lgd_district_code", "pc11_district_code"):
        if c not in m:
            m[c] = pd.NA
    m["match_type"] = "unmatched"
    m.loc[m.pc11_district_code.notna(), "match_type"] = "pc11_code"                   # existed in 2011
    m.loc[m.lgd_district_code.notna() & m.pc11_district_code.isna(), "match_type"] = "post2011_no_parent"

    # Districts created after 2011: parent from the tehsil route (src/post2011_parents.py, D6c).
    par = pd.read_csv(INTERIM / "post2011_parents.csv")
    par = par.set_index("lgd_district_code")
    need = m["match_type"] == "post2011_no_parent"
    codes = m.loc[need, "lgd_district_code"].astype(int)
    found = codes.isin(par.index)
    idx = codes[found].index
    m.loc[idx, "pc11_district_code"] = par.loc[codes[found], "pc11_parent_code"].values
    m.loc[idx, "parent_share"] = par.loc[codes[found], "parent_share"].values
    m.loc[idx, "parent_tie"] = par.loc[codes[found], "tie"].values
    m.loc[idx, "match_type"] = ["post2011_" + t for t in par.loc[codes[found], "parent_type"]]
    out = INTERIM / "district_map.csv"
    m.to_csv(out, index=False)
    print(m.groupby(["source", "match_type"]).size().unstack(fill_value=0).to_string())
    print(f"saved {out}")


if __name__ == "__main__":
    main()
