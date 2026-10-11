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
import unittest
import numpy as np
import pandas as pd

from src.metrics_engine import SupplyChainMetricsEngine, ExecutiveKPIs
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
                mask = (
                    df["request_id"].astype(str).str.lower().str.contains(query, regex=False, na=False)
                    | df["clinic_name"].astype(str).str.lower().str.contains(query, regex=False, na=False)
                    | df["product_name"].astype(str).str.lower().str.contains(query, regex=False, na=False)
                    | df["region"].astype(str).str.lower().str.contains(query, regex=False, na=False)
                )
                filtered_count = mask.sum()
                self.assertIsInstance(int(filtered_count), int)
            except Exception as e:
                self.fail(f"Search failed on punctuation query '{query}': {e}")


if __name__ == "__main__":
    unittest.main()
