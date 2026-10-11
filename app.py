"""Rural Healthcare Supply Chain & Logistics Analytics Dashboard.

Ghana Medical Drone & Ground Fleet Logistics Network (Zipline & GHS Operational Model).
Comprehensive operational telemetry and multi-modal logistics performance analytics.
"""

from datetime import datetime
from typing import Optional
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.metrics_engine import SupplyChainMetricsEngine, ExecutiveKPIs, filter_shipment_ledger
from src.map_visualizer import build_pydeck_logistics_map, build_plotly_geographic_scatter

# -----------------------------------------------------------------------------
# 1. Page Configuration & Custom CSS Injection
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Ghana Rural Healthcare Logistics Telemetry",
    page_icon="🚁",
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

engine = get_metrics_engine()


# -----------------------------------------------------------------------------
# 3. Sidebar Filtering Controls
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
            <div style="background: linear-gradient(135deg, #00D2BA, #3B82F6); padding: 8px; border-radius: 10px; font-size: 20px;">🚁</div>
            <div>
                <div style="font-weight: 800; font-size: 1.05rem; color: #FFFFFF; line-height: 1.2;">AERO-MED GHANA</div>
                <div style="font-size: 0.72rem; color: #00D2BA; letter-spacing: 0.05em; font-weight: 600;">LOGISTICS TELEMETRY</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🎛️ Multidimensional Filters")

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
    st.markdown("### 🗺️ Map Display Preferences")
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
        <span>ℹ️</span>
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
    st.warning("⚠️ No shipment records match the selected filter criteria. Please broaden your selection in the sidebar.")

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
            <div class="metric-sub neutral">📦 Delivered: <b>{kpis.delivered_orders:,}</b> &nbsp;•&nbsp; Stock-outs: <b>{kpis.stock_outs:,}</b></div>
        </div>
    """, unsafe_allow_html=True)

with row1_col2:
    deliv_rate_str = fmt_pct(kpis.delivery_success_rate_pct)
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Delivery Success Rate</div>
            <div class="metric-value" style="color: #10B981;">{deliv_rate_str}</div>
            <div class="metric-sub positive">✅ On-Time: <b>{kpis.on_time_orders:,}</b> &nbsp;•&nbsp; Late: <b>{kpis.delayed_orders:,}</b></div>
        </div>
    """, unsafe_allow_html=True)

with row1_col3:
    avg_lt_str = f"{kpis.avg_lead_time_hours:.1f}" if kpis.avg_lead_time_hours is not None else "N/A"
    if kpis.drone_road_delta_hours is not None:
        delta_sub = f"⚡ Diff in avg simulated lead time: <b>-{kpis.drone_road_delta_hours:.1f} hrs</b> (Drone vs Road)"
    elif kpis.drone_avg_lead_time_hours is not None:
        delta_sub = f"⚡ Drone-only active ({kpis.drone_avg_lead_time_hours:.1f} hrs)"
    elif kpis.road_avg_lead_time_hours is not None:
        delta_sub = f"🚗 Road-only active ({kpis.road_avg_lead_time_hours:.1f} hrs)"
    else:
        delta_sub = "⚡ No deliveries in view"

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
            <div class="metric-sub">🎯 Strict SLA: On-Time & In-Full</div>
        </div>
    """, unsafe_allow_html=True)

with row2_col2:
    qual_otif_str = fmt_pct(kpis.quality_otif_rate_pct)
    st.markdown(f"""
        <div class="metric-card purple">
            <div class="metric-title">Quality OTIF (OTIF-Q)</div>
            <div class="metric-value" style="color: #A78BFA;">{qual_otif_str}</div>
            <div class="metric-sub">❄️ Standard OTIF + Thermal Compliance</div>
        </div>
    """, unsafe_allow_html=True)

with row2_col3:
    cold_str = fmt_pct(kpis.cold_chain_integrity_pct)
    unknown_note = f" (Unknown: {kpis.unknown_quality_cold_orders})" if kpis.unknown_quality_cold_orders > 0 else ""
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Cold-Chain Thermal Integrity</div>
            <div class="metric-value" style="color: {'#10B981' if kpis.cold_chain_integrity_pct and kpis.cold_chain_integrity_pct >= 95 else '#F59E0B'};">{cold_str}</div>
            <div class="metric-sub">❄️ Denom: {kpis.total_delivered_cold_orders:,} Delivered Cold Items{unknown_note}</div>
        </div>
    """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 6. Geospatial Mapping Section
# -----------------------------------------------------------------------------
st.markdown("""
    <div class="section-header">
        <span>📍 Geospatial Distribution Network & Illustrative Supply Corridors</span>
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
            st.warning(f"⚠️ Unmapped Hub Relationships: {len(unmapped)} clinic(s) could not be matched to an active hub: {', '.join(unmapped[:3])}")
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
        legend_nodes_html = """<div style="font-weight: 600; color: #E2E8F0; margin: 10px 0 6px 0; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px;">Clinic Risk Classification</div>
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
• <b>&ge; 80%</b>: Meets emergency target reliability benchmarks.<br>
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
<div style="font-weight: 700; color: #00D2BA; margin-bottom: 12px; font-size: 0.95rem; display: flex; align-items: center; gap: 6px;">
    <span>🗺️</span> <span>Network Topology Legend</span>
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
            st.markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #EF4444; margin: 12px 0 6px 0;'>⚠️ Critical Bottleneck Clinics:</div>", unsafe_allow_html=True)
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
        <span>📊 Operational Performance & Modal Efficiency Breakdown</span>
        <span class="section-badge">Drone Velocity vs. Rural Road Logistics</span>
    </div>
""", unsafe_allow_html=True)

chart_tab1, chart_tab2, chart_tab3 = st.tabs([
    "🚀 Transport Efficiency (Drone vs. Road)",
    "📈 Weekly OTIF & Fulfillment Trends",
    "⚠️ Regional Bottlenecks & Stock-Out Diagnostics",
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
    st.markdown("#### 🌧️ Weather Impact on Delivery Lead Times")
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


# -----------------------------------------------------------------------------
# 8. Deep-Dive Transactional Data Grid & Record Inspection
# -----------------------------------------------------------------------------
st.markdown("""
    <div class="section-header">
        <span>🔎 Deep-Dive Transactional Shipment Ledger</span>
        <span class="section-badge">Grain: Individual Requisition</span>
    </div>
""", unsafe_allow_html=True)

table_control_col1, table_control_col2, table_control_col3 = st.columns([2, 1, 1])

with table_control_col1:
    search_query = st.text_input("🔍 Search Clinic, Request ID, or Product (Literal Text)", placeholder="e.g., Donkorkrom, Antivenom, REQ-2025-000452")

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
    label="📥 Export Filtered Shipment Records (CSV)",
    data=csv_data,
    file_name=f"ghana_healthcare_logistics_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv",
)

# -----------------------------------------------------------------------------
# 9. Architectural & Methodological Documentation
# -----------------------------------------------------------------------------
with st.expander("📐 Technical Architecture, Star Schema & Methodological Notes"):
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
      $$\\text{OTIF-Q} \\iff \\text{Standard OTIF} \\land (\\neg \\text{ColdChainBreach})$$

    #### 3. Regional Bottleneck Composite Index
    Normalized against a stable operational reference of 12.0 hours (benchmark max acceptable lead time):
    $$\\text{Bottleneck Index} = 0.35 \\times \\text{StockOut\\%} + 0.35 \\times \\text{Delay\\%} + 20 \\times \\min\\left(1.0, \\frac{\\bar{T}_{\\text{lead}}}{12.0}\\right) + 0.10 \\times \\text{ColdBreach\\%}$$

    #### 4. Operational Risk Threshold Rationale
    - **Optimal Tier (Standard OTIF $\\ge 80\\%$)**: Aligns with WHO and humanitarian logistics targets where at least 4 out of 5 critical requisitions arrive strictly on-time and in-full.
    - **Moderate Risk (Standard OTIF $65\\% \\le \\text{Rate} < 80\\%$)**: Represents an unstable operational corridor with elevated lead-time volatility requiring higher safety stock buffers.
    - **High Risk (Standard OTIF $< 65\\%$ or Stockout Rate $> 8\\%$)**: Signifies severe delivery bottlenecks and stockouts that risk life-threatening gaps in anti-snake venom, emergency blood transfusion, and neonatal resuscitation.

    #### 5. Fleet Model Scope Notice
    *Fleet capacity constraints (discrete vehicle counts), maximum payload weight limits, and service-radius eligibility criteria are recorded in dimension schemas but are not yet enforced in dispatch allocation logic.*
    """)
