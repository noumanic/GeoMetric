"""
part2_choropleth.py
===================
Part 2 – Choropleth Map and Its Pitfalls

Creates two choropleths of CO₂ per capita using different
classification schemes (quantiles vs natural breaks) and
critiques their limitations.

Produces:
  - map_quantiles.png
  - map_natural_breaks.png
  - classification_comparison.csv
  - part2_critique.txt

Usage:
    python scripts/parts/part2_choropleth.py
"""

import sys
import warnings

warnings.filterwarnings("ignore")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import geopandas as gpd
import pandas as pd
import numpy as np
import mapclassify as mc

from scripts.utils.config import PATHS, STYLE, PROJECTION_LABELS
from scripts.utils.map_utils import save_figure, add_map_annotations, reproject_gdf

VARIABLE = "co2_per_capita"
VAR_LABEL = "CO₂ Emissions per Capita (tonnes)"
PROJ_KEY = "albers_equal_area"
N_CLASSES = 5
YEAR = 2020


def load_data() -> gpd.GeoDataFrame:
    """
    Load the master processed global dataset for choropleth mapping.

    Returns:
        gpd.GeoDataFrame: Geospatial database containing 2020 emissions metrics.
    """
    return gpd.read_file(PATHS["processed"] / "master_world.gpkg")


def plot_choropleth(
    gdf: gpd.GeoDataFrame,
    scheme: str,
    scheme_label: str,
    filename: str,
):
    """
    Generate and save a single choropleth map using a specified MapClassify scheme.

    Args:
        gdf (gpd.GeoDataFrame): Master spatial database.
        scheme (str): The pysal classification scheme name (e.g., 'quantiles', 'natural_breaks').
        scheme_label (str): Human-readable label for the scheme in the plot title.
        filename (str): Output physical filename for the map graphic.
    """
    gdf_proj = reproject_gdf(gdf.copy(), PROJ_KEY)

    fig, ax = plt.subplots(1, 1, figsize=STYLE["fig_size_world"])
    fig.patch.set_facecolor("white")
    ax.set_facecolor(STYLE["ocean_color"])

    # No-data countries
    gdf_proj[gdf_proj[VARIABLE].isna()].plot(
        ax=ax,
        color=STYLE["missing_data_color"],
        linewidth=0.3,
        edgecolor=STYLE["boundary_color"],
    )

    # Choropleth
    gdf_proj.dropna(subset=[VARIABLE]).plot(
        column=VARIABLE,
        ax=ax,
        scheme=scheme,
        k=N_CLASSES,
        cmap=STYLE["sequential_palette"],
        legend=True,
        legend_kwds={
            "title": VAR_LABEL,
            "fontsize": STYLE["legend_fontsize"],
            "loc": "lower left",
            "framealpha": 0.85,
            "fmt": "{:.1f}",
        },
        linewidth=STYLE["boundary_linewidth"],
        edgecolor=STYLE["boundary_color"],
        missing_kwds={"color": STYLE["missing_data_color"], "label": "No data"},
    )

    ax.set_axis_off()
    add_map_annotations(
        ax,
        title=f"CO₂ Emissions per Capita, {YEAR}  [{scheme_label}]",
        subtitle="Normalised by population — equal area projection",
        source="Our World in Data (OWID), 2020",
        projection_name=PROJ_KEY,
        year=YEAR,
    )

    save_figure(fig, PATHS["fig_part2"] / filename)
    plt.close(fig)


def save_classification_comparison(gdf: gpd.GeoDataFrame):
    """
    Build and save a statistical table comparing classification bin thresholds.

    Calculates Quantiles, Natural Breaks, Equal Interval, and Jenks Caspall 
    boundaries, appending statistical variance metrics (ADCM, GVF).

    Args:
        gdf (gpd.GeoDataFrame): Input spatial database.

    Returns:
        pd.DataFrame: A formatted pandas DataFrame containing the statistical comparison.
    """
    data = gdf[VARIABLE].dropna()

    schemes = {
        "Quantiles": mc.Quantiles(data, k=N_CLASSES),
        "Natural Breaks": mc.NaturalBreaks(data, k=N_CLASSES),
        "Equal Interval": mc.EqualInterval(data, k=N_CLASSES),
        "Jenks Caspall": mc.JenksCaspall(data, k=N_CLASSES),
    }

    rows = []
    for name, classifier in schemes.items():
        bins = [round(b, 2) for b in classifier.bins]
        rows.append(
            {
                "Method": name,
                "Bin boundaries": " | ".join(map(str, bins)),
                "ADCM": round(
                    classifier.adcm, 3
                ),  # absolute deviation around class means
                "GVF": (
                    round(
                        1 - classifier.adcm / mc.MaximumBreaks(data, k=N_CLASSES).adcm,
                        3,
                    )
                    if name != "Equal Interval"
                    else "—"
                ),
            }
        )

    df = pd.DataFrame(rows)
    out = PATHS["fig_part2"] / "classification_comparison.csv"
    df.to_csv(out, index=False)
    print(f"   Classification comparison saved: {out.name}")
    print(df.to_string(index=False))
    return df


CRITIQUE = """
PART 2 – CHOROPLETH CRITIQUE
==============================

WHY RATIO / RATE DATA MUST BE USED INSTEAD OF RAW COUNTS
---------------------------------------------------------
A choropleth encodes a variable as a fill colour covering the entire area of
a region. If raw counts (e.g. total tonnes of CO₂) are mapped, larger countries
will always appear darker simply because they contain more people, industry, and
land — not because they are more intensive emitters per capita. China's total
emissions dwarf Luxembourg's, but Luxembourg's per-capita emissions exceed many
industrialised countries. Mapping raw counts would systematically mislead the
reader. Normalisation by population (producing per-capita rates) or area
(producing density values) is therefore mandatory for choropleth maps.

HOW REGION SIZE AFFECTS INTERPRETATION
---------------------------------------
Even with normalised data, large low-population-density regions (Russia, Canada,
Australia, the Sahara states) dominate the visual field simply because of their
physical size. The reader's eye is drawn to large coloured polygons, causing
visual over-weighting of large-but-sparse regions and under-weighting of small
but populous or intensive regions (the Netherlands, South Korea, Singapore).
This is the "large area bias" inherent to standard geographic choropleths and
motivates the use of cartograms (Part 6).

CLASSIFICATION METHOD EFFECTS
-------------------------------
Quantiles: Forces equal numbers of countries into each bin. Maximises colour
contrast and readability but can place countries with very different values into
the same class, or split a natural cluster across classes.

Natural Breaks (Jenks): Minimises within-class variance. Bins reflect natural
data clusters, making statistical sense — but bin boundaries shift with every
new dataset, making cross-map comparison harder.

Equal Interval: Divides the data range into equal-width bins. Intuitive and
comparable across years, but highly sensitive to outliers: if Qatar emits 30
t/capita while most countries emit 1–5, the top bin spans a huge range that
captures only a handful of outliers.

WHEN CHOROPLETHS MISLEAD
--------------------------
1. Raw count data mapped directly (see above).
2. Highly skewed distributions where most countries cluster in one bin.
3. Comparing regions of radically different geographic sizes.
4. Categorical data (e.g. political party) mapped with sequential colour ramps
   implying order or magnitude where none exists.
5. Missing data countries coloured with a colour from the main ramp rather
   than a distinct neutral grey.
"""


def run():
    print("=" * 60)
    print("  Part 2 — Choropleth Map")
    print("=" * 60)
    PATHS["fig_part2"].mkdir(parents=True, exist_ok=True)

    gdf = load_data()

    print("\n[1/2] Quantiles choropleth...")
    plot_choropleth(gdf, "Quantiles", "Quantiles", "map_quantiles.png")

    print("\n[2/2] Natural Breaks choropleth...")
    plot_choropleth(
        gdf, "NaturalBreaks", "Natural Breaks (Jenks)", "map_natural_breaks.png"
    )

    print("\n[3/3] Saving classification comparison...")
    save_classification_comparison(gdf)

    out = PATHS["fig_part2"] / "part2_critique.txt"
    out.write_text(CRITIQUE.strip(), encoding="utf-8")
    print(f"   Critique saved: {out.name}")

    print("\n Part 2 complete.")


if __name__ == "__main__":
    run()
