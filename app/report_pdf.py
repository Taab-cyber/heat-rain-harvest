"""One-page A4 district report (D24). fpdf2 with its built-in Helvetica font, so it runs on Streamlit
Community Cloud without system fonts. English only: the built-in fonts cannot draw Hindi or Punjabi."""
from __future__ import annotations

import datetime as dt
import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from fpdf import FPDF  # noqa: E402

from helpers import BAD, latin1, season  # noqa: E402

SOURCES = ("Crop yields: Directorate of Economics and Statistics, Ministry of Agriculture and Farmers Welfare. "
           "Irrigation: DES Land Use Statistics. Weather: India Meteorological Department gridded data "
           "(Pai et al. 2014; Srivastava et al. 2009). District boundaries: Census 2011, SHRUG Open Polygons "
           "(Development Data Lab, CC BY-NC-SA 4.0).")


def yield_chart(y: pd.DataFrame, crop_word: str) -> io.BytesIO:
    """Bar chart of yield by season with the district's usual level; bad years in red."""
    y = y.sort_values("year")
    fig, ax = plt.subplots(figsize=(7.2, 2.6), dpi=150)
    colours = ["#c0392b" if a < BAD else "#2e8b57" for a in y.yield_rel_anom.fillna(0)]
    labels = [season(v) for v in y.year]
    ax.bar(labels, y.yield_t_ha, color=colours, width=0.75)
    ax.plot(labels, y.trend_full, color="#e08e0b", lw=2, ls="--", label="usual level")
    ax.set_ylabel("tonnes per hectare", fontsize=8)
    ax.set_title(f"{crop_word.capitalize()} yield by season (red = more than 10% below the usual level)", fontsize=9)
    ax.tick_params(axis="x", labelrotation=70, labelsize=6)
    ax.tick_params(axis="y", labelsize=7)
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf


def district_pdf(district: str, state: str, crop_label: str, crop_word: str, risk: str, bad: int, n: int,
                 mean_yield: float, bad_years: list[tuple[str, float]], heat_per_c: float | None, warm: float,
                 scenario: float | None, national_range: tuple[float, float] | None,
                 actions: list[tuple[str, str]], disclaimer: str, y: pd.DataFrame) -> bytes:
    """Return the PDF as bytes. actions = [(text, 'Source name: url'), ...]."""
    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(False)
    pdf.set_margins(14, 12, 14)
    pdf.add_page()
    w = pdf.w - 28

    def line(text, size=9, style="", h=4.6, color=(0, 0, 0)):
        pdf.set_font("Helvetica", style, size)
        pdf.set_text_color(*color)
        pdf.multi_cell(w, h, latin1(text), new_x="LMARGIN", new_y="NEXT")

    line("Heat, Rain & Harvest: district report", 16, "B", 8)
    line(f"{district}, {state}  |  {crop_label}  |  {dt.date.today():%d %b %Y}", 10, "", 5.5, (90, 90, 90))
    pdf.ln(2)

    line(f"Risk of a bad year: {risk.upper()}", 12, "B", 6)
    q = mean_yield * 10 / 2.471
    line(f"{bad} of {n} seasons (1997-98 to 2022-23) were bad years, with yield more than 10% below the "
         f"district's usual level. Typical yield: {mean_yield:.2f} t/ha (about {q:.0f} quintals per acre).")
    if bad_years:
        line("Bad years: " + "; ".join(f"{s} ({p:.0f}% below)" for s, p in bad_years))
    if heat_per_c is not None and pd.notna(heat_per_c):
        line(f"Modelled change in yield for every 1 °C of warming: {heat_per_c * 100:+.1f}%.")
    if scenario is not None and pd.notna(scenario):
        txt = f"Modelled change at +{warm:g} °C (every day warmer, rainfall and farming unchanged): {scenario * 100:+.1f}%."
        if national_range:
            txt += (f" For India as a whole the 95% range at this warming is {national_range[0] * 100:+.1f}% to "
                    f"{national_range[1] * 100:+.1f}%.")
        line(txt)
    pdf.ln(1.5)
    pdf.image(yield_chart(y, crop_word), x=14, w=w)
    pdf.ln(2)

    line("What can be done?", 12, "B", 6)
    for text, src in actions:
        line(f"- {text}", 9)
        line(f"  {src}", 7.5, "", 3.8, (60, 60, 140))
        pdf.ln(0.8)
    line(disclaimer, 8.5, "I", 4.4, (90, 90, 90))
    pdf.ln(2)
    line("Data and method", 10, "B", 5)
    line(SOURCES, 7.5, "", 3.8, (60, 60, 60))
    line("A bad year is a season with yield more than 10% below the district's long-run trend. Warming effects come "
         "from a regression with district and year fixed effects (see the project report); they are estimates, "
         "not forecasts. Project: github.com/Taab-cyber/heat-rain-harvest", 7.5, "", 3.8, (60, 60, 60))
    return bytes(pdf.output())
