# DECISIONS

Each entry: what was chosen, the alternatives, and why. Newest at the bottom.

## D1. Study window 1997-98 to 2022-23 (Phase 2)
- **Chosen:** agricultural years 1997-98 to 2022-23 (26 seasons). Weather downloaded for calendar 1997 to 2023.
- **Alternatives:** start in 1966 (ICRISAT district database: not a government source, so not allowed); end in 2023-24 (not yet on the APY portal).
- **Why:** these are the years the DES APY portal offers. Calendar 2023 weather is needed because the 2022-23 rabi season ends in March/April 2023.

## D2. APY and LUS acquired manually (Phase 2)
- **Chosen:** manual Excel export, one file per state (docs/MANUAL_DOWNLOADS.md).
- **Alternatives:** scripting the portal's internal POST endpoint.
- **Why:** the report form uses a per-session token. Automating around it would bypass the portal's access control, so we don't. The project rules also require manual download where a form is involved.

## D3. Download all crops, not only wheat and rice (Phase 2)
- **Chosen:** export "All Crops" and every season.
- **Alternatives:** wheat and rice only.
- **Why:** wheat plus rice at district-year level is expected to be roughly 20-35k rows (to be verified after download), below the 50,000 requirement. The full all-crop APY panel is the honest way to reach it. No padding: the extra rows are real crop-district-season-years. The main hypotheses stay focused on wheat and rice; other crops are used for the descriptive atlas and as a robustness check.

## D4. Coarse 1.0 deg temperature grid (planned, Phase 3)
- **Chosen:** area-weighted district average, where each cell's weight is the share of district area falling in that cell. For small districts that sit inside a single 1 deg cell (about 110 km), the district gets that cell's value.
- **Alternatives:** nearest cell to the centroid; bilinear interpolation to 0.25 deg first.
- **Why:** area weighting is consistent with how rainfall is handled, and it doesn't invent sub-grid detail. Limitation, recorded honestly: neighbouring small districts often share identical temperature values, which reduces the effective number of independent temperature observations. We will report how many districts share a cell.

## D5. Time-based validation: train <= 2017, test 2018-2022 (planned, Phase 8)
- **Alternatives:** random K-fold (leaks future climate and trend information); leave-one-year-out (used as a secondary check).
- **Why:** the forecasting use case predicts future years, so the test set must be in the future.

## D6. Boundaries: fixed Census 2011 (PC11) districts (decided by Mehtaab, 2026-11-21)
- **Chosen:** PC11 district polygons from AIKosh (Government of India IndiaAI portal),
  https://aikosh.indiaai.gov.in/home/datasets/details/2011_population_census_district_polygon_geometries.html
  Licence CC BY-NC-SA 4.0 (non-commercial academic use is OK). 29.71 MB.
- **Cross-check only:** Survey of India Administrative Boundary Database, used to sanity-check outlines and as the official citation. Not the analysis base.
- **Rejected:** DataMeet and GADM as direct sources (not official). Census office PDF maps (not machine-readable).
- **Provenance, stated honestly in the paper:** the dataset card names Development Data Lab as the source organisation; AIKosh hosts it. The polygons are compiled from SEDAC, Bharatmaps, Datameet and the Administrative Atlas of India, with up to about 1 km boundary error in places.
- **Method:** every dataset (APY, LUS, climate) is harmonised to fixed PC11 districts. Districts created after 2011 are mapped back to their 2011 parent through LGD codes and a documented mapping table (`data/interim/district_map_pc11.csv`, built in Phase 3). Area and production are summed and yield is recomputed as production / area. We never average yields.
- **Why fixed 2011 units:** India went from about 640 districts (2011) to more than 750. Without fixed units, one district's time series breaks every time it is split, and yield shocks get confused with boundary changes.
- **Known risk:** if a post-2011 district was carved out of *two* 2011 parents, it can't be assigned cleanly. These cases are listed in D6a (to be filled in during Phase 3) and mentioned in the paper's limitations.

### D6a. Unmatched / ambiguous district cases
To be filled in from the real data in Phase 3.

## D7. Drop portal aggregate "crops" (Phase 3)
- **Chosen:** remove "Oilseeds total", "Pulses total", "Total foodgrain", "Jute & mesta" (1,193 rows) from the APY long table.
- **Alternatives:** keep them as separate crops.
- **Why:** they are sums of other crops in the same file, so keeping them double-counts area and production and inflates the row count used for the 50,000 requirement.

## D3 verified (2026-11-24)
All-crop APY long table = 406,612 rows (>= 50,000). Wheat + rice = 37,995 rows, which alone would not meet the requirement.

## D8. IMD rainfall downloaded from IMD's own web page (Phase 2, 2026-11-24)
- **Chosen:** download yearly 0.25 deg rainfall binaries from https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html in the browser; `src/collect_imd_rain.py` moves each file into imdlib's layout (`data/raw/imd/rain/<year>.grd`) only if its size is exactly 135 x 129 x days x 4 bytes.
- **Alternatives:** imdlib's scripted download (failed for every rainfall year: IMD server dropped the SSL connection 8/8 times); unofficial mirrors (not allowed).
- **Why:** same official IMD product, same file format; the size check guarantees no truncated file is used. tmax/tmin still come from imdlib.

## D9. Land Use Statistics scope (Phase 2)
- **Chosen:** export the classification groups "land use", "sources of irrigation" and "crop-wise irrigated area"; leave out "area under crops".
- **Why:** "area under crops" duplicates APY and doubled the file size (Punjab 24.5 MB -> 12.8 MB). LUS starts at 1998-99, so irrigation is missing for 1997-98.

## D10. Crop-wise irrigated area from LUS (Phase 3)
- **Observed (not assumed):** the portal header gives irrigated rice the season sub-columns Autumn / Winter / Summer / Total (a few files use Kharif / Rabi). Header and data cell counts match (183 = 183), so this is the portal's own labelling (traditional aus / aman / boro rice seasons), not a parsing shift. E.g. Ludhiana 1998: 241,124 ha irrigated rice is filed under "Autumn".
- **Chosen:** `rice_irrigated_ha` = portal Total if present, else the sum of the season columns present; same rule for `wheat_irrigated_ha`. Missing stays missing (never 0).
- **Alternatives:** use one season column only (would undercount in states using Winter/Summer rice).
- **Why:** gives one comparable irrigated-area number per district-year without relabelling the portal's data. Irrigation share = irrigated area (LUS) / crop area (APY), computed after both are on 2011 districts.
- Dropped 950 "Total of <State>" rows (state sums).
