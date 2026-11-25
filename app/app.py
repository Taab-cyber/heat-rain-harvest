"""Crop-Climate Risk Atlas (Phase 9). Streamlit + SQLite.

Run from the project root:   streamlit run app/app.py
Reads only app/atlas.sqlite and app/districts.geojson (built by `python -m src.build_db`).
"""
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

APP = Path(__file__).resolve().parent
DB = APP / "atlas.sqlite"
GEOJSON = APP / "districts.geojson"
STATES = {1: "Jammu & Kashmir", 2: "Himachal Pradesh", 3: "Punjab", 4: "Chandigarh", 5: "Uttarakhand", 6: "Haryana",
          7: "Delhi", 8: "Rajasthan", 9: "Uttar Pradesh", 10: "Bihar", 11: "Sikkim", 12: "Arunachal Pradesh",
          13: "Nagaland", 14: "Manipur", 15: "Mizoram", 16: "Tripura", 17: "Meghalaya", 18: "Assam", 19: "West Bengal",
          20: "Jharkhand", 21: "Odisha", 22: "Chhattisgarh", 23: "Madhya Pradesh", 24: "Gujarat", 25: "Daman & Diu",
          26: "Dadra & Nagar Haveli", 27: "Maharashtra", 28: "Andhra Pradesh", 29: "Karnataka", 30: "Goa",
          31: "Lakshadweep", 32: "Kerala", 33: "Tamil Nadu", 34: "Puducherry", 35: "Andaman & Nicobar"}
# Census 2011 state codes (pc11_s_id). Telangana was part of Andhra Pradesh in 2011.

st.set_page_config(page_title="Crop-Climate Risk Atlas", page_icon="🌾", layout="wide")


@st.cache_data
def load():
    with sqlite3.connect(DB) as con:
        t = {n: pd.read_sql(f"select * from {n}", con) for n in
             ("districts", "yields", "climate", "sensitivity", "scenarios", "forecasts", "meta")}
        have = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
        for n in ("clim_annual", "clim_trends", "clim_winters", "clim_hot_days", "clim_records", "clim_district_trends",
                  "monsoon_annual", "monsoon_trends", "harvest_link"):
            t[n] = pd.read_sql(f"select * from {n}", con) if n in have else None
    t["geo"] = json.loads(GEOJSON.read_text())
    t["districts"]["state"] = t["districts"].state_id.map(STATES).fillna("Other")
    return t


T = load()
D = T["districts"]

# ------------------------------------------------------------------ sidebar
st.sidebar.title("🌾 Crop-Climate Risk Atlas")
st.sidebar.caption("Heat, Rain & Harvest: India, 1997-2022, Census 2011 districts")
crop = st.sidebar.radio("Crop", ["Wheat", "Rice (monsoon)"], help="Rice (monsoon) = kharif/autumn/winter rice only")
warm = st.sidebar.slider("Warming scenario (+X °C)", 0.5, 3.0, 2.0, 0.5,
                         help="Added to every day's max and min temperature; rain unchanged; no adaptation")
have = T["yields"][T["yields"].crop == crop].unit_id.unique()
opts = D[D.unit_id.isin(have)].assign(label=lambda d: d.d_name + " (" + d.state + ")").sort_values("label")
default = opts.index[opts.d_name.eq("Ludhiana")].tolist()
pick = st.sidebar.selectbox("District", opts.label, index=opts.index.get_loc(default[0]) if default else 0)
uid = int(opts.loc[opts.label == pick, "unit_id"].iloc[0])

# risk score: share of loss years (more than 10% below trend) in 1997-2017; wheat districts without data use propagated probability
y_all = T["yields"][T["yields"].crop == crop]
loss = y_all[y_all.year <= 2017].groupby("unit_id").yield_rel_anom.apply(lambda s: (s < -0.10).mean()).rename("risk_score")
scen = T["scenarios"][(T["scenarios"].crop == crop) & (T["scenarios"].delta_c == warm)].set_index("unit_id").delta_rel_yield
layer_df = D.set_index("unit_id").join(loss).join(scen.rename("scenario"))
layer_df = layer_df.join(T["sensitivity"][T["sensitivity"].crop == crop].set_index("unit_id").heat_effect_per_c)
layer_df = layer_df.join(y_all.groupby("unit_id").yield_t_ha.mean().rename("mean_yield"))
if crop == "Wheat":
    prop = layer_df.risk_prob_high.where(layer_df.risk_label_source == "propagated")
    layer_df["risk_score_src"] = np.where(layer_df.risk_score.notna(), "observed loss share", np.where(prop.notna(), "propagated (climate similarity)", None))
    layer_df["risk_score"] = layer_df.risk_score.fillna(prop)

tab_map, tab_d, tab_clim, tab_about = st.tabs(["🗺️ Map", "📍 District", "🌡️ Climate 1901-2025", "ℹ️ About & caveats"])

# ------------------------------------------------------------------ map
with tab_map:
    layers = {f"Yield change at +{warm:g} °C (% of trend)": ("scenario", 100, "RdBu", True),
              "Risk score (share of loss years 1997-2017)": ("risk_score", 100, "Reds", False),
              "Heat sensitivity (% yield per +1 °C)": ("heat_effect_per_c", 100, "RdBu", True),
              "Mean yield (t/ha)": ("mean_yield", 1, "YlGn", False)}
    if crop == "Wheat":
        layers["Risk zone (k-means, 1997-2017)"] = ("zone", None, None, False)
    choice = st.selectbox("Map layer", list(layers))
    col, scale, cmap, diverging = layers[choice]
    m = layer_df.reset_index()[["unit_id", "d_name", "state", col]].dropna(subset=[col])
    if scale is None:
        fig = px.choropleth(m, geojson=T["geo"], locations="unit_id", featureidkey="properties.unit_id", color=col,
                            hover_name="d_name", hover_data={"state": True, "unit_id": False},
                            color_discrete_sequence=px.colors.diverging.RdYlGn_r)
    else:
        m["value"] = m[col] * scale
        rng = np.nanpercentile(np.abs(m.value), 98) if diverging else None
        fig = px.choropleth(m, geojson=T["geo"], locations="unit_id", featureidkey="properties.unit_id", color="value",
                            color_continuous_scale=cmap, range_color=(-rng, rng) if diverging else None,
                            hover_name="d_name", hover_data={"state": True, "unit_id": False, "value": ":.2f"})
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(height=650, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
    if col == "scenario":
        w = layer_df.dropna(subset=["scenario", "mean_yield"])
        area = y_all.groupby("unit_id").area_ha.mean().reindex(w.index)
        st.metric(f"Area-weighted mean change at +{warm:g} °C ({crop})", f"{np.average(w.scenario, weights=area)*100:+.1f}%")
    st.caption("Grey = no data or not grown. Scenario values are model extrapolations (see About & caveats).")

# ------------------------------------------------------------------ district
with tab_d:
    info = layer_df.loc[uid]
    st.subheader(f"{info.d_name}, {info.state}: {crop}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mean yield (t/ha)", f"{info.mean_yield:.2f}" if pd.notna(info.mean_yield) else "n/a",
              help="Mean of 1997-2022 seasons in the analysis sample")
    c2.metric("Risk score", f"{info.risk_score:.0%}" if pd.notna(info.risk_score) else "n/a",
              help="Share of 1997-2017 years more than 10% below the district's trend")
    c3.metric("Per +1 °C", f"{info.heat_effect_per_c*100:+.1f}%" if pd.notna(info.heat_effect_per_c) else "n/a",
              help="Heat sensitivity: fixed-effects model, change in yield for +1 °C uniform warming, 2018-22 seasons")
    c4.metric(f"At +{warm:g} °C", f"{info.scenario*100:+.1f}%" if pd.notna(info.scenario) else "n/a",
              help="Modelled yield change under the slider's warming, % of trend yield")
    if crop == "Wheat" and isinstance(info.get("zone"), str):
        st.info(f"Risk zone: **{info.zone}**")

    y = y_all[y_all.unit_id == uid].sort_values("year")
    left, right = st.columns(2)
    with left:
        fig = go.Figure()
        fig.add_bar(x=y.year, y=y.yield_t_ha, name="yield", marker_color="#d9a441")
        fig.add_scatter(x=y.year, y=y.trend_full, name="trend", line=dict(color="black", dash="dash"))
        fig.update_layout(title="Yield and long-run trend (t/ha)", height=330, margin=dict(t=40, b=10))
        st.plotly_chart(fig, width="stretch")
    with right:
        c = T["climate"][(T["climate"].crop == crop) & (T["climate"].unit_id == uid)].sort_values("year")
        var = "mar_tmax_mean" if crop == "Wheat" else "rain_jun_sep"
        lab = "Mean March max temperature (°C)" if crop == "Wheat" else "Jun-Sep rainfall (mm)"
        if var in c and c[var].notna().any():
            fig = px.line(c, x="year", y=var, markers=True, title=lab)
            z = np.polyfit(c.year[c[var].notna()], c[var].dropna(), 1)
            fig.add_scatter(x=c.year, y=np.polyval(z, c.year), name="linear trend", line=dict(dash="dot"))
            fig.update_layout(height=330, margin=dict(t=40, b=10), showlegend=False)
            st.plotly_chart(fig, width="stretch")

    left, right = st.columns(2)
    with left:
        a = y.dropna(subset=["yield_rel_anom"])
        fig = px.bar(a, x="year", y=a.yield_rel_anom * 100, color=a.yield_rel_anom < -0.10,
                     color_discrete_map={True: "#c0392b", False: "#7f8c8d"}, title="Yield vs trend (%); red = loss year")
        fig.update_layout(height=300, showlegend=False, yaxis_title="%", margin=dict(t=40, b=10))
        st.plotly_chart(fig, width="stretch")
    with right:
        s = T["scenarios"][(T["scenarios"].crop == crop) & (T["scenarios"].unit_id == uid)]
        if len(s):
            fig = px.line(s, x="delta_c", y=s.delta_rel_yield * 100, markers=True, title="Modelled yield change vs warming (%)")
            fig.add_vline(x=warm, line_dash="dash")
            fig.update_layout(height=300, xaxis_title="+°C", yaxis_title="% of trend", margin=dict(t=40, b=10))
            st.plotly_chart(fig, width="stretch")

    f = T["forecasts"][(T["forecasts"].crop == crop) & (T["forecasts"].unit_id == uid)]
    if len(f):
        st.markdown("**Test-year forecasts (2018-22)**: model trained on 1997-2017 only")
        show = f.assign(season=f.year.astype(str) + "-" + (f.year + 1 - 2000).astype(str).str.zfill(2))[
            ["season", "actual", "trend_train", "pred_ridge"]].rename(columns={
            "actual": "actual (t/ha)", "trend_train": "trend-only forecast", "pred_ridge": "weather model (Ridge)"})
        st.dataframe(show.round(2), hide_index=True, width="stretch")
        st.caption("Out of sample, the weather model is only marginally better than the trend for wheat (+1.8% skill) and "
                   "not better for rice. It did not anticipate the 2021-22 Punjab-Haryana heat losses.")

# ------------------------------------------------------------------ long-run climate
with tab_clim:
    if T["clim_annual"] is None:
        st.info("Long-run climate tables not built yet: run `python -m src.climate_trends` then `python -m src.build_db`.")
    else:
        ca, ct = T["clim_annual"], T["clim_trends"]
        a = ct[(ct.period == "annual")].set_index("variable")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Mean temperature trend", f"{a.loc['tmean', 'sen_per_decade']:+.2f} °C/dec", help="Sen's slope, 1951-2025")
        c2.metric("Night (tmin) trend", f"{a.loc['tmin', 'sen_per_decade']:+.2f} °C/dec")
        c3.metric("Warming so far", f"{a.loc['tmean', 'sen_per_decade'] * 7.4:+.2f} °C", help="slope x 74 years")
        hot = T["clim_records"]
        c4.metric("Hottest year", str(int(hot.year.iloc[0])), f"{hot.tmean_anom_vs_1951_80.iloc[0]:+.2f} °C vs 1951-80")
        f = go.Figure()
        for v, col in (("tmax", "#d62728"), ("tmin", "#1f77b4"), ("tmean", "#333")):
            s = ca[f"{v}_anom_vs_1951_80"]
            f.add_scatter(x=ca.year, y=s, name=v, line=dict(color=col, width=1), opacity=.45)
            f.add_scatter(x=ca.year, y=s.rolling(10, center=True).mean(), name=f"{v} 10-yr mean", line=dict(color=col, width=3))
        f.update_layout(title="All-India temperature anomaly vs 1951-1980 (°C)", height=380, margin=dict(t=40, b=10))
        st.plotly_chart(f, width="stretch")

        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        mt = ct[(ct.variable == "tmean") & ct.period.isin(months)].set_index("period").loc[months].reset_index()
        mt["significant (5%)"] = np.where(mt.mk_p < .05, "yes", "no")
        left, right = st.columns(2)
        left.plotly_chart(px.bar(mt, x="period", y="sen_per_decade", color="significant (5%)",
                                 color_discrete_map={"yes": "#d62728", "no": "#bbb"},
                                 labels={"period": "", "sen_per_decade": "°C per decade"},
                                 title="Warming by month, 1951-2025").update_layout(height=330), width="stretch")
        w = T["clim_winters"]
        fw = go.Figure()
        fw.add_scatter(x=w.season, y=w.cool_days, name="cool days", line=dict(width=1))
        fw.add_scatter(x=w.season, y=w.cool_days.rolling(10, center=True).mean(), name="10-yr mean", line=dict(width=3))
        fw.update_layout(title="Cool days per winter (Oct-Mar, colder than the coolest quarter of the year in 1951-80)", height=330)
        right.plotly_chart(fw, width="stretch")

        dtr = T["clim_district_trends"]
        if dtr is not None:
            fm = px.choropleth(dtr.merge(D[["unit_id", "d_name"]], on="unit_id"), geojson=T["geo"], locations="unit_id",
                               featureidkey="properties.unit_id", color="tmin_per_decade", color_continuous_scale="RdBu_r",
                               range_color=(-.25, .25), hover_name="d_name", labels={"tmin_per_decade": "°C / decade"},
                               title="Night-time (tmin) warming by district, 1951-2025")
            fm.update_geos(fitbounds="locations", visible=False).update_layout(height=520, margin=dict(t=40, b=0))
            st.plotly_chart(fm, width="stretch")
            r = dtr[dtr.unit_id == uid]
            if len(r):
                st.write(f"**{pick}**: day-time {r.tmax_per_decade.iloc[0]:+.2f} °C/decade, "
                         f"night-time {r.tmin_per_decade.iloc[0]:+.2f} °C/decade (1951-2025).")

        if T["monsoon_annual"] is not None:
            mn = T["monsoon_annual"]
            fmn = go.Figure()
            fmn.add_bar(x=mn.year, y=mn.jjas_mm, name="June-September rain (mm)", marker_color="#6baed6")
            fmn.add_scatter(x=mn.year, y=mn.jjas_mm.rolling(10, center=True).mean(), name="10-yr mean", line=dict(color="#08519c", width=3))
            fmn.update_layout(title="All-India monsoon rainfall, 1901-2025 (district-area weighted)", height=340, yaxis_range=[600, 1100])
            st.plotly_chart(fmn, width="stretch")
            mtr = T["monsoon_trends"]
            st.dataframe(mtr[mtr.period == "1951-2025"][["variable", "sen_per_decade", "mk_p"]].round(4),
                         hide_index=True, width="stretch")
        if T["harvest_link"] is not None:
            st.markdown("#### What the warming already means for harvests")
            st.dataframe(T["harvest_link"].round(3), hide_index=True, width="stretch")
            st.caption("Season night warming (1996-2025 vs 1951-80) x the Phase 8 night-heat coefficient. Back-of-envelope: "
                       "assumes today's sensitivity held earlier; ignores adaptation, new varieties and CO2.")

# ------------------------------------------------------------------ about
with tab_about:
    meta = dict(zip(T["meta"].key, T["meta"].value))
    st.markdown("### What this atlas shows")
    st.markdown("District-level wheat and monsoon-rice yields (1997-2022) on fixed Census 2011 districts, their link to "
                "heat and rain, a data-driven risk score, and modelled yield changes under uniform warming.")
    st.markdown("### Sources"); st.write(meta["sources"])
    st.markdown("### Caveats (please read)"); st.write(meta["caveats"])
    st.markdown("""
- **Risk score** = share of 1997-2017 seasons more than 10% below the district's trend. For wheat districts with too few
  years, a value propagated from climatically similar districts is shown (validated balanced accuracy 0.64).
- **Heat sensitivity / scenarios** come from a district-fixed-effects regression of yield anomalies on weather; national
  estimates: wheat -5.7% at +1 °C and -11.3% at +2 °C (95% bootstrap CI -13.2 to -9.4); monsoon rice -4.4% and -7.5%.
- **Irrigation**: less-irrigated districts show larger losses, but they are also mostly hill districts, so this mixes
  irrigation with location.
- Built: """ + meta["built"])
