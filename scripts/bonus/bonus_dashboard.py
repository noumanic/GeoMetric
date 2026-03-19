"""
bonus_dashboard.py
==================
BONUS – Interactive Plotly Dash Dashboard

A multi-tab dashboard combining all datasets with:
  - Tab 1: World choropleth with dropdown variable selector
  - Tab 2: Proportional symbol map (airports)
  - Tab 3: Flow network (top routes)
  - Tab 4: Temperature surface
  - Hover tooltips on all maps

Usage:
    python scripts/bonus/bonus_dashboard.py
    Then open http://127.0.0.1:8050 in your browser.
"""

import sys, warnings

warnings.filterwarnings("ignore")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import numpy as np
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc

from scripts.utils.config import PATHS

# ─── LOAD DATA ────────────────────────────────────────────


def load_all():
    """
    Load all required datasets for the interactive dashboard.

    Returns:
        tuple[gpd.GeoDataFrame, dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]: 
            WGS84 geometries, WGS84 geojson dictionary, airport traffic data, 
            route network data, and temperature points data.
    """
    world = gpd.read_file(PATHS["processed"] / "master_world.gpkg")
    airports = pd.read_csv(PATHS["processed"] / "airports_clean.csv")
    routes = pd.read_csv(PATHS["processed"] / "routes_clean.csv")
    temps = pd.read_csv(PATHS["processed"] / "temperature_stations.csv")

    # Convert world to WGS84 for Plotly
    world_wgs = world.to_crs("EPSG:4326") if world.crs.to_epsg() != 4326 else world
    world_json = world_wgs.__geo_interface__

    return world_wgs, world_json, airports, routes, temps


# ─── CHOROPLETH FIGURE ────────────────────────────────────


def make_choropleth_fig(world_wgs, world_json, variable, title):
    """
    Generate an interactive Plotly choropleth figure with hover tooltips.

    Args:
        world_wgs (gpd.GeoDataFrame): WGS-projected world geometries.
        world_json (dict): GeoJSON representation of the world geometries.
        variable (str): Column name representing the variable to plot.
        title (str): The display title for the map.

    Returns:
        go.Figure: A Plotly Express choropleth map object.
    """
    df = (
        world_wgs[["iso_a3", "country_name", "continent", variable]]
        .dropna(subset=[variable])
        .copy()
    )

    fig = px.choropleth(
        df,
        geojson=world_json,
        locations="iso_a3",
        featureidkey="properties.iso_a3",
        color=variable,
        color_continuous_scale="YlOrRd",
        hover_name="country_name",
        hover_data={
            "iso_a3": False,
            "continent": True,
            variable: ":.2f",
        },
        title=title,
        labels={variable: variable.replace("_", " ").title()},
    )
    fig.update_geos(
        showcoastlines=True,
        coastlinecolor="white",
        showland=True,
        landcolor="#f5f5f0",
        showocean=True,
        oceancolor="#cfe2f3",
        projection_type="natural earth",
    )
    fig.update_layout(
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        height=500,
        paper_bgcolor="#fafafa",
    )
    return fig


# ─── AIRPORT BUBBLE MAP ───────────────────────────────────


def make_airport_fig(airports):
    """
    Generate an interactive Plotly bubble map of global airport traffic.

    Args:
        airports (pd.DataFrame): Dataframe containing airports and traffic metrics.

    Returns:
        go.Figure: A Plotly Express scatter_geo map object.
    """
    top = airports.nlargest(400, "total_routes").dropna(subset=["lat", "lon"])

    fig = px.scatter_geo(
        top,
        lat="lat",
        lon="lon",
        size="total_routes",
        color="total_routes",
        color_continuous_scale="plasma",
        hover_name="name",
        hover_data={
            "city": True,
            "country": True,
            "iata": True,
            "total_routes": True,
            "departures": True,
            "arrivals": True,
            "lat": False,
            "lon": False,
        },
        size_max=30,
        title="Global Airport Traffic — Proportional Bubbles",
        projection="natural earth",
    )
    fig.update_layout(
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        height=500,
        coloraxis_colorbar_title="Routes",
        paper_bgcolor="#fafafa",
    )
    return fig


# ─── FLOW MAP FIGURE ──────────────────────────────────────


def make_flow_fig(routes, airports):
    """
    Generate an interactive Plotly line map of top aviation route flows.

    Args:
        routes (pd.DataFrame): Network edges representing routes between airports.
        airports (pd.DataFrame): Network nodes for airport coordinates.

    Returns:
        go.Figure: A Plotly graph_objects Figure containing route lines.
    """
    ap_coords = airports.set_index("iata")[["lat", "lon", "city", "country"]].to_dict(
        "index"
    )

    routes = routes.copy()
    routes["src_lat"] = routes["src_iata"].map(
        lambda x: ap_coords.get(x, {}).get("lat")
    )
    routes["src_lon"] = routes["src_iata"].map(
        lambda x: ap_coords.get(x, {}).get("lon")
    )
    routes["dst_lat"] = routes["dst_iata"].map(
        lambda x: ap_coords.get(x, {}).get("lat")
    )
    routes["dst_lon"] = routes["dst_iata"].map(
        lambda x: ap_coords.get(x, {}).get("lon")
    )

    # Aggregate to pairs
    routes["pair"] = routes.apply(
        lambda r: tuple(sorted([r["src_iata"], r["dst_iata"]])), axis=1
    )
    flows = routes.groupby("pair").size().reset_index(name="n")
    flows[["src", "dst"]] = pd.DataFrame(flows["pair"].tolist(), index=flows.index)
    top = flows.nlargest(30, "n")

    fig = go.Figure()

    max_n = top["n"].max()
    for _, row in top.iterrows():
        src_info = ap_coords.get(row["src"], {})
        dst_info = ap_coords.get(row["dst"], {})
        if not src_info or not dst_info:
            continue
        width = 0.5 + (row["n"] / max_n) * 4

        fig.add_trace(
            go.Scattergeo(
                lon=[src_info["lon"], dst_info["lon"], None],
                lat=[src_info["lat"], dst_info["lat"], None],
                mode="lines",
                line=dict(width=width, color="#2166ac"),
                opacity=0.5,
                hoverinfo="text",
                text=f"{row['src']}  {row['dst']}: {row['n']} routes",
                showlegend=False,
            )
        )

    fig.update_layout(
        title="Top 30 Global Airline Routes",
        showlegend=False,
        geo=dict(
            showland=True,
            landcolor="#f5f5f0",
            showocean=True,
            oceancolor="#cfe2f3",
            showcoastlines=True,
            coastlinecolor="white",
            projection_type="natural earth",
        ),
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        height=500,
        paper_bgcolor="#fafafa",
    )
    return fig


# ─── TEMPERATURE SCATTER MAP ──────────────────────────────


def make_temp_fig(temps):
    """
    Generate an interactive Plotly scatter map of global temperature stations.

    Args:
        temps (pd.DataFrame): Station coordinates and temperature values.

    Returns:
        go.Figure: A Plotly Express scatter_geo map object.
    """
    fig = px.scatter_geo(
        temps,
        lat="lat",
        lon="lon",
        color="mean_temp_c",
        color_continuous_scale="RdYlBu_r",
        color_continuous_midpoint=15,
        hover_name="city",
        hover_data={
            "country": True,
            "mean_temp_c": ":.1f",
            "lat": ":.2f",
            "lon": ":.2f",
        },
        title="Global Temperature Stations",
        projection="natural earth",
    )
    fig.update_traces(marker=dict(size=8, opacity=0.8))
    fig.update_layout(
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        height=500,
        coloraxis_colorbar_title="Temp (°C)",
        paper_bgcolor="#fafafa",
    )
    return fig


# ─── DASH APP LAYOUT ──────────────────────────────────────


def build_app():
    """
    Construct the Dash application layout and attach interactive callbacks.

    Returns:
        Dash: The configured Dash application instance.
    """
    world_wgs, world_json, airports, routes, temps = load_all()

    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.FLATLY],
        title="GeoViz Dashboard",
    )

    CHOROPLETH_VARS = {
        "co2_per_capita": "CO₂ per Capita (tonnes)",
        "co2_total": "Total CO₂ (million tonnes)",
        "total_ghg": "Total GHG Emissions",
        "pop_density": "Population Density (per km²)",
        "gdp_per_capita": "GDP per Capita (USD)",
        "area_km2": "Country Area (km²)",
    }
    available_vars = [v for v in CHOROPLETH_VARS if v in world_wgs.columns]

    app.layout = dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.H1(
                            " GeoViz Project Dashboard",
                            className="text-primary fw-bold my-3",
                        ),
                        width=10,
                    ),
                    dbc.Col(
                        html.P(
                            "Global Climate & Mobility Atlas",
                            className="text-muted mt-4",
                        ),
                        width=2,
                    ),
                ]
            ),
            dbc.Tabs(
                [
                    # ── Tab 1: World Choropleth ──────────────────
                    dbc.Tab(
                        label=" World Choropleth",
                        children=[
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Label(
                                                "Select Variable:",
                                                className="fw-bold mt-3",
                                            ),
                                            dcc.Dropdown(
                                                id="choropleth-var",
                                                options=[
                                                    {"label": v, "value": k}
                                                    for k, v in CHOROPLETH_VARS.items()
                                                    if k in available_vars
                                                ],
                                                value=(
                                                    available_vars[0]
                                                    if available_vars
                                                    else "co2_per_capita"
                                                ),
                                                clearable=False,
                                            ),
                                        ],
                                        width=4,
                                    ),
                                ]
                            ),
                            dcc.Graph(id="choropleth-map"),
                            html.P(
                                " Hover over any country for details. Use dropdown to change the variable.",
                                className="text-muted small",
                            ),
                        ],
                    ),
                    # ── Tab 2: Airport Traffic ───────────────────
                    dbc.Tab(
                        label=" Airport Traffic",
                        children=[
                            dcc.Graph(figure=make_airport_fig(airports)),
                            html.P(
                                " Bubble size and colour proportional to number of routes. Hover for airport details.",
                                className="text-muted small",
                            ),
                        ],
                    ),
                    # ── Tab 3: Flow Map ──────────────────────────
                    dbc.Tab(
                        label=" Route Flows",
                        children=[
                            dcc.Graph(figure=make_flow_fig(routes, airports)),
                            html.P(
                                " Line width proportional to number of routes between airport pair.",
                                className="text-muted small",
                            ),
                        ],
                    ),
                    # ── Tab 4: Temperature ───────────────────────
                    dbc.Tab(
                        label=" Temperature",
                        children=[
                            dcc.Graph(figure=make_temp_fig(temps)),
                            html.P(
                                " Each dot is a monitoring station. Colour = mean annual temperature.",
                                className="text-muted small",
                            ),
                        ],
                    ),
                ]
            ),
            html.Hr(),
            html.Footer(
                [
                    html.P(
                        "GeoViz Project | Data: OWID, Natural Earth, OpenFlights, Berkeley Earth",
                        className="text-muted small text-center",
                    ),
                ]
            ),
        ],
        fluid=True,
    )

    # ── Callback: update choropleth ──────────────────────
    @app.callback(
        Output("choropleth-map", "figure"),
        Input("choropleth-var", "value"),
    )
    def update_choropleth(variable):
        title = CHOROPLETH_VARS.get(variable, variable)
        return make_choropleth_fig(world_wgs, world_json, variable, title)

    return app


def run():
    print("=" * 60)
    print("  BONUS — Interactive Dashboard")
    print("=" * 60)
    app = build_app()
    print("\n Starting dashboard at http://127.0.0.1:8050")
    print("   Press Ctrl+C to stop.\n")
    app.run(debug=True, host="127.0.0.1", port=8050)


if __name__ == "__main__":
    run()
