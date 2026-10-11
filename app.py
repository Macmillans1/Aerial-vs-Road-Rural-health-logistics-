"""Rural Healthcare Supply Chain & Logistics Analytics Dashboard.

Ghana Medical Drone & Ground Fleet Logistics Network (Zipline & GHS Model).
A Master's in Data Science / Data Analytics Flagship Portfolio Project.
"""

from datetime import datetime
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.metrics_engine import SupplyChainMetricsEngine, ExecutiveKPIs
from src.map_visualizer import build_pydeck_logistics_map, build_plotly_geographic_scatter

# -----------------------------------------------------------------------------
# 1. Page Configuration & Custom CSS Injection
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Ghana Rural Healthcare Logistics Dashboard",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Premium Dark Glassmorphism CSS styling
st.markdown("""
<style>
    /* Google Fonts Import */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Background and main container adjustments */
    .stApp {
        background: radial-gradient(circle at 15% 15%, #101826 0%, #0B0F19 100%);
    }

    /* Metric Card Styling */
    .metric-card {
        background: rgba(22, 31, 48, 0.75);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 20px 22px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, border-color 0.2s ease;
        position: relative;
        overflow: hidden;
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

    .metric-title {
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #9CA3AF;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 2.1rem;
        font-weight: 800;
        color: #FFFFFF;
        line-height: 1.1;
    }
    .metric-sub {
        font-size: 0.78rem;
        color: #6EE7B7;
        margin-top: 6px;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .metric-sub.negative {
        color: #FCA5A5;
    }
    .metric-sub.neutral {
        color: #D1D5DB;
    }

    /* Section Headers */
    .section-header {
        font-size: 1.25rem;
        font-weight: 700;
        color: #F3F4F6;
        margin: 28px 0 14px 0;
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

    /* Sidebar adjustments */
    [data-testid="stSidebar"] {
        background-color: #0e1422;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* Badges */
    .badge-drone {
        background-color: rgba(0, 210, 186, 0.18);
        color: #00D2BA;
        padding: 2px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-road {
        background-color: rgba(245, 158, 11, 0.18);
        color: #F59E0B;
        padding: 2px 8px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.8rem;
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

    # Date Range Slider
    min_date = engine.df_master["requested_timestamp"].min().date()
    max_date = engine.df_master["requested_timestamp"].max().date()
    date_selection = st.date_input(
        "Evaluation Timeframe",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        help="Select the transactional window (1 full year available)."
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
    map_engine_choice = st.radio("Map Rendering Engine", ["PyDeck 3D (Flight Arcs)", "Plotly 2D Scatter"], index=0)
    map_color_choice = st.selectbox("Color Clinics By", ["risk_tier", "remote_tier"], format_func=lambda x: "Delivery Delay Risk Tier" if x == "risk_tier" else "Remote Accessibility Tier")
    show_flight_corridors = st.checkbox("Show Aerial Corridors (Hub to Clinic)", value=True)

    st.markdown("---")
    st.markdown("""
        <div style="font-size: 0.72rem; color: #6B7280; line-height: 1.4;">
            <b>Portfolio Project Context:</b><br>
            Designed for Master's in Data Science / Analytics admissions in Germany (TUM / LMU / RWTH).<br>
            <i>Architecture: Star Schema | Python 3.10+ | Streamlit | Plotly | PyDeck</i>
        </div>
    """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 4. Filter Execution & Data Subsetting
# -----------------------------------------------------------------------------
if isinstance(date_selection, tuple) and len(date_selection) == 2:
    start_filter_date, end_filter_date = date_selection
else:
    start_filter_date, end_filter_date = min_date, max_date

df_filtered = engine.filter_data(
    regions=selected_regions,
    date_range=(start_filter_date, end_filter_date),
    product_categories=selected_categories,
    transport_modes=selected_modes,
    remote_tiers=selected_tiers,
)

kpis = engine.compute_executive_kpis(df_filtered)
df_clinic_metrics = engine.get_clinic_performance_summary(df_filtered)


# -----------------------------------------------------------------------------
# 5. Header & Executive KPI Scorecard
# -----------------------------------------------------------------------------
st.markdown("""
    <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 20px;">
        <div>
            <h1 style="margin: 0; font-size: 2.1rem; font-weight: 800; color: #FFFFFF; letter-spacing: -0.02em;">
                Rural Healthcare Supply Chain & Drone Logistics Analytics
            </h1>
            <p style="margin: 4px 0 0 0; color: #9CA3AF; font-size: 0.95rem;">
                Operational Telemetry & Performance Dashboard • Autonomous Drone Fleet vs. Rural Ground Fleet • Republic of Ghana
            </p>
        </div>
        <div style="text-align: right; background: rgba(0, 210, 186, 0.08); padding: 8px 14px; border-radius: 8px; border: 1px solid rgba(0, 210, 186, 0.25);">
            <div style="font-size: 0.72rem; color: #9CA3AF; font-weight: 600; text-transform: uppercase;">Active Subnetwork</div>
            <div style="font-size: 0.95rem; font-weight: 700; color: #00D2BA;">5 Hubs • 32 Clinics • 14 Formulations</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Executive KPI Cards (Row of 5 metrics)
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Dispatched Requests</div>
            <div class="metric-value">{kpis.total_requests:,}</div>
            <div class="metric-sub neutral">📦 Delivered: <b>{kpis.total_units_delivered:,} units</b></div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    otif_color = "positive" if kpis.otif_rate_pct >= 75.0 else ("neutral" if kpis.otif_rate_pct >= 65.0 else "negative")
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">OTIF (On-Time In-Full) Rate</div>
            <div class="metric-value" style="color: {'#10B981' if kpis.otif_rate_pct >= 75 else '#F59E0B'};">{kpis.otif_rate_pct:.1f}%</div>
            <div class="metric-sub {otif_color}">🎯 Strict SLA + Quality Pass</div>
        </div>
    """, unsafe_allow_html=True)

with col3:
    time_delta = kpis.road_avg_lead_time_hours - kpis.drone_avg_lead_time_hours if kpis.drone_avg_lead_time_hours > 0 else 0
    st.markdown(f"""
        <div class="metric-card gold">
            <div class="metric-title">Avg Order Cycle Time</div>
            <div class="metric-value">{kpis.avg_lead_time_hours:.1f} <span style="font-size: 1.1rem; font-weight: 500; color: #9CA3AF;">hrs</span></div>
            <div class="metric-sub">⚡ Drones save <b>{time_delta:.1f} hrs/trip</b> vs Road</div>
        </div>
    """, unsafe_allow_html=True)

with col4:
    stockout_class = "negative" if kpis.stock_out_rate_pct > 5.0 else "positive"
    st.markdown(f"""
        <div class="metric-card alert">
            <div class="metric-title">Stock-Out Frequency</div>
            <div class="metric-value" style="color: {'#EF4444' if kpis.stock_out_rate_pct > 5.0 else '#10B981'};">{kpis.stock_out_rate_pct:.1f}%</div>
            <div class="metric-sub {stockout_class}">⚠️ Unmet demand: <b>{kpis.stock_outs:,} requests</b></div>
        </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Cold-Chain Integrity Rate</div>
            <div class="metric-value" style="color: {'#10B981' if kpis.cold_chain_integrity_pct >= 95 else '#F59E0B'};">{kpis.cold_chain_integrity_pct:.1f}%</div>
            <div class="metric-sub">❄️ Vaccines, Blood & Insulin</div>
        </div>
    """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 6. Geospatial Mapping Section
# -----------------------------------------------------------------------------
st.markdown("""
    <div class="section-header">
        <span>📍 Geospatial Distribution Network & Drone Flight Corridors</span>
        <span class="section-badge">PyDeck 3D / Plotly Engine</span>
    </div>
""", unsafe_allow_html=True)

map_col1, map_col2 = st.columns([3, 1])

with map_col1:
    if map_engine_choice == "PyDeck 3D (Flight Arcs)":
        deck = build_pydeck_logistics_map(
            df_clinic_metrics=df_clinic_metrics,
            df_hubs=engine.df_hubs,
            color_by=map_color_choice,
            show_flight_arcs=show_flight_corridors,
        )
        st.pydeck_chart(deck, use_container_width=True)
    else:
        fig_geo = build_plotly_geographic_scatter(
            df_clinic_metrics=df_clinic_metrics,
            df_hubs=engine.df_hubs,
            color_by=map_color_choice,
        )
        st.plotly_chart(fig_geo, use_container_width=True)

with map_col2:
    st.markdown("""
        <div style="background: rgba(22, 31, 48, 0.7); border-radius: 12px; padding: 16px; border: 1px solid rgba(255, 255, 255, 0.08); font-size: 0.85rem;">
            <div style="font-weight: 700; color: #00D2BA; margin-bottom: 10px; font-size: 0.95rem;">Network Topology Legend</div>
            <div style="margin-bottom: 8px;">
                <span style="display: inline-block; width: 12px; height: 12px; background: #00D2BA; border-radius: 3px; margin-right: 6px;"></span>
                <b>Central Hub / Drone Nest</b> (Omenako, Mpanya, Kukua, Sefwi, Ankaful)
            </div>
            <div style="margin-bottom: 8px;">
                <span style="display: inline-block; width: 10px; height: 10px; background: #10B981; border-radius: 50%; margin-right: 6px;"></span>
                <b>Optimal Clinic</b> (OTIF &gt; 85%)
            </div>
            <div style="margin-bottom: 8px;">
                <span style="display: inline-block; width: 10px; height: 10px; background: #F59E0B; border-radius: 50%; margin-right: 6px;"></span>
                <b>Moderate Risk Clinic</b> (OTIF 70-85%)
            </div>
            <div style="margin-bottom: 8px;">
                <span style="display: inline-block; width: 10px; height: 10px; background: #EF4444; border-radius: 50%; margin-right: 6px;"></span>
                <b>High Delay Risk</b> (OTIF &lt; 70% or High Stockouts)
            </div>
            <hr style="border-color: rgba(255,255,255,0.08); margin: 12px 0;">
            <div style="font-size: 0.78rem; color: #9CA3AF; line-height: 1.4;">
                <b>Terrain Insights:</b><br>
                High Risk nodes predominantly cluster in <b>Tier 3</b> zones: Afram Plains islands (Eastern), Rainforest belts (Western), and isolated border enclaves (Northern).
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Mini high-risk clinics table
    high_risk_clinics = df_clinic_metrics[df_clinic_metrics["risk_tier"] == "High Risk"].sort_values("otif_rate_pct").head(4)
    if len(high_risk_clinics) > 0:
        st.markdown("<div style='font-size: 0.82rem; font-weight: 700; color: #EF4444; margin: 12px 0 6px 0;'>Critical Bottleneck Clinics:</div>", unsafe_allow_html=True)
        for _, cln in high_risk_clinics.iterrows():
            st.markdown(f"""
                <div style="background: rgba(239, 68, 68, 0.1); border-left: 3px solid #EF4444; padding: 6px 10px; margin-bottom: 6px; border-radius: 0 6px 6px 0; font-size: 0.76rem;">
                    <b>{cln['clinic_name']}</b> ({cln['region']})<br>
                    OTIF: <b>{cln['otif_rate_pct']}%</b> | Avg LT: <b>{cln['avg_lead_time_hours']} hrs</b>
                </div>
            """, unsafe_allow_html=True)


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
                title="Average Lead Time by Distance Band (Hours)",
                labels={"avg_lead_time_hours": "Average Lead Time (Hours)", "distance_band": "Distance Bracket", "transport_mode": "Transport Fleet"},
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
            st.info("No shipment records match current filter criteria.")

    with modal_col2:
        # Lead time box plot / distribution comparison
        delivered_subset = df_filtered[df_filtered["order_status"].isin(["Fulfilled", "Delayed"])].copy()
        if len(delivered_subset) > 0:
            fig_box = px.box(
                delivered_subset,
                x="remote_tier",
                y="lead_time_hours",
                color="transport_mode",
                title="Lead Time Variance Across Remote Accessibility Tiers",
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

    # Weather impact row
    st.markdown("#### 🌧️ Weather Shock Resilience: Transit Delays Under Severe Weather")
    weather_summary = delivered_subset.groupby(["weather_condition", "transport_mode"]).agg(
        avg_lead_time=("lead_time_hours", "mean"),
        otif_pct=("is_otif", lambda s: (s.sum() / len(s)) * 100.0),
        delay_count=("order_status", lambda s: (s == "Delayed").sum()),
        total=("request_id", "count"),
    ).reset_index()

    fig_weather = px.bar(
        weather_summary,
        x="weather_condition",
        y="avg_lead_time",
        color="transport_mode",
        barmode="group",
        title="Impact of Weather Severity on Fulfillment Lead Times (Clear vs. Rainy/Flood)",
        labels={"avg_lead_time": "Average Lead Time (Hours)", "weather_condition": "Weather State", "transport_mode": "Transport Modality"},
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

        # OTIF Rate line
        fig_trend.add_trace(go.Scatter(
            x=df_trend["week_start"],
            y=df_trend["otif_rate_pct"],
            name="OTIF Rate (%)",
            line=dict(color="#00D2BA", width=3),
            mode="lines+markers",
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
            title="Weekly OTIF, Delay, and Stock-Out Rates (Seasonal Monsoon Dip in May-July)",
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
            title="Weekly Shipment Request Volume Over 1-Year Operational Horizon",
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

    with diag_col2:
        fig_bot = px.bar(
            reg_bottlenecks,
            x="region",
            y="bottleneck_score",
            title="Regional Bottleneck Composite Index (Scale 0-100)",
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


# -----------------------------------------------------------------------------
# 8. Deep-Dive Transactional Data Grid & Record Inspection
# -----------------------------------------------------------------------------
st.markdown("""
    <div class="section-header">
        <span>🔎 Deep-Dive Transactional Shipment Ledger</span>
        <span class="section-badge">Star Schema Grain: Individual Request</span>
    </div>
""", unsafe_allow_html=True)

table_control_col1, table_control_col2, table_control_col3 = st.columns([2, 1, 1])

with table_control_col1:
    search_query = st.text_input("🔍 Search Clinic Name, Request ID, or Product", placeholder="e.g., Donkorkrom, Antivenom, REQ-2025-000452")

with table_control_col2:
    status_filter = st.selectbox("Order Status Filter", ["All Statuses", "Fulfilled", "Delayed", "Stock-Out"])

with table_control_col3:
    limit_rows = st.selectbox("Display Row Limit", [50, 100, 250, 1000], index=1)

# Apply ledger filters
df_ledger = df_filtered.copy()

if status_filter != "All Statuses":
    df_ledger = df_ledger[df_ledger["order_status"] == status_filter]

if search_query:
    query = search_query.strip().lower()
    df_ledger = df_ledger[
        df_ledger["request_id"].str.lower().str.contains(query)
        | df_ledger["clinic_name"].str.lower().str.contains(query)
        | df_ledger["product_name"].str.lower().str.contains(query)
        | df_ledger["region"].str.lower().str.contains(query)
    ]

# Display relevant star schema projection columns
display_columns = [
    "request_id",
    "requested_timestamp",
    "clinic_name",
    "region",
    "remote_tier",
    "product_name",
    "category",
    "transport_mode",
    "distance_km",
    "lead_time_hours",
    "order_status",
    "is_otif",
    "cold_chain_breach",
    "weather_condition",
]

st.dataframe(
    df_ledger[display_columns].head(limit_rows),
    use_container_width=True,
    height=340,
    column_config={
        "request_id": st.column_config.TextColumn("Request ID", width="medium"),
        "requested_timestamp": st.column_config.DatetimeColumn("Requested At", format="YYYY-MM-DD HH:mm"),
        "clinic_name": st.column_config.TextColumn("Destination Health Post"),
        "region": st.column_config.TextColumn("Region", width="small"),
        "remote_tier": st.column_config.TextColumn("Tier", width="small"),
        "product_name": st.column_config.TextColumn("Medical Cargo"),
        "category": st.column_config.TextColumn("Category"),
        "transport_mode": st.column_config.TextColumn("Modality", width="small"),
        "distance_km": st.column_config.NumberColumn("Distance (km)", format="%.1f km"),
        "lead_time_hours": st.column_config.NumberColumn("Lead Time", format="%.2f hrs"),
        "order_status": st.column_config.TextColumn("Status", width="small"),
        "is_otif": st.column_config.CheckboxColumn("OTIF"),
        "cold_chain_breach": st.column_config.CheckboxColumn("Cold Breach"),
        "weather_condition": st.column_config.TextColumn("Weather"),
    }
)

csv_data = df_ledger[display_columns].to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Export Filtered Shipment Records (CSV)",
    data=csv_data,
    file_name=f"ghana_healthcare_logistics_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv",
)

# -----------------------------------------------------------------------------
# 9. Architectural & Methodological Footer
# -----------------------------------------------------------------------------
with st.expander("📐 Technical Architecture, Star Schema & Methodological Notes (Master's Portfolio Support)"):
    st.markdown("""
    ### Data Engineering & Mathematical Methodology

    #### 1. Star Schema Relational Mapping
    - **Fact Table (`fact_shipments`)**: Granularity is one individual logistics request. Keys link to `dim_clinics`, `dim_products`, and `dim_hubs`.
    - **Physical Distance Calculation**: Great-circle geodesic distance derived via the **Haversine formula**:
      $$d = 2r \\arcsin \\left( \\sqrt{\\sin^2\\left(\\frac{\\Delta \\phi}{2}\\right) + \\cos(\\phi_1)\\cos(\\phi_2)\\sin^2\\left(\\frac{\\Delta \\lambda}{2}\\right)} \\right)$$
      Road transit paths apply a curvature winding penalty $\\omega \\in [1.35, 1.85]$ reflecting rural terrain degradation.

    #### 2. Rigorous Supply Chain OTIF (On-Time In-Full) Metric
    An order is strictly defined as **OTIF** if and only if all three validation constraints are satisfied:
    1. **On-Time**: $\\text{Lead Time} \\le \\text{SLA Target Hours}$
    2. **In-Full**: $\\text{Units Delivered} = \\text{Units Requested} \\land \\text{Status} \\ne \\text{'Stock-Out'}$
    3. **Quality / Cold-Chain Integrity**: $\\text{Cold Chain Breach} = \\text{False}$

    #### 3. Regional Bottleneck Vulnerability Score
    $$\\text{Bottleneck Index} = 0.35 \\times \\text{StockOut\\%} + 0.35 \\times \\text{Delay\\%} + 20 \\times \\left(\\frac{\\bar{T}_{\\text{lead}}}{\\max(T_{\\text{lead}})}\\right) + 0.10 \\times \\text{ColdBreach\\%}$$
    """)
