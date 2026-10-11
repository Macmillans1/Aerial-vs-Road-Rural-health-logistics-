"""Reproducible Simulation Results Table Generator.

Calls SupplyChainMetricsEngine to calculate exact operational metrics, modal comparisons,
and percentage point differences for documentation and reporting.
"""

import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.metrics_engine import SupplyChainMetricsEngine


def generate_simulation_markdown_table(data_dir: str = "data") -> str:
    """Generate Markdown comparison table from underlying simulation dataset."""
    engine = SupplyChainMetricsEngine(data_dir=data_dir).load_data()
    df = engine.df_master

    drone = df[df["transport_mode"] == "Drone"]
    road = df[df["transport_mode"] == "Road"]

    total_n = len(df)
    drone_n = len(drone)
    road_n = len(road)

    # 1. Delivered orders
    total_deliv = int(df["is_delivered"].sum())
    drone_deliv = int(drone["is_delivered"].sum())
    road_deliv = int(road["is_delivered"].sum())

    total_deliv_rate = total_deliv / total_n * 100.0
    drone_deliv_rate = drone_deliv / drone_n * 100.0
    road_deliv_rate = road_deliv / road_n * 100.0
    deliv_rate_diff_pp = drone_deliv_rate - road_deliv_rate

    # 2. Stock-outs
    total_so = int((df["order_status"] == "Stock-Out").sum())
    drone_so = int((drone["order_status"] == "Stock-Out").sum())
    road_so = int((road["order_status"] == "Stock-Out").sum())

    total_so_rate = total_so / total_n * 100.0
    drone_so_rate = drone_so / drone_n * 100.0
    road_so_rate = road_so / road_n * 100.0
    so_rate_diff_pp = drone_so_rate - road_so_rate

    # 3. Standard OTIF
    total_std_otif = int(df["is_standard_otif"].sum())
    drone_std_otif = int(drone["is_standard_otif"].sum())
    road_std_otif = int(road["is_standard_otif"].sum())

    total_std_otif_rate = total_std_otif / total_n * 100.0
    drone_std_otif_rate = drone_std_otif / drone_n * 100.0
    road_std_otif_rate = road_std_otif / road_n * 100.0
    std_otif_diff_pp = drone_std_otif_rate - road_std_otif_rate

    # 4. Quality-Adjusted OTIF (OTIF-Q)
    total_q_otif = int(df["is_quality_otif"].sum())
    drone_q_otif = int(drone["is_quality_otif"].sum())
    road_q_otif = int(road["is_quality_otif"].sum())

    total_q_otif_rate = total_q_otif / total_n * 100.0
    drone_q_otif_rate = drone_q_otif / drone_n * 100.0
    road_q_otif_rate = road_q_otif / road_n * 100.0
    q_otif_diff_pp = drone_q_otif_rate - road_q_otif_rate

    # 5. Lead Times (delivered only)
    total_lead = df[df["is_delivered"]]["lead_time_hours"].mean()
    drone_lead = drone[drone["is_delivered"]]["lead_time_hours"].mean()
    road_lead = road[road["is_delivered"]]["lead_time_hours"].mean()
    lead_diff_hours = drone_lead - road_lead
    lead_reduction_pct = (road_lead - drone_lead) / road_lead * 100.0

    # 6. Tier 3 Lead Times
    t3_delivered = df[df["is_delivered"] & (df["remote_tier"] == "Tier 3")]
    t3_drone = t3_delivered[t3_delivered["transport_mode"] == "Drone"]
    t3_road = t3_delivered[t3_delivered["transport_mode"] == "Road"]

    t3_total_lead = t3_delivered["lead_time_hours"].mean()
    t3_drone_lead = t3_drone["lead_time_hours"].mean()
    t3_road_lead = t3_road["lead_time_hours"].mean()
    t3_lead_diff_hours = t3_drone_lead - t3_road_lead
    t3_reduction_pct = (t3_road_lead - t3_drone_lead) / t3_road_lead * 100.0

    # 7. Cold-Chain Breach Rates (Delivered Cold Cargo)
    cold_delivered = df[df["is_delivered"] & (df["storage_requirement"] == "Cold Chain")]
    cold_drone = cold_delivered[cold_delivered["transport_mode"] == "Drone"]
    cold_road = cold_delivered[cold_delivered["transport_mode"] == "Road"]

    total_cold_n = len(cold_delivered)
    drone_cold_n = len(cold_drone)
    road_cold_n = len(cold_road)

    total_cold_breaches = int((cold_delivered["cold_chain_breach"] == True).sum())
    drone_cold_breaches = int((cold_drone["cold_chain_breach"] == True).sum())
    road_cold_breaches = int((cold_road["cold_chain_breach"] == True).sum())

    total_breach_rate = total_cold_breaches / total_cold_n * 100.0
    drone_breach_rate = drone_cold_breaches / drone_cold_n * 100.0
    road_breach_rate = road_cold_breaches / road_cold_n * 100.0
    breach_diff_pp = drone_breach_rate - road_breach_rate

    table_md = f"""| Metric | Total / Baseline | Autonomous Drone Fleet | Rural Ground Fleet | Modal Comparison (Drone vs. Road) |
| :--- | :---: | :---: | :---: | :---: |
| **Total Requisitions ($N$)** | **{total_n:,}** | {drone_n:,} ({(drone_n/total_n*100):.1f}%) | {road_n:,} ({(road_n/total_n*100):.1f}%) | Denominator basis |
| **Successfully Delivered** | **{total_deliv:,} ({total_deliv_rate:.2f}%)** | {drone_deliv:,} ({drone_deliv_rate:.2f}%) | {road_deliv:,} ({road_deliv_rate:.2f}%) | {deliv_rate_diff_pp:+.2f} percentage points |
| **Stock-Out Rate** | **{total_so:,} ({total_so_rate:.2f}%)** | {drone_so:,} ({drone_so_rate:.2f}%) | {road_so:,} ({road_so_rate:.2f}%) | {so_rate_diff_pp:+.2f} percentage points |
| **Standard OTIF Rate** | **{total_std_otif_rate:.2f}% ({total_std_otif:,} / {total_n:,})** | {drone_std_otif_rate:.2f}% ({drone_std_otif:,} / {drone_n:,}) | {road_std_otif_rate:.2f}% ({road_std_otif:,} / {road_n:,}) | **{std_otif_diff_pp:+.2f} percentage points** |
| **Quality OTIF (OTIF-Q)** | **{total_q_otif_rate:.2f}% ({total_q_otif:,} / {total_n:,})** | {drone_q_otif_rate:.2f}% ({drone_q_otif:,} / {drone_n:,}) | {road_q_otif_rate:.2f}% ({road_q_otif:,} / {road_n:,}) | **{q_otif_diff_pp:+.2f} percentage points** |
| **Average Simulated Lead Time** | **{total_lead:.2f} hours** | **{drone_lead:.2f} hours** | **{road_lead:.2f} hours** | **{lead_diff_hours:+.2f} hours ({lead_reduction_pct:.1f}% relative difference)** |
| **Tier 3 (Deep Rural) Lead Time** | **{t3_total_lead:.2f} hours** | **{t3_drone_lead:.2f} hours** | **{t3_road_lead:.2f} hours** | **{t3_lead_diff_hours:+.2f} hours ({t3_reduction_pct:.1f}% relative difference)** |
| **Cold-Chain Breach Rate** | **{total_breach_rate:.2f}% ({total_cold_breaches:,} / {total_cold_n:,})** | **{drone_breach_rate:.2f}% ({drone_cold_breaches:,} / {drone_cold_n:,})** | **{road_breach_rate:.2f}% ({road_cold_breaches:,} / {road_cold_n:,})** | **{breach_diff_pp:+.2f} percentage points** |"""

    return table_md


if __name__ == "__main__":
    print(generate_simulation_markdown_table())
