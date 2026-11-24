"""Builds notebooks/09_climate_trends.ipynb. Reads results saved by src.climate_trends, src.monsoon_trends,
src.climate_harvest and src.harvest_factors (no recomputation of the heavy steps)."""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[2]
nb = nbf.v4.new_notebook()
C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s))
code = lambda s: C.append(nbf.v4.new_code_cell(s))

md("""# 09 - India's long-run climate: warming, winters, monsoon, and what it means for harvests
**Heat, Rain & Harvest.** Phase 10 (extension). Data: IMD gridded daily temperature 1951-2025 (1 deg) and rainfall
1901-2025 (0.25 deg), averaged to the 640 Census-2011 districts with area weights, then to India with district-area
weights. Trends are **Sen's slope per decade** with the **Mann-Kendall** test (robust to outliers, no normality
assumption). Baseline normal: 1951-1980. Methods: DECISIONS D20-D22.

Produced by:
```
python -m src.climate_to_district --vars tmax tmin --start 1951 --end 2025 --tag longrun
python -m src.climate_to_district --vars rain --start 1901 --end 2025 --tag longrun
python -m src.climate_trends && python -m src.monsoon_trends
python -m src.climate_harvest && python -m src.harvest_factors
```""")

code("""import sys
from pathlib import Path
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT))
import numpy as np, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
from src.config import PROCESSED, FIGURES
from src.boundaries import load_pc11_districts
sns.set_theme(style="whitegrid"); plt.rcParams["figure.dpi"] = 110
save = lambda fig, n: fig.savefig(FIGURES / f"{n}.png", bbox_inches="tight", dpi=150)
C = PROCESSED / "climate"; geo = load_pc11_districts()
ann = pd.read_csv(C / "national_annual.csv"); tr = pd.read_csv(C / "national_trends.csv")
sig = lambda p: "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else ""
print(ann.year.min(), "-", ann.year.max(), "|", len(ann), "years")""")

md("""## 1. How fast is India warming? (year, season, month)""")
code("""fig, ax = plt.subplots(figsize=(11, 4))
for v, c in (("tmax", "tab:red"), ("tmin", "tab:blue"), ("tmean", "k")):
    s = ann[f"{v}_anom_vs_1951_80"]
    ax.plot(ann.year, s, c=c, lw=.8, alpha=.5); ax.plot(ann.year, s.rolling(10, center=True).mean(), c=c, lw=2, label=f"{v} (10-yr mean)")
ax.axhline(0, c="grey", lw=.8); ax.set(ylabel="deg C vs 1951-1980", title="All-India temperature anomaly, 1951-2025 (IMD gridded, district-area weighted)")
ax.legend(); save(fig, "09_india_temperature_anomaly"); plt.show()
a = tr[tr.period == "annual"].set_index("variable")
for v in ("tmax", "tmin", "tmean"):
    r = a.loc[v]; print(f"{v}: {r.sen_per_decade:+.3f} C per decade (Mann-Kendall p={r.mk_p:.2g}) -> {r.sen_per_decade*7.4:+.2f} C over 1951-2025")""")
md("""**Per day / week / month / year.** A *rate* only makes sense per unit of time over many years, so "how much warmer each
day" is answered as: how much warmer is the *same calendar day* now (1996-2025 normal) than it used to be (1951-1980
normal). The per-decade slope divided by 10 is the per-year rate.""")
code("""per = tr[tr.variable == "tmean"].set_index("period")
months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
fig, ax = plt.subplots(1, 2, figsize=(13, 3.8))
m = per.loc[months]
ax[0].bar(months, m.sen_per_decade, color=["tab:red" if p < .05 else "lightgrey" for p in m.mk_p])
ax[0].set(title="Warming by month (mean temperature, C per decade)\\nred = significant at 5% (Mann-Kendall)", ylabel="C / decade")
wk = pd.read_csv(C / "national_week_of_year.csv")
ax[1].bar(wk.week, wk.warming_c, color=["tab:red" if p < .05 else "lightgrey" for p in wk.mk_p], width=.9)
ax[1].set(title="Each week of the year: 1996-2025 normal minus 1951-1980 normal", xlabel="week of year", ylabel="C")
save(fig, "09_warming_by_month_week"); plt.show()
tab = tr.pivot_table(index="period", columns="variable", values="sen_per_decade").loc[["annual"] + months + ["winter (DJF)", "pre-monsoon (MAM)", "monsoon (JJAS)", "post-monsoon (ON)"]]
tab["tmean per year"] = tab.tmean / 10
tab["tmean signif."] = [sig(p) for p in per.loc[tab.index].mk_p]
tab.round(3)""")
code("""doy = pd.read_csv(C / "national_day_of_year.csv")
print(f"Average calendar day: {doy.warming_c.mean():+.2f} C warmer than in 1951-80; warmest-shift day-of-year range "
      f"{doy.warming_c.min():+.2f} to {doy.warming_c.max():+.2f} C")
print("Record hot years (all-India mean):"); print(pd.read_csv(C / "record_hot_years.csv").round(2).to_string(index=False))
rm = pd.read_csv(C / "record_hot_month_years.csv"); print("\\nHottest year for each month:", dict(zip(rm.month, rm.year)))""")
md("""**What this says.** India's mean temperature is rising by roughly 0.07-0.08 C per decade since 1951 (about
0.5-0.6 C so far), with the fastest and most certain warming after the monsoon (Oct-Nov) and in late summer. May and
June show no clear trend - pre-monsoon heat is very variable year to year. This is a district-average of gridded data,
so it is smaller than single-station trends in cities (which also include urban heat).""")

md("""### Where is it warming fastest?""")
code("""dt = pd.read_parquet(C / "district_trends.parquet")
g = geo.merge(dt[dt.period == "annual"], on="district_id")
fig, ax = plt.subplots(1, 2, figsize=(13, 6.5))
for a, v, t in ((ax[0], "tmax_per_decade", "Day-time (tmax)"), (ax[1], "tmin_per_decade", "Night-time (tmin)")):
    g.plot(column=v, cmap="RdBu_r", vmin=-.25, vmax=.25, legend=True, ax=a, legend_kwds={"shrink": .6, "label": "C / decade"})
    a.set_title(f"{t} warming 1951-2025"); a.axis("off")
save(fig, "09_map_district_warming"); plt.show()
print("share of districts with significant (p<0.05) mean warming:", round((dt[dt.period == 'annual'].tmean_mk_p < .05).mean() * 100, 1), "%")""")

md("""## 2. Are winters getting shorter and milder? Will they disappear?
**Cool day** (Oct-Mar): a day whose 7-day mean temperature is colder than the district's own coolest quarter of the year
in 1951-1980 (25th percentile of the 7-day mean). **Cold night**: tmin below the district's 1951-1980 Dec-Feb 10th percentile. Counts are averaged over
districts. Winter season labelled by the year it ends.""")
code("""w = pd.read_csv(C / "national_winters.csv")
fig, ax = plt.subplots(1, 3, figsize=(15, 3.6))
for a, v, t in ((ax[0], "cool_days", "Cool days per winter"), (ax[1], "cold_nights", "Cold nights per winter")):
    a.plot(w.season, w[v], c="tab:blue", lw=.8); a.plot(w.season, w[v].rolling(10, center=True).mean(), c="navy", lw=2); a.set_title(t)
ax[2].plot(w.season, w.first_cool_day, label="first cool day (days after 1 Oct)")
ax[2].plot(w.season, w.last_cool_day, label="last cool day")
ax[2].legend(fontsize=8); ax[2].set_title("Start and end of the cool spell")
save(fig, "09_winters"); plt.show()
from src.climate_trends import trend
for v in ("cool_days", "cold_nights", "first_cool_day", "last_cool_day"):
    r = trend(w.season, w[v]); print(f"{v}: {r['sen_per_decade']:+.2f} per decade (p={r['mk_p']:.2g})")
old, new = w[w.season.between(1952, 1981)].cool_days.mean(), w[w.season.between(1996, 2025)].cool_days.mean()
print(f"cool days: {old:.1f} (1952-81) -> {new:.1f} (1996-2025), {100*(new-old)/old:+.0f}%")""")
md("""**Will winters vanish?** Not on any timescale these data can support. At the observed rate (about 2 cool days lost
per decade out of ~80) a straight line would take centuries to reach zero - and a straight line is the wrong tool:
warming is accelerating and depends on future emissions, which no historical trend knows. The honest statements are:
(1) Indian winters already have about 10 fewer cool days than in 1951-80 and fewer cold nights; (2) the post-monsoon
and Feb-Mar shoulders are warming fastest, so winter *edges* are being eaten first - exactly the months that matter for
wheat grain-fill; (3) for the future, use the official projections (IPCC AR6 WG1 Atlas / MoES 2020 *Assessment of
Climate Change over the Indian Region*), which project further large increases in warm days and nights.""")

md("""## 3. Hot days""")
code("""h = pd.read_csv(C / "national_hot_days.csv")
fig, ax = plt.subplots(figsize=(11, 3.4))
ax.plot(h.year, h.days_tmax_ge40, label="days with tmax >= 40 C (district average)")
ax.plot(h.year, h.march_days_tmax_ge35, label="March days with tmax >= 35 C (wheat grain-fill heat)")
ax.legend(); save(fig, "09_hot_days"); plt.show()
for v in ("days_tmax_ge40", "march_days_tmax_ge35"):
    r = trend(h.year, h[v]); print(f"{v}: {r['sen_per_decade']:+.2f} days per decade (p={r['mk_p']:.2g})")""")

md("""## 4. The monsoon, 1901-2025""")
code("""mn = pd.read_csv(C / "monsoon_national_annual.csv"); mt = pd.read_csv(C / "monsoon_national_trends.csv")
fig, ax = plt.subplots(2, 2, figsize=(13, 7))
for a, v, t in ((ax[0, 0], "jjas_mm", "June-September rainfall (mm)"), (ax[0, 1], "heavy_days", "Heavy-rain days (>= 64.5 mm)"),
                (ax[1, 0], "longest_dry", "Longest dry spell in JJAS (days)"), (ax[1, 1], "share_area_deficient", "Share of area with deficient monsoon")):
    a.plot(mn.year, mn[v], lw=.8, c="tab:blue"); a.plot(mn.year, mn[v].rolling(10, center=True).mean(), lw=2, c="navy"); a.set_title(t)
save(fig, "09_monsoon"); plt.show()
print(mt.pivot_table(index="variable", columns="period", values="sen_per_decade").round(3))
print("\\nMann-Kendall p:"); print(mt.pivot_table(index="variable", columns="period", values="mk_p").round(3))
pd.read_csv(C / "monsoon_by_decade.csv").round(2)""")
md("""**Reading the monsoon.** Total monsoon rain has no strong all-India trend over 125 years - the monsoon is not
simply "drying". The change is in *how* rain falls: compare heavy-rain days and dry spells in the table above. A
district average smooths out single-station cloudbursts, so heavy-day counts here are lower than station counts.""")

md("""## 5. What the long-run warming means for harvests
Season night-time warming (1996-2025 normal minus 1951-1980 normal) x the robust Phase 8 night-heat coefficient.
This is a back-of-envelope number: it assumes the 1997-2022 sensitivity held earlier and ignores adaptation, new
varieties and CO2 fertilisation.""")
code("""s = pd.read_csv(C / "harvest_link_summary.csv"); print(s.round(3).to_string(index=False))
hw = pd.read_csv(C / "harvest_link_wheat.csv")
gg = geo.merge(hw, on="district_id")
fig, ax = plt.subplots(1, 2, figsize=(13, 6))
gg.plot(column="warming_c", cmap="Reds", legend=True, ax=ax[0], legend_kwds={"shrink": .6, "label": "C"}); ax[0].set_title("Wheat-season (Nov-Mar) night warming\\n1996-2025 vs 1951-1980"); ax[0].axis("off")
gg.plot(column="implied_yield_effect_pct", cmap="RdYlGn", vmin=-8, vmax=8, legend=True, ax=ax[1], legend_kwds={"shrink": .6, "label": "%"}); ax[1].set_title("Implied wheat yield effect of that warming (%)"); ax[1].axis("off")
save(fig, "09_map_wheat_warming_impact"); plt.show()""")
md("""**Reading it.** The wheat season's nights have warmed by about 0.6 C on average, which at the estimated -5% per
+1 C implies roughly a 3% (CI about 2.5-4%) drag on wheat yields compared with a 1951-80 climate - a drag that
technology and irrigation have more than offset, since yields still doubled. The district correlation between warming
rate and yield growth is weak and its sign is not causal evidence (fast-warming districts are also the irrigated
north-west where yields grew fastest).""")

md("""## 6. Beyond weather: other harvest factors
Only factors available from official sources without an account could be tested (see DECISIONS D22 and
`docs/MANUAL_DOWNLOADS.md` for the rest). Skill = 1 - MSE / MSE(trend-only), on yield anomalies.
`cv_skill` = year-grouped CV inside 1997-2017 (used to judge); `test_skill` = 2018+ scored once.""")
code("""for k in ("wheat", "rice_monsoon"):
    f = pd.read_csv(C / f"harvest_factors_{k}.csv"); print(k, "train rows", f.rows_train[0], "test rows", f.rows_test[0])
    print(f.pivot_table(index="features", columns="model", values=["cv_skill", "test_skill"]).round(3), "\\n")""")
md("""**Reading it.** Last year's yield anomaly is the single most useful non-weather factor: it raises wheat CV skill from
about 2% to 7%. On the test years it helps even more, partly because it corrects the drift of a trend fitted only up
to 2017 - useful for forecasting, but it is persistence, not agronomy. Groundwater dependence (tubewell share of
irrigation) adds nothing once irrigation is known. Weather still explains only a small part of year-to-year yield
changes; most variation comes from things not in public data (management, seed, pests, prices, reporting).""")

nb["cells"] = C
nbf.write(nb, ROOT / "notebooks" / "09_climate_trends.ipynb")
print("wrote notebooks/09_climate_trends.ipynb")
