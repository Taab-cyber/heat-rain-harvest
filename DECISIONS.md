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
- **Result (2026-11-24):** tmax/tmin: 640 districts, **64 served by a single 1 deg cell**, median 3 cells per district. Rain: 636 districts, 6 single-cell, median 14 cells. The 4 island districts (Nicobars, North & Middle Andaman, South Andaman, Lakshadweep) have no rainfall: the IMD 0.25 deg grid does not cover them. About 0.4% of daily temperature values are missing (district-days with no cell data that day).

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

### D6a. Unmatched / ambiguous district cases (status 2026-11-24)
- Route used: source name -> LGD current district (exact name within state family, or a reviewed alias listed in `src/district_map.py`) -> LGD "Census 2011 Code" -> PC11 polygon.
- APY: 634 names reach a 2011 district; 113 are post-2011 districts (LGD Census 2011 Code = 0) still needing a parent; 0 unmatched.
- LUS: 690 reach a 2011 district; 104 post-2011; 1 unmatched ("Warangal urban", Telangana; post-2011, renamed Hanumakonda; parent = Warangal).
- Mahe and Yanam (Puducherry) are Census 2011 districts that LGD no longer lists; linked directly to PC11 codes 636 and 634.
- Census districts reached by no crop/LUS name: the 9 Delhi districts and Kolkata (urban, no crop records). Correctly absent.
- **Open:** parents of the post-2011 districts. Planned source: LGD "Download Only Modifications" report (official split/merge history). Until then they are excluded from district-level analysis, and this is stated.

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

## D12. Crop irrigation share (Phase 3, 2026-11-24)
- **Definition:** irr_share = crop-wise irrigated area (LUS) / crop area (APY), per unit-year. Seasons combined.
- **Observed:** the two sources are collected separately, so the ratio can exceed 1. Wheat raw ratio median 0.98, 95th pct 1.16, 99th pct 10.0; rice median 0.78, 99th pct 1.48. Over-1.1 cases cluster in Odisha wheat (mostly < 2,000 ha) and Uttar Pradesh rice.
- **Chosen:** clip 1.0-1.1 to 1.0 (rounding / timing differences); above 1.1 set missing and flag `irr_share_flag` (wheat 588, rice 394 unit-years).
- **Sanity:** Punjab wheat median 1.00 every year; Bihar rice median rises from about 0.40 (1999) to 0.81 (2022).
- **Alternatives:** clip everything to 1 (hides inconsistent data); use net irrigated / net sown (not crop-specific). The district-level `net_irr_intensity` is kept as a second irrigation measure for robustness.
- LUS starts 1998-99, so irr_share is missing for 1997.

## D11. Implausible yields are flagged, not deleted (Phase 3, 2026-11-24)
- **Observed:** e.g. Kolhapur rice 1997 = 224 t/ha, North/South Goa rice 2022 = 39-45 t/ha, Moga wheat 2008 = 7.46 t/ha. Real district-average yields are about 5-6 t/ha at most, so these are reporting/unit errors in the source.
- **Chosen:** `yield_raw` keeps the computed value; `yield_flag` = True if yield > ceiling (wheat 7, rice 8 t/ha) or > 3x / < 1/3 of the unit's own median for that crop and season; `yield_clean` = yield with flagged values set to missing. Analyses use `yield_clean`.
- **Result:** 12,247 of 383,580 yields flagged (3.2%); wheat 100 (0.8%), rice 433 (1.8%). Most flags are minor crops on tiny areas.
- **Alternatives:** keep everything (errors would dominate regressions); delete rows (loses the record and changes counts); winsorise (still keeps impossible values).
- **Sensitivity:** the 3x threshold is a judgement call; Phase 8 re-runs the main model with 2x and 4x.

## D6c. 2011 parents of post-2011 districts via sub-districts (2026-11-24)
- **Problem:** LGD gives "Census 2011 Code = 0" for 152 districts created after 2011, and LGD's "Download Only Modifications" report (kept in data/raw/boundaries/) has no "carved from" column.
- **Chosen:** tehsil route. LGD "All Sub-Districts of India" gives each current tehsil's current district and Census 2011 sub-district code; SHRUG PC11 sub-district file gives each 2011 sub-district's 2011 district. A new district's parent = the 2011 district that most of its tehsils came from (`src/post2011_parents.py`). Exact ties: lower PC11 code wins, flagged `parent_tie`.
- **Validation:** applied to the 627 districts that existed in 2011, the route reproduces LGD's own Census 2011 code for 625 (99.7%); the 2 misses are New Delhi and Chennai (urban, no crop data).
- **Result:** of 152 post-2011 districts, 117 single parent, 27 split across 2-3 parents (majority parent used; share stored in `parent_share`), 8 with no tehsil carrying a 2011 code.
- In our data: APY 87 single-parent + 22 split-parent names; LUS 80 + 21.
- **Tripura:** its 4 districts created in 2012 (Gomati, Khowai, Sepahijala, Unakoti) have no tehsil with a 2011 code, so no parent can be determined. Chosen: aggregate all of Tripura into one unit for analysis (instead of guessing parents).
- **Limitation (paper):** for split districts, all of the new district's area and production is credited to the majority parent, which misallocates a minority share. Robustness check planned in Phase 8: re-run excluding every 2011 district touched by a split child.
- **Alternative considered:** merging all parents linked by split children into composite units. Rejected as primary because chains (e.g. Telangana 534/535/540/541) would merge large areas and lose resolution; kept as a possible robustness check.

## D6b. PC11 polygons downloaded from the original producer, not the AIKosh copy (2026-11-24)
- **What happened:** AIKosh requires a registered login for every file (even the 10-byte .cpg), and the login could not be completed in the automated Chrome profile.
- **Chosen:** the same dataset, "PC11 District Polygons" (SHRUG Open Polygons, Development Data Lab), from its publisher's public download page https://www.devdatalab.org/shrug_download/ (module "Open Polygons and Spatial Statistics", SHP). AIKosh's own dataset card names Development Data Lab as the source and calls the files "version 2.1 of the SHRUG"; DDL's page currently serves SHRUG 2.2.
- **Not a change of dataset:** same producer, same Census 2011 district polygons, same licence (CC BY-NC-SA 4.0). Still no GADM or DataMeet as a direct source.
- **Downloaded file:** `shrug-pc11dist-poly-shp.zip` = SHRUG **version 2.2** (README). 641 features = 640 Census 2011 districts + 1 unnamed, unassigned J&K feature (pc11_d_id 000), which is dropped in `src/boundaries.py`. All 628 Census 2011 codes reached via LGD exist in the polygons.
- **For the paper:** source = Development Data Lab SHRUG Open Polygons (also hosted on AIKosh, GoI); cite Asher, Lunt, Matsuura & Novosad, "Development research at high geographic resolution: an analysis of night-lights, firms, and poverty in India using the SHRUG open data platform", World Bank Economic Review (the citation DDL asks for). The exact version used is recorded from the downloaded files.
- **Check before use:** compare the district count and names with Census 2011 (640 districts) and with the AIKosh file list (district.shp/.dbf/.shx/.prj).
