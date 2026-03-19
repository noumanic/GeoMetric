"""
config.py
=========
Central configuration for the GeoViz project.
All paths, projection strings, style settings, and dataset URLs
are defined here so every script imports from one place.

Usage:
    from scripts.utils.config import PATHS, PROJECTIONS, STYLE, DATASETS
"""

from pathlib import Path

# ============================================================
# ROOT PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]  # project root

PATHS = {
    # --- Raw data directories ---
    "raw_shapefiles": ROOT / "data" / "raw" / "shapefiles",
    "raw_emissions": ROOT / "data" / "raw" / "emissions",
    "raw_population": ROOT / "data" / "raw" / "population",
    "raw_airports": ROOT / "data" / "raw" / "airports",
    "raw_temperature": ROOT / "data" / "raw" / "temperature",
    "raw_migration": ROOT / "data" / "raw" / "migration",
    "raw_gdp": ROOT / "data" / "raw" / "gdp",
    # --- Processed data ---
    "processed": ROOT / "data" / "processed",
    "cache": ROOT / "data" / "cache",
    # --- Output figures (static) ---
    "fig_part1": ROOT / "outputs" / "figures" / "part1_projections",
    "fig_part2": ROOT / "outputs" / "figures" / "part2_choropleth",
    "fig_part3": ROOT / "outputs" / "figures" / "part3_proportional",
    "fig_part4": ROOT / "outputs" / "figures" / "part4_flow",
    "fig_part5": ROOT / "outputs" / "figures" / "part5_contour",
    "fig_part6": ROOT / "outputs" / "figures" / "part6_cartogram",
    "fig_part7": ROOT / "outputs" / "figures" / "part7_scenarios",
    "fig_bonus": ROOT / "outputs" / "figures" / "bonus",
    # --- Interactive outputs ---
    "interactive_dash": ROOT / "outputs" / "interactive" / "dashboards",
    "interactive_folium": ROOT / "outputs" / "interactive" / "folium_maps",
    "interactive_anim": ROOT / "outputs" / "interactive" / "animations",
    # --- Report ---
    "report": ROOT / "report",
    "report_assets": ROOT / "report" / "assets",
}


# ============================================================
# COORDINATE REFERENCE SYSTEMS (CRS)
# ============================================================

PROJECTIONS = {
    # Part 1 – the three required projections
    "albers_equal_area": "+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96",
    "lambert_conformal_conic": "+proj=lcc +lat_1=33 +lat_2=45 +lat_0=39 +lon_0=-96",
    "winkel_tripel": "+proj=wintri",
    "robinson": "+proj=robin",
    # Standard working CRS
    "wgs84": "EPSG:4326",  # geographic, lat/lon
    "web_mercator": "EPSG:3857",  # web tiles (contextily)
    "mollweide": "+proj=moll",  # equal-area world map
    "eckert4": "+proj=eck4",  # another equal-area option
}

# Human-readable labels for map titles
PROJECTION_LABELS = {
    "albers_equal_area": "Albers Equal-Area Conic",
    "lambert_conformal_conic": "Lambert Conformal Conic",
    "winkel_tripel": "Winkel Tripel",
    "robinson": "Robinson",
    "wgs84": "WGS84 (Geographic)",
    "mollweide": "Mollweide",
}

# What each projection preserves / distorts (for Part 1 table)
PROJECTION_PROPERTIES = {
    "albers_equal_area": {
        "preserves": "Area",
        "distorts": "Shape (at edges), direction",
        "best_for": "Thematic comparison by area",
    },
    "lambert_conformal_conic": {
        "preserves": "Shape (angles/conformality) locally",
        "distorts": "Area (inflated at poles)",
        "best_for": "Navigation, aeronautical charts",
    },
    "winkel_tripel": {
        "preserves": "Compromise — minimises overall distortion",
        "distorts": "Neither fully area nor fully conformal",
        "best_for": "General educational world maps (used by NGS)",
    },
}


# ============================================================
# DATASET DOWNLOAD URLs
# ============================================================

DATASETS = {
    # Natural Earth — GeoJSON files served directly from GitHub raw
    # (More reliable than ZIP downloads; no extraction needed; always 200 OK)
    "shapefile_110m": (
        "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
        "master/geojson/ne_110m_admin_0_countries.geojson"
    ),
    "shapefile_10m": (
        "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
        "master/geojson/ne_110m_admin_0_countries.geojson"
    ),
    "populated_places": (
        "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
        "master/geojson/ne_10m_populated_places.geojson"
    ),
    # Emissions — Our World in Data
    "owid_co2": "https://nyc3.digitaloceanspaces.com/owid-public/data/co2/owid-co2-data.csv",
    "owid_codebook": "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-codebook.csv",
    # Population
    "population_csv": "https://raw.githubusercontent.com/datasets/population/main/data/population.csv",
    # Airports & routes — OpenFlights
    "airports_dat": "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat",
    "routes_dat": "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat",
    # World Bank indicators
    "wb_gdp": "https://api.worldbank.org/v2/en/indicator/NY.GDP.MKTP.CD?downloadformat=csv",
    "wb_migration": "https://api.worldbank.org/v2/en/indicator/SM.POP.NETM?downloadformat=csv",
}

# Column name mappings after download (standardise across datasets)
COLUMN_MAP = {
    "owid_co2": {
        "country": "country",
        "year": "year",
        "iso_code": "iso_code",
        "co2": "co2_total",
        "co2_per_capita": "co2_per_capita",
        "total_ghg": "total_ghg",
        "population": "population",
        "gdp": "gdp",
        "energy_per_capita": "energy_per_capita",
    },
    "airports": {
        0: "airport_id",
        1: "name",
        2: "city",
        3: "country",
        4: "iata",
        5: "icao",
        6: "lat",
        7: "lon",
        8: "altitude",
        9: "timezone",
        10: "dst",
        11: "tz_db",
        12: "type",
        13: "source",
    },
    "routes": {
        0: "airline",
        1: "airline_id",
        2: "src_iata",
        3: "src_id",
        4: "dst_iata",
        5: "dst_id",
        6: "codeshare",
        7: "stops",
        8: "equipment",
    },
}

# Reference year for analysis
ANALYSIS_YEAR = 2020


# ============================================================
# VISUAL STYLE SETTINGS
# ============================================================

STYLE = {
    # Figure dimensions (width, height) in inches
    "fig_size_world": (16, 9),
    "fig_size_regional": (12, 8),
    "fig_size_small": (8, 6),
    # DPI for saved outputs
    "dpi_draft": 150,
    "dpi_final": 300,
    # Font sizes
    "title_fontsize": 16,
    "subtitle_fontsize": 12,
    "label_fontsize": 10,
    "caption_fontsize": 8,
    "legend_fontsize": 9,
    # Color palettes
    "sequential_palette": "YlOrRd",  # for choropleth (low→high)
    "diverging_palette": "RdBu_r",  # for above/below average
    "categorical_palette": "tab10",  # for categorical data
    "flow_color": "#2166ac",  # flow map lines
    "symbol_color": "#d73027",  # proportional symbol fill
    "symbol_alpha": 0.6,  # transparency for symbols
    "boundary_color": "#333333",  # country borders
    "boundary_linewidth": 0.4,
    "ocean_color": "#cfe2f3",
    "land_color": "#f5f5f0",
    "missing_data_color": "#d9d9d9",  # grey for no-data countries
    # Fonts
    "font_family": "DejaVu Sans",
    # Standard footer / source note template
    "source_template": "Source: {source} | Projection: {projection} | Year: {year}",
}


# ============================================================
# CLASSIFICATION METHODS (Part 2)
# ============================================================

CLASSIFICATION = {
    "methods": ["quantiles", "equal_interval", "natural_breaks", "jenks"],
    "n_classes": 5,  # number of bins
    "default": "quantiles",
}


# ============================================================
# FLOW MAP SETTINGS (Part 4)
# ============================================================

FLOW = {
    "top_n_routes": 30,  # show only top N airline routes
    "min_flow_threshold": 1000,  # minimum passengers/migrants to display
    "max_line_width": 8,  # maximum line width for flows
    "min_line_width": 0.5,
    "arrow_size": 10,
}


# ============================================================
# INTERPOLATION SETTINGS (Part 5)
# ============================================================

INTERPOLATION = {
    "method": "rbf",  # 'rbf', 'idw', 'linear', 'cubic'
    "grid_resolution": 200,  # pixels per side for interpolation grid
    "contour_levels": 15,  # number of contour lines
    "idw_power": 2,  # IDW power parameter
}


# ============================================================
# HELPER: ensure all output dirs exist
# ============================================================


def ensure_dirs():
    """Create all output directories if they don't already exist."""
    for key, path in PATHS.items():
        path.mkdir(parents=True, exist_ok=True)
    print(" All directories verified.")


if __name__ == "__main__":
    ensure_dirs()
    print("\nProject root:", ROOT)
    print("Configured paths:")
    for k, v in PATHS.items():
        print(f"  {k:<25} → {v}")
