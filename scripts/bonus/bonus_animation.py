"""
bonus_animation.py
==================
BONUS – Animated Temporal Flow Map

Animates CO₂ emissions per capita change over time (1990–2020)
using Plotly animated choropleth.

Produces:
  - outputs/interactive/animations/co2_animation.html

Usage:
    python scripts/bonus/bonus_animation.py
"""

import sys, warnings

warnings.filterwarnings("ignore")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import geopandas as gpd
import plotly.express as px

from scripts.utils.config import PATHS


def run():
    """
    Execute the Plotly animated temporal choropleth generation.
    
    Reads historical CO2 data from 1990 to 2020 and builds an interactive HTML
    animation of emissions per capita.
    """
    print("=" * 60)
    print("  BONUS — Animated Temporal Choropleth")
    print("=" * 60)

    # Load full emissions time series (all years)
    emiss_full = pd.read_csv(
        PATHS["raw_emissions"] / "owid-co2-data.csv", low_memory=False
    )

    # Filter years and clean
    years = list(range(1990, 2021, 5))  # 1990, 1995, 2000, ... 2020
    df = emiss_full[
        emiss_full["year"].isin(years)
        & emiss_full["iso_code"].notna()
        & ~emiss_full["iso_code"].str.startswith("OWID")
    ][["iso_code", "country", "year", "co2_per_capita", "co2", "population"]].copy()

    df = df.dropna(subset=["co2_per_capita"])
    df["year"] = df["year"].astype(str)

    PATHS["interactive_anim"].mkdir(parents=True, exist_ok=True)

    fig = px.choropleth(
        df,
        locations="iso_code",
        color="co2_per_capita",
        color_continuous_scale="YlOrRd",
        range_color=[0, 20],
        animation_frame="year",
        hover_name="country",
        hover_data={
            "iso_code": False,
            "co2_per_capita": ":.2f",
            "co2": ":.1f",
            "population": ":,.0f",
        },
        title="CO₂ Emissions per Capita — Animated 1990→2020",
        labels={"co2_per_capita": "CO₂ per capita (t)"},
        projection="natural earth",
    )
    fig.update_geos(
        showcoastlines=True,
        coastlinecolor="white",
        showland=True,
        landcolor="#f5f5f0",
        showocean=True,
        oceancolor="#cfe2f3",
    )
    fig.update_layout(
        height=550,
        margin={"r": 0, "t": 50, "l": 0, "b": 0},
        paper_bgcolor="white",
        sliders=[{"currentvalue": {"prefix": "Year: "}}],
    )

    out = PATHS["interactive_anim"] / "co2_animation.html"
    fig.write_html(str(out), include_plotlyjs="cdn")
    print(f"   Animation saved: {out}")
    print("     Open in browser to play the animation.")


if __name__ == "__main__":
    run()
