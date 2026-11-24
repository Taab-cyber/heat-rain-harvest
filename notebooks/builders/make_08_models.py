"""Builds notebooks/08_models.ipynb. Reads results saved by `python -m src.run_phase8` (no refitting)."""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[2]
nb = nbf.v4.new_notebook()
C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s))
code = lambda s: C.append(nbf.v4.new_code_cell(s))

md("""# 08 - Prediction, forecast and warming scenarios
**Heat, Rain & Harvest.** Phase 8. Train 1997-2017, test 2018-2022 (time-based split; nothing from the test years is used
for fitting, scaling, trends or tuning). All numbers here are read from `data/processed/phase8/`, produced by
`python -m src.run_phase8` (see DECISIONS D18, D19).""")

code("""import sys, json
from pathlib import Path
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT))
import numpy as np, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
from src.config import PROCESSED, FIGURES
from src.boundaries import load_pc11_districts
sns.set_theme(style="whitegrid"); plt.rcParams["figure.dpi"] = 110
save = lambda fig, n: fig.savefig(FIGURES / f"{n}.png", bbox_inches="tight", dpi=150)
OUT = PROCESSED / "phase8"; geo = load_pc11_districts()
summary = json.load(open(OUT / "run_summary.json"))
for k, v in summary.items(): print(k, "features:", v["features"], "| log rain:", v["log_rain"])""")

md("""## 1. Do the models beat the trend-only baseline? (test years 2018-2022)
**Skill vs baseline** = 1 - MSE(model) / MSE(baseline). Positive = better than just extending each district's trend.""")
code("""for key, name in (("wheat", "Wheat"), ("rice_monsoon", "Rice (monsoon season)")):
    te = pd.read_csv(OUT / f"eval_test_{key}.csv", index_col=0); trn = pd.read_csv(OUT / f"eval_train_{key}.csv", index_col=0)
    print(f"\\n{name} - TEST"); print(te.round(4).to_string())
    print(f"{name} - TRAIN skill (in-sample):", trn["skill vs baseline"].round(3).to_dict())
fig, ax = plt.subplots(1, 2, figsize=(12, 3.8), sharey=True)
for a, key, name in ((ax[0], "wheat", "Wheat"), (ax[1], "rice_monsoon", "Rice (monsoon)")):
    te = pd.read_csv(OUT / f"eval_test_{key}.csv", index_col=0)["skill vs baseline"].drop("Baseline (trend only)")
    trn = pd.read_csv(OUT / f"eval_train_{key}.csv", index_col=0)["skill vs baseline"].drop("Baseline (trend only)")
    x = np.arange(len(te)); a.bar(x - .2, trn.values * 100, .4, label="train (in-sample)"); a.bar(x + .2, te.values * 100, .4, label="test 2018-22")
    a.axhline(0, c="k", lw=.8); a.set_xticks(x); a.set_xticklabels(te.index, rotation=20, ha="right", fontsize=8); a.set_title(name)
ax[0].set_ylabel("skill vs trend-only baseline (%)"); ax[0].legend()
save(fig, "08_skill_train_vs_test"); plt.show()""")
md("""**Reading this honestly:** flexible models (random forest, boosting) look good in-sample and lose that advantage on
new years, which is overfitting. On test years every model is within a few percent of the baseline. Weather explains
only a small share of year-to-year yield variation out of sample (about 1-2% in training-year cross-validation, D19).""")

code("""fig, ax = plt.subplots(1, 2, figsize=(12, 3.6), sharey=True)
for a, key, name in ((ax[0], "wheat", "Wheat"), (ax[1], "rice_monsoon", "Rice (monsoon)")):
    s = pd.read_csv(OUT / f"skill_by_year_{key}.csv", index_col=0).drop(columns="Baseline (trend only)") * 100
    s.plot(ax=a, marker="o"); a.axhline(0, c="k", lw=.8); a.set(title=f"{name}: skill by test year (%)", xlabel="agricultural year")
    a.legend(fontsize=7)
save(fig, "08_skill_by_year"); plt.show()""")

md("""## 2. The pre-harvest wheat forecast
The wheat weather window ends on **31 March** and the preceding-monsoon rain is known before sowing, so every wheat
prediction above is a **pre-harvest forecast** (harvest is in April). How did it do in the 2021-22 heatwave season?""")
code("""p = pd.read_parquet(OUT / "predictions_wheat.parquet")
p = p[~p.train & p.yield_t_ha.notna()].copy()
best = "pred_Ridge"
for yr in (2021,):
    g = p[p.year == yr]
    for region, ids in (("Punjab+Haryana", [3, 6]), ("All India (sample)", None)):
        s = g if ids is None else g[g.state_id.isin(ids)]
        print(f"{yr}-{yr-1999:02d} {region}: actual vs trend {(s.yield_t_ha/s.trend_train-1).median()*100:+.1f}%, "
              f"Ridge forecast vs trend {(s[best]/s.trend_train-1).median()*100:+.1f}%  (median over districts, n={len(s)})")
fig, ax = plt.subplots(figsize=(5.5, 5))
g = p[p.year == 2021]
ax.scatter(g.yield_t_ha / g.trend_train - 1, g[best] / g.trend_train - 1, s=10, alpha=.6)
ax.axline((0, 0), slope=1, c="k", lw=.8); ax.set(xlabel="actual anomaly 2021-22", ylabel="forecast anomaly (Ridge)",
       title="Wheat 2021-22: forecast vs actual"); ax.set_xlim(-.6, .6); ax.set_ylim(-.15, .15)
save(fig, "08_forecast_2022"); plt.show()""")
md("""The forecast anomalies are tiny compared with what happened (note the different axis ranges): the model is very
cautious (Ridge shrinks coefficients) and it did not anticipate the Punjab-Haryana losses. As an early-warning tool for
heat damage it is **not** good enough; this is reported as a limitation.""")

md("""## 3. Yield-loss classifier (loss = more than 10% below the train-only trend)""")
code("""for key, name in (("wheat", "Wheat"), ("rice_monsoon", "Rice (monsoon)")):
    print(f"\\n{name}"); print(pd.read_csv(OUT / f"eval_classifier_{key}.csv", index_col=0).round(3).to_string())""")
md("""ROC-AUC 0.5 = coin flip, 1 = perfect. The baseline (each district's historical loss frequency) is hard to beat:
knowing *where* losses usually happen is about as informative as this year's weather.""")

md("""## 4. Robustness of the main heat effect (district + year fixed effects, clustered SE)""")
code("""for key, name in (("wheat", "Wheat"), ("rice_monsoon", "Rice (monsoon)")):
    r = pd.read_csv(OUT / f"robustness_{key}.csv")
    print(f"\\n{name}: effect of +1 C season night temperature on relative yield")
    print(r.assign(**{c: r[c] * 100 for c in ["effect per +1C night temp", "ci_low", "ci_high"]}).round(2).to_string(index=False))
r = pd.read_csv(OUT / "robustness_wheat.csv")
fig, ax = plt.subplots(figsize=(7, 3.8))
ax.errorbar(r["effect per +1C night temp"] * 100, range(len(r)), xerr=[(r["effect per +1C night temp"] - r.ci_low) * 100,
            (r.ci_high - r["effect per +1C night temp"]) * 100], fmt="o", capsize=3)
ax.set_yticks(range(len(r))); ax.set_yticklabels(r.variant, fontsize=8); ax.axvline(0, c="k", lw=.8)
ax.set(xlabel="% yield change per +1 C night temperature (95% CI)", title="Wheat: robustness of the night-heat effect")
save(fig, "08_robustness_wheat"); plt.show()""")

md("""## 5. Warming scenarios: +1 C and +2 C
Every daily max and min temperature is raised by 1 or 2 C, the season features are recomputed from the daily data, and
the fixed-effects model predicts the change in yield for the 2018-22 seasons. **Assumptions:** uniform warming, unchanged
rain, no adaptation (same sowing dates, varieties, irrigation). Warming of 2 C lies partly outside the variation seen in
1997-2017, so these are model extrapolations, not forecasts.""")
code("""prof = pd.read_parquet(PROCESSED / "district_profiles.parquet")
zones = pd.read_csv(PROCESSED / "risk_zones_wheat.csv", index_col=0)
for key, name in (("wheat", "Wheat"), ("rice_monsoon", "Rice (monsoon)")):
    s = pd.read_parquet(OUT / f"scenarios_{key}.parquet")
    d = s.groupby(["unit_id", "delta_c"]).agg(delta=("delta_rel_yield", "mean"), area=("area_ha", "mean"), irr=("irr_static", "first")).reset_index()
    print(f"\\n{name}: area-weighted mean change in yield (% of trend)")
    for dc, g in d.groupby("delta_c"):
        print(f"  +{dc:.0f} C: {np.average(g.delta, weights=g.area)*100:+.1f}%   (districts: 10th pct {g.delta.quantile(.1)*100:+.1f}%, "
              f"median {g.delta.median()*100:+.1f}%, 90th pct {g.delta.quantile(.9)*100:+.1f}%)")
        g2 = g.assign(irr_group=pd.cut(g.irr, [0, .5, .9, 1.01], labels=["<50%", "50-90%", ">90%"]))
        print("     by irrigation:", g2.groupby("irr_group", observed=True).apply(
            lambda x: round(np.average(x.delta, weights=x.area) * 100, 1), include_groups=False).to_dict())
    if key == "wheat":
        z = d[d.delta_c == 2].set_index("unit_id").join(zones)
        print("     +2 C by risk zone:", z.groupby("zone").apply(lambda x: round(np.average(x.delta, weights=x.area) * 100, 1), include_groups=False).to_dict())
    two = d[d.delta_c == 2].set_index("unit_id").delta * 100
    g = geo.merge(two.rename("v").reset_index().rename(columns={"unit_id": "district_id"}), on="district_id", how="left")
    fig, ax = plt.subplots(figsize=(6.5, 7))
    lim = np.nanpercentile(np.abs(g.v), 98)
    g.plot(column="v", cmap="RdBu", vmin=-lim, vmax=lim, legend=True, ax=ax, linewidth=.05, edgecolor="grey",
           missing_kwds=dict(color="#eeeeee"), legend_kwds=dict(shrink=.6))
    ax.set_axis_off(); ax.set_title(f"{name}: modelled yield change at +2 C (% of trend)")
    save(fig, f"08_map_scenario_2C_{key}"); plt.show()""")

md("""### 5b. Uncertainty: cluster bootstrap (300 resamples of districts, `src/scenario_uncertainty.py`)""")
code("""R = pd.read_parquet(OUT / "scenario_bootstrap.parquet")
est = R[R.b == 0].set_index(["crop", "delta_c"])[["all", "<50%", "50-90%", ">90%"]] * 100
lo = R[R.b > 0].groupby(["crop", "delta_c"])[["all", "<50%", "50-90%", ">90%"]].quantile(.025) * 100
hi = R[R.b > 0].groupby(["crop", "delta_c"])[["all", "<50%", "50-90%", ">90%"]].quantile(.975) * 100
tab = est.round(1).astype(str) + " [" + lo.round(1).astype(str) + ", " + hi.round(1).astype(str) + "]"
print("Area-weighted yield change, % of trend, with 95% bootstrap interval (columns = irrigation group)"); print(tab.to_string())""")
md("""**Caution on the irrigation gradient.** Irrigation here is each district's fixed training-period share, and the
least-irrigated wheat districts are mostly cool Himalayan hill districts (risk zone 4). The gradient therefore mixes
"less irrigation" with "different climate and location", and +2 C in the hills is an extrapolation. It is consistent with
irrigation reducing heat losses, but it is not a clean causal estimate of irrigation's protective effect (compare Phase 6:
the wheat heat x irrigation interaction was not significant on its own, p = 0.10).""")

md("""## 6. Summary (written after reviewing the outputs: see LEARNING.md / VIVA.md Phase 8)""")

nb["cells"] = C
nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3"}
nbf.write(nb, ROOT / "notebooks" / "08_models.ipynb")
print("written")
