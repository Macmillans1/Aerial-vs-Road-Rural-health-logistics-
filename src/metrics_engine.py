"""Supply Chain Analytics & Metrics Engine.

Provides star-schema joins, data transformations, and core operational KPI calculations:
- OTIF (On-Time In-Full) Rate (%)
- Order Cycle / Lead Time distributions (hours)
- Stock-Out frequencies across regions & product categories
- Modal Transport Efficiency (Drone vs. Road velocity, distance bands, weather impact)
- Cold-Chain integrity and Regional Bottleneck Indices
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class ExecutiveKPIs:
    """Core supply chain performance indicators for executive scorecard."""
    total_requests: int
    fulfilled_orders: int
    delayed_orders: int
    stock_outs: int
    fulfillment_rate_pct: float
    otif_rate_pct: float
    avg_lead_time_hours: float
    drone_avg_lead_time_hours: float
    road_avg_lead_time_hours: float
    stock_out_rate_pct: float
    cold_chain_integrity_pct: float
    total_units_delivered: int
    total_value_delivered_usd: float


class SupplyChainMetricsEngine:
    """Analytical engine executing star-schema transformations and metric evaluations."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.df_fact: Optional[pd.DataFrame] = None
        self.df_clinics: Optional[pd.DataFrame] = None
        self.df_products: Optional[pd.DataFrame] = None
        self.df_hubs: Optional[pd.DataFrame] = None
        self.df_master: Optional[pd.DataFrame] = None

    def load_data(self) -> "SupplyChainMetricsEngine":
        """Load fact and dimension tables from CSV storage."""
        self.df_fact = pd.read_csv(f"{self.data_dir}/fact_shipments.csv")
        self.df_clinics = pd.read_csv(f"{self.data_dir}/dim_clinics.csv")
        self.df_products = pd.read_csv(f"{self.data_dir}/dim_products.csv")
        self.df_hubs = pd.read_csv(f"{self.data_dir}/dim_hubs.csv")

        # Parse timestamps
        for col in ["requested_timestamp", "dispatch_timestamp", "delivery_timestamp"]:
            self.df_fact[col] = pd.to_datetime(self.df_fact[col], errors="coerce")

        self._build_star_schema()
        return self

    def _build_star_schema(self) -> None:
        """Denormalize fact and dimension tables into an analytical star-schema master dataframe."""
        df = self.df_fact.merge(
            self.df_clinics,
            on="clinic_id",
            how="left",
            suffixes=("", "_clinic")
        ).merge(
            self.df_products,
            on="product_id",
            how="left",
            suffixes=("", "_product")
        ).merge(
            self.df_hubs,
            on="hub_id",
            how="left",
            suffixes=("", "_hub")
        )

        # Derived temporal attributes
        df["request_date"] = df["requested_timestamp"].dt.date
        df["year_month"] = df["requested_timestamp"].dt.to_period("M").astype(str)
        df["week"] = df["requested_timestamp"].dt.isocalendar().week
        df["day_of_week"] = df["requested_timestamp"].dt.day_name()
        df["hour_of_day"] = df["requested_timestamp"].dt.hour

        # Distance brackets
        distance_bins = [0, 25, 50, 75, 100, 150, 300]
        distance_labels = ["0-25 km", "25-50 km", "50-75 km", "75-100 km", "100-150 km", "150+ km"]
        df["distance_band"] = pd.cut(df["distance_km"], bins=distance_bins, labels=distance_labels, right=True)

        # Value calculated
        df["order_value_usd"] = df["units_delivered"] * df["unit_cost_usd"]

        # Strict Supply Chain OTIF Definition:
        # 1. On-Time: is_on_time == True
        # 2. In-Full: units_delivered == units_requested and order_status != 'Stock-Out'
        # 3. Quality: For cold-chain items, cold_chain_breach must be False
        df["is_in_full"] = (df["units_delivered"] == df["units_requested"]) & (df["order_status"] != "Stock-Out")
        df["is_quality_pass"] = ~df["cold_chain_breach"]
        df["is_otif"] = df["is_on_time"] & df["is_in_full"] & df["is_quality_pass"]

        self.df_master = df

    def filter_data(
        self,
        regions: Optional[List[str]] = None,
        date_range: Optional[Tuple[pd.Timestamp, pd.Timestamp]] = None,
        product_categories: Optional[List[str]] = None,
        transport_modes: Optional[List[str]] = None,
        remote_tiers: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Apply multidimensional slice-and-dice filters to the analytical view."""
        df = self.df_master.copy()

        if regions and len(regions) > 0 and "All" not in regions:
            df = df[df["region"].isin(regions)]

        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            df = df[
                (df["requested_timestamp"].dt.date >= start_date)
                & (df["requested_timestamp"].dt.date <= end_date)
            ]

        if product_categories and len(product_categories) > 0 and "All" not in product_categories:
            df = df[df["category"].isin(product_categories)]

        if transport_modes and len(transport_modes) > 0 and "All" not in transport_modes:
            df = df[df["transport_mode"].isin(transport_modes)]

        if remote_tiers and len(remote_tiers) > 0 and "All" not in remote_tiers:
            df = df[df["remote_tier"].isin(remote_tiers)]

        return df

    @staticmethod
    def compute_executive_kpis(df: pd.DataFrame) -> ExecutiveKPIs:
        """Calculate high-level executive KPIs from filtered dataset."""
        total_requests = len(df)
        if total_requests == 0:
            return ExecutiveKPIs(0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0.0)

        fulfilled_orders = int((df["order_status"] == "Fulfilled").sum())
        delayed_orders = int((df["order_status"] == "Delayed").sum())
        stock_outs = int((df["order_status"] == "Stock-Out").sum())

        fulfillment_rate = (fulfilled_orders / total_requests) * 100.0
        otif_rate = (df["is_otif"].sum() / total_requests) * 100.0

        # Lead times (exclude stockouts with NaN)
        delivered_mask = df["order_status"].isin(["Fulfilled", "Delayed"])
        avg_lead_time = df.loc[delivered_mask, "lead_time_hours"].mean() if delivered_mask.any() else 0.0

        drone_mask = delivered_mask & (df["transport_mode"] == "Drone")
        road_mask = delivered_mask & (df["transport_mode"] == "Road")

        drone_avg_lead_time = df.loc[drone_mask, "lead_time_hours"].mean() if drone_mask.any() else 0.0
        road_avg_lead_time = df.loc[road_mask, "lead_time_hours"].mean() if road_mask.any() else 0.0

        stock_out_rate = (stock_outs / total_requests) * 100.0

        # Cold chain integrity
        cold_chain_df = df[df["storage_requirement"] == "Cold Chain"]
        if len(cold_chain_df) > 0:
            cold_chain_integrity = (1.0 - (cold_chain_df["cold_chain_breach"].sum() / len(cold_chain_df))) * 100.0
        else:
            cold_chain_integrity = 100.0

        total_units = int(df["units_delivered"].sum())
        total_value = float(df["order_value_usd"].sum())

        return ExecutiveKPIs(
            total_requests=total_requests,
            fulfilled_orders=fulfilled_orders,
            delayed_orders=delayed_orders,
            stock_outs=stock_outs,
            fulfillment_rate_pct=round(fulfillment_rate, 2),
            otif_rate_pct=round(otif_rate, 2),
            avg_lead_time_hours=round(avg_lead_time, 2),
            drone_avg_lead_time_hours=round(drone_avg_lead_time, 2),
            road_avg_lead_time_hours=round(road_avg_lead_time, 2),
            stock_out_rate_pct=round(stock_out_rate, 2),
            cold_chain_integrity_pct=round(cold_chain_integrity, 2),
            total_units_delivered=total_units,
            total_value_delivered_usd=round(total_value, 2),
        )

    @staticmethod
    def get_weekly_trend(df: pd.DataFrame) -> pd.DataFrame:
        """Compute weekly aggregated time-series of volume, OTIF, and delay rates."""
        if len(df) == 0:
            return pd.DataFrame()

        df_trend = df.copy()
        # Group by weekly period
        df_trend["week_start"] = df_trend["requested_timestamp"].dt.to_period("W").dt.start_time

        agg = df_trend.groupby("week_start").agg(
            total_requests=("request_id", "count"),
            fulfilled=("order_status", lambda s: (s == "Fulfilled").sum()),
            delayed=("order_status", lambda s: (s == "Delayed").sum()),
            stock_outs=("order_status", lambda s: (s == "Stock-Out").sum()),
            otif_count=("is_otif", "sum"),
            avg_lead_time=("lead_time_hours", "mean"),
        ).reset_index()

        agg["otif_rate_pct"] = (agg["otif_count"] / agg["total_requests"]) * 100.0
        agg["delay_rate_pct"] = (agg["delayed"] / agg["total_requests"]) * 100.0
        agg["stock_out_rate_pct"] = (agg["stock_outs"] / agg["total_requests"]) * 100.0
        return agg.sort_values("week_start")

    @staticmethod
    def get_modal_comparison(df: pd.DataFrame) -> pd.DataFrame:
        """Compare lead times, distance, and OTIF rates across transport modes and distance bands."""
        delivered_df = df[df["order_status"].isin(["Fulfilled", "Delayed"])].copy()
        if len(delivered_df) == 0:
            return pd.DataFrame()

        grouped = delivered_df.groupby(["distance_band", "transport_mode"], observed=True).agg(
            shipment_count=("request_id", "count"),
            avg_lead_time_hours=("lead_time_hours", "mean"),
            median_lead_time_hours=("lead_time_hours", "median"),
            otif_rate_pct=("is_otif", lambda s: (s.sum() / len(s)) * 100.0),
            cold_chain_breach_pct=("cold_chain_breach", lambda s: (s.sum() / len(s)) * 100.0),
            avg_distance_km=("distance_km", "mean"),
        ).reset_index()

        # Compute speed km/h
        grouped["effective_speed_kmh"] = grouped["avg_distance_km"] / grouped["avg_lead_time_hours"]
        return grouped

    @staticmethod
    def get_stockout_diagnostics(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Compute stock-out frequencies by product category and by administrative region."""
        # By Category
        cat_agg = df.groupby("category").agg(
            total_requests=("request_id", "count"),
            stock_outs=("order_status", lambda s: (s == "Stock-Out").sum()),
            unmet_units=("units_requested", lambda s: s[df.loc[s.index, "order_status"] == "Stock-Out"].sum()),
        ).reset_index()
        cat_agg["stock_out_rate_pct"] = (cat_agg["stock_outs"] / cat_agg["total_requests"]) * 100.0
        cat_agg = cat_agg.sort_values("stock_out_rate_pct", ascending=False)

        # By Region
        reg_agg = df.groupby(["region", "remote_tier"]).agg(
            total_requests=("request_id", "count"),
            stock_outs=("order_status", lambda s: (s == "Stock-Out").sum()),
            delays=("order_status", lambda s: (s == "Delayed").sum()),
            otif_count=("is_otif", "sum"),
            avg_lead_time=("lead_time_hours", "mean"),
        ).reset_index()
        reg_agg["stock_out_rate_pct"] = (reg_agg["stock_outs"] / reg_agg["total_requests"]) * 100.0
        reg_agg["otif_rate_pct"] = (reg_agg["otif_count"] / reg_agg["total_requests"]) * 100.0
        reg_agg = reg_agg.sort_values("stock_out_rate_pct", ascending=False)

        return cat_agg, reg_agg

    @staticmethod
    def get_regional_bottlenecks(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Regional Bottleneck Composite Index (0-100 scale)."""
        reg_df = df.groupby("region").agg(
            total_orders=("request_id", "count"),
            stock_out_rate=("order_status", lambda s: (s == "Stock-Out").mean() * 100.0),
            delay_rate=("order_status", lambda s: (s == "Delayed").mean() * 100.0),
            avg_lead_time_hours=("lead_time_hours", "mean"),
            cold_breach_rate=("cold_chain_breach", lambda s: s.mean() * 100.0),
            drone_share_pct=("transport_mode", lambda s: (s == "Drone").mean() * 100.0),
        ).reset_index()

        # Composite Bottleneck Index: Higher means more acute logistics vulnerability
        # Normalized weighted formula:
        reg_df["bottleneck_score"] = (
            reg_df["stock_out_rate"] * 0.35
            + reg_df["delay_rate"] * 0.35
            + (reg_df["avg_lead_time_hours"] / reg_df["avg_lead_time_hours"].max() * 20.0)
            + reg_df["cold_breach_rate"] * 0.10
        ).round(1)

        return reg_df.sort_values("bottleneck_score", ascending=False)

    @staticmethod
    def get_clinic_performance_summary(df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate performance metrics at individual clinic granularity for map and drill-down."""
        clinic_agg = df.groupby(["clinic_id", "clinic_name", "region", "remote_tier", "latitude", "longitude"]).agg(
            total_orders=("request_id", "count"),
            fulfilled=("order_status", lambda s: (s == "Fulfilled").sum()),
            delayed=("order_status", lambda s: (s == "Delayed").sum()),
            stock_outs=("order_status", lambda s: (s == "Stock-Out").sum()),
            otif_rate_pct=("is_otif", lambda s: (s.sum() / len(s)) * 100.0),
            avg_lead_time_hours=("lead_time_hours", "mean"),
            drone_share_pct=("transport_mode", lambda s: (s == "Drone").mean() * 100.0),
            cold_chain_breaches=("cold_chain_breach", "sum"),
        ).reset_index()

        # Risk categorization
        def assign_risk(row):
            if row["otif_rate_pct"] < 70.0 or row["stock_outs"] / row["total_orders"] > 0.08:
                return "High Risk"
            elif row["otif_rate_pct"] < 85.0:
                return "Moderate Risk"
            return "Optimal"

        clinic_agg["risk_tier"] = clinic_agg.apply(assign_risk, axis=1)
        clinic_agg["avg_lead_time_hours"] = clinic_agg["avg_lead_time_hours"].round(2)
        clinic_agg["otif_rate_pct"] = clinic_agg["otif_rate_pct"].round(1)
        clinic_agg["drone_share_pct"] = clinic_agg["drone_share_pct"].round(1)

        return clinic_agg
