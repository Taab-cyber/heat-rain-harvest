"""Read the official reference tables used for production, value and food-equivalent checks (D25).

Inputs (data/raw/official/, never edited):
  asag_2024.pdf                Agricultural Statistics at a Glance 2024, DES, Ministry of Agriculture & FW
                                 p.21  Table 1.1(a)  population, Census 2011 (rural share)
                                 p.47-48 Table 2.4(a) rice, all-India, by year;  p.49 Table 2.4(b) rice, major states
                                 p.50-51 Table 2.5(a) wheat, all-India;          p.52 Table 2.5(b) wheat, major states
                                 p.169 Table 2.71 MSP;  p.171 Table 2.73(a) state cost of production A2+FL (paddy, wheat)
                                 p.188 Table 3.6 per-capita net availability of rice and wheat
  hces_report_2023-24.pdf      NSS Report 592, Household Consumption Expenditure Survey 2023-24, MoSPI
                                 p.52 Table 3.7 monthly per-capita cereal consumption; p.53-54 Tables 3.8R/3.8U shares
  cag_paddy_milling_2015_chap_2.pdf   CAG Report 31 of 2015: out-turn ratio 67 kg raw rice per 100 kg paddy

Every parser checks itself (row totals, shares, column counts) and stops with an error rather than
returning a number it cannot vouch for. Output: data/interim/official/*.csv
"""
from __future__ import annotations

import re

import pandas as pd
import pdfplumber

from src.config import INTERIM, RAW

OFF = RAW / "official"
OUT = INTERIM / "official"
NUM = re.compile(r"^-?\d+(\.\d+)?$")


def _rows(page, tol: float = 3.0) -> list[list[dict]]:
    """Words grouped into text rows by vertical position."""
    rows: list[list[dict]] = []
    for w in sorted(page.extract_words(), key=lambda w: (round(w["top"]), w["x0"])):
        if rows and abs(rows[-1][0]["top"] - w["top"]) <= tol:
            rows[-1].append(w)
        else:
            rows.append([w])
    return [sorted(r, key=lambda w: w["x0"]) for r in rows]


def _split(row: list[dict]) -> tuple[str, list[dict]]:
    """Leading words that are not numbers form the label; the rest are numeric cells."""
    label, nums = [], []
    for w in row:
        if NUM.match(w["text"].replace(",", "")) and (nums or label):
            nums.append(w)
        elif not nums:
            label.append(w["text"])
    return " ".join(label), nums


def _page(pdf, n: int):
    return pdf.pages[n - 1]


def major_states(pdf, pno: int, crop: str) -> pd.DataFrame:
    """Tables 2.4(b)/2.5(b): production (million tonnes) by major state, 2022-23 and 2023-24."""
    page = _page(pdf, pno)
    assert crop.lower() in (page.extract_text() or "").lower()[:120], f"page {pno} is not the {crop} table"
    out = []
    for row in _rows(page):
        label, nums = _split(row)
        if len(nums) != 11 or not re.match(r"^[A-Za-z][A-Za-z &]+$", label):
            continue
        v = [float(w["text"]) for w in nums]
        out.append({"state": label, "prod_2022_mt": v[2], "share_2022_pct": v[3], "prod_2023_mt": v[7],
                    "share_2023_pct": v[8], "area_2022_mha": v[0], "yield_2022_kg_ha": v[4]})
    df = pd.DataFrame(out)
    ai = df[df.state == "All India"].iloc[0]
    for yr in ("2022", "2023"):                      # self-check: each share = production / all-India production
        calc = df[f"prod_{yr}_mt"] / ai[f"prod_{yr}_mt"] * 100
        bad = (calc - df[f"share_{yr}_pct"]).abs() > 0.1
        assert not bad.any(), f"{crop} {yr}: share check failed for {df.state[bad].tolist()}"
    assert len(df) >= 10, f"{crop}: only {len(df)} rows parsed"
    return df.assign(crop=crop)


def all_india(pdf, pages: tuple[int, ...], crop: str) -> pd.DataFrame:
    """Tables 2.4(a)/2.5(a): all-India area, production, yield by agricultural year."""
    out = []
    for p in pages:
        for row in _rows(_page(pdf, p)):
            label, nums = _split(row)
            if re.match(r"^\d{4}-\d{2}$", label) and len(nums) >= 3:
                a, prod, y = (float(w["text"]) for w in nums[:3])
                out.append({"crop": crop, "year": int(label[:4]), "area_mha": a, "prod_mt": prod, "yield_kg_ha": y})
    df = pd.DataFrame(out).drop_duplicates("year")
    chk = (df.prod_mt * 1e3 / df.area_mha - df.yield_kg_ha).abs() / df.yield_kg_ha     # yield = production / area
    assert (chk < 0.02).all(), f"{crop}: yield != production/area in {df.year[chk >= 0.02].tolist()}"
    return df


def msp(pdf, pno: int = 169) -> pd.DataFrame:
    """Table 2.71: MSP (Rs per quintal) by crop year, paddy (common) and wheat."""
    page = _page(pdf, pno)
    rows = _rows(page)
    years = None
    out = []
    for row in rows:
        txt = [w["text"] for w in row]
        if years is None and sum(bool(re.match(r"^\d{4}-\d{2}$", t)) for t in txt) >= 5:
            years = [int(t[:4]) for t in txt if re.match(r"^\d{4}-\d{2}$", t)]
        label, nums = _split(row)
        key = {"1 Paddy Common": "Paddy (common)", "15 Wheat": "Wheat"}.get(label)
        if key:
            assert years and len(nums) == len(years), f"MSP row {label}: {len(nums)} values for {years}"
            out += [{"crop": key, "year": y, "msp_rs_q": float(w["text"])} for y, w in zip(years, nums)]
    df = pd.DataFrame(out)
    assert set(df.crop) == {"Paddy (common)", "Wheat"}, "MSP rows not found"
    return df


def cost(pdf, pno: int = 171) -> pd.DataFrame:
    """Table 2.73(a): projected cost of production A2+FL (Rs per quintal) by state and crop year.
    Some states have blanks, so each number is assigned to the year column it sits under (by position)."""
    page = _page(pdf, pno)
    rows = _rows(page)
    head = next(r for r in rows if sum(bool(re.match(r"^\d{4}-\d{2}$", w["text"])) for w in r) >= 5)
    cols = [(int(w["text"][:4]), w["x1"]) for w in head if re.match(r"^\d{4}-\d{2}$", w["text"])]
    out, crop = [], None
    for row in rows:
        label, nums = _split(row)
        if label in ("Paddy", "Wheat") and not nums:
            crop = label
            continue
        if crop and nums and re.match(r"^[A-Za-z][A-Za-z ]+$", label):
            for w in nums:
                yr, x = min(cols, key=lambda c: abs(c[1] - w["x1"]))
                assert abs(x - w["x1"]) < 12, f"cost: {label} value {w['text']} not under a year column"
                out.append({"crop": crop, "state": label.replace("Uttrakhand", "Uttarakhand"), "year": yr,
                            "cost_a2fl_rs_q": float(w["text"])})
    df = pd.DataFrame(out)
    assert df.duplicated(["crop", "state", "year"]).sum() == 0
    assert {"Punjab", "All India"} <= set(df.state)
    return df


def availability(pdf, pno: int = 188) -> pd.DataFrame:
    """Table 3.6: per-capita net availability (kg per year) of rice and wheat. From 2022 the year is the
    financial year (2022 = 2022-23), per the table's note (v)."""
    out = []
    for row in _rows(_page(pdf, pno)):
        label, nums = _split(row)
        if re.match(r"^\d{4}$", label) and len(nums) >= 6:
            v = [float(w["text"].lstrip(".")) for w in nums]
            out.append({"year": int(label), "rice_kg": v[0], "wheat_kg": v[1], "cereals_kg": v[3]})
    df = pd.DataFrame(out)
    assert len(df) > 30 and df.year.max() >= 2022
    return df


def hces(pdf) -> pd.DataFrame:
    """NSS Report 592 Tables 3.7, 3.8R, 3.8U: monthly per-capita cereal consumption (kg) and the % shares of
    rice and wheat in it, all-India, rural and urban, 2023-24."""
    out = {}
    for sector, pno in (("rural", 53), ("urban", 54)):
        for row in _rows(_page(pdf, pno)):
            label, nums = _split(row)
            if label == "All-India" and len(nums) >= 3:
                kg, rice, wheat = (float(w["text"]) for w in nums[:3])
                out[sector] = {"sector": sector, "cereal_kg_month": kg, "rice_share_pct": rice, "wheat_share_pct": wheat}
    t37 = (_page(pdf, 52).extract_text() or "")
    for sector in ("Rural", "Urban"):                 # cross-check with Table 3.7 (2023-24 is the last column)
        m = re.search(rf"^{sector} .* ([\d.]+)$", t37, re.M)
        assert m and abs(float(m.group(1)) - out[sector.lower()]["cereal_kg_month"]) < 0.005, f"HCES {sector} mismatch"
    return pd.DataFrame(out.values())


def census_rural_share(pdf, pno: int = 21) -> float:
    """Table 1.1(a): 2011 total and rural population (million) -> rural share."""
    for row in _rows(_page(pdf, pno)):
        label, nums = _split(row)
        if label == "2011":
            total, _, rural = (float(w["text"]) for w in nums[:3])
            return rural / total
    raise ValueError("2011 row not found in Table 1.1(a)")


def cag_out_turn() -> float:
    """CAG Report 31 of 2015, chapter 2: 'Out-turn Ratio of production of 67 per cent of raw rice ... out of one
    quintal paddy'. Returned only if that sentence is found in the downloaded report."""
    with pdfplumber.open(OFF / "cag_paddy_milling_2015_chap_2.pdf") as pdf:
        text = " ".join((p.extract_text() or "") for p in pdf.pages)
    assert re.search(r"Out-turn Ratio of production of 67 per cent of raw rice", text), "67% sentence not found"
    return 0.67


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with pdfplumber.open(OFF / "asag_2024.pdf") as pdf:
        states = pd.concat([major_states(pdf, 49, "Rice"), major_states(pdf, 52, "Wheat")])
        ai = pd.concat([all_india(pdf, (47, 48), "Rice"), all_india(pdf, (50, 51), "Wheat")])
        m, c, av = msp(pdf), cost(pdf), availability(pdf)
        rural = census_rural_share(pdf)
    with pdfplumber.open(OFF / "hces_report_2023-24.pdf") as pdf:
        h = hces(pdf)
    otr = cag_out_turn()
    for name, df in (("state_production", states), ("all_india_production", ai), ("msp", m), ("cost_a2fl", c),
                     ("availability", av), ("hces_cereals", h)):
        df.to_csv(OUT / f"{name}.csv", index=False)
    pd.DataFrame([{"key": "census2011_rural_share", "value": rural}, {"key": "out_turn_raw_rice", "value": otr}]).to_csv(
        OUT / "constants.csv", index=False)
    print(states[["crop", "state", "prod_2022_mt"]].to_string(index=False))
    print(ai[ai.year >= 2017].to_string(index=False))
    print(m[m.year == 2022].to_string(index=False))
    print(c[c.year == 2022].pivot(index="state", columns="crop", values="cost_a2fl_rs_q").to_string())
    print(av.tail(3).to_string(index=False)); print(h.to_string(index=False))
    print(f"rural share 2011: {rural:.4f}   out-turn: {otr}")


if __name__ == "__main__":
    main()
