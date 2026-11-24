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

## 2. Data (all official / original sources)
| Data | Source | Coverage | Size |
|---|---|---|---|
| Area, production, yield | DES, Ministry of Agriculture (data.desagri.gov.in) | 38 states/UTs, 1997-98 to 2022-23, all crops and seasons | 406,612 rows |
| Land use and irrigation | DES Land Use Statistics | 1998-99 to 2022-23 | 19,875 district-years |
| Rainfall | IMD Pune, 0.25 deg daily grid | 1997-2023 | 27 files |
| Max/min temperature | IMD Pune, 1.0 deg daily grid | 1997-2023 | 54 files |
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

Every choice, with its alternatives, is in `DECISIONS.md` (D1-D19).

## 4. Key results
**Heat hurts wheat, robustly.** With district and year fixed effects and district-clustered errors, +1 C in
wheat-season night temperature goes with **-5.3% yield (95% CI -6.6 to -4.0)**; across eight robustness variants
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

**Warming scenarios (no adaptation).** Wheat **-5.7%** [-6.6, -4.8] at +1 C, **-11.3%** [-13.2, -9.4] at +2 C;
monsoon rice -4.4% [-5.7, -2.6] and -7.5% [-10.4, -3.7]. Less-irrigated districts lose more, but they are mostly hill
districts (irrigation and location are confounded).

## 5. Application
**Crop-Climate Risk Atlas** (`streamlit run app/app.py`): pick crop and district; see the yield trend, anomalies and loss
years, the weather trend, heat sensitivity, risk score and zone, a +X C warming slider (0.5-3 C), and the 2018-22
forecasts against actual yields. Data are served from `app/atlas.sqlite`. A Tableau Public dashboard can be built from
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

## 7. Reproducibility
Seed 42 throughout; pinned environment (`environment.yml`); raw data never edited; every derived file rebuilt by scripts in
the order given in `README.md`; leakage test in `tests/`.

## 8. Team contributions
*(Fill in: who did what. Both members should be able to explain every phase; see LEARNING.md and VIVA.md.)*
