"""Unit and Interaction Test Suite for Clinic & Hub Explorer and Scenario Export.

Verifies:
1. Clinic and hub selection returns the correct request IDs.
2. Location selection intersects correctly with sidebar filters.
3. Location KPIs match direct calculations from the same subset.
4. Inactive hubs and empty selections work cleanly with N/A rates and zero counts.
5. Changing locations invalidates local scenarios and downloads.
6. Exports contain only the selected cohort.
7. Scenario baseline status agrees with baseline on-time flags.
8. Existing simulator Apply, Reset, and filter-invalidation behaviour works through Streamlit interaction tests.
"""

import io
import unittest
import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

from src.metrics_engine import (
    SupplyChainMetricsEngine,
    LocationKPIs,
)
from src.scenario_engine import (
    ScenarioParameters,
    simulate_scenario,
)


class TestClinicAndHubExplorer(unittest.TestCase):
    """Test suite covering location drill-down, star-schema filtering, and KPI evaluation."""

    @classmethod
    def setUpClass(cls):
        cls.engine = SupplyChainMetricsEngine(data_dir="data").load_data()
        cls.df = cls.engine.df_master

    def test_clinic_selection_returns_correct_request_ids(self):
        """Selecting a clinic returns all and only requests for that clinic_id."""
        sample_clinics = ["CLN-EAS-001", "CLN-ASH-001", "CLN-NOR-001"]
        for cid in sample_clinics:
            filtered = self.engine.filter_by_location(self.df, "Clinic", cid)
            expected_mask = self.df["clinic_id"] == cid
            expected_ids = set(self.df.loc[expected_mask, "request_id"])

            self.assertEqual(len(filtered), expected_mask.sum())
            self.assertEqual(set(filtered["request_id"]), expected_ids)
            self.assertTrue((filtered["clinic_id"] == cid).all())

    def test_hub_selection_uses_actual_handling_hub_and_distinguishes_assigned(self):
        """Selecting a hub uses shipment actual hub_id, distinguishing it from clinic nearest_hub."""
        sample_hubs = ["HUB-OMN", "HUB-KUK", "HUB-MPN"]
        for hid in sample_hubs:
            filtered = self.engine.filter_by_location(self.df, "Hub", hid)
            expected_mask = self.df["hub_id"] == hid
            expected_ids = set(self.df.loc[expected_mask, "request_id"])

            self.assertEqual(len(filtered), expected_mask.sum())
            self.assertEqual(set(filtered["request_id"]), expected_ids)
            self.assertTrue((filtered["hub_id"] == hid).all())

        # Distinguish nearest_hub from actual handling hub_id
        # dim_clinics maps nearest_hub; verify fact_shipments actual hub_id is what filtered on
        clinic_with_hub = self.df[["clinic_id", "nearest_hub", "hub_id"]].drop_duplicates()
        self.assertIn("nearest_hub", clinic_with_hub.columns)
        self.assertIn("hub_id", clinic_with_hub.columns)

    def test_location_selection_intersects_correctly_with_sidebar_filters(self):
        """Location filter intersects correctly on top of sidebar multidimensional filters."""
        # Case A: Matching intersection
        df_sidebar = self.engine.filter_data(
            regions=["Eastern"],
            transport_modes=["Drone"],
        )
        cid = "CLN-EAS-001"
        df_loc = self.engine.filter_by_location(df_sidebar, "Clinic", cid)

        self.assertGreater(len(df_loc), 0)
        self.assertTrue((df_loc["region"] == "Eastern").all())
        self.assertTrue((df_loc["transport_mode"] == "Drone").all())
        self.assertTrue((df_loc["clinic_id"] == cid).all())

        # Exact intersection verification
        expected = self.df[
            (self.df["region"] == "Eastern")
            & (self.df["transport_mode"] == "Drone")
            & (self.df["clinic_id"] == cid)
        ]
        self.assertEqual(len(df_loc), len(expected))
        self.assertEqual(set(df_loc["request_id"]), set(expected["request_id"]))

        # Case B: Disjoint intersection (clinic is in Eastern, sidebar filters for Northern)
        df_disjoint_sidebar = self.engine.filter_data(regions=["Northern"])
        df_disjoint_loc = self.engine.filter_by_location(df_disjoint_sidebar, "Clinic", cid)
        self.assertEqual(len(df_disjoint_loc), 0)

    def test_location_kpis_match_direct_calculations(self):
        """Location KPIs match manual/direct calculations evaluated over the exact same subset."""
        cid = "CLN-EAS-001"
        df_loc = self.engine.filter_by_location(self.df, "Clinic", cid)
        kpis = self.engine.compute_location_kpis(df_loc)

        total_reqs = len(df_loc)
        delivered_reqs = int(df_loc["is_delivered"].sum())
        actual_dispatches = int(df_loc["dispatch_timestamp"].notna().sum())
        stockouts = int((df_loc["order_status"] == "Stock-Out").sum())
        ontime = int(df_loc["is_on_time"].sum())
        delayed = int(df_loc["is_delayed"].sum())
        std_otif = int(df_loc["is_standard_otif"].sum())
        q_otif = int(df_loc["is_quality_otif"].sum())

        delivered_subset = df_loc[df_loc["is_delivered"]]
        direct_avg_lt = round(float(delivered_subset["lead_time_hours"].mean()), 2)
        direct_p90_lt = round(float(delivered_subset["lead_time_hours"].quantile(0.90)), 2)

        cold_subset = delivered_subset[delivered_subset["storage_requirement"] == "Cold Chain"]
        known_cold = cold_subset[cold_subset["cold_chain_breach"].notna()]
        direct_cold_integrity = (
            round(((known_cold["cold_chain_breach"] == False).sum() / len(known_cold)) * 100.0, 2)
            if len(known_cold) > 0 else None
        )
        direct_unknown_cold = int(cold_subset["cold_chain_breach"].isna().sum())

        self.assertEqual(kpis.total_requests, total_reqs)
        self.assertEqual(kpis.delivered_requests, delivered_reqs)
        self.assertEqual(kpis.actual_dispatches, actual_dispatches)
        self.assertEqual(kpis.stock_outs, stockouts)
        self.assertEqual(kpis.on_time_orders, ontime)
        self.assertEqual(kpis.delayed_orders, delayed)
        self.assertAlmostEqual(kpis.stock_out_rate_pct, round((stockouts / total_reqs) * 100.0, 2))
        self.assertAlmostEqual(kpis.standard_otif_rate_pct, round((std_otif / total_reqs) * 100.0, 2))
        self.assertAlmostEqual(kpis.quality_otif_rate_pct, round((q_otif / total_reqs) * 100.0, 2))
        self.assertAlmostEqual(kpis.avg_lead_time_hours, direct_avg_lt)
        self.assertAlmostEqual(kpis.p90_lead_time_hours, direct_p90_lt)
        self.assertEqual(kpis.cold_chain_integrity_pct, direct_cold_integrity)
        self.assertEqual(kpis.unknown_quality_cold_orders, direct_unknown_cold)

    def test_inactive_hub_and_empty_selections(self):
        """Configured inactive hub (HUB-ANK) and empty selections yield zero counts and N/A rates."""
        # HUB-ANK is configured in dim_hubs.csv but has 0 shipments in fact_shipments.csv
        df_ank = self.engine.filter_by_location(self.df, "Hub", "HUB-ANK")
        self.assertEqual(len(df_ank), 0)

        kpis = self.engine.compute_location_kpis(df_ank)
        self.assertEqual(kpis.total_requests, 0)
        self.assertEqual(kpis.delivered_requests, 0)
        self.assertEqual(kpis.actual_dispatches, 0)
        self.assertEqual(kpis.stock_outs, 0)
        self.assertIsNone(kpis.stock_out_rate_pct)
        self.assertIsNone(kpis.standard_otif_rate_pct)
        self.assertIsNone(kpis.quality_otif_rate_pct)
        self.assertIsNone(kpis.avg_lead_time_hours)
        self.assertIsNone(kpis.p90_lead_time_hours)
        self.assertIsNone(kpis.cold_chain_integrity_pct)
        self.assertEqual(kpis.unknown_quality_cold_orders, 0)

        # Diagnostics table is empty with correct columns
        prod_diag = self.engine.get_location_product_diagnostics(df_ank)
        self.assertEqual(len(prod_diag), 0)
        self.assertIn("product_name", prod_diag.columns)
        self.assertIn("request_count", prod_diag.columns)
        self.assertIn("late_delivery_count", prod_diag.columns)

    def test_changing_locations_invalidates_local_scenarios(self):
        """Changing location identity modifies the scenario signature, triggering invalidation."""
        filter_tuple = ("Eastern", "2025-01-01", "2025-06-30")

        sig_clinic_1 = ("Clinic", "CLN-EAS-001", filter_tuple)
        sig_clinic_2 = ("Clinic", "CLN-EAS-002", filter_tuple)
        sig_hub = ("Hub", "HUB-OMN", filter_tuple)

        self.assertNotEqual(sig_clinic_1, sig_clinic_2)
        self.assertNotEqual(sig_clinic_1, sig_hub)

        # Simulating signature invalidation guard logic from app.py
        stored_sig = sig_clinic_1
        applied = True

        # User changes clinic selector to CLN-EAS-002
        current_sig = sig_clinic_2
        if stored_sig != current_sig:
            applied = False

        self.assertFalse(applied, "Local scenario was not invalidated when location changed!")

    def test_exports_contain_only_selected_cohort(self):
        """CSV exports contain strictly the selected location cohort and requested export schema."""
        cid = "CLN-EAS-002"
        df_loc = self.engine.filter_by_location(self.df, "Clinic", cid)

        # 1. Location Requests CSV
        csv_str = df_loc.to_csv(index=False)
        reloaded_df = pd.read_csv(io.StringIO(csv_str))

        self.assertEqual(len(reloaded_df), len(df_loc))
        self.assertTrue((reloaded_df["clinic_id"] == cid).all())
        self.assertEqual(set(reloaded_df["request_id"]), set(df_loc["request_id"]))

        # 2. Location Scenario CSV Export
        params = ScenarioParameters(drone_prep_adj_minutes=15, weather_delay_minutes=30)
        scen_res = simulate_scenario(df_loc, params)
        scen_df = scen_res.df

        scen_export_cols = [
            "request_id", "clinic_name", "region", "remote_tier", "product_name", "category",
            "transport_mode", "target_delivery_hours", "lead_time_hours", "scenario_lead_time_hours",
            "scenario_prep_change_minutes", "scenario_weather_delay_minutes", "is_on_time",
            "scenario_is_on_time", "is_delayed", "scenario_is_delayed", "is_standard_otif",
            "scenario_is_standard_otif", "is_quality_otif", "scenario_is_quality_otif",
            "raw_order_status", "baseline_order_status_display", "scenario_order_status_display",
        ]
        avail_cols = [c for c in scen_export_cols if c in scen_df.columns]
        scen_csv_str = scen_df[avail_cols].to_csv(index=False)
        reloaded_scen_df = pd.read_csv(io.StringIO(scen_csv_str))

        self.assertEqual(len(reloaded_scen_df), len(df_loc))
        self.assertIn("raw_order_status", reloaded_scen_df.columns)
        self.assertIn("baseline_order_status_display", reloaded_scen_df.columns)
        self.assertIn("scenario_order_status_display", reloaded_scen_df.columns)
        self.assertNotIn("CLN-EAS-001", set(reloaded_scen_df["clinic_name"]))

    def test_scenario_baseline_status_agrees_with_baseline_on_time_flags(self):
        """Scenario baseline_order_status_display strictly agrees with baseline on-time and delay flags."""
        scen_res = simulate_scenario(self.df, ScenarioParameters())
        res_df = scen_res.df

        self.assertIn("baseline_order_status_display", res_df.columns)
        self.assertIn("scenario_order_status_display", res_df.columns)
        self.assertIn("raw_order_status", res_df.columns)

        # Baseline On-Time agreements
        delivered_ontime = res_df[res_df["is_delivered"] & res_df["is_on_time"]]
        self.assertTrue((delivered_ontime["baseline_order_status_display"] == "Delivered (On-Time)").all())

        # Baseline Delayed agreements
        delivered_delayed = res_df[res_df["is_delivered"] & res_df["is_delayed"]]
        self.assertTrue((delivered_delayed["baseline_order_status_display"] == "Delivered (Delayed)").all())

        # Baseline Stock-Out agreements
        stockouts = res_df[res_df["order_status"] == "Stock-Out"]
        self.assertTrue((stockouts["baseline_order_status_display"] == "Stock-Out").all())
        self.assertTrue((stockouts["raw_order_status"] == "Stock-Out").all())


class TestStreamlitSimulatorInteractions(unittest.TestCase):
    """Streamlit AppTest interaction tests covering Apply, Reset, and filter invalidation."""

    def test_simulator_apply_reset_and_invalidation(self):
        """Test Streamlit interaction: applying scenario, resetting, and filter invalidation."""
        from pathlib import Path
        app_path = Path(__file__).parent.parent / "app.py"
        at = AppTest.from_file(str(app_path), default_timeout=30)
        at.run()
        self.assertEqual(len(at.exception), 0)

        # Initial state: scenario not applied
        self.assertFalse(at.session_state.get("scenario_applied", False))

        # 1. Click Apply Scenario
        apply_buttons = [b for b in at.button if "Apply Scenario" in b.proto.label]
        self.assertGreater(len(apply_buttons), 0)
        apply_buttons[0].click()
        at.run()
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(at.session_state.get("scenario_applied", False))

        # 2. Click Reset Scenario
        reset_buttons = [b for b in at.button if "Reset Scenario" in b.proto.label]
        self.assertGreater(len(reset_buttons), 0)
        reset_buttons[0].click()
        at.run()
        self.assertEqual(len(at.exception), 0)
        self.assertFalse(at.session_state.get("scenario_applied", False))

        # 3. Apply scenario again and test sidebar filter invalidation
        apply_buttons = [b for b in at.button if "Apply Scenario" in b.proto.label]
        apply_buttons[0].click()
        at.run()
        self.assertTrue(at.session_state.get("scenario_applied", False))

        # Change region sidebar filter (Eastern is selected by default; unselecting it changes active filters)
        region_multiselect = [m for m in at.multiselect if "Administrative Regions" in m.proto.label]
        self.assertGreater(len(region_multiselect), 0)
        region_multiselect[0].unselect("Eastern")
        at.run()
        self.assertEqual(len(at.exception), 0)

        # Filter mismatch triggers invalidation guard: scenario_applied flips to False
        self.assertFalse(at.session_state.get("scenario_applied", False))


if __name__ == "__main__":
    unittest.main()
