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

## D19. Feature-engineering iteration and model choice (Phase 8, 2026-11-24)
- **Trigger:** first run (D18) barely beat the trend-only baseline for wheat (best +4% skill) and not at all for rice; models did not help in the 2021-22 heatwave year.
- **Diagnosis:** 2018-22 yields came in +8.5% (wheat) / +6% (rice) above the 1997-2017 trend, a common shift no weather variable can explain; rice yield mixed dry-season (boro/rabi) rice with a monsoon-only weather window.
- **Tried (agronomy-driven):** wheat: February tmax, extreme degree days above 30 C in Feb-Mar, preceding monsoon (Jun-Sep) rain; rain as log(1 + mm) so deviations are ~% of normal; rice: monsoon-season rice only ("Rice (monsoon)" = Kharif + Autumn + Winter seasons), monthly monsoon rain.
- **Selection rule:** feature version chosen by leave-years-out CV on **training years only** (not on the test set, to avoid test-set overfitting). CV skill (Ridge): wheat v1 +0.6%, v2 +1.6% -> v2; rice all-seasons v1 +2.0%, monsoon v1 +2.1%, monsoon v2 +0.2% -> monsoon v1. A few test-set looks happened before this rule was adopted; this is disclosed.
- **Finding:** weather explains only about 1-2% of out-of-sample yield-anomaly variance. This is consistent with Phase 6: effects are significant but small relative to other year-to-year noise (anomaly sd about 19%; a typical +/-0.5 C night-temperature swing moves yield about +/-2%).
- **Limitation:** LUS irrigated rice covers all seasons, so irr_share for monsoon rice is approximate (more > 1.1 flags: 1,453).

## D18. Prediction set-up (Phase 8)
- **Split:** train 1997-2017, test 2018-2022 (time-based; D5). Hyper-parameters by GroupKFold over training years.
- **Target:** relative anomaly vs the train-only trend; yield_hat = trend_train x (1 + anomaly_hat). Baseline = trend_train.
- **Leak-free features:** within-district deviations from training-year means; irrigation = district's training-period mean share (same-year LUS irrigation is not known before harvest).
- **Models:** FE regression (OLS on within features + irrigation interactions), Ridge (alpha by CV), Random forest and HistGradientBoosting (small grids), loss classifiers (logistic balanced, GBM) vs the district's historical loss frequency.
- **Metrics:** RMSE, MAE (t/ha), skill vs baseline = 1 - MSE/MSE_baseline, correlation of anomalies; classifier ROC-AUC, PR-AUC, Brier.
- **Pre-harvest wheat forecast:** the wheat window ends 31 March and the preceding monsoon is known before sowing, so the wheat model is a pre-harvest forecast by construction (harvest is April).
- **Warming scenarios:** +1 / +2 C added to every daily tmax and tmin, features recomputed from daily data, applied to the 2018-22 seasons with the FE regression; rain unchanged, no adaptation (same sowing dates, varieties, irrigation). Extrapolation beyond observed variation is a stated limitation.

## D17. Pattern finding choices (Phase 7, 2026-11-24)
- **Unit and period:** one row per district, profiles from 1997-2017 only (`src/profiles.py`), so zones, propagated labels and selected features never use test years. Wheat profile needs >= 15 sample years (368 districts). Missing irrigation mean (17 districts) filled with the median.
- **Features for zones:** hot_days_mean, tmin_mean, rain_cv, yield_mean, yield_trend_kg, anom_sd, loss_share, heat_sens, irr_mean, all z-scored.
- **k:** chosen by the best silhouette over k = 2..8 -> **k = 5** (silhouette 0.292; agreement with Ward clustering ARI = 0.61). A first run with a fixed k = 4 had silhouette 0.224 and ARI 0.43, so it was replaced. Zones are ordered by observed loss share and named by profile.
- **Label propagation:** label "high risk" = loss years >= 30% of 1997-2017; kNN graph (k = 10) on 6 climate-only features for 637 districts; LabelSpreading alpha = 0.2. Validation (hide 30% of labels, 30 repeats): balanced accuracy 0.64 vs 0.59 (supervised kNN) vs 0.50 (chance). Modest; propagated values are climate-similarity guesses, not observed losses.
- **Feature selection (train years only):** within-district deviations; 3 votes (mutual information top-6, Lasso nonzero with year-grouped CV, RF permutation importance top-6), keep >= 2 votes, then drop one of any pair with |r| > 0.85. Selected: gdd, mar_tmax_mean, tmin_mean, rain_total.
- **Warning recorded:** RF permutation importance was negative for most features on held-out years and Lasso kept only tmin_mean, so weather explains little of out-of-sample year-to-year variation. Phase 8 must check honestly whether any model beats the trend-only baseline.
- **Alternatives:** DBSCAN (no k, but density varies a lot between regions); Gaussian mixtures; UMAP (not installed).

## D16. Which inference to trust (Phase 6, 2026-11-24)
- **Problem:** district-years are not independent (same district over years, same weather across neighbours), and anomalies are heavy-tailed (excess kurtosis about 23). Simple t/ANOVA/chi-square p-values are therefore too optimistic.
- **Chosen as the main test:** OLS with district fixed effects + year fixed effects, standard errors clustered by district (statsmodels `cov_type="cluster"`), plus a cluster bootstrap (resample districts, 2,000 draws, seed 42) for key differences. Simple tests are shown for teaching and as consistency checks.
- **Hot March definition for group tests:** >= 3 more days > 35 C than the district's own mean. Drought (rice): Jun-Sep rain >= 20% below the district's mean.
- **Alternatives:** two-way clustering (district and year) or Conley spatial errors (better for spatially correlated weather; not used because it needs extra packages, so listed as a limitation); linearmodels PanelOLS (same estimates, not installed).
- **Results recorded:** wheat night temp about -4.2% per +1 C (p < 0.001); +10 hot March days about -1.8% (p = 0.017); wheat heat x irrigation interaction +0.045 (p = 0.10; p = 0.045 without MP 2018+: suggestive only); rice monsoon deficit x irrigation -0.19 (p < 0.0001: irrigation buffers drought).
- **Multiple testing:** for families of exploratory tests use Benjamini-Hochberg FDR; report Bonferroni/Holm alongside.

## D15. Madhya Pradesh area/production series break from 2018 (Phase 5, 2026-11-24)
- **Observed:** MP wheat area in APY: 5.8 Mha (2017), 7.7 (2018), 10.2 (2019), about 9.5-9.8 after. District examples: Shivpuri 76,900 ha (2017) -> 311,478 ha (2019); Mandsaur 86,300 -> 238,130. Exactly one APY row per district-season, so this is in the source, not a processing double count. Production rose with area, so district **yields** stay in their usual range (Shivpuri 2.7-3.3, Rajgarh 2.9-3.5 t/ha).
- **Interpretation:** a break in the reported area/production series (cause not determinable from the data: real expansion or a change in collection). Not assumed either way.
- **Chosen:** (1) national/regional averages use fixed area weights (each unit's 1997-2017 mean area) so reporting changes cannot shift them; (2) all regressions include year fixed effects; (3) Phase 8 robustness check excluding MP 2018+.
- **Side effect found:** with fixed weights, the 1997-2022 trend in mean March tmax over wheat districts is about 0 (+0.01 C/decade) and March hot days rise only +0.28 days/decade. The earlier "+0.28 C/decade" came from changing weights. Short window; the warming scenarios rely on estimated sensitivities, not on this trend.

## D13. Crop-season windows and weather features (Phase 4, 2026-11-24)
- **Wheat (rabi):** 1 Nov Y to 31 Mar Y+1. Ends on 31 March so the same window serves the pre-harvest forecast (weather only up to end of March). Alternative: Nov-Apr (more complete, but April is after the forecast cutoff and overlaps harvest).
- **Rice (kharif):** 1 Jun to 31 Oct Y; dry spells counted Jun-Sep (core monsoon). Alternative: state-specific crop calendars (better, but no single official machine-readable calendar for all districts). Limitation: rice yield combines all seasons (rabi/summer rice in the east and south), while the weather window is kharif only.
- **GDD:** daily mean T = (tmax+tmin)/2; GDD = sum max(0, min(T, T_upper) - T_base). Wheat base 0 C, cap 30 C; rice base 10 C, cap 35 C. Common choices in the crop literature; the simple mean-temperature method is used because only daily max/min exist.
- **Extreme heat:** EDD = sum max(0, tmax - 34 C) for wheat (Lobell et al. 2012 used 34 C for Indian wheat), 35 C for rice; plus count of days with tmax > 35 C (wheat: March only, the grain-filling month).
- **Rain:** season total; rainy days = rain >= 2.5 mm (IMD rainy-day definition); variability = coefficient of variation of monthly totals; longest dry spell = longest run of days < 2.5 mm.
- **Missing data:** a season feature is missing if > 10% of its days lack data, or if the season is not fully covered by the data (e.g. Jan-Mar 1997 only).
- **Tripura unit:** daily weather = area-weighted mean of its 2011 districts (areas in EPSG:6933).

## D14. Analysis sample, detrending and the yield-loss event (Phase 4)
- **Sample:** crop area >= 1,000 ha and a clean yield (`in_sample`). Wheat 9,793 unit-years (444 units), rice 13,052 (575). Tiny areas give very noisy yields. Alternative: weight by area (planned as robustness in Phase 8).
- **Detrending:** linear trend per unit (captures technology/varieties). Two versions:
  `trend_full` (all years; descriptive EDA and statistics only) and `detrend_train_only()` (fit on years <= 2017, extrapolated; used for every prediction task). A test (`tests/test_no_leakage.py`) proves the train-only trend ignores test years. Alternatives: quadratic trend or year fixed effects (used in the regressions).
- **Yield loss:** relative anomaly < -10% (`yield_loss`). Share: wheat 21.9%, rice 23.3% of the sample. Threshold sensitivity (-5%, -15%) to be checked in Phase 8.

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

## D20. Long-run climate trends: data, units and statistics (Phase 10, 2026-11-25)
- **Data:** IMD gridded daily tmax/tmin 1951-2025 (1 deg) and rainfall 1901-2025 (0.25 deg), downloaded with imdlib from IMD Pune (same source as Phases 3-8). Rain 1901-1996 was scripted this time (imdlib worked; earlier it failed on SSL).
- **Separate files:** long-run district series are written as `climate_<var>_longrun_daily.parquet` (flag `--tag longrun`), so the 1997-2023 inputs of the crop models stay byte-for-byte reproducible. Processed in 10-year chunks (memory); grid weights from the first chunk (IMD land mask is fixed).
- **India values:** district values averaged with district-area weights, so each part of the country counts in proportion to its land area.
- **Trend statistic:** Sen's slope (median of pairwise slopes) per decade with the Mann-Kendall test. Chosen because it is robust to outlier years (e.g. 2009 drought, 1987) and needs no normality; OLS slope is reported alongside and agrees closely. Serial correlation is not corrected (no pre-whitening), so p-values are slightly optimistic: stated as a limitation.
- **Baseline normal:** 1951-1980 (first 30 years of the temperature record; WMO-style 30-year normal). "Recent" = 1996-2025.
- **Seasons:** IMD's four: winter DJF (December counted with the following year), pre-monsoon MAM, monsoon JJAS, post-monsoon ON.
- **Not done:** no extrapolation of trends into the future. Future statements cite IPCC AR6 / MoES (2020) projections instead.

## D21. Winter, hot-day and monsoon indices (Phase 10, 2026-11-25)
- **Cool day:** Oct-Mar day whose 7-day running mean of tmean is below the district's own 1951-1980 all-year 25th percentile of that 7-day mean (i.e. colder than the coolest quarter of the year in the old climate). Relative (per district) so a "cool day" in Kerala and in Punjab are comparable. **Cold night:** tmin below the district's 1951-80 DJF 10th percentile (ETCCDI-style TN10p). First/last cool day = start/end of the cool spell (days after 1 October).
- **Hot days:** tmax >= 40 C (IMD heatwave threshold for plains), and March tmax >= 35 C (wheat grain-fill heat, as in D13).
- **Monsoon:** IMD thresholds - rainy day >= 2.5 mm, heavy >= 64.5 mm, very heavy >= 115.6 mm, extremely heavy >= 204.5 mm; longest dry spell = longest run of < 2.5 mm days in JJAS; deficient = JJAS rain more than 19% below the district's 1951-2000 mean (IMD's "deficient" cut-off applied to each district).
- **Caveat:** district averages smooth single-station extremes, so heavy-rain-day counts are lower than station counts; the trend direction is what matters.

## D22. Linking long-run warming to harvests, and non-weather harvest factors (Phase 10, 2026-11-25)
- **Implied yield effect** = season night warming (1996-2025 minus 1951-1980; wheat Nov-Mar labelled by harvest year, rice Jun-Oct) x the main Phase 8 robust night-heat coefficient, area-weighted over districts. Back-of-envelope: assumes the 1997-2022 sensitivity held earlier; ignores adaptation, varieties and CO2.
- **Cross-district check:** Spearman correlation of district warming rate (1951-2025) with district yield trend (1997-2022). Reported, but not interpreted causally (confounded by region).
- **Harvest factors tested:** only those available from official sources without an account: (a) previous season's yield anomaly vs the train-only trend (known before sowing, so leak-free); (b) tubewell share of net irrigated area (DES LUS), averaged over training years only. Judged by 5-fold GroupKFold-by-year CV inside 1997-2017; the 2018+ test set scored once. Same rows for every variant.
- **Not tested (blocked):** groundwater levels (India-WRIS needs sign-in with captcha; CGWB static files cover only 2018, 2019, 2021), NDVI (ISRO Bhuvan/VEDAS need an account; NASA MODIS needs Earthdata login - awaiting the team's approval), fertiliser and machinery (Agricultural Input Survey tables not found as a direct download), soil health card data, MSP/Agmarknet prices (data.gov.in API needs the team's own key). Steps for the team are in docs/MANUAL_DOWNLOADS.md.

## D23. Separate attribution model, year fixed effects, wider error clustering (review fixes, 2026-11-26)
- **Problem found in review:** the warming scenarios used the forecasting regression (district effects only, training years only). Shocks that hit all of India in one year (prices, policy, a national pest outbreak) could be credited to heat. That model also had ~30 correlated columns with no regularisation, and its intervals resampled districts only, although neighbouring districts share weather (64 share one 1 deg temperature cell) and all districts share each year.
- **Chosen:**
  1. Forecasting and attribution are separate. Forecasting keeps D18 (train years only, no year effects, because next year's national shock is unknown). Attribution (`fit_attribution`) uses all in-sample years with **district + year fixed effects** (two-way demeaning, `twoway_demean`). Effects cancel in a scenario, so only the slopes matter.
  2. Main scenario model = two-way FE **Ridge** (alpha by leave-years-out CV). `scenario_model_comparison_<crop>.csv` reports it next to two-way FE OLS, a parsimonious two-way FE OLS (night temperature, extreme degree days, rain) and the old model. If they disagree a lot, the headline number is fragile and we say so.
  3. Uncertainty: the robustness regression reports district, state and two-way (district + year) clustered CIs; the scenario bootstrap resamples by district, state and year. Headline intervals use the **widest** of the three.
  4. The app labels the two heat numbers as two models (simple night-temperature model vs full scenario model) and reads all numbers and ranges from the database instead of hard-coding them. "Failed harvest" wording replaced by "bad year (more than 10% below normal)".
- **Also fixed:** `feb_tmax_mean` was not masked for incomplete seasons (missing `feb_` prefix); `climate_harvest.py` now labels wheat seasons by sowing year like the crop tables. Synthetic-data unit tests added (`tests/test_core.py`), including one showing district-only effects overstate a heat effect when bad years are also hot years.
- **Alternatives:** keep one model for both jobs (rejected: forecasting cannot use year effects, attribution should); Driscoll-Kraay errors (reasonable, but the three-way comparison is easier to explain).
- **Own review of the D23 patch (2026-11-26), changes made before using it:**
  - Renumbered from "D20" (already used for the long-run climate work) to D23.
  - **Bug fixed:** `scenario_uncertainty.py` built the scenario features on the 2018+ rows only, but they need each district's training-year means, so every row became NaN and the bootstrap crashed (0 rows). Now built on the full table, then 2018+ kept, with an assert.
  - **Added state + year two-way clustering** (the textbook choice for spatial plus common-year correlation) to the robustness regression, next to district, state and district + year. A NaN covariance (statsmodels can return one for two-way clusters) can no longer be picked as "widest".
  - **Ridge as headline is checked, not assumed:** Ridge shrinks coefficients toward zero, which can understate a causal effect, and the bootstrap keeps alpha fixed. The comparison table decides: wheat agrees across all four specifications at +2 C (Ridge -10.4%, two-way OLS -10.4%, small 3-variable OLS -9.2%, old -11.4%), so the wheat headline is robust. Rice does not (Ridge -8.6%, two-way OLS -7.3%, small OLS -4.1%, old -7.5%): the rice scenario is reported as uncertain, with this range.
  - **Effect on the night-heat result:** wheat -5.3% per +1 C night temperature; widest 95% CI now [-9.3, -1.3] (state clustering; was [-6.6, -4.0] with district clustering), p = 0.012; significant in all 8 variants (-4.5% to -5.8%). Monsoon-rice night effect -1.3% [-5.1, +2.4], not significant: for rice the rainfall effect carries the story.
  - Harvest link (D22) recomputed with corrected wheat season labels and the widest CI: wheat-season nights +0.61 C, implied wheat yield -3.2% [-5.7, -0.8].
  - The February masking bug affected 1 wheat row, which was outside the analysis sample: no result changed because of it.

## D24. Practical additions to the atlas, plainer wording, data release (2026-11-26)
(The request called this "D21"; D21 already exists, so it is D24.)
- **Why:** the atlas served researchers well but did little for the people it is about. Farmers and extension officers need to know what they can do; researchers and examiners need the numbers in a usable form. The wording also read like generated text (rhetorical title, emoji on every line), which undermines trust with a professional reader.
- **Added:**
  1. "What can be done?" on My district: 2-4 general actions chosen from the district's own data by `app/helpers.advice_keys` (wheat: medium/high risk plus March heat in the top third of wheat districts -> timely sowing and heat-tolerant varieties; under 50% irrigated -> PMKSY irrigation support; rice with 2+ bad years that came with a weak monsoon -> drought-tolerant varieties; high risk or drought losses -> PMFBY insurance; always -> IMD agromet advisories and the Krishi Vigyan Kendra). All text in one `ADVICE` dictionary at the top of `app/app.py`, each item linked to an official page. No variety names, doses or dates. Disclaimer: "General guidance only. Ask your local Krishi Vigyan Kendra for advice for your farm."
  2. Downloads under For experts -> About, data and caveats: district summary CSV (both crops) and district-year panel CSV (selected crop), built from atlas.sqlite in the app (`district_summary`, `district_panel`), with column meanings, units, sources, the CC BY-NC-SA 4.0 boundary licence and a citation.
  3. One-page PDF district report (fpdf2 + matplotlib, built-in Helvetica so it runs on Streamlit Community Cloud; English only because the built-in fonts cannot draw Devanagari or Gurmukhi).
  4. Language toggle English / Hindi / Punjabi for Start here, the sidebar and the advice box (`app/i18n.py`, `TEXT` dictionary). Numbers are filled in by code, never typed into translations. For experts stays in English.
  5. Plainer interface wording: no rhetorical title, no emoji in headings or cards, specific labels ("bad year (more than 10% below normal)", "modelled change at +2 °C"), "failed" never used.
  6. All raw, intermediate and processed data published as GitHub release `data-v1` (10 zip archives, about 0.9 GB, with SHA-256 checksums), because several files exceed GitHub's 100 MB file limit and 3.2 GB of IMD grids would bloat every clone.
- **Limits:** the advice is general, not agronomic advice for a farm; three source URLs (ICAR-IIWBR, ICAR-NRRI, KVK portal) could not be opened from the build machine and need a manual check; every Hindi and Punjabi string needs review by a native speaker before wider use; IMD raw grids are redistributed with citation of Pai et al. (2014) and Srivastava et al. (2009).
- **Not changed:** models, statistics and numbers (src/models.py, run_phase8.py, scenario_uncertainty.py untouched).

## D25. Production, value and food equivalent, checked against official totals (2026-11-26)
- **Question:** how much wheat and rice is produced (tonnes), what is it worth to farmers, and how many people could it feed?
- **Problem found:** summing the DES portal's district production gives totals above the official figures from 2016 onwards (2022-23: wheat 128.5 against 110.55 Mt, rice 155.0 against 135.76 Mt). The raw download already has the excess; it is not our processing. Biggest gaps (2022-23, ours/official): Madhya Pradesh wheat 1.54 (area too high, the D15 break), Odisha rice 1.45 with area matching (district figures most likely paddy: 1/0.67 = 1.49), Madhya Pradesh rice 1.87.
- **Chosen:**
  1. Official reference tables read by code from the PDFs with self-checks (`src/official_stats.py`): Agricultural Statistics at a Glance 2024 (production 2.4/2.5, MSP 2.71, cost A2+FL 2.73(a), availability per person 3.6, population 1.1(a)); HCES 2023-24 Tables 3.7, 3.8R, 3.8U; CAG Report 31 of 2015 for the 67% out-turn ratio. Files in data/raw/official/.
  2. A state passes if our district sum is within ±5% of the official 2022-23 total; non-major states are checked together against the official remainder. District tonnes, value, margin and people-equivalent are shown only for districts in passing states with a known, single state; otherwise the app shows the reason and both totals. India figures use official totals only.
  3. Value = quintals × MSP of the crop year; rice converted to paddy (÷ 0.67) because MSP is for paddy. Margin = (MSP − state cost A2+FL) × quintals; no state cost → no margin (never the all-India cost as a stand-in).
  4. People-equivalent = production ÷ per-capita net availability (rice 69.6, wheat 68.8 kg, 2022-23). Chosen over HCES consumption (57.5 and 45.9 kg) because it gives the smaller, more conservative number. Labelled "people-equivalent", not "people fed", because gross production also covers exports, stocks, seed, feed and losses.
- **Result 2022-23:** 252 of 487 wheat and 121 of 564 rice districts pass. India at MSP: wheat ₹2,34,919 crore, rice ₹4,13,359 crore; margin over A2+FL ₹1,17,183 and ₹1,37,786 crore; people-equivalents 161 and 195 crore. Full derivation: docs/EVIDENCE_production_value.md.
- **Alternatives:** scale district figures to official state totals (rejected: hides which districts are wrong); use all-India cost where a state cost is missing (rejected: invents a local number); use HCES consumption (kept as a cross-check).
- **Open item (affects the climate analysis):** likely unit switches in rice yields that the D11 outlier rule (3× median) does not catch: Madhya Pradesh 2022-23 (+49% state yield in one year) and Bihar 2011-12 (+125%). A robustness run of the monsoon-rice models dropping these seasons has not been done yet.
