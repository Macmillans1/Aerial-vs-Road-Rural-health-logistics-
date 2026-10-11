"""Reproducible Simulation Results Table Generator.

Calls SupplyChainMetricsEngine to calculate exact operational metrics, modal comparisons,
and percentage point differences for documentation and reporting.
"""

import sys
import os
from typing import Optional
import pandas as pd

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.metrics_engine import SupplyChainMetricsEngine


def generate_simulation_markdown_table(
    data_dir: str = "data",
    df: Optional[pd.DataFrame] = None
) -> str:
    """Generate Markdown comparison table from underlying simulation dataset.

    Safely handles empty denominators and unverified cold-chain telemetry by:
    - Restricting verified cold-chain breach rates strictly to delivered cold items with known quality.
    - Reporting unverified / unknown cold quality counts in a separate dedicated row.
    - Displaying 'N/A' (not 0.00%) when no verified records remain in a group or when denominators are empty.
    """
    if df is None:
        engine = SupplyChainMetricsEngine(data_dir=data_dir).load_data()
        df = engine.df_master

    drone = df[df["transport_mode"] == "Drone"]
    road = df[df["transport_mode"] == "Road"]

    total_n = len(df)
    drone_n = len(drone)
    road_n = len(road)

    # 1. Delivered orders
    total_deliv = int(df["is_delivered"].sum()) if total_n > 0 else 0
    drone_deliv = int(drone["is_delivered"].sum()) if drone_n > 0 else 0
    road_deliv = int(road["is_delivered"].sum()) if road_n > 0 else 0

    total_deliv_rate = (total_deliv / total_n * 100.0) if total_n > 0 else None
    drone_deliv_rate = (drone_deliv / drone_n * 100.0) if drone_n > 0 else None
    road_deliv_rate = (road_deliv / road_n * 100.0) if road_n > 0 else None
    deliv_rate_diff_pp = (
        (drone_deliv_rate - road_deliv_rate)
        if (drone_deliv_rate is not None and road_deliv_rate is not None)
        else None
    )

    # 2. Stock-outs
    total_so = int((df["order_status"] == "Stock-Out").sum()) if total_n > 0 else 0
    drone_so = int((drone["order_status"] == "Stock-Out").sum()) if drone_n > 0 else 0
    road_so = int((road["order_status"] == "Stock-Out").sum()) if road_n > 0 else 0

    total_so_rate = (total_so / total_n * 100.0) if total_n > 0 else None
    drone_so_rate = (drone_so / drone_n * 100.0) if drone_n > 0 else None
    road_so_rate = (road_so / road_n * 100.0) if road_n > 0 else None
    so_rate_diff_pp = (
        (drone_so_rate - road_so_rate)
        if (drone_so_rate is not None and road_so_rate is not None)
        else None
    )

    # 3. Standard OTIF
    total_std_otif = int(df["is_standard_otif"].sum()) if total_n > 0 else 0
    drone_std_otif = int(drone["is_standard_otif"].sum()) if drone_n > 0 else 0
    road_std_otif = int(road["is_standard_otif"].sum()) if road_n > 0 else 0

    total_std_otif_rate = (total_std_otif / total_n * 100.0) if total_n > 0 else None
    drone_std_otif_rate = (drone_std_otif / drone_n * 100.0) if drone_n > 0 else None
    road_std_otif_rate = (road_std_otif / road_n * 100.0) if road_n > 0 else None
    std_otif_diff_pp = (
        (drone_std_otif_rate - road_std_otif_rate)
        if (drone_std_otif_rate is not None and road_std_otif_rate is not None)
        else None
    )

    # 4. Quality-Adjusted OTIF (OTIF-Q)
    total_q_otif = int(df["is_quality_otif"].sum()) if total_n > 0 else 0
    drone_q_otif = int(drone["is_quality_otif"].sum()) if drone_n > 0 else 0
    road_q_otif = int(road["is_quality_otif"].sum()) if road_n > 0 else 0

    total_q_otif_rate = (total_q_otif / total_n * 100.0) if total_n > 0 else None
    drone_q_otif_rate = (drone_q_otif / drone_n * 100.0) if drone_n > 0 else None
    road_q_otif_rate = (road_q_otif / road_n * 100.0) if road_n > 0 else None
    q_otif_diff_pp = (
        (drone_q_otif_rate - road_q_otif_rate)
        if (drone_q_otif_rate is not None and road_q_otif_rate is not None)
        else None
    )

    # 5. Lead Times (delivered only)
    deliv_all = df[df["is_delivered"]]
    deliv_drone = drone[drone["is_delivered"]]
    deliv_road = road[road["is_delivered"]]

    total_lead = deliv_all["lead_time_hours"].mean() if len(deliv_all) > 0 and deliv_all["lead_time_hours"].notna().any() else None
    drone_lead = deliv_drone["lead_time_hours"].mean() if len(deliv_drone) > 0 and deliv_drone["lead_time_hours"].notna().any() else None
    road_lead = deliv_road["lead_time_hours"].mean() if len(deliv_road) > 0 and deliv_road["lead_time_hours"].notna().any() else None

    lead_diff_hours = (drone_lead - road_lead) if (drone_lead is not None and road_lead is not None) else None
    lead_reduction_pct = (
        ((road_lead - drone_lead) / road_lead * 100.0)
        if (drone_lead is not None and road_lead is not None and road_lead > 0)
        else None
    )

    # 6. Tier 3 Lead Times
    t3_delivered = df[df["is_delivered"] & (df["remote_tier"] == "Tier 3")]
    t3_drone = t3_delivered[t3_delivered["transport_mode"] == "Drone"]
    t3_road = t3_delivered[t3_delivered["transport_mode"] == "Road"]

    t3_total_lead = t3_delivered["lead_time_hours"].mean() if len(t3_delivered) > 0 and t3_delivered["lead_time_hours"].notna().any() else None
    t3_drone_lead = t3_drone["lead_time_hours"].mean() if len(t3_drone) > 0 and t3_drone["lead_time_hours"].notna().any() else None
    t3_road_lead = t3_road["lead_time_hours"].mean() if len(t3_road) > 0 and t3_road["lead_time_hours"].notna().any() else None

    t3_lead_diff_hours = (t3_drone_lead - t3_road_lead) if (t3_drone_lead is not None and t3_road_lead is not None) else None
    t3_reduction_pct = (
        ((t3_road_lead - t3_drone_lead) / t3_road_lead * 100.0)
        if (t3_drone_lead is not None and t3_road_lead is not None and t3_road_lead > 0)
        else None
    )

    # 7. Cold-Chain Breach Rates (Delivered Cold Cargo with Verified Quality)
    cold_delivered = df[df["is_delivered"] & (df["storage_requirement"] == "Cold Chain")]
    cold_drone = cold_delivered[cold_delivered["transport_mode"] == "Drone"]
    cold_road = cold_delivered[cold_delivered["transport_mode"] == "Road"]

    # Unknown quality counts reported separately
    total_cold_unknown = int(cold_delivered["cold_chain_breach"].isna().sum()) if len(cold_delivered) > 0 else 0
    drone_cold_unknown = int(cold_drone["cold_chain_breach"].isna().sum()) if len(cold_drone) > 0 else 0
    road_cold_unknown = int(cold_road["cold_chain_breach"].isna().sum()) if len(cold_road) > 0 else 0

    # Verified records only
    known_total_cold = cold_delivered[cold_delivered["cold_chain_breach"].notna()]
    known_drone_cold = cold_drone[cold_drone["cold_chain_breach"].notna()]
    known_road_cold = cold_road[cold_road["cold_chain_breach"].notna()]

    known_total_n = len(known_total_cold)
    known_drone_n = len(known_drone_cold)
    known_road_n = len(known_road_cold)

    total_cold_breaches = int((known_total_cold["cold_chain_breach"] == True).sum()) if known_total_n > 0 else 0
    drone_cold_breaches = int((known_drone_cold["cold_chain_breach"] == True).sum()) if known_drone_n > 0 else 0
    road_cold_breaches = int((known_road_cold["cold_chain_breach"] == True).sum()) if known_road_n > 0 else 0

    if known_total_n > 0:
        total_breach_rate = total_cold_breaches / known_total_n * 100.0
        total_breach_str = f"{total_breach_rate:.2f}% ({total_cold_breaches:,} / {known_total_n:,})"
    else:
        total_breach_rate = None
        total_breach_str = "N/A"

    if known_drone_n > 0:
        drone_breach_rate = drone_cold_breaches / known_drone_n * 100.0
        drone_breach_str = f"{drone_breach_rate:.2f}% ({drone_cold_breaches:,} / {known_drone_n:,})"
    else:
        drone_breach_rate = None
        drone_breach_str = "N/A"

    if known_road_n > 0:
        road_breach_rate = road_cold_breaches / known_road_n * 100.0
        road_breach_str = f"{road_breach_rate:.2f}% ({road_cold_breaches:,} / {known_road_n:,})"
    else:
        road_breach_rate = None
        road_breach_str = "N/A"

    if drone_breach_rate is not None and road_breach_rate is not None:
        breach_diff_str = f"{drone_breach_rate - road_breach_rate:+.2f} percentage points"
    else:
        breach_diff_str = "N/A"

    # Helper formatting closures
    def fmt_pct_row(rate: Optional[float], count: int, denom: int) -> str:
        if rate is not None and denom > 0:
            return f"{rate:.2f}% ({count:,} / {denom:,})"
        return "N/A"

    def fmt_diff_pp(diff: Optional[float]) -> str:
        return f"{diff:+.2f} percentage points" if diff is not None else "N/A"

    def fmt_hours_cell(val: Optional[float]) -> str:
        return f"{val:.2f} hours" if val is not None else "N/A"

    def fmt_lead_diff(diff: Optional[float], rel: Optional[float]) -> str:
        if diff is not None and rel is not None:
            return f"{diff:+.2f} hours ({rel:.1f}% relative difference)"
        elif diff is not None:
            return f"{diff:+.2f} hours"
        return "N/A"

    drone_n_str = f"{drone_n:,} ({(drone_n/total_n*100):.1f}%)" if total_n > 0 else "0"
    road_n_str = f"{road_n:,} ({(road_n/total_n*100):.1f}%)" if total_n > 0 else "0"
    total_deliv_str = f"{total_deliv:,} ({total_deliv_rate:.2f}%)" if total_deliv_rate is not None else "N/A"
    drone_deliv_str = f"{drone_deliv:,} ({drone_deliv_rate:.2f}%)" if drone_deliv_rate is not None else "N/A"
    road_deliv_str = f"{road_deliv:,} ({road_deliv_rate:.2f}%)" if road_deliv_rate is not None else "N/A"

    total_so_str = f"{total_so:,} ({total_so_rate:.2f}%)" if total_so_rate is not None else "N/A"
    drone_so_str = f"{drone_so:,} ({drone_so_rate:.2f}%)" if drone_so_rate is not None else "N/A"
    road_so_str = f"{road_so:,} ({road_so_rate:.2f}%)" if road_so_rate is not None else "N/A"

    table_md = f"""| Metric | Total / Baseline | Autonomous Drone Fleet | Rural Ground Fleet | Modal Comparison (Drone vs. Road) |
| :--- | :---: | :---: | :---: | :---: |
| **Total Requisitions ($N$)** | **{total_n:,}** | {drone_n_str} | {road_n_str} | Denominator basis |
| **Successfully Delivered** | **{total_deliv_str}** | {drone_deliv_str} | {road_deliv_str} | {fmt_diff_pp(deliv_rate_diff_pp)} |
| **Stock-Out Rate** | **{total_so_str}** | {drone_so_str} | {road_so_str} | {fmt_diff_pp(so_rate_diff_pp)} |
| **Standard OTIF Rate** | **{fmt_pct_row(total_std_otif_rate, total_std_otif, total_n)}** | {fmt_pct_row(drone_std_otif_rate, drone_std_otif, drone_n)} | {fmt_pct_row(road_std_otif_rate, road_std_otif, road_n)} | **{fmt_diff_pp(std_otif_diff_pp)}** |
| **Quality OTIF (OTIF-Q)** | **{fmt_pct_row(total_q_otif_rate, total_q_otif, total_n)}** | {fmt_pct_row(drone_q_otif_rate, drone_q_otif, drone_n)} | {fmt_pct_row(road_q_otif_rate, road_q_otif, road_n)} | **{fmt_diff_pp(q_otif_diff_pp)}** |
| **Average Simulated Lead Time** | **{fmt_hours_cell(total_lead)}** | **{fmt_hours_cell(drone_lead)}** | **{fmt_hours_cell(road_lead)}** | **{fmt_lead_diff(lead_diff_hours, lead_reduction_pct)}** |
| **Tier 3 (Deep Rural) Lead Time** | **{fmt_hours_cell(t3_total_lead)}** | **{fmt_hours_cell(t3_drone_lead)}** | **{fmt_hours_cell(t3_road_lead)}** | **{fmt_lead_diff(t3_lead_diff_hours, t3_reduction_pct)}** |
| **Cold-Chain Breach Rate** | **{total_breach_str}** | **{drone_breach_str}** | **{road_breach_str}** | **{breach_diff_str}** |
| **Unknown Quality Cold Cargo** | **{total_cold_unknown:,}** | {drone_cold_unknown:,} | {road_cold_unknown:,} | Missing/unverified telemetry |"""

    return table_md


if __name__ == "__main__":
    print(generate_simulation_markdown_table())
