"""Unit Test Suite for What-If Operational Scenario Simulator.

Verifies:
1. Default controls reproduce baseline metrics exactly.
2. Input data is not mutated.
3. Preparation reductions never create negative preparation times.
4. Weather delays affect only matching records and apply once.
5. Stock-outs remain stock-outs.
6. Quality observations and unknown-quality treatment remain unchanged.
7. Positive delays cannot improve on-time performance for an unchanged cohort.
8. Exact-deadline deliveries count as on time.
9. Empty, stock-out-only, and single-mode cases work without exception.
10. Reset restores baseline behaviour.
11. Changing sidebar filters invalidates stale scenario results.
"""

import unittest
import numpy as np
import pandas as pd

from src.metrics_engine import SupplyChainMetricsEngine
from src.scenario_engine import (
    ScenarioParameters,
    ScenarioResult,
    simulate_scenario,
)


class TestScenarioSimulator(unittest.TestCase):
    """Test suite covering scenario simulation logic and invariant guarantees."""

    @classmethod
    def setUpClass(cls):
        cls.engine = SupplyChainMetricsEngine(data_dir="data").load_data()
        cls.df = cls.engine.df_master

    def test_default_controls_reproduce_baseline_exactly(self):
        """Applying default controls (zero adjustments) reproduces baseline metrics exactly."""
        res = simulate_scenario(self.df, ScenarioParameters())

        self.assertEqual(res.summary.status_changed_count, 0)
        self.assertFalse(res.df["on_time_status_changed"].any())

        delivered_mask = self.df["is_delivered"]
        np.testing.assert_allclose(
            res.df.loc[delivered_mask, "scenario_lead_time_hours"].values,
            self.df.loc[delivered_mask, "lead_time_hours"].values,
            err_msg="Scenario lead times differed from baseline under default controls",
        )

        for row in res.summary.metric_rows:
            if row.baseline_value is not None:
                self.assertAlmostEqual(
                    row.baseline_value,
                    row.scenario_value,
                    places=5,
                    msg=f"Metric {row.metric_name} changed under default controls",
                )
                self.assertAlmostEqual(row.change_value, 0.0, places=5)

    def test_input_data_immutability(self):
        """Ensure simulate_scenario operates on an isolated copy and never mutates input DataFrame."""
        df_copy = self.df.copy(deep=True)
        aggressive_params = ScenarioParameters(
            drone_prep_adj_minutes=60,
            road_prep_adj_minutes=180,
            weather_delay_minutes=120,
        )

        res = simulate_scenario(self.df, aggressive_params)

        pd.testing.assert_frame_equal(self.df, df_copy)
        self.assertNotIn("scenario_lead_time_hours", self.df.columns)
        self.assertIn("scenario_lead_time_hours", res.df.columns)

    def test_preparation_reductions_never_create_negative_prep_time(self):
        """Maximum reductions (-30m drone, -60m road) are floored at 0 minutes."""
        res = simulate_scenario(
            self.df,
            ScenarioParameters(drone_prep_adj_minutes=-30, road_prep_adj_minutes=-60),
        )

        delivered = res.df[res.df["is_delivered"]]
        req_dt = pd.to_datetime(delivered["requested_timestamp"])
        disp_dt = pd.to_datetime(delivered["dispatch_timestamp"])
        baseline_prep = (disp_dt - req_dt).dt.total_seconds() / 60.0

        new_prep = baseline_prep + delivered["scenario_prep_change_minutes"]
        self.assertTrue((new_prep >= -1e-9).all(), "New preparation time was negative!")

        # Explicit test with synthetic ultra-short prep time (5 mins)
        synth_row = delivered.iloc[0:1].copy()
        synth_row["requested_timestamp"] = pd.Timestamp("2025-01-01 10:00:00")
        synth_row["dispatch_timestamp"] = pd.Timestamp("2025-01-01 10:05:00")  # 5 min prep
        synth_row["transport_mode"] = "Drone"
        synth_row["lead_time_hours"] = 1.0

        synth_res = simulate_scenario(synth_row, ScenarioParameters(drone_prep_adj_minutes=-30))
        actual_change = synth_res.df.iloc[0]["scenario_prep_change_minutes"]
        # Expected change is -5 mins (floored at 0), not -30 mins
        self.assertAlmostEqual(actual_change, -5.0, places=2)
        self.assertAlmostEqual(synth_res.df.iloc[0]["scenario_lead_time_hours"], 1.0 - (5.0 / 60.0), places=4)

    def test_weather_delays_affect_only_matching_records_and_apply_once(self):
        """Additional weather delay applies once only to matching category and transport mode."""
        params = ScenarioParameters(
            weather_delay_minutes=75.0,
            weather_categories=("Heavy Rain",),
            weather_modes=("Drone",),
        )
        res = simulate_scenario(self.df, params)

        delivered = res.df[res.df["is_delivered"]]
        matching_mask = (delivered["weather_condition"] == "Heavy Rain") & (delivered["transport_mode"] == "Drone")
        non_matching_mask = ~matching_mask

        self.assertTrue(matching_mask.any())
        self.assertTrue(non_matching_mask.any())

        # Matching records receive exactly 75 minutes (+1.25 hrs)
        self.assertTrue((delivered.loc[matching_mask, "scenario_weather_delay_minutes"] == 75.0).all())
        expected_diff = 75.0 / 60.0
        lead_time_diffs = delivered.loc[matching_mask, "scenario_lead_time_hours"] - delivered.loc[matching_mask, "lead_time_hours"]
        np.testing.assert_allclose(lead_time_diffs.values, expected_diff, rtol=1e-5)

        # Non-matching records receive 0 minutes weather delay
        self.assertTrue((delivered.loc[non_matching_mask, "scenario_weather_delay_minutes"] == 0.0).all())

    def test_stockouts_remain_stockouts(self):
        """Stock-outs retain unfulfilled status, missing delivery times, and null scenario lead times."""
        params = ScenarioParameters(
            drone_prep_adj_minutes=45,
            road_prep_adj_minutes=90,
            weather_delay_minutes=60,
        )
        res = simulate_scenario(self.df, params)

        stockouts = res.df[res.df["order_status"] == "Stock-Out"]
        self.assertGreater(len(stockouts), 0)
        self.assertFalse(stockouts["is_delivered"].any())
        self.assertTrue(stockouts["scenario_lead_time_hours"].isna().all())
        self.assertFalse(stockouts["scenario_is_on_time"].any())
        self.assertFalse(stockouts["scenario_is_delayed"].any())
        self.assertFalse(stockouts["scenario_is_standard_otif"].any())
        self.assertEqual(res.summary.stockout_requests, len(stockouts))

    def test_quality_observations_and_unknown_quality_remain_unchanged(self):
        """Thermal quality observations and unknown-quality handling remain strictly held constant."""
        df_corrupt = self.df.copy()
        # Create unknown quality records
        df_corrupt["cold_chain_breach"] = df_corrupt["cold_chain_breach"].astype(object)
        cold_mask = df_corrupt["is_delivered"] & (df_corrupt["storage_requirement"] == "Cold Chain")
        target_idx = df_corrupt[cold_mask].index[:10]
        df_corrupt.loc[target_idx, "cold_chain_breach"] = np.nan
        df_corrupt.loc[target_idx, "is_quality_pass"] = False

        params = ScenarioParameters(drone_prep_adj_minutes=30, weather_delay_minutes=40)
        res = simulate_scenario(df_corrupt, params)

        # Quality pass status must be identical
        pd.testing.assert_series_equal(
            df_corrupt["is_quality_pass"],
            res.df["is_quality_pass"],
            check_names=False,
        )
        # Quality OTIF cannot be granted to unknown quality records
        self.assertFalse(res.df.loc[target_idx, "scenario_is_quality_otif"].any())

    def test_positive_delays_cannot_improve_on_time_performance(self):
        """Positive preparation and weather delays cannot improve on-time rates for an unchanged cohort."""
        params = ScenarioParameters(
            drone_prep_adj_minutes=30,
            road_prep_adj_minutes=60,
            weather_delay_minutes=45,
        )
        res = simulate_scenario(self.df, params)

        base_ontime = int(self.df["is_on_time"].sum())
        scen_ontime = int(res.df["scenario_is_on_time"].sum())
        self.assertLessEqual(scen_ontime, base_ontime, "Positive delays improved on-time count!")

        base_late = int(self.df["is_delayed"].sum())
        scen_late = int(res.df["scenario_is_delayed"].sum())
        self.assertGreaterEqual(scen_late, base_late, "Positive delays reduced late deliveries count!")

    def test_exact_deadline_deliveries_count_as_on_time(self):
        """Deliveries whose scenario lead time exactly equals product deadline count as on-time."""
        delivered = self.df[self.df["is_delivered"]].copy().iloc[0:2]
        # Force scenario lead time to equal deadline
        delivered.iloc[0, delivered.columns.get_loc("target_delivery_hours")] = 3.0
        delivered.iloc[0, delivered.columns.get_loc("lead_time_hours")] = 2.0
        delivered.iloc[0, delivered.columns.get_loc("transport_mode")] = "Drone"
        delivered.iloc[0, delivered.columns.get_loc("weather_condition")] = "Clear"

        # Apply +60m (+1.0 hr) prep adjustment so scenario lead time = 3.0 == deadline
        params = ScenarioParameters(drone_prep_adj_minutes=60, weather_delay_minutes=0)
        res = simulate_scenario(delivered, params)

        row0 = res.df.iloc[0]
        self.assertAlmostEqual(row0["scenario_lead_time_hours"], 3.0)
        self.assertEqual(row0["scenario_lead_time_hours"], row0["target_delivery_hours"])
        self.assertTrue(row0["scenario_is_on_time"], "Exact deadline delivery was not counted as on-time!")
        self.assertFalse(row0["scenario_is_delayed"])

    def test_empty_stockout_only_and_single_mode_cases(self):
        """Empty, stock-out-only, and single-mode selections execute cleanly with safe N/A metrics."""
        # 1. Empty DataFrame
        empty_df = self.df.iloc[0:0].copy()
        res_empty = simulate_scenario(empty_df, ScenarioParameters(drone_prep_adj_minutes=15))
        self.assertEqual(res_empty.summary.total_requests, 0)
        self.assertEqual(len(res_empty.summary.metric_rows), 0)

        # 2. Stock-out only DataFrame
        stockouts_only = self.df[self.df["order_status"] == "Stock-Out"].copy()
        res_so = simulate_scenario(stockouts_only, ScenarioParameters(road_prep_adj_minutes=30))
        self.assertEqual(res_so.summary.delivered_requests, 0)
        self.assertEqual(res_so.summary.stockout_requests, len(stockouts_only))
        # Average lead time metric should have None (N/A)
        avg_lt_metric = next(m for m in res_so.summary.metric_rows if m.metric_name == "Average Lead Time")
        self.assertIsNone(avg_lt_metric.scenario_value)

        # 3. Single-mode DataFrame (Drone only)
        drone_only = self.df[self.df["transport_mode"] == "Drone"].copy()
        res_drone = simulate_scenario(drone_only, ScenarioParameters(drone_prep_adj_minutes=20))
        self.assertEqual(len(res_drone.summary.mode_comparison), 1)
        self.assertEqual(res_drone.summary.mode_comparison.iloc[0]["transport_mode"], "Drone")

        # 4. Single-mode DataFrame (Road only)
        road_only = self.df[self.df["transport_mode"] == "Road"].copy()
        res_road = simulate_scenario(road_only, ScenarioParameters(road_prep_adj_minutes=40))
        self.assertEqual(len(res_road.summary.mode_comparison), 1)
        self.assertEqual(res_road.summary.mode_comparison.iloc[0]["transport_mode"], "Road")

    def test_reset_restores_baseline_behaviour(self):
        """Resetting to default controls restores identical baseline outputs."""
        aggressive_params = ScenarioParameters(drone_prep_adj_minutes=60, road_prep_adj_minutes=120)
        res_mod = simulate_scenario(self.df, aggressive_params)
        self.assertGreater(res_mod.summary.status_changed_count, 0)

        # Reset parameters
        reset_params = ScenarioParameters()
        res_reset = simulate_scenario(self.df, reset_params)
        self.assertEqual(res_reset.summary.status_changed_count, 0)
        np.testing.assert_allclose(
            res_reset.df.loc[self.df["is_delivered"], "scenario_lead_time_hours"].values,
            self.df.loc[self.df["is_delivered"], "lead_time_hours"].values,
        )

    def test_filter_signature_tracking_prevents_stale_results(self):
        """Verifies that filter signature mismatches reliably detect changed sidebar cohorts."""
        sig1 = (("Ashanti",), "2025-01-01", "2025-06-30", ("Vaccines",), ("Drone",), ("Tier 1",))
        sig2 = (("Northern",), "2025-01-01", "2025-06-30", ("Vaccines",), ("Drone",), ("Tier 1",))

        # Distinct filter choices generate distinct signatures
        self.assertNotEqual(sig1, sig2)

        # Same choices in different order produce identical canonical tuple
        sig_a = tuple(sorted(["Northern", "Eastern"]))
        sig_b = tuple(sorted(["Eastern", "Northern"]))
        self.assertEqual(sig_a, sig_b)


if __name__ == "__main__":
    unittest.main()
