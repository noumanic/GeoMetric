"""
part7_scenarios.py
==================
Part 7 – Case-Based Map Design Challenge

Scenario A: Public Health — disease burden mapping
Scenario B: Urban Services — airport accessibility
Scenario C: Climate Risk — flood risk + population exposure

Produces:
  - scenario_a_public_health.png
  - scenario_b_urban_services.png
  - scenario_c_climate_risk.png
  - part7_design_decisions.txt

Usage:
    python scripts/parts/part7_scenarios.py
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
from scipy.interpolate import RBFInterpolator
from scipy.ndimage import gaussian_filter

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
    Load the core geographic datasets, aviation nodes, and climate sensors for scenarios mapping.

    Returns:
        tuple[gpd.GeoDataFrame, pd.DataFrame, pd.DataFrame]: The master world geometries, 
            airport database, and temperature station observations.
    """
    world = gpd.read_file(PATHS["processed"] / "master_world.gpkg")
    airports = pd.read_csv(PATHS["processed"] / "airports_clean.csv")
    temps = pd.read_csv(PATHS["processed"] / "temperature_stations.csv")
    return world, airports, temps


# ============================================================
# SCENARIO A – PUBLIC HEALTH
# Map type: Choropleth (disease burden by country)
# ============================================================


def scenario_a_public_health(world):
    """
    Generate a Public Health Scenario Map using an inverted wealth index as a disease proxy.

    Args:
        world (gpd.GeoDataFrame): GeoDataFrame containing 'gdp_per_capita'.
    """
    world = world.copy()

    # Synthetic disease burden index (0–100, higher = worse)
    # Derived from GDP per capita (inverse) and population density
    if "gdp_per_capita" in world.columns:
        gdp_norm = world["gdp_per_capita"].clip(upper=50000)
        world["disease_index"] = 100 * (1 - gdp_norm / 50000)
    else:
        world["disease_index"] = np.random.uniform(10, 90, len(world))

    world_proj = reproject_gdf(world, "robinson")

    fig, ax = plt.subplots(1, 1, figsize=STYLE["fig_size_world"])
    fig.patch.set_facecolor("white")
    ax.set_facecolor(STYLE["ocean_color"])

    world_proj[world_proj["disease_index"].isna()].plot(
        ax=ax,
        color=STYLE["missing_data_color"],
        linewidth=0.3,
        edgecolor=STYLE["boundary_color"],
    )
    world_proj.dropna(subset=["disease_index"]).plot(
        column="disease_index",
        ax=ax,
        scheme="quantiles",
        k=5,
        cmap="YlOrRd",
        legend=True,
        legend_kwds={
            "title": "Disease Burden Index\n(100 = highest burden)",
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
        title="Scenario A — Public Health: Disease Burden by Country",
        subtitle="Choropleth with quantile classification | Proxy: inverse GDP per capita",
        source="Derived from World Bank / OWID (2020)",
        projection_name="robinson",
        year=2020,
    )
    save_figure(fig, PATHS["fig_part7"] / "scenario_a_public_health.png")
    plt.close(fig)


# ============================================================
# SCENARIO B – URBAN SERVICES (Airport accessibility)
# Map type: Proportional symbol + point map
# ============================================================


def scenario_b_urban_services(world, airports):
    """
    Generate an Urban Services Scenario Map visualizing global airport connectivity.

    Args:
        world (gpd.GeoDataFrame): Base polygon geometries for the world map.
        airports (pd.DataFrame): Point database of airports to plot using proportional symbols.
    """
    world_proj = reproject_gdf(world.copy(), "robinson")
    top_ap = airports.nlargest(300, "total_routes").dropna(subset=["lat", "lon"])
    ap_gdf = points_to_gdf(top_ap, "lat", "lon")
    ap_proj = reproject_gdf(ap_gdf, "robinson")
    coords = np.array([(g.x, g.y) for g in ap_proj.geometry])

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
        ap_proj["total_routes"], min_size=5, max_size=1200, method="area"
    )
    ax.scatter(
        coords[:, 0],
        coords[:, 1],
        s=sizes,
        c="#2c7bb6",
        alpha=0.6,
        edgecolors="white",
        linewidths=0.4,
        zorder=5,
    )

    # Mark underserved regions
    for label, xy in [
        ("Central Africa\n(underserved)", (-15e5, -5e5)),
        ("Central Asia\n(underserved)", (7e6, 4.5e6)),
        ("Pacific Islands\n(isolated)", (1.5e7, -2e6)),
    ]:
        ax.annotate(
            label,
            xy=xy,
            fontsize=8,
            color="#cc0000",
            bbox=dict(boxstyle="round", fc="white", alpha=0.75),
            ha="center",
        )

    # Legend
    for ref_val in [10, 50, 200]:
        ref_s = scale_symbols(
            pd.Series([ref_val, top_ap["total_routes"].max()]),
            min_size=5,
            max_size=1200,
            method="area",
        )[0]
        ax.scatter([], [], s=ref_s, c="#2c7bb6", alpha=0.6, label=f"{ref_val} routes")
    ax.legend(
        title="Airport Routes",
        loc="lower left",
        fontsize=STYLE["legend_fontsize"],
        framealpha=0.85,
    )

    ax.set_axis_off()
    add_map_annotations(
        ax,
        title="Scenario B — Urban Services: Global Airport Connectivity",
        subtitle="Proportional symbols — circle area ∝ route count | Red labels = underserved regions",
        source="OpenFlights.org",
        projection_name="robinson",
        year=2020,
    )
    save_figure(fig, PATHS["fig_part7"] / "scenario_b_urban_services.png")
    plt.close(fig)


# ============================================================
# SCENARIO C – CLIMATE RISK (two-layer: hazard + population)
# Map type: Bivariate choropleth (temp risk + population density)
# ============================================================


def scenario_c_climate_risk(world, temps):
    """
    Generate a Climate Risk Scenario Map using a bivariate distribution of temperature anomaly and population exposure.

    Args:
        world (gpd.GeoDataFrame): Geospatial database containing population density.
        temps (pd.DataFrame): Point observations of temperature to interpolate as climate risk.
    """
    world = world.copy()

    # --- Hazard layer: temperature as climate risk proxy ---
    # Interpolate station temps onto country centroids
    lons = temps["lon"].values
    lats = temps["lat"].values
    vals = temps["mean_temp_c"].values
    rbf = RBFInterpolator(
        np.column_stack([lons, lats]), vals, kernel="thin_plate_spline", smoothing=5
    )

    if world.crs.to_epsg() != 4326:
        world_wgs = world.to_crs("EPSG:4326")
    else:
        world_wgs = world

    centroids = world_wgs.geometry.centroid
    ctr_coords = np.column_stack([centroids.x.values, centroids.y.values])
    world["interp_temp"] = rbf(ctr_coords)

    # Normalise both layers 0–1 for bivariate encoding
    pop_vals = world["pop_density"].fillna(0).clip(lower=0)
    temp_vals = world["interp_temp"].fillna(world["interp_temp"].mean())

    pop_norm = (pop_vals - pop_vals.min()) / (pop_vals.max() - pop_vals.min() + 1e-9)
    temp_norm = (temp_vals - temp_vals.min()) / (
        temp_vals.max() - temp_vals.min() + 1e-9
    )

    # Bivariate class (3×3 grid)
    world["pop_class"] = pd.qcut(pop_norm, 3, labels=[0, 1, 2]).astype(int)
    world["temp_class"] = pd.qcut(temp_norm, 3, labels=[0, 1, 2]).astype(int)
    world["bivar_class"] = world["pop_class"] + world["temp_class"] * 3

    # Bivariate colour matrix (3×3 = 9 classes)
    bivar_colors = {
        0: "#e8e8e8",
        1: "#ace4e4",
        2: "#5ac8c8",
        3: "#dfb0d6",
        4: "#a5add3",
        5: "#5698b9",
        6: "#be64ac",
        7: "#8c62aa",
        8: "#3b4994",
    }
    world["bivar_color"] = world["bivar_class"].map(bivar_colors).fillna("#d9d9d9")

    world_proj = reproject_gdf(world, "robinson")

    fig, ax = plt.subplots(1, 1, figsize=STYLE["fig_size_world"])
    fig.patch.set_facecolor("white")
    ax.set_facecolor(STYLE["ocean_color"])

    for color, group in world_proj.groupby("bivar_color"):
        group.plot(
            ax=ax,
            color=color,
            linewidth=STYLE["boundary_linewidth"],
            edgecolor=STYLE["boundary_color"],
        )

    # Legend (3×3 matrix)
    legend_ax = fig.add_axes([0.08, 0.12, 0.12, 0.12])
    for row in range(3):
        for col in range(3):
            cls = col + row * 3
            c = bivar_colors.get(cls, "#eee")
            legend_ax.add_patch(
                mpatches.Rectangle((col, row), 1, 1, fc=c, ec="white", lw=0.5)
            )
    legend_ax.set_xlim(0, 3)
    legend_ax.set_ylim(0, 3)
    legend_ax.set_xticks([0.5, 1.5, 2.5])
    legend_ax.set_xticklabels(["Low", "Med", "High"], fontsize=7)
    legend_ax.set_yticks([0.5, 1.5, 2.5])
    legend_ax.set_yticklabels(["Low", "Med", "High"], fontsize=7)
    legend_ax.set_xlabel("Temperature (hazard)", fontsize=7)
    legend_ax.set_ylabel("Pop. Density (exposure)", fontsize=7)
    legend_ax.set_title("Climate Risk Matrix", fontsize=7, pad=3)
    legend_ax.tick_params(length=0)

    ax.set_axis_off()
    add_map_annotations(
        ax,
        title="Scenario C — Climate Risk: Hazard × Population Exposure",
        subtitle="Bivariate map: colour = (temperature level × population density) | Dark blue = highest combined risk",
        source="OWID, Natural Earth, Berkeley Earth (2020)",
        projection_name="robinson",
        year=2020,
    )
    save_figure(fig, PATHS["fig_part7"] / "scenario_c_climate_risk.png")
    plt.close(fig)


DESIGN_DECISIONS = """
PART 7 – MAP DESIGN DECISIONS
==============================

SCENARIO A – PUBLIC HEALTH
----------------------------
Chosen map type: CHOROPLETH (normalised disease index by country)

Why choropleth:
  The variable (disease burden rate) is a normalised country-level statistic —
  exactly the use case choropleths are designed for. It allows rapid continental
  comparison (Sub-Saharan Africa vs Western Europe) and is familiar to the
  health policy audience.

Why not a proportional symbol map:
  Proportional symbols would show absolute case counts, not rates. Large
  countries (India, China) would appear most burdened even if their per-capita
  rates are moderate. Symbols also obscure the spatial extent of high-burden
  regions, which is critical for policy planning.

Why not a flow map:
  Disease burden is a stock measure (how sick a region is), not a flow
  (movement between regions). A flow map would be appropriate for tracking
  contagion spread, not static burden.

SCENARIO B – URBAN SERVICES
-----------------------------
Chosen map type: PROPORTIONAL SYMBOL MAP (airport size = connectivity)

Why proportional symbols:
  Airports are POINT features. Their connectivity (number of routes) is
  inherently tied to a specific geographic location, not to a region as a whole.
  A proportional symbol correctly places the data at the service facility.
  The visual size immediately communicates service capacity.

Why not a choropleth:
  Aggregating airport routes by country and filling the country polygon implies
  that air connectivity is distributed across the entire country, which is
  meaningless. Nigeria's connectivity is Lagos + Abuja, not everywhere in Nigeria.

Why not a density map:
  Density maps smooth point data across space — appropriate for diffuse phenomena
  (population, crime incidents) but wrong for discrete infrastructure nodes.

SCENARIO C – CLIMATE RISK
---------------------------
Chosen map type: BIVARIATE CHOROPLETH (hazard × exposure)

Why bivariate:
  Risk = hazard × exposure. Neither layer alone answers the policy question.
  A high-hazard but unpopulated area (Sahara) has low risk. A low-hazard but
  densely populated area (Netherlands coastal lowlands) has moderate risk.
  Only the combined bivariate encoding correctly identifies high-risk zones:
  South Asia, coastal West Africa, Bangladesh.

Why not two separate maps:
  Two maps require the reader to mentally overlay them — a cognitively demanding
  task that introduces error. The bivariate map performs this overlay visually
  and instantly communicates the combined risk zones.

Limitation:
  The 3×3 bivariate colour matrix is hard to decode without the legend. The
  9 distinct colours exceed the recommended palette size for most readers. For a
  general audience, a simpler two-variable dot map or side-by-side comparison
  might be more accessible, at the cost of the combined visual message.
"""


def run():
    print("=" * 60)
    print("  Part 7 — Case-Based Scenarios")
    print("=" * 60)
    PATHS["fig_part7"].mkdir(parents=True, exist_ok=True)

    world, airports, temps = load_data()

    print("\n[1/3] Scenario A — Public Health...")
    scenario_a_public_health(world)

    print("\n[2/3] Scenario B — Urban Services...")
    scenario_b_urban_services(world, airports)

    print("\n[3/3] Scenario C — Climate Risk...")
    scenario_c_climate_risk(world, temps)

    out = PATHS["fig_part7"] / "part7_design_decisions.txt"
    out.write_text(DESIGN_DECISIONS.strip(), encoding="utf-8")
    print(f"   Design decisions saved.")
    print("\n Part 7 complete.")


if __name__ == "__main__":
    run()
