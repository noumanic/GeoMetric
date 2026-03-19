"""
part1_projections.py
====================
Part 1 – Map Projections & Distortion Analysis

Plots the same CO2 emissions dataset in three projections:
  1. Albers Equal-Area Conic
  2. Lambert Conformal Conic
  3. Winkel Tripel

Produces:
  - outputs/figures/part1_projections/map_albers.png
  - outputs/figures/part1_projections/map_lambert.png
  - outputs/figures/part1_projections/map_winkel.png
  - outputs/figures/part1_projections/projection_comparison_table.csv
  - outputs/figures/part1_projections/part1_discussion.txt

Usage:
    python scripts/parts/part1_projections.py
"""

import sys
import warnings

warnings.filterwarnings("ignore")

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path

# Ensure project root is on sys.path
import sys as _sys

_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJECT_ROOT)

from scripts.utils.config import (
    PATHS,
    PROJECTIONS,
    STYLE,
    PROJECTION_PROPERTIES,
    PROJECTION_LABELS,
)
from scripts.utils.map_utils import (
    save_figure,
    add_map_annotations,
    reproject_gdf,
    projection_comparison_table,
)

# ============================================================
# LOAD DATA
# ============================================================


def load_data():
    """
    Load the master GeoDataFrame for Part 1 mapping.

    Returns:
        gpd.GeoDataFrame: The preprocessed master spatial database containing
            the 2020 emissions, demographic stats, and country geometries.
    """
    master = gpd.read_file(PATHS["processed"] / "master_world.gpkg")
    return master


# ============================================================
# PLOT A SINGLE PROJECTION
# ============================================================


def plot_projection(
    gdf: gpd.GeoDataFrame,
    proj_key: str,
    column: str = "co2_per_capita",
    title: str = "",
    filename: str = "",
):
    """
    Plot a global choropleth map localized to a specific map projection.

    Args:
        gdf (gpd.GeoDataFrame): Master spatial database.
        proj_key (str): The configuration key for the target coordinate projection.
        column (str, optional): Target metric to visualize. Defaults to "co2_per_capita".
        title (str, optional): The chart title header.
        filename (str, optional): Output save file denominator.

    Returns:
        Path: The path to the physically saved PNG image.
    """

    proj_string = PROJECTIONS[proj_key]
    proj_label = PROJECTION_LABELS[proj_key]

    # Reproject
    gdf_proj = reproject_gdf(gdf.copy(), proj_key)

    # Plot
    fig, ax = plt.subplots(1, 1, figsize=STYLE["fig_size_world"])
    fig.patch.set_facecolor("white")
    ax.set_facecolor(STYLE["ocean_color"])

    # Missing data countries
    missing = gdf_proj[gdf_proj[column].isna()]
    missing.plot(
        ax=ax,
        color=STYLE["missing_data_color"],
        linewidth=0.3,
        edgecolor=STYLE["boundary_color"],
    )

    # Choropleth
    gdf_proj.dropna(subset=[column]).plot(
        column=column,
        ax=ax,
        cmap=STYLE["sequential_palette"],
        scheme="quantiles",
        k=5,
        legend=True,
        legend_kwds={
            "title": "CO₂ per capita (t)",
            "fontsize": STYLE["legend_fontsize"],
            "loc": "lower left",
            "framealpha": 0.8,
        },
        linewidth=STYLE["boundary_linewidth"],
        edgecolor=STYLE["boundary_color"],
        missing_kwds={"color": STYLE["missing_data_color"]},
    )

    ax.set_axis_off()
    add_map_annotations(
        ax,
        title=title or f"CO₂ Emissions per Capita — {proj_label}",
        subtitle=f"Projection: {proj_label}",
        source="Our World in Data (2020)",
        projection_name=proj_key,
        year=2020,
    )

    # Annotation: what this projection preserves
    props = PROJECTION_PROPERTIES.get(proj_key, {})
    note = f"Preserves: {props.get('preserves','—')}  |  Distorts: {props.get('distorts','—')}"
    ax.annotate(
        note,
        xy=(0.01, -0.07),
        xycoords="axes fraction",
        fontsize=STYLE["caption_fontsize"],
        color="#333",
        bbox=dict(boxstyle="round,pad=0.3", fc="#fffbe6", ec="#cccc00", alpha=0.9),
    )

    out = PATHS["fig_part1"] / filename
    save_figure(fig, out)
    plt.close(fig)
    return out


# ============================================================
# COMPARISON TABLE
# ============================================================


def save_comparison_table():
    df = projection_comparison_table()

    # Add navigation / area / education recommendation
    recommendations = {
        "Albers Equal-Area Conic": "Thematic area comparison (choropleths)",
        "Lambert Conformal Conic": "Navigation & aeronautical charts",
        "Winkel Tripel": "General educational world maps",
    }
    df["Recommended Use"] = df["Projection"].map(recommendations)

    out = PATHS["fig_part1"] / "projection_comparison_table.csv"
    df.to_csv(out, index=False)
    print(f"   Comparison table saved: {out.name}")

    # Also print nicely
    print("\n" + "=" * 80)
    print(df.to_string(index=False))
    print("=" * 80 + "\n")
    return df


# ============================================================
# DISCUSSION TEXT
# ============================================================

DISCUSSION = """
PART 1 – PROJECTION ANALYSIS DISCUSSION
========================================

Projection is not a cosmetic choice. Every flat map of the spherical Earth
requires a transformation that inevitably introduces distortion. Depending on
the mathematical properties of the projection chosen, that distortion affects
area, shape (angles), distance, or direction — and crucially, it changes the
reader's perception of the mapped phenomenon.

1. ALBERS EQUAL-AREA CONIC
   This projection faithfully preserves the *area* of all regions. Countries
   and continents appear at their true relative size. As a result, large but
   sparsely populated regions (Russia, Canada, Australia) look large only
   because they genuinely are large — not because the projection inflates them.
   This makes it the most defensible choice for a thematic choropleth where
   visual area should correspond to real-world area. Its weakness is shape
   distortion near the edges of the mapped region.

2. LAMBERT CONFORMAL CONIC
   This projection preserves *local shape* (conformality), meaning angles and
   small shapes look correct. It is the standard for aeronautical and navigation
   charts precisely because rhumb lines (constant compass bearing) are easy to
   draw. However, it significantly exaggerates the *area* of high-latitude
   regions. On a global Lambert map, Greenland appears dramatically oversized
   relative to Africa — the opposite of their true ratio.

3. WINKEL TRIPEL
   The Winkel Tripel is a compromise projection that does not perfectly preserve
   either area or shape, but minimises overall distortion across both dimensions.
   The National Geographic Society adopted it as its standard world map in 1998
   precisely for this reason. It gives a visually balanced impression of the world
   suitable for general reference and education, even though it is technically
   inferior to equal-area projections for quantitative comparisons.

CONCLUSION
   For this assignment's choropleth maps (Parts 2 and 6), the Albers Equal-Area
   projection is the correct scientific choice. The Lambert is retained for the
   navigation scenario. The Winkel Tripel is the appropriate default for
   educational and reference maps where no single attribute dominates.
"""


def save_discussion():
    out = PATHS["fig_part1"] / "part1_discussion.txt"
    out.write_text(DISCUSSION.strip(), encoding="utf-8")
    print(f"   Discussion saved: {out.name}")


# ============================================================
# MAIN
# ============================================================


def run():
    print("=" * 60)
    print("  Part 1 — Map Projections")
    print("=" * 60)

    PATHS["fig_part1"].mkdir(parents=True, exist_ok=True)
    gdf = load_data()

    print("\n[1/3] Plotting Albers Equal-Area...")
    plot_projection(
        gdf,
        "albers_equal_area",
        title="CO₂ per Capita — Albers Equal-Area Conic",
        filename="map_albers_equal_area.png",
    )

    print("\n[2/3] Plotting Lambert Conformal Conic...")
    plot_projection(
        gdf,
        "lambert_conformal_conic",
        title="CO₂ per Capita — Lambert Conformal Conic",
        filename="map_lambert_conformal.png",
    )

    print("\n[3/3] Plotting Winkel Tripel...")
    plot_projection(
        gdf,
        "winkel_tripel",
        title="CO₂ per Capita — Winkel Tripel",
        filename="map_winkel_tripel.png",
    )

    save_comparison_table()
    save_discussion()

    print("\n Part 1 complete. Outputs in:", PATHS["fig_part1"])


if __name__ == "__main__":
    run()
