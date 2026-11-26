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
                  "monsoon_annual", "monsoon_trends", "harvest_link",
                  "loss_by_year", "loss_region_year", "loss_weather", "loss_bins", "scenario_ci", "robustness"):
            t[n] = pd.read_sql(f"select * from {n}", con) if n in have else None
    t["geo"] = json.loads(GEOJSON.read_text())
    t["districts"]["state"] = t["districts"].state_id.map(STATES).fillna("Other")
    return t


T = load()
D = T["districts"]

# ------------------------------------------------------------------ sidebar
st.sidebar.title("🌾 Heat, Rain & Harvest")
st.sidebar.markdown("How India's weather is changing, and what it does to our **wheat** and **rice**.")
CROP_LABEL = {"Wheat": "🌾 Wheat (grows in winter)", "Rice (monsoon)": "🍚 Rice (grows in the monsoon)"}
crop = st.sidebar.radio("1. Pick a crop", list(CROP_LABEL), format_func=CROP_LABEL.get)
have = T["yields"][T["yields"].crop == crop].unit_id.unique()
opts = D[D.unit_id.isin(have)].assign(label=lambda d: d.d_name + " (" + d.state + ")").sort_values("label")
default = opts.index[opts.d_name.eq("Ludhiana")].tolist()
pick = st.sidebar.selectbox("2. Pick your district (type to search)", opts.label,
                            index=opts.index.get_loc(default[0]) if default else 0)
warm = st.sidebar.slider("3. What if India gets hotter by...", 0.5, 3.0, 2.0, 0.5, format="+%.1f °C",
                         help="Every day made this much warmer; rain unchanged; farmers change nothing")
st.sidebar.caption("Data: Government of India (Ministry of Agriculture, India Meteorological Department), 1997-2022.")
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

tab_home, tab_mine, tab_map, tab_exp = st.tabs(["🏠 Start here", "📍 My district", "🗺️ India map", "🔬 For experts"])
with tab_exp:
    st.caption("Detailed charts and methods for students, researchers and examiners.")
    tab_d, tab_loss, tab_clim, tab_about = st.tabs(
        ["📊 District details", "📉 Loss years", "🌡️ Climate 1901-2025", "ℹ️ About & caveats"])
season = lambda y: f"{int(y)}-{(int(y) + 1) % 100:02d}"      # agricultural year label, e.g. 2014 -> "2014-15"
WX_LABEL = {"tmin_mean": "Night temperature", "tmax_mean": "Day temperature", "feb_tmax_mean": "February day temp.",
            "mar_tmax_mean": "March day temp.", "mar_hot_days_35": "March days >= 35 °C", "rain_total": "Season rain",
            "rain_nov_jan": "Nov-Jan rain", "prev_monsoon_rain": "Previous monsoon rain", "rain_jun_sep": "Jun-Sep rain",
            "longest_dry_spell": "Longest dry spell", "rainy_days": "Rainy days", "hot_days_35": "Days >= 35 °C"}

# ------------------------------------------------------------------ plain-language helpers
st.markdown("""<style>
.card {border-radius: 14px; padding: 18px 18px 14px; background: rgba(127,127,127,.10); height: 100%;}
.card .big {font-size: 2.3rem; font-weight: 800; line-height: 1.1; margin: 4px 0 6px;}
.card .emo {font-size: 2rem;}
.card .txt {font-size: 1.02rem; line-height: 1.35;}
.pill {display:inline-block; padding: 4px 14px; border-radius: 999px; font-weight: 700; font-size: 1.1rem; color: #fff;}
.lead {font-size: 1.15rem; line-height: 1.5;}
</style>""", unsafe_allow_html=True)


def card(col, emoji, big, text, color="inherit"):
    col.markdown(f'<div class="card"><div class="emo">{emoji}</div><div class="big" style="color:{color}">{big}</div>'
                 f'<div class="txt">{text}</div></div>', unsafe_allow_html=True)


CROP_WORD = {"Wheat": "wheat", "Rice (monsoon)": "rice"}[crop]
RED, AMBER, GREEN, BLUE = "#d64545", "#e0a100", "#2e9e5b", "#3b7dd8"


def national_change(c: str, dc: float) -> float:
    s = T["scenarios"][(T["scenarios"].crop == c) & (T["scenarios"].delta_c == dc)].set_index("unit_id").delta_rel_yield
    a = T["yields"][T["yields"].crop == c].groupby("unit_id").area_ha.mean().reindex(s.index)
    ok = a.notna() & s.notna()
    return float(np.average(s[ok], weights=a[ok]))


def scenario_range(c: str, dc: float):
    """95% bootstrap interval (widest clustering scheme, D23) for the national change, if built."""
    ci = T["scenario_ci"]
    if ci is None:
        return None
    r = ci[(ci.crop == c) & (ci.delta_c == dc) & (ci.group == "all")]
    return (float(r.lo.iloc[0]), float(r.hi.iloc[0])) if len(r) else None


def night_effect(c: str = "Wheat"):
    """Simple-model effect of +1 C warmer nights (main robustness row), with its widest 95% CI."""
    rb = T["robustness"]
    if rb is None:
        return None
    r = rb[rb.crop == c].iloc[0]
    return float(r["effect per +1C night temp"]), float(r.ci_low), float(r.ci_high)


def risk_level(share: float):
    if pd.isna(share):
        return "Not enough data", "#888"
    if share < 0.15:
        return "LOW", GREEN
    return ("MEDIUM", AMBER) if share < 0.30 else ("HIGH", RED)


# ------------------------------------------------------------------ start here
with tab_home:
    st.title("Is a hotter India hurting our food?")
    st.markdown('<p class="lead">We looked at <b>26 years of harvests</b> in <b>every district of India</b> and '
                '<b>125 years of weather</b>, using only Government of India data. Here is what we found, in five numbers.</p>',
                unsafe_allow_html=True)
    warming = float(T["clim_trends"].query("period == 'annual' and variable == 'tmean'").sen_per_decade.iloc[0] * 7.4) \
        if T["clim_trends"] is not None else 0.56
    w2, r2 = national_change("Wheat", warm), national_change("Rice (monsoon)", warm)
    c1, c2, c3, c4, c5 = st.columns(5)
    card(c1, "🌡️", f"+{warming:.1f} °C", "India is <b>warmer</b> than in the 1950s. October and November warmed the most.", RED)
    card(c2, "❄️", "10 fewer", "<b>cold days</b> every winter than our grandparents had (about 89 then, 79 now).", BLUE)
    ne = night_effect("Wheat")
    ne_big = f"{ne[0]*100:+.0f}%".replace("-", "−") if ne else "−5%"
    ne_rng = f" (range {ne[1]*100:+.0f}% to {ne[2]*100:+.0f}%)".replace("-", "−") if ne else ""
    card(c3, "🌙", ne_big, f"<b>wheat</b> for every 1 °C warmer winter <b>night</b>{ne_rng}. Wheat needs cool nights to "
         "fill its grains. <i>Simple model: night temperature only.</i>", RED)
    card(c4, "🌧️", "2 in 3", "rice harvests in <b>central India</b> are bad years (more than 10% below normal) when the monsoon rain fails (normally 1 in 3).", AMBER)
    pct = lambda v: f"{v*100:+.0f}%".replace("-", "−")
    rng_w = scenario_range("Wheat", warm)
    rng_txt = f" (range {pct(rng_w[0])} to {pct(rng_w[1])})" if rng_w else ""
    card(c5, "🔮", pct(w2), f"wheat{rng_txt} (and {pct(r2)} rice) if <b>every day and night</b> gets <b>{warm:+.1f} °C</b> "
         "hotter and farmers change nothing. <i>Full model: all heat and rain measures.</i> Move the slider to try other numbers.", RED)

    st.markdown("### The story in four pictures")
    left, right = st.columns(2)
    if T["clim_annual"] is not None:
        ca = T["clim_annual"]
        sm = ca.tmean_anom_vs_1951_80.rolling(10, center=True, min_periods=5).mean()
        f = go.Figure()
        f.add_bar(x=ca.year, y=ca.tmean_anom_vs_1951_80, marker_color=np.where(ca.tmean_anom_vs_1951_80 > 0, RED, BLUE),
                  name="each year", opacity=.55)
        f.add_scatter(x=ca.year, y=sm, line=dict(color="#f39c12", width=4), name="10-year average")
        f.update_layout(title="① India is getting hotter<br><sup>Each bar is one year: red = hotter than the 1950s-70s, "
                              "blue = cooler; orange line = 10-year average</sup>", height=360, yaxis_title="°C warmer than 1951-80", showlegend=False,
                        margin=dict(t=70, b=10))
        left.plotly_chart(f, width="stretch")
    if T["clim_winters"] is not None:
        w = T["clim_winters"]
        f = go.Figure()
        f.add_scatter(x=w.season, y=w.cool_days.rolling(10, center=True, min_periods=5).mean(), fill="tozeroy",
                      line=dict(color=BLUE, width=3), name="cold days")
        f.update_layout(title="② Winters are getting shorter<br><sup>Number of cold days in a winter (10-year average)</sup>",
                        height=360, yaxis_title="cold days per winter", yaxis_range=[60, 100], margin=dict(t=70, b=10))
        right.plotly_chart(f, width="stretch")

    left, right = st.columns(2)
    if T["loss_by_year"] is not None:
        ly = T["loss_by_year"][T["loss_by_year"].crop == crop].copy()
        ly["season"] = ly.year.map(season)
        why = ({2014: "rain & hail at harvest", 2015: "warm, dry winter", 2005: "very hot February"} if crop == "Wheat"
               else {2002: "monsoon failed", 2015: "monsoon failed", 2009: "monsoon failed"})
        f = go.Figure()
        f.add_bar(x=ly.season, y=ly.share_area_in_loss * 100,
                  marker_color=np.where(ly.share_area_in_loss > .3, RED, "#b9b9b9"))
        for yr, txt in why.items():
            r = ly[ly.year == yr]
            if len(r):
                f.add_annotation(x=r.season.iloc[0], y=float(r.share_area_in_loss.iloc[0] * 100), text=txt,
                                 showarrow=True, arrowhead=0, ay=-30, font=dict(size=12))
        f.update_layout(title=f"③ Bad years for {CROP_WORD}<br><sup>% of India's {CROP_WORD} fields that gave a much smaller "
                              "harvest than usual (more than 10% less)</sup>", height=380, xaxis_type="category",
                        xaxis_tickangle=-60, yaxis_title="% of fields", margin=dict(t=70, b=10))
        left.plotly_chart(f, width="stretch")
    sc = pd.DataFrame({"crop": ["🌾 Wheat", "🍚 Rice"], "change": [w2 * 100, r2 * 100]})
    f = px.bar(sc, x="crop", y="change", text=sc.change.map(lambda v: f"{v:+.0f}%"), color_discrete_sequence=[RED])
    f.update_traces(textposition="outside", textfont_size=20)
    f.update_layout(title=f"④ If India gets {warm:+.1f} °C hotter<br><sup>Change in harvest if farmers change nothing "
                          "(move the slider on the left)</sup>", height=380, yaxis_title="% change in harvest",
                    yaxis_range=[min(-25, sc.change.min() * 1.4), 5], xaxis_title="", margin=dict(t=70, b=10))
    right.plotly_chart(f, width="stretch")

    st.markdown("### What does this mean?")
    st.markdown("""
- 🌙 **Warm nights are the hidden danger for wheat.** Hot days get the headlines, but wheat suffers most when winter
  *nights* stay warm.
- 💧 **Water protects rice, not wheat.** Irrigated districts barely lose rice in a drought. But water cannot cool a wheat
  plant in a heatwave, so even well-watered Punjab lost wheat in the March 2022 heatwave.
- 🧑‍🌾 **Farmers have kept up so far.** Harvests still grew over these 26 years thanks to better seeds and irrigation.
  The question is whether they can keep up if warming speeds up.
""")
    st.info("👉 **Next:** open **📍 My district** (top of the page) to see your own district, or **🗺️ India map** to compare districts.")
    st.caption("These are patterns from real data, not exact predictions. Weather is only one reason harvests go up and "
               "down; seeds, pests, prices and farming methods matter too. Details and methods: 🔬 For experts.")

# ------------------------------------------------------------------ my district (plain language)
with tab_mine:
    info = layer_df.loc[uid]
    y = y_all[y_all.unit_id == uid].sort_values("year")
    valid = y.dropna(subset=["yield_rel_anom"])
    n, bad = len(valid), int((valid.yield_rel_anom < -0.10).sum())
    level, lcol = risk_level(bad / n if n else np.nan)
    st.title(f"📍 {info.d_name}, {info.state}")
    st.markdown(f'<p class="lead">{CROP_LABEL[crop]} &nbsp; Risk of a bad harvest: '
                f'<span class="pill" style="background:{lcol}">{level}</span></p>', unsafe_allow_html=True)

    qpa = info.mean_yield * 10 / 2.471 if pd.notna(info.mean_yield) else np.nan      # t/ha -> quintals per acre
    irr = float(np.clip(y.irr_share.mean(), 0, 1)) if y.irr_share.notna().any() else np.nan
    c1, c2, c3, c4 = st.columns(4)
    card(c1, "📉", f"{bad} of {n}", f"years had a <b>bad harvest</b> here (much smaller than usual).", lcol)
    card(c2, "🌾" if crop == "Wheat" else "🍚", f"{qpa:.0f} quintals" if pd.notna(qpa) else "n/a",
         f"per acre is a <b>typical harvest</b> here ({info.mean_yield:.1f} tonnes per hectare).")
    card(c3, "💧", f"{irr*10:.0f} in 10" if pd.notna(irr) else "n/a",
         f"{CROP_WORD} fields here get <b>irrigation</b> water (not just rain).", BLUE)
    if pd.notna(info.scenario):
        word = "less" if info.scenario < 0 else "more"
        card(c4, "🔮", f"{abs(info.scenario)*100:.0f}% {word}",
             f"{CROP_WORD} if it gets <b>{warm:+.1f} °C</b> hotter here"
             + (f" (about {abs(info.scenario)*qpa:.1f} quintals per acre)." if pd.notna(qpa) else "."),
             RED if info.scenario < 0 else GREEN)
    else:
        card(c4, "🔮", "n/a", "No warming estimate for this district.")

    dtr = T["clim_district_trends"]
    if dtr is not None and (dtr.unit_id == uid).any():
        r = dtr[dtr.unit_id == uid].iloc[0]
        nights = r.tmin_per_decade * 7.4
        st.markdown(f"🌡️ **Since 1951, nights in {info.d_name} have become {abs(nights):.1f} °C "
                    f"{'warmer' if nights >= 0 else 'cooler'}** and days {abs(r.tmax_per_decade*7.4):.1f} °C "
                    f"{'warmer' if r.tmax_per_decade >= 0 else 'cooler'}.")

    st.markdown(f"### Every {CROP_WORD} harvest in {info.d_name}")
    f = go.Figure()
    f.add_bar(x=y.year.map(season), y=y.yield_t_ha * 10 / 2.471,
              marker_color=np.where(y.yield_rel_anom < -0.10, RED, GREEN), name="harvest")
    f.add_scatter(x=y.year.map(season), y=y.trend_full * 10 / 2.471, line=dict(color="#f39c12", dash="dash", width=3),
                  name="usual level")
    f.update_layout(height=380, xaxis_type="category", xaxis_tickangle=-60, yaxis_title="quintals per acre",
                    legend=dict(orientation="h", y=1.1), margin=dict(t=30, b=10))
    st.plotly_chart(f, width="stretch")
    st.caption("🟥 red = bad year (more than 10% below the usual level) · 🟩 green = normal or good year · "
               "orange dashed line = the usual level, which rises over time as farming improves.")

    # plain-language reason for each bad year, from that season's weather vs this district's normal
    cl = T["climate"][(T["climate"].crop == crop) & (T["climate"].unit_id == uid)].set_index("year")
    if crop == "Wheat":
        rules = [("tmin_mean", 1, "winter nights were unusually warm 🌙"), ("mar_tmax_mean", 1, "March was unusually hot ☀️"),
                 ("rain_total", 1, "it was an unusually wet season (rain or hail) 🌧️"),
                 ("rain_total", -1, "it was an unusually dry winter 🏜️")]
    else:
        rules = [("rain_jun_sep", -1, "the monsoon rain was far below normal 🏜️"),
                 ("longest_dry_spell", 1, "there was a long dry spell in the monsoon ☀️"),
                 ("rain_jun_sep", 1, "the monsoon was unusually heavy (possible floods) 🌊"),
                 ("tmax_mean", 1, "days were unusually hot ☀️")]
    z = {v: (cl[v] - cl[v].mean()) / cl[v].std() for v, _, _ in rules if v in cl}
    lines = []
    for _, r in valid[valid.yield_rel_anom < -0.10].iterrows():
        why = [txt for v, s, txt in rules if v in z and r.year in z[v].index and pd.notna(z[v][r.year])
               and ((s > 0 and z[v][r.year] > 0.8) or (s < 0 and z[v][r.year] < -0.8))]
        reason = (", ".join(why[:-1]) + " and " + why[-1] if len(why) > 1 else why[0]) if why else "the weather looked normal, so something else (pests, floods, seeds, " \
                                                 "markets, reporting) was probably the cause ❓"
        lines.append(f"- **{season(r.year)}:** harvest {abs(r.yield_rel_anom)*100:.0f}% below usual — {reason}.")
    if lines:
        st.markdown(f"### What happened in the bad years?")
        st.markdown("\n".join(lines))
        st.caption("Compared with this district's own normal weather. These are clues, not proof.")
    else:
        st.success(f"No bad {CROP_WORD} years in {info.d_name} in this period. 🎉")
    st.info("👉 Try another district in the left panel, or switch crop. Detailed charts are under 🔬 For experts.")

# ------------------------------------------------------------------ map
with tab_map:
    st.markdown(f"### {CROP_LABEL[crop]} across India")
    layers = {"⚠️ How often harvests were bad (>10% below normal, % of years)": ("risk_score", 100, "Reds", False),
              f"🔮 Harvest change if {warm:+.1f} °C hotter (%)": ("scenario", 100, "RdBu", True),
              "🌡️ How much 1 °C of heat hurts (% per °C)": ("heat_effect_per_c", 100, "RdBu", True),
              "🌾 Typical harvest (tonnes per hectare)": ("mean_yield", 1, "YlGn", False)}
    if crop == "Wheat":
        layers["🧩 Risk zones (districts grouped by climate)"] = ("zone", None, None, False)
    choice = st.selectbox("What do you want to see?", list(layers))
    st.caption({"risk_score": "Darker red = bad harvests happen more often there.",
                "scenario": "Red = harvest goes down, blue = goes up. Darker = bigger change.",
                "heat_effect_per_c": "Red = heat hurts the harvest more there.",
                "mean_yield": "Darker green = bigger harvests.",
                "zone": "Districts with similar climate risk share a colour."}[layers[choice][0]]
               + " Grey = no data or the crop is not grown. Hover over a district to see its name.")
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

# ------------------------------------------------------------------ loss years
with tab_loss:
    if T["loss_by_year"] is None:
        st.info("Loss-pattern tables not built yet: run `python -m src.loss_patterns` then `python -m src.build_db`.")
    else:
        st.markdown(f"#### {crop}: when and where were harvests bad (>10% below normal)?")
        st.caption("Loss season = district yield more than 10% below its own long-run trend. Weather is compared with the "
                   "same district's normal (z-score), so 'hot' means hot for that district. Patterns, not proof of cause.")
        if crop == "Wheat":
            st.markdown(
                "- **Warm nights** are the most consistent signal: in 7 of 8 regions loss seasons had warmer nights than normal "
                "(Gangetic plain: 32% of warm-night seasons were losses vs 6% of cool-night seasons).\n"
                "- **A weak monsoon before sowing** comes next (6 of 8 regions): less stored soil moisture and water.\n"
                "- **A hot February** matters as much as a hot March in the Gangetic plain and the hills (grain filling starts).\n"
                "- **Too much rain hurts too:** in the irrigated north-west, losses come with *wet* seasons (rain and hail near "
                "harvest, e.g. 2014-15).\n"
                "- Worst seasons: 2014-15 (unseasonal March rain), 2015-16 (warm and dry after two weak monsoons), "
                "2005-06 (very hot February), 2021-22 in the north-west (March heatwave).")
        else:
            st.markdown(
                "- **Rain is the main factor:** when Jun-Sep rain is far below a district's normal, loss rates jump "
                "(Central India 66% vs 33%; east 51%; dry west 45%). Long dry spells and fewer rainy days point the same way.\n"
                "- Loss years are also hotter by day, mostly because drought years are sunny: heat and drought come together.\n"
                "- The irrigated north-west barely reacts (12% loss rate vs 21-36% elsewhere): irrigation buffers drought.\n"
                "- Worst seasons: 2002, 2015, 2009 (official monsoon droughts). 2008 was wet and still had losses, so not "
                "every loss is a weather loss.")
        ly = T["loss_by_year"][T["loss_by_year"].crop == crop].copy()
        ly["season"] = ly.year.map(season)
        f1 = px.bar(ly, x="season", y=ly.share_area_in_loss * 100, color="mean_anomaly_pct", color_continuous_scale="RdBu",
                    range_color=(-15, 15), labels={"y": "% of crop area in loss", "mean_anomaly_pct": "mean yield vs trend (%)"},
                    title="Share of India's crop area in a loss season")
        st.plotly_chart(f1.update_layout(height=330, xaxis_tickangle=-60, xaxis_type="category"), width="stretch")

        ry = T["loss_region_year"][T["loss_region_year"].crop == crop]
        hm = ry.pivot_table(index="region", columns="year", values="share_area_in_loss") * 100
        f2 = px.imshow(hm, color_continuous_scale="Reds", zmin=0, zmax=100, aspect="auto",
                       labels={"color": "% area in loss", "x": "season (start year)", "y": ""},
                       title="Loss seasons by region (% of the region's crop area in loss)")
        st.plotly_chart(f2.update_layout(height=380), width="stretch")

        left, right = st.columns(2)
        wx = T["loss_weather"][T["loss_weather"].crop == crop].copy()
        wx["variable"] = wx.variable.map(WX_LABEL).fillna(wx.variable)
        hw = wx.pivot_table(index="region", columns="variable", values="z_loss_minus_normal")
        f3 = px.imshow(hw, color_continuous_scale="RdBu_r", zmin=-1, zmax=1, aspect="auto", text_auto=".1f",
                       labels={"color": "z (loss - normal)", "x": "", "y": ""},
                       title="Weather in loss seasons vs normal seasons")
        left.plotly_chart(f3.update_layout(height=430), width="stretch")
        left.caption("Red = higher than the district's normal in loss seasons; blue = lower. 1 = one standard deviation.")

        bn = T["loss_bins"][T["loss_bins"].crop == crop].copy()
        vopts = sorted(bn.variable.unique(), key=lambda v: list(WX_LABEL).index(v) if v in WX_LABEL else 99)
        v = right.selectbox("Loss rate when this was low / normal / high", vopts, format_func=lambda x: WX_LABEL.get(x, x))
        b = bn[bn.variable == v]
        f4 = px.bar(b, x="region", y=b.loss_rate * 100, color="bin", barmode="group",
                    category_orders={"bin": ["low (z<-1)", "normal", "high (z>1)"]},
                    color_discrete_map={"low (z<-1)": "#4393c3", "normal": "#bbbbbb", "high (z>1)": "#d6604d"},
                    labels={"y": "% of seasons that were losses", "region": ""})
        right.plotly_chart(f4.update_layout(height=390, xaxis_tickangle=-35), width="stretch")

        # the selected district: its loss seasons and that season's weather vs its own normal
        yd = y_all[(y_all.unit_id == uid)].merge(T["climate"][(T["climate"].crop == crop) & (T["climate"].unit_id == uid)],
                                                  on=["unit_id", "year"], how="left")
        cols = [c for c in (["tmin_mean", "mar_tmax_mean", "rain_total"] if crop == "Wheat"
                            else ["rain_jun_sep", "longest_dry_spell", "tmax_mean"]) if c in yd]
        for c in cols:
            yd[c] = (yd[c] - yd[c].mean()) / yd[c].std()
        lossy = yd[yd.yield_rel_anom < -0.10].sort_values("year")
        st.markdown(f"#### {pick}: {len(lossy)} loss seasons out of {yd.yield_rel_anom.notna().sum()}")
        if len(lossy):
            show = lossy[["year", "yield_rel_anom"] + cols].assign(year=lossy.year.map(season),
                                                                   yield_rel_anom=lossy.yield_rel_anom * 100)
            show = show.rename(columns={"year": "season", "yield_rel_anom": "yield vs trend (%)",
                                        **{c: WX_LABEL.get(c, c) + " (z)" for c in cols}})
            st.dataframe(show.round(1), hide_index=True, width="stretch")
            st.caption("z above +1 = unusually high for this district; below -1 = unusually low.")

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
- **Two heat numbers, two models.** The 🌙 number is a *simple* model: yield vs night temperature and rain only, with
  district and year effects. The 🔮 scenarios use the *full* model (all heat and rain measures: mean temperatures, degree
  days, extreme heat, March/February heat), Ridge regression with district and year effects, and warm every day and
  night. They answer different questions, so the numbers differ.
- **Uncertainty**: intervals are 95% bootstrap ranges. We resampled by district, by state and by year and report the
  widest, because neighbouring districts share weather and all districts share each year's national shocks.
""" + "".join(
        f"- {c}: {r.estimate*100:+.1f}% at +{r.delta_c:g} °C (95% range {r.lo*100:+.1f} to {r.hi*100:+.1f}, "
        f"resampled by {r.ci_used})\n"
        for c, rr in ([] if T["scenario_ci"] is None else T["scenario_ci"].query("group == 'all'").groupby("crop"))
        for r in rr.itertuples()) + """
- **Irrigation**: less-irrigated districts show larger losses, but they are also mostly hill districts, so this mixes
  irrigation with location.
- Built: """ + meta["built"])
