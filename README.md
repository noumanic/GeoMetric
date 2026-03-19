# 🌍 GeoMetric Project - Global Climate & Mobility Atlas

A comprehensive geospatial data visualization assignment covering 7 mapping
techniques plus bonus interactive features. Built with Python, GeoPandas,
Matplotlib, Folium, Plotly, and Dash.

---

## 📁 Project Structure

```
GeoMetric/
│
├── data/
│   ├── raw/
│   │   ├── shapefiles/          # Natural Earth country polygons + city points
│   │   ├── emissions/           # OWID CO₂ & greenhouse gas data
│   │   ├── population/          # World Bank population time series
│   │   ├── airports/            # OpenFlights airports.dat + routes.dat
│   │   ├── temperature/         # Global temperature station data
│   │   ├── migration/           # UN/World Bank net migration data
│   │   └── gdp/                 # World Bank GDP data
│   ├── processed/               # Cleaned, joined GeoDataFrames (auto-generated)
│   └── cache/                   # Temporary download cache
│
├── notebooks/                   # Jupyter notebooks (one per part)
│
├── scripts/
│   ├── utils/
│   │   ├── config.py            # ★ Central config: paths, projections, styles
│   │   ├── data_loader.py       # Download + load all datasets
│   │   ├── preprocess.py        # Clean, join, build master GeoDataFrame
│   │   └── map_utils.py         # Reusable map helper functions
│   ├── parts/
│   │   ├── part1_projections.py # 3 projections + comparison table
│   │   ├── part2_choropleth.py  # 2 choropleths + classification critique
│   │   ├── part3_proportional.py# Static + interactive proportional symbol maps
│   │   ├── part4_flow.py        # Flow map + NetworkX analysis
│   │   ├── part5_contour.py     # Temperature interpolation + isopleth map
│   │   ├── part6_cartogram.py   # Geographic vs Dorling cartogram
│   │   └── part7_scenarios.py   # 3 case-based scenarios (A, B, C)
│   └── bonus/
│       ├── bonus_dashboard.py   # Plotly Dash multi-tab dashboard
│       ├── bonus_animation.py   # Animated temporal choropleth (1990→2020)
│       └── bonus_morans_i.py    # Spatial autocorrelation (Moran's I + LISA)
│
├── outputs/
│   ├── figures/
│   │   ├── part1_projections/
│   │   ├── part2_choropleth/
│   │   ├── part3_proportional/
│   │   ├── part4_flow/
│   │   ├── part5_contour/
│   │   ├── part6_cartogram/
│   │   ├── part7_scenarios/
│   │   └── bonus/
│   └── interactive/
│       ├── dashboards/
│       ├── folium_maps/
│       └── animations/
│
├── report/
│   ├── assets/                  # Images embedded in report
│   ├── drafts/                  # Work-in-progress report sections
│   └── report.pdf               # Final compiled report
│
├── tests/                       # Unit tests
├── docs/                        # Additional documentation
├── run_all.py                   # ★ Master pipeline runner
├── requirements.txt             # All Python dependencies
└── README.md                    # This file
```

---

## 🚀 Quick Start

### 1. Clone / set up environment

```bash
# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note for Windows users:** Installing `cartopy` via pip can fail.
> Use conda instead:
> ```bash
> conda install -c conda-forge cartopy geopandas pysal
> pip install -r requirements.txt
> ```

### 3. Download all datasets (one time)

```bash
python scripts/utils/data_loader.py
```

### 4. Preprocess data

```bash
python scripts/utils/preprocess.py
```

### 5. Run all parts

```bash
python run_all.py
```

### 6. Run a single part

```bash
python scripts/parts/part1_projections.py
python scripts/parts/part2_choropleth.py
# ... etc
```

### 7. Launch the interactive dashboard (Bonus)

```bash
python scripts/bonus/bonus_dashboard.py
# Open http://127.0.0.1:8050
```

---

## ⚡ Pipeline Commands

| Command | Description |
|---|---|
| `python run_all.py` | Run complete pipeline |
| `python run_all.py --parts 1 2 3` | Run specific parts only |
| `python run_all.py --skip-download` | Skip download (data already present) |
| `python run_all.py --skip-preprocess` | Skip preprocessing |
| `python run_all.py --bonus` | Also run all bonus scripts |
| `python run_all.py --draft` | Fast 150-DPI draft mode |
| `python run_all.py --bonus --skip-download --skip-preprocess` | Bonus only |

---

## 📊 Parts Overview

| Part | Topic | Map Types | Key Libraries |
|---|---|---|---|
| 1 | Projections | 3 world maps | geopandas, matplotlib |
| 2 | Choropleth | 2 classification schemes | mapclassify, geopandas |
| 3 | Proportional Symbols | Static + interactive | matplotlib, folium |
| 4 | Flow Map | Route flows + network | networkx, matplotlib |
| 5 | Contour/Isopleth | Interpolated surface | scipy, matplotlib |
| 6 | Cartogram | Geographic vs Dorling | matplotlib, geopandas |
| 7 | Scenarios | Bivariate + choropleth | matplotlib, scipy |
| ★ | Dashboard | Multi-tab interactive | plotly, dash |
| ★ | Animation | Temporal choropleth | plotly |
| ★ | Moran's I | Spatial autocorrelation | pysal, esda |

---

## 🗂️ Datasets Used

| Dataset | Source | Format | Used In |
|---|---|---|---|
| World Countries (110m) | Natural Earth | Shapefile | Parts 1,2,3,6,7 |
| World Countries (10m) | Natural Earth | Shapefile | Parts 5,7 |
| Populated Places | Natural Earth | Shapefile | Part 3 |
| CO₂ & GHG Emissions | Our World in Data | CSV | Parts 1,2,6,7,★ |
| World Population | World Bank | CSV | Parts 2,6,7 |
| Global Airports | OpenFlights | DAT | Parts 3,4,7 |
| Airline Routes | OpenFlights | DAT | Part 4,★ |
| Temperature Stations | Berkeley Earth / Synthetic | CSV | Parts 5,7 |
| Net Migration | World Bank | ZIP/CSV | Part 4 |
| GDP by Country | World Bank | ZIP/CSV | Part 6,7 |

---

## ✅ Minimum Technical Requirements Checklist

- [x] Read **4+ different spatial datasets** (shapefile, CSV airports, CSV emissions, CSV temperature)
- [x] Perform **2+ dataset joins** (world + emissions in `preprocess.py`; world + population)
- [x] Handle **2+ geometry types** (Polygon countries + Point airports/stations)
- [x] **Reproject data 3+ times** (Albers, Lambert, Winkel Tripel, Robinson in Parts 1–6)
- [x] Create **6+ distinct maps** (3 in Part 1 alone + 2 per subsequent part)
- [x] **Save high-resolution outputs** (300 DPI via `save_figure()`)
- [x] Every map has **legend, title, source label, projection note**
- [x] **Assumptions and limitations** documented in each part's `.txt` output

---

## ⭐ Bonus Features

| Feature | Script | Output |
|---|---|---|
| Interactive multi-tab dashboard | `bonus_dashboard.py` | Dash app at localhost:8050 |
| Hover tooltips | All Folium + Plotly maps | `.html` files |
| Animated temporal choropleth | `bonus_animation.py` | `co2_animation.html` |
| Spatial autocorrelation (Moran's I) | `bonus_morans_i.py` | LISA cluster map + scatter plot |
| Network centrality analysis | `part4_flow.py` | NetworkX summary table |
| Multiple basemap projections | `part1_projections.py` | 3 projection maps |

---

## 🐛 Troubleshooting

**PROJ/pyproj errors on Windows:**
```bash
conda install -c conda-forge proj pyproj
```

**`cartopy` import error:**
```bash
conda install -c conda-forge cartopy
```

**`fiona` error reading shapefiles:**
```bash
pip install fiona --upgrade
```

**Shapefile not found after download:**
Check `data/raw/shapefiles/` — the `.downloaded` marker file should be present.
Re-run: `python scripts/utils/data_loader.py --force`

**Dashboard not loading:**
Ensure port 8050 is free. Change port in `bonus_dashboard.py`:
```python
app.run(debug=True, port=8051)
```

---

## 📝 Report Structure

The final report (`report/report.pdf`) should follow this structure:

1. **Introduction** — dataset selection rationale
2. **Part 1** — projection maps + comparison table + discussion
3. **Part 2** — choropleth maps + classification comparison + critique
4. **Part 3** — proportional symbol maps + comparison paragraph
5. **Part 4** — flow map + network summary + interpretation
6. **Part 5** — point map + contour map + interpolation discussion
7. **Part 6** — geographic map + cartogram + 1-page critique
8. **Part 7** — three scenarios with design justifications
9. **Bonus** — dashboard screenshots + animation + Moran's I results
10. **Conclusion** — overall lessons learned
11. **References** — data sources with URLs

---

## 📜 Data Licenses

| Dataset | License |
|---|---|
| Natural Earth | Public Domain |
| Our World in Data | CC BY 4.0 |
| World Bank | CC BY 4.0 |
| OpenFlights | Open Database License (ODbL) |
| Berkeley Earth | CC BY 4.0 (non-commercial) |

---

## 👤 Author

*[Muhammad Nouman Hafeez]*
*[Data Visualization / FAST-NUCES Islamabad]*