# Deploying the Crop-Climate Risk Atlas (free, Streamlit Community Cloud)

**Live app:** https://crop-climate-risk-atlas.streamlit.app (repository https://github.com/Taab-cyber/heat-rain-harvest, deployed 2026-11-25).

The atlas is a pure-Python dashboard (pandas + Plotly + Streamlit) and replaces Tableau for the interactive part.
The static analysis figures come from seaborn/matplotlib in the notebooks (`reports/figures/`).
Ask the professor once whether a Python dashboard is acceptable in place of Tableau; the Tableau exports in
`reports/tableau/` still work if Tableau is required.

## What the deployed app needs (already in the repo)
| File | Why |
|---|---|
| `app/app.py` | the dashboard |
| `app/requirements.txt` | 4 pinned packages (streamlit, plotly, pandas, numpy); Streamlit Cloud reads this first |
| `app/atlas.sqlite` (7 MB) | all results, built by `python -m src.build_db` |
| `app/districts.geojson` (2.4 MB) | simplified Census 2011 district polygons |

Raw and processed data (`data/`) are not needed and stay out of git. Tested 2026-11-25 in a fresh virtual
environment with only `app/requirements.txt` installed: all four tabs load, no errors in the server log.

## Steps (about 10 minutes, done by you: it needs your own GitHub and Streamlit accounts)
1. Create an empty repository on https://github.com (for example `heat-rain-harvest`; public is simplest).
2. In WSL, from the project folder:
   ```bash
   git remote add origin https://github.com/<your-username>/heat-rain-harvest.git
   git push -u origin main
   ```
   (GitHub asks for a personal access token instead of a password, or use `gh auth login`.)
3. Open https://share.streamlit.io, sign in with GitHub, click **Create app** -> **Deploy a public app from GitHub**.
4. Repository `<your-username>/heat-rain-harvest`, branch `main`, main file path `app/app.py`.
   Under **Advanced settings** choose Python **3.12**. Click **Deploy**.
5. After 2-3 minutes you get a public link like `https://<name>.streamlit.app`. Put it in the report and the paper's
   "Data and code availability" section.

## Updating the live app
Rebuild the database (`python -m src.build_db`), commit `app/atlas.sqlite`, push. The app redeploys itself.

## Licences and credit (shown in the app's About tab)
DES and IMD data are Government of India open data. The district polygons (SHRUG Open Polygons, Development Data
Lab) are CC BY-NC-SA 4.0: non-commercial use with attribution, which a student project meets.
