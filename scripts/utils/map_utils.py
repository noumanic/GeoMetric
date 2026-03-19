"""
map_utils.py
============
Reusable helper functions for all map parts.
Handles figure setup, saving, legends, annotations, and basemaps.

Usage:
    from scripts.utils.map_utils import (
        setup_figure, save_figure, add_map_annotations,
        reproject_gdf, make_choropleth, north_arrow
    )
"""

from pathlib import Path
from typing import Tuple

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable

import sys
from pathlib import Path as _Path

_PROJECT_ROOT = _Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.utils.config import STYLE, PROJECTIONS, PROJECTION_LABELS

# ============================================================
# FIGURE SETUP
# ============================================================


def setup_figure(
    size: str = "world",
    nrows: int = 1,
    ncols: int = 1,
    projection=None,
) -> Tuple[plt.Figure, any]:
    """
    Create a matplotlib figure with consistent styling.

    Args:
        size (str, optional): The physical map size alias ('world', 'regional', or 'small'). Defaults to 'world'.
        nrows (int, optional): Number of subplot rows. Defaults to 1.
        ncols (int, optional): Number of subplot columns. Defaults to 1.
        projection (optional): A Cartopy projection object. Defaults to None.

    Returns:
        tuple[plt.Figure, any]: A tuple containing the Figure and Axes object(s).
    """
    plt.rcParams.update(
        {
            "font.family": STYLE["font_family"],
            "font.size": STYLE["label_fontsize"],
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )

    figsize = {
        "world": STYLE["fig_size_world"],
        "regional": STYLE["fig_size_regional"],
        "small": STYLE["fig_size_small"],
    }.get(size, STYLE["fig_size_world"])

    if projection is not None:
        # cartopy subplot
        fig, axes = plt.subplots(
            nrows,
            ncols,
            figsize=figsize,
            subplot_kw={"projection": projection},
        )
    else:
        fig, axes = plt.subplots(nrows, ncols, figsize=figsize)

    fig.patch.set_facecolor("white")
    return fig, axes


# ============================================================
# SAVE FIGURE
# ============================================================


def save_figure(
    fig: plt.Figure,
    path: Path,
    draft: bool = False,
    tight: bool = True,
) -> Path:
    """
    Save a matplotlib figure at the appropriate resolution.

    Args:
        fig (plt.Figure): The matplotlib figure object to save.
        path (Path): Path location for the generated file.
        draft (bool, optional): If True, saves at 150 DPI for rapid previewing. 
            If False, saves at 300 DPI. Defaults to False.
        tight (bool, optional): If True, uses tight bounding boxes. Defaults to True.

    Returns:
        Path: The final saved physical path.
    """
    dpi = STYLE["dpi_draft"] if draft else STYLE["dpi_final"]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    kwargs = {
        "dpi": dpi,
        "bbox_inches": "tight" if tight else None,
        "facecolor": "white",
    }
    fig.savefig(path, **kwargs)
    print(f"   Saved: {path.name}  ({dpi} DPI)")
    return path


# ============================================================
# MAP ANNOTATIONS
# ============================================================


def add_map_annotations(
    ax,
    title: str,
    subtitle: str = "",
    source: str = "",
    projection_name: str = "",
    year: int = 2020,
    x_source: float = 0.01,
    y_source: float = -0.04,
):
    """
    Add a title, subtitle, and source attribution to a map axis.

    Args:
        ax: The matplotlib Axes target.
        title (str): Main title string.
        subtitle (str, optional): Subtitle text. Defaults to "".
        source (str, optional): Citation string. Defaults to "".
        projection_name (str, optional): Cartographic projection name. Defaults to "".
        year (int, optional): Descriptive year for the data. Defaults to 2020.
        x_source (float, optional): Relative X offset for the source text. Defaults to 0.01.
        y_source (float, optional): Relative Y offset for the source text. Defaults to -0.04.
    """
    ax.set_title(
        title,
        fontsize=STYLE["title_fontsize"],
        fontweight="bold",
        pad=12,
        loc="left",
    )
    if subtitle:
        ax.annotate(
            subtitle,
            xy=(0, 1.01),
            xycoords="axes fraction",
            fontsize=STYLE["subtitle_fontsize"],
            color="#555555",
        )

    proj_label = PROJECTION_LABELS.get(projection_name, projection_name)
    source_text = STYLE["source_template"].format(
        source=source or "Various",
        projection=proj_label or "WGS84",
        year=year,
    )
    ax.annotate(
        source_text,
        xy=(x_source, y_source),
        xycoords="axes fraction",
        fontsize=STYLE["caption_fontsize"],
        color="#777777",
        style="italic",
    )


# ============================================================
# REPROJECT
# ============================================================


def reproject_gdf(
    gdf: gpd.GeoDataFrame,
    target_crs: str,
) -> gpd.GeoDataFrame:
    """
    Reproject a GeoDataFrame to a target Coordinate Reference System (CRS).

    Accepts standard EPSG strings or internal PROJ strings defined in config.py.

    Args:
        gdf (gpd.GeoDataFrame): The spatial data to transform.
        target_crs (str): The destination CRS string or string alias.

    Returns:
        gpd.GeoDataFrame: The transformed spatial database.
    """
    # Resolve named projections from config
    crs = PROJECTIONS.get(target_crs, target_crs)

    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")

    reprojected = gdf.to_crs(crs)
    print(f"   Reprojected → {target_crs}")
    return reprojected


# ============================================================
# CHOROPLETH HELPER
# ============================================================


def make_choropleth(
    ax,
    gdf: gpd.GeoDataFrame,
    column: str,
    scheme: str = "quantiles",
    k: int = 5,
    cmap: str = None,
    legend: bool = True,
    missing_kwds: dict = None,
) -> gpd.GeoDataFrame:
    """
    Plot a discrete choropleth onto an axis using a MapClassify scheme.

    Args:
        ax: The matplotlib Axes target.
        gdf (gpd.GeoDataFrame): GeoDataFrame containing geometries and data.
        column (str): Data column to symbolize.
        scheme (str, optional): Classification scheme ('quantiles', 'natural_breaks', etc.). Defaults to 'quantiles'.
        k (int, optional): The number of classification bins. Defaults to 5.
        cmap (str, optional): The colormap string. Defaults to the sequential style palette.
        legend (bool, optional): Whether to embed a legend. Defaults to True.
        missing_kwds (dict, optional): Styling for empty geometries.

    Returns:
        gpd.GeoDataFrame: The plotted GeoDataFrame with a '_class' column added.
    """
    cmap = cmap or STYLE["sequential_palette"]
    missing_kwds = missing_kwds or {
        "color": STYLE["missing_data_color"],
        "label": "No data",
    }

    # Map scheme names to mapclassify
    scheme_map = {
        "quantiles": "Quantiles",
        "equal_interval": "EqualInterval",
        "natural_breaks": "NaturalBreaks",
        "jenks": "JenksCaspall",
        "fisher_jenks": "FisherJenks",
    }
    mc_scheme = scheme_map.get(scheme.lower(), "Quantiles")

    gdf.plot(
        column=column,
        ax=ax,
        scheme=mc_scheme,
        k=k,
        cmap=cmap,
        legend=legend,
        missing_kwds=missing_kwds,
        linewidth=STYLE["boundary_linewidth"],
        edgecolor=STYLE["boundary_color"],
        legend_kwds={
            "title": column,
            "fontsize": STYLE["legend_fontsize"],
            "title_fontsize": STYLE["legend_fontsize"],
            "loc": "lower left",
        },
    )
    return gdf


# ============================================================
# NORTH ARROW
# ============================================================


def north_arrow(ax, x: float = 0.95, y: float = 0.12, size: float = 0.04):
    """
    Draw a simple north arrow at relative axes coordinates.
    """
    ax.annotate(
        "N",
        xy=(x, y + size),
        xycoords="axes fraction",
        ha="center",
        va="bottom",
        fontsize=11,
        fontweight="bold",
    )
    ax.annotate(
        "",
        xy=(x, y + size),
        xytext=(x, y),
        xycoords="axes fraction",
        textcoords="axes fraction",
        arrowprops=dict(arrowstyle="-|>", color="black", lw=1.5),
    )


# ============================================================
# SCALE BAR (for geographic/projected maps)
# ============================================================


def scale_bar(ax, length_km: float = 1000, location: tuple = (0.05, 0.05)):
    """
    Add a scale bar to a map axis (for projected CRS in metres).
    length_km: approximate desired length in km.
    """
    # This is a simplified version; for accurate scale bars use matplotlib-scalebar
    try:
        from matplotlib_scalebar.scalebar import ScaleBar

        ax.add_artist(ScaleBar(1, units="m", location="lower right", frameon=False))
    except ImportError:
        # Fallback: simple annotation
        ax.annotate(
            f"≈ {length_km} km",
            xy=location,
            xycoords="axes fraction",
            fontsize=STYLE["caption_fontsize"],
            bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7),
        )


# ============================================================
# COLORBAR LEGEND
# ============================================================


def add_colorbar(
    fig: plt.Figure,
    ax,
    vmin: float,
    vmax: float,
    cmap: str,
    label: str,
    orientation: str = "vertical",
) -> None:
    """
    Attach a standalone colorbar to a figure.
    """
    norm = Normalize(vmin=vmin, vmax=vmax)
    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, orientation=orientation, shrink=0.6, pad=0.02)
    cbar.set_label(label, fontsize=STYLE["legend_fontsize"])
    cbar.ax.tick_params(labelsize=STYLE["caption_fontsize"])


# ============================================================
# COMPARISON TABLE (for Part 1 projections)
# ============================================================


def projection_comparison_table() -> pd.DataFrame:
    """Return a DataFrame comparing the three required projections."""
    from scripts.utils.config import PROJECTION_PROPERTIES

    rows = []
    for proj, props in PROJECTION_PROPERTIES.items():
        rows.append(
            {
                "Projection": PROJECTION_LABELS.get(proj, proj),
                "Preserves": props["preserves"],
                "Distorts": props["distorts"],
                "Best For": props["best_for"],
            }
        )
    return pd.DataFrame(rows)


# ============================================================
# POINTS → GeoDataFrame
# ============================================================


def points_to_gdf(
    df: pd.DataFrame,
    lat_col: str = "lat",
    lon_col: str = "lon",
    crs: str = "EPSG:4326",
) -> gpd.GeoDataFrame:
    """
    Convert a DataFrame with lat/lon columns to a GeoDataFrame.
    """
    from shapely.geometry import Point

    geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
    return gpd.GeoDataFrame(df.copy(), geometry=geometry, crs=crs)


# ============================================================
# PROPORTIONAL SYMBOL SCALER
# ============================================================


def scale_symbols(
    values: pd.Series,
    min_size: float = 10,
    max_size: float = 2000,
    method: str = "area",
) -> np.ndarray:
    """
    Perform visual scaling of symbol markers based on numeric values.

    Args:
        values (pd.Series): The raw numeric data series to be scaled.
        min_size (float, optional): The minimum bounding scatter size (points squared). Defaults to 10.
        max_size (float, optional): The maximum bounding scatter size (points squared). Defaults to 2000.
        method (str, optional): Symbol scaling technique ('area' or 'radius'). Defaults to 'area'.

    Returns:
        np.ndarray: Size values appropriate for the scatter s= parameter.
    """
    v = values.fillna(0).clip(lower=0)
    v_norm = (v - v.min()) / (v.max() - v.min() + 1e-9)

    if method == "area":
        # Scale area linearly → visually correct
        sizes = min_size + v_norm * (max_size - min_size)
    else:
        # Scale radius (perceptually misleading but simpler)
        radii = np.sqrt(min_size) + v_norm * (np.sqrt(max_size) - np.sqrt(min_size))
        sizes = radii**2

    return sizes.values


# ============================================================
# FLOW LINE HELPER
# ============================================================


def flow_linewidth(
    value: float,
    vmin: float,
    vmax: float,
    min_lw: float = 0.3,
    max_lw: float = 6.0,
) -> float:
    """Scale a single flow value to a line width."""
    if vmax == vmin:
        return min_lw
    norm = (value - vmin) / (vmax - vmin)
    return min_lw + norm * (max_lw - min_lw)
