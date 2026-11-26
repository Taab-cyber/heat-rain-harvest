"""Heat, Rain & Harvest: Crop-Climate Risk Atlas. Streamlit + SQLite.

Run from the project root:   streamlit run app/app.py
Reads only app/atlas.sqlite and app/districts.geojson (built by `python -m src.build_db`).
Helpers without Streamlit live in app/helpers.py (tested in tests/test_app_helpers.py),
interface text in app/i18n.py, the PDF report in app/report_pdf.py.
"""
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from helpers import (BAD, advice_keys, district_panel, district_summary, drought_bad_years, risk_level, season)
from i18n import LANGS, tr

# ------------------------------------------------------------------ advice (D24)
# General actions shown in "What can be done?". Each links to an official page. No variety names, doses or
# dates on purpose: those depend on the farm and change every season, so we point to the people who decide them.
# Sources marked verified=False could not be opened from our build machine on 2026-11-26 and need a manual check.
# Every Hindi and Punjabi text needs review by a native speaker.
ADVICE = {
    "wheat_heat": {
        "en": "Sow on time. Late-sown wheat fills its grain in the March heat, and hot Marches go with lower yields. "
              "Ask which heat-tolerant varieties are recommended for your area.",
        "hi": "समय पर बुआई करें। देर से बोया गया गेहूँ मार्च की गर्मी में दाना भरता है, और गर्म मार्च में पैदावार घटती है। "
              "पूछें कि आपके इलाके के लिए गर्मी सहने वाली कौन सी किस्में सुझाई गई हैं।",  # needs human review
        "pa": "ਸਮੇਂ ਸਿਰ ਬਿਜਾਈ ਕਰੋ। ਪਿਛੇਤੀ ਬੀਜੀ ਕਣਕ ਮਾਰਚ ਦੀ ਗਰਮੀ ਵਿੱਚ ਦਾਣਾ ਭਰਦੀ ਹੈ, ਅਤੇ ਗਰਮ ਮਾਰਚ ਵਿੱਚ ਝਾੜ ਘਟਦਾ ਹੈ। "
              "ਪੁੱਛੋ ਕਿ ਤੁਹਾਡੇ ਇਲਾਕੇ ਲਈ ਗਰਮੀ ਸਹਿਣ ਵਾਲੀਆਂ ਕਿਹੜੀਆਂ ਕਿਸਮਾਂ ਦੀ ਸਿਫ਼ਾਰਸ਼ ਹੈ।",  # needs human review
        "sources": [("ICAR-Indian Institute of Wheat and Barley Research, Karnal", "https://iiwbr.icar.gov.in/", False),
                    ("Punjab Agricultural University, Ludhiana", "https://www.pau.edu/", True)],
    },
    "rice_drought": {
        "en": "Several bad rice years here came with a weak monsoon. Ask about drought-tolerant and short-duration rice "
              "varieties suited to your district, and about saving water in the nursery and the field.",
        "hi": "यहाँ धान के कई खराब साल कमज़ोर मानसून के साथ आए। अपने ज़िले के लिए सूखा सहने वाली और कम अवधि वाली धान की "
              "किस्मों के बारे में पूछें, और नर्सरी व खेत में पानी बचाने के तरीकों के बारे में भी।",  # needs human review
        "pa": "ਇੱਥੇ ਝੋਨੇ ਦੇ ਕਈ ਮਾੜੇ ਸਾਲ ਕਮਜ਼ੋਰ ਮਾਨਸੂਨ ਨਾਲ ਆਏ। ਆਪਣੇ ਜ਼ਿਲ੍ਹੇ ਲਈ ਸੋਕਾ ਸਹਿਣ ਵਾਲੀਆਂ ਅਤੇ ਘੱਟ ਸਮੇਂ ਵਾਲੀਆਂ ਝੋਨੇ ਦੀਆਂ "
              "ਕਿਸਮਾਂ ਬਾਰੇ ਪੁੱਛੋ, ਅਤੇ ਪਨੀਰੀ ਤੇ ਖੇਤ ਵਿੱਚ ਪਾਣੀ ਬਚਾਉਣ ਦੇ ਤਰੀਕਿਆਂ ਬਾਰੇ ਵੀ।",  # needs human review
        "sources": [("Indian Council of Agricultural Research", "https://icar.org.in/", True),
                    ("ICAR-National Rice Research Institute, Cuttack", "https://icar-nrri.in/", False)],
    },
    "water": {
        "en": "Less than half of the crop area here is irrigated. Drip and sprinkler irrigation can get government "
              "support under the Pradhan Mantri Krishi Sinchayee Yojana (Per Drop More Crop).",
        "hi": "यहाँ आधे से कम रकबे में सिंचाई होती है। प्रधानमंत्री कृषि सिंचाई योजना (पर ड्रॉप मोर क्रॉप) के तहत ड्रिप और "
              "स्प्रिंकलर सिंचाई पर सरकारी मदद मिल सकती है।",  # needs human review
        "pa": "ਇੱਥੇ ਅੱਧੇ ਤੋਂ ਘੱਟ ਰਕਬੇ ਵਿੱਚ ਸਿੰਜਾਈ ਹੁੰਦੀ ਹੈ। ਪ੍ਰਧਾਨ ਮੰਤਰੀ ਕ੍ਰਿਸ਼ੀ ਸਿੰਚਾਈ ਯੋਜਨਾ (ਪਰ ਡ੍ਰੌਪ ਮੋਰ ਕ੍ਰੌਪ) ਤਹਿਤ ਤੁਪਕਾ "
              "ਅਤੇ ਫੁਹਾਰਾ ਸਿੰਜਾਈ ਲਈ ਸਰਕਾਰੀ ਮਦਦ ਮਿਲ ਸਕਦੀ ਹੈ।",  # needs human review
        "sources": [("Pradhan Mantri Krishi Sinchayee Yojana", "https://pmksy.gov.in/", True)],
    },
    "insurance": {
        "en": "Crop insurance under the Pradhan Mantri Fasal Bima Yojana covers yield losses caused by weather. "
              "Enrolment closes on fixed dates each season, so check them early.",
        "hi": "प्रधानमंत्री फ़सल बीमा योजना के तहत फ़सल बीमा मौसम से हुए पैदावार के नुकसान को कवर करता है। हर मौसम में "
              "नामांकन तय तारीख तक ही होता है, इसलिए तारीखें पहले से देख लें।",  # needs human review
        "pa": "ਪ੍ਰਧਾਨ ਮੰਤਰੀ ਫ਼ਸਲ ਬੀਮਾ ਯੋਜਨਾ ਤਹਿਤ ਫ਼ਸਲ ਬੀਮਾ ਮੌਸਮ ਕਾਰਨ ਹੋਏ ਝਾੜ ਦੇ ਨੁਕਸਾਨ ਨੂੰ ਕਵਰ ਕਰਦਾ ਹੈ। ਹਰ ਮੌਸਮ ਵਿੱਚ ਨਾਮਾਂਕਣ "
              "ਮਿੱਥੀ ਤਾਰੀਖ਼ ਤੱਕ ਹੀ ਹੁੰਦਾ ਹੈ, ਇਸ ਲਈ ਤਾਰੀਖ਼ਾਂ ਪਹਿਲਾਂ ਹੀ ਵੇਖ ਲਓ।",  # needs human review
        "sources": [("Pradhan Mantri Fasal Bima Yojana", "https://pmfby.gov.in/", True)],
    },
    "advisory": {
        "en": "Use the district agromet advisories from the India Meteorological Department for sowing, irrigation and "
              "spraying decisions, and contact your nearest Krishi Vigyan Kendra.",
        "hi": "बुआई, सिंचाई और छिड़काव के फ़ैसलों के लिए भारत मौसम विज्ञान विभाग की ज़िला कृषि-मौसम सलाह देखें, और अपने "
              "नज़दीकी कृषि विज्ञान केंद्र से संपर्क करें।",  # needs human review
        "pa": "ਬਿਜਾਈ, ਸਿੰਜਾਈ ਅਤੇ ਛਿੜਕਾਅ ਦੇ ਫ਼ੈਸਲਿਆਂ ਲਈ ਭਾਰਤ ਮੌਸਮ ਵਿਗਿਆਨ ਵਿਭਾਗ ਦੀ ਜ਼ਿਲ੍ਹਾ ਖੇਤੀ-ਮੌਸਮ ਸਲਾਹ ਵੇਖੋ, ਅਤੇ ਆਪਣੇ "
              "ਨੇੜਲੇ ਕ੍ਰਿਸ਼ੀ ਵਿਗਿਆਨ ਕੇਂਦਰ ਨਾਲ ਸੰਪਰਕ ਕਰੋ।",  # needs human review
        "sources": [("IMD Agromet Advisory Services",
                     "https://mausam.imd.gov.in/responsive/agromet_adv_ser_state_current.php", True),
                    ("Krishi Vigyan Kendra portal (ICAR)", "https://kvk.icar.gov.in/", False)],
    },
}

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
RED, AMBER, GREEN, BLUE, ORANGE = "#c8443c", "#d39b00", "#2e8b57", "#3b6fb6", "#e08e0b"

st.set_page_config(page_title="Heat, Rain & Harvest", page_icon="🌾", layout="wide")


@st.cache_data
def load():
    with sqlite3.connect(DB) as con:
        t = {n: pd.read_sql(f"select * from {n}", con) for n in
             ("districts", "yields", "climate", "sensitivity", "scenarios", "forecasts", "meta")}
        have = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
        for n in ("clim_annual", "clim_trends", "clim_winters", "clim_hot_days", "clim_records", "clim_district_trends",
                  "monsoon_annual", "monsoon_trends", "harvest_link",
                  "loss_by_year", "loss_region_year", "loss_weather", "loss_bins", "scenario_ci", "robustness",
                  "value_state_check", "value_district", "value_india", "value_series"):
            t[n] = pd.read_sql(f"select * from {n}", con) if n in have else None
    t["geo"] = json.loads(GEOJSON.read_text())
    t["districts"]["state"] = t["districts"].state_id.map(STATES).fillna("Other")
    return t


T = load()
D = T["districts"]


@st.cache_data
def summary_csv() -> bytes:
    return district_summary(T["districts"], T["yields"], T["sensitivity"], T["scenarios"], STATES).to_csv(
        index=False).encode()


@st.cache_data
def panel_csv(crop_: str) -> bytes:
    return district_panel(T["yields"], T["climate"], T["districts"], crop_, STATES).to_csv(index=False).encode()


@st.cache_data
def march_heat_percentile() -> pd.Series:
    """Each wheat district's percentile (0-1) of average March days >= 35 C."""
    c = T["climate"][T["climate"].crop == "Wheat"]
    return c.groupby("unit_id").mar_hot_days_35.mean().rank(pct=True)


# ------------------------------------------------------------------ sidebar
lang = st.sidebar.radio("Language / भाषा / ਭਾਸ਼ਾ", list(LANGS), format_func=LANGS.get, horizontal=True)
t = lambda key, **v: tr(lang, key, **v)
st.sidebar.title(t("app_title"))
st.sidebar.caption(t("app_sub"))
CROP_LABEL = {"Wheat": t("crop_wheat"), "Rice (monsoon)": t("crop_rice")}
crop = st.sidebar.radio(t("crop"), list(CROP_LABEL), format_func=CROP_LABEL.get)
have = T["yields"][T["yields"].crop == crop].unit_id.unique()
opts = D[D.unit_id.isin(have)].assign(label=lambda d: d.d_name + " (" + d.state + ")").sort_values("label")
default = opts.index[opts.d_name.eq("Ludhiana")].tolist()
pick = st.sidebar.selectbox(t("district"), opts.label, index=opts.index.get_loc(default[0]) if default else 0)
warm = st.sidebar.slider(t("warm"), 0.5, 3.0, 2.0, 0.5, format="+%.1f °C", help=t("warm_help"))
st.sidebar.caption(t("data_note"))
uid = int(opts.loc[opts.label == pick, "unit_id"].iloc[0])
CROP_WORD = {"Wheat": "wheat", "Rice (monsoon)": "rice"}[crop]

# risk score: share of bad years in 1997-2017; wheat districts without data use the propagated probability
y_all = T["yields"][T["yields"].crop == crop]
loss = y_all[y_all.year <= 2017].groupby("unit_id").yield_rel_anom.apply(lambda s: (s < BAD).mean()).rename("risk_score")
scen = T["scenarios"][(T["scenarios"].crop == crop) & (T["scenarios"].delta_c == warm)].set_index("unit_id").delta_rel_yield
layer_df = D.set_index("unit_id").join(loss).join(scen.rename("scenario"))
layer_df = layer_df.join(T["sensitivity"][T["sensitivity"].crop == crop].set_index("unit_id").heat_effect_per_c)
layer_df = layer_df.join(y_all.groupby("unit_id").yield_t_ha.mean().rename("mean_yield"))
if crop == "Wheat":
    prop = layer_df.risk_prob_high.where(layer_df.risk_label_source == "propagated")
    layer_df["risk_score_src"] = np.where(layer_df.risk_score.notna(), "observed", np.where(prop.notna(), "propagated", None))
    layer_df["risk_score"] = layer_df.risk_score.fillna(prop)

tab_home, tab_mine, tab_map, tab_exp = st.tabs(["Start here", "My district", "India map", "For experts"])
with tab_exp:
    st.caption("Detailed charts, methods and data downloads.")
    tab_d, tab_loss, tab_value, tab_clim, tab_about = st.tabs(
        ["District details", "Bad seasons", "Production and value", "Climate 1901-2025", "About, data and caveats"])
EVIDENCE_URL = "https://github.com/Taab-cyber/heat-rain-harvest/blob/main/docs/EVIDENCE_production_value.md"


def crore(rs: float) -> str:
    """Rupees in crore (1 crore = 10 million), e.g. 2,349 crore; lakh below one crore."""
    return f"₹{rs / 1e7:,.0f} crore" if rs >= 1e7 else f"₹{rs / 1e5:,.1f} lakh"


def people(n: float) -> str:
    return f"{n / 1e7:,.1f} crore" if n >= 1e7 else f"{n / 1e5:,.1f} lakh"
WX_LABEL = {"tmin_mean": "Night temperature", "tmax_mean": "Day temperature", "feb_tmax_mean": "February day temp.",
            "mar_tmax_mean": "March day temp.", "mar_hot_days_35": "March days >= 35 °C", "rain_total": "Season rain",
            "rain_nov_jan": "Nov-Jan rain", "prev_monsoon_rain": "Previous monsoon rain", "rain_jun_sep": "Jun-Sep rain",
            "longest_dry_spell": "Longest dry spell", "rainy_days": "Rainy days", "hot_days_35": "Days >= 35 °C"}

st.markdown("""<style>
.card {border-radius: 12px; padding: 16px 16px 12px; background: rgba(127,127,127,.09); height: 100%;
       border-top: 4px solid var(--accent, #999);}
.card .big {font-size: clamp(1.15rem, 2.1vw, 2.1rem); font-weight: 750; line-height: 1.1; margin: 2px 0 8px;
            white-space: nowrap;}
.card .txt {font-size: .98rem; line-height: 1.4;}
.pill {display:inline-block; padding: 3px 12px; border-radius: 999px; font-weight: 700; font-size: 1rem; color: #fff;}
.lead {font-size: 1.08rem; line-height: 1.55; max-width: 62rem;}
.adv {border-left: 4px solid #3b6fb6; padding: 10px 14px; background: rgba(59,111,182,.07); border-radius: 6px;}
.adv li {margin-bottom: 8px;} .adv .src {font-size: .85rem; opacity: .85;}
</style>""", unsafe_allow_html=True)


def card(col, big, text, color="#999"):
    col.markdown(f'<div class="card" style="--accent:{color}"><div class="big" style="color:{color}">{big}</div>'
                 f'<div class="txt">{text}</div></div>', unsafe_allow_html=True)


pct = lambda v: f"{v * 100:+.0f}%".replace("-", "−")


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


RISK_STYLE = {"low": ("LOW", GREEN), "medium": ("MEDIUM", AMBER), "high": ("HIGH", RED), "na": ("NOT ENOUGH DATA", "#888")}

# ------------------------------------------------------------------ start here
with tab_home:
    st.title(t("title"))
    st.markdown(f'<p class="lead">{t("lead")}</p>', unsafe_allow_html=True)
    warming = float(T["clim_trends"].query("period == 'annual' and variable == 'tmean'").sen_per_decade.iloc[0] * 7.4) \
        if T["clim_trends"] is not None else 0.56
    w2, r2 = national_change("Wheat", warm), national_change("Rice (monsoon)", warm)
    c1, c2, c3, c4, c5 = st.columns(5)
    card(c1, f"+{warming:.1f} °C", t("c1"), RED)
    if T["clim_winters"] is not None:
        wn = T["clim_winters"]
        old, new = wn[wn.season.between(1952, 1981)].cool_days.mean(), wn[wn.season.between(1996, 2025)].cool_days.mean()
        card(c2, t("c2_big", n=round(old - new)), t("c2", old=round(old), new=round(new)), BLUE)
    ne = night_effect("Wheat")
    if ne:
        card(c3, pct(ne[0]), t("c3", lo=pct(ne[1]), hi=pct(ne[2])), RED)
    if T["loss_bins"] is not None:
        b = T["loss_bins"].query("crop == 'Rice (monsoon)' and region == 'Central' and variable == 'rain_jun_sep'")
        low, normal = b[b.bin == "low (z<-1)"].loss_rate.iloc[0], b[b.bin == "normal"].loss_rate.iloc[0]
        card(c4, f"{low * 100:.0f}%", t("c4", normal=f"{normal * 100:.0f}%"), AMBER)
    rng_w = scenario_range("Wheat", warm)
    card(c5, pct(w2), t("c5", warm=f"{warm:g}", lo=pct(rng_w[0]) if rng_w else "n/a",
                        hi=pct(rng_w[1]) if rng_w else "n/a", rice=pct(r2)), RED)

    st.markdown(f"### {t('charts_h')}")
    left, right = st.columns(2)
    if T["clim_annual"] is not None:
        ca = T["clim_annual"]
        sm = ca.tmean_anom_vs_1951_80.rolling(10, center=True, min_periods=5).mean()
        f = go.Figure()
        f.add_bar(x=ca.year, y=ca.tmean_anom_vs_1951_80, marker_color=np.where(ca.tmean_anom_vs_1951_80 > 0, RED, BLUE),
                  opacity=.55)
        f.add_scatter(x=ca.year, y=sm, line=dict(color=ORANGE, width=4))
        f.update_layout(title=f"{t('ch1_t')}<br><sup>{t('ch1_s')}</sup>", height=360, yaxis_title=t("ch1_y"),
                        showlegend=False, margin=dict(t=70, b=10))
        left.plotly_chart(f, width="stretch")
    if T["clim_winters"] is not None:
        f = go.Figure()
        f.add_scatter(x=wn.season, y=wn.cool_days.rolling(10, center=True, min_periods=5).mean(), fill="tozeroy",
                      line=dict(color=BLUE, width=3))
        f.update_layout(title=f"{t('ch2_t')}<br><sup>{t('ch2_s')}</sup>", height=360, yaxis_title=t("ch2_y"),
                        yaxis_range=[60, 100], margin=dict(t=70, b=10))
        right.plotly_chart(f, width="stretch")

    left, right = st.columns(2)
    cw = t("crop_w_wheat") if crop == "Wheat" else t("crop_w_rice")
    if T["loss_by_year"] is not None:
        ly = T["loss_by_year"][T["loss_by_year"].crop == crop].copy()
        ly["season"] = ly.year.map(season)
        why = ({2014: t("why_2014"), 2015: t("why_2015"), 2005: t("why_2005")} if crop == "Wheat"
               else {2002: t("why_rice"), 2015: t("why_rice"), 2009: t("why_rice")})
        f = go.Figure()
        f.add_bar(x=ly.season, y=ly.share_area_in_loss * 100, marker_color=np.where(ly.share_area_in_loss > .3, RED, "#b3b3b3"))
        for yr, txt in why.items():
            r = ly[ly.year == yr]
            if len(r):
                f.add_annotation(x=r.season.iloc[0], y=float(r.share_area_in_loss.iloc[0] * 100), text=txt,
                                 showarrow=True, arrowhead=0, ay=-30, font=dict(size=12))
        f.update_layout(title=f"{t('ch3_t', crop=cw)}<br><sup>{t('ch3_s', crop=cw)}</sup>", height=380,
                        xaxis_type="category", xaxis_tickangle=-60, yaxis_title=t("ch3_y"), margin=dict(t=70, b=10))
        left.plotly_chart(f, width="stretch")
    sc = pd.DataFrame({"crop": [t("x_wheat"), t("x_rice")], "change": [w2 * 100, r2 * 100]})
    f = px.bar(sc, x="crop", y="change", text=sc.change.map(lambda v: f"{v:+.0f}%"), color_discrete_sequence=[RED])
    f.update_traces(textposition="outside", textfont_size=18)
    f.update_layout(title=f"{t('ch4_t', warm=f'+{warm:g}')}<br><sup>{t('ch4_s')}</sup>", height=380,
                    yaxis_title=t("ch4_y"), yaxis_range=[min(-25, sc.change.min() * 1.4), 5], xaxis_title="",
                    margin=dict(t=70, b=10))
    right.plotly_chart(f, width="stretch")

    st.markdown(f"### {t('findings_h')}")
    st.markdown("\n".join(f"- {t(k)}" for k in ("f1", "f2", "f3")))
    st.info(t("next"))
    st.caption(t("caveat"))


def advice_box(keys: list[str]) -> None:
    items = []
    for k in keys:
        a = ADVICE[k]
        src = " · ".join(f'<a href="{u}" target="_blank">{n}</a>' for n, u, _ in a["sources"])
        items.append(f'<li>{a.get(lang, a["en"])}<br><span class="src">{t("adv_source")}: {src}</span></li>')
    st.markdown(f'<div class="adv"><b>{t("adv_h")}</b><ul>{"".join(items)}</ul>'
                f'<span class="src"><i>{t("adv_disclaimer")}</i></span></div>', unsafe_allow_html=True)


@st.cache_data
def district_report(uid_: int, crop_: str, warm_: float, keys: tuple) -> bytes:
    from report_pdf import district_pdf
    info_ = layer_df.loc[uid_]
    y_ = y_all[y_all.unit_id == uid_].sort_values("year")
    v_ = y_.dropna(subset=["yield_rel_anom"])
    bad_ = v_[v_.yield_rel_anom < BAD]
    actions = [(ADVICE[k]["en"], "; ".join(f"{n}: {u}" for n, u, _ in ADVICE[k]["sources"])) for k in keys]
    return district_pdf(
        district=info_.d_name, state=info_.state, crop_label=crop_, crop_word=CROP_WORD,
        risk=RISK_STYLE[risk_level(len(bad_) / len(v_) if len(v_) else np.nan)][0], bad=len(bad_), n=len(v_),
        mean_yield=float(info_.mean_yield), bad_years=[(season(r.year), abs(r.yield_rel_anom) * 100) for r in bad_.itertuples()],
        heat_per_c=info_.heat_effect_per_c, warm=warm_, scenario=info_.scenario,
        national_range=scenario_range(crop_, warm_), actions=actions,
        disclaimer=tr("en", "adv_disclaimer"), y=y_)


# ------------------------------------------------------------------ my district
with tab_mine:
    info = layer_df.loc[uid]
    y = y_all[y_all.unit_id == uid].sort_values("year")
    valid = y.dropna(subset=["yield_rel_anom"])
    n, bad = len(valid), int((valid.yield_rel_anom < BAD).sum())
    share = bad / n if n else np.nan
    level_txt, lcol = RISK_STYLE[risk_level(share)]
    st.title(f"{info.d_name}, {info.state}")
    st.markdown(f'<p class="lead">{CROP_LABEL[crop]} &nbsp;·&nbsp; Risk of a bad year: '
                f'<span class="pill" style="background:{lcol}">{level_txt}</span></p>', unsafe_allow_html=True)

    cl = T["climate"][(T["climate"].crop == crop) & (T["climate"].unit_id == uid)]
    irr = float(np.clip(y.irr_share.mean(), 0, 1)) if y.irr_share.notna().any() else np.nan
    keys = advice_keys(crop, share, march_heat_percentile().get(uid) if crop == "Wheat" else None,
                       irr, drought_bad_years(valid, cl))
    advice_box(keys)
    st.write("")

    qpa = info.mean_yield * 10 / 2.471 if pd.notna(info.mean_yield) else np.nan      # t/ha -> quintals per acre
    c1, c2, c3, c4 = st.columns(4)
    card(c1, f"{bad} of {n}", "seasons were bad years (more than 10% below normal).", lcol)
    card(c2, f"{qpa:.0f} q/acre" if pd.notna(qpa) else "n/a",
         f"typical yield here ({info.mean_yield:.1f} tonnes per hectare).", GREEN)
    card(c3, f"{irr * 10:.0f} in 10" if pd.notna(irr) else "n/a", f"{CROP_WORD} fields are irrigated.", BLUE)
    if pd.notna(info.scenario):
        card(c4, pct(info.scenario), f"modelled change at +{warm:g} °C"
             + (f", about {abs(info.scenario) * qpa:.1f} quintals per acre." if pd.notna(qpa) else "."),
             RED if info.scenario < 0 else GREEN)
    else:
        card(c4, "n/a", "No warming estimate for this district.")

    dtr = T["clim_district_trends"]
    if dtr is not None and (dtr.unit_id == uid).any():
        r = dtr[dtr.unit_id == uid].iloc[0]
        nights, days = r.tmin_per_decade * 7.4, r.tmax_per_decade * 7.4
        st.markdown(f"Since 1951, nights in {info.d_name} have become **{abs(nights):.1f} °C "
                    f"{'warmer' if nights >= 0 else 'cooler'}** and days {abs(days):.1f} °C "
                    f"{'warmer' if days >= 0 else 'cooler'}.")

    # production, value and food equivalent, 2022-23 (D25): only where district figures match official totals
    if T["value_district"] is not None:
        vkey = "Wheat" if crop == "Wheat" else "Rice"
        st.markdown(f"### Production and value, 2022-23 ({'wheat' if vkey == 'Wheat' else 'rice, all seasons'})")
        vd = T["value_district"].query("unit_id == @uid and crop == @vkey")
        chk = T["value_state_check"].query("crop == @vkey")
        if vd.empty:
            st.info("No 2022-23 production record for this district.")
        elif not bool(vd.verified.iloc[0]):
            r = vd.iloc[0]
            srow = chk[chk.state == r.state]
            if len(srow):
                s = srow.iloc[0]
                st.warning(f"Not shown. For {r.state}, the district figures on the DES portal add up to "
                           f"{s.ours_mt:.2f} million tonnes, but the official state total is {s.official_mt:.2f} million "
                           f"tonnes (Agricultural Statistics at a Glance 2024), a gap of {(s.ratio - 1) * 100:+.0f}%. "
                           "We only show district figures that add up to the official total.")
            else:
                st.warning(f"Not shown: {r.reason}.")
            st.caption(f"How this check works: {EVIDENCE_URL}")
        else:
            r = vd.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            card(c1, f"{r.production_t / 1e3:,.0f} thousand t", f"{'wheat' if vkey == 'Wheat' else 'rice'} produced "
                 "(DES; this state's district figures match the official state total).", GREEN)
            card(c2, crore(r.value_rs), f"value at the Minimum Support Price (₹{r.msp_rs_q:,.0f} per quintal"
                 + (" of paddy" if vkey == "Rice" else "") + "), if all of it sold at MSP.", BLUE)
            if pd.notna(r.margin_rs_per_acre):
                card(c3, f"₹{r.margin_rs_per_acre:,.0f} per acre", "estimated margin over paid-out costs and family "
                     f"labour (CACP cost A2+FL, ₹{r.cost_a2fl_rs_q:,.0f} per quintal in {r.state}).", GREEN)
            else:
                card(c3, "n/a", f"CACP publishes no 2022-23 cost of production for {vkey.lower()} in {r.state}.")
            card(c4, people(r.people_equivalent) + " people", "is how many people's yearly "
                 f"{'wheat' if vkey == 'Wheat' else 'rice'} this equals at the national average availability per person.",
                 AMBER)
            st.caption("Upper estimates: many farmers sell below MSP, the margin leaves out land rent and interest, and the "
                       "harvest also goes to seed, feed, exports, stocks and losses. "
                       f"Sources and arithmetic: {EVIDENCE_URL}")

    st.markdown(f"### {CROP_WORD.capitalize()} yield by season")
    f = go.Figure()
    f.add_bar(x=y.year.map(season), y=y.yield_t_ha * 10 / 2.471,
              marker_color=np.where(y.yield_rel_anom < BAD, RED, GREEN), name="yield")
    f.add_scatter(x=y.year.map(season), y=y.trend_full * 10 / 2.471, line=dict(color=ORANGE, dash="dash", width=3),
                  name="usual level")
    f.update_layout(height=380, xaxis_type="category", xaxis_tickangle=-60, yaxis_title="quintals per acre",
                    legend=dict(orientation="h", y=1.1), margin=dict(t=30, b=10))
    st.plotly_chart(f, width="stretch")
    st.caption("Red: bad year (more than 10% below the usual level). Green: normal or good year. Dashed line: the usual "
               "level, which rises over time as farming improves.")

    # a plain reason for each bad year, from that season's weather compared with this district's normal
    cy = cl.set_index("year")
    if crop == "Wheat":
        rules = [("tmin_mean", 1, "winter nights were unusually warm"), ("mar_tmax_mean", 1, "March was unusually hot"),
                 ("rain_total", 1, "the season was unusually wet (rain or hail)"),
                 ("rain_total", -1, "the winter was unusually dry")]
    else:
        rules = [("rain_jun_sep", -1, "monsoon rain was well below normal"),
                 ("longest_dry_spell", 1, "there was a long dry spell during the monsoon"),
                 ("rain_jun_sep", 1, "the monsoon was unusually heavy (possible flooding)"),
                 ("tmax_mean", 1, "days were unusually hot")]
    z = {v: (cy[v] - cy[v].mean()) / cy[v].std() for v, _, _ in rules if v in cy}
    lines = []
    for _, r in valid[valid.yield_rel_anom < BAD].iterrows():
        why = [txt for v, s, txt in rules if v in z and r.year in z[v].index and pd.notna(z[v][r.year])
               and ((s > 0 and z[v][r.year] > 0.8) or (s < 0 and z[v][r.year] < -0.8))]
        reason = (", ".join(why[:-1]) + " and " + why[-1] if len(why) > 1 else why[0]) if why else \
            "the weather was close to normal, so other causes (pests, floods, seed or reporting problems) are more likely"
        lines.append(f"- **{season(r.year)}**: {abs(r.yield_rel_anom) * 100:.0f}% below the usual level; {reason}.")
    if lines:
        st.markdown("### What happened in the bad years")
        st.markdown("\n".join(lines))
        st.caption("Each season's weather is compared with this district's own normal. These are pointers, not proof.")
    else:
        st.success(f"No bad {CROP_WORD} years in {info.d_name} in this period.")

    st.download_button("Download district report (PDF)", data=district_report(uid, crop, warm, tuple(keys)),
                       file_name=f"{info.d_name.replace(' ', '_')}_{CROP_WORD}_report.pdf", mime="application/pdf")

# ------------------------------------------------------------------ map
with tab_map:
    st.markdown(f"### {CROP_LABEL[crop]}: India")
    layers = {"How often seasons were bad (more than 10% below normal, % of years)": ("risk_score", 100, "Reds", False),
              f"Modelled change at +{warm:g} °C (%)": ("scenario", 100, "RdBu", True),
              "Change in yield per 1 °C of warming (%)": ("heat_effect_per_c", 100, "RdBu", True),
              "Typical yield (tonnes per hectare)": ("mean_yield", 1, "YlGn", False)}
    if crop == "Wheat":
        layers["Risk zones (districts grouped by climate)"] = ("zone", None, None, False)
    choice = st.selectbox("Map layer", list(layers))
    st.caption({"risk_score": "Darker red: bad seasons were more frequent.",
                "scenario": "Red: yield goes down; blue: yield goes up. Darker means a larger change.",
                "heat_effect_per_c": "Red: warming lowers yield more.",
                "mean_yield": "Darker green: higher yields.",
                "zone": "Districts with a similar climate risk profile share a colour."}[layers[choice][0]]
               + " Grey: no data, or the crop is not grown. Hover over a district for its name.")
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
        st.metric(f"India, area-weighted change at +{warm:g} °C ({CROP_WORD})", f"{np.average(w.scenario, weights=area)*100:+.1f}%")
    st.caption("Scenario values are model estimates, not forecasts (see For experts, About, data and caveats).")

# ------------------------------------------------------------------ district details
with tab_d:
    info = layer_df.loc[uid]
    st.subheader(f"{info.d_name}, {info.state}: {crop}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mean yield (t/ha)", f"{info.mean_yield:.2f}" if pd.notna(info.mean_yield) else "n/a",
              help="Mean of 1997-2022 seasons in the analysis sample")
    c2.metric("Risk score", f"{info.risk_score:.0%}" if pd.notna(info.risk_score) else "n/a",
              help="Share of 1997-2017 seasons more than 10% below the district's trend")
    c3.metric("Per +1 °C", f"{info.heat_effect_per_c*100:+.1f}%" if pd.notna(info.heat_effect_per_c) else "n/a",
              help="Modelled change in yield for +1 °C uniform warming, 2018-22 seasons (two-way fixed-effects Ridge, D23)")
    c4.metric(f"At +{warm:g} °C", f"{info.scenario*100:+.1f}%" if pd.notna(info.scenario) else "n/a",
              help="Modelled yield change at the selected warming, % of trend yield")
    if crop == "Wheat" and isinstance(info.get("zone"), str):
        st.info(f"Risk zone: **{info.zone}**")

    y = y_all[y_all.unit_id == uid].sort_values("year")
    left, right = st.columns(2)
    with left:
        fig = go.Figure()
        fig.add_bar(x=y.year, y=y.yield_t_ha, name="yield", marker_color="#d9a441")
        fig.add_scatter(x=y.year, y=y.trend_full, name="trend", line=dict(color=ORANGE, dash="dash"))
        fig.update_layout(title="Yield and long-run trend (t/ha)", height=330, margin=dict(t=40, b=10))
        st.plotly_chart(fig, width="stretch")
    with right:
        c = T["climate"][(T["climate"].crop == crop) & (T["climate"].unit_id == uid)].sort_values("year")
        var = "mar_tmax_mean" if crop == "Wheat" else "rain_jun_sep"
        lab = "Mean March maximum temperature (°C)" if crop == "Wheat" else "June-September rainfall (mm)"
        if var in c and c[var].notna().any():
            fig = px.line(c, x="year", y=var, markers=True, title=lab)
            zz = np.polyfit(c.year[c[var].notna()], c[var].dropna(), 1)
            fig.add_scatter(x=c.year, y=np.polyval(zz, c.year), name="linear trend", line=dict(dash="dot"))
            fig.update_layout(height=330, margin=dict(t=40, b=10), showlegend=False)
            st.plotly_chart(fig, width="stretch")

    left, right = st.columns(2)
    with left:
        a = y.dropna(subset=["yield_rel_anom"])
        fig = px.bar(a, x="year", y=a.yield_rel_anom * 100, color=a.yield_rel_anom < BAD,
                     color_discrete_map={True: RED, False: "#8a8a8a"}, title="Yield compared with trend (%); red = bad year")
        fig.update_layout(height=300, showlegend=False, yaxis_title="%", margin=dict(t=40, b=10))
        st.plotly_chart(fig, width="stretch")
    with right:
        s = T["scenarios"][(T["scenarios"].crop == crop) & (T["scenarios"].unit_id == uid)]
        if len(s):
            fig = px.line(s, x="delta_c", y=s.delta_rel_yield * 100, markers=True, title="Modelled yield change by warming (%)")
            fig.add_vline(x=warm, line_dash="dash")
            fig.update_layout(height=300, xaxis_title="+°C", yaxis_title="% of trend", margin=dict(t=40, b=10))
            st.plotly_chart(fig, width="stretch")

    f = T["forecasts"][(T["forecasts"].crop == crop) & (T["forecasts"].unit_id == uid)]
    if len(f):
        st.markdown("**Test-year forecasts (2018-22).** The model was trained on 1997-2017 only.")
        show = f.assign(season=f.year.map(season))[["season", "actual", "trend_train", "pred_ridge"]].rename(columns={
            "actual": "actual (t/ha)", "trend_train": "trend-only forecast", "pred_ridge": "weather model (Ridge)"})
        st.dataframe(show.round(2), hide_index=True, width="stretch")
        st.caption("On unseen years the weather model is only slightly better than the trend for wheat (+1.8% skill) "
                   "and no better for rice. It did not anticipate the 2021-22 Punjab-Haryana heat losses.")

# ------------------------------------------------------------------ bad seasons
with tab_loss:
    if T["loss_by_year"] is None:
        st.info("Bad-season tables not built yet: run `python -m src.loss_patterns` then `python -m src.build_db`.")
    else:
        st.markdown(f"#### {crop}: when and where were seasons bad (more than 10% below normal)?")
        st.caption("A bad season is a district yield more than 10% below its own long-run trend. Weather is compared with "
                   "the same district's normal (z-score), so 'hot' means hot for that district. These are associations, "
                   "not causal estimates.")
        if crop == "Wheat":
            st.markdown(
                "- **Warm nights** are the most consistent signal: in 7 of 8 regions bad seasons had warmer nights than "
                "normal (Gangetic plain: 32% of warm-night seasons were bad, against 6% of cool-night seasons).\n"
                "- **A weak monsoon before sowing** comes next (6 of 8 regions), through less stored soil moisture.\n"
                "- **A hot February** matters as much as a hot March in the Gangetic plain and the hills.\n"
                "- **Too much rain also hurts.** In the irrigated north-west, bad seasons were *wet* ones (rain and hail "
                "near harvest, as in 2014-15).\n"
                "- Worst seasons: 2014-15 (unseasonal March rain), 2015-16 (warm and dry after two weak monsoons), "
                "2005-06 (very hot February), and 2021-22 in the north-west (March heatwave).")
        else:
            st.markdown(
                "- **Rain is the main factor.** When June-September rain is well below a district's normal, the share of "
                "bad seasons rises (central India 66% against 33%; east 51%; dry west 45%).\n"
                "- Bad years are also hotter by day, mostly because drought years are sunny.\n"
                "- The irrigated north-west hardly reacts (12% bad seasons, against 21-36% elsewhere).\n"
                "- Worst seasons: 2002, 2015 and 2009, the official monsoon droughts. 2008 was wet and still had bad "
                "seasons, so not every bad season is caused by weather.")
        ly = T["loss_by_year"][T["loss_by_year"].crop == crop].copy()
        ly["season"] = ly.year.map(season)
        f1 = px.bar(ly, x="season", y=ly.share_area_in_loss * 100, color="mean_anomaly_pct", color_continuous_scale="RdBu",
                    range_color=(-15, 15), labels={"y": "% of crop area in a bad season", "mean_anomaly_pct": "mean yield vs trend (%)"},
                    title="Share of India's crop area in a bad season")
        st.plotly_chart(f1.update_layout(height=330, xaxis_tickangle=-60, xaxis_type="category"), width="stretch")

        ry = T["loss_region_year"][T["loss_region_year"].crop == crop]
        hm = ry.pivot_table(index="region", columns="year", values="share_area_in_loss") * 100
        f2 = px.imshow(hm, color_continuous_scale="Reds", zmin=0, zmax=100, aspect="auto",
                       labels={"color": "% of area", "x": "season (start year)", "y": ""},
                       title="Bad seasons by region (% of the region's crop area)")
        st.plotly_chart(f2.update_layout(height=380), width="stretch")

        left, right = st.columns(2)
        wx = T["loss_weather"][T["loss_weather"].crop == crop].copy()
        wx["variable"] = wx.variable.map(WX_LABEL).fillna(wx.variable)
        hw = wx.pivot_table(index="region", columns="variable", values="z_loss_minus_normal")
        f3 = px.imshow(hw, color_continuous_scale="RdBu_r", zmin=-1, zmax=1, aspect="auto", text_auto=".1f",
                       labels={"color": "z (bad - normal)", "x": "", "y": ""},
                       title="Weather in bad seasons compared with normal seasons")
        left.plotly_chart(f3.update_layout(height=430), width="stretch")
        left.caption("Red: higher than the district's normal in bad seasons. Blue: lower. 1 = one standard deviation.")

        bn = T["loss_bins"][T["loss_bins"].crop == crop].copy()
        vopts = sorted(bn.variable.unique(), key=lambda v: list(WX_LABEL).index(v) if v in WX_LABEL else 99)
        v = right.selectbox("Share of bad seasons when this was low, normal or high", vopts,
                            format_func=lambda x: WX_LABEL.get(x, x))
        b = bn[bn.variable == v]
        f4 = px.bar(b, x="region", y=b.loss_rate * 100, color="bin", barmode="group",
                    category_orders={"bin": ["low (z<-1)", "normal", "high (z>1)"]},
                    color_discrete_map={"low (z<-1)": "#4393c3", "normal": "#bbbbbb", "high (z>1)": "#d6604d"},
                    labels={"y": "% of seasons that were bad", "region": ""})
        right.plotly_chart(f4.update_layout(height=390, xaxis_tickangle=-35), width="stretch")

        yd = y_all[(y_all.unit_id == uid)].merge(T["climate"][(T["climate"].crop == crop) & (T["climate"].unit_id == uid)],
                                                  on=["unit_id", "year"], how="left")
        cols = [c for c in (["tmin_mean", "mar_tmax_mean", "rain_total"] if crop == "Wheat"
                            else ["rain_jun_sep", "longest_dry_spell", "tmax_mean"]) if c in yd]
        for c in cols:
            yd[c] = (yd[c] - yd[c].mean()) / yd[c].std()
        lossy = yd[yd.yield_rel_anom < BAD].sort_values("year")
        st.markdown(f"#### {pick}: {len(lossy)} bad seasons out of {yd.yield_rel_anom.notna().sum()}")
        if len(lossy):
            show = lossy[["year", "yield_rel_anom"] + cols].assign(year=lossy.year.map(season),
                                                                   yield_rel_anom=lossy.yield_rel_anom * 100)
            show = show.rename(columns={"year": "season", "yield_rel_anom": "yield vs trend (%)",
                                        **{c: WX_LABEL.get(c, c) + " (z)" for c in cols}})
            st.dataframe(show.round(1), hide_index=True, width="stretch")
            st.caption("z above +1: unusually high for this district. Below -1: unusually low.")

# ------------------------------------------------------------------ production and value
with tab_value:
    if T["value_india"] is None:
        st.info("Value tables not built yet: run `python -m src.official_stats`, `python -m src.production_value`, "
                "then `python -m src.build_db`.")
    else:
        st.markdown("#### India, 2022-23 (official totals)")
        vi = T["value_india"].set_index("crop")
        rows = []
        for c in ("Wheat", "Rice"):
            r = vi.loc[c]
            rows.append({"crop": c, "production (million t)": r.production_t / 1e6, "MSP (₹/quintal)": r.msp_rs_q,
                         "value at MSP (₹ crore)": r.value_rs / 1e7, "cost A2+FL (₹/quintal)": r.cost_a2fl_rs_q,
                         "margin at MSP (₹ crore)": r.margin_rs / 1e7,
                         "people-equivalent (crore)": r.people_equivalent / 1e7,
                         "availability (kg/person/yr)": r.availability_kg_per_person})
        st.dataframe(pd.DataFrame(rows).round(2), hide_index=True, width="stretch")
        st.caption("Rice is valued as paddy: 1 tonne of rice = 1/0.67 tonnes of paddy (out-turn ratio, CAG Report 31 of "
                   "2015). The people-equivalent is larger than India's population because gross production also covers "
                   "exports, government stocks, seed, feed and losses; it measures size, not who is fed.")

        st.markdown("#### Do the district figures add up to the official state totals? (2022-23)")
        ck = T["value_state_check"].copy()
        ck["gap %"] = (ck.ratio - 1) * 100
        st.dataframe(ck[["crop", "state", "official_mt", "ours_mt", "gap %", "verified"]].round(2), hide_index=True,
                     width="stretch")
        st.caption("Official: Agricultural Statistics at a Glance 2024, Tables 2.4(b) and 2.5(b). Ours: sum of district "
                   "figures from the DES Area-Production-Yield portal. A state passes within ±5%. District production, "
                   "value and people figures are shown only for districts in states that pass.")

        s = T["value_series"]
        f = px.line(s, x="year", y=(s.ratio - 1) * 100, color="crop", markers=True,
                    labels={"y": "district sum vs official all-India (%)", "year": "season (start year)"},
                    title="When did the district figures start drifting from the official totals?")
        f.add_hline(y=5, line_dash="dot").add_hline(y=-5, line_dash="dot")
        st.plotly_chart(f.update_layout(height=340), width="stretch")
        st.markdown(f"Full method, every source page and every check: [evidence document]({EVIDENCE_URL}).")

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
        for v, col in (("tmax", "#d62728"), ("tmin", "#1f77b4"), ("tmean", "#7f7f7f")):
            s = ca[f"{v}_anom_vs_1951_80"]
            f.add_scatter(x=ca.year, y=s, name=v, line=dict(color=col, width=1), opacity=.45)
            f.add_scatter(x=ca.year, y=s.rolling(10, center=True).mean(), name=f"{v} 10-yr mean", line=dict(color=col, width=3))
        f.update_layout(title="All-India temperature compared with 1951-1980 (°C)", height=380, margin=dict(t=40, b=10))
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
                st.write(f"**{pick}**: day-time {r.tmax_per_decade.iloc[0]:+.2f} °C per decade, "
                         f"night-time {r.tmin_per_decade.iloc[0]:+.2f} °C per decade (1951-2025).")

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
            st.markdown("#### What the warming so far means for yields")
            st.dataframe(T["harvest_link"].round(3), hide_index=True, width="stretch")
            st.caption("Season night warming (1996-2025 against 1951-80) multiplied by the night-temperature coefficient. "
                       "A rough estimate: it assumes today's sensitivity also held in the past and ignores adaptation, "
                       "new varieties and CO2.")

# ------------------------------------------------------------------ about, data and caveats
with tab_about:
    meta = dict(zip(T["meta"].key, T["meta"].value))
    st.markdown("### What this atlas shows")
    st.markdown("District wheat and monsoon-rice yields (1997-98 to 2022-23) on fixed Census 2011 districts, their link "
                "to heat and rain, a risk score based on past bad years, and modelled yield changes under uniform warming.")
    st.markdown("### Sources"); st.write(meta["sources"])
    st.markdown("### Caveats"); st.write(meta["caveats"])
    st.markdown("""
- **Risk score**: share of 1997-2017 seasons more than 10% below the district's trend. For wheat districts with too few
  years, a value carried over from climatically similar districts is shown (balanced accuracy 0.64 in validation).
- **Two heat numbers, two models.** The night-temperature number on Start here comes from a simple model (yield against
  night temperature and rain, with district and year effects). The warming scenarios use the full model (all heat and
  rain measures, Ridge regression with district and year effects) and warm every day and night. They answer different
  questions, so the numbers differ.
- **Uncertainty**: intervals are 95% bootstrap ranges. We resampled by district, by state and by year and report the
  widest, because neighbouring districts share weather and all districts share each year's national conditions.
""" + "".join(
        f"- {c}: {r.estimate*100:+.1f}% at +{r.delta_c:g} °C (95% range {r.lo*100:+.1f} to {r.hi*100:+.1f}, "
        f"resampled by {r.ci_used})\n"
        for c, rr in ([] if T["scenario_ci"] is None else T["scenario_ci"].query("group == 'all'").groupby("crop"))
        for r in rr.itertuples()) + """
- **Irrigation**: less-irrigated districts show larger losses, but most of them are hill districts, so irrigation and
  location are mixed up.
- Built: """ + meta["built"])

    st.markdown("### Download the data")
    st.markdown("""
**District summary** (one row per district and crop):
`unit_id` Census 2011 district code · `district`, `state` · `crop` (Wheat or Rice (monsoon), i.e. kharif, autumn and
winter rice) · `seasons` number of seasons with a yield · `mean_yield_t_ha` mean yield in tonnes per hectare ·
`risk_score_pct` share of 1997-2017 seasons more than 10% below the district's trend, in % · `risk_source` observed, or
propagated from similar districts (wheat only) · `heat_effect_pct_per_1C` modelled change in yield for every 1 °C of
uniform warming, in % · `change_pct_at_plus_1C`, `change_pct_at_plus_2C` modelled change at +1 °C and +2 °C, in %.

**District-year panel** (selected crop): one row per district and season with `yield_t_ha`, `area_ha`, `trend_full`
(long-run trend), `yield_rel_anom` (yield against trend, as a fraction), `irr_share` (irrigated share), `bad_year`, and
that season's weather: temperatures in °C, `gdd`/`edd` growing and extreme degree days, rain in mm, dry spells and hot
days in days.

**Sources**: crop yields from the Directorate of Economics and Statistics (Ministry of Agriculture and Farmers Welfare);
irrigation from DES Land Use Statistics; weather from India Meteorological Department gridded data (Pai et al. 2014;
Srivastava et al. 2009). **Licence**: district boundaries come from SHRUG Open Polygons (Development Data Lab),
CC BY-NC-SA 4.0, so derived maps are for non-commercial use with attribution. The full raw and cleaned datasets are on
the project's GitHub release page.

**How to cite**: Mehtaab and Pravansh (2026), *Heat, Rain & Harvest: district climate risk for wheat and rice in India*,
MCA project, Thapar Institute of Engineering and Technology. https://github.com/Taab-cyber/heat-rain-harvest
""")
    d1, d2 = st.columns(2)
    d1.download_button("District summary (CSV)", data=summary_csv(), file_name="district_summary.csv", mime="text/csv")
    d2.download_button(f"District-year panel, {crop} (CSV)", data=panel_csv(crop),
                       file_name=f"district_year_panel_{CROP_WORD}.csv", mime="text/csv")
