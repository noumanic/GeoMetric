"""
tests/test_config.py
====================
Unit tests for config and utility functions.

Run with: pytest tests/
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
import pandas as pd

# ─── Config tests ───────────────────────────────────────────


def test_config_imports():
    from scripts.utils.config import PATHS, PROJECTIONS, STYLE, DATASETS

    assert isinstance(PATHS, dict)
    assert isinstance(PROJECTIONS, dict)
    assert isinstance(STYLE, dict)
    assert isinstance(DATASETS, dict)


def test_all_paths_are_path_objects():
    from scripts.utils.config import PATHS

    for key, val in PATHS.items():
        assert isinstance(val, Path), f"PATHS['{key}'] is not a Path object"


def test_required_projections_present():
    from scripts.utils.config import PROJECTIONS

    required = [
        "albers_equal_area",
        "lambert_conformal_conic",
        "winkel_tripel",
        "wgs84",
        "robinson",
    ]
    for proj in required:
        assert proj in PROJECTIONS, f"Missing projection: {proj}"


def test_required_datasets_present():
    from scripts.utils.config import DATASETS

    required = [
        "shapefile_110m",
        "owid_co2",
        "population_csv",
        "airports_dat",
        "routes_dat",
    ]
    for ds in required:
        assert ds in DATASETS, f"Missing dataset key: {ds}"
        assert DATASETS[ds].startswith("http"), f"Dataset URL invalid: {ds}"


def test_style_has_required_keys():
    from scripts.utils.config import STYLE

    required = [
        "fig_size_world",
        "dpi_final",
        "sequential_palette",
        "boundary_color",
        "ocean_color",
        "source_template",
    ]
    for key in required:
        assert key in STYLE, f"Missing STYLE key: {key}"


# ─── map_utils tests ────────────────────────────────────────


def test_scale_symbols_area():
    from scripts.utils.map_utils import scale_symbols

    values = pd.Series([1, 10, 100, 1000])
    sizes = scale_symbols(values, min_size=10, max_size=1000, method="area")
    assert len(sizes) == 4
    # Must be monotonically increasing
    assert all(sizes[i] <= sizes[i + 1] for i in range(len(sizes) - 1))
    # Must be within bounds
    assert sizes.min() >= 10
    assert sizes.max() <= 1000


def test_scale_symbols_no_negatives():
    from scripts.utils.map_utils import scale_symbols

    values = pd.Series([0, 0, 5, 10])
    sizes = scale_symbols(values, min_size=5, max_size=500)
    assert (sizes >= 0).all()


def test_flow_linewidth_bounds():
    from scripts.utils.map_utils import flow_linewidth

    lw = flow_linewidth(50, vmin=0, vmax=100, min_lw=0.5, max_lw=6.0)
    assert 0.5 <= lw <= 6.0


def test_flow_linewidth_equal_min_max():
    from scripts.utils.map_utils import flow_linewidth

    lw = flow_linewidth(5, vmin=5, vmax=5, min_lw=0.5, max_lw=6.0)
    assert lw == 0.5  # should return min when vmin == vmax


def test_projection_comparison_table_has_3_rows():
    from scripts.utils.map_utils import projection_comparison_table

    df = projection_comparison_table()
    assert len(df) == 3
    assert "Projection" in df.columns
    assert "Preserves" in df.columns
    assert "Distorts" in df.columns
    assert "Best For" in df.columns


def test_points_to_gdf():
    from scripts.utils.map_utils import points_to_gdf

    df = pd.DataFrame(
        {
            "city": ["London", "Tokyo"],
            "lat": [51.5, 35.7],
            "lon": [-0.1, 139.7],
        }
    )
    gdf = points_to_gdf(df, lat_col="lat", lon_col="lon")
    assert len(gdf) == 2
    assert gdf.crs.to_epsg() == 4326
    assert all(not g.is_empty for g in gdf.geometry)


# ─── Data loader tests (structure only, no network) ─────────


def test_column_map_airports_has_14_entries():
    from scripts.utils.config import COLUMN_MAP

    assert len(COLUMN_MAP["airports"]) == 14


def test_column_map_routes_has_9_entries():
    from scripts.utils.config import COLUMN_MAP

    assert len(COLUMN_MAP["routes"]) == 9


# ─── Preprocessing tests (if processed data exists) ─────────


def test_processed_master_has_geometry(tmp_path):
    """Only runs if master_world.gpkg has been generated."""
    import geopandas as gpd
    from scripts.utils.config import PATHS

    master_path = PATHS["processed"] / "master_world.gpkg"
    if not master_path.exists():
        pytest.skip("Processed data not yet generated — run preprocess.py first")
    master = gpd.read_file(master_path)
    assert "geometry" in master.columns
    assert len(master) > 150  # at least 150 countries
    assert master.crs is not None


def test_processed_master_has_key_columns():
    import geopandas as gpd
    from scripts.utils.config import PATHS

    master_path = PATHS["processed"] / "master_world.gpkg"
    if not master_path.exists():
        pytest.skip("Processed data not yet generated")
    master = gpd.read_file(master_path)
    for col in ["iso_a3", "country_name", "co2_per_capita", "pop_final", "area_km2"]:
        assert col in master.columns, f"Missing column: {col}"


def test_airports_clean_has_coordinates():
    import pandas as pd
    from scripts.utils.config import PATHS

    ap_path = PATHS["processed"] / "airports_clean.csv"
    if not ap_path.exists():
        pytest.skip("airports_clean.csv not yet generated")
    ap = pd.read_csv(ap_path)
    assert ap["lat"].notna().all()
    assert ap["lon"].notna().all()
    assert ap["lat"].between(-90, 90).all()
    assert ap["lon"].between(-180, 180).all()


def test_temperature_stations_in_range():
    import pandas as pd
    from scripts.utils.config import PATHS

    tmp_path = PATHS["processed"] / "temperature_stations.csv"
    if not tmp_path.exists():
        pytest.skip("temperature_stations.csv not yet generated")
    df = pd.read_csv(tmp_path)
    assert (
        df["mean_temp_c"].between(-80, 60).all()
    ), "Temperature values out of plausible range"
    assert df["lat"].between(-90, 90).all()
    assert df["lon"].between(-180, 180).all()
