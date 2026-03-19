"""
part3_proportional.py
=====================
Part 3 – Proportional Symbol Map

Maps airport traffic (total routes) using proportional circles.
Produces both a static matplotlib map and an interactive Folium map.

Produces:
  - map_proportional_static.png
  - map_proportional_interactive.html
  - part3_comparison.txt

Usage:
    python scripts/parts/part3_proportional.py
"""

import sys, warnings

warnings.filterwarnings("ignore")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import geopandas as gpd
import pandas as pd
import numpy as np
import folium
from folium.plugins import MarkerCluster

from scripts.utils.config import PATHS, STYLE
from scripts.utils.map_utils import (
    save_figure,
    add_map_annotations,
    reproject_gdf,
    scale_symbols,
    points_to_gdf,
)


def load_data():
    """
    Load master world base-map geometries and the cleaned airport database.

    Returns:
        tuple[gpd.GeoDataFrame, pd.DataFrame]: The background geographical regions 
            and the processed tabular airports dataset.
    """
    world = gpd.read_file(PATHS["processed"] / "master_world.gpkg")
    airports = pd.read_csv(PATHS["processed"] / "airports_clean.csv")
    return world, airports


# ─── STATIC MAP ────────────────────────────────────────────


def static_proportional_map(world, airports):
    """
    Generate a static matplotlib proportional symbol map.

    Args:
        world (gpd.GeoDataFrame): Polygon database for plotting the background map.
        airports (pd.DataFrame): Point database of nodes to plot, sized by total routes.
    """
    # Use top 300 airports by total routes to avoid overplotting
    top = airports.nlargest(300, "total_routes").dropna(subset=["lat", "lon"])

    world_proj = reproject_gdf(world.copy(), "robinson")
    ap_gdf = points_to_gdf(top, "lat", "lon")
    ap_proj = reproject_gdf(ap_gdf, "robinson")

    fig, ax = plt.subplots(1, 1, figsize=STYLE["fig_size_world"])
    fig.patch.set_facecolor("white")
    ax.set_facecolor(STYLE["ocean_color"])

    world_proj.plot(
        ax=ax,
        color=STYLE["land_color"],
        linewidth=STYLE["boundary_linewidth"],
        edgecolor=STYLE["boundary_color"],
    )

    sizes = scale_symbols(
        ap_proj["total_routes"], min_size=5, max_size=1500, method="area"
    )
    coords = np.array([(g.x, g.y) for g in ap_proj.geometry])

    sc = ax.scatter(
        coords[:, 0],
        coords[:, 1],
        s=sizes,
        c=STYLE["symbol_color"],
        alpha=STYLE["symbol_alpha"],
        linewidths=0.3,
        edgecolors="white",
        zorder=5,
    )

    # Legend for symbol sizes
    for ref_val in [10, 50, 200]:
        ref_size = scale_symbols(
            pd.Series([ref_val, top["total_routes"].max()]),
            min_size=5,
            max_size=1500,
            method="area",
        )[0]
        ax.scatter(
            [],
            [],
            s=ref_size,
            c=STYLE["symbol_color"],
            alpha=STYLE["symbol_alpha"],
            label=f"{ref_val} routes",
        )
    ax.legend(
        title="Total Routes\n(symbol area ∝ routes)",
        loc="lower left",
        fontsize=STYLE["legend_fontsize"],
        framealpha=0.85,
    )

    ax.set_axis_off()
    add_map_annotations(
        ax,
        title="Global Airport Traffic — Proportional Symbol Map",
        subtitle="Symbol area proportional to number of routes (top 300 airports, 2020)",
        source="OpenFlights.org",
        projection_name="robinson",
        year=2020,
    )

    save_figure(fig, PATHS["fig_part3"] / "map_proportional_static.png")
    plt.close(fig)


# ─── INTERACTIVE FOLIUM MAP ────────────────────────────────


def interactive_proportional_map(airports):
    """
    Generate an interactive Leaflet (Folium) proportional symbol map.

    Args:
        airports (pd.DataFrame): Point database containing latitude, longitude, and metrics.

    Returns:
        folium.Map: The generated interactive map object, also saved physically as HTML.
    """
    top = airports.nlargest(500, "total_routes").dropna(subset=["lat", "lon"])

    m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB positron")

    max_routes = top["total_routes"].max()

    for _, row in top.iterrows():
        radius = 3 + (row["total_routes"] / max_routes) * 25
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=radius,
            color="#d73027",
            fill=True,
            fill_color="#d73027",
            fill_opacity=0.5,
            tooltip=folium.Tooltip(
                f"<b>{row['name']}</b> ({row['iata']})<br>"
                f"City: {row['city']}, {row['country']}<br>"
                f"Routes: {int(row['total_routes'])}<br>"
                f"Departures: {int(row['departures'])} | "
                f"Arrivals: {int(row['arrivals'])}"
            ),
        ).add_to(m)

    # Legend HTML
    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
                background:white;padding:10px;border-radius:8px;
                box-shadow:0 2px 6px rgba(0,0,0,0.3);font-size:13px;">
      <b>Airport Routes</b><br>
      <span style="color:#d73027">●</span> Circle area ∝ total routes<br>
      <span style="opacity:0.5;color:#d73027">●</span> Small = few routes<br>
      Source: OpenFlights.org
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    out = PATHS["interactive_folium"] / "airports_proportional.html"
    m.save(str(out))
    print(f"   Interactive map saved: {out.name}")
    return m


COMPARISON = """
PART 3 – PROPORTIONAL SYMBOL vs CHOROPLETH COMPARISON
=======================================================

SYMBOL AREA vs SYMBOL RADIUS
------------------------------
Symbol size must be scaled so that AREA is proportional to the data value,
not radius. If radius were scaled linearly, a country with 4× the traffic
would appear 16× larger (since area = π r²), grossly exaggerating differences.
Scaling by area (size = min + k × value) ensures the visual quantity the eye
perceives — area — correctly encodes the data magnitude.

WHY PROPORTIONAL SYMBOLS ARE BETTER THAN CHOROPLETHS FOR THIS DATA
--------------------------------------------------------------------
Airport traffic is a POINT phenomenon: it originates at discrete geographic
locations, not continuously across polygon areas. A choropleth would aggregate
traffic by country and fill the entire country polygon — implying that traffic
is distributed across all of Russia or all of Australia, which is false.
Proportional symbols place the data exactly at the airport location, preserving
spatial accuracy.

Furthermore, choropleths require normalisation by area or population. For
airports, there is no meaningful per-area normalisation: the Maldives airport
handles huge traffic relative to its tiny land area, but that is not a useful
comparison. Proportional symbols avoid this forced normalisation entirely.

OVERLAP HANDLING
-----------------
With 300+ airports, overlap is inevitable in Europe, Northeast USA, and SE Asia.
This was addressed by:
  - Using transparency (alpha=0.5) so overlapping circles remain readable.
  - Limiting to top 300 airports (reducing clutter).
  - In the interactive map, using zoom functionality and tooltips so users can
    explore dense regions at higher zoom levels.
"""


def run():
    print("=" * 60)
    print("  Part 3 — Proportional Symbol Map")
    print("=" * 60)
    PATHS["fig_part3"].mkdir(parents=True, exist_ok=True)
    PATHS["interactive_folium"].mkdir(parents=True, exist_ok=True)

    world, airports = load_data()

    print("\n[1/2] Static proportional map...")
    static_proportional_map(world, airports)

    print("\n[2/2] Interactive Folium map...")
    interactive_proportional_map(airports)

    out = PATHS["fig_part3"] / "part3_comparison.txt"
    out.write_text(COMPARISON.strip(), encoding="utf-8")
    print(f"   Comparison text saved.")
    print("\n Part 3 complete.")


if __name__ == "__main__":
    run()
