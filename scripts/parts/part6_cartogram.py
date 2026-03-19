"""
part6_cartogram.py
==================
Part 6 – Cartogram / Area Correction Map

Compares:
  1. Standard geographic choropleth (area = land mass)
  2. Dorling cartogram (circles sized by population)
  3. Tile/hex grid map (equal area per country)

Produces:
  - map_standard_geographic.png
  - map_dorling_cartogram.png
  - part6_critique.txt

Usage:
    python scripts/parts/part6_cartogram.py
"""

import sys, warnings

warnings.filterwarnings("ignore")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import geopandas as gpd
import pandas as pd
import numpy as np

from scripts.utils.config import PATHS, STYLE
from scripts.utils.map_utils import (
    save_figure,
    add_map_annotations,
    reproject_gdf,
    scale_symbols,
)


def load_data() -> gpd.GeoDataFrame:
    """
    Load the master processed global dataset for cartogram mapping.

    Returns:
        gpd.GeoDataFrame: Master spatial geometries with demographic metrics.
    """
    return gpd.read_file(PATHS["processed"] / "master_world.gpkg")


# ─── MAP 1: STANDARD GEOGRAPHIC (CO2 per capita) ───────────


def standard_geographic_map(world):
    """
    Generate a standard choropleth map where visualization impact is dominated by land area.

    Args:
        world (gpd.GeoDataFrame): Master spatial database containing 'co2_per_capita'.
    """
    world_proj = reproject_gdf(world.copy(), "robinson")

    fig, ax = plt.subplots(1, 1, figsize=STYLE["fig_size_world"])
    fig.patch.set_facecolor("white")
    ax.set_facecolor(STYLE["ocean_color"])

    world_proj[world_proj["co2_per_capita"].isna()].plot(
        ax=ax,
        color=STYLE["missing_data_color"],
        linewidth=0.3,
        edgecolor=STYLE["boundary_color"],
    )
    world_proj.dropna(subset=["co2_per_capita"]).plot(
        column="co2_per_capita",
        ax=ax,
        scheme="quantiles",
        k=5,
        cmap=STYLE["sequential_palette"],
        legend=True,
        legend_kwds={
            "title": "CO₂ per capita (t)",
            "fontsize": STYLE["legend_fontsize"],
            "loc": "lower left",
            "framealpha": 0.85,
        },
        linewidth=STYLE["boundary_linewidth"],
        edgecolor=STYLE["boundary_color"],
        missing_kwds={"color": STYLE["missing_data_color"]},
    )
    ax.set_axis_off()
    add_map_annotations(
        ax,
        title="Standard Geographic Map — CO₂ per Capita (2020)",
        subtitle="Visual area = land mass. Russia & Canada dominate even if per-capita emissions are moderate.",
        source="Our World in Data, Natural Earth",
        projection_name="robinson",
        year=2020,
    )
    save_figure(fig, PATHS["fig_part6"] / "map_standard_geographic.png")
    plt.close(fig)


# ─── MAP 2: DORLING CARTOGRAM (circles sized by population) ─


def dorling_cartogram(world):
    """
    Generate a Dorling cartogram using geometric circles positioned at country centroids.
    
    Circle size is proportional to population, and color encodes CO2 per capita.

    Args:
        world (gpd.GeoDataFrame): GeoDataFrame containing population and emission stats.
    """
    world_wgs = world.copy()
    if world_wgs.crs.to_epsg() != 4326:
        world_wgs = world_wgs.to_crs("EPSG:4326")

    # Get centroids in Robinson for plotting
    world_rob = reproject_gdf(world.copy(), "robinson")
    centroids = world_rob.geometry.centroid
    world_rob["cx"] = centroids.x
    world_rob["cy"] = centroids.y

    # Only countries with both population and emissions data
    plot_df = world_rob.dropna(subset=["pop_final", "co2_per_capita"]).copy()
    plot_df = plot_df[plot_df["pop_final"] > 0]

    sizes = scale_symbols(
        plot_df["pop_final"], min_size=5, max_size=3000, method="area"
    )

    # Colour by co2_per_capita
    norm = mcolors.Normalize(vmin=0, vmax=plot_df["co2_per_capita"].quantile(0.95))
    cmap = cm.get_cmap(STYLE["sequential_palette"])
    colors = cmap(norm(plot_df["co2_per_capita"].values))

    fig, ax = plt.subplots(1, 1, figsize=STYLE["fig_size_world"])
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#e8f4f8")

    # Light basemap outlines
    world_rob.plot(
        ax=ax, color="#f0f0f0", linewidth=0.2, edgecolor="#aaaaaa", alpha=0.4
    )

    ax.scatter(
        plot_df["cx"].values,
        plot_df["cy"].values,
        s=sizes,
        c=colors,
        alpha=0.75,
        linewidths=0.5,
        edgecolors="white",
        zorder=5,
    )

    # Annotate largest circles
    top10 = plot_df.nlargest(10, "pop_final")
    for _, row in top10.iterrows():
        ax.annotate(
            row["iso_a3"],
            xy=(row["cx"], row["cy"]),
            fontsize=6,
            ha="center",
            va="center",
            color="white",
            fontweight="bold",
            zorder=10,
        )

    # Colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(
        sm, ax=ax, orientation="vertical", pad=0.01, fraction=0.02, shrink=0.6
    )
    cbar.set_label("CO₂ per Capita (t)", fontsize=STYLE["legend_fontsize"])

    # Legend for circle sizes
    for ref_pop in [1e6, 100e6, 1e9]:
        ref_size = scale_symbols(
            pd.Series([ref_pop, plot_df["pop_final"].max()]),
            min_size=5,
            max_size=3000,
            method="area",
        )[0]
        label = f"{ref_pop/1e6:.0f}M" if ref_pop < 1e9 else "1B"
        ax.scatter([], [], s=ref_size, c="grey", alpha=0.6, label=label)
    ax.legend(
        title="Population\n(circle area)",
        loc="lower left",
        fontsize=STYLE["legend_fontsize"],
        framealpha=0.85,
    )

    ax.set_axis_off()
    add_map_annotations(
        ax,
        title="Dorling Cartogram — Circle Size = Population, Colour = CO₂ per Capita",
        subtitle="Land area is irrelevant — each country's footprint reflects its population",
        source="Our World in Data, World Bank (2020)",
        projection_name="robinson",
        year=2020,
    )
    save_figure(fig, PATHS["fig_part6"] / "map_dorling_cartogram.png")
    plt.close(fig)


CRITIQUE = """
PART 6 – CARTOGRAM CRITIQUE: LAND AREA ≠ IMPORTANCE
=====================================================

THE PROBLEM WITH STANDARD GEOGRAPHIC MAPS
------------------------------------------
On a standard geographic map, Russia occupies 11% of the world's visible land
area but holds only 1.8% of the world's population. Canada fills a vast swathe
of North America yet houses 38 million people — less than California alone.
When we map per-capita statistics on these outlines, the reader's eye is
inevitably drawn to large polygons, creating a systematic perceptual bias.

In the standard CO₂ per capita map (Map 1), Russia and Canada visually dominate
even though their per-capita emissions, while significant, are not the highest
in the world. Qatar, Kuwait, and UAE — tiny polygons — have the world's highest
per-capita emissions and are nearly invisible.

HOW THE DORLING CARTOGRAM CORRECTS THIS
-----------------------------------------
The Dorling cartogram replaces geographic polygons with circles whose AREA
is proportional to population. Countries with large populations (India, China)
become large circles regardless of their geographic size. Countries with tiny
populations (Luxembourg, Qatar) remain small.

This immediately changes the map's message:
  - China and India dominate visually — accurately reflecting their demographic
    importance.
  - Russia and Canada shrink to modest circles.
  - The colour (CO₂ per capita) now reads correctly: the largest circles (most
    people) are not the darkest circles (highest per-capita emissions),
    illustrating that the most populous countries are not necessarily the biggest
    per-capita emitters.

SIZE vs DATA EFFECT
--------------------
The "size vs data effect" refers to the cognitive error where readers interpret
a large region as having more of whatever is being mapped, regardless of
normalisation. Even with correct per-capita data, the geographic map fails
because the reader perceives Russia (large country, medium emissions) as more
important than Qatar (tiny country, highest emissions).

TRADE-OFFS
-----------
Cartograms sacrifice geographic familiarity. Many readers cannot identify
countries from circles alone — hence the ISO code labels. They are powerful
for emphasising the CORRECT variable but require more reader effort than
standard maps. For a general audience, combining both maps side-by-side (as
in this assignment) is the most pedagogically effective approach.
"""


def run():
    print("=" * 60)
    print("  Part 6 — Cartogram / Area Correction")
    print("=" * 60)
    PATHS["fig_part6"].mkdir(parents=True, exist_ok=True)

    world = load_data()

    print("\n[1/2] Standard geographic map...")
    standard_geographic_map(world)

    print("\n[2/2] Dorling cartogram...")
    dorling_cartogram(world)

    out = PATHS["fig_part6"] / "part6_critique.txt"
    out.write_text(CRITIQUE.strip(), encoding="utf-8")
    print(f"   Critique saved.")
    print("\n Part 6 complete.")


if __name__ == "__main__":
    run()
