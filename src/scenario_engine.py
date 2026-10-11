"""Deterministic What-If Scenario Engine for Rural Healthcare Logistics.

Simulates the operational impact of dispatch preparation adjustments and severe weather
transit delays across autonomous aerial drones and rural ground vehicle fleets.

Guarantees:
- Never mutates the source DataFrame or cached engine data.
- Preserves stored baseline lead times so default controls reproduce baseline metrics exactly.
- Enforces non-negative preparation times (max of zero).
- Applies weather delay exactly once per eligible delivery only when both category and mode match.
- Evaluates on-time criteria strictly against unchanged product deadlines (<= deadline is on-time).
- Preserves stock-out outcomes, requested/delivered quantities, and quality audit observations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ScenarioParameters:
    """Operational adjustment parameters for what-if scenario modeling.

    Attributes:
        drone_prep_adj_minutes: Adjustment to drone dispatch preparation time (-30 to +120 mins).
        road_prep_adj_minutes: Adjustment to ground fleet preparation time (-60 to +240 mins).
        weather_delay_minutes: Additional transit delay under specified weather (0 to 180 mins).
        weather_categories: Weather classifications subject to additional delay.
        weather_modes: Modalities affected by the weather delay ("Drone", "Road", or both).
    """
    drone_prep_adj_minutes: float = 0.0
    road_prep_adj_minutes: float = 0.0
    weather_delay_minutes: float = 0.0
    weather_categories: Tuple[str, ...] = ("Heavy Rain", "Severe Storm/Flood")
    weather_modes: Tuple[str, ...] = ("Drone", "Road")


@dataclass
class ScenarioMetricRow:
    """Structured metric comparison between baseline and scenario cohorts."""
    metric_name: str
    baseline_value: Optional[float]
    scenario_value: Optional[float]
    change_value: Optional[float]
    unit: str
    denominator_explanation: str
    is_percentage_point: bool = False


@dataclass
class ScenarioSummary:
    """Comprehensive analytical summary of scenario outcomes."""
    total_requests: int
    delivered_requests: int
    stockout_requests: int
    metric_rows: List[ScenarioMetricRow]
    status_changed_count: int
    mode_comparison: pd.DataFrame
    regional_comparison: pd.DataFrame

    def to_dict(self) -> Dict[str, Any]:
        """Serialize summary metrics to dictionary format for JSON export."""
        return {
            "total_requests": self.total_requests,
            "delivered_requests": self.delivered_requests,
            "stockout_requests": self.stockout_requests,
            "status_changed_count": self.status_changed_count,
            "metrics": [
                {
                    "metric": r.metric_name,
                    "baseline": round(r.baseline_value, 2) if r.baseline_value is not None else None,
                    "scenario": round(r.scenario_value, 2) if r.scenario_value is not None else None,
                    "change": round(r.change_value, 2) if r.change_value is not None else None,
                    "unit": r.unit,
                    "is_percentage_point": r.is_percentage_point,
                    "denominator": r.denominator_explanation,
                }
                for r in self.metric_rows
            ],
            "mode_comparison": self.mode_comparison.to_dict(orient="records") if len(self.mode_comparison) > 0 else [],
            "regional_comparison": self.regional_comparison.to_dict(orient="records") if len(self.regional_comparison) > 0 else [],
        }


@dataclass
class ScenarioResult:
    """Complete output package containing adjusted data and summary metrics."""
    parameters: ScenarioParameters
    df: pd.DataFrame
    summary: ScenarioSummary


def simulate_scenario(
    df: pd.DataFrame,
    params: Optional[ScenarioParameters] = None,
) -> ScenarioResult:
    """Execute deterministic what-if timing adjustments on a filtered shipment ledger.

    Args:
        df: Input DataFrame containing baseline shipment records.
        params: Configurable scenario parameters. If None, default (zero-adjustment) controls apply.

    Returns:
        ScenarioResult containing an augmented copy of the DataFrame and comparative summaries.
    """
    if params is None:
        params = ScenarioParameters()

    # 1. Guarantee source immutability by working on an isolated copy
    df_scenario = df.copy()

    total_requests = len(df_scenario)
    if total_requests == 0:
        empty_summary = ScenarioSummary(
            total_requests=0,
            delivered_requests=0,
            stockout_requests=0,
            metric_rows=[],
            status_changed_count=0,
            mode_comparison=pd.DataFrame(),
            regional_comparison=pd.DataFrame(),
        )
        return ScenarioResult(parameters=params, df=df_scenario, summary=empty_summary)

    # 2. Ensure delivery flags and baseline identifiers exist
    if "is_delivered" not in df_scenario.columns:
        df_scenario["is_delivered"] = (
            df_scenario["delivery_timestamp"].notna()
            & (df_scenario["units_delivered"] > 0)
            & (df_scenario["order_status"] != "Stock-Out")
        )

    if "is_in_full" not in df_scenario.columns:
        df_scenario["is_in_full"] = (
            df_scenario["is_delivered"]
            & (df_scenario["units_delivered"] == df_scenario["units_requested"])
            & (df_scenario["units_requested"] > 0)
        )

    if "is_quality_pass" not in df_scenario.columns:
        is_cold = df_scenario["storage_requirement"] == "Cold Chain"
        df_scenario["is_quality_pass"] = False
        df_scenario.loc[is_cold & (df_scenario["cold_chain_breach"] == False), "is_quality_pass"] = True
        df_scenario.loc[~is_cold, "is_quality_pass"] = True

    # 3. Compute baseline preparation times for delivered shipments
    delivered_mask = df_scenario["is_delivered"] & df_scenario["dispatch_timestamp"].notna() & df_scenario["requested_timestamp"].notna()

    req_dt = pd.to_datetime(df_scenario["requested_timestamp"])
    disp_dt = pd.to_datetime(df_scenario["dispatch_timestamp"])

    baseline_prep_minutes = pd.Series(np.nan, index=df_scenario.index, dtype=float)
    baseline_prep_minutes.loc[delivered_mask] = (
        disp_dt.loc[delivered_mask] - req_dt.loc[delivered_mask]
    ).dt.total_seconds() / 60.0

    # 4. Mode-specific preparation adjustment with zero floor
    mode_adj_minutes = pd.Series(0.0, index=df_scenario.index, dtype=float)
    drone_mask = delivered_mask & (df_scenario["transport_mode"] == "Drone")
    road_mask = delivered_mask & (df_scenario["transport_mode"] == "Road")

    mode_adj_minutes.loc[drone_mask] = float(params.drone_prep_adj_minutes)
    mode_adj_minutes.loc[road_mask] = float(params.road_prep_adj_minutes)

    # New preparation time = max(0, baseline preparation time + adjustment)
    new_prep_minutes = pd.Series(np.nan, index=df_scenario.index, dtype=float)
    new_prep_minutes.loc[delivered_mask] = np.maximum(
        0.0,
        baseline_prep_minutes.loc[delivered_mask] + mode_adj_minutes.loc[delivered_mask]
    )

    # Actual preparation change = new preparation time - baseline preparation time
    actual_prep_change_minutes = pd.Series(0.0, index=df_scenario.index, dtype=float)
    actual_prep_change_minutes.loc[delivered_mask] = (
        new_prep_minutes.loc[delivered_mask] - baseline_prep_minutes.loc[delivered_mask]
    )

    # 5. Applicable weather delay (applied once only when both weather and mode match)
    weather_cat_set = set(params.weather_categories)
    weather_mode_set = set(params.weather_modes)

    weather_match = df_scenario["weather_condition"].isin(weather_cat_set)
    mode_match = df_scenario["transport_mode"].isin(weather_mode_set)
    weather_eligible = delivered_mask & weather_match & mode_match

    weather_delay_applied_minutes = pd.Series(0.0, index=df_scenario.index, dtype=float)
    weather_delay_applied_minutes.loc[weather_eligible] = float(params.weather_delay_minutes)

    # 6. Compute scenario lead time: stored baseline + prep change (hrs) + weather delay (hrs)
    # Stored baseline lead_time_hours is strictly preserved when changes are zero
    scenario_lead_time_hours = pd.Series(np.nan, index=df_scenario.index, dtype=float)
    scenario_lead_time_hours.loc[delivered_mask] = (
        df_scenario.loc[delivered_mask, "lead_time_hours"]
        + (actual_prep_change_minutes.loc[delivered_mask] / 60.0)
        + (weather_delay_applied_minutes.loc[delivered_mask] / 60.0)
    )

    # Stock-outs retain missing delivery / lead times
    scenario_lead_time_hours.loc[~df_scenario["is_delivered"]] = np.nan

    # 7. Recalculate scenario fulfillment flags
    target_deadline = df_scenario["target_delivery_hours"]
    # Exact-deadline deliveries count as strictly on-time (<= target)
    scenario_is_on_time = (
        df_scenario["is_delivered"]
        & (scenario_lead_time_hours <= target_deadline)
    )
    scenario_is_delayed = (
        df_scenario["is_delivered"]
        & (scenario_lead_time_hours > target_deadline)
    )
    scenario_is_standard_otif = scenario_is_on_time & df_scenario["is_in_full"]
    # Quality compliance remains held constant; unmonitored / breached packages remain unchanged
    scenario_is_quality_otif = scenario_is_standard_otif & df_scenario["is_quality_pass"]

    # 8. Record scenario values in distinct, dedicated columns
    df_scenario["scenario_prep_change_minutes"] = actual_prep_change_minutes
    df_scenario["scenario_weather_delay_minutes"] = weather_delay_applied_minutes
    df_scenario["scenario_lead_time_hours"] = scenario_lead_time_hours
    df_scenario["scenario_is_on_time"] = scenario_is_on_time
    df_scenario["scenario_is_delayed"] = scenario_is_delayed
    df_scenario["scenario_is_standard_otif"] = scenario_is_standard_otif
    df_scenario["scenario_is_quality_otif"] = scenario_is_quality_otif

    # Display status string for ledger table
    scenario_order_status_display = pd.Series(index=df_scenario.index, dtype=object)
    scenario_order_status_display[df_scenario["order_status"] == "Stock-Out"] = "Stock-Out"
    scenario_order_status_display[scenario_is_on_time] = "Delivered (On-Time)"
    scenario_order_status_display[scenario_is_delayed] = "Delivered (Delayed)"
    df_scenario["scenario_order_status_display"] = scenario_order_status_display

    # Flag records whose on-time delivery status changed relative to baseline
    baseline_on_time = df_scenario.get("is_on_time", pd.Series(False, index=df_scenario.index))
    df_scenario["on_time_status_changed"] = (
        df_scenario["is_delivered"] & (baseline_on_time != scenario_is_on_time)
    )

    # 9. Compute comparative summary metrics
    delivered_count = int(df_scenario["is_delivered"].sum())
    stockout_count = int((df_scenario["order_status"] == "Stock-Out").sum())
    status_changed_count = int(df_scenario["on_time_status_changed"].sum())

    metric_rows: List[ScenarioMetricRow] = []

    # A. Average Lead Time (delivered requests only)
    if delivered_count > 0:
        base_avg_lt = float(df_scenario.loc[df_scenario["is_delivered"], "lead_time_hours"].mean())
        scen_avg_lt = float(scenario_lead_time_hours.loc[df_scenario["is_delivered"]].mean())
        diff_avg_lt = scen_avg_lt - base_avg_lt
    else:
        base_avg_lt, scen_avg_lt, diff_avg_lt = None, None, None

    metric_rows.append(ScenarioMetricRow(
        metric_name="Average Lead Time",
        baseline_value=base_avg_lt,
        scenario_value=scen_avg_lt,
        change_value=diff_avg_lt,
        unit="hrs",
        denominator_explanation=f"Delivered Requests (N = {delivered_count:,})",
        is_percentage_point=False,
    ))

    # B. 90th-Percentile Lead Time (delivered requests only)
    if delivered_count > 0:
        base_p90_lt = float(df_scenario.loc[df_scenario["is_delivered"], "lead_time_hours"].quantile(0.90))
        scen_p90_lt = float(scenario_lead_time_hours.loc[df_scenario["is_delivered"]].quantile(0.90))
        diff_p90_lt = scen_p90_lt - base_p90_lt
    else:
        base_p90_lt, scen_p90_lt, diff_p90_lt = None, None, None

    metric_rows.append(ScenarioMetricRow(
        metric_name="90th-Percentile Lead Time",
        baseline_value=base_p90_lt,
        scenario_value=scen_p90_lt,
        change_value=diff_p90_lt,
        unit="hrs",
        denominator_explanation=f"Delivered Requests (N = {delivered_count:,})",
        is_percentage_point=False,
    ))

    # C. On-Time Delivery Rate among delivered requests
    if delivered_count > 0:
        base_ontime_rate = (int(baseline_on_time.sum()) / delivered_count) * 100.0
        scen_ontime_rate = (int(scenario_is_on_time.sum()) / delivered_count) * 100.0
        diff_ontime_rate = scen_ontime_rate - base_ontime_rate
    else:
        base_ontime_rate, scen_ontime_rate, diff_ontime_rate = None, None, None

    metric_rows.append(ScenarioMetricRow(
        metric_name="On-Time Delivery Rate",
        baseline_value=base_ontime_rate,
        scenario_value=scen_ontime_rate,
        change_value=diff_ontime_rate,
        unit="%",
        denominator_explanation=f"Delivered Requests (N = {delivered_count:,})",
        is_percentage_point=True,
    ))

    # D. Standard OTIF Rate (all selected requests)
    if total_requests > 0:
        base_std_otif = (int(df_scenario.get("is_standard_otif", pd.Series(False)).sum()) / total_requests) * 100.0
        scen_std_otif = (int(scenario_is_standard_otif.sum()) / total_requests) * 100.0
        diff_std_otif = scen_std_otif - base_std_otif
    else:
        base_std_otif, scen_std_otif, diff_std_otif = None, None, None

    metric_rows.append(ScenarioMetricRow(
        metric_name="Standard OTIF Rate",
        baseline_value=base_std_otif,
        scenario_value=scen_std_otif,
        change_value=diff_std_otif,
        unit="%",
        denominator_explanation=f"All Selected Requests (N = {total_requests:,})",
        is_percentage_point=True,
    ))

    # E. Quality-Adjusted OTIF (OTIF-Q) (all selected requests)
    if total_requests > 0:
        base_q_otif = (int(df_scenario.get("is_quality_otif", pd.Series(False)).sum()) / total_requests) * 100.0
        scen_q_otif = (int(scenario_is_quality_otif.sum()) / total_requests) * 100.0
        diff_q_otif = scen_q_otif - base_q_otif
    else:
        base_q_otif, scen_q_otif, diff_q_otif = None, None, None

    metric_rows.append(ScenarioMetricRow(
        metric_name="Quality-Adjusted OTIF (OTIF-Q)",
        baseline_value=base_q_otif,
        scenario_value=scen_q_otif,
        change_value=diff_q_otif,
        unit="%",
        denominator_explanation=f"All Selected Requests (N = {total_requests:,})",
        is_percentage_point=True,
    ))

    # F. Number of Late Delivered Requests
    base_late = int(df_scenario.get("is_delayed", pd.Series(False)).sum())
    scen_late = int(scenario_is_delayed.sum())
    diff_late = scen_late - base_late

    metric_rows.append(ScenarioMetricRow(
        metric_name="Late Delivered Requests",
        baseline_value=float(base_late),
        scenario_value=float(scen_late),
        change_value=float(diff_late),
        unit="orders",
        denominator_explanation=f"Delivered Requests (N = {delivered_count:,})",
        is_percentage_point=False,
    ))

    # 10. Mode-specific lead-time comparison
    delivered_df = df_scenario[df_scenario["is_delivered"]]
    mode_records = []
    if len(delivered_df) > 0 and "transport_mode" in delivered_df.columns:
        for mode, grp in delivered_df.groupby("transport_mode", observed=True):
            b_mean = float(grp["lead_time_hours"].mean()) if len(grp) > 0 else np.nan
            s_mean = float(grp["scenario_lead_time_hours"].mean()) if len(grp) > 0 else np.nan
            b_ontime = (int(grp["is_on_time"].sum()) / len(grp)) * 100.0 if len(grp) > 0 else np.nan
            s_ontime = (int(grp["scenario_is_on_time"].sum()) / len(grp)) * 100.0 if len(grp) > 0 else np.nan
            mode_records.append({
                "transport_mode": mode,
                "delivered_shipments": len(grp),
                "baseline_avg_lead_time_hours": round(b_mean, 2),
                "scenario_avg_lead_time_hours": round(s_mean, 2),
                "lead_time_change_hours": round(s_mean - b_mean, 2),
                "baseline_on_time_rate_pct": round(b_ontime, 2),
                "scenario_on_time_rate_pct": round(s_ontime, 2),
                "on_time_rate_change_pp": round(s_ontime - b_ontime, 2),
            })
    mode_comparison_df = pd.DataFrame(mode_records)

    # 11. Regional OTIF comparison
    regional_records = []
    if "region" in df_scenario.columns and len(df_scenario) > 0:
        for region, grp in df_scenario.groupby("region", observed=True):
            r_total = len(grp)
            b_std = (int(grp["is_standard_otif"].sum()) / r_total) * 100.0 if r_total > 0 else 0.0
            s_std = (int(grp["scenario_is_standard_otif"].sum()) / r_total) * 100.0 if r_total > 0 else 0.0
            b_q = (int(grp["is_quality_otif"].sum()) / r_total) * 100.0 if r_total > 0 else 0.0
            s_q = (int(grp["scenario_is_quality_otif"].sum()) / r_total) * 100.0 if r_total > 0 else 0.0

            deliv_grp = grp[grp["is_delivered"]]
            b_lt = float(deliv_grp["lead_time_hours"].mean()) if len(deliv_grp) > 0 else np.nan
            s_lt = float(deliv_grp["scenario_lead_time_hours"].mean()) if len(deliv_grp) > 0 else np.nan

            regional_records.append({
                "region": region,
                "total_orders": r_total,
                "delivered_orders": len(deliv_grp),
                "baseline_standard_otif_pct": round(b_std, 2),
                "scenario_standard_otif_pct": round(s_std, 2),
                "standard_otif_change_pp": round(s_std - b_std, 2),
                "baseline_quality_otif_pct": round(b_q, 2),
                "scenario_quality_otif_pct": round(s_q, 2),
                "quality_otif_change_pp": round(s_q - b_q, 2),
                "baseline_avg_lead_time_hours": round(b_lt, 2) if pd.notna(b_lt) else None,
                "scenario_avg_lead_time_hours": round(s_lt, 2) if pd.notna(s_lt) else None,
            })
    regional_comparison_df = pd.DataFrame(regional_records)

    summary = ScenarioSummary(
        total_requests=total_requests,
        delivered_requests=delivered_count,
        stockout_requests=stockout_count,
        metric_rows=metric_rows,
        status_changed_count=status_changed_count,
        mode_comparison=mode_comparison_df,
        regional_comparison=regional_comparison_df,
    )

    return ScenarioResult(
        parameters=params,
        df=df_scenario,
        summary=summary,
    )
