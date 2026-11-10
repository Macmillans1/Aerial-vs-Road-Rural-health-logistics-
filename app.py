"""Rural Healthcare Supply Chain & Logistics Analytics Dashboard.

Ghana Medical Drone & Ground Fleet Logistics Network (Zipline & GHS Operational Model).
Comprehensive operational telemetry and multi-modal logistics performance analytics.
"""

import json
from datetime import datetime
from typing import Optional
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.metrics_engine import (
    SupplyChainMetricsEngine,
    ExecutiveKPIs,
    DataValidationError,
    filter_shipment_ledger,
)
from src.map_visualizer import build_pydeck_logistics_map, build_plotly_geographic_scatter
from src.scenario_engine import ScenarioParameters, simulate_scenario

# -----------------------------------------------------------------------------
# 1. Page Configuration & Custom CSS Injection
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Ghana Rural Healthcare Logistics Telemetry",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Premium Dark Glassmorphism CSS styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: radial-gradient(circle at 15% 15%, #101826 0%, #0B0F19 100%);
    }

    .synthetic-banner {
        background: rgba(30, 58, 138, 0.25);
        border: 1px solid rgba(59, 130, 246, 0.4);
        border-radius: 8px;
        padding: 8px 14px;
        color: #93C5FD;
        font-size: 0.82rem;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 16px;
    }

    .metric-card {
        background: rgba(22, 31, 48, 0.75);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 16px 20px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, border-color 0.2s ease;
        position: relative;
        overflow: hidden;
        min-height: 122px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(0, 210, 186, 0.4);
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, #00D2BA, #3B82F6);
    }
    .metric-card.alert::before {
        background: linear-gradient(90deg, #EF4444, #F59E0B);
    }
    .metric-card.gold::before {
        background: linear-gradient(90deg, #F59E0B, #10B981);
    }
    .metric-card.purple::before {
        background: linear-gradient(90deg, #8B5CF6, #EC4899);
    }

    .metric-title {
        font-size: 0.80rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #9CA3AF;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 2.05rem;
        font-weight: 800;
        color: #FFFFFF;
        line-height: 1.1;
        margin-bottom: 4px;
    }
    .metric-sub {
        font-size: 0.80rem;
        color: #6EE7B7;
        display: flex;
        align-items: center;
        gap: 6px;
        line-height: 1.3;
    }
    .metric-sub.negative {
        color: #FCA5A5;
    }
    .metric-sub.neutral {
        color: #D1D5DB;
    }

    .section-header {
        font-size: 1.22rem;
        font-weight: 700;
        color: #F3F4F6;
        margin: 26px 0 14px 0;
        display: flex;
        align-items: center;
        gap: 10px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding-bottom: 8px;
    }
    .section-badge {
        font-size: 0.72rem;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 9999px;
        background: rgba(0, 210, 186, 0.15);
        color: #00D2BA;
        border: 1px solid rgba(0, 210, 186, 0.3);
    }

    [data-testid="stSidebar"] {
        background-color: #0e1422;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 2. Data Engine Caching
# -----------------------------------------------------------------------------
@st.cache_resource
def get_metrics_engine() -> SupplyChainMetricsEngine:
    """Instantiate and load the star-schema metrics engine."""
    engine = SupplyChainMetricsEngine(data_dir="data")
    engine.load_data()
    return engine

try:
    engine = get_metrics_engine()
except DataValidationError as exc:
    st.error(f"Data Validation Error: {exc}")
    st.stop()


# -----------------------------------------------------------------------------
# 3. Sidebar Filtering Controls
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
            <div style="background: linear-gradient(135deg, #00D2BA, #3B82F6); width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 14px; color: #FFFFFF; letter-spacing: 0.5px;">AM</div>
            <div>
                <div style="font-weight: 800; font-size: 1.05rem; color: #FFFFFF; line-height: 1.2;">AERO-MED GHANA</div>
                <div style="font-size: 0.72rem; color: #00D2BA; letter-spacing: 0.05em; font-weight: 600;">LOGISTICS TELEMETRY</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Multidimensional Filters")

    # Region Multi-Select
    available_regions = sorted(engine.df_clinics["region"].unique().tolist())
    selected_regions = st.multiselect(
        "Administrative Regions",
        options=available_regions,
        default=available_regions,
        help="Filter shipments delivered to health posts across administrative regions in Ghana."
    )

    # Date Range Input
    min_date = engine.df_master["requested_timestamp"].min().date()
    max_date = engine.df_master["requested_timestamp"].max().date()
    date_selection = st.date_input(
        "Evaluation Timeframe",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        help="Select the evaluation window (1 full calendar year)."
    )

    # Product Category Filter
    available_categories = sorted(engine.df_products["category"].unique().tolist())
    selected_categories = st.multiselect(
        "Medical Product Category",
        options=available_categories,
        default=available_categories,
        help="Select cargo types: Cold-chain vaccines, blood reserves, antivenoms, or essential meds."
    )

    # Transport Mode Filter
    available_modes = ["Drone", "Road"]
    selected_modes = st.multiselect(
        "Transport Fleet Modality",
        options=available_modes,
        default=available_modes,
        help="Compare autonomous electric medical drones vs. regional ground vehicles."
    )

    # Remote Tier Filter
    available_tiers = ["Tier 1", "Tier 2", "Tier 3"]
    selected_tiers = st.multiselect(
        "Clinic Accessibility Tier",
        options=available_tiers,
        default=available_tiers,
        help="Tier 1: Peri-urban accessible | Tier 2: Rural unpaved | Tier 3: Isolated deep-forest & riverine."
    )

    st.markdown("---")
    st.markdown("### Map Display Preferences")
    map_engine_choice = st.radio("Map Rendering Engine", ["PyDeck 3D (Illustrative Corridors)", "Plotly 2D Scatter"], index=0)
    map_color_choice = st.selectbox(
        "Color Clinics By",
        ["risk_tier", "remote_tier"],
        format_func=lambda x: "Delivery Delay Risk Tier" if x == "risk_tier" else "Remote Accessibility Tier"
    )
    show_supply_corridors = st.checkbox("Show Illustrative Supply Corridors (Hub to Clinic)", value=True)

    st.markdown("---")
    st.markdown("""
        <div style="font-size: 0.72rem; color: #6B7280; line-height: 1.4;">
            <b>Operational Context:</b><br>
            Multi-modal supply chain modeling comparing autonomous aerial delivery vs. ground fleet logistics.<br>
            <i>Architecture: Star Schema | Python 3.10+ | Streamlit | Plotly | PyDeck</i>
        </div>
    """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 4. Filter Execution & Data Subsetting
# -----------------------------------------------------------------------------
# Safe handling of incomplete date selection (e.g. single date while user is picking range)
if isinstance(date_selection, (tuple, list)):
    if len(date_selection) == 2:
        start_filter_date, end_filter_date = date_selection[0], date_selection[1]
    elif len(date_selection) == 1:
        start_filter_date = date_selection[0]
        end_filter_date = date_selection[0]
    else:
        start_filter_date, end_filter_date = min_date, max_date
else:
    start_filter_date, end_filter_date = min_date, max_date

# Pass filter lists directly so deselecting everything ([] vs None) yields empty results accurately
df_filtered = engine.filter_data(
    regions=selected_regions,
    date_range=(start_filter_date, end_filter_date),
    product_categories=selected_categories,
    transport_modes=selected_modes,
    remote_tiers=selected_tiers,
)

kpis = engine.compute_executive_kpis(df_filtered)
df_clinic_metrics = engine.get_clinic_performance_summary(df_filtered)

# Accurate dynamic network counts from filtered data
active_hubs_count = df_filtered["hub_id"].nunique() if len(df_filtered) > 0 else 0
active_clinics_count = df_filtered["clinic_id"].nunique() if len(df_filtered) > 0 else 0
active_products_count = df_filtered["product_id"].nunique() if len(df_filtered) > 0 else 0


# -----------------------------------------------------------------------------
# 5. Header & Executive KPI Scorecard
# -----------------------------------------------------------------------------
st.markdown("""
    <div class="synthetic-banner">
        <span><b>Synthetic Data Notice:</b> All shipment telemetry, GPS coordinates, lead times, and operational records in this dashboard are generated synthetically for supply chain analytics and simulation modeling.</span>
    </div>
""", unsafe_allow_html=True)

st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 20px;">
        <div>
            <h1 style="margin: 0; font-size: 2.05rem; font-weight: 800; color: #FFFFFF; letter-spacing: -0.02em;">
                Rural Healthcare Supply Chain & Drone Logistics Analytics
            </h1>
            <p style="margin: 4px 0 0 0; color: #9CA3AF; font-size: 0.92rem;">
                Operational Telemetry Dashboard • Autonomous Drone Fleet vs. Rural Ground Fleet • Republic of Ghana
            </p>
        </div>
        <div style="text-align: right; background: rgba(0, 210, 186, 0.08); padding: 8px 14px; border-radius: 8px; border: 1px solid rgba(0, 210, 186, 0.25);">
            <div style="font-size: 0.70rem; color: #9CA3AF; font-weight: 600; text-transform: uppercase;">Active Filtered Subnetwork</div>
            <div style="font-size: 0.95rem; font-weight: 700; color: #00D2BA;">{active_hubs_count} Hubs • {active_clinics_count} Clinics • {active_products_count} Products</div>
        </div>
    </div>
""", unsafe_allow_html=True)

if len(df_filtered) == 0:
    st.warning("No shipment records match the selected filter criteria. Please broaden your selection in the sidebar.")

# Helper formatting function
def fmt_pct(val: Optional[float]) -> str:
    return f"{val:.1f}%" if val is not None else "N/A"

def fmt_hours(val: Optional[float]) -> str:
    return f"{val:.1f} hrs" if val is not None else "N/A"

# Executive KPI Cards (Organized into two balanced 3-column rows for optimal fit)
row1_col1, row1_col2, row1_col3 = st.columns(3)

with row1_col1:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Requests</div>
            <div class="metric-value">{kpis.total_requests:,}</div>
            <div class="metric-sub neutral">Delivered: <b>{kpis.delivered_orders:,}</b> &nbsp;•&nbsp; Stock-outs: <b>{kpis.stock_outs:,}</b></div>
        </div>
    """, unsafe_allow_html=True)

with row1_col2:
    deliv_rate_str = fmt_pct(kpis.delivery_success_rate_pct)
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Delivery Success Rate</div>
            <div class="metric-value" style="color: #10B981;">{deliv_rate_str}</div>
            <div class="metric-sub positive">On-Time: <b>{kpis.on_time_orders:,}</b> &nbsp;•&nbsp; Late: <b>{kpis.delayed_orders:,}</b></div>
        </div>
    """, unsafe_allow_html=True)

with row1_col3:
    avg_lt_str = f"{kpis.avg_lead_time_hours:.1f}" if kpis.avg_lead_time_hours is not None else "N/A"
    if kpis.drone_road_delta_hours is not None:
        delta_sub = f"Diff in avg simulated lead time: <b>-{kpis.drone_road_delta_hours:.1f} hrs</b> (Drone vs Road)"
    elif kpis.drone_avg_lead_time_hours is not None:
        delta_sub = f"Drone-only active ({kpis.drone_avg_lead_time_hours:.1f} hrs)"
    elif kpis.road_avg_lead_time_hours is not None:
        delta_sub = f"Road-only active ({kpis.road_avg_lead_time_hours:.1f} hrs)"
    else:
        delta_sub = "No deliveries in view"

    st.markdown(f"""
        <div class="metric-card gold">
            <div class="metric-title">Avg Order Cycle Time</div>
            <div class="metric-value">{avg_lt_str} <span style="font-size: 1.05rem; font-weight: 500; color: #9CA3AF;">hrs</span></div>
            <div class="metric-sub">{delta_sub}</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

row2_col1, row2_col2, row2_col3 = st.columns(3)

with row2_col1:
    std_otif_str = fmt_pct(kpis.standard_otif_rate_pct)
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Standard OTIF Rate</div>
            <div class="metric-value" style="color: {'#10B981' if kpis.standard_otif_rate_pct and kpis.standard_otif_rate_pct >= 75 else '#F59E0B'};">{std_otif_str}</div>
            <div class="metric-sub">Strict SLA: On-Time & In-Full</div>
        </div>
    """, unsafe_allow_html=True)

with row2_col2:
    qual_otif_str = fmt_pct(kpis.quality_otif_rate_pct)
    st.markdown(f"""
        <div class="metric-card purple">
            <div class="metric-title">Quality OTIF (OTIF-Q)</div>
            <div class="metric-value" style="color: #A78BFA;">{qual_otif_str}</div>
            <div class="metric-sub">Standard OTIF + Thermal Compliance</div>
        </div>
    """, unsafe_allow_html=True)

with row2_col3:
    cold_str = fmt_pct(kpis.cold_chain_integrity_pct)
    unknown_note = f" (Unknown: {kpis.unknown_quality_cold_orders})" if kpis.unknown_quality_cold_orders > 0 else ""
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Cold-Chain Thermal Integrity</div>
            <div class="metric-value" style="color: {'#10B981' if kpis.cold_chain_integrity_pct and kpis.cold_chain_integrity_pct >= 95 else '#F59E0B'};">{cold_str}</div>
            <div class="metric-sub">Denom: {kpis.total_delivered_cold_orders:,} Delivered Cold Items{unknown_note}</div>
        </div>
    """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 6. Geospatial Mapping Section
# -----------------------------------------------------------------------------
st.markdown("""
    <div class="section-header">
        <span>Geospatial Distribution Network & Illustrative Supply Corridors</span>
        <span class="section-badge">PyDeck 3D / Plotly Engine</span>
    </div>
""", unsafe_allow_html=True)

map_col1, map_col2 = st.columns([2.8, 1.2])

with map_col1:
    if map_engine_choice == "PyDeck 3D (Illustrative Corridors)":
        deck, unmapped = build_pydeck_logistics_map(
            df_clinic_metrics=df_clinic_metrics,
            df_hubs=engine.df_hubs,
            df_filtered=df_filtered,
            color_by=map_color_choice,
            show_supply_corridors=show_supply_corridors,
        )
        st.pydeck_chart(deck, use_container_width=True)
        if len(unmapped) > 0:
            st.warning(f"Unmapped Hub Relationships: {len(unmapped)} clinic(s) could not be matched to an active hub: {', '.join(unmapped[:3])}")
    else:
        fig_geo = build_plotly_geographic_scatter(
            df_clinic_metrics=df_clinic_metrics,
            df_hubs=engine.df_hubs,
            df_filtered=df_filtered,
            color_by=map_color_choice,
        )
        st.plotly_chart(fig_geo, use_container_width=True)

with map_col2:
    if map_color_choice == "risk_tier":
        legend_nodes_html = """<div style="font-weight: 600; color: #E2E8F0; margin: 10px 0 6px 0; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px;">Clinic Risk Classification (Demonstration Assumptions)</div>
<div style="display: flex; align-items: center; margin-bottom: 6px; font-size: 0.82rem;">
    <span style="display: inline-block; width: 10px; height: 10px; background: #10B981; border: 1.5px solid #FFFFFF; border-radius: 50%; margin-right: 8px; flex-shrink: 0;"></span>
    <span><b>Optimal Clinic</b> (Std OTIF &ge; 80%)</span>
</div>
<div style="display: flex; align-items: center; margin-bottom: 6px; font-size: 0.82rem;">
    <span style="display: inline-block; width: 10px; height: 10px; background: #F59E0B; border: 1.5px solid #FFFFFF; border-radius: 50%; margin-right: 8px; flex-shrink: 0;"></span>
    <span><b>Moderate Risk</b> (Std OTIF 65–80%)</span>
</div>
<div style="display: flex; align-items: center; margin-bottom: 8px; font-size: 0.82rem;">
    <span style="display: inline-block; width: 10px; height: 10px; background: #EF4444; border: 1.5px solid #FFFFFF; border-radius: 50%; margin-right: 8px; flex-shrink: 0;"></span>
    <span><b>High Risk</b> (&lt; 65% OTIF or &gt; 8% Stockout)</span>
</div>"""
        legend_explainer = """<b>Threshold Rationale:</b><br>
• <b>&ge; 80%</b>: Meets the selected demonstration threshold.<br>
• <b>65–80%</b>: Elevated delay volatility requiring buffer stock.<br>
• <b>&lt; 65% / &gt; 8% stockout</b>: Critical service gaps risking treatment access."""
    else:
        legend_nodes_html = """<div style="font-weight: 600; color: #E2E8F0; margin: 10px 0 6px 0; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px;">Clinic Remoteness Tier</div>
<div style="display: flex; align-items: center; margin-bottom: 6px; font-size: 0.82rem;">
    <span style="display: inline-block; width: 10px; height: 10px; background: #3B82F6; border: 1.5px solid #FFFFFF; border-radius: 50%; margin-right: 8px; flex-shrink: 0;"></span>
    <span><b>Tier 1</b>: Peri-urban accessible (&lt; 50 km)</span>
</div>
<div style="display: flex; align-items: center; margin-bottom: 6px; font-size: 0.82rem;">
    <span style="display: inline-block; width: 10px; height: 10px; background: #8B5CF6; border: 1.5px solid #FFFFFF; border-radius: 50%; margin-right: 8px; flex-shrink: 0;"></span>
    <span><b>Tier 2</b>: Rural unpaved (50–150 km)</span>
</div>
<div style="display: flex; align-items: center; margin-bottom: 8px; font-size: 0.82rem;">
    <span style="display: inline-block; width: 10px; height: 10px; background: #EC4899; border: 1.5px solid #FFFFFF; border-radius: 50%; margin-right: 8px; flex-shrink: 0;"></span>
    <span><b>Tier 3</b>: Remote rainforest / riverine (&gt; 150 km)</span>
</div>"""
        legend_explainer = """<b>Terrain Classification:</b><br>
Reflects road infrastructure decay and terrain winding multipliers (1.35x to 1.85x) that increase road travel times."""

    corridor_legend_html = ""
    if show_supply_corridors:
        corridor_legend_html = """<div style="font-weight: 600; color: #E2E8F0; margin: 10px 0 6px 0; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px;">Supply Corridors</div>
<div style="display: flex; align-items: center; margin-bottom: 8px; font-size: 0.82rem;">
    <span style="display: inline-block; width: 20px; height: 3px; background: linear-gradient(90deg, #00D2BA, #10B981); border-radius: 2px; margin-right: 8px; flex-shrink: 0;"></span>
    <span><b>Illustrative Links</b> (Hub &rarr; Clinic)</span>
</div>"""

    legend_card_html = f"""<div style="background: rgba(22, 31, 48, 0.75); border-radius: 12px; padding: 16px; border: 1px solid rgba(255, 255, 255, 0.08); font-size: 0.85rem; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);">
<div style="font-weight: 700; color: #00D2BA; margin-bottom: 12px; font-size: 0.95rem;">
    <span>Network Topology Legend</span>
</div>
<div style="font-weight: 600; color: #E2E8F0; margin: 6px 0 6px 0; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px;">Distribution Hubs</div>
<div style="display: flex; align-items: center; margin-bottom: 6px; font-size: 0.82rem;">
    <span style="display: inline-block; width: 9px; height: 9px; background: #00D2BA; border: 1.5px solid #FFFFFF; transform: rotate(45deg); margin-right: 8px; margin-left: 2px; flex-shrink: 0; box-shadow: 0 0 4px rgba(0,210,186,0.6);"></span>
    <span><b>Active Hub</b> (Dispatches in filter)</span>
</div>
<div style="display: flex; align-items: center; margin-bottom: 8px; font-size: 0.82rem;">
    <span style="display: inline-block; width: 8px; height: 8px; background: transparent; border: 1.5px solid #9CA3AF; transform: rotate(45deg); margin-right: 8px; margin-left: 2px; flex-shrink: 0;"></span>
    <span><b>Configured Hub</b> (0 dispatches in filter)</span>
</div>
{legend_nodes_html}
{corridor_legend_html}
<hr style="border-color: rgba(255,255,255,0.08); margin: 10px 0;">
<div style="font-size: 0.76rem; color: #9CA3AF; line-height: 1.4;">
    {legend_explainer}
    <div style="margin-top: 6px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 6px; color: #6B7280;">
        * Corridors indicate illustrative supply connections, not live aerial tracks.
    </div>
</div>
</div>"""

    st.markdown(legend_card_html, unsafe_allow_html=True)

    if len(df_clinic_metrics) > 0 and "risk_tier" in df_clinic_metrics.columns:
        high_risk_clinics = df_clinic_metrics[df_clinic_metrics["risk_tier"] == "High Risk"].sort_values("standard_otif_rate_pct").head(4)
        if len(high_risk_clinics) > 0:
            st.markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #EF4444; margin: 12px 0 6px 0;'>Critical Bottleneck Clinics:</div>", unsafe_allow_html=True)
            for _, cln in high_risk_clinics.iterrows():
                clinic_pill_html = f"""<div style="background: rgba(239, 68, 68, 0.12); border-left: 3px solid #EF4444; padding: 6px 10px; margin-bottom: 6px; border-radius: 0 6px 6px 0; font-size: 0.76rem;">
<b>{cln['clinic_name']}</b> ({cln['region']})<br>
Assigned Hub: <b>{cln['nearest_hub']}</b><br>
Standard OTIF: <b>{cln['standard_otif_rate_pct']}%</b> | Avg LT: <b>{cln['avg_lead_time_hours']} hrs</b>
</div>"""
                st.markdown(clinic_pill_html, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 7. Operational Performance Analytics
# -----------------------------------------------------------------------------
st.markdown("""
    <div class="section-header">
        <span>Operational Performance & Modal Efficiency Breakdown</span>
        <span class="section-badge">Drone Velocity vs. Rural Road Logistics</span>
    </div>
""", unsafe_allow_html=True)

chart_tab1, chart_tab2, chart_tab3, chart_tab4, chart_tab5 = st.tabs([
    "Transport Efficiency (Drone vs. Road)",
    "Weekly OTIF & Fulfillment Trends",
    "Regional Bottlenecks & Stock-Out Diagnostics",
    "What-If Scenario Simulator",
    "Clinic & Hub Explorer",
])


# TAB 1: MODAL TRANSPORT EFFICIENCY
with chart_tab1:
    modal_col1, modal_col2 = st.columns(2)
    df_modal = engine.get_modal_comparison(df_filtered)

    with modal_col1:
        if len(df_modal) > 0:
            fig_lead_time = px.bar(
                df_modal,
                x="distance_band",
                y="avg_lead_time_hours",
                color="transport_mode",
                barmode="group",
                title="Average Lead Time by Distance Bracket (Hours)",
                labels={"avg_lead_time_hours": "Average Lead Time (Hours)", "distance_band": "Distance Bracket", "transport_mode": "Modality"},
                color_discrete_map={"Drone": "#00D2BA", "Road": "#F59E0B"},
                text_auto=".1f",
            )
            fig_lead_time.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E5E7EB"),
                margin=dict(t=50, b=40, l=40, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="#1F2937"),
            )
            st.plotly_chart(fig_lead_time, use_container_width=True)
        else:
            st.info("No delivered shipments available in current filter selection.")

    with modal_col2:
        delivered_subset = df_filtered[df_filtered["is_delivered"]].copy()
        if len(delivered_subset) > 0:
            fig_box = px.box(
                delivered_subset,
                x="remote_tier",
                y="lead_time_hours",
                color="transport_mode",
                title="Lead Time Distribution Across Remote Accessibility Tiers",
                labels={"lead_time_hours": "Lead Time (Hours)", "remote_tier": "Accessibility Tier", "transport_mode": "Modality"},
                color_discrete_map={"Drone": "#00D2BA", "Road": "#F59E0B"},
                points=False,
            )
            fig_box.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E5E7EB"),
                margin=dict(t=50, b=40, l=40, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="#1F2937"),
            )
            st.plotly_chart(fig_box, use_container_width=True)
        else:
            st.info("No delivered shipments to plot distribution.")

    # Weather impact section
    st.markdown("#### Weather Impact on Delivery Lead Times")
    if len(delivered_subset) > 0:
        weather_summary = delivered_subset.groupby(["weather_condition", "transport_mode"], observed=True).agg(
            avg_lead_time=("lead_time_hours", "mean"),
            std_otif_pct=("is_standard_otif", lambda s: (s.sum() / len(s)) * 100.0),
            delay_count=("is_delayed", "sum"),
            total=("request_id", "count"),
        ).reset_index()

        fig_weather = px.bar(
            weather_summary,
            x="weather_condition",
            y="avg_lead_time",
            color="transport_mode",
            barmode="group",
            title="Transit Lead Time by Weather Condition and Modality",
            labels={"avg_lead_time": "Average Lead Time (Hours)", "weather_condition": "Weather State", "transport_mode": "Modality"},
            color_discrete_map={"Drone": "#00D2BA", "Road": "#F59E0B"},
            text_auto=".2f",
        )
        fig_weather.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#E5E7EB"),
            margin=dict(t=40, b=30, l=40, r=20),
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor="#1F2937"),
        )
        st.plotly_chart(fig_weather, use_container_width=True)


# TAB 2: WEEKLY OTIF & FULFILLMENT TRENDS
with chart_tab2:
    df_trend = engine.get_weekly_trend(df_filtered)
    if len(df_trend) > 0:
        fig_trend = go.Figure()

        # Standard OTIF Rate line
        fig_trend.add_trace(go.Scatter(
            x=df_trend["week_start"],
            y=df_trend["standard_otif_rate_pct"],
            name="Standard OTIF (%)",
            line=dict(color="#00D2BA", width=3),
            mode="lines+markers",
        ))

        # Quality OTIF Rate line
        fig_trend.add_trace(go.Scatter(
            x=df_trend["week_start"],
            y=df_trend["quality_otif_rate_pct"],
            name="Quality OTIF-Q (%)",
            line=dict(color="#A78BFA", width=2, dash="dash"),
            mode="lines",
        ))

        # Delay Rate line
        fig_trend.add_trace(go.Scatter(
            x=df_trend["week_start"],
            y=df_trend["delay_rate_pct"],
            name="Delay Rate (%)",
            line=dict(color="#F59E0B", width=2, dash="dot"),
            mode="lines",
        ))

        # Stockout Rate line
        fig_trend.add_trace(go.Scatter(
            x=df_trend["week_start"],
            y=df_trend["stock_out_rate_pct"],
            name="Stock-Out Rate (%)",
            line=dict(color="#EF4444", width=2),
            mode="lines",
        ))

        fig_trend.update_layout(
            title="Weekly OTIF, Delay, and Stock-Out Rate Trajectories",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#E5E7EB"),
            margin=dict(t=50, b=40, l=40, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(showgrid=False, gridcolor="#1F2937"),
            yaxis=dict(title="Percentage (%)", gridcolor="#1F2937"),
            hovermode="x unified",
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        # Weekly Volume Bar Chart
        fig_vol = px.bar(
            df_trend,
            x="week_start",
            y="total_requests",
            title="Weekly Requisition Volume Over Operational Horizon",
            labels={"week_start": "Week Commencing", "total_requests": "Orders Requested"},
            color_discrete_sequence=["#3B82F6"],
        )
        fig_vol.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#E5E7EB"),
            margin=dict(t=50, b=40, l=40, r=20),
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor="#1F2937"),
        )
        st.plotly_chart(fig_vol, use_container_width=True)
    else:
        st.info("Insufficient data to compute weekly aggregated trends.")


# TAB 3: REGIONAL BOTTLENECKS & STOCKOUT DIAGNOSTICS
with chart_tab3:
    cat_stock, reg_stock = engine.get_stockout_diagnostics(df_filtered)
    reg_bottlenecks = engine.get_regional_bottlenecks(df_filtered)

    diag_col1, diag_col2 = st.columns(2)

    with diag_col1:
        if len(cat_stock) > 0:
            fig_cat = px.bar(
                cat_stock,
                x="category",
                y="stock_out_rate_pct",
                title="Stock-Out Frequency by Medical Product Category (%)",
                labels={"stock_out_rate_pct": "Stock-Out Frequency (%)", "category": "Product Category"},
                color="stock_out_rate_pct",
                color_continuous_scale="Reds",
                text_auto=".1f",
            )
            fig_cat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E5E7EB"),
                margin=dict(t=50, b=40, l=40, r=20),
                coloraxis_showscale=False,
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="#1F2937"),
            )
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("No product categories to display.")

    with diag_col2:
        if len(reg_bottlenecks) > 0:
            fig_bot = px.bar(
                reg_bottlenecks,
                x="region",
                y="bottleneck_score",
                title="Regional Bottleneck Composite Index (0–100 Scale)",
                labels={"bottleneck_score": "Composite Vulnerability Score", "region": "Administrative Region"},
                color="bottleneck_score",
                color_continuous_scale="Viridis",
                text_auto=".1f",
            )
            fig_bot.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E5E7EB"),
                margin=dict(t=50, b=40, l=40, r=20),
                coloraxis_showscale=False,
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="#1F2937"),
            )
            st.plotly_chart(fig_bot, use_container_width=True)
        else:
            st.info("No regional bottlenecks to compute.")

# TAB 4: WHAT-IF SCENARIO SIMULATOR
with chart_tab4:
    st.markdown("""
        <div style="font-size: 1.15rem; font-weight: 700; color: #F3F4F6; margin-bottom: 4px;">
            Multi-Modal What-If Operational Scenario Simulator
        </div>
        <div style="font-size: 0.85rem; color: #9CA3AF; margin-bottom: 12px;">
            Evaluate how pre-flight drone preparation adjustments, ground fleet dispatch delays, and seasonal severe weather affect SLA attainment.
        </div>
    """, unsafe_allow_html=True)

    # Disclaimer and labeling notice
    st.markdown("""
        <div style="background: rgba(30, 58, 138, 0.25); border: 1px solid rgba(59, 130, 246, 0.4); border-radius: 8px; padding: 10px 14px; color: #93C5FD; font-size: 0.82rem; margin-bottom: 16px; line-height: 1.5;">
            <b>Operational Context & Definitions:</b><br>
            • <b>Baseline:</b> Existing simulated records in active sidebar filter selection.<br>
            • <b>Scenario:</b> Results after the selected timing adjustments.<br>
            • <i>Notice:</i> Scenario estimates reflect user-defined assumptions, not predictions of actual operational performance.<br>
            • <i>Scope:</i> Changes timing only. Quality outcomes (cold-chain breach observations) and inventory availability are held constant.
        </div>
    """, unsafe_allow_html=True)

    # Filter change tracking & invalidation
    current_filter_sig = (
        tuple(sorted(selected_regions)) if selected_regions else (),
        str(start_filter_date),
        str(end_filter_date),
        tuple(sorted(selected_categories)) if selected_categories else (),
        tuple(sorted(selected_modes)) if selected_modes else (),
        tuple(sorted(selected_tiers)) if selected_tiers else (),
    )

    if st.session_state.get("scenario_applied", False):
        if st.session_state.get("scenario_filter_sig") != current_filter_sig:
            st.warning("Active sidebar filters have changed since the scenario was applied. Re-apply the scenario to calculate results for the current cohort.")
            st.session_state["scenario_applied"] = False

    # Control form
    with st.form(key="what_if_scenario_form"):
        scen_ctrl_col1, scen_ctrl_col2 = st.columns(2)

        with scen_ctrl_col1:
            st.markdown("<div style='font-size: 0.88rem; font-weight: 600; color: #00D2BA; margin-bottom: 8px;'>Dispatch Preparation Adjustments</div>", unsafe_allow_html=True)
            drone_prep_adj = st.slider(
                "Drone Preparation-Time Adjustment (mins)",
                min_value=-30,
                max_value=120,
                value=int(st.session_state.get("scen_drone_prep_adj", 0)),
                step=5,
                help="Adjustment to drone pre-flight preparation and staging duration (-30 to +120 minutes; default 0).",
            )
            road_prep_adj = st.slider(
                "Road Preparation-Time Adjustment (mins)",
                min_value=-60,
                max_value=240,
                value=int(st.session_state.get("scen_road_prep_adj", 0)),
                step=5,
                help="Adjustment to ground fleet loading, mechanical inspection, and driver staging (-60 to +240 minutes; default 0).",
            )

        with scen_ctrl_col2:
            st.markdown("<div style='font-size: 0.88rem; font-weight: 600; color: #F59E0B; margin-bottom: 8px;'>Severe Weather Transit Delay</div>", unsafe_allow_html=True)
            weather_delay = st.slider(
                "Additional Weather Transit Delay (mins)",
                min_value=0,
                max_value=180,
                value=int(st.session_state.get("scen_weather_delay", 0)),
                step=5,
                help="Additional transit delay added once to eligible shipments under selected weather and transport modes (0 to 180 minutes; default 0).",
            )
            available_weather_conditions = sorted(engine.df_master["weather_condition"].dropna().unique().tolist())
            weather_categories_selected = st.multiselect(
                "Weather Categories Subject to Additional Delay",
                options=available_weather_conditions,
                default=st.session_state.get("scen_weather_categories", [c for c in ["Heavy Rain", "Severe Storm/Flood"] if c in available_weather_conditions]),
                help="Select weather classifications that incur the additional transit delay (default Heavy Rain and Severe Storm/Flood).",
            )
            weather_modes_selected = st.multiselect(
                "Transport Modes Subject to Weather Delay",
                options=["Drone", "Road"],
                default=st.session_state.get("scen_weather_modes", ["Drone", "Road"]),
                help="Select transport modes affected by the weather delay (Drone, Road, or both; default both).",
            )

        form_btn_col1, form_btn_col2 = st.columns([1, 1])
        with form_btn_col1:
            apply_submitted = st.form_submit_button("Apply Scenario", type="primary", use_container_width=True)

    # Reset button (outside form to allow resetting state cleanly)
    reset_col1, reset_col2 = st.columns([1, 3])
    with reset_col1:
        if st.button("Reset Scenario", use_container_width=True, help="Restores default controls (0 timing adjustments) and clears the applied scenario."):
            st.session_state["scenario_applied"] = False
            st.session_state["scen_drone_prep_adj"] = 0
            st.session_state["scen_road_prep_adj"] = 0
            st.session_state["scen_weather_delay"] = 0
            st.session_state["scen_weather_categories"] = [c for c in ["Heavy Rain", "Severe Storm/Flood"] if c in available_weather_conditions]
            st.session_state["scen_weather_modes"] = ["Drone", "Road"]
            st.rerun()

    if apply_submitted:
        st.session_state["scenario_applied"] = True
        st.session_state["scenario_filter_sig"] = current_filter_sig
        st.session_state["scen_drone_prep_adj"] = drone_prep_adj
        st.session_state["scen_road_prep_adj"] = road_prep_adj
        st.session_state["scen_weather_delay"] = weather_delay
        st.session_state["scen_weather_categories"] = weather_categories_selected
        st.session_state["scen_weather_modes"] = weather_modes_selected
        st.rerun()

    # Scenario Results Presentation
    if st.session_state.get("scenario_applied", False):
        scenario_params = ScenarioParameters(
            drone_prep_adj_minutes=float(st.session_state.get("scen_drone_prep_adj", 0)),
            road_prep_adj_minutes=float(st.session_state.get("scen_road_prep_adj", 0)),
            weather_delay_minutes=float(st.session_state.get("scen_weather_delay", 0)),
            weather_categories=tuple(st.session_state.get("scen_weather_categories", ["Heavy Rain", "Severe Storm/Flood"])),
            weather_modes=tuple(st.session_state.get("scen_weather_modes", ["Drone", "Road"])),
        )

        scenario_res = simulate_scenario(df_filtered, scenario_params)
        scen_df = scenario_res.df
        scen_summary = scenario_res.summary

        if len(df_filtered) == 0:
            st.warning("No shipment records match the active filter criteria. Broaden your filters to view scenario simulation.")
        elif scen_summary.delivered_requests == 0:
            st.info("The active selection contains stock-out requests only. No shipments were delivered, so lead times and on-time delivery rates are N/A.")
        else:
            # 1. Headline Comparisons Table
            st.markdown("<div style='font-size: 1.05rem; font-weight: 700; color: #FFFFFF; margin: 18px 0 10px 0;'>Performance Comparison: Baseline vs. Scenario</div>", unsafe_allow_html=True)

            comparison_rows = []
            for m in scen_summary.metric_rows:
                base_val = f"{m.baseline_value:.2f} {m.unit}" if m.baseline_value is not None else "N/A"
                scen_val = f"{m.scenario_value:.2f} {m.unit}" if m.scenario_value is not None else "N/A"
                if m.change_value is not None:
                    if m.is_percentage_point:
                        chg_val = f"{m.change_value:+.2f} pp"
                    else:
                        chg_val = f"{m.change_value:+.2f} {m.unit}"
                else:
                    chg_val = "N/A"

                comparison_rows.append({
                    "Operational Metric": m.metric_name,
                    "Baseline": base_val,
                    "Scenario": scen_val,
                    "Change": chg_val,
                    "Denominator Basis": m.denominator_explanation,
                })

            st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)

            # 2. Charts: Lead Time by Mode & Regional OTIF Comparison
            ch_col1, ch_col2 = st.columns(2)

            with ch_col1:
                if len(scen_summary.mode_comparison) > 0:
                    mode_chart_data = []
                    for _, row in scen_summary.mode_comparison.iterrows():
                        mode_chart_data.append({
                            "Transport Mode": row["transport_mode"],
                            "Evaluation": "Baseline",
                            "Avg Lead Time (Hours)": row["baseline_avg_lead_time_hours"]
                        })
                        mode_chart_data.append({
                            "Transport Mode": row["transport_mode"],
                            "Evaluation": "Scenario",
                            "Avg Lead Time (Hours)": row["scenario_avg_lead_time_hours"]
                        })
                    fig_mode_lt = px.bar(
                        pd.DataFrame(mode_chart_data),
                        x="Transport Mode",
                        y="Avg Lead Time (Hours)",
                        color="Evaluation",
                        barmode="group",
                        title="Average Lead Time by Modality: Baseline vs. Scenario",
                        color_discrete_map={"Baseline": "#6B7280", "Scenario": "#00D2BA"},
                        text_auto=".2f",
                    )
                    fig_mode_lt.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#E5E7EB"),
                        margin=dict(t=50, b=40, l=40, r=20),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        xaxis=dict(showgrid=False),
                        yaxis=dict(gridcolor="#1F2937"),
                    )
                    st.plotly_chart(fig_mode_lt, use_container_width=True)
                else:
                    st.info("No modal comparisons available.")

            with ch_col2:
                if len(scen_summary.regional_comparison) > 0:
                    reg_chart_data = []
                    for _, row in scen_summary.regional_comparison.iterrows():
                        reg_chart_data.append({
                            "Region": row["region"],
                            "Evaluation": "Baseline",
                            "Standard OTIF (%)": row["baseline_standard_otif_pct"]
                        })
                        reg_chart_data.append({
                            "Region": row["region"],
                            "Evaluation": "Scenario",
                            "Standard OTIF (%)": row["scenario_standard_otif_pct"]
                        })
                    fig_reg_otif = px.bar(
                        pd.DataFrame(reg_chart_data),
                        x="Region",
                        y="Standard OTIF (%)",
                        color="Evaluation",
                        barmode="group",
                        title="Regional Standard OTIF Rate: Baseline vs. Scenario",
                        color_discrete_map={"Baseline": "#6B7280", "Scenario": "#3B82F6"},
                        text_auto=".1f",
                    )
                    fig_reg_otif.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#E5E7EB"),
                        margin=dict(t=50, b=40, l=40, r=20),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        xaxis=dict(showgrid=False),
                        yaxis=dict(gridcolor="#1F2937"),
                    )
                    st.plotly_chart(fig_reg_otif, use_container_width=True)
                else:
                    st.info("No regional comparisons available.")

            # 3. Table of Requests whose on-time status changed
            st.markdown("<div style='font-size: 1.05rem; font-weight: 700; color: #FFFFFF; margin: 18px 0 8px 0;'>Requisitions with Changed On-Time Delivery Status</div>", unsafe_allow_html=True)
            changed_records = scen_df[scen_df["on_time_status_changed"]].copy()

            if len(changed_records) > 0:
                st.caption(f"Showing {len(changed_records):,} requisitions whose on-time status flipped between baseline and scenario.")
                changed_display_cols = [
                    "request_id",
                    "clinic_name",
                    "transport_mode",
                    "target_delivery_hours",
                    "lead_time_hours",
                    "scenario_lead_time_hours",
                    "is_on_time",
                    "scenario_is_on_time",
                ]
                changed_view = changed_records[changed_display_cols].copy()
                changed_view["target_delivery_hours"] = changed_view["target_delivery_hours"].round(2)
                changed_view["lead_time_hours"] = changed_view["lead_time_hours"].round(2)
                changed_view["scenario_lead_time_hours"] = changed_view["scenario_lead_time_hours"].round(2)

                st.dataframe(
                    changed_view,
                    use_container_width=True,
                    height=280,
                    column_config={
                        "request_id": st.column_config.TextColumn("Request ID"),
                        "clinic_name": st.column_config.TextColumn("Destination Health Post"),
                        "transport_mode": st.column_config.TextColumn("Modality"),
                        "target_delivery_hours": st.column_config.NumberColumn("Target SLA", format="%.2f hrs"),
                        "lead_time_hours": st.column_config.NumberColumn("Baseline Lead Time", format="%.2f hrs"),
                        "scenario_lead_time_hours": st.column_config.NumberColumn("Scenario Lead Time", format="%.2f hrs"),
                        "is_on_time": st.column_config.CheckboxColumn("Baseline On-Time"),
                        "scenario_is_on_time": st.column_config.CheckboxColumn("Scenario On-Time"),
                    }
                )
            else:
                st.info("No requisitions changed on-time delivery status under this scenario (timing adjustments did not cause or resolve any delivery SLA breaches).")

            # 4. Downloads: CSV and JSON Exports
            st.markdown("<div style='font-size: 1.05rem; font-weight: 700; color: #FFFFFF; margin: 18px 0 8px 0;'>Export Scenario Telemetry & Analytics</div>", unsafe_allow_html=True)
            dl_col1, dl_col2 = st.columns(2)

            with dl_col1:
                export_cols = [
                    "request_id", "clinic_name", "region", "remote_tier", "product_name", "category",
                    "transport_mode", "target_delivery_hours", "lead_time_hours", "scenario_lead_time_hours",
                    "scenario_prep_change_minutes", "scenario_weather_delay_minutes", "is_on_time",
                    "scenario_is_on_time", "is_delayed", "scenario_is_delayed", "is_standard_otif",
                    "scenario_is_standard_otif", "is_quality_otif", "scenario_is_quality_otif",
                    "raw_order_status", "baseline_order_status_display", "scenario_order_status_display",
                ]
                avail_export_cols = [c for c in export_cols if c in scen_df.columns]
                csv_bytes = scen_df[avail_export_cols].to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download Request-Level Scenario CSV",
                    data=csv_bytes,
                    file_name=f"what_if_scenario_shipments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            with dl_col2:
                json_payload = {
                    "generated_at": datetime.now().isoformat(),
                    "scenario_parameters": {
                        "drone_prep_adj_minutes": scenario_params.drone_prep_adj_minutes,
                        "road_prep_adj_minutes": scenario_params.road_prep_adj_minutes,
                        "weather_delay_minutes": scenario_params.weather_delay_minutes,
                        "weather_categories": list(scenario_params.weather_categories),
                        "weather_modes": list(scenario_params.weather_modes),
                    },
                    "active_filters": {
                        "regions": selected_regions,
                        "date_range": [str(start_filter_date), str(end_filter_date)],
                        "product_categories": selected_categories,
                        "transport_modes": selected_modes,
                        "remote_tiers": selected_tiers,
                    },
                    "summary_metrics": scen_summary.to_dict(),
                }
                json_bytes = json.dumps(json_payload, indent=2).encode("utf-8")
                st.download_button(
                    label="Download Scenario Summary JSON",
                    data=json_bytes,
                    file_name=f"what_if_scenario_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True,
                )
    else:
        st.info("Adjust the scenario parameters above and click **Apply Scenario** to calculate comparative operational metrics.")


# TAB 5: CLINIC & HUB EXPLORER
with chart_tab5:
    st.markdown("""
        <div style="font-size: 1.15rem; font-weight: 700; color: #F3F4F6; margin-bottom: 4px;">
            Clinic & Hub Operational Explorer
        </div>
        <div style="font-size: 0.85rem; color: #9CA3AF; margin-bottom: 14px;">
            Granular drill-down into individual destination health posts and fulfillment hubs under active regional and temporal filters.
        </div>
    """, unsafe_allow_html=True)

    exp_ctrl_col1, exp_ctrl_col2 = st.columns([1, 2])
    with exp_ctrl_col1:
        explorer_loc_type = st.radio(
            "Explore by:",
            ["Clinic", "Hub"],
            horizontal=True,
            key="explorer_loc_type",
            help="Select whether to analyze an individual destination health clinic or a dispatching fulfillment hub."
        )

    with exp_ctrl_col2:
        if explorer_loc_type == "Clinic":
            clinic_dim = engine.df_clinics.sort_values("clinic_name")
            clinic_id_list = clinic_dim["clinic_id"].tolist()
            clinic_name_dict = dict(zip(clinic_dim["clinic_id"], clinic_dim["clinic_name"]))
            selected_loc_id = st.selectbox(
                "Select Destination Health Clinic:",
                options=clinic_id_list,
                format_func=lambda cid: f"{clinic_name_dict.get(cid, cid)} ({cid})",
                key="explorer_clinic_selector",
                help="Searchable clinic selector displaying clinic names while preserving stable internal IDs."
            )
            selected_loc_name = clinic_name_dict.get(selected_loc_id, selected_loc_id)
        else:
            hub_dim = engine.df_hubs.sort_values("hub_name")
            hub_id_list = hub_dim["hub_id"].tolist()
            hub_name_dict = dict(zip(hub_dim["hub_id"], hub_dim["hub_name"]))
            selected_loc_id = st.selectbox(
                "Select Dispatch / Fulfillment Hub:",
                options=hub_id_list,
                format_func=lambda hid: f"{hub_name_dict.get(hid, hid)} ({hid})",
                key="explorer_hub_selector",
                help="Searchable hub selector displaying hub names while preserving stable internal IDs."
            )
            selected_loc_name = hub_name_dict.get(selected_loc_id, selected_loc_id)

    # Location selection applies strictly on top of existing sidebar filters
    df_loc = engine.filter_by_location(df_filtered, explorer_loc_type, selected_loc_id)

    # Build location metadata summary
    hub_name_map = dict(zip(engine.df_hubs["hub_id"], engine.df_hubs["hub_name"]))
    if explorer_loc_type == "Clinic":
        clinic_meta_match = engine.df_clinics[engine.df_clinics["clinic_id"] == selected_loc_id]
        if len(clinic_meta_match) > 0:
            c_meta = clinic_meta_match.iloc[0]
            loc_region = c_meta.get("region", "N/A")
            loc_tier = c_meta.get("remote_tier", "N/A")
            loc_pop = f"{int(c_meta.get('population_served', 0)):,} residents" if pd.notna(c_meta.get("population_served")) else "N/A"
            assigned_hub_id = c_meta.get("nearest_hub", "N/A")
            assigned_hub_display = f"{hub_name_map.get(assigned_hub_id, assigned_hub_id)} ({assigned_hub_id})"
        else:
            loc_region, loc_tier, loc_pop, assigned_hub_display = "N/A", "N/A", "N/A", "N/A"

        # Hubs that actually handled requests for this clinic in the active cohort
        if len(df_loc) > 0 and "hub_id" in df_loc.columns:
            handling_hub_counts = df_loc.groupby("hub_id")["request_id"].count().to_dict()
            handling_hubs_text = ", ".join([f"{hub_name_map.get(h, h)} ({h}): {cnt:,} requests" for h, cnt in handling_hub_counts.items()])
        else:
            handling_hubs_text = "None in active selection"

        meta_col1, meta_col2, meta_col3 = st.columns(3)
        with meta_col1:
            st.markdown(f"""
                <div style="background: rgba(17, 24, 39, 0.7); border: 1px solid rgba(55, 65, 81, 0.7); border-radius: 8px; padding: 10px 14px; font-size: 0.82rem;">
                    <span style="color: #9CA3AF; text-transform: uppercase; font-size: 0.72rem; font-weight: 600;">Clinic Identity</span><br>
                    <b style="color: #00D2BA; font-size: 0.95rem;">{selected_loc_name}</b><br>
                    <span style="color: #E5E7EB;">ID: <code>{selected_loc_id}</code> | Region: <b>{loc_region}</b></span>
                </div>
            """, unsafe_allow_html=True)
        with meta_col2:
            st.markdown(f"""
                <div style="background: rgba(17, 24, 39, 0.7); border: 1px solid rgba(55, 65, 81, 0.7); border-radius: 8px; padding: 10px 14px; font-size: 0.82rem;">
                    <span style="color: #9CA3AF; text-transform: uppercase; font-size: 0.72rem; font-weight: 600;">Accessibility & Demographics</span><br>
                    <span style="color: #E5E7EB;">Remote Tier: <b>{loc_tier}</b></span><br>
                    <span style="color: #E5E7EB;">Catchment Population: <b>{loc_pop}</b></span>
                </div>
            """, unsafe_allow_html=True)
        with meta_col3:
            st.markdown(f"""
                <div style="background: rgba(17, 24, 39, 0.7); border: 1px solid rgba(55, 65, 81, 0.7); border-radius: 8px; padding: 10px 14px; font-size: 0.82rem;">
                    <span style="color: #9CA3AF; text-transform: uppercase; font-size: 0.72rem; font-weight: 600;">Hub Network Topology</span><br>
                    <span style="color: #E5E7EB;">Assigned Hub: <b>{assigned_hub_display}</b></span><br>
                    <span style="color: #9CA3AF; font-size: 0.76rem;">Actual Fulfilling Hubs: {handling_hubs_text}</span>
                </div>
            """, unsafe_allow_html=True)
    else:
        hub_meta_match = engine.df_hubs[engine.df_hubs["hub_id"] == selected_loc_id]
        if len(hub_meta_match) > 0:
            h_meta = hub_meta_match.iloc[0]
            loc_region = h_meta.get("region", "N/A")
            loc_radius = f"{h_meta.get('serviced_radius_km', 'N/A')} km"
            loc_fleet = f"{h_meta.get('vehicle_fleet_size', 'N/A')} vehicles"
        else:
            loc_region, loc_radius, loc_fleet = "N/A", "N/A", "N/A"

        clinics_represented = df_loc["clinic_id"].nunique() if len(df_loc) > 0 else 0
        total_clinics_assigned = len(engine.df_clinics[engine.df_clinics["nearest_hub"] == selected_loc_id])
        req_share = (len(df_loc) / len(df_filtered) * 100.0) if len(df_filtered) > 0 else 0.0

        meta_col1, meta_col2, meta_col3 = st.columns(3)
        with meta_col1:
            st.markdown(f"""
                <div style="background: rgba(17, 24, 39, 0.7); border: 1px solid rgba(55, 65, 81, 0.7); border-radius: 8px; padding: 10px 14px; font-size: 0.82rem;">
                    <span style="color: #9CA3AF; text-transform: uppercase; font-size: 0.72rem; font-weight: 600;">Hub Identity</span><br>
                    <b style="color: #3B82F6; font-size: 0.95rem;">{selected_loc_name}</b><br>
                    <span style="color: #E5E7EB;">ID: <code>{selected_loc_id}</code> | Region: <b>{loc_region}</b></span>
                </div>
            """, unsafe_allow_html=True)
        with meta_col2:
            st.markdown(f"""
                <div style="background: rgba(17, 24, 39, 0.7); border: 1px solid rgba(55, 65, 81, 0.7); border-radius: 8px; padding: 10px 14px; font-size: 0.82rem;">
                    <span style="color: #9CA3AF; text-transform: uppercase; font-size: 0.72rem; font-weight: 600;">Capacity & Service Radius</span><br>
                    <span style="color: #E5E7EB;">Configured Fleet: <b>{loc_fleet}</b></span><br>
                    <span style="color: #E5E7EB;">Service Radius: <b>{loc_radius}</b></span>
                </div>
            """, unsafe_allow_html=True)
        with meta_col3:
            st.markdown(f"""
                <div style="background: rgba(17, 24, 39, 0.7); border: 1px solid rgba(55, 65, 81, 0.7); border-radius: 8px; padding: 10px 14px; font-size: 0.82rem;">
                    <span style="color: #9CA3AF; text-transform: uppercase; font-size: 0.72rem; font-weight: 600;">Network Reach & Volume</span><br>
                    <span style="color: #E5E7EB;">Clinics Represented in Selection: <b>{clinics_represented:,}</b> (of {total_clinics_assigned} assigned)</span><br>
                    <span style="color: #9CA3AF; font-size: 0.76rem;">Selected Request Share: {len(df_loc):,} orders ({req_share:.1f}% of filtered requests)</span>
                </div>
            """, unsafe_allow_html=True)

    # Active Sidebar Filters summary bar
    active_filters_text = (
        f"Regions: {', '.join(selected_regions) if selected_regions else 'All'} | "
        f"Dates: {start_filter_date} to {end_filter_date} | "
        f"Categories: {', '.join(selected_categories) if selected_categories else 'All'} | "
        f"Modes: {', '.join(selected_modes) if selected_modes else 'All'} | "
        f"Tiers: {', '.join(selected_tiers) if selected_tiers else 'All'}"
    )
    st.markdown(f"""
        <div style="background: rgba(31, 41, 55, 0.5); border-left: 3px solid #6366F1; padding: 6px 12px; margin: 8px 0 14px 0; border-radius: 0 6px 6px 0; font-size: 0.76rem; color: #9CA3AF;">
            <b>Active Context Filters Intersecting Location:</b> {active_filters_text}
        </div>
    """, unsafe_allow_html=True)

    # Handle Empty / Inactive Location Case
    if len(df_loc) == 0:
        st.warning(f"**No requests in this selection** for {selected_loc_name} ({selected_loc_id}). Active sidebar filters or operational inactivity exclude any matching records.")
        
        # Display zero counts and N/A rates as required by Requirement 6
        kpi_row1_c1, kpi_row1_c2, kpi_row1_c3, kpi_row1_c4, kpi_row1_c5 = st.columns(5)
        kpi_row1_c1.metric("Total Requisitions", "0", help="Total requisition requests in active selection.")
        kpi_row1_c2.metric("Delivered Orders", "0", help="Delivered requisitions with verified receipt.")
        kpi_row1_c3.metric("Actual Dispatches", "0", help="Shipments with recorded dispatch timestamp.")
        kpi_row1_c4.metric("Stock-Out Rate", "N/A", help="Stock-out frequency.")
        kpi_row1_c5.metric("Standard OTIF", "N/A", help="On-Time In-Full fulfillment rate.")

        kpi_row2_c1, kpi_row2_c2, kpi_row2_c3, kpi_row2_c4, kpi_row2_c5 = st.columns(5)
        kpi_row2_c1.metric("Quality OTIF (OTIF-Q)", "N/A", help="Standard OTIF with thermal quality compliance.")
        kpi_row2_c2.metric("Avg Delivered Lead Time", "N/A", help="Average transit and prep lead time.")
        kpi_row2_c3.metric("90th-Percentile Lead Time", "N/A", help="P90 delivered lead time.")
        kpi_row2_c4.metric("Cold-Chain Integrity", "N/A", help="Verified thermal pass rate.")
        kpi_row2_c5.metric("Unknown Quality Count", "0", help="Delivered cold-chain orders with missing quality audit.")
    else:
        # Compute location performance KPIs reusing existing metrics engine
        loc_kpis = engine.compute_location_kpis(df_loc)

        # Performance KPI Scorecard
        st.markdown("<div style='font-size: 1.0rem; font-weight: 700; color: #FFFFFF; margin: 12px 0 8px 0;'>Location Operational Scorecard</div>", unsafe_allow_html=True)
        kpi_row1_c1, kpi_row1_c2, kpi_row1_c3, kpi_row1_c4, kpi_row1_c5 = st.columns(5)
        kpi_row1_c1.metric("Total Requisitions", f"{loc_kpis.total_requests:,}")
        kpi_row1_c2.metric(
            "Delivered Orders",
            f"{loc_kpis.delivered_requests:,}",
            help=f"Denominator: {loc_kpis.total_requests:,} total requests ({loc_kpis.delivered_requests/loc_kpis.total_requests*100:.1f}%)" if loc_kpis.total_requests > 0 else None
        )
        kpi_row1_c3.metric(
            "Actual Dispatches",
            f"{loc_kpis.actual_dispatches:,}",
            help=f"Denominator: {loc_kpis.total_requests:,} total requests ({loc_kpis.actual_dispatches/loc_kpis.total_requests*100:.1f}%)" if loc_kpis.total_requests > 0 else None
        )
        kpi_row1_c4.metric(
            "Stock-Out Rate",
            f"{loc_kpis.stock_out_rate_pct:.1f}%" if loc_kpis.stock_out_rate_pct is not None else "N/A",
            help=f"Denominator: {loc_kpis.total_requests:,} total requests ({loc_kpis.stock_outs:,} stock-outs)"
        )
        kpi_row1_c5.metric(
            "Standard OTIF",
            f"{loc_kpis.standard_otif_rate_pct:.1f}%" if loc_kpis.standard_otif_rate_pct is not None else "N/A",
            help=f"Denominator: {loc_kpis.total_requests:,} total requests (On-Time & In-Full)"
        )

        kpi_row2_c1, kpi_row2_c2, kpi_row2_c3, kpi_row2_c4, kpi_row2_c5 = st.columns(5)
        kpi_row2_c1.metric(
            "Quality OTIF (OTIF-Q)",
            f"{loc_kpis.quality_otif_rate_pct:.1f}%" if loc_kpis.quality_otif_rate_pct is not None else "N/A",
            help=f"Denominator: {loc_kpis.total_requests:,} total requests (Standard OTIF & Quality Pass)"
        )
        kpi_row2_c2.metric(
            "Avg Delivered Lead Time",
            f"{loc_kpis.avg_lead_time_hours:.2f} hrs" if loc_kpis.avg_lead_time_hours is not None else "N/A",
            help=f"Denominator: {loc_kpis.delivered_requests:,} delivered orders"
        )
        kpi_row2_c3.metric(
            "90th-Percentile Lead Time",
            f"{loc_kpis.p90_lead_time_hours:.2f} hrs" if loc_kpis.p90_lead_time_hours is not None else "N/A",
            help=f"Denominator: {loc_kpis.delivered_requests:,} delivered orders"
        )
        known_cold_count = loc_kpis.total_delivered_cold_orders - loc_kpis.unknown_quality_cold_orders
        kpi_row2_c4.metric(
            "Cold-Chain Integrity",
            f"{loc_kpis.cold_chain_integrity_pct:.1f}%" if loc_kpis.cold_chain_integrity_pct is not None else "N/A",
            help=f"Denominator: {known_cold_count:,} delivered cold orders with verified audit status" if known_cold_count > 0 else "No audited cold-chain deliveries"
        )
        kpi_row2_c5.metric(
            "Unknown Quality Count",
            f"{loc_kpis.unknown_quality_cold_orders:,}",
            help=f"Delivered cold-chain orders with missing audit telemetry (excluded from compliance denominator)"
        )

        # Focused Diagnostics (Requirement 4)
        st.markdown("<div style='font-size: 1.0rem; font-weight: 700; color: #FFFFFF; margin: 20px 0 8px 0;'>Focused Location Diagnostics</div>", unsafe_allow_html=True)
        diag_col1, diag_col2 = st.columns(2)

        with diag_col1:
            st.markdown("<div style='font-size: 0.88rem; font-weight: 600; color: #E5E7EB; margin-bottom: 6px;'>Weekly Request Volume & OTIF Attainment</div>", unsafe_allow_html=True)
            df_loc_trend = engine.get_weekly_trend(df_loc)
            if len(df_loc_trend) > 0:
                fig_loc_trend = go.Figure()
                fig_loc_trend.add_trace(go.Bar(
                    x=df_loc_trend["week_start"],
                    y=df_loc_trend["total_requests"],
                    name="Request Volume",
                    marker_color="#3B82F6",
                    yaxis="y",
                    opacity=0.6,
                ))
                fig_loc_trend.add_trace(go.Scatter(
                    x=df_loc_trend["week_start"],
                    y=df_loc_trend["standard_otif_rate_pct"],
                    name="Standard OTIF (%)",
                    line=dict(color="#00D2BA", width=2.5),
                    mode="lines+markers",
                    yaxis="y2",
                ))
                fig_loc_trend.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#E5E7EB"),
                    margin=dict(t=30, b=40, l=40, r=40),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    xaxis=dict(showgrid=False),
                    yaxis=dict(title="Requisition Volume", gridcolor="#1F2937"),
                    yaxis2=dict(title="Standard OTIF (%)", overlaying="y", side="right", range=[0, 105], showgrid=False),
                    height=280,
                )
                st.plotly_chart(fig_loc_trend, use_container_width=True)
            else:
                st.info("Insufficient longitudinal data for weekly trends.")

        with diag_col2:
            st.markdown("<div style='font-size: 0.88rem; font-weight: 600; color: #E5E7EB; margin-bottom: 6px;'>Medical Product Breakdown & SLA Risk</div>", unsafe_allow_html=True)
            prod_diag_df = engine.get_location_product_diagnostics(df_loc)
            if len(prod_diag_df) > 0:
                st.dataframe(
                    prod_diag_df,
                    use_container_width=True,
                    height=280,
                    hide_index=True,
                    column_config={
                        "product_name": st.column_config.TextColumn("Product"),
                        "category": st.column_config.TextColumn("Category"),
                        "request_count": st.column_config.NumberColumn("Requests", format="%d"),
                        "delivered_count": st.column_config.NumberColumn("Delivered", format="%d"),
                        "late_delivery_count": st.column_config.NumberColumn("Late Delivered", format="%d"),
                        "delay_rate_pct": st.column_config.NumberColumn("Delay Rate", format="%.1f%%"),
                        "stock_outs": st.column_config.NumberColumn("Stock-Outs", format="%d"),
                        "unmet_units": st.column_config.NumberColumn("Unmet Units", format="%d"),
                    }
                )
            else:
                st.info("No product demand recorded.")

        # Request Ledger & CSV Export
        st.markdown("<div style='font-size: 0.95rem; font-weight: 700; color: #FFFFFF; margin: 18px 0 6px 0;'>Filtered Location Requisition Ledger</div>", unsafe_allow_html=True)
        ledger_cols = [
            "request_id", "product_name", "transport_mode", "target_delivery_hours",
            "lead_time_hours", "order_status_display", "cold_chain_breach", "storage_requirement"
        ]
        avail_ledger_cols = [c for c in ledger_cols if c in df_loc.columns]
        ledger_view = df_loc[avail_ledger_cols].copy()
        
        # Friendly cold chain audit display
        if "cold_chain_breach" in ledger_view.columns:
            def format_quality(row):
                if row.get("storage_requirement") != "Cold Chain":
                    return "Ambient (Exempt)"
                if pd.isna(row.get("cold_chain_breach")):
                    return "Unknown (Missing Audit)"
                return "Pass (No Breach)" if row.get("cold_chain_breach") is False else "Fail (Thermal Breach)"
            ledger_view["cold_chain_quality"] = ledger_view.apply(format_quality, axis=1)
            drop_cols = [c for c in ["cold_chain_breach", "storage_requirement"] if c in ledger_view.columns]
            ledger_view = ledger_view.drop(columns=drop_cols)

        st.dataframe(
            ledger_view,
            use_container_width=True,
            height=250,
            column_config={
                "request_id": st.column_config.TextColumn("Request ID"),
                "product_name": st.column_config.TextColumn("Product"),
                "transport_mode": st.column_config.TextColumn("Modality"),
                "target_delivery_hours": st.column_config.NumberColumn("SLA Deadline", format="%.2f hrs"),
                "lead_time_hours": st.column_config.NumberColumn("Delivered Lead Time", format="%.2f hrs"),
                "order_status_display": st.column_config.TextColumn("Recalculated Status"),
                "cold_chain_quality": st.column_config.TextColumn("Cold-Chain Quality"),
            }
        )

        # CSV Download for selected location's filtered requests
        loc_csv_bytes = df_loc.to_csv(index=False).encode("utf-8")
        st.download_button(
            label=f"Download Filtered {explorer_loc_type} Requisitions CSV ({len(df_loc):,} records)",
            data=loc_csv_bytes,
            file_name=f"{explorer_loc_type.lower()}_{selected_loc_id}_filtered_requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        # Connect Existing Simulator (Requirement 5)
        st.markdown("<div style='font-size: 1.05rem; font-weight: 700; color: #FFFFFF; margin: 24px 0 4px 0;'>Location What-If Scenario Simulator</div>", unsafe_allow_html=True)
        st.caption(f"Evaluate sensitivity of delivery timing and SLA attainment specifically for **{selected_loc_name} ({selected_loc_id})** (Cohort: N = {len(df_loc):,}).")

        # Invalidate local scenario when location or sidebar filters change
        current_loc_sig = (
            explorer_loc_type,
            selected_loc_id,
            tuple(sorted(selected_regions)) if selected_regions else (),
            str(start_filter_date),
            str(end_filter_date),
            tuple(sorted(selected_categories)) if selected_categories else (),
            tuple(sorted(selected_modes)) if selected_modes else (),
            tuple(sorted(selected_tiers)) if selected_tiers else (),
        )

        if st.session_state.get("explorer_loc_scen_applied", False):
            if st.session_state.get("explorer_scen_sig") != current_loc_sig:
                st.warning("Selected location or active sidebar filters have changed. Re-apply scenario to calculate results for the updated cohort.")
                st.session_state["explorer_loc_scen_applied"] = False

        with st.form(key="explorer_scenario_form"):
            loc_scen_col1, loc_scen_col2 = st.columns(2)
            with loc_scen_col1:
                st.markdown("<div style='font-size: 0.88rem; font-weight: 600; color: #00D2BA; margin-bottom: 8px;'>Dispatch Preparation Adjustments</div>", unsafe_allow_html=True)
                loc_drone_prep = st.slider(
                    "Drone Prep Adjustment (mins)",
                    min_value=-30, max_value=120,
                    value=int(st.session_state.get("exp_scen_drone_prep", 0)),
                    step=5,
                    key="loc_drone_prep_slider",
                )
                loc_road_prep = st.slider(
                    "Road Prep Adjustment (mins)",
                    min_value=-60, max_value=240,
                    value=int(st.session_state.get("exp_scen_road_prep", 0)),
                    step=5,
                    key="loc_road_prep_slider",
                )
            with loc_scen_col2:
                st.markdown("<div style='font-size: 0.88rem; font-weight: 600; color: #F59E0B; margin-bottom: 8px;'>Severe Weather Transit Delay</div>", unsafe_allow_html=True)
                loc_weather_delay = st.slider(
                    "Severe Weather Delay (mins)",
                    min_value=0, max_value=180,
                    value=int(st.session_state.get("exp_scen_weather_delay", 0)),
                    step=5,
                    key="loc_weather_delay_slider",
                )
                avail_weather = sorted(engine.df_master["weather_condition"].dropna().unique().tolist())
                loc_weather_cats = st.multiselect(
                    "Weather Categories Subject to Delay",
                    options=avail_weather,
                    default=st.session_state.get("exp_scen_weather_cats", [c for c in ["Heavy Rain", "Severe Storm/Flood"] if c in avail_weather]),
                    key="loc_weather_cats_select",
                )
                loc_weather_modes = st.multiselect(
                    "Transport Modes Subject to Weather Delay",
                    options=["Drone", "Road"],
                    default=st.session_state.get("exp_scen_weather_modes", ["Drone", "Road"]),
                    key="loc_weather_modes_select",
                )

            loc_apply_submitted = st.form_submit_button("Apply Location Scenario", type="primary", use_container_width=True)

        loc_reset_col1, _ = st.columns([1, 3])
        with loc_reset_col1:
            if st.button("Reset Location Scenario", use_container_width=True, key="reset_loc_scen_btn"):
                st.session_state["explorer_loc_scen_applied"] = False
                st.session_state["exp_scen_drone_prep"] = 0
                st.session_state["exp_scen_road_prep"] = 0
                st.session_state["exp_scen_weather_delay"] = 0
                st.session_state["exp_scen_weather_cats"] = [c for c in ["Heavy Rain", "Severe Storm/Flood"] if c in avail_weather]
                st.session_state["exp_scen_weather_modes"] = ["Drone", "Road"]
                st.rerun()

        if loc_apply_submitted:
            st.session_state["explorer_loc_scen_applied"] = True
            st.session_state["explorer_scen_sig"] = current_loc_sig
            st.session_state["exp_scen_drone_prep"] = loc_drone_prep
            st.session_state["exp_scen_road_prep"] = loc_road_prep
            st.session_state["exp_scen_weather_delay"] = loc_weather_delay
            st.session_state["exp_scen_weather_cats"] = loc_weather_cats
            st.session_state["exp_scen_weather_modes"] = loc_weather_modes
            st.rerun()

        if st.session_state.get("explorer_loc_scen_applied", False):
            loc_scenario_params = ScenarioParameters(
                drone_prep_adj_minutes=float(st.session_state.get("exp_scen_drone_prep", 0)),
                road_prep_adj_minutes=float(st.session_state.get("exp_scen_road_prep", 0)),
                weather_delay_minutes=float(st.session_state.get("exp_scen_weather_delay", 0)),
                weather_categories=tuple(st.session_state.get("exp_scen_weather_cats", ["Heavy Rain", "Severe Storm/Flood"])),
                weather_modes=tuple(st.session_state.get("exp_scen_weather_modes", ["Drone", "Road"])),
            )

            loc_scen_res = simulate_scenario(df_loc, loc_scenario_params)
            loc_scen_df = loc_scen_res.df
            loc_scen_summary = loc_scen_res.summary

            st.markdown(f"<div style='font-size: 0.95rem; font-weight: 700; color: #FFFFFF; margin: 16px 0 8px 0;'>Simulation Outcomes: {selected_loc_name} ({selected_loc_id})</div>", unsafe_allow_html=True)
            
            loc_comp_rows = []
            for m in loc_scen_summary.metric_rows:
                base_v = f"{m.baseline_value:.2f} {m.unit}" if m.baseline_value is not None else "N/A"
                scen_v = f"{m.scenario_value:.2f} {m.unit}" if m.scenario_value is not None else "N/A"
                if m.change_value is not None:
                    chg_v = f"{m.change_value:+.2f} pp" if m.is_percentage_point else f"{m.change_value:+.2f} {m.unit}"
                else:
                    chg_v = "N/A"
                loc_comp_rows.append({
                    "Operational Metric": m.metric_name,
                    "Baseline": base_v,
                    "Scenario": scen_v,
                    "Change": chg_v,
                    "Denominator Basis": m.denominator_explanation,
                })
            st.dataframe(pd.DataFrame(loc_comp_rows), use_container_width=True, hide_index=True)

            # Requisitions with Changed Status
            loc_changed = loc_scen_df[loc_scen_df["on_time_status_changed"]].copy()
            if len(loc_changed) > 0:
                st.caption(f"{len(loc_changed):,} requisitions changed on-time delivery status for this location.")
                changed_cols = [
                    "request_id", "product_name", "transport_mode", "target_delivery_hours",
                    "lead_time_hours", "scenario_lead_time_hours", "is_on_time", "scenario_is_on_time"
                ]
                avail_chg_cols = [c for c in changed_cols if c in loc_changed.columns]
                st.dataframe(loc_changed[avail_chg_cols], use_container_width=True, height=200)

            # Export Location Scenario CSV
            loc_exp_cols = [
                "request_id", "clinic_name", "region", "remote_tier", "product_name", "category",
                "transport_mode", "target_delivery_hours", "lead_time_hours", "scenario_lead_time_hours",
                "scenario_prep_change_minutes", "scenario_weather_delay_minutes", "is_on_time",
                "scenario_is_on_time", "is_delayed", "scenario_is_delayed", "is_standard_otif",
                "scenario_is_standard_otif", "is_quality_otif", "scenario_is_quality_otif",
                "raw_order_status", "baseline_order_status_display", "scenario_order_status_display",
            ]
            avail_loc_exp = [c for c in loc_exp_cols if c in loc_scen_df.columns]
            loc_scen_csv = loc_scen_df[avail_loc_exp].to_csv(index=False).encode("utf-8")
            st.download_button(
                label=f"Download {selected_loc_name} Scenario CSV ({len(loc_scen_df):,} records)",
                data=loc_scen_csv,
                file_name=f"{explorer_loc_type.lower()}_{selected_loc_id}_scenario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="dl_loc_scen_csv",
            )
        else:
            st.info("Adjust local scenario parameters above and click **Apply Location Scenario** to simulate operational impact on this location.")



# -----------------------------------------------------------------------------
# 8. Deep-Dive Transactional Data Grid & Record Inspection
# -----------------------------------------------------------------------------
st.markdown("""
    <div class="section-header">
        <span>Deep-Dive Transactional Shipment Ledger</span>
        <span class="section-badge">Grain: Individual Requisition</span>
    </div>
""", unsafe_allow_html=True)

table_control_col1, table_control_col2, table_control_col3 = st.columns([2, 1, 1])

with table_control_col1:
    search_query = st.text_input("Search Clinic, Request ID, or Product (Literal Text)", placeholder="e.g., Donkorkrom, Antivenom, REQ-2025-000452")

with table_control_col2:
    status_filter = st.selectbox("Order Status Filter", ["All Statuses", "Delivered (On-Time)", "Delivered (Delayed)", "Stock-Out"])

with table_control_col3:
    limit_rows = st.selectbox("Display Row Limit", [50, 100, 250, 1000], index=1)

# Apply ledger filters using extracted reusable search function
df_ledger = filter_shipment_ledger(df_filtered, search_query=search_query, status_filter=status_filter)

display_columns = [
    "request_id",
    "requested_timestamp",
    "clinic_name",
    "nearest_hub",
    "region",
    "remote_tier",
    "product_name",
    "category",
    "transport_mode",
    "distance_km",
    "lead_time_hours",
    "target_delivery_hours",
    "order_status_display",
    "is_on_time",
    "is_standard_otif",
    "cold_chain_breach",
    "weather_condition",
]

# Ensure display columns exist
available_display_cols = [c for c in display_columns if c in df_ledger.columns]

st.dataframe(
    df_ledger[available_display_cols].head(limit_rows),
    use_container_width=True,
    height=340,
    column_config={
        "request_id": st.column_config.TextColumn("Request ID", width="medium"),
        "requested_timestamp": st.column_config.DatetimeColumn("Requested At", format="YYYY-MM-DD HH:mm"),
        "clinic_name": st.column_config.TextColumn("Destination Health Post"),
        "nearest_hub": st.column_config.TextColumn("Assigned Hub", width="small"),
        "region": st.column_config.TextColumn("Region", width="small"),
        "remote_tier": st.column_config.TextColumn("Tier", width="small"),
        "product_name": st.column_config.TextColumn("Medical Cargo"),
        "category": st.column_config.TextColumn("Category"),
        "transport_mode": st.column_config.TextColumn("Modality", width="small"),
        "distance_km": st.column_config.NumberColumn("Distance (km)", format="%.1f km"),
        "lead_time_hours": st.column_config.NumberColumn("Lead Time", format="%.2f hrs"),
        "target_delivery_hours": st.column_config.NumberColumn("Target SLA", format="%.2f hrs"),
        "order_status_display": st.column_config.TextColumn("Status", width="medium"),
        "is_on_time": st.column_config.CheckboxColumn("On-Time"),
        "is_standard_otif": st.column_config.CheckboxColumn("Std OTIF"),
        "cold_chain_breach": st.column_config.CheckboxColumn("Cold Breach"),
        "weather_condition": st.column_config.TextColumn("Weather"),
    }
)

csv_data = df_ledger[available_display_cols].to_csv(index=False).encode("utf-8")
st.download_button(
    label="Export Filtered Shipment Records (CSV)",
    data=csv_data,
    file_name=f"ghana_healthcare_logistics_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv",
)

# -----------------------------------------------------------------------------
# 9. Architectural & Methodological Documentation
# -----------------------------------------------------------------------------
with st.expander("Technical Architecture, Star Schema & Methodological Notes"):
    st.markdown("""
    ### Data Engineering & Mathematical Methodology

    #### 1. Star Schema Relational Mapping
    - **Fact Table (`fact_shipments`)**: Granularity is one individual logistics request. Keys link to `dim_clinics`, `dim_products`, and `dim_hubs`.
    - **Geodesic Distance Calculation**: Great-circle geodesic distance derived via the **Haversine formula**:
      $$d = 2r \\arcsin \\left( \\sqrt{\\sin^2\\left(\\frac{\\Delta \\phi}{2}\\right) + \\cos(\\phi_1)\\cos(\\phi_2)\\sin^2\\left(\\frac{\\Delta \\lambda}{2}\\right)} \\right)$$
      Road transit paths apply a curvature winding penalty $\\omega \\in [1.35, 1.85]$ reflecting rural terrain degradation.

    #### 2. Supply Chain OTIF (On-Time In-Full) Definitions
    - **Standard OTIF**:
      $$\\text{Standard OTIF} \\iff \\text{On-Time} \\land \\text{In-Full}$$
      $$\\text{Standard OTIF Rate (\\%)} = \\frac{\\sum (\\mathbb{I}(\\text{OnTime}) \\cdot \\mathbb{I}(\\text{InFull}))}{\\text{Total Requests}} \\times 100$$
    - **Quality-Adjusted OTIF (OTIF-Q)**:
      $$\\text{OTIF-Q} \\iff \\text{Standard OTIF} \\land \\text{QualityPass}$$
      *Quality-Adjusted OTIF strictly requires verified thermal compliance. Unverified items with missing telemetry fail OTIF-Q.*

    #### 3. Regional Bottleneck Composite Index
    Normalized against a stable operational reference of 12.0 hours (benchmark max acceptable lead time):
    $$\\text{Bottleneck Index} = 0.35 \\times \\text{StockOut\\%} + 0.35 \\times \\text{Delay\\%} + 20 \\times \\min\\left(1.0, \\frac{\\bar{T}_{\\text{lead}}}{12.0}\\right) + 0.10 \\times \\text{ColdBreach\\%}$$

    #### 4. Operational Risk Threshold Rationale & Demonstration Assumptions
    *The risk categorization thresholds below represent configurable demonstration and scenario analysis assumptions engineered for interactive operational drill-down across healthcare logistics models, rather than statutory clinical or regulatory mandates:*
    - **Optimal Demonstration Benchmark (Standard OTIF $\\ge 80\\%$)**: Target reliability corridor where at least 4 out of 5 critical requisitions arrive strictly on-time and in-full.
    - **Moderate Risk (Standard OTIF $65\\% \\le \\text{Rate} < 80\\%$)**: Represents an unstable intermediate operational corridor with elevated lead-time volatility requiring higher safety stock buffers.
    - **High Risk (Standard OTIF $< 65\\%$ or Stockout Rate $> 8\\%$)**: Identifies severe delivery bottlenecks and stockout vulnerabilities for targeted resource reallocation (e.g., anti-snake venom, emergency blood transfusion, and neonatal resuscitation).

    #### 5. Fleet Model Scope Notice
    *Fleet capacity constraints (discrete vehicle counts), maximum payload weight limits, and service-radius eligibility criteria are recorded in dimension schemas but are not yet enforced in dispatch allocation logic.*

    #### 6. What-If Scenario Simulator Methodology & Scope
    - **Preparation Time Adjustment**:
      $$T_{\\text{new\\_prep}} = \\max\\left(0, T_{\\text{base\\_prep}} + \\Delta_{\\text{mode}}\\right)$$
      $$\\Delta T_{\\text{prep}} = T_{\\text{new\\_prep}} - T_{\\text{base\\_prep}}$$
      Mode-specific adjustments apply to drone ($-30$ to $+120$ min) and road ($-60$ to $+240$ min) staging. Preparation reductions are strictly floored at 0 minutes.
    - **Severe Weather Delay**: Applied once per delivered requisition when both weather category and transport mode match active scenario controls ($\\Delta T_{\\text{weather}}$).
    - **Scenario Lead Time**:
      $$T_{\\text{scenario}} = T_{\\text{lead\\_base}} + \\Delta T_{\\text{prep}} + \\Delta T_{\\text{weather}}$$
    - **Stated Denominators**:
      - Average Lead Time, 90th-percentile Lead Time, and On-Time Delivery Rate are evaluated strictly over **delivered requests** ($N_{\\text{delivered}}$).
      - Standard OTIF Rate and Quality-Adjusted OTIF (OTIF-Q) are evaluated over **all selected requests** ($N_{\\text{total}}$).
    - **Simulation Scope & Boundary Assumptions**:
      - This simulation changes timing only.
      - Cold-chain quality audit outcomes and hub inventory availability are held constant.
      - Fleet capacity constraints (discrete vehicle counts), queuing at hubs, payload weight feasibility, mode switching, and dynamic cold-chain breach generation/resolution are outside this simulator's scope.
    """)
