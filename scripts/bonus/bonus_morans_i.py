"""
bonus_morans_i.py
=================
BONUS – Spatial Autocorrelation (Moran's I)

Computes Global and Local Moran's I for CO₂ per capita,
identifying spatial clusters and outliers (LISA map).

Produces:
  - outputs/figures/bonus/morans_i_results.txt
  - outputs/figures/bonus/map_lisa_clusters.png
  - outputs/figures/bonus/morans_i_scatter.png

Usage:
    python scripts/bonus/bonus_morans_i.py
"""

import sys, warnings

warnings.filterwarnings("ignore")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import geopandas as gpd
import numpy as np

from scripts.utils.config import PATHS, STYLE
from scripts.utils.map_utils import save_figure, add_map_annotations, reproject_gdf


def run():
    """
    Execute the Moran's I spatial autocorrelation bonus module.
    
    Loads master world data, computes Global and Local Moran's I for CO2 per capita,
    and produces static LISA cluster maps and Moran scatter plots.
    """
    print("=" * 60)
    print("  BONUS — Spatial Autocorrelation (Moran's I)")
    print("=" * 60)

    PATHS["fig_bonus"].mkdir(parents=True, exist_ok=True)

    # Load
    world = gpd.read_file(PATHS["processed"] / "master_world.gpkg")
    world = world.dropna(subset=["co2_per_capita"]).copy()

    if world.crs.to_epsg() != 4326:
        world = world.to_crs("EPSG:4326")

    # Fix any invalid geometries
    world["geometry"] = world["geometry"].buffer(0)

    try:
        import libpysal
        from libpysal.weights import Queen
        from esda.moran import Moran, Moran_Local

        # Spatial weights
        w = Queen.from_dataframe(world, silence_warnings=True)
        w.transform = "R"  # row-standardise

        y = world["co2_per_capita"].values

        # ─── Global Moran's I ────────────────────────────────
        mi = Moran(y, w)
        result_text = f"""
GLOBAL MORAN'S I — CO₂ per Capita
====================================
Moran's I statistic : {mi.I:.4f}
Expected I (random) : {mi.EI:.4f}
Variance            : {mi.VI_norm:.6f}
z-score             : {mi.z_norm:.4f}
p-value (normal)    : {mi.p_norm:.6f}

INTERPRETATION
--------------
Moran's I ranges from -1 (perfect dispersion) to +1 (perfect clustering).
A value of {mi.I:.3f} with p = {mi.p_norm:.4f} indicates:
{"SIGNIFICANT POSITIVE spatial autocorrelation — similar CO₂ values cluster geographically." if mi.p_norm < 0.05 else "No significant spatial autocorrelation detected."}

High-emission countries tend to be spatially adjacent to other high-emission
countries (e.g. the Gulf states cluster; sub-Saharan low-emission countries cluster).
This has implications for regional climate policy — targeting geographic clusters
may be more efficient than country-by-country approaches.
"""
        print(result_text)
        out_txt = PATHS["fig_bonus"] / "morans_i_results.txt"
        out_txt.write_text(result_text.strip(), encoding="utf-8")

        # ─── Local Moran's I (LISA) ──────────────────────────
        lm = Moran_Local(y, w, seed=42)

        sig = lm.p_sim < 0.05
        quad = lm.q  # 1=HH, 2=LH, 3=LL, 4=HL

        world["lisa_cluster"] = "Not significant"
        world.loc[sig & (quad == 1), "lisa_cluster"] = "High-High"
        world.loc[sig & (quad == 2), "lisa_cluster"] = "Low-High"
        world.loc[sig & (quad == 3), "lisa_cluster"] = "Low-Low"
        world.loc[sig & (quad == 4), "lisa_cluster"] = "High-Low"

        cluster_colors = {
            "High-High": "#d73027",
            "Low-Low": "#4575b4",
            "Low-High": "#abd9e9",
            "High-Low": "#fdae61",
            "Not significant": "#eeeeee",
        }
        world["lisa_color"] = world["lisa_cluster"].map(cluster_colors)

        # ─── LISA Map ────────────────────────────────────────
        world_proj = reproject_gdf(world.copy(), "robinson")

        fig, ax = plt.subplots(1, 1, figsize=STYLE["fig_size_world"])
        fig.patch.set_facecolor("white")
        ax.set_facecolor(STYLE["ocean_color"])

        for cluster, color in cluster_colors.items():
            subset = world_proj[world_proj["lisa_cluster"] == cluster]
            if len(subset) > 0:
                subset.plot(
                    ax=ax,
                    color=color,
                    linewidth=STYLE["boundary_linewidth"],
                    edgecolor=STYLE["boundary_color"],
                )

        # Legend
        patches = [mpatches.Patch(color=c, label=l) for l, c in cluster_colors.items()]
        ax.legend(
            handles=patches,
            title="LISA Cluster\n(p < 0.05)",
            loc="lower left",
            fontsize=STYLE["legend_fontsize"],
            framealpha=0.85,
        )
        ax.set_axis_off()
        add_map_annotations(
            ax,
            title=f"Local Moran's I — CO₂ per Capita Spatial Clusters (Global I = {mi.I:.3f})",
            subtitle="LISA: High-High = emission hotspot cluster | Low-Low = low-emission cluster",
            source="OWID (2020), PySAL/ESDA",
            projection_name="robinson",
            year=2020,
        )
        save_figure(fig, PATHS["fig_bonus"] / "map_lisa_clusters.png")
        plt.close(fig)

        # ─── Moran Scatter Plot ──────────────────────────────
        from splot.esda import moran_scatterplot

        fig2, ax2 = plt.subplots(1, 1, figsize=(8, 7))
        moran_scatterplot(mi, ax=ax2)
        ax2.set_title(
            f"Moran's I Scatter Plot — CO₂ per Capita\n"
            f"I = {mi.I:.4f}, p = {mi.p_norm:.4f}",
            fontsize=STYLE["title_fontsize"],
        )
        ax2.set_xlabel(
            "CO₂ per capita (standardised)", fontsize=STYLE["label_fontsize"]
        )
        ax2.set_ylabel("Spatial lag (standardised)", fontsize=STYLE["label_fontsize"])
        save_figure(fig2, PATHS["fig_bonus"] / "morans_i_scatter.png")
        plt.close(fig2)

        print("\n Moran's I analysis complete.")
        print(f"   Results: {PATHS['fig_bonus']}")

    except ImportError as e:
        print(f"    PySAL not installed: {e}")
        print("  Install with: pip install libpysal esda splot")
        # Create placeholder
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(
            0.5,
            0.5,
            "PySAL not installed.\nRun: pip install libpysal esda splot",
            ha="center",
            va="center",
            fontsize=14,
            transform=ax.transAxes,
        )
        save_figure(fig, PATHS["fig_bonus"] / "morans_i_placeholder.png")
        plt.close(fig)


if __name__ == "__main__":
    run()
