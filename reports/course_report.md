# Heat, Rain & Harvest: How India's changing climate is hitting crop yields

**MCA109 Data Science Foundation, end-semester project, TIET Patiala**
**Team:** Mehtaab, Pravansh
**Theme:** Environment

---

## 1. Problem and questions
Rising temperatures and erratic monsoons threaten India's two staple crops. Using only official government data, we ask:
1. How strongly do heat and rainfall shocks move district wheat and rice yields (1997-2022)?
2. Does irrigation protect against these shocks?
3. Can weather known before harvest (up to end of March) forecast wheat yield better than a simple trend?
4. What happens to yields under +1 C and +2 C warming?
5. (Extension) How fast has India warmed since 1951, are winters shrinking, is the monsoon changing (1901-2025), and what has that already done to harvests?

## 2. Data (all official / original sources)
| Data | Source | Coverage | Size |
|---|---|---|---|
| Area, production, yield | DES, Ministry of Agriculture (data.desagri.gov.in) | 38 states/UTs, 1997-98 to 2022-23, all crops and seasons | 406,612 rows |
| Land use and irrigation | DES Land Use Statistics | 1998-99 to 2022-23 | 19,875 district-years |
| Rainfall | IMD Pune, 0.25 deg daily grid | 1901-2025 (models use 1997-2023) | 125 files |
| Max/min temperature | IMD Pune, 1.0 deg daily grid | 1951-2025 (models use 1997-2023) | 150 files |
| District boundaries | Census 2011 polygons, SHRUG Open Polygons v2.2 (Development Data Lab; also on AIKosh, GoI) | 640 districts | |
| District and tehsil codes | Local Government Directory (lgdirectory.gov.in) | 790 districts, 7,112 tehsils | |

**Sample-size requirement (>= 50,000):** met by the harmonised all-crop panel, **388,399 rows** (district x year x
crop x season, 626 fixed districts). The wheat and rice analysis tables are smaller (wheat 12,323, rice 14,494
district-years), and we state this openly (DECISIONS D3).

## 3. Pipeline (phases)
| Phase | What | Where |
|---|---|---|
| 1 Setup | WSL, conda env `hrh`, folders, git | `environment.yml` |
| 2 Acquisition | scripted IMD temperature; browser exports of DES APY/LUS, IMD rain, LGD; size and content checks | `src/download_imd.py`, `src/collect_*.py` |
| 3 Cleaning and integration | parse wide HTML tables, map 747 district names to 2011 districts (validated 99.7%), grid to district weather, master table | `src/parse_*.py`, `src/district_map.py`, `src/post2011_parents.py`, `src/climate_to_district.py`, `src/build_*.py` |
| 4 Features | season windows, GDD, extreme heat, March hot days, rain, dry spells; train-only detrending | `src/features.py`, `tests/test_no_leakage.py` |
| 5 EDA | distributions, trends, binned plots, maps | `notebooks/05_eda.ipynb` |
| 6 Statistics | distributions, z-scores, t vs z, CI, chi-square, ANOVA/F, Type I/II and power, multiple testing, bootstrap, FE regression | `notebooks/06_statistics.ipynb` |
| 7 Patterns | PCA, distances, MDS, t-SNE, k-means and Ward risk zones, label propagation, feature selection | `src/profiles.py`, `notebooks/07_patterns.ipynb` |
| 8 Prediction | trend baseline, FE, Ridge, RF, GBM, loss classifier, pre-harvest forecast, scenarios | `src/models.py`, `src/run_phase8.py`, `notebooks/08_models.ipynb` |
| 9 Application | SQLite + Streamlit Risk Atlas, Tableau exports, report, paper | `app/`, `src/build_db.py`, `reports/` |
| 10 Long-run climate (extension) | warming 1951-2025 by year/season/month/week/day, winters, hot days, monsoon 1901-2025, harvest link, non-weather factors | `src/climate_trends.py`, `src/monsoon_trends.py`, `src/climate_harvest.py`, `src/harvest_factors.py`, `notebooks/09_climate_trends.ipynb` |
| 10b Loss-season patterns | loss seasons by region and season, weather in loss vs normal seasons | `src/loss_patterns.py`, `notebooks/10_loss_patterns.ipynb` |

Every choice, with its alternatives, is in `DECISIONS.md` (D1-D23).

## 4. Key results
**Heat hurts wheat, robustly.** With district and year fixed effects, +1 C in wheat-season night temperature goes with
**-5.3% yield (95% CI -9.3 to -1.3; p = 0.012)**, using the widest of four error-clustering choices (district, state,
district + year, state + year; D23); across eight robustness variants
-4.5% to -5.8%. Ten extra days above 35 C in March: -1.8% (p = 0.017). The 2021-22 heatwave cut Punjab and Haryana
wheat by **9.5%** below trend [-11.6, -7.4].

**Irrigation protects rice from drought, clearly.** A monsoon 20% below normal costs about 3.1% of rice yield at 20%
irrigation but about 0.3% at 95% (interaction p < 0.0001).

**Irrigation and wheat heat: not established.** The estimate points the protective way but p = 0.10 (0.045 only
without Madhya Pradesh 2018+). The highest-risk wheat zone (Madhya Pradesh and Bihar) is 83% irrigated.

**Risk zones.** Five zones (silhouette-optimal; stable vs Ward clustering, ARI 0.61), geographically coherent although
no coordinates were used: irrigated north-west 15% loss years, MP-Bihar 34%.

**Prediction is weak, and we say so.** On test years 2018-2022 the best wheat model (Ridge) beats the trend-only
baseline by only 1.8%; no rice model beats it. One round of agronomy-driven feature engineering (selected by training-year
cross-validation) did not change this. The pre-harvest forecast missed the 2022 Punjab-Haryana losses (forecast +3.7%,
actual -12.3% vs trend). Explanation: real but small weather effects (about +/-2.5% for a typical +/-0.5 C year) against yield
noise with sd about 19%.

For monsoon rice the night effect is not significant (-1.3%, CI -5.1 to +2.4): rice responds to rain.

**Warming scenarios (no adaptation; two-way fixed-effects Ridge, D23).** Wheat **-5.2%** [-8.4, -1.5] at +1 C,
**-10.4%** [-16.8, -3.2] at +2 C; monsoon rice -4.5% [-8.1, -0.8] and -8.6% [-16.1, -0.9] (95% bootstrap, widest of
district, state and year resampling). The wheat number holds across four model specifications (-9.2% to -11.4% at
+2 C); the rice number does not (-4.1% to -8.6%), and it falls to -6.0% when seasons with a suspected switch from rice to paddy reporting are removed (D26), so it is uncertain: roughly -6% to -9%. Less-irrigated districts lose more (wheat at
+2 C: -17.7% below 50% irrigation vs -9.6% above 90%), but they are mostly hill districts (irrigation and location
are confounded).

**Long-run climate (extension, 1901-2025).** Trends are Sen slopes per decade with the Mann-Kendall test, against a
1951-1980 normal, on district-area-weighted all-India series.

| Measure | Change | p |
|---|---|---|
| Mean temperature, 1951-2025 | +0.075 C per decade (about +0.56 C in total) | < 0.001 |
| Post-monsoon (Oct-Nov) mean temperature | +0.136 C per decade, the fastest season | < 0.001 |
| Cool days per winter (Oct-Mar) | 89 (1952-81) to 79 (1996-2025), -2.1 per decade | < 0.001 |
| Cold nights per winter (Dec-Feb) | 8.9 to 6.4 | 0.14 |
| March days with tmax >= 35 C | +0.4 per decade | 0.046 |
| June-September rain, 1901-2025 | no trend (+0.9 mm per decade) | 0.65 |
| Heavy-rain days (>= 64.5 mm) | rising, +0.013 per decade | 0.005 |
| Very heavy and extreme rain days | rising | < 0.001 |
| Longest June-September dry spell | -0.17 days per decade | 0.013 |

Hottest years: 2009, 2010, 2016, 2024, 2017. We do not extrapolate when winters might vanish; future statements belong
to official projections (MoES 2020, IPCC AR6). Wheat-season nights warmed by 0.61 C between the 1951-80 and 1996-2025
normals; with the -5.3% per C effect this implies wheat yields **about 3.2% lower** (95% CI 0.8-5.7%) than in a 1951-80
climate, all else equal (monsoon rice -0.3%). Of the non-weather factors available without portal accounts, last
season's yield anomaly raised wheat CV skill from 2.4% to 7.3% (test 2018-22: -6.3% to +18.5%, partly a trend-drift
correction); the tubewell share of irrigation added nothing. Groundwater, NDVI, fertiliser and soil data need portal
accounts (docs/MANUAL_DOWNLOADS.md, section D).

**Loss seasons: where and with what weather (descriptive).** A loss season is a district yield more than 10% below
its trend; weather is compared with the same district's normal (z-score). Worst wheat seasons: 2014-15 (57% of area in
loss; March cooler and much wetter than normal, i.e. harvest-time rain and hail), 2015-16 (warm nights, dry, after two
weak monsoons), 2005-06 (very hot February); the north-west's worst was 2021-22 (March heatwave). Warm nights are the most
consistent wheat signal (7 of 8 regions; Gangetic plain 32% of warm-night seasons were losses vs 6% of cool-night ones),
then a weak preceding monsoon (6 of 8). In the irrigated north-west, losses come with *wet* seasons. Monsoon-rice losses
follow rain: worst in the drought years 2002, 2015 and 2009, and when June-September rain is far below normal the loss
rate rises to 66% in Central India (33% normally). The irrigated north-west hardly reacts (12% loss rate vs 21-36%).
Some losses have no weather signature (rice 2008 was wet). Figures: `reports/figures/10_*.png`; notebook 10.

## 5. Application
**Crop-Climate Risk Atlas** (`streamlit run app/app.py`): pick crop and district; see the yield trend, anomalies and loss
years, the weather trend, heat sensitivity, risk score and zone, a +X C warming slider (0.5-3 C), and the 2018-22
forecasts against actual yields. Live at https://crop-climate-risk-atlas.streamlit.app. A "Climate 1901-2025" tab shows the long-run warming, winters, monsoon and harvest link, and a "Loss years" tab shows when and where harvests failed. Data are served from `app/atlas.sqlite`. A Tableau Public dashboard can be built from
`reports/tableau/` following `reports/tableau/TABLEAU.md`.

## 6. Limitations
- Temperature grid is 1 deg (about 110 km): 64 districts share a single cell's temperature.
- Boundary polygons compiled from several sources (up to about 1 km error); 27 new districts with split parents are assigned
  to the majority parent; Tripura handled as one unit.
- Madhya Pradesh wheat area/production series break from 2018; implausible yields flagged by rule; irrigation and crop area
  come from separate surveys; irrigation data start 1998-99.
- Fixed season windows ignore local sowing dates; rice "monsoon" irrigation share uses all-season irrigated rice.
- Fixed effects do not remove time-varying confounders; irrigation is not randomly assigned.
- Five test years; a few test-set comparisons were made before features were chosen by training-year CV (disclosed in D19).
- Scenarios assume uniform warming, unchanged rain, no adaptation; +2 C is an extrapolation.
- Long-run trend p-values ignore autocorrelation (slightly optimistic); the implied effect of past warming assumes today's sensitivity held in the past.

## 7. Reproducibility
Seed 42 throughout; pinned environment (`environment.yml`); raw data never edited; every derived file rebuilt by scripts in
the order given in `README.md`; leakage test in `tests/`.

## 8. Team contributions
*(Fill in: who did what. Both members should be able to explain every phase; see LEARNING.md and VIVA.md.)*
