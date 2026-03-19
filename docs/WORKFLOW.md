# Workflow Guide — GeoViz Project

This document explains the complete data flow from raw download through to
final figures. Read this before modifying any script.

---

## Data Flow Diagram

```
Internet sources
      │
      ▼
data_loader.py ──────────────────────────────────────────────┐
      │                                                       │
      │  Downloads to data/raw/                              │
      │  ├── shapefiles/   (Natural Earth ZIPs → extracted)  │
      │  ├── emissions/    (OWID CSV)                        │
      │  ├── population/   (World Bank CSV)                  │
      │  ├── airports/     (OpenFlights DAT files)           │
      │  ├── temperature/  (Synthetic CSV, created locally)  │
      │  ├── migration/    (World Bank ZIP)                   │
      │  └── gdp/          (World Bank ZIP)                  │
      │                                                       │
      ▼                                                       │
preprocess.py                                                 │
      │                                                       │
      │  Saves to data/processed/                            │
      │  ├── world_countries.gpkg    (cleaned shapefile)     │
      │  ├── emissions_2020.csv      (filtered + renamed)    │
      │  ├── population_2020.csv     (filtered)              │
      │  ├── airports_clean.csv      (with route counts)     │
      │  ├── routes_clean.csv        (with coordinates)      │
      │  ├── temperature_stations.csv                        │
      │  └── master_world.gpkg       (joined: world+emiss+pop)│
      │                                                       │
      ▼                                                       │
Part scripts (scripts/parts/)                                 │
      │                                                       │
      │  All parts import from data/processed/               │
      │  All parts call map_utils.py helpers                 │
      │  All parts call config.py for paths/styles           │
      │                                                       │
      ▼                                                       │
outputs/figures/part*/    ← static PNG maps (300 DPI)        │
outputs/interactive/      ← HTML files (Folium, Plotly)      │
      │                                                       │
      ▼                                                       │
report/report.pdf         ← final compiled report            │
```

---

## Config System

`scripts/utils/config.py` is the single source of truth for:

- **PATHS**: all directory paths (absolute, derived from project root)
- **PROJECTIONS**: CRS strings for all projections used
- **STYLE**: figure sizes, DPI, colours, fonts, line widths
- **DATASETS**: download URLs for all raw data
- **COLUMN_MAP**: column name standardisation after loading
- **FLOW / INTERPOLATION / CLASSIFICATION**: per-part tuning parameters

**Never hardcode paths or style values in part scripts.**
Always import from `config.py`.

### Changing output DPI

```python
# In config.py:
STYLE["dpi_final"] = 300    # production
STYLE["dpi_draft"] = 150    # drafting

# Or via CLI:
python run_all.py --draft   # forces 150 DPI
```

### Changing the analysis year

```python
# In config.py:
ANALYSIS_YEAR = 2019   # change from 2020 to any year with OWID data
```

---

## Adding a New Part

1. Create `scripts/parts/partN_name.py`
2. Include a `run()` function at module level
3. Import from `config.py` and `map_utils.py`
4. Save outputs to `PATHS["fig_partN"]`
5. Add to `PARTS` dict in `run_all.py`
6. Add tests in `tests/`

Template:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.utils.config import PATHS, STYLE
from scripts.utils.map_utils import save_figure, add_map_annotations

def run():
    PATHS["fig_partN"].mkdir(parents=True, exist_ok=True)
    # ... your code ...

if __name__ == "__main__":
    run()
```

---

## Reprojection Convention

Always reproject using `map_utils.reproject_gdf()`, not raw `.to_crs()` calls,
so that reprojections are logged consistently.

```python
from scripts.utils.map_utils import reproject_gdf
from scripts.utils.config import PROJECTIONS

# Named projection from config
gdf_proj = reproject_gdf(gdf, "albers_equal_area")

# EPSG code
gdf_wgs  = reproject_gdf(gdf, "EPSG:4326")
```

Projections used per part:

| Part | Projection(s) |
|---|---|
| Part 1 | Albers, Lambert, Winkel Tripel |
| Part 2 | Albers Equal-Area |
| Part 3 | Robinson (static), WGS84 (Folium) |
| Part 4 | Robinson (static), WGS84 (Folium) |
| Part 5 | WGS84 (interpolation grid) |
| Part 6 | Robinson (both maps) |
| Part 7 | Robinson (A, B), WGS84 (C bivariate) |

---

## Saving Figures Convention

Always use `map_utils.save_figure()` rather than `fig.savefig()` directly:

```python
from scripts.utils.map_utils import save_figure
from scripts.utils.config import PATHS

save_figure(fig, PATHS["fig_part1"] / "my_map.png")              # 300 DPI
save_figure(fig, PATHS["fig_part1"] / "my_map.png", draft=True)  # 150 DPI
```

This ensures consistent DPI, white background, and tight bounding box.

---

## Interactive Maps Convention

- **Folium maps** → save to `PATHS["interactive_folium"] / "name.html"`
- **Plotly HTML** → save with `fig.write_html(str(out), include_plotlyjs="cdn")`
- **Dash app** → runs live, no file saved (screenshots taken manually for report)

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_config.py -v

# Run only tests that don't require downloaded data
pytest tests/ -v -k "not processed"
```

Tests are designed to:
- Pass without downloaded data (skip gracefully if data missing)
- Validate config structure and utility functions
- Validate processed data shape and ranges once data is present

---

## Common Issues & Fixes

### Shapefile CRS is None
```python
gdf = gdf.set_crs("EPSG:4326", allow_override=True)
```

### Invalid geometries causing join failures
```python
gdf["geometry"] = gdf["geometry"].buffer(0)
```

### Missing ISO codes after join
Natural Earth uses `-99` for disputed territories. These are filtered in
`preprocess.py`. If you need them, remove the filter line.

### Memory issues with 10m shapefile
Use the 110m version for world maps. Only use 10m for regional zooms.

### Cartopy projection not found
Some projections (Winkel Tripel) require Cartopy to be built with PROJ 6+.
Check: `python -c "import cartopy; print(cartopy.__version__)"`
Required: 0.20+

---

## Output Quality Checklist

Before submitting, verify every map has:

- [ ] **Title** (descriptive, includes variable name and year)
- [ ] **Legend** (with labelled classes/units)
- [ ] **Source note** (data origin + URL if possible)
- [ ] **Projection note** (which CRS was used)
- [ ] **Missing data** shown in distinct neutral grey
- [ ] **No clipped geometries** at map edges
- [ ] **300 DPI** for all final outputs
- [ ] **Saved to correct output folder**
