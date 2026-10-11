"""Supply Chain Analytics & Metrics Engine.

Provides star-schema joins, runtime data validation, and core operational KPI calculations:
- Runtime schema, relational, and physical consistency validation with many-to-one merge guards
- Standard OTIF (On-Time In-Full) Rate (%) and Quality-Adjusted OTIF (OTIF-Q) Rate (%)
- Order Cycle / Lead Time distributions (hours) across transport modes
- Stock-Out frequencies across regions & product categories
- Modal Transport Efficiency (Drone vs. Road velocity, distance bands, weather impact)
- Cold-Chain thermal integrity strictly evaluated over delivered cold shipments with unknown tracking
- Regional Bottleneck Composite Index with stable normalization benchmarks
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd


# Benchmark constant for stable bottleneck score normalization across all filters
BENCHMARK_MAX_LEAD_TIME_HOURS = 12.0


class DataValidationError(ValueError):
    """Raised when logistics data violates schema requirements, relational integrity, or physical constraints."""
    pass


@dataclass
class ExecutiveKPIs:
    """Core supply chain performance indicators for executive scorecard."""
    total_requests: int
    delivered_orders: int
    on_time_orders: int
    delayed_orders: int
    stock_outs: int
    delivery_success_rate_pct: Optional[float]
    standard_otif_rate_pct: Optional[float]
    quality_otif_rate_pct: Optional[float]
    avg_lead_time_hours: Optional[float]
    drone_avg_lead_time_hours: Optional[float]
    road_avg_lead_time_hours: Optional[float]
    drone_road_delta_hours: Optional[float]
    stock_out_rate_pct: Optional[float]
    cold_chain_integrity_pct: Optional[float]
    total_delivered_cold_orders: int
    cold_chain_breaches_count: int
    unknown_quality_cold_orders: int
    total_units_delivered: int
    total_value_delivered_usd: float


def filter_shipment_ledger(
    df: pd.DataFrame,
    search_query: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> pd.DataFrame:
    """Filter shipment ledger using literal, null-safe text matching and order status.

    Extracts ledger filtering into a reusable function to prevent duplication between
    the UI and test suite, and ensures regex characters like '[' or '*' do not crash queries.
    """
    if df is None or len(df) == 0:
        return pd.DataFrame() if df is None else df.copy()

    df_result = df.copy()

    if status_filter and status_filter != "All Statuses":
        if "order_status_display" in df_result.columns:
            df_result = df_result[df_result["order_status_display"] == status_filter]
        elif "order_status" in df_result.columns:
            df_result = df_result[df_result["order_status"] == status_filter]

    if search_query:
        query = search_query.strip().lower()
        if query:
            # Literal, null-safe string search across relevant dimensional descriptors
            search_cols = ["request_id", "clinic_name", "product_name", "region", "hub_name"]
            match_mask = pd.Series(False, index=df_result.index)
            for col in search_cols:
                if col in df_result.columns:
                    col_matches = df_result[col].astype(str).str.lower().str.contains(query, regex=False, na=False)
                    match_mask = match_mask | col_matches
            df_result = df_result[match_mask]

    return df_result


class SupplyChainMetricsEngine:
    """Analytical engine executing star-schema transformations, data validation, and KPI evaluations."""

    REQUIRED_FACT_COLS = {
        "request_id", "clinic_id", "product_id", "hub_id",
        "requested_timestamp", "dispatch_timestamp", "delivery_timestamp",
        "distance_km", "transport_mode", "order_status",
        "units_requested", "units_delivered", "lead_time_hours"
    }

    REQUIRED_CLINIC_COLS = {
        "clinic_id", "clinic_name", "region",
        "latitude", "longitude", "remote_tier", "nearest_hub"
    }

    REQUIRED_PRODUCT_COLS = {
        "product_id", "product_name", "category",
        "storage_requirement", "target_delivery_hours"
    }

    REQUIRED_HUB_COLS = {
        "hub_id", "hub_name", "region", "latitude", "longitude"
    }

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.df_fact: Optional[pd.DataFrame] = None
        self.df_clinics: Optional[pd.DataFrame] = None
        self.df_products: Optional[pd.DataFrame] = None
        self.df_hubs: Optional[pd.DataFrame] = None
        self.df_master: Optional[pd.DataFrame] = None

    @classmethod
    def validate_raw_data(
        cls,
        df_fact: pd.DataFrame,
        df_clinics: pd.DataFrame,
        df_products: pd.DataFrame,
        df_hubs: pd.DataFrame,
    ) -> None:
        """Validate raw datasets before relational joins.

        Enforces:
        - Required schema columns in fact and dimension tables
        - Unique and non-null primary keys
        - Referential foreign key integrity
        - Logical chronological ordering of timestamps
        - Quantity consistency across delivery statuses
        - Non-negative physical metrics (distance, lead time)
        """
        # 1. Required column validation
        fact_missing = cls.REQUIRED_FACT_COLS - set(df_fact.columns)
        if fact_missing:
            raise DataValidationError(f"fact_shipments missing required columns: {sorted(fact_missing)}")

        clinic_missing = cls.REQUIRED_CLINIC_COLS - set(df_clinics.columns)
        if clinic_missing:
            raise DataValidationError(f"dim_clinics missing required columns: {sorted(clinic_missing)}")

        product_missing = cls.REQUIRED_PRODUCT_COLS - set(df_products.columns)
        if product_missing:
            raise DataValidationError(f"dim_products missing required columns: {sorted(product_missing)}")

        hub_missing = cls.REQUIRED_HUB_COLS - set(df_hubs.columns)
        if hub_missing:
            raise DataValidationError(f"dim_hubs missing required columns: {sorted(hub_missing)}")

        # 2. Primary Key non-null and uniqueness
        for df, pk, table_name in [
            (df_fact, "request_id", "fact_shipments"),
            (df_clinics, "clinic_id", "dim_clinics"),
            (df_products, "product_id", "dim_products"),
            (df_hubs, "hub_id", "dim_hubs"),
        ]:
            if df[pk].isna().any():
                null_count = int(df[pk].isna().sum())
                raise DataValidationError(f"{table_name} has {null_count} null primary key entries in column '{pk}'.")
            if df[pk].duplicated().any():
                dup_count = int(df[pk].duplicated().sum())
                dup_samples = df[pk][df[pk].duplicated()].head(3).tolist()
                raise DataValidationError(
                    f"{table_name} has {dup_count} duplicate primary key values in '{pk}' (e.g. {dup_samples})."
                )

        # 3. Foreign Key referential integrity
        valid_clinics = set(df_clinics["clinic_id"])
        fact_invalid_clinics = set(df_fact["clinic_id"]) - valid_clinics
        if fact_invalid_clinics:
            raise DataValidationError(
                f"fact_shipments contains invalid foreign keys in 'clinic_id': {sorted(list(fact_invalid_clinics))[:3]}"
            )

        valid_products = set(df_products["product_id"])
        fact_invalid_products = set(df_fact["product_id"]) - valid_products
        if fact_invalid_products:
            raise DataValidationError(
                f"fact_shipments contains invalid foreign keys in 'product_id': {sorted(list(fact_invalid_products))[:3]}"
            )

        valid_hubs = set(df_hubs["hub_id"])
        fact_invalid_hubs = set(df_fact["hub_id"]) - valid_hubs
        if fact_invalid_hubs:
            raise DataValidationError(
                f"fact_shipments contains invalid foreign keys in 'hub_id': {sorted(list(fact_invalid_hubs))[:3]}"
            )

        clinic_invalid_hubs = set(df_clinics["nearest_hub"].dropna()) - valid_hubs
        if clinic_invalid_hubs:
            raise DataValidationError(
                f"dim_clinics contains invalid 'nearest_hub' foreign keys: {sorted(list(clinic_invalid_hubs))}"
            )

        # 4. Quantity consistency
        stockouts = df_fact[df_fact["order_status"] == "Stock-Out"]
        if (stockouts["units_delivered"] != 0).any():
            invalid_cnt = int((stockouts["units_delivered"] != 0).sum())
            raise DataValidationError(f"Quantity error: {invalid_cnt} Stock-Out shipments have units_delivered != 0.")

        if (df_fact["units_requested"] <= 0).any():
            invalid_cnt = int((df_fact["units_requested"] <= 0).sum())
            raise DataValidationError(f"Quantity error: {invalid_cnt} shipments have units_requested <= 0.")

        delivered = df_fact[df_fact["order_status"].isin(["Fulfilled", "Delayed"])]
        if (delivered["units_delivered"] <= 0).any():
            invalid_cnt = int((delivered["units_delivered"] <= 0).sum())
            raise DataValidationError(f"Quantity error: {invalid_cnt} delivered shipments have units_delivered <= 0.")

        # 5. Timestamp chronology for delivered shipments
        req_dt = pd.to_datetime(delivered["requested_timestamp"], errors="coerce")
        disp_dt = pd.to_datetime(delivered["dispatch_timestamp"], errors="coerce")
        deliv_dt = pd.to_datetime(delivered["delivery_timestamp"], errors="coerce")

        if (disp_dt < req_dt).any():
            invalid_cnt = int((disp_dt < req_dt).sum())
            raise DataValidationError(f"Timestamp error: {invalid_cnt} shipments have dispatch_timestamp < requested_timestamp.")

        if (deliv_dt < disp_dt).any():
            invalid_cnt = int((deliv_dt < disp_dt).sum())
            raise DataValidationError(f"Timestamp error: {invalid_cnt} shipments have delivery_timestamp < dispatch_timestamp.")

        # 6. Physical metrics sanity
        if (df_fact["distance_km"] < 0).any():
            raise DataValidationError("distance_km cannot contain negative values.")

        deliv_lead = delivered["lead_time_hours"].dropna()
        if (deliv_lead < 0).any():
            raise DataValidationError("lead_time_hours cannot contain negative values for delivered shipments.")

    def load_data(self) -> "SupplyChainMetricsEngine":
        """Load fact and dimension tables from CSV storage and build analytical star-schema."""
        self.df_fact = pd.read_csv(f"{self.data_dir}/fact_shipments.csv")
        self.df_clinics = pd.read_csv(f"{self.data_dir}/dim_clinics.csv")
        self.df_products = pd.read_csv(f"{self.data_dir}/dim_products.csv")
        self.df_hubs = pd.read_csv(f"{self.data_dir}/dim_hubs.csv")

        # Run strict validation before joins
        self.validate_raw_data(self.df_fact, self.df_clinics, self.df_products, self.df_hubs)

        # Parse timestamps safely
        for col in ["requested_timestamp", "dispatch_timestamp", "delivery_timestamp"]:
            if col in self.df_fact.columns:
                self.df_fact[col] = pd.to_datetime(self.df_fact[col], errors="coerce")

        self._build_star_schema()
        return self

    def _build_star_schema(self) -> None:
        """Denormalize fact and dimension tables with many-to-one merge guards.

        Validates merges to guarantee dimension duplicates cannot multiply shipment rows.
        Recomputes on-time delivery flags and handles missing cold-chain quality values as unknown.
        """
        # Guard against dimension duplicates multiplying shipment records using validate="many_to_one"
        df = self.df_fact.merge(
            self.df_clinics,
            on="clinic_id",
            how="left",
            suffixes=("", "_clinic"),
            validate="many_to_one"
        ).merge(
            self.df_products,
            on="product_id",
            how="left",
            suffixes=("", "_product"),
            validate="many_to_one"
        ).merge(
            self.df_hubs,
            on="hub_id",
            how="left",
            suffixes=("", "_hub"),
            validate="many_to_one"
        )

        # Ensure nearest_hub is explicitly present; fall back to hub_id if missing in dim_clinics
        if "nearest_hub" not in df.columns or df["nearest_hub"].isna().any():
            if "nearest_hub" not in df.columns:
                df["nearest_hub"] = df["hub_id"]
            else:
                df["nearest_hub"] = df["nearest_hub"].fillna(df["hub_id"])

        # Derived temporal attributes
        df["request_date"] = df["requested_timestamp"].dt.date
        df["year_month"] = df["requested_timestamp"].dt.to_period("M").astype(str)
        df["week"] = df["requested_timestamp"].dt.isocalendar().week
        df["day_of_week"] = df["requested_timestamp"].dt.day_name()
        df["hour_of_day"] = df["requested_timestamp"].dt.hour

        # Open-ended distance brackets ensuring distances above 300 km are retained
        distance_bins = [0.0, 25.0, 50.0, 75.0, 100.0, 150.0, float("inf")]
        distance_labels = ["0-25 km", "25-50 km", "50-75 km", "75-100 km", "100-150 km", "150+ km"]
        df["distance_band"] = pd.cut(df["distance_km"], bins=distance_bins, labels=distance_labels, right=True)

        # Value calculated
        df["order_value_usd"] = df["units_delivered"].fillna(0) * df["unit_cost_usd"].fillna(0)

        # 1. Delivery Classification:
        # Delivered orders have confirmed delivery timestamp and positive units delivered
        df["is_delivered"] = df["delivery_timestamp"].notna() & (df["units_delivered"] > 0) & (df["order_status"] != "Stock-Out")

        # 2. Strict On-Time Delivery Flag recomputed against the single product target deadline
        # (Both Drone and Road are evaluated against the exact same product SLA deadline)
        df["is_on_time"] = (
            df["is_delivered"]
            & df["lead_time_hours"].notna()
            & (df["lead_time_hours"] <= df["target_delivery_hours"])
        )

        # 3. Delayed Orders: Delivered, but exceeded target deadline
        df["is_delayed"] = df["is_delivered"] & (~df["is_on_time"])

        # 4. In-Full Condition: Delivered quantity equals requested quantity
        df["is_in_full"] = df["is_delivered"] & (df["units_delivered"] == df["units_requested"])

        # 5. Quality Compliance Condition:
        # For cold-chain products:
        #   - False breach -> Quality pass
        #   - True breach  -> Quality fail
        #   - NaN/missing  -> Unknown quality (CANNOT be silently treated as a pass!)
        # For ambient products: Quality compliance is inherent (not temperature-controlled).
        is_cold = df["storage_requirement"] == "Cold Chain"
        df["is_cold_chain"] = is_cold
        df["quality_known"] = (~is_cold) | (df["cold_chain_breach"].notna())
        df["is_quality_pass"] = False

        # Cold chain pass only when explicitly False (verified no breach)
        df.loc[is_cold & (df["cold_chain_breach"] == False), "is_quality_pass"] = True
        # Ambient items automatically pass thermal compliance
        df.loc[~is_cold, "is_quality_pass"] = True

        # 6. Standard OTIF: On-Time AND In-Full
        df["is_standard_otif"] = df["is_on_time"] & df["is_in_full"]

        # 7. Quality-Adjusted OTIF (OTIF-Q): Standard OTIF AND verified Quality Pass
        df["is_quality_otif"] = df["is_standard_otif"] & df["is_quality_pass"]

        # Sync master order status view for display consistency
        df.loc[df["order_status"] == "Stock-Out", "order_status_display"] = "Stock-Out"
        df.loc[df["is_on_time"], "order_status_display"] = "Delivered (On-Time)"
        df.loc[df["is_delayed"], "order_status_display"] = "Delivered (Delayed)"

        self.df_master = df

    def filter_data(
        self,
        regions: Optional[List[str]] = None,
        date_range: Optional[Union[Tuple[pd.Timestamp, pd.Timestamp], List[pd.Timestamp]]] = None,
        product_categories: Optional[List[str]] = None,
        transport_modes: Optional[List[str]] = None,
        remote_tiers: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Apply multidimensional slice-and-dice filters to the analytical view.

        Distinguishes omitted filters (None -> keep all) from explicitly empty selections ([] -> 0 records).
        Handles incomplete or single-date selections safely.
        """
        df = self.df_master.copy()

        if regions is not None:
            df = df[df["region"].isin(regions)]

        if product_categories is not None:
            df = df[df["category"].isin(product_categories)]

        if transport_modes is not None:
            df = df[df["transport_mode"].isin(transport_modes)]

        if remote_tiers is not None:
            df = df[df["remote_tier"].isin(remote_tiers)]

        if date_range is not None:
            if isinstance(date_range, (tuple, list)) and len(date_range) >= 1:
                start_date = date_range[0]
                end_date = date_range[1] if len(date_range) > 1 else date_range[0]
                if start_date is not None and end_date is not None:
                    if hasattr(start_date, "date"):
                        start_date = start_date.date()
                    if hasattr(end_date, "date"):
                        end_date = end_date.date()
                    df = df[
                        (df["requested_timestamp"].dt.date >= start_date)
                        & (df["requested_timestamp"].dt.date <= end_date)
                    ]

        return df

    @staticmethod
    def compute_executive_kpis(df: pd.DataFrame) -> ExecutiveKPIs:
        """Calculate high-level executive KPIs from filtered dataset.

        Returns None for metrics that have no eligible denominator records, enabling
        clean 'N/A' display in the UI. Explicitly tracks unknown quality counts.
        """
        total_requests = len(df)
        if total_requests == 0:
            return ExecutiveKPIs(
                total_requests=0,
                delivered_orders=0,
                on_time_orders=0,
                delayed_orders=0,
                stock_outs=0,
                delivery_success_rate_pct=None,
                standard_otif_rate_pct=None,
                quality_otif_rate_pct=None,
                avg_lead_time_hours=None,
                drone_avg_lead_time_hours=None,
                road_avg_lead_time_hours=None,
                drone_road_delta_hours=None,
                stock_out_rate_pct=None,
                cold_chain_integrity_pct=None,
                total_delivered_cold_orders=0,
                cold_chain_breaches_count=0,
                unknown_quality_cold_orders=0,
                total_units_delivered=0,
                total_value_delivered_usd=0.0,
            )

        delivered_orders = int(df["is_delivered"].sum())
        on_time_orders = int(df["is_on_time"].sum())
        delayed_orders = int(df["is_delayed"].sum())
        stock_outs = int((df["order_status"] == "Stock-Out").sum())

        delivery_success_rate = (delivered_orders / total_requests) * 100.0
        standard_otif_rate = (df["is_standard_otif"].sum() / total_requests) * 100.0
        quality_otif_rate = (df["is_quality_otif"].sum() / total_requests) * 100.0
        stock_out_rate = (stock_outs / total_requests) * 100.0

        # Lead times computed strictly over delivered shipments
        delivered_df = df[df["is_delivered"]]
        avg_lead_time = (
            round(float(delivered_df["lead_time_hours"].mean()), 2)
            if len(delivered_df) > 0 and delivered_df["lead_time_hours"].notna().any()
            else None
        )

        drone_delivered = delivered_df[delivered_df["transport_mode"] == "Drone"]
        road_delivered = delivered_df[delivered_df["transport_mode"] == "Road"]

        drone_avg_lead_time = (
            round(float(drone_delivered["lead_time_hours"].mean()), 2)
            if len(drone_delivered) > 0 and drone_delivered["lead_time_hours"].notna().any()
            else None
        )
        road_avg_lead_time = (
            round(float(road_delivered["lead_time_hours"].mean()), 2)
            if len(road_delivered) > 0 and road_delivered["lead_time_hours"].notna().any()
            else None
        )

        # Drone vs Road delta is computed only when BOTH groups contain deliveries
        drone_road_delta = (
            round(road_avg_lead_time - drone_avg_lead_time, 2)
            if (road_avg_lead_time is not None and drone_avg_lead_time is not None)
            else None
        )

        # Cold chain integrity evaluated strictly among delivered cold-chain shipments
        delivered_cold = delivered_df[delivered_df["storage_requirement"] == "Cold Chain"]
        total_delivered_cold = len(delivered_cold)

        if total_delivered_cold > 0:
            breaches_count = int((delivered_cold["cold_chain_breach"] == True).sum())
            unknown_quality_count = int(delivered_cold["cold_chain_breach"].isna().sum())
            known_delivered_cold = delivered_cold[delivered_cold["cold_chain_breach"].notna()]

            # Verified integrity evaluated over known delivered cold items
            if len(known_delivered_cold) > 0:
                cold_chain_integrity = round(
                    ((known_delivered_cold["cold_chain_breach"] == False).sum() / len(known_delivered_cold)) * 100.0,
                    2
                )
            else:
                cold_chain_integrity = None
        else:
            breaches_count = 0
            unknown_quality_count = 0
            cold_chain_integrity = None

        total_units = int(df["units_delivered"].sum())
        total_value = float(df["order_value_usd"].sum())

        return ExecutiveKPIs(
            total_requests=total_requests,
            delivered_orders=delivered_orders,
            on_time_orders=on_time_orders,
            delayed_orders=delayed_orders,
            stock_outs=stock_outs,
            delivery_success_rate_pct=round(delivery_success_rate, 2),
            standard_otif_rate_pct=round(standard_otif_rate, 2),
            quality_otif_rate_pct=round(quality_otif_rate, 2),
            avg_lead_time_hours=avg_lead_time,
            drone_avg_lead_time_hours=drone_avg_lead_time,
            road_avg_lead_time_hours=road_avg_lead_time,
            drone_road_delta_hours=drone_road_delta,
            stock_out_rate_pct=round(stock_out_rate, 2),
            cold_chain_integrity_pct=cold_chain_integrity,
            total_delivered_cold_orders=total_delivered_cold,
            cold_chain_breaches_count=breaches_count,
            unknown_quality_cold_orders=unknown_quality_count,
            total_units_delivered=total_units,
            total_value_delivered_usd=round(total_value, 2),
        )

    @staticmethod
    def get_weekly_trend(df: pd.DataFrame) -> pd.DataFrame:
        """Compute weekly aggregated time-series of volume, OTIF, and delay rates."""
        if len(df) == 0:
            return pd.DataFrame()

        df_trend = df.copy()
        df_trend["week_start"] = df_trend["requested_timestamp"].dt.to_period("W").dt.start_time

        agg = df_trend.groupby("week_start").agg(
            total_requests=("request_id", "count"),
            delivered=("is_delivered", "sum"),
            on_time=("is_on_time", "sum"),
            delayed=("is_delayed", "sum"),
            stock_outs=("order_status", lambda s: (s == "Stock-Out").sum()),
            std_otif=("is_standard_otif", "sum"),
            quality_otif=("is_quality_otif", "sum"),
            avg_lead_time=("lead_time_hours", lambda s: s[df_trend.loc[s.index, "is_delivered"]].mean()),
        ).reset_index()

        agg["standard_otif_rate_pct"] = (agg["std_otif"] / agg["total_requests"]) * 100.0
        agg["quality_otif_rate_pct"] = (agg["quality_otif"] / agg["total_requests"]) * 100.0
        agg["delay_rate_pct"] = (agg["delayed"] / agg["total_requests"]) * 100.0
        agg["stock_out_rate_pct"] = (agg["stock_outs"] / agg["total_requests"]) * 100.0
        return agg.sort_values("week_start")

    @staticmethod
    def get_modal_comparison(df: pd.DataFrame) -> pd.DataFrame:
        """Compare lead times, distance, and OTIF rates across transport modes and distance bands."""
        delivered_df = df[df["is_delivered"]].copy()
        if len(delivered_df) == 0:
            return pd.DataFrame()

        grouped = delivered_df.groupby(["distance_band", "transport_mode"], observed=True).agg(
            shipment_count=("request_id", "count"),
            avg_lead_time_hours=("lead_time_hours", "mean"),
            median_lead_time_hours=("lead_time_hours", "median"),
            standard_otif_rate_pct=("is_standard_otif", lambda s: (s.sum() / len(s)) * 100.0),
            quality_otif_rate_pct=("is_quality_otif", lambda s: (s.sum() / len(s)) * 100.0),
            cold_chain_breach_pct=("cold_chain_breach", lambda s: (s.sum() / len(s)) * 100.0),
            avg_distance_km=("distance_km", "mean"),
        ).reset_index()

        grouped["effective_speed_kmh"] = grouped["avg_distance_km"] / grouped["avg_lead_time_hours"]
        return grouped

    @staticmethod
    def get_stockout_diagnostics(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Compute stock-out frequencies by product category and by administrative region."""
        if len(df) == 0:
            return pd.DataFrame(), pd.DataFrame()

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
            delays=("is_delayed", "sum"),
            std_otif=("is_standard_otif", "sum"),
            avg_lead_time=("lead_time_hours", lambda s: s[df.loc[s.index, "is_delivered"]].mean()),
        ).reset_index()
        reg_agg["stock_out_rate_pct"] = (reg_agg["stock_outs"] / reg_agg["total_requests"]) * 100.0
        reg_agg["standard_otif_rate_pct"] = (reg_agg["std_otif"] / reg_agg["total_requests"]) * 100.0
        reg_agg = reg_agg.sort_values("stock_out_rate_pct", ascending=False)

        return cat_agg, reg_agg

    @staticmethod
    def get_regional_bottlenecks(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Regional Bottleneck Composite Index (0-100 scale).

        Methodological Formulation & Assumptions:
        - Evaluates vulnerability across four weighted risk factors:
          1. Stock-Out Rate (weight: 0.35): Unfulfilled critical healthcare demand.
          2. Delivery Delay Rate (weight: 0.35): Late arrivals relative to medical SLA.
          3. Lead Time Severity (weight: 0.20): Normalized against a fixed operational benchmark
             of 12.0 hours (BENCHMARK_MAX_LEAD_TIME_HOURS) rather than a relative filter max,
             ensuring stable scoring across filters. If a region has zero delivered orders due to
             100% stock-outs, it receives the full 20-point penalty rather than 0.
          4. Cold-Chain Breach Rate (weight: 0.10): Quality failures among delivered cold cargo.

        Index Formula:
        Score = 0.35 * StockOut% + 0.35 * Delay% + 20.0 * min(1.0, LeadTime / 12.0) + 0.10 * ColdBreach%
        """
        if len(df) == 0:
            return pd.DataFrame()

        def compute_region_metrics(group: pd.DataFrame) -> pd.Series:
            total_orders = len(group)
            stock_outs = (group["order_status"] == "Stock-Out").sum()
            delays = group["is_delayed"].sum()
            stock_out_rate = (stock_outs / total_orders) * 100.0 if total_orders > 0 else 0.0
            delay_rate = (delays / total_orders) * 100.0 if total_orders > 0 else 0.0

            delivered = group[group["is_delivered"]]
            has_delivered = len(delivered) > 0 and delivered["lead_time_hours"].notna().any()
            avg_lead_time = delivered["lead_time_hours"].mean() if has_delivered else np.nan

            cold_delivered = delivered[delivered["storage_requirement"] == "Cold Chain"]
            known_cold = cold_delivered[cold_delivered["cold_chain_breach"].notna()]
            cold_breach_rate = (
                ((known_cold["cold_chain_breach"] == True).sum() / len(known_cold)) * 100.0
                if len(known_cold) > 0
                else 0.0
            )

            drone_share = (group["transport_mode"] == "Drone").mean() * 100.0 if total_orders > 0 else 0.0

            # Normalization against fixed benchmark constant:
            # If no shipments were delivered (e.g. 100% stockouts), impute maximum lead time penalty (1.0 * 20.0)
            if pd.isna(avg_lead_time):
                lead_time_penalty = 20.0
            else:
                lead_time_penalty = min(float(avg_lead_time) / BENCHMARK_MAX_LEAD_TIME_HOURS, 1.0) * 20.0

            bottleneck_score = round(
                (stock_out_rate * 0.35)
                + (delay_rate * 0.35)
                + lead_time_penalty
                + (cold_breach_rate * 0.10),
                1
            )

            return pd.Series({
                "total_orders": total_orders,
                "stock_out_rate": round(stock_out_rate, 1),
                "delay_rate": round(delay_rate, 1),
                "avg_lead_time_hours": round(avg_lead_time, 2) if pd.notna(avg_lead_time) else np.nan,
                "cold_breach_rate": round(cold_breach_rate, 1),
                "drone_share_pct": round(drone_share, 1),
                "bottleneck_score": bottleneck_score,
            })

        reg_df = df.groupby("region", as_index=False).apply(compute_region_metrics)
        return reg_df.sort_values("bottleneck_score", ascending=False)

    @staticmethod
    def get_clinic_performance_summary(df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate performance metrics at individual clinic granularity.

        Preserves valid nearest_hub relationships or derives them from actual shipment records
        to prevent silent defaulting in geospatial visualizations.
        """
        if len(df) == 0:
            return pd.DataFrame()

        group_cols = ["clinic_id", "clinic_name", "region", "remote_tier", "latitude", "longitude", "nearest_hub"]
        for col in group_cols:
            if col not in df.columns:
                if col == "nearest_hub":
                    df["nearest_hub"] = df["hub_id"]

        clinic_agg = df.groupby(group_cols, observed=True).agg(
            total_orders=("request_id", "count"),
            delivered=("is_delivered", "sum"),
            on_time=("is_on_time", "sum"),
            delayed=("is_delayed", "sum"),
            stock_outs=("order_status", lambda s: (s == "Stock-Out").sum()),
            std_otif=("is_standard_otif", "sum"),
            quality_otif=("is_quality_otif", "sum"),
            avg_lead_time_hours=("lead_time_hours", lambda s: s[df.loc[s.index, "is_delivered"]].mean()),
            drone_share_pct=("transport_mode", lambda s: (s == "Drone").mean() * 100.0),
            cold_chain_breaches=("cold_chain_breach", lambda s: (s[df.loc[s.index, "is_delivered"]] == True).sum()),
        ).reset_index()

        clinic_agg["standard_otif_rate_pct"] = (
            (clinic_agg["std_otif"] / clinic_agg["total_orders"]) * 100.0
        ).round(1)

        clinic_agg["quality_otif_rate_pct"] = (
            (clinic_agg["quality_otif"] / clinic_agg["total_orders"]) * 100.0
        ).round(1)

        # Risk tier categorization rationale:
        # Standard OTIF < 65% represents a critical supply failure rate.
        # Stockouts > 8% signifies severe localized inventory depletion.
        # 65% - 80% represents an unstable intermediate operational buffer.
        # >= 80% aligns with humanitarian healthcare distribution benchmarks.
        def assign_risk(row: pd.Series) -> str:
            stockout_freq = row["stock_outs"] / row["total_orders"] if row["total_orders"] > 0 else 0
            if row["standard_otif_rate_pct"] < 65.0 or stockout_freq > 0.08:
                return "High Risk"
            elif row["standard_otif_rate_pct"] < 80.0:
                return "Moderate Risk"
            return "Optimal"

        clinic_agg["risk_tier"] = clinic_agg.apply(assign_risk, axis=1)
        clinic_agg["avg_lead_time_hours"] = clinic_agg["avg_lead_time_hours"].round(2)
        clinic_agg["drone_share_pct"] = clinic_agg["drone_share_pct"].round(1)

        return clinic_agg
