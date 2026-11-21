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

## C. District boundaries + LGD codes, needs your decision first

See the "Boundaries" entry in DECISIONS.md. Don't download anything until
you've picked an option.

If you choose **Survey of India** (recommended):
1. Go to https://onlinemaps.surveyofindia.gov.in and register (free).
   Account creation is yours to do; the team won't sign up for you.
2. Open **Digital Products** and find the **Administrative Boundary Database**
   (district level, whole country), priced at Rs 0.
3. Add it to the cart, check out at Rs 0, and download the shapefile ZIP.
4. Save the ZIP **unextracted** as `data/raw/boundaries/soi_districts.zip`.

LGD district codes:
1. Go to https://lgdirectory.gov.in → **Download Directory** → **All Districts of India**
   (solve the captcha yourself; the team doesn't do captchas).
2. Format CSV (or XLS). Save as `data/raw/boundaries/lgd_districts.csv`.
