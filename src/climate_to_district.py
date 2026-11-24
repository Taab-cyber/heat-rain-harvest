"""Phase 3 (step 4): IMD gridded daily weather -> daily district averages.

Method (DECISIONS D4): area-weighted average.
  1. Turn every grid cell centre into a square cell polygon (0.25 deg for rain,
     1.0 deg for tmax/tmin).
  2. Intersect cells with each Census-2011 district polygon (equal-area CRS,
     EPSG:6933, so areas are in m^2 and comparable across latitudes).
  3. weight(cell, district) = intersection area / sum of intersection areas of
     that district over cells that have data.  Cells that are all-NaN (sea,
     outside India) get no weight.
  4. district value(day) = sum_i weight_i * value_i(day).

Coarse 1 deg temperature: a small district may sit inside a single 1 deg cell
(~110 km), in which case it simply gets that cell's value; neighbouring small
districts can therefore share identical temperature series. We report how many
districts are served by a single temperature cell (see main()).

Inputs : data/raw/imd/{rain,tmax,tmin}/YYYY.grd, district polygons GeoDataFrame
Outputs: data/interim/climate_<var>_daily.parquet  (district_id, date, value)
         data/interim/grid_weights_<var>.parquet
"""
import argparse

import geopandas as gpd
import imdlib as imd
import numpy as np
import pandas as pd
from shapely.geometry import box

from src.config import INTERIM, RAW_IMD

RES = {"rain": 0.25, "tmax": 1.0, "tmin": 1.0}
EQUAL_AREA = "EPSG:6933"


def load_grid(var: str, start: int, end: int):
    """Return xarray DataArray (time, lat, lon) with IMD missing values as NaN."""
    ds = imd.open_data(var, start, end, "yearwise", str(RAW_IMD)).get_xarray()
    da = ds[var]
    return da.where(da > -98)          # IMD uses -999 (rain) / 99.9 (temp) as fill
                                        # temps: 99.9 handled below


def clean_temperature(da):
    return da.where(da < 99)            # IMD temperature fill value is 99.9


def build_weights(da, districts: gpd.GeoDataFrame, var: str) -> pd.DataFrame:
    res = RES[var]
    has_data = da.notnull().any("time").values               # (lat, lon) cells with any data
    lats, lons = da["lat"].values, da["lon"].values
    rows = [(i, j, box(lons[j] - res / 2, lats[i] - res / 2, lons[j] + res / 2, lats[i] + res / 2))
            for i in range(len(lats)) for j in range(len(lons)) if has_data[i, j]]
    cells = gpd.GeoDataFrame({"ilat": [r[0] for r in rows], "ilon": [r[1] for r in rows]},
                             geometry=[r[2] for r in rows], crs="EPSG:4326").to_crs(EQUAL_AREA)
    d = districts[["district_id", "geometry"]].to_crs(EQUAL_AREA)
    ov = gpd.overlay(d, cells, how="intersection", keep_geom_type=True)
    ov["area"] = ov.geometry.area
    ov["weight"] = ov["area"] / ov.groupby("district_id")["area"].transform("sum")
    return pd.DataFrame(ov[["district_id", "ilat", "ilon", "weight"]])


def aggregate(da, w: pd.DataFrame) -> pd.DataFrame:
    vals = da.values                                          # (time, lat, lon)
    out = []
    for did, g in w.groupby("district_id"):
        cell_vals = vals[:, g["ilat"].values, g["ilon"].values]          # (time, ncells)
        wt = np.broadcast_to(g["weight"].values, cell_vals.shape)
        ok = ~np.isnan(cell_vals)
        # renormalise per day over cells that have data that day
        num = np.nansum(cell_vals * wt, axis=1)
        den = np.where(ok, wt, 0).sum(axis=1)
        series = np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
        out.append(pd.DataFrame({"district_id": did, "date": da["time"].values, "value": series}))
    return pd.concat(out, ignore_index=True)


def run(var: str, districts: gpd.GeoDataFrame, start: int, end: int, tag: str = "") -> None:
    """tag='' -> the 1997-2023 files used by the crop models; tag='longrun' -> separate
    long-run files (Phase 10), so the crop-model inputs stay exactly reproducible."""
    # Long periods are processed 10 years at a time: 125 years of the 0.25 deg rain grid would need
    # about 6 GB of memory at once. Weights come from the first chunk (the IMD land mask is fixed).
    chunks = [(y, min(y + 9, end)) for y in range(start, end + 1, 10)]
    parts, w = [], None
    for c0, c1 in chunks:
        da = load_grid(var, c0, c1)
        if var in ("tmax", "tmin"):
            da = clean_temperature(da)
        if w is None:
            w = build_weights(da, districts, var)
        part = aggregate(da, w)
        part["value"] = part["value"].astype("float32")
        parts.append(part)
        del da
    sfx = f"_{tag}" if tag else ""
    w.to_parquet(INTERIM / f"grid_weights_{var}{sfx}.parquet", index=False)
    ncell = w.groupby("district_id").size()
    print(f"{var}{sfx}: districts={ncell.size}, served by a single cell={int((ncell == 1).sum())}, "
          f"median cells per district={int(ncell.median())}, years {start}-{end}")
    out = pd.concat(parts, ignore_index=True)
    out["value"] = out["value"].astype("float32")              # halves the file; 0.01 C / 0.01 mm precision kept
    out.to_parquet(INTERIM / f"climate_{var}{sfx}_daily.parquet", index=False)


def main() -> None:
    from src.boundaries import load_pc11_districts   # written once boundary files are available
    ap = argparse.ArgumentParser()
    ap.add_argument("--vars", nargs="+", default=["tmax", "tmin", "rain"])
    ap.add_argument("--start", type=int, default=1997)
    ap.add_argument("--end", type=int, default=2023)
    ap.add_argument("--tag", default="", help="'longrun' writes climate_<var>_longrun_daily.parquet")
    a = ap.parse_args()
    districts = load_pc11_districts()
    for var in a.vars:
        run(var, districts, a.start, a.end, a.tag)


if __name__ == "__main__":
    main()
