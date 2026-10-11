"""Focused Validation and Regression Test Suite for Rural Healthcare Logistics.

Covers:
- Primary key uniqueness and foreign key integrity
- Chronological timestamp ordering
- Requisition and delivered quantity consistency
- Deadline calculations across transport modalities
- Cold-chain integrity denominator correctness
- Clinic-to-hub mapping preservation without silent defaulting
- Open-ended distance bin retention for distances above 300 km
- Explicitly empty filter vs omitted filter distinctions
- Single-mode comparison safety (avoiding invalid deltas)
- Punctuation and regex-character search safety
"""

import os
import tempfile
import unittest
import numpy as np
import pandas as pd

from src.metrics_engine import (
    SupplyChainMetricsEngine,
    ExecutiveKPIs,
    DataValidationError,
    filter_shipment_ledger,
)
from src.map_visualizer import build_pydeck_logistics_map


class TestSupplyChainDataIntegrity(unittest.TestCase):
    """Test suite verifying raw data integrity and dimensional constraints."""

    @classmethod
    def setUpClass(cls):
        cls.data_dir = "data"
        cls.df_fact = pd.read_csv(f"{cls.data_dir}/fact_shipments.csv")
        cls.df_clinics = pd.read_csv(f"{cls.data_dir}/dim_clinics.csv")
        cls.df_products = pd.read_csv(f"{cls.data_dir}/dim_products.csv")
        cls.df_hubs = pd.read_csv(f"{cls.data_dir}/dim_hubs.csv")

    def test_duplicate_primary_keys(self):
        """Ensure all primary keys are unique across fact and dimension tables."""
        self.assertEqual(
            self.df_fact["request_id"].nunique(),
            len(self.df_fact),
            "Duplicate request_id found in fact_shipments.csv"
        )
        self.assertEqual(
            self.df_clinics["clinic_id"].nunique(),
            len(self.df_clinics),
            "Duplicate clinic_id found in dim_clinics.csv"
        )
        self.assertEqual(
            self.df_products["product_id"].nunique(),
            len(self.df_products),
            "Duplicate product_id found in dim_products.csv"
        )
        self.assertEqual(
            self.df_hubs["hub_id"].nunique(),
            len(self.df_hubs),
            "Duplicate hub_id found in dim_hubs.csv"
        )

    def test_missing_foreign_keys(self):
        """Ensure all foreign keys in fact and dimension tables resolve to valid dimension records."""
        valid_clinics = set(self.df_clinics["clinic_id"])
        valid_products = set(self.df_products["product_id"])
        valid_hubs = set(self.df_hubs["hub_id"])

        # Fact table FK integrity
        self.assertTrue(
            set(self.df_fact["clinic_id"]).issubset(valid_clinics),
            "Fact table contains clinic_id not found in dim_clinics"
        )
        self.assertTrue(
            set(self.df_fact["product_id"]).issubset(valid_products),
            "Fact table contains product_id not found in dim_products"
        )
        self.assertTrue(
            set(self.df_fact["hub_id"]).issubset(valid_hubs),
            "Fact table contains hub_id not found in dim_hubs"
        )

        # Clinic nearest_hub FK integrity
        self.assertTrue(
            set(self.df_clinics["nearest_hub"]).issubset(valid_hubs),
            "dim_clinics contains nearest_hub not found in dim_hubs"
        )

    def test_timestamp_order(self):
        """Ensure chronological order: requested_timestamp <= dispatch_timestamp <= delivery_timestamp."""
        delivered = self.df_fact[self.df_fact["order_status"].isin(["Fulfilled", "Delayed"])].copy()

        req_dt = pd.to_datetime(delivered["requested_timestamp"])
        disp_dt = pd.to_datetime(delivered["dispatch_timestamp"])
        deliv_dt = pd.to_datetime(delivered["delivery_timestamp"])

        self.assertTrue(
            (disp_dt >= req_dt).all(),
            "Dispatch timestamp preceded requested timestamp in delivered records"
        )
        self.assertTrue(
            (deliv_dt >= disp_dt).all(),
            "Delivery timestamp preceded dispatch timestamp in delivered records"
        )

    def test_delivered_quantities(self):
        """Ensure Stock-Out orders deliver 0 units, and fulfilled orders deliver requested units."""
        stockouts = self.df_fact[self.df_fact["order_status"] == "Stock-Out"]
        self.assertTrue(
            (stockouts["units_delivered"] == 0).all(),
            "Stock-Out records must have units_delivered == 0"
        )

        delivered = self.df_fact[self.df_fact["order_status"].isin(["Fulfilled", "Delayed"])]
        self.assertTrue(
            (delivered["units_delivered"] == delivered["units_requested"]).all(),
            "Delivered records must have units_delivered == units_requested"
        )


class TestMetricsEngineCalculations(unittest.TestCase):
    """Test suite verifying metric formulas, deadlines, filters, and edge cases."""

    @classmethod
    def setUpClass(cls):
        cls.engine = SupplyChainMetricsEngine(data_dir="data").load_data()

    def test_deadline_calculations(self):
        """Ensure on-time flag strictly evaluates lead_time_hours <= target_delivery_hours across all modes."""
        df = self.engine.df_master

        # For delivered shipments with valid lead times, is_on_time must strictly match the SLA target
        delivered = df[df["is_delivered"]]
        expected_on_time = (delivered["lead_time_hours"] <= delivered["target_delivery_hours"])

        self.assertTrue(
            (delivered["is_on_time"] == expected_on_time).all(),
            "is_on_time flag does not strictly match lead_time_hours <= target_delivery_hours"
        )

        # Check Road specifically: road shipments exceeding target must NOT be marked on-time
        road_overdue = delivered[(delivered["transport_mode"] == "Road") & (delivered["lead_time_hours"] > delivered["target_delivery_hours"])]
        self.assertFalse(
            road_overdue["is_on_time"].any(),
            "Road shipments exceeding the product deadline were incorrectly marked on-time"
        )

    def test_cold_chain_denominator(self):
        """Ensure cold-chain integrity is computed ONLY over delivered cold-chain shipments."""
        kpis = self.engine.compute_executive_kpis(self.engine.df_master)

        delivered_cold = self.engine.df_master[
            self.engine.df_master["is_delivered"] & (self.engine.df_master["storage_requirement"] == "Cold Chain")
        ]
        expected_integrity = round(
            (1.0 - (delivered_cold["cold_chain_breach"].sum() / len(delivered_cold))) * 100.0,
            2
        )
        self.assertEqual(
            kpis.cold_chain_integrity_pct,
            expected_integrity,
            "Cold chain integrity was not calculated strictly over delivered cold-chain items"
        )

        # Edge case: No cold-chain items
        ambient_only = self.engine.filter_data(product_categories=["Antivenom"])
        kpis_amb = self.engine.compute_executive_kpis(ambient_only)
        self.assertIsNone(
            kpis_amb.cold_chain_integrity_pct,
            "Cold chain integrity must be None (N/A) when zero cold chain items are delivered"
        )

    def test_hub_mapping_preservation(self):
        """Ensure clinic summary preserves nearest_hub and does not default all clinics to Omenako."""
        summary = self.engine.get_clinic_performance_summary(self.engine.df_master)
        self.assertIn("nearest_hub", summary.columns, "nearest_hub was dropped in clinic summary")

        hubs_represented = set(summary["nearest_hub"].dropna())
        self.assertGreater(
            len(hubs_represented),
            1,
            f"All clinics collapsed to a single hub. Found only: {hubs_represented}"
        )
        self.assertIn("HUB-MPN", hubs_represented, "HUB-MPN (Ashanti) missing from clinic assignments")
        self.assertIn("HUB-KUK", hubs_represented, "HUB-KUK (Northern) missing from clinic assignments")

        # PyDeck builder flags unmapped hubs rather than silently choosing a fallback
        broken_summary = summary.copy()
        broken_summary.loc[0, "nearest_hub"] = "INVALID_HUB"
        deck, unmapped = build_pydeck_logistics_map(broken_summary, self.engine.df_hubs)
        self.assertIn(
            broken_summary.loc[0, "clinic_name"],
            unmapped,
            "Unmapped hub relationship was not flagged explicitly"
        )

    def test_distances_above_300km_retained(self):
        """Ensure shipments with distance > 300 km are assigned to the open-ended bracket '150+ km' and not NaN."""
        df = self.engine.df_master
        long_distance_shipments = df[df["distance_km"] > 300.0]
        self.assertGreater(len(long_distance_shipments), 0, "No shipments > 300 km found in test dataset")

        self.assertFalse(
            long_distance_shipments["distance_band"].isna().any(),
            "Shipments > 300 km received NaN distance_band"
        )
        self.assertTrue(
            (long_distance_shipments["distance_band"] == "150+ km").all(),
            "Shipments > 300 km were not placed in '150+ km' bracket"
        )

    def test_empty_filters(self):
        """Ensure explicitly empty filter selections ([]) return 0 records rather than resetting to all."""
        # Deselecting all regions
        df_empty_reg = self.engine.filter_data(regions=[])
        self.assertEqual(len(df_empty_reg), 0, "regions=[] did not return 0 records")

        # Deselecting all transport modes
        df_empty_mode = self.engine.filter_data(transport_modes=[])
        self.assertEqual(len(df_empty_mode), 0, "transport_modes=[] did not return 0 records")

        # Calling KPIs on 0 records returns clean N/A (None) representation
        kpis_empty = self.engine.compute_executive_kpis(df_empty_reg)
        self.assertEqual(kpis_empty.total_requests, 0)
        self.assertIsNone(kpis_empty.standard_otif_rate_pct)
        self.assertIsNone(kpis_empty.avg_lead_time_hours)
        self.assertIsNone(kpis_empty.drone_road_delta_hours)

    def test_single_mode_comparisons(self):
        """Ensure single-mode filtering safely sets drone_road_delta_hours to None rather than crashing."""
        drone_only = self.engine.filter_data(transport_modes=["Drone"])
        kpis_drone = self.engine.compute_executive_kpis(drone_only)
        self.assertIsNotNone(kpis_drone.drone_avg_lead_time_hours)
        self.assertIsNone(kpis_drone.road_avg_lead_time_hours)
        self.assertIsNone(kpis_drone.drone_road_delta_hours, "Delta must be None when only Drone deliveries exist")

        road_only = self.engine.filter_data(transport_modes=["Road"])
        kpis_road = self.engine.compute_executive_kpis(road_only)
        self.assertIsNone(kpis_road.drone_avg_lead_time_hours)
        self.assertIsNotNone(kpis_road.road_avg_lead_time_hours)
        self.assertIsNone(kpis_road.drone_road_delta_hours, "Delta must be None when only Road deliveries exist")

    def test_punctuation_and_regex_searches(self):
        """Ensure search queries containing regex characters (e.g., '[', '*', '(', '?') execute safely without crashing."""
        df = self.engine.df_master
        search_terms = ["[", "*", "(", ")", "+", "?", "\\", "^", "$"]

        for query in search_terms:
            try:
                res = filter_shipment_ledger(df, search_query=query)
                self.assertIsInstance(len(res), int)
            except Exception as e:
                self.fail(f"Search failed on punctuation query '{query}': {e}")


class TestRuntimeDataValidation(unittest.TestCase):
    """Test suite verifying that runtime validation detects and rejects corrupt datasets."""

    @classmethod
    def setUpClass(cls):
        cls.data_dir = "data"
        cls.df_fact = pd.read_csv(f"{cls.data_dir}/fact_shipments.csv")
        cls.df_clinics = pd.read_csv(f"{cls.data_dir}/dim_clinics.csv")
        cls.df_products = pd.read_csv(f"{cls.data_dir}/dim_products.csv")
        cls.df_hubs = pd.read_csv(f"{cls.data_dir}/dim_hubs.csv")

    def test_missing_required_column_raises_error(self):
        """Ensure dropping a required column from fact or dim table raises DataValidationError."""
        corrupt_fact = self.df_fact.drop(columns=["lead_time_hours"])
        with self.assertRaises(DataValidationError) as ctx:
            SupplyChainMetricsEngine.validate_raw_data(
                corrupt_fact, self.df_clinics, self.df_products, self.df_hubs
            )
        self.assertIn("lead_time_hours", str(ctx.exception))

    def test_duplicate_primary_key_raises_error(self):
        """Ensure duplicate primary keys in dimension tables raise DataValidationError."""
        corrupt_clinics = pd.concat([self.df_clinics, self.df_clinics.iloc[[0]]], ignore_index=True)
        with self.assertRaises(DataValidationError) as ctx:
            SupplyChainMetricsEngine.validate_raw_data(
                self.df_fact, corrupt_clinics, self.df_products, self.df_hubs
            )
        self.assertIn("duplicate primary key", str(ctx.exception).lower())

    def test_null_primary_key_raises_error(self):
        """Ensure null primary keys in fact table raise DataValidationError."""
        corrupt_fact = self.df_fact.copy()
        corrupt_fact.loc[0, "request_id"] = np.nan
        with self.assertRaises(DataValidationError) as ctx:
            SupplyChainMetricsEngine.validate_raw_data(
                corrupt_fact, self.df_clinics, self.df_products, self.df_hubs
            )
        self.assertIn("null primary key", str(ctx.exception).lower())

    def test_invalid_foreign_key_raises_error(self):
        """Ensure unmapped foreign keys in fact table raise DataValidationError."""
        corrupt_fact = self.df_fact.copy()
        corrupt_fact.loc[0, "clinic_id"] = "CLN-NONEXISTENT"
        with self.assertRaises(DataValidationError) as ctx:
            SupplyChainMetricsEngine.validate_raw_data(
                corrupt_fact, self.df_clinics, self.df_products, self.df_hubs
            )
        self.assertIn("invalid foreign key", str(ctx.exception).lower())

    def test_invalid_timestamp_order_raises_error(self):
        """Ensure dispatch preceding request raises DataValidationError."""
        corrupt_fact = self.df_fact.copy()
        fulfilled_idx = corrupt_fact[corrupt_fact["order_status"] == "Fulfilled"].index[0]
        corrupt_fact.loc[fulfilled_idx, "dispatch_timestamp"] = "2023-01-01 00:00:00"
        corrupt_fact.loc[fulfilled_idx, "requested_timestamp"] = "2023-01-02 00:00:00"
        with self.assertRaises(DataValidationError) as ctx:
            SupplyChainMetricsEngine.validate_raw_data(
                corrupt_fact, self.df_clinics, self.df_products, self.df_hubs
            )
        self.assertIn("dispatch_timestamp < requested_timestamp", str(ctx.exception))

    def test_inconsistent_quantities_raises_error(self):
        """Ensure stock-out with positive delivered units raises DataValidationError."""
        corrupt_fact = self.df_fact.copy()
        stockout_idx = corrupt_fact[corrupt_fact["order_status"] == "Stock-Out"].index[0]
        corrupt_fact.loc[stockout_idx, "units_delivered"] = 15
        with self.assertRaises(DataValidationError) as ctx:
            SupplyChainMetricsEngine.validate_raw_data(
                corrupt_fact, self.df_clinics, self.df_products, self.df_hubs
            )
        self.assertIn("stock-out shipments have units_delivered != 0", str(ctx.exception).lower())


class TestUnknownColdChainHandling(unittest.TestCase):
    """Test suite verifying missing cold-chain records are handled as unknown rather than quality passes."""

    def test_missing_cold_chain_breach_treated_as_unknown(self):
        """Ensure null cold_chain_breach evaluates to is_quality_pass=False and quality_known=False via load_data()."""
        df_fact = pd.read_csv("data/fact_shipments.csv")
        df_clinics = pd.read_csv("data/dim_clinics.csv")
        df_products = pd.read_csv("data/dim_products.csv")
        df_hubs = pd.read_csv("data/dim_hubs.csv")

        # Identify delivered cold-chain records
        cold_prod_ids = set(df_products[df_products["storage_requirement"] == "Cold Chain"]["product_id"])
        delivered_cold_mask = (df_fact["order_status"].isin(["Fulfilled", "Delayed"])) & (
            df_fact["product_id"].isin(cold_prod_ids)
        )
        self.assertTrue(delivered_cold_mask.any())

        corrupt_fact = df_fact.copy()
        corrupt_fact["cold_chain_breach"] = corrupt_fact["cold_chain_breach"].astype(object)
        target_indices = corrupt_fact[delivered_cold_mask].index[:10]
        corrupt_fact.loc[target_indices, "cold_chain_breach"] = np.nan

        with tempfile.TemporaryDirectory() as temp_dir:
            corrupt_fact.to_csv(os.path.join(temp_dir, "fact_shipments.csv"), index=False)
            df_clinics.to_csv(os.path.join(temp_dir, "dim_clinics.csv"), index=False)
            df_products.to_csv(os.path.join(temp_dir, "dim_products.csv"), index=False)
            df_hubs.to_csv(os.path.join(temp_dir, "dim_hubs.csv"), index=False)

            # Let the metrics engine derive features end-to-end without duplicated test logic
            engine = SupplyChainMetricsEngine(data_dir=temp_dir).load_data()
            df = engine.df_master

            target_req_ids = corrupt_fact.loc[target_indices, "request_id"].tolist()
            target_rows = df[df["request_id"].isin(target_req_ids)]

            self.assertFalse(target_rows["is_quality_pass"].any(), "NaN cold chain breach was treated as quality pass!")
            self.assertFalse(target_rows["quality_known"].any(), "NaN cold chain breach was treated as known quality!")
            self.assertFalse(target_rows["is_quality_otif"].any(), "NaN cold chain breach was treated as quality OTIF!")

            # Check KPI computation
            kpis = engine.compute_executive_kpis(df)
            self.assertEqual(kpis.unknown_quality_cold_orders, 10, "KPI did not report 10 unknown quality cold orders")

            # Check regional bottlenecks computation executes without error and tracks unknown counts
            reg_df = engine.get_regional_bottlenecks(df)
            self.assertGreater(len(reg_df), 0)
            self.assertIn("unknown_quality_cold_count", reg_df.columns)
            self.assertEqual(reg_df["unknown_quality_cold_count"].sum(), 10)


class TestTemporaryCSVValidation(unittest.TestCase):
    """Test suite calling load_data() on temporary CSV directories to verify end-to-end dataset validation."""

    @classmethod
    def setUpClass(cls):
        cls.df_fact = pd.read_csv("data/fact_shipments.csv")
        cls.df_clinics = pd.read_csv("data/dim_clinics.csv")
        cls.df_products = pd.read_csv("data/dim_products.csv")
        cls.df_hubs = pd.read_csv("data/dim_hubs.csv")

    def _write_temp_bundle(self, temp_dir, fact=None, clinics=None, products=None, hubs=None):
        (fact if fact is not None else self.df_fact).to_csv(os.path.join(temp_dir, "fact_shipments.csv"), index=False)
        (clinics if clinics is not None else self.df_clinics).to_csv(os.path.join(temp_dir, "dim_clinics.csv"), index=False)
        (products if products is not None else self.df_products).to_csv(os.path.join(temp_dir, "dim_products.csv"), index=False)
        (hubs if hubs is not None else self.df_hubs).to_csv(os.path.join(temp_dir, "dim_hubs.csv"), index=False)

    def test_load_data_invalid_timestamp_raises_error(self):
        """Calling load_data() with inverted timestamps raises DataValidationError."""
        corrupt_fact = self.df_fact.copy()
        fulfilled_idx = corrupt_fact[corrupt_fact["order_status"] == "Fulfilled"].index[0]
        corrupt_fact.loc[fulfilled_idx, "dispatch_timestamp"] = "2025-06-01 12:00:00"
        corrupt_fact.loc[fulfilled_idx, "requested_timestamp"] = "2025-06-02 12:00:00"

        with tempfile.TemporaryDirectory() as temp_dir:
            self._write_temp_bundle(temp_dir, fact=corrupt_fact)
            engine = SupplyChainMetricsEngine(data_dir=temp_dir)
            with self.assertRaises(DataValidationError) as ctx:
                engine.load_data()
            self.assertIn("dispatch_timestamp < requested_timestamp", str(ctx.exception))

    def test_load_data_missing_timestamp_raises_error(self):
        """Calling load_data() with null requested_timestamp raises DataValidationError."""
        corrupt_fact = self.df_fact.copy()
        corrupt_fact.loc[0, "requested_timestamp"] = np.nan

        with tempfile.TemporaryDirectory() as temp_dir:
            self._write_temp_bundle(temp_dir, fact=corrupt_fact)
            engine = SupplyChainMetricsEngine(data_dir=temp_dir)
            with self.assertRaises(DataValidationError) as ctx:
                engine.load_data()
            self.assertIn("missing requested_timestamp", str(ctx.exception).lower())

    def test_load_data_excessive_quantities_raises_error(self):
        """Calling load_data() with units_delivered > units_requested raises DataValidationError."""
        corrupt_fact = self.df_fact.copy()
        fulfilled_idx = corrupt_fact[corrupt_fact["order_status"] == "Fulfilled"].index[0]
        corrupt_fact.loc[fulfilled_idx, "units_delivered"] = corrupt_fact.loc[fulfilled_idx, "units_requested"] + 25

        with tempfile.TemporaryDirectory() as temp_dir:
            self._write_temp_bundle(temp_dir, fact=corrupt_fact)
            engine = SupplyChainMetricsEngine(data_dir=temp_dir)
            with self.assertRaises(DataValidationError) as ctx:
                engine.load_data()
            self.assertIn("overdelivery", str(ctx.exception).lower())

    def test_load_data_missing_required_columns_raises_error(self):
        """Calling load_data() with missing required dimension column raises DataValidationError."""
        corrupt_products = self.df_products.drop(columns=["storage_requirement"])

        with tempfile.TemporaryDirectory() as temp_dir:
            self._write_temp_bundle(temp_dir, products=corrupt_products)
            engine = SupplyChainMetricsEngine(data_dir=temp_dir)
            with self.assertRaises(DataValidationError) as ctx:
                engine.load_data()
            self.assertIn("missing required columns", str(ctx.exception).lower())


class TestShipmentLedgerSearch(unittest.TestCase):
    """Test suite verifying filter_shipment_ledger behavior."""

    @classmethod
    def setUpClass(cls):
        cls.engine = SupplyChainMetricsEngine(data_dir="data").load_data()

    def test_filter_by_status(self):
        """Ensure filtering by status returns only records of that status."""
        df_fulfilled = filter_shipment_ledger(self.engine.df_master, status_filter="Fulfilled")
        self.assertTrue((df_fulfilled["order_status"] == "Fulfilled").all())

        df_delayed = filter_shipment_ledger(self.engine.df_master, status_filter="Delayed")
        self.assertTrue((df_delayed["order_status"] == "Delayed").all())

        df_stockout = filter_shipment_ledger(self.engine.df_master, status_filter="Stock-Out")
        self.assertTrue((df_stockout["order_status"] == "Stock-Out").all())

    def test_literal_search_brackets_and_wildcards(self):
        """Ensure bracket and wildcard characters don't cause regex parse crashes."""
        for char in ["[", "]", "*", "+", "?", "^", "$", "(", ")"]:
            res = filter_shipment_ledger(self.engine.df_master, search_query=char)
            self.assertIsInstance(len(res), int)

    def test_case_insensitive_matching(self):
        """Ensure searching 'kumasi' or 'KUMASI' matches case-insensitively."""
        res_lower = filter_shipment_ledger(self.engine.df_master, search_query="omenako")
        res_upper = filter_shipment_ledger(self.engine.df_master, search_query="OMENAKO")
        self.assertEqual(len(res_lower), len(res_upper))
        self.assertGreater(len(res_lower), 0)

    def test_ui_status_labels_exact_counts(self):
        """Assert exact expected counts for UI status filter labels on the supplied dataset."""
        df_ontime = filter_shipment_ledger(self.engine.df_master, status_filter="Delivered (On-Time)")
        self.assertEqual(len(df_ontime), 8653, "Expected exactly 8,653 Delivered (On-Time) records")

        df_delayed = filter_shipment_ledger(self.engine.df_master, status_filter="Delivered (Delayed)")
        self.assertEqual(len(df_delayed), 3246, "Expected exactly 3,246 Delivered (Delayed) records")

        df_stockout = filter_shipment_ledger(self.engine.df_master, status_filter="Stock-Out")
        self.assertEqual(len(df_stockout), 601, "Expected exactly 601 Stock-Out records")

        # Partition exhaustiveness check: 8,653 + 3,246 + 601 == 12,500
        self.assertEqual(len(df_ontime) + len(df_delayed) + len(df_stockout), len(self.engine.df_master))


if __name__ == "__main__":
    unittest.main()

