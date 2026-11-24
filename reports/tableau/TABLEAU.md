# Building the Tableau Public dashboard

Files in this folder are produced by `python -m src.export_tableau` (after `python -m src.build_db`).

| File | One row per | Key fields |
|---|---|---|
| `districts.geojson` | Census 2011 district (polygon) | `unit_id`, `d_name` |
| `district_summary.csv` | district x crop | `mean_yield`, `risk_score`, `heat_effect_per_c`, `change_pct_1C`, `change_pct_2C`, `zone`, `mean_irr_share` |
| `district_year.csv` | district x crop x year | `season`, `yield_t_ha`, `trend_full`, `yield_anomaly_pct`, `loss_year`, `irr_share`, weather columns |
| `scenario_grid.csv` | district x crop x warming step | `delta_c` (0.5 to 3.0), `change_pct` |

Tableau Public (free desktop app) can read GeoJSON and CSV directly.

## 1. Connect the data
1. Open Tableau Public. Under **Connect**, choose **Spatial file** and open `districts.geojson`.
2. In the Data Source pane, click **Add** next to Connections, choose **Text file**, and open `district_summary.csv`.
3. Drag `district_summary.csv` onto the canvas next to `districts.geojson`. In the relationship
   dialog, set **unit_id (districts.geojson) = unit_id (district_summary.csv)**.
4. Add `district_year.csv` and `scenario_grid.csv` the same way, each related on `unit_id`
   (and for `district_year`, also add `crop = crop` to its relationship with the summary).
5. Check data types: `unit_id` = Number (whole); `delta_c` = Number (decimal); `season` = String.

## 2. Sheet "Risk map"
1. New sheet. Double-click **Geometry** (from districts.geojson): a map of India appears.
2. Drag `crop` to **Filters**, choose "Wheat", then right-click the filter and **Show Filter** (single value list).
3. Drag `change_pct_2C` to **Colour**. Edit colours: **Red-Blue Diverging**, centre 0, reversed so losses are red.
4. Drag `d_name`, `risk_score`, `heat_effect_per_c`, `zone` to **Tooltip**.
5. Create a parameter **Map metric** (String list: "Change at +2 C", "Risk score", "Heat sensitivity") and a
   calculated field `Map value` with a CASE statement returning the matching column. Put `Map value` on Colour
   instead, and show the parameter control.

## 3. Sheet "District trend"
1. Columns: `year` (continuous); Rows: `yield_t_ha` and `trend_full` (dual axis, synchronise axes).
2. Marks for `yield_t_ha` = Bar; for `trend_full` = Line (dashed).
3. Filter on `d_name` (show as a single-value dropdown) and `crop`.

## 4. Sheet "Anomalies"
Columns `season`, Rows `yield_anomaly_pct`, Colour `loss_year` (red = 1). Same filters.

## 5. Sheet "Warming curve"
Columns `delta_c`, Rows `change_pct` (line with markers), filtered to the selected district and crop.
Add a reference line at 0.

## 6. Dashboard
1. New Dashboard (size: Automatic). Put **Risk map** on the left, the three district sheets stacked on the right.
2. On Risk map, **Dashboard > Actions > Add Action > Filter**: source Risk map, targets the three district
   sheets, run on **Select**, fields `unit_id` and `crop`. Clicking a district then updates the charts.
3. Add a text box with the caveats (copy from the app's "About & caveats" tab): fixed 2011 districts; scenarios =
   uniform warming, rain unchanged, no adaptation; weather explains only 1-2% of out-of-sample yield variation.
4. Add the data sources: DES APY and Land Use Statistics, IMD gridded data, SHRUG Open Polygons (Census 2011).

## 7. Publish
**File > Save to Tableau Public As...**, sign in with your own Tableau Public account, and give the workbook a name.
Tableau Public workbooks are **public**, so don't include anything you wouldn't publish.
