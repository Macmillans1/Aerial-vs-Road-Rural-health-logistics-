import re

def remove_emojis_from_app():
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Page icon in set_page_config
    content = content.replace('    page_icon="🚁",\n', '')

    # 2. Validation error
    content = content.replace('st.error(f"❌ Data Validation Error: {exc}")', 'st.error(f"Data Validation Error: {exc}")')

    # 3. Logo badge in sidebar
    old_badge = '<div style="background: linear-gradient(135deg, #00D2BA, #3B82F6); padding: 8px; border-radius: 10px; font-size: 20px;">🚁</div>'
    new_badge = '<div style="background: linear-gradient(135deg, #00D2BA, #3B82F6); width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 14px; color: #FFFFFF; letter-spacing: 0.5px;">AM</div>'
    content = content.replace(old_badge, new_badge)

    # 4. Sidebar section headers
    content = content.replace('st.markdown("### 🎛️ Multidimensional Filters")', 'st.markdown("### Multidimensional Filters")')
    content = content.replace('st.markdown("### 🗺️ Map Display Preferences")', 'st.markdown("### Map Display Preferences")')

    # 5. Synthetic banner icon
    content = content.replace('        <span>ℹ️</span>\n', '')

    # 6. Filter warning
    content = content.replace(
        'st.warning("⚠️ No shipment records match the selected filter criteria. Please broaden your selection in the sidebar.")',
        'st.warning("No shipment records match the selected filter criteria. Please broaden your selection in the sidebar.")'
    )

    # 7. KPI card subtext
    content = content.replace(
        '<div class="metric-sub neutral">📦 Delivered: <b>{kpis.delivered_orders:,}</b> &nbsp;•&nbsp; Stock-outs: <b>{kpis.stock_outs:,}</b></div>',
        '<div class="metric-sub neutral">Delivered: <b>{kpis.delivered_orders:,}</b> &nbsp;•&nbsp; Stock-outs: <b>{kpis.stock_outs:,}</b></div>'
    )
    content = content.replace(
        '<div class="metric-sub positive">✅ On-Time: <b>{kpis.on_time_orders:,}</b> &nbsp;•&nbsp; Late: <b>{kpis.delayed_orders:,}</b></div>',
        '<div class="metric-sub positive">On-Time: <b>{kpis.on_time_orders:,}</b> &nbsp;•&nbsp; Late: <b>{kpis.delayed_orders:,}</b></div>'
    )
    content = content.replace(
        'delta_sub = f"⚡ Diff in avg simulated lead time: <b>-{kpis.drone_road_delta_hours:.1f} hrs</b> (Drone vs Road)"',
        'delta_sub = f"Diff in avg simulated lead time: <b>-{kpis.drone_road_delta_hours:.1f} hrs</b> (Drone vs Road)"'
    )
    content = content.replace(
        'delta_sub = f"⚡ Drone-only active ({kpis.drone_avg_lead_time_hours:.1f} hrs)"',
        'delta_sub = f"Drone-only active ({kpis.drone_avg_lead_time_hours:.1f} hrs)"'
    )
    content = content.replace(
        'delta_sub = f"🚗 Road-only active ({kpis.road_avg_lead_time_hours:.1f} hrs)"',
        'delta_sub = f"Road-only active ({kpis.road_avg_lead_time_hours:.1f} hrs)"'
    )
    content = content.replace(
        'delta_sub = "⚡ No deliveries in view"',
        'delta_sub = "No deliveries in view"'
    )
    content = content.replace(
        '<div class="metric-sub">🎯 Strict SLA: On-Time & In-Full</div>',
        '<div class="metric-sub">Strict SLA: On-Time & In-Full</div>'
    )
    content = content.replace(
        '<div class="metric-sub">❄️ Standard OTIF + Thermal Compliance</div>',
        '<div class="metric-sub">Standard OTIF + Thermal Compliance</div>'
    )
    content = content.replace(
        '<div class="metric-sub">❄️ Denom: {kpis.total_delivered_cold_orders:,} Delivered Cold Items{unknown_note}</div>',
        '<div class="metric-sub">Denom: {kpis.total_delivered_cold_orders:,} Delivered Cold Items{unknown_note}</div>'
    )

    # 8. Map section header & unmapped warning
    content = content.replace(
        '<span>📍 Geospatial Distribution Network & Illustrative Supply Corridors</span>',
        '<span>Geospatial Distribution Network & Illustrative Supply Corridors</span>'
    )
    content = content.replace(
        'st.warning(f"⚠️ Unmapped Hub Relationships: {len(unmapped)} clinic(s) could not be matched to an active hub: {\', \'.join(unmapped[:3])}")',
        'st.warning(f"Unmapped Hub Relationships: {len(unmapped)} clinic(s) could not be matched to an active hub: {\', \'.join(unmapped[:3])}")'
    )

    # 9. Topology legend
    old_topo = '<div style="font-weight: 700; color: #00D2BA; margin-bottom: 12px; font-size: 0.95rem; display: flex; align-items: center; gap: 6px;">\n    <span>🗺️</span> <span>Network Topology Legend</span>\n</div>'
    new_topo = '<div style="font-weight: 700; color: #00D2BA; margin-bottom: 12px; font-size: 0.95rem;">\n    <span>Network Topology Legend</span>\n</div>'
    content = content.replace(old_topo, new_topo)

    # 10. Bottleneck clinics
    content = content.replace(
        "<div style='font-size: 0.82rem; font-weight: 700; color: #EF4444; margin: 12px 0 6px 0;'>⚠️ Critical Bottleneck Clinics:</div>",
        "<div style='font-size: 0.82rem; font-weight: 700; color: #EF4444; margin: 12px 0 6px 0;'>Critical Bottleneck Clinics:</div>"
    )

    # 11. Performance Breakdown header & tabs
    content = content.replace(
        '<span>📊 Operational Performance & Modal Efficiency Breakdown</span>',
        '<span>Operational Performance & Modal Efficiency Breakdown</span>'
    )
    content = content.replace(
        '"🚀 Transport Efficiency (Drone vs. Road)"',
        '"Transport Efficiency (Drone vs. Road)"'
    )
    content = content.replace(
        '"📈 Weekly OTIF & Fulfillment Trends"',
        '"Weekly OTIF & Fulfillment Trends"'
    )
    content = content.replace(
        '"⚠️ Regional Bottlenecks & Stock-Out Diagnostics"',
        '"Regional Bottlenecks & Stock-Out Diagnostics"'
    )
    content = content.replace(
        '"🔮 What-If Scenario Simulator"',
        '"What-If Scenario Simulator"'
    )
    content = content.replace(
        '"🏥 Clinic & Hub Explorer"',
        '"Clinic & Hub Explorer"'
    )

    # 12. Weather impact header
    content = content.replace(
        'st.markdown("#### 🌧️ Weather Impact on Delivery Lead Times")',
        'st.markdown("#### Weather Impact on Delivery Lead Times")'
    )

    # 13. Tab 4 What-if Simulator
    content = content.replace(
        '🔮 Multi-Modal What-If Operational Scenario Simulator',
        'Multi-Modal What-If Operational Scenario Simulator'
    )
    content = content.replace(
        "<div style='font-size: 0.88rem; font-weight: 600; color: #00D2BA; margin-bottom: 8px;'>⏱️ Dispatch Preparation Adjustments</div>",
        "<div style='font-size: 0.88rem; font-weight: 600; color: #00D2BA; margin-bottom: 8px;'>Dispatch Preparation Adjustments</div>"
    )
    content = content.replace(
        "<div style='font-size: 0.88rem; font-weight: 600; color: #F59E0B; margin-bottom: 8px;'>🌧️ Severe Weather Transit Delay</div>",
        "<div style='font-size: 0.88rem; font-weight: 600; color: #F59E0B; margin-bottom: 8px;'>Severe Weather Transit Delay</div>"
    )
    content = content.replace(
        'apply_submitted = st.form_submit_button("⚡ Apply Scenario", type="primary", use_container_width=True)',
        'apply_submitted = st.form_submit_button("Apply Scenario", type="primary", use_container_width=True)'
    )
    content = content.replace(
        'st.warning("⚠️ No shipment records match the active filter criteria. Broaden your filters to view scenario simulation.")',
        'st.warning("No shipment records match the active filter criteria. Broaden your filters to view scenario simulation.")'
    )
    content = content.replace(
        'st.info("ℹ️ The active selection contains stock-out requests only. No shipments were delivered, so lead times and on-time delivery rates are N/A.")',
        'st.info("The active selection contains stock-out requests only. No shipments were delivered, so lead times and on-time delivery rates are N/A.")'
    )
    content = content.replace(
        "<div style='font-size: 1.05rem; font-weight: 700; color: #FFFFFF; margin: 18px 0 10px 0;'>📊 Performance Comparison: Baseline vs. Scenario</div>",
        "<div style='font-size: 1.05rem; font-weight: 700; color: #FFFFFF; margin: 18px 0 10px 0;'>Performance Comparison: Baseline vs. Scenario</div>"
    )
    content = content.replace(
        "<div style='font-size: 1.05rem; font-weight: 700; color: #FFFFFF; margin: 18px 0 8px 0;'>⚠️ Requisitions with Changed On-Time Delivery Status</div>",
        "<div style='font-size: 1.05rem; font-weight: 700; color: #FFFFFF; margin: 18px 0 8px 0;'>Requisitions with Changed On-Time Delivery Status</div>"
    )
    content = content.replace(
        'st.info("ℹ️ No requisitions changed on-time delivery status under this scenario (timing adjustments did not cause or resolve any delivery SLA breaches).")',
        'st.info("No requisitions changed on-time delivery status under this scenario (timing adjustments did not cause or resolve any delivery SLA breaches).")'
    )
    content = content.replace(
        "<div style='font-size: 1.05rem; font-weight: 700; color: #FFFFFF; margin: 18px 0 8px 0;'>📥 Export Scenario Telemetry & Analytics</div>",
        "<div style='font-size: 1.05rem; font-weight: 700; color: #FFFFFF; margin: 18px 0 8px 0;'>Export Scenario Telemetry & Analytics</div>"
    )
    content = content.replace(
        'label="📥 Download Request-Level Scenario CSV",',
        'label="Download Request-Level Scenario CSV",'
    )
    content = content.replace(
        'label="📥 Download Scenario Summary JSON",',
        'label="Download Scenario Summary JSON",'
    )
    content = content.replace(
        'st.info("💡 Adjust the scenario parameters above and click **⚡ Apply Scenario** to calculate comparative operational metrics.")',
        'st.info("Adjust the scenario parameters above and click **Apply Scenario** to calculate comparative operational metrics.")'
    )

    # 14. Tab 5 Clinic & Hub Explorer
    content = content.replace(
        '🏥 Clinic & Hub Operational Explorer',
        'Clinic & Hub Operational Explorer'
    )
    content = content.replace(
        '🔍 <b>Active Context Filters Intersecting Location:</b>',
        '<b>Active Context Filters Intersecting Location:</b>'
    )
    content = content.replace(
        'st.warning(f"ℹ️ **No requests in this selection**',
        'st.warning(f"**No requests in this selection**'
    )
    content = content.replace(
        "<div style='font-size: 1.0rem; font-weight: 700; color: #FFFFFF; margin: 12px 0 8px 0;'>📊 Location Operational Scorecard</div>",
        "<div style='font-size: 1.0rem; font-weight: 700; color: #FFFFFF; margin: 12px 0 8px 0;'>Location Operational Scorecard</div>"
    )
    content = content.replace(
        "<div style='font-size: 1.0rem; font-weight: 700; color: #FFFFFF; margin: 20px 0 8px 0;'>📈 Focused Location Diagnostics</div>",
        "<div style='font-size: 1.0rem; font-weight: 700; color: #FFFFFF; margin: 20px 0 8px 0;'>Focused Location Diagnostics</div>"
    )
    content = content.replace(
        "<div style='font-size: 0.95rem; font-weight: 700; color: #FFFFFF; margin: 18px 0 6px 0;'>📋 Filtered Location Requisition Ledger</div>",
        "<div style='font-size: 0.95rem; font-weight: 700; color: #FFFFFF; margin: 18px 0 6px 0;'>Filtered Location Requisition Ledger</div>"
    )
    content = content.replace(
        'label=f"📥 Download Filtered {explorer_loc_type} Requisitions CSV ({len(df_loc):,} records)",',
        'label=f"Download Filtered {explorer_loc_type} Requisitions CSV ({len(df_loc):,} records)",'
    )
    content = content.replace(
        "<div style='font-size: 1.05rem; font-weight: 700; color: #FFFFFF; margin: 24px 0 4px 0;'>🔮 Location What-If Scenario Simulator</div>",
        "<div style='font-size: 1.05rem; font-weight: 700; color: #FFFFFF; margin: 24px 0 4px 0;'>Location What-If Scenario Simulator</div>"
    )
    content = content.replace(
        'st.warning("⚠️ Selected location or active sidebar filters have changed. Re-apply scenario to calculate results for the updated cohort.")',
        'st.warning("Selected location or active sidebar filters have changed. Re-apply scenario to calculate results for the updated cohort.")'
    )
    content = content.replace(
        "<div style='font-size: 0.88rem; font-weight: 600; color: #00D2BA; margin-bottom: 8px;'>⏱️ Dispatch Preparation Adjustments</div>",
        "<div style='font-size: 0.88rem; font-weight: 600; color: #00D2BA; margin-bottom: 8px;'>Dispatch Preparation Adjustments</div>"
    )
    content = content.replace(
        "<div style='font-size: 0.88rem; font-weight: 600; color: #F59E0B; margin-bottom: 8px;'>🌧️ Severe Weather Transit Delay</div>",
        "<div style='font-size: 0.88rem; font-weight: 600; color: #F59E0B; margin-bottom: 8px;'>Severe Weather Transit Delay</div>"
    )
    content = content.replace(
        'loc_apply_submitted = st.form_submit_button("⚡ Apply Location Scenario", type="primary", use_container_width=True)',
        'loc_apply_submitted = st.form_submit_button("Apply Location Scenario", type="primary", use_container_width=True)'
    )
    content = content.replace(
        'if st.button("🔄 Reset Location Scenario", use_container_width=True, key="reset_loc_scen_btn"):',
        'if st.button("Reset Location Scenario", use_container_width=True, key="reset_loc_scen_btn"):',
    )
    content = content.replace(
        "<div style='font-size: 0.95rem; font-weight: 700; color: #FFFFFF; margin: 16px 0 8px 0;'>📊 Simulation Outcomes: {selected_loc_name} ({selected_loc_id})</div>",
        "<div style='font-size: 0.95rem; font-weight: 700; color: #FFFFFF; margin: 16px 0 8px 0;'>Simulation Outcomes: {selected_loc_name} ({selected_loc_id})</div>"
    )
    content = content.replace(
        'st.caption(f"⚠️ {len(loc_changed):,} requisitions changed on-time delivery status for this location.")',
        'st.caption(f"{len(loc_changed):,} requisitions changed on-time delivery status for this location.")'
    )
    content = content.replace(
        'label=f"📥 Download {selected_loc_name} Scenario CSV ({len(loc_scen_df):,} records)",',
        'label=f"Download {selected_loc_name} Scenario CSV ({len(loc_scen_df):,} records)",'
    )
    content = content.replace(
        'st.info("💡 Adjust local scenario parameters above and click **⚡ Apply Location Scenario** to simulate operational impact on this location.")',
        'st.info("Adjust local scenario parameters above and click **Apply Location Scenario** to simulate operational impact on this location.")'
    )

    # 15. Ledger & Expander
    content = content.replace(
        '<span>🔎 Deep-Dive Transactional Shipment Ledger</span>',
        '<span>Deep-Dive Transactional Shipment Ledger</span>'
    )
    content = content.replace(
        'search_query = st.text_input("🔍 Search Clinic, Request ID, or Product (Literal Text)"',
        'search_query = st.text_input("Search Clinic, Request ID, or Product (Literal Text)"'
    )
    content = content.replace(
        'label="📥 Export Filtered Shipment Records (CSV)",',
        'label="Export Filtered Shipment Records (CSV)",'
    )
    content = content.replace(
        'with st.expander("📐 Technical Architecture, Star Schema & Methodological Notes"):',
        'with st.expander("Technical Architecture, Star Schema & Methodological Notes"):'
    )

    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    remove_emojis_from_app()
