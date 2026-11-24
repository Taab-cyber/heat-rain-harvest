"""Census 2011 (PC11) district polygons (DECISIONS D6, D6b).

Source file: data/raw/boundaries/shrug-pc11dist-poly-shp.zip
(Development Data Lab, SHRUG Open Polygons, version 2.2 per its README).
Columns in the file: pc11_s_id, pc11_d_id, d_name, geometry (EPSG:4326).

The file has 641 features: 640 Census 2011 districts plus one feature with
pc11_d_id "000" and no name in state 01 (Jammu and Kashmir) - an area not
assigned to any Census district. It is dropped, leaving 640 districts.
"""
import geopandas as gpd

from src.config import RAW

PC11_ZIP = RAW / "boundaries" / "shrug-pc11dist-poly-shp.zip"


def load_pc11_districts() -> gpd.GeoDataFrame:
    g = gpd.read_file(f"zip://{PC11_ZIP}")
    g["district_id"] = g["pc11_d_id"].astype(int)
    g["state_id"] = g["pc11_s_id"].astype(int)
    g = g[g["district_id"] > 0].copy()            # drop the unnamed, unassigned J&K polygon
    assert len(g) == 640 and g["district_id"].is_unique
    return g[["state_id", "district_id", "d_name", "geometry"]]
