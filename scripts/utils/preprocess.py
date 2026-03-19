"""
preprocess.py
=============
Data cleaning, joining, and preprocessing pipeline.
Run AFTER data_loader.py and BEFORE any part script.

Produces standardised files in data/processed/ that all parts use.

Usage:
    python scripts/utils/preprocess.py
"""

import sys
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.utils.config import PATHS, ANALYSIS_YEAR
from scripts.utils.data_loader import (
    load_world,
    load_emissions,
    load_population,
    load_airports,
    load_routes,
    load_temperature,
)

# ============================================================
# 1. WORLD SHAPEFILE → cleaned GeoDataFrame
# ============================================================


def process_world_shapefile() -> gpd.GeoDataFrame:
    """
    Load and clean the Natural Earth 110m countries shapefile.
    
    Standardises column names to lowercase and fixes common ISO code issues 
    where some countries are missing standard 3-letter codes.

    Returns:
        gpd.GeoDataFrame: A cleaned GeoDataFrame with resolved standard ISO codes.
        
    Saves: 
        data/processed/world_countries.gpkg
    """
    print(" Processing world shapefile...")
    world = load_world("110m")

    # Normalise all columns to uppercase for consistent access
    # (GeoJSON from GitHub uses uppercase, shapefile uses uppercase too after load_world())
    world.columns = [c.upper() if c != "geometry" else c for c in world.columns]

    # Handle both full and abbreviated column name variants across NE versions
    col_aliases = {
        "country_name": ["NAME", "ADMIN", "NAME_LONG"],
        "iso_a3": ["ISO_A3", "ADM0_A3", "SOV_A3"],
        "iso_a2": ["ISO_A2"],
        "continent": ["CONTINENT", "REGION_UN"],
        "pop_est": ["POP_EST"],
        "gdp_md": ["GDP_MD", "GDP_MD_EST"],
        "subregion": ["SUBREGION", "REGION_WB"],
    }

    for target, candidates in col_aliases.items():
        for c in candidates:
            if c in world.columns:
                world = world.rename(columns={c: target})
                break

    # Keep only columns that exist
    keep = [
        "country_name",
        "iso_a3",
        "iso_a2",
        "continent",
        "pop_est",
        "gdp_md",
        "subregion",
        "geometry",
    ]
    world = world[[c for c in keep if c in world.columns]].copy()

    # Fix known ISO code issues in Natural Earth
    fixes = {
        "France": "FRA",
        "Norway": "NOR",
        "Kosovo": "XKX",
        "Somaliland": "SOM",
    }
    for name, iso in fixes.items():
        mask = world["country_name"] == name
        world.loc[mask, "iso_a3"] = iso

    world = world[world["iso_a3"] != "-99"]
    world = world.set_crs("EPSG:4326", allow_override=True)

    out = PATHS["processed"] / "world_countries.gpkg"
    world.to_file(out, driver="GPKG")
    print(f"   world_countries.gpkg  ({len(world)} countries)")
    return world


# ============================================================
# 2. EMISSIONS DATA → cleaned CSV
# ============================================================


def process_emissions() -> pd.DataFrame:
    """
    Load and clean OWID CO2 data for the specific analysis year.
    
    Filters global historical data, drops regional aggregate rows, and
    mathematically calibrates missing per-capita emission metrics.

    Returns:
        pd.DataFrame: A cleaned DataFrame of country-level emissions.
        
    Saves: 
        data/processed/emissions_{year}.csv
    """
    print(" Processing emissions data...")
    df = load_emissions(ANALYSIS_YEAR)

    keep_cols = [
        "iso_code",
        "country",
        "year",
        "co2",
        "co2_per_capita",
        "methane",
        "nitrous_oxide",
        "total_ghg",
        "population",
        "gdp",
        "energy_per_capita",
        "share_global_co2",
        "cumulative_co2",
    ]
    df = df[[c for c in keep_cols if c in df.columns]].copy()
    df = df.rename(columns={"iso_code": "iso_a3", "co2": "co2_total"})

    # Fill missing per-capita where possible
    if "co2_total" in df.columns and "population" in df.columns:
        mask = (
            df["co2_per_capita"].isna()
            & df["co2_total"].notna()
            & df["population"].notna()
        )
        df.loc[mask, "co2_per_capita"] = (
            df.loc[mask, "co2_total"] * 1e6 / df.loc[mask, "population"]
        )

    out = PATHS["processed"] / f"emissions_{ANALYSIS_YEAR}.csv"
    df.to_csv(out, index=False)
    print(f"   emissions_{ANALYSIS_YEAR}.csv  ({len(df)} countries)")
    return df


# ============================================================
# 3. POPULATION DATA → cleaned CSV
# ============================================================


def process_population() -> pd.DataFrame:
    """
    Load and clean World Bank demographic population data.
    
    Standardizes inconsistent API column headers. If World Bank data is 
    corrupted or missing, falls back to OWID population figures.

    Returns:
        pd.DataFrame: A standardized DataFrame containing ISO codes and population counts.
        
    Saves: 
        data/processed/population_{year}.csv
    """
    print(" Processing population data...")
    try:
        df = load_population(ANALYSIS_YEAR)
        # Normalise columns
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        # Handle different World Bank CSV formats
        if "country_code" in df.columns:
            df = df.rename(columns={"country_code": "iso_a3", "value": "population"})
        elif "country.code" in df.columns:
            df = df.rename(columns={"country.code": "iso_a3", "value": "population"})

        df = df[["iso_a3", "population"]].dropna()

    except Exception:
        # Fallback: extract from OWID emissions which has population column
        print("    Falling back to OWID population data...")
        raw = load_emissions(ANALYSIS_YEAR)
        df = raw[["iso_code", "population"]].dropna().copy()
        df = df.rename(columns={"iso_code": "iso_a3"})

    out = PATHS["processed"] / f"population_{ANALYSIS_YEAR}.csv"
    df.to_csv(out, index=False)
    print(f"   population_{ANALYSIS_YEAR}.csv  ({len(df)} records)")
    return df


# ============================================================
# 4. AIRPORTS + ROUTES → cleaned CSVs + GeoDataFrame
# ============================================================


def process_airports_and_routes():
    """
    Clean openflight airports dataset and merge geometric facts into routes.
    
    Computes graph node degrees (route counts per airport), and embeds 
    source/destination Spatial coordinates directly into the flight edges table.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: Cleaned airports DataFrame and routes DataFrame.
        
    Saves:
        data/processed/airports_clean.csv
        data/processed/routes_clean.csv
    """
    print(" Processing airports & routes...")
    airports = load_airports()
    routes = load_routes()

    # --- Clean routes ---
    routes = routes[
        routes["src_iata"].notna()
        & routes["dst_iata"].notna()
        & (routes["src_iata"] != "\\N")
        & (routes["dst_iata"] != "\\N")
    ].copy()

    # --- Route count per airport ---
    src_count = routes.groupby("src_iata").size().reset_index(name="departures")
    dst_count = routes.groupby("dst_iata").size().reset_index(name="arrivals")

    airports = airports.merge(
        src_count, left_on="iata", right_on="src_iata", how="left"
    )
    airports = airports.merge(
        dst_count, left_on="iata", right_on="dst_iata", how="left"
    )
    airports["departures"] = airports["departures"].fillna(0).astype(int)
    airports["arrivals"] = airports["arrivals"].fillna(0).astype(int)
    airports["total_routes"] = airports["departures"] + airports["arrivals"]

    # --- Attach coordinates to routes ---
    coord_map = airports.set_index("iata")[["lat", "lon", "country", "name"]].to_dict(
        "index"
    )

    def get_coord(iata, field):
        return coord_map.get(iata, {}).get(field, np.nan)

    routes["src_lat"] = routes["src_iata"].map(lambda x: get_coord(x, "lat"))
    routes["src_lon"] = routes["src_iata"].map(lambda x: get_coord(x, "lon"))
    routes["dst_lat"] = routes["dst_iata"].map(lambda x: get_coord(x, "lat"))
    routes["dst_lon"] = routes["dst_iata"].map(lambda x: get_coord(x, "lon"))
    routes["src_country"] = routes["src_iata"].map(lambda x: get_coord(x, "country"))
    routes["dst_country"] = routes["dst_iata"].map(lambda x: get_coord(x, "country"))

    routes = routes.dropna(subset=["src_lat", "dst_lat"])

    # --- Save ---
    ap_out = PATHS["processed"] / "airports_clean.csv"
    rt_out = PATHS["processed"] / "routes_clean.csv"
    airports.to_csv(ap_out, index=False)
    routes.to_csv(rt_out, index=False)

    print(f"   airports_clean.csv   ({len(airports)} airports)")
    print(f"   routes_clean.csv     ({len(routes)} routes)")
    return airports, routes


# ============================================================
# 5. TEMPERATURE → cleaned CSV
# ============================================================


def process_temperature() -> pd.DataFrame:
    """
    Load and validate temperature station data.

    Saves: data/processed/temperature_stations.csv
    """
    print(" Processing temperature data...")
    df = load_temperature()
    df = df.dropna(subset=["lat", "lon", "mean_temp_c"])
    df = df[df["lat"].between(-90, 90) & df["lon"].between(-180, 180)]

    out = PATHS["processed"] / "temperature_stations.csv"
    df.to_csv(out, index=False)
    print(f"   temperature_stations.csv  ({len(df)} stations)")
    return df


# ============================================================
# 6. MASTER JOIN: world + emissions + population
# ============================================================


def build_master_geodataframe() -> gpd.GeoDataFrame:
    """
    Integrate spatial, demographic, and environmental datasets into a master table.
    
    Executes a left-join on valid ISO-3 codes, merging CO2 metrics and population metrics
    into the World GeoDataFrame. Dynamically resolves missing population counts and calculates
    geometric area and population density.

    Returns:
        gpd.GeoDataFrame: The finalized composite geospatial database for choropleth mapping.
        
    Saves: 
        data/processed/master_world.gpkg
    """
    print(" Building master GeoDataFrame...")

    world = gpd.read_file(PATHS["processed"] / "world_countries.gpkg")
    emiss = pd.read_csv(PATHS["processed"] / f"emissions_{ANALYSIS_YEAR}.csv")
    pop = pd.read_csv(PATHS["processed"] / f"population_{ANALYSIS_YEAR}.csv")

    # --- Join 1: world + emissions ---
    master = world.merge(emiss, on="iso_a3", how="left", suffixes=("", "_owid"))
    n1 = master["co2_total"].notna().sum()
    print(f"   Join 1 (emissions): {n1}/{len(master)} matched")

    # --- Join 2: master + population ---
    pop = pop.rename(columns={"population": "population_wb"})
    master = master.merge(pop, on="iso_a3", how="left")
    n2 = master["population_wb"].notna().sum()
    print(f"   Join 2 (population): {n2}/{len(master)} matched")

    # --- Derived columns ---
    # Use OWID population where WB is missing
    master["pop_final"] = master["population_wb"].fillna(master["population"])

    # co2 per million people
    master["co2_per_million"] = (
        master["co2_total"] * 1e6 / master["pop_final"].replace(0, np.nan)
    )

    # GDP per capita (USD)
    if "gdp" in master.columns:
        master["gdp_per_capita"] = master["gdp"] / master["pop_final"].replace(
            0, np.nan
        )

    # Area in km²
    world_proj = master.to_crs("EPSG:6933")  # equal-area
    master["area_km2"] = world_proj.geometry.area / 1e6
    master["pop_density"] = master["pop_final"] / master["area_km2"].replace(0, np.nan)

    out = PATHS["processed"] / "master_world.gpkg"
    master.to_file(out, driver="GPKG")
    print(
        f"   master_world.gpkg  ({len(master)} countries, {master.shape[1]} columns)"
    )
    return master


# ============================================================
# RUN ALL
# ============================================================


def run():
    print("=" * 60)
    print("  GeoViz Project — Preprocessing Pipeline")
    print("=" * 60)

    process_world_shapefile()
    process_emissions()
    process_population()
    process_airports_and_routes()
    process_temperature()
    build_master_geodataframe()

    print("\n Preprocessing complete. Files saved to data/processed/")
    print("\nProcessed files:")
    for f in sorted(PATHS["processed"].glob("*")):
        size = f.stat().st_size / 1024
        print(f"  {f.name:<40} {size:>8.1f} KB")


if __name__ == "__main__":
    run()
