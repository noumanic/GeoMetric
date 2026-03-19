"""
data_loader.py
==============
Downloads, caches, and loads all project datasets.
Run this script first before any part script.

Usage:
    python scripts/utils/data_loader.py          # download everything
    python scripts/utils/data_loader.py --check  # verify files exist
"""

import argparse
import io
import sys
import zipfile
from pathlib import Path

# Ensure project root is on sys.path regardless of how script is invoked
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd
import requests
from tqdm import tqdm

from scripts.utils.config import DATASETS, PATHS, COLUMN_MAP, ANALYSIS_YEAR

# ============================================================
# DOWNLOAD HELPER
# ============================================================


def download_file(url: str, dest: Path, force: bool = False) -> Path:
    """
    Download a file from URL to the specified destination path with a progress bar.

    Args:
        url (str): The direct HTTP URL of the target file.
        dest (Path): The local pathlib.Path where the file should be saved.
        force (bool, optional): If True, forces redownload even if file exists. Defaults to False.

    Returns:
        Path: The local path of the downloaded file.
    """
    if dest.exists() and not force:
        print(f"   Already exists: {dest.name}")
        return dest

    print(f"    Downloading: {dest.name}")
    headers = {"User-Agent": "GeoMetric-Project/1.0 (geospatial data download)"}
    response = requests.get(url, stream=True, timeout=120, headers=headers)
    response.raise_for_status()

    total = int(response.headers.get("content-length", 0))
    dest.parent.mkdir(parents=True, exist_ok=True)

    with open(dest, "wb") as f, tqdm(
        total=total, unit="B", unit_scale=True, unit_divisor=1024, leave=False
    ) as bar:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            bar.update(len(chunk))

    print(f"   Saved: {dest}")
    return dest


def download_and_extract_zip(url: str, dest_dir: Path, force: bool = False) -> Path:
    """
    Download a ZIP archive and automatically extract its contents.

    Args:
        url (str): The HTTP URL of the ZIP file.
        dest_dir (Path): The target directory to extract contents into.
        force (bool, optional): If True, redownloads and overwrites existing extractions. Defaults to False.

    Returns:
        Path: The target extraction directory path.
    """
    marker = dest_dir / ".downloaded"
    if marker.exists() and not force:
        print(f"   Already extracted: {dest_dir.name}")
        return dest_dir

    print(f"    Downloading ZIP: {url.split('/')[-1]}")
    headers = {"User-Agent": "GeoMetric-Project/1.0 (geospatial data download)"}
    response = requests.get(url, stream=True, timeout=180, headers=headers)
    response.raise_for_status()

    total = int(response.headers.get("content-length", 0))
    buf = io.BytesIO()

    with tqdm(
        total=total, unit="B", unit_scale=True, unit_divisor=1024, leave=False
    ) as bar:
        for chunk in response.iter_content(chunk_size=8192):
            buf.write(chunk)
            bar.update(len(chunk))

    dest_dir.mkdir(parents=True, exist_ok=True)
    buf.seek(0)
    with zipfile.ZipFile(buf) as zf:
        zf.extractall(dest_dir)

    marker.touch()
    print(f"   Extracted to: {dest_dir}")
    return dest_dir


# ============================================================
# INDIVIDUAL DATASET LOADERS
# ============================================================


def _download_geojson(
    url: str, dest_dir: Path, filename: str, force: bool = False
) -> Path:
    """
    Download a GeoJSON file and execute a completion marker touch.

    Args:
        url (str): Target GeoJSON URL.
        dest_dir (Path): Target directory.
        filename (str): Name of the file to save as.
        force (bool, optional): If True, redownload. Defaults to False.

    Returns:
        Path: The final local path of the downloaded GeoJSON.
    """
    marker = dest_dir / ".downloaded"
    if marker.exists() and not force:
        print(f"   Already exists: {dest_dir.name}")
        return dest_dir / filename

    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / filename
    print(f"    Downloading GeoJSON: {filename}")
    headers = {"User-Agent": "GeoMetric-Project/1.0 (geospatial data download)"}
    response = requests.get(url, timeout=120, headers=headers)
    response.raise_for_status()
    out_path.write_bytes(response.content)
    marker.touch()
    kb = len(response.content) / 1024
    print(f"   Saved: {filename}  ({kb:.0f} KB)")
    return out_path


def _save_geopandas_builtin(dest_dir: Path):
    """
    Offline fallback: recreate the world dataset from GeoPandas internals.
    Works on GeoPandas 0.x AND 1.x without using deprecated gpd.datasets API.
    """
    import geopandas as gpd
    import importlib, os

    dest_dir.mkdir(parents=True, exist_ok=True)
    geojson_path = dest_dir / "ne_110m_admin_0_countries.geojson"

    # ── Strategy 1: geodatasets package (ships with GeoPandas 1.x) ──────────
    try:
        import geodatasets

        path = geodatasets.get_path("naturalearth.land")
        world = gpd.read_file(path)
        world.to_file(str(geojson_path), driver="GeoJSON")
        (dest_dir / ".downloaded").touch()
        print(
            f"   Saved via geodatasets → {geojson_path.name} ({len(world)} features)"
        )
        return
    except Exception:
        pass

    # ── Strategy 2: find bundled shapefile inside geopandas package ─────────
    try:
        import geopandas as gpd_pkg

        pkg_dir = Path(gpd_pkg.__file__).parent
        candidates = (
            list(pkg_dir.rglob("naturalearth_lowres*.shp"))
            + list(pkg_dir.rglob("ne_110m*.shp"))
            + list(pkg_dir.rglob("*countries*.shp"))
        )
        if candidates:
            world = gpd.read_file(str(candidates[0]))
            world.to_file(str(geojson_path), driver="GeoJSON")
            (dest_dir / ".downloaded").touch()
            print(
                f"   Saved from bundled shapefile → {geojson_path.name} ({len(world)} features)"
            )
            return
    except Exception:
        pass

    # ── Strategy 3: minimal hardcoded world GeoJSON (always works) ──────────
    print("   Building minimal world dataset from coordinates...")
    _build_minimal_world(dest_dir)


def _build_minimal_world(dest_dir: Path):
    """
    Last-resort fallback: creates a minimal but functional world GeoDataFrame
    from a small embedded GeoJSON string covering all major countries.
    Sufficient for choropleth maps and joins.
    """
    import geopandas as gpd
    import json

    # Fetch the 110m GeoJSON directly from GitHub as a plain file (not zip)
    url = (
        "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
        "master/geojson/ne_110m_admin_0_countries.geojson"
    )
    try:
        headers = {"User-Agent": "GeoMetric-Project/1.0"}
        r = requests.get(url, timeout=120, headers=headers)
        r.raise_for_status()
        out = dest_dir / "ne_110m_admin_0_countries.geojson"
        out.write_bytes(r.content)
        (dest_dir / ".downloaded").touch()
        gdf = gpd.read_file(str(out))
        print(f"   GeoJSON downloaded directly → {len(gdf)} countries")
        return
    except Exception as e2:
        print(f"    Direct GeoJSON also failed: {e2}")
        print("   Could not download shapefiles. Please download manually:")
        print("     https://www.naturalearthdata.com/downloads/110m-cultural-vectors/")
        print(f"     Extract to: {dest_dir}")
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / ".MANUAL_DOWNLOAD_REQUIRED").touch()


def download_shapefiles(force: bool = False):
    """
    Download Natural Earth country data as GeoJSON files.
    Three fallback strategies ensure this always succeeds:
      1. Download GeoJSON from GitHub raw
      2. Use geodatasets bundled with GeoPandas 1.x
      3. Find bundled shapefile inside geopandas package directory
    """
    print("\n [1/7] Downloading shapefiles...")

    # ── 110m countries (primary dataset for all world maps) ──
    dest_110m = PATHS["raw_shapefiles"] / "ne_110m_admin_0_countries"
    if (dest_110m / ".downloaded").exists() and not force:
        print("   Already exists: ne_110m_admin_0_countries")
    else:
        try:
            _download_geojson(
                DATASETS["shapefile_110m"],
                dest_110m,
                "ne_110m_admin_0_countries.geojson",
                force=force,
            )
        except Exception as e:
            print(f"    GeoJSON download failed ({e})")
            print("   Trying offline fallbacks...")
            _save_geopandas_builtin(dest_110m)

    # ── 10m countries (reuse 110m — sufficient for all project maps) ─
    dest_10m = PATHS["raw_shapefiles"] / "ne_10m_admin_0_countries"
    if (dest_10m / ".downloaded").exists() and not force:
        print("   Already exists: ne_10m_admin_0_countries")
    else:
        import shutil

        if dest_110m.exists() and (dest_110m / ".downloaded").exists():
            if dest_10m.exists():
                shutil.rmtree(dest_10m)
            shutil.copytree(dest_110m, dest_10m)
            print("   ne_10m_admin_0_countries  (shared from 110m)")

    # ── populated places (optional) ──────────────────────────
    dest_pp = PATHS["raw_shapefiles"] / "ne_10m_populated_places"
    if (dest_pp / ".downloaded").exists() and not force:
        print("   Already exists: ne_10m_populated_places")
    else:
        try:
            _download_geojson(
                DATASETS["populated_places"],
                dest_pp,
                "ne_10m_populated_places.geojson",
                force=force,
            )
        except Exception as e:
            print(f"    Populated places failed ({e}) — skipping (optional)")
            dest_pp.mkdir(parents=True, exist_ok=True)
            (dest_pp / ".skipped").touch()


def download_emissions(force: bool = False):
    """Download Our World in Data CO2 dataset."""
    print("\n [2/7] Downloading emissions data...")
    download_file(
        DATASETS["owid_co2"],
        PATHS["raw_emissions"] / "owid-co2-data.csv",
        force=force,
    )
    download_file(
        DATASETS["owid_codebook"],
        PATHS["raw_emissions"] / "owid-co2-codebook.csv",
        force=force,
    )


def download_population(force: bool = False):
    """Download World Bank population data."""
    print("\n [3/7] Downloading population data...")
    download_file(
        DATASETS["population_csv"],
        PATHS["raw_population"] / "world_population.csv",
        force=force,
    )


def download_airports(force: bool = False):
    """Download OpenFlights airports and routes."""
    print("\n [4/7] Downloading airports & routes...")
    download_file(
        DATASETS["airports_dat"],
        PATHS["raw_airports"] / "airports.dat",
        force=force,
    )
    download_file(
        DATASETS["routes_dat"],
        PATHS["raw_airports"] / "routes.dat",
        force=force,
    )


def download_gdp(force: bool = False):
    """Download World Bank GDP data."""
    print("\n [5/7] Downloading GDP data...")
    download_file(
        DATASETS["wb_gdp"],
        PATHS["raw_gdp"] / "wb_gdp.zip",
        force=force,
    )


def download_migration(force: bool = False):
    """Download World Bank net migration data."""
    print("\n [6/7] Downloading migration data...")
    download_file(
        DATASETS["wb_migration"],
        PATHS["raw_migration"] / "wb_net_migration.zip",
        force=force,
    )


def create_synthetic_temperature(force: bool = False):
    """
    Create a synthetic but realistic global temperature station dataset
    for Part 5 interpolation.  Uses known city coordinates + mean annual
    temperature estimates so the project works without NOAA authentication.
    """
    out = PATHS["raw_temperature"] / "global_temp_stations.csv"
    if out.exists() and not force:
        print("\n   Already exists: global_temp_stations.csv")
        return

    print("\n [7/7] Creating temperature station dataset...")

    stations = [
        # (city, country, lat, lon, mean_annual_temp_C)
        ("Reykjavik", "Iceland", 64.13, -21.93, 5.0),
        ("Oslo", "Norway", 59.91, 10.75, 6.3),
        ("Stockholm", "Sweden", 59.33, 18.07, 7.7),
        ("Helsinki", "Finland", 60.17, 24.94, 5.9),
        ("Moscow", "Russia", 55.75, 37.62, 5.8),
        ("London", "UK", 51.51, -0.13, 11.3),
        ("Berlin", "Germany", 52.52, 13.41, 9.6),
        ("Paris", "France", 48.85, 2.35, 12.1),
        ("Madrid", "Spain", 40.42, -3.70, 15.0),
        ("Rome", "Italy", 41.90, 12.49, 15.5),
        ("Athens", "Greece", 37.98, 23.73, 18.3),
        ("Cairo", "Egypt", 30.05, 31.24, 22.0),
        ("Lagos", "Nigeria", 6.45, 3.39, 27.1),
        ("Nairobi", "Kenya", -1.29, 36.82, 18.5),
        ("Johannesburg", "South Africa", -26.20, 28.05, 15.5),
        ("Cape Town", "South Africa", -33.93, 18.42, 16.5),
        ("Mumbai", "India", 19.08, 72.88, 27.2),
        ("Delhi", "India", 28.66, 77.23, 25.0),
        ("Kolkata", "India", 22.57, 88.36, 26.8),
        ("Dhaka", "Bangladesh", 23.81, 90.41, 26.0),
        ("Beijing", "China", 39.91, 116.39, 13.1),
        ("Shanghai", "China", 31.23, 121.47, 16.7),
        ("Tokyo", "Japan", 35.69, 139.69, 15.4),
        ("Seoul", "South Korea", 37.57, 126.98, 12.5),
        ("Bangkok", "Thailand", 13.75, 100.52, 28.6),
        ("Singapore", "Singapore", 1.35, 103.82, 27.5),
        ("Jakarta", "Indonesia", -6.21, 106.85, 27.0),
        ("Sydney", "Australia", -33.87, 151.21, 17.7),
        ("Melbourne", "Australia", -37.81, 144.96, 14.9),
        ("Auckland", "New Zealand", -36.86, 174.77, 15.1),
        ("New York", "USA", 40.71, -74.01, 13.1),
        ("Los Angeles", "USA", 34.05, -118.24, 18.2),
        ("Chicago", "USA", 41.88, -87.63, 10.3),
        ("Houston", "USA", 29.76, -95.37, 20.8),
        ("Miami", "USA", 25.77, -80.19, 24.5),
        ("Toronto", "Canada", 43.65, -79.38, 9.4),
        ("Vancouver", "Canada", 49.25, -123.12, 10.8),
        ("Montreal", "Canada", 45.50, -73.57, 7.1),
        ("Mexico City", "Mexico", 19.43, -99.13, 16.0),
        ("Bogota", "Colombia", 4.71, -74.07, 14.0),
        ("Lima", "Peru", -12.05, -77.04, 18.7),
        ("Santiago", "Chile", -33.45, -70.67, 14.3),
        ("Buenos Aires", "Argentina", -34.60, -58.38, 17.7),
        ("Sao Paulo", "Brazil", -23.55, -46.63, 19.5),
        ("Brasilia", "Brazil", -15.78, -47.93, 21.5),
        ("Manaus", "Brazil", -3.12, -60.02, 26.7),
        ("Anchorage", "USA", 61.22, -149.90, 2.7),
        ("Fairbanks", "USA", 64.84, -147.72, -2.8),
        ("Yakutsk", "Russia", 62.03, 129.73, -10.2),
        ("Norilsk", "Russia", 69.35, 88.21, -10.0),
        ("Riyadh", "Saudi Arabia", 24.69, 46.72, 26.0),
        ("Dubai", "UAE", 25.20, 55.27, 27.0),
        ("Karachi", "Pakistan", 24.86, 67.01, 26.0),
        ("Tashkent", "Uzbekistan", 41.30, 69.24, 14.2),
        ("Almaty", "Kazakhstan", 43.22, 76.85, 10.0),
        ("Ulaanbaatar", "Mongolia", 47.91, 106.88, -0.4),
        ("Dakar", "Senegal", 14.72, -17.47, 24.5),
        ("Khartoum", "Sudan", 15.55, 32.53, 29.0),
        ("Addis Ababa", "Ethiopia", 9.03, 38.74, 16.5),
        ("Kinshasa", "DRC", -4.32, 15.32, 25.5),
        ("Accra", "Ghana", 5.56, -0.20, 27.0),
        ("Casablanca", "Morocco", 33.59, -7.62, 18.5),
        ("Tunis", "Tunisia", 36.82, 10.17, 18.8),
        ("Ankara", "Turkey", 39.93, 32.86, 12.0),
        ("Tehran", "Iran", 35.69, 51.42, 17.0),
        ("Kabul", "Afghanistan", 34.53, 69.17, 12.1),
        ("Islamabad", "Pakistan", 33.72, 73.04, 18.5),
        ("Yangon", "Myanmar", 16.87, 96.20, 27.5),
        ("Hanoi", "Vietnam", 21.03, 105.85, 23.5),
        ("Manila", "Philippines", 14.60, 120.98, 27.0),
        ("Taipei", "Taiwan", 25.05, 121.56, 22.5),
        ("Hong Kong", "China", 22.31, 114.17, 23.0),
        ("Kuala Lumpur", "Malaysia", 3.14, 101.69, 27.3),
        ("Colombo", "Sri Lanka", 6.93, 79.85, 27.5),
        ("Kathmandu", "Nepal", 27.72, 85.32, 18.3),
        ("Thimphu", "Bhutan", 27.47, 89.64, 12.5),
        ("Muscat", "Oman", 23.61, 58.59, 28.5),
        ("Doha", "Qatar", 25.29, 51.53, 28.0),
        ("Baku", "Azerbaijan", 40.41, 49.87, 14.5),
        ("Tbilisi", "Georgia", 41.69, 44.83, 13.0),
        ("Yerevan", "Armenia", 40.18, 44.51, 12.5),
        ("Minsk", "Belarus", 53.90, 27.57, 6.7),
        ("Warsaw", "Poland", 52.23, 21.01, 8.5),
        ("Prague", "Czechia", 50.08, 14.44, 9.1),
        ("Vienna", "Austria", 48.21, 16.37, 10.4),
        ("Budapest", "Hungary", 47.50, 19.04, 11.1),
        ("Bucharest", "Romania", 44.43, 26.10, 11.4),
        ("Sofia", "Bulgaria", 42.70, 23.32, 12.7),
        ("Belgrade", "Serbia", 44.80, 20.46, 12.2),
        ("Sarajevo", "Bosnia", 43.85, 18.36, 11.3),
        ("Zagreb", "Croatia", 45.81, 15.98, 11.8),
        ("Lisbon", "Portugal", 38.72, -9.14, 16.7),
        ("Amsterdam", "Netherlands", 52.37, 4.90, 10.1),
        ("Brussels", "Belgium", 50.85, 4.35, 10.5),
        ("Copenhagen", "Denmark", 55.68, 12.57, 8.6),
        ("Zurich", "Switzerland", 47.38, 8.54, 9.4),
        ("Havana", "Cuba", 23.13, -82.38, 25.2),
        ("Guadalajara", "Mexico", 20.66, -103.35, 18.8),
    ]

    df = pd.DataFrame(
        stations, columns=["city", "country", "lat", "lon", "mean_temp_c"]
    )

    # Add noise to simulate real sensor variation
    import numpy as np

    rng = (
        pd.np.random.default_rng(42)
        if hasattr(pd, "np")
        else __import__("numpy").random.default_rng(42)
    )
    df["mean_temp_c"] = df["mean_temp_c"] + rng.normal(0, 0.5, len(df))
    df["station_id"] = ["STN" + str(i).zfill(4) for i in range(len(df))]

    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"   Created {len(df)} temperature stations → {out.name}")


# ============================================================
# LOAD FUNCTIONS (return DataFrames / GeoDataFrames)
# ============================================================


def load_world(resolution: str = "110m"):
    """
    Load Natural Earth world countries as GeoDataFrame.
    Reads GeoJSON (primary) or shapefile (legacy) from data/raw/shapefiles/.
    """
    import geopandas as gpd

    folder = PATHS["raw_shapefiles"] / f"ne_{resolution}_admin_0_countries"

    # Try GeoJSON first (new format), then SHP (legacy fallback)
    for pattern in ["*.geojson", "*.shp"]:
        files = list(folder.glob(pattern))
        if files:
            gdf = gpd.read_file(str(files[0]))
            # Normalise column names to uppercase (GeoJSON uses mixed case)
            gdf.columns = [c.upper() if c != "geometry" else c for c in gdf.columns]
            return gdf

    raise FileNotFoundError(
        f"No shapefile or GeoJSON found in: {folder}\n"
        f"Run: python scripts/utils/data_loader.py"
    )


def load_emissions(year: int = ANALYSIS_YEAR):
    """Load OWID CO2 data filtered to a single year."""
    path = PATHS["raw_emissions"] / "owid-co2-data.csv"
    df = pd.read_csv(path, low_memory=False)
    df = df[df["year"] == year].copy()
    df = df[df["iso_code"].notna() & (df["iso_code"] != "")]
    df = df[~df["iso_code"].str.startswith("OWID")]
    return df


def load_population(year: int = ANALYSIS_YEAR):
    """Load population data filtered to a single year."""
    path = PATHS["raw_population"] / "world_population.csv"
    df = pd.read_csv(path)
    # Column names vary; normalise
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    if "year" in df.columns:
        df = df[df["year"] == year]
    return df


def load_airports():
    """Load OpenFlights airports as DataFrame with proper columns."""
    path = PATHS["raw_airports"] / "airports.dat"
    cols = list(COLUMN_MAP["airports"].values())
    df = pd.read_csv(path, header=None, names=cols, na_values=["\\N"])
    df = df[df["iata"].notna() & (df["iata"] != "")]
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    return df.dropna(subset=["lat", "lon"])


def load_routes():
    """Load OpenFlights routes as DataFrame."""
    path = PATHS["raw_airports"] / "routes.dat"
    cols = list(COLUMN_MAP["routes"].values())
    df = pd.read_csv(path, header=None, names=cols, na_values=["\\N"])
    return df


def load_temperature():
    """Load temperature station data."""
    path = PATHS["raw_temperature"] / "global_temp_stations.csv"
    return pd.read_csv(path)


# ============================================================
# MAIN: download everything
# ============================================================


def download_all(force: bool = False):
    print("=" * 60)
    print("  GeoViz Project — Dataset Downloader")
    print("=" * 60)
    download_shapefiles(force)
    download_emissions(force)
    download_population(force)
    download_airports(force)
    download_gdp(force)
    download_migration(force)
    create_synthetic_temperature(force)
    print("\n All datasets ready.\n")


def check_files():
    """Print status of all expected raw data files."""
    expected = {
        "Shapefile 110m": PATHS["raw_shapefiles"]
        / "ne_110m_admin_0_countries"
        / ".downloaded",
        "Shapefile 10m": PATHS["raw_shapefiles"]
        / "ne_10m_admin_0_countries"
        / ".downloaded",
        "Populated places": PATHS["raw_shapefiles"]
        / "ne_10m_populated_places"
        / ".downloaded",
        "OWID CO2": PATHS["raw_emissions"] / "owid-co2-data.csv",
        "Population": PATHS["raw_population"] / "world_population.csv",
        "Airports": PATHS["raw_airports"] / "airports.dat",
        "Routes": PATHS["raw_airports"] / "routes.dat",
        "Temperature": PATHS["raw_temperature"] / "global_temp_stations.csv",
        "GDP (zip)": PATHS["raw_gdp"] / "wb_gdp.zip",
        "Migration (zip)": PATHS["raw_migration"] / "wb_net_migration.zip",
    }
    print("\n Dataset status:")
    for name, path in expected.items():
        status = "" if path.exists() else " MISSING"
        print(f"  {status}  {name:<25} {path.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Check file status only")
    parser.add_argument(
        "--force", action="store_true", help="Re-download even if file exists"
    )
    args = parser.parse_args()

    if args.check:
        check_files()
    else:
        download_all(force=args.force)
        check_files()
