# Manual downloads (DES portals and boundaries)

These sources can't be scripted: the DES report forms issue a per-session
token, so a script would have to get around it. Download them by hand,
save them **exactly** where listed, and never edit the files afterwards
(the cleaning scripts read them as they are).

Checked on 2026-11-21. If a screen looks different from this guide,
note what you see in DECISIONS.md instead of guessing.

---

## A. DES Area-Production-Yield (APY), required

Portal (no login): https://data.desagri.gov.in/website/crops-apy-report-web
Years offered: 1997-98 to 2022-23.

We need **all crops** (not only wheat and rice). The extra crops are what
get the master table past the 50,000-row requirement honestly, and they
also let us check whether the climate effects are specific to wheat and rice.

One file per state keeps each export small enough for the portal.

For each state in the **State** list (36 entries, excluding "All States"):

1. Select the radio button **"Horizontal Crop and Vertical Year"**.
2. **State**: pick one state (e.g. Punjab).
3. **District**: pick **All Districts**.
4. **Crops**: pick **All Crops**.
5. **Season**: select **all six** seasons (Rabi, Kharif, Autumn, Winter, Summer, Whole Year).
   If the box allows "Select season" only, leave it blank and note that here.
6. **From Year**: `1997 - 1998`. **To Year**: `2022 - 2023`.
7. **Report Format**: **Excel**.
8. Click **View Report** and wait (large states can take a minute or more).
9. Save the file as
   `~/projects/heat-rain-harvest/data/raw/apy/apy_<state>.xlsx`
   (or `.xls`/`.csv`, whatever the portal gives you; keep the extension).
   Use lowercase with underscores, e.g. `apy_uttar_pradesh.xlsx`.

From Windows, the folder is `\\wsl$\Ubuntu\home\hpmehtaabkohli\projects\heat-rain-harvest\data\raw\apy\`.

**If a state times out:** split it into two year ranges (1997-98 to 2009-10
and 2010-11 to 2022-23) and save as `apy_<state>_part1.xlsx`, `_part2.xlsx`.

**Minimum if you are short on time:** first do the wheat and rice states
(Punjab, Haryana, Uttar Pradesh, Bihar, Madhya Pradesh, Rajasthan, Gujarat,
Maharashtra, West Bengal, Odisha, Andhra Pradesh, Telangana, Tamil Nadu,
Karnataka, Chhattisgarh, Assam, Jharkhand, Uttarakhand, Himachal Pradesh),
then the rest.

When you are done, open the files and record the real columns and row counts
before writing any cleaning code.

---

## B. DES Land Use Statistics: crop-wise irrigated area, required for the irrigation hypothesis

Portal (no login): https://data.desagri.gov.in/weblus/lus-grand-query-report
Years offered start at 1998-99.

1. **From Year**: `1998-1999`. **To Year**: `2022-2023`.
2. **State**: one state (the list may fill only after you choose the years).
3. **District**: all districts.
4. **Classification of Area**: open the dropdown and tick the
   **crop-wise irrigated area** items for **Wheat** and **Rice** (also
   "Total"/"Gross irrigated area" and "Net irrigated area" if they are offered).
   **Write down the exact names of the options you see.** They are needed to label
   the columns correctly.
5. **Unit**: Hectare. **Report Type**: Vertical Year. **Report Format**: Excel.
6. Click **Get Data** and save as `data/raw/lus/lus_<state>.xlsx`.

Same state list and same fallback (split the years) as APY.

---

## C. District boundaries + LGD codes (decision D6)

### C1. PC11 district polygons (analysis base), AIKosh
1. Open https://aikosh.indiaai.gov.in/home/datasets/details/2011_population_census_district_polygon_geometries.html
2. Click **Download (29.71 MB)**. If AIKosh asks you to sign in or register,
   do that yourself and click Download again.
3. Save the file **as delivered** (don't extract it) into `data/raw/boundaries/`,
   e.g. `data/raw/boundaries/pc11_district_polygons.zip`.
4. Also click **Download Metadata** and save it next to the ZIP. We cite it in the paper.

### C2. LGD districts (for post-2011 → 2011 mapping)
Preferred (same portal): AIKosh dataset **"Local Government Directory (LGD) - Districts"**
(linked under "Related Datasets" on the page above). Save to `data/raw/boundaries/lgd_districts.<ext>`.

Fallback: https://lgdirectory.gov.in → **Download Directory** → **All Districts of India**
(you solve the captcha). Save as `data/raw/boundaries/lgd_districts.csv`.

Record which one you used. The mapping only works if the file
has a Census 2011 district code column, so check that on the real file.

### C3. Survey of India (cross-check only, optional if short on time)
1. Go to https://onlinemaps.surveyofindia.gov.in/Digital_Product_Show.aspx and register (free).
   Creating the account is yours to do.
2. Find the **Administrative Boundary Database** (district level, whole country), priced at Rs 0.
3. Check out at Rs 0, download, and save the ZIP unextracted as `data/raw/boundaries/soi_districts.zip`.

## D. Phase 10 extensions that need a personal sign-in (not done automatically)
These portals need an account, a captcha or a personal API key, so the downloads are done by the team members
themselves. Put each file in the folder shown; the analysis code is then a short addition (DECISIONS D22).

### D1. Groundwater levels (CGWB well observations), India-WRIS
1. Open https://indiawris.gov.in/wris/ -> Ground Water -> Ground Water Level. Sign in (free account; captcha).
2. Choose: all states, district-wise, seasons Pre-monsoon (May) and Post-monsoon (November), years 1996-2024.
3. Download CSV/Excel per state into `data/raw/groundwater/`.
- Plan: depth to water level per district, pre and post monsoon; recharge = pre minus post; trend per district
  (Sen slope); link to tubewell share and to rice/wheat yields. Without login, CGWB's public pages only have single
  years (2018-2019 district tables, 2021 KML, 2021-22 PDF reports): too few years for trends.

### D2. Vegetation greenness (NDVI)
- Preferred (Indian, government): ISRO NRSC Bhuvan / VEDAS (SAC) NDVI products: need a Bhuvan/VEDAS account.
- Alternative: NASA MODIS MOD13A3 monthly NDVI 1 km (2000-present) via NASA Earthdata (free login). This is a
  government source but not Indian: the team should confirm with the professor before we use it.
- Put files in `data/raw/ndvi/`. Plan: district mean NDVI in Feb-Mar (wheat) and Aug-Sep (rice) as an in-season signal.

### D3. Fertiliser, machinery, tubewells: Agricultural Input Survey (DES / Agriculture Census)
- https://inputsurvey.dacnet.nic.in (district tables by survey round 2001-02, 2006-07, 2011-12, 2016-17).
  Download district tables on fertiliser use per ha and tubewell/pumpset counts into `data/raw/input_survey/`.
- Only 4 rounds -> usable as slow-changing district traits, not year-to-year drivers.

### D4. Soil health
- https://soilhealth.dac.gov.in : district summaries of N, P, K, organic carbon (cycles 2015-17, 2017-19). Static traits.

### D5. Crop prices (MSP, mandi prices)
- MSP: CACP price-policy reports (https://cacp.da.gov.in), national per crop and year: identical for all districts, so it
  cannot explain district differences (it is absorbed by year effects).
- Mandi prices: Agmarknet (https://agmarknet.gov.in) or data.gov.in with the team's own API key.
