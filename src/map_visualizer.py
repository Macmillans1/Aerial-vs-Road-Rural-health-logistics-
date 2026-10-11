"""Geospatial Map Visualizer for Rural Healthcare Logistics in Ghana.

Provides PyDeck 3D illustrative network corridors and Plotly interactive geospatial maps.
Visualizes active vs. configured distribution hubs, clinic delivery endpoints, risk tiers, and supply corridors.
Connections represent illustrative routing corridors, not live aerial flight paths.
"""

from typing import Dict, List, Optional, Tuple
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
    "Active Hub": [0, 210, 186, 255],     # Cyan #00D2BA
    "Configured Hub": [107, 114, 128, 190], # Muted Gray #6B7280
    "Tier 1": [59, 130, 246, 210],        # Blue
    "Tier 2": [139, 92, 246, 210],        # Purple
    "Tier 3": [236, 72, 153, 210],        # Magenta
}


def build_pydeck_logistics_map(
    df_clinic_metrics: pd.DataFrame,
    df_hubs: pd.DataFrame,
    df_filtered: Optional[pd.DataFrame] = None,
    color_by: str = "risk_tier",
    show_supply_corridors: bool = True,
) -> Tuple[pdk.Deck, List[str]]:
    """Construct an interactive PyDeck 3D map featuring hubs, clinics, and illustrative corridors.

    Distinguishes active hubs (with actual dispatches in filtered view, excluding stockouts)
    from configured hubs. Provides dedicated, relevant tooltips for clinics, hubs, and routes.

    Returns:
        Tuple[pdk.Deck, List[str]]: The Deck object and a list of clinic names with unmapped hubs.
    """
    unmapped_clinics: List[str] = []
    layers = []

    # 1. Hubs Layer (Active vs Configured)
    if df_hubs is not None and len(df_hubs) > 0:
        df_hubs_map = df_hubs.copy()

        # Count actual dispatches using valid dispatch_timestamp values (strictly excluding stock-outs)
        hub_counts = {}
        if df_filtered is not None and len(df_filtered) > 0 and "hub_id" in df_filtered.columns:
            if "dispatch_timestamp" in df_filtered.columns:
                dispatched_records = df_filtered[df_filtered["dispatch_timestamp"].notna()]
            else:
                dispatched_records = df_filtered[df_filtered["order_status"] != "Stock-Out"]
            hub_counts = dispatched_records["hub_id"].value_counts().to_dict()

        df_hubs_map["dispatches_in_filter"] = df_hubs_map["hub_id"].map(lambda h: hub_counts.get(h, 0))
        df_hubs_map["is_active"] = df_hubs_map["dispatches_in_filter"] > 0
        df_hubs_map["hub_status"] = df_hubs_map["is_active"].map(
            lambda a: "Active Fulfillment Center" if a else "Configured Center (0 Dispatches in Filter)"
        )
        df_hubs_map["color"] = df_hubs_map["is_active"].map(
            lambda a: PALETTE["Active Hub"] if a else PALETTE["Configured Hub"]
        )
        df_hubs_map["radius"] = df_hubs_map["is_active"].map(lambda a: 14000 if a else 9000)

        # Dedicated hub tooltip containing only relevant hub fields
        df_hubs_map["tooltip_html"] = df_hubs_map.apply(
            lambda r: f"""<div style="background-color: #111827; color: #F3F4F6; padding: 10px 14px; border-radius: 8px; border: 1px solid #374151; font-family: sans-serif; font-size: 12px; line-height: 1.5; box-shadow: 0 8px 16px rgba(0,0,0,0.5);">
    <div style="font-weight: 700; font-size: 13px; color: #00D2BA; margin-bottom: 4px;">{r['hub_name']} (Distribution Hub)</div>
    <div><b>Region:</b> {r['region']}</div>
    <div><b>Status:</b> {r['hub_status']}</div>
    <div><b>Actual Dispatches in View:</b> {r['dispatches_in_filter']:,}</div>
</div>""",
            axis=1,
        )

        active_hubs_layer = pdk.Layer(
            "ScatterplotLayer",
            id="distribution-hubs-layer",
            data=df_hubs_map,
            get_position=["longitude", "latitude"],
            get_color="color",
            get_radius="radius",
            pickable=True,
            stroked=True,
            get_line_color=[255, 255, 255, 240],
            line_width_min_pixels=2,
            radius_min_pixels=8,
            radius_max_pixels=22,
        )
        layers.append(active_hubs_layer)

    # 2. Clinic Endpoints Layer
    if df_clinic_metrics is not None and len(df_clinic_metrics) > 0:
        df_clinics_map = df_clinic_metrics.copy()

        if color_by == "risk_tier":
            df_clinics_map["color"] = df_clinics_map["risk_tier"].map(
                lambda r: PALETTE.get(r, [150, 150, 150, 200])
            )
        else:  # remote_tier
            df_clinics_map["color"] = df_clinics_map["remote_tier"].map(
                lambda t: PALETTE.get(t, [150, 150, 150, 200])
            )

        # Dedicated clinic tooltip containing only relevant clinic performance fields
        df_clinics_map["tooltip_html"] = df_clinics_map.apply(
            lambda r: f"""<div style="background-color: #111827; color: #F3F4F6; padding: 10px 14px; border-radius: 8px; border: 1px solid #374151; font-family: sans-serif; font-size: 12px; line-height: 1.5; box-shadow: 0 8px 16px rgba(0,0,0,0.5);">
    <div style="font-weight: 700; font-size: 13px; color: #00D2BA; margin-bottom: 4px;">{r.get('clinic_name', r.get('clinic_id', 'Clinic'))}</div>
    <div><b>Region:</b> {r.get('region', 'N/A')}</div>
    <div><b>Accessibility:</b> {r.get('remote_tier', 'N/A')}</div>
    <div><b>Risk Tier:</b> {r.get('risk_tier', 'N/A')}</div>
    <div><b>Assigned Hub:</b> {r.get('nearest_hub', 'N/A')}</div>
    <div><b>Standard OTIF:</b> <span style="color: #10B981; font-weight: 700;">{r.get('standard_otif_rate_pct', 'N/A')}%</span></div>
    <div><b>Quality OTIF:</b> {r.get('quality_otif_rate_pct', 'N/A')}%</div>
    <div><b>Avg Lead Time:</b> {r.get('avg_lead_time_hours', 'N/A')} hrs</div>
    <div><b>Total Requests:</b> {r.get('total_orders', 0):,} (Stockouts: {r.get('stock_outs', 0):,})</div>
</div>""",
            axis=1,
        )

        clinic_layer = pdk.Layer(
            "ScatterplotLayer",
            id="clinics-endpoints-layer",
            data=df_clinics_map,
            get_position=["longitude", "latitude"],
            get_color="color",
            get_radius=6000,
            pickable=True,
            auto_highlight=True,
            radius_min_pixels=6,
            radius_max_pixels=18,
        )
        layers.append(clinic_layer)

        # 3. Illustrative Supply Corridors (Hub to Clinic)
        if show_supply_corridors and df_hubs is not None and len(df_hubs) > 0:
            hubs_lookup = df_hubs.set_index("hub_id")[["latitude", "longitude", "hub_name"]].to_dict("index")
            arc_records = []

            for _, clinic in df_clinics_map.iterrows():
                hub_id = clinic.get("nearest_hub")
                # Strict check: Never silently default to arbitrary fallback
                if not hub_id or hub_id not in hubs_lookup or pd.isna(hub_id):
                    unmapped_clinics.append(str(clinic.get("clinic_name", clinic.get("clinic_id", "Unknown"))))
                    continue

                hub = hubs_lookup[hub_id]
                c_name = clinic.get("clinic_name", "Clinic")
                h_name = hub.get("hub_name", "Hub")
                c_otif = clinic.get("standard_otif_rate_pct", 0.0)

                arc_records.append({
                    "source_lon": hub["longitude"],
                    "source_lat": hub["latitude"],
                    "target_lon": clinic["longitude"],
                    "target_lat": clinic["latitude"],
                    "clinic_name": c_name,
                    "hub_name": h_name,
                    "otif": c_otif,
                    "color_start": [0, 210, 186, 160],
                    "color_end": [239, 68, 68, 160] if clinic.get("risk_tier") == "High Risk" else [16, 185, 129, 140],
                    "tooltip_html": f"""<div style="background-color: #111827; color: #F3F4F6; padding: 10px 14px; border-radius: 8px; border: 1px solid #374151; font-family: sans-serif; font-size: 12px; line-height: 1.5; box-shadow: 0 8px 16px rgba(0,0,0,0.5);">
    <div style="font-weight: 700; font-size: 13px; color: #00D2BA; margin-bottom: 4px;">Supply Routing Corridor</div>
    <div><b>Fulfillment Hub:</b> {h_name}</div>
    <div><b>Destination Clinic:</b> {c_name}</div>
    <div><b>Destination Std OTIF:</b> {c_otif}%</div>
    <div style="font-size: 10px; color: #9CA3AF; margin-top: 4px; border-top: 1px solid #374151; padding-top: 4px;">* Corridors represent illustrative logistical links.</div>
</div>""",
                })

            if len(arc_records) > 0:
                df_arcs = pd.DataFrame(arc_records)
                arc_layer = pdk.Layer(
                    "ArcLayer",
                    id="illustrative-corridors-layer",
                    data=df_arcs,
                    get_source_position=["source_lon", "source_lat"],
                    get_target_position=["target_lon", "target_lat"],
                    get_source_color="color_start",
                    get_target_color="color_end",
                    get_width=2.2,
                    pickable=True,
                    auto_highlight=True,
                )
                layers.append(arc_layer)

    view_state = pdk.ViewState(
        latitude=7.85,
        longitude=-1.10,
        zoom=6.3,
        pitch=38,
        bearing=0,
    )

    tooltip = {
        "html": "{tooltip_html}",
        "style": {"backgroundColor": "transparent", "color": "white"}
    }

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/dark-v11",
        tooltip=tooltip,
    )
    return deck, unmapped_clinics


def build_plotly_geographic_scatter(
    df_clinic_metrics: pd.DataFrame,
    df_hubs: pd.DataFrame,
    df_filtered: Optional[pd.DataFrame] = None,
    color_by: str = "risk_tier"
) -> go.Figure:
    """High-contrast Plotly 2D fallback map of clinics and hubs with telemetry styling."""
    fig = go.Figure()

    color_map = {
        "Optimal": "#10B981",
        "Moderate Risk": "#F59E0B",
        "High Risk": "#EF4444",
        "Tier 1": "#3B82F6",
        "Tier 2": "#8B5CF6",
        "Tier 3": "#EC4899",
    }

    # Add Clinics
    if df_clinic_metrics is not None and len(df_clinic_metrics) > 0 and color_by in df_clinic_metrics.columns:
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
                customdata=subset[["region", "remote_tier", "standard_otif_rate_pct", "avg_lead_time_hours", "total_orders", "stock_outs", "nearest_hub"]],
                hovertemplate="""<b>%{text}</b><br>Region: %{customdata[0]}<br>Accessibility: %{customdata[1]}<br>Assigned Hub: %{customdata[6]}<br>Standard OTIF: %{customdata[2]}%<br>Avg Lead Time: %{customdata[3]} hrs<br>Total Requests: %{customdata[4]} (Stockouts: %{customdata[5]})<extra></extra>"""
            ))

    # Add Hubs (Distinguishing active vs configured, counting actual dispatches excluding stockouts)
    if df_hubs is not None and len(df_hubs) > 0:
        hub_counts = {}
        if df_filtered is not None and len(df_filtered) > 0 and "hub_id" in df_filtered.columns:
            if "dispatch_timestamp" in df_filtered.columns:
                dispatched_filter = df_filtered[df_filtered["dispatch_timestamp"].notna()]
            else:
                dispatched_filter = df_filtered[df_filtered["order_status"] != "Stock-Out"]
            hub_counts = dispatched_filter["hub_id"].value_counts().to_dict()

        df_hubs_copy = df_hubs.copy()
        df_hubs_copy["dispatches"] = df_hubs_copy["hub_id"].map(lambda h: hub_counts.get(h, 0))
        active_hubs = df_hubs_copy[df_hubs_copy["dispatches"] > 0]
        configured_hubs = df_hubs_copy[df_hubs_copy["dispatches"] == 0]

        if len(active_hubs) > 0:
            fig.add_trace(go.Scattergeo(
                lon=active_hubs["longitude"],
                lat=active_hubs["latitude"],
                text=active_hubs["hub_name"],
                name="Active Hub",
                mode="markers+text",
                textposition="top right",
                textfont=dict(color="#00D2BA", size=11),
                marker=dict(
                    size=18,
                    symbol="diamond",
                    color="#00D2BA",
                    line=dict(width=2, color="#FFFFFF")
                ),
                customdata=active_hubs[["region", "dispatches"]],
                hovertemplate="<b>%{text} (Distribution Hub)</b><br>Region: %{customdata[0]}<br>Actual Dispatches: %{customdata[1]}<extra></extra>"
            ))

        if len(configured_hubs) > 0:
            fig.add_trace(go.Scattergeo(
                lon=configured_hubs["longitude"],
                lat=configured_hubs["latitude"],
                text=configured_hubs["hub_name"],
                name="Configured Hub (Inactive)",
                mode="markers+text",
                textposition="top right",
                textfont=dict(color="#9CA3AF", size=10),
                marker=dict(
                    size=14,
                    symbol="diamond-open",
                    color="#6B7280",
                    line=dict(width=2, color="#9CA3AF")
                ),
                customdata=configured_hubs[["region", "dispatches"]],
                hovertemplate="<b>%{text} (Distribution Hub)</b><br>Region: %{customdata[0]}<br>Status: Configured (0 dispatches in filter)<extra></extra>"
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
