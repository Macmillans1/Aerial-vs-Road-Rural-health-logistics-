"""Geospatial Map Visualizer for Rural Healthcare Logistics in Ghana.

Provides PyDeck 3D flight arcs & clinic pins and Plotly interactive geospatial maps.
Visualizes distribution hubs, clinic delivery endpoints, risk tiers, and supply corridors.
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk


# Color palettes tailored for modern dark telemetry UI
PALETTE = {
    "Optimal": [16, 185, 129, 210],       # Emerald #10B981
    "Moderate Risk": [245, 158, 11, 210], # Amber #F59E0B
    "High Risk": [239, 68, 68, 220],      # Crimson #EF4444
    "Hub": [0, 210, 186, 255],            # Cyan #00D2BA
    "Tier 1": [59, 130, 246, 210],        # Blue
    "Tier 2": [139, 92, 246, 210],        # Purple
    "Tier 3": [236, 72, 153, 210],        # Magenta
}


def build_pydeck_logistics_map(
    df_clinic_metrics: pd.DataFrame,
    df_hubs: pd.DataFrame,
    color_by: str = "risk_tier",
    show_flight_arcs: bool = True,
) -> pdk.Deck:
    """Construct an interactive PyDeck 3D map featuring distribution hubs, clinics, and flight corridors."""
    # Prepare clinic layer data
    df_clinics_map = df_clinic_metrics.copy()

    if color_by == "risk_tier":
        df_clinics_map["color"] = df_clinics_map["risk_tier"].map(
            lambda r: PALETTE.get(r, [150, 150, 150, 200])
        )
    else:  # remote_tier
        df_clinics_map["color"] = df_clinics_map["remote_tier"].map(
            lambda t: PALETTE.get(t, [150, 150, 150, 200])
        )

    # Clinic Scatterplot Layer
    clinic_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_clinics_map,
        get_position=["longitude", "latitude"],
        get_color="color",
        get_radius=6000,
        pickable=True,
        auto_highlight=True,
        radius_min_pixels=6,
        radius_max_pixels=18,
    )

    # Hubs Scatterplot Layer
    df_hubs_map = df_hubs.copy()
    df_hubs_map["color"] = [PALETTE["Hub"] for _ in range(len(df_hubs_map))]
    hub_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_hubs_map,
        get_position=["longitude", "latitude"],
        get_color="color",
        get_radius=14000,
        pickable=True,
        stroked=True,
        get_line_color=[255, 255, 255, 240],
        line_width_min_pixels=2,
        radius_min_pixels=10,
        radius_max_pixels=24,
    )

    layers = [clinic_layer, hub_layer]

    # Drone Flight Arc Layer
    if show_flight_arcs:
        # Build arc dataframe connecting nearest hub to clinics
        hubs_lookup = df_hubs.set_index("hub_id")[["latitude", "longitude", "hub_name"]].to_dict("index")
        arc_records = []
        for _, clinic in df_clinics_map.iterrows():
            # Find closest hub or default
            nearest_hub_id = clinic.get("nearest_hub", "HUB-OMN")
            if nearest_hub_id not in hubs_lookup:
                nearest_hub_id = "HUB-OMN"
            hub = hubs_lookup[nearest_hub_id]

            arc_records.append({
                "source_lon": hub["longitude"],
                "source_lat": hub["latitude"],
                "target_lon": clinic["longitude"],
                "target_lat": clinic["latitude"],
                "clinic_name": clinic["clinic_name"],
                "hub_name": hub["hub_name"],
                "otif": clinic["otif_rate_pct"],
                "color_start": [0, 210, 186, 160],
                "color_end": [236, 72, 153, 140] if clinic["risk_tier"] == "High Risk" else [16, 185, 129, 140],
            })

        df_arcs = pd.DataFrame(arc_records)

        arc_layer = pdk.Layer(
            "ArcLayer",
            data=df_arcs,
            get_source_position=["source_lon", "source_lat"],
            get_target_position=["target_lon", "target_lat"],
            get_source_color="color_start",
            get_target_color="color_end",
            get_width=2.5,
            pickable=True,
            auto_highlight=True,
        )
        layers.append(arc_layer)

    # Centered over Ghana (approx 7.9° N, -1.0° W)
    view_state = pdk.ViewState(
        latitude=7.85,
        longitude=-1.10,
        zoom=6.3,
        pitch=38,
        bearing=0,
    )

    tooltip = {
        "html": """
        <div style="background-color: #111827; color: #F3F4F6; padding: 10px 14px; border-radius: 8px; border: 1px solid #374151; font-family: sans-serif; font-size: 12px; line-height: 1.5; box-shadow: 0 8px 16px rgba(0,0,0,0.5);">
            <div style="font-weight: 700; font-size: 14px; color: #00D2BA; margin-bottom: 4px;">{clinic_name} {hub_name}</div>
            <div><b>Region:</b> {region}</div>
            <div><b>Classification:</b> {remote_tier} ({risk_tier})</div>
            <div><b>OTIF Rate:</b> <span style="color: #10B981; font-weight: 700;">{otif_rate_pct}%</span></div>
            <div><b>Avg Lead Time:</b> {avg_lead_time_hours} hrs</div>
            <div><b>Orders Logged:</b> {total_orders} (Stockouts: {stock_outs})</div>
            <div><b>Drone Utilization:</b> {drone_share_pct}%</div>
        </div>
        """,
        "style": {"backgroundColor": "transparent", "color": "white"}
    }

    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v11",
        tooltip=tooltip,
    )


def build_plotly_geographic_scatter(
    df_clinic_metrics: pd.DataFrame,
    df_hubs: pd.DataFrame,
    color_by: str = "risk_tier"
) -> go.Figure:
    """High-contrast Plotly 2D fallback map of clinics and hubs with telemetry styling."""
    fig = go.Figure()

    # Add Clinics
    color_map = {
        "Optimal": "#10B981",
        "Moderate Risk": "#F59E0B",
        "High Risk": "#EF4444",
        "Tier 1": "#3B82F6",
        "Tier 2": "#8B5CF6",
        "Tier 3": "#EC4899",
    }

    for key in df_clinic_metrics[color_by].unique():
        subset = df_clinic_metrics[df_clinic_metrics[color_by] == key]
        fig.add_trace(go.Scattergeo(
            lon=subset["longitude"],
            lat=subset["latitude"],
            text=subset["clinic_name"],
            name=f"{key}",
            mode="markers",
            marker=dict(
                size=12,
                color=color_map.get(key, "#9CA3AF"),
                opacity=0.85,
                line=dict(width=1, color="#FFFFFF"),
            ),
            customdata=subset[["region", "remote_tier", "otif_rate_pct", "avg_lead_time_hours", "total_orders", "stock_outs"]],
            hovertemplate="""
            <b>%{text}</b><br>
            Region: %{customdata[0]}<br>
            Tier: %{customdata[1]}<br>
            OTIF: %{customdata[2]}%<br>
            Avg Lead Time: %{customdata[3]} hrs<br>
            Total Orders: %{customdata[4]} (Stockouts: %{customdata[5]})<br>
            <extra></extra>
            """
        ))

    # Add Hubs
    fig.add_trace(go.Scattergeo(
        lon=df_hubs["longitude"],
        lat=df_hubs["latitude"],
        text=df_hubs["hub_name"],
        name="Distribution Hub (Nest)",
        mode="markers+text",
        textposition="top right",
        textfont=dict(color="#00D2BA", size=11),
        marker=dict(
            size=18,
            symbol="diamond",
            color="#00D2BA",
            line=dict(width=2, color="#FFFFFF")
        ),
        hovertemplate="<b>%{text}</b><br>Regional Medical Hub<extra></extra>"
    ))

    fig.update_layout(
        geo=dict(
            scope="africa",
            center=dict(lat=7.9, lon=-1.0),
            projection_scale=13,
            showland=True,
            landcolor="#161F30",
            subunitcolor="#2D3748",
            countrycolor="#4A5568",
            showocean=True,
            oceancolor="#0B0F19",
            showlakes=True,
            lakecolor="#0B0F19",
            bgcolor="#0B0F19",
        ),
        paper_bgcolor="#0B0F19",
        plot_bgcolor="#0B0F19",
        margin=dict(l=0, r=0, t=20, b=0),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(color="#E5E7EB", size=11),
        ),
        height=520,
    )
    return fig
