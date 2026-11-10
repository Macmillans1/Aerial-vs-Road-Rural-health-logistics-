

# Rural Healthcare Supply Chain & Drone Logistics Analytics (Ghana)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Plotly & PyDeck](https://img.shields.io/badge/Visualization-Plotly%20%7C%20PyDeck-00D2BA.svg)](https://deckgl.readthedocs.io/)
[![Architecture](https://img.shields.io/badge/Data%20Architecture-Star%20Schema-8B5CF6.svg)](#2-architectural-design--star-schema)
[![Tests](https://img.shields.io/badge/Tests-11%20Passed-10B981.svg)](#7-validation-and-regression-testing)

> **Notice:** All shipment records, clinic coordinates, route telemetry, and weather events in this project are synthetically generated for supply chain analytics and logistics simulation modeling.

An end-to-end Data Engineering and Analytics project modeling multi-modal medical supply chains in the Republic of Ghana. The system compares autonomous aerial drone deliveries against rural ground fleet logistics across diverse regional terrains, evaluating critical cold-chain medicine delivery, emergency blood product dispatches, antivenom supply, and chronic drug replenishment.

---

## 1. Problem Context & Logistics Domain
In rural healthcare distribution, seasonal monsoon flooding, washed-out infrastructure, and geographic obstacles (such as the Lake Volta riverine basin and mountainous forest enclaves) create severe supply chain bottlenecks. Delays in delivering post-partum hemorrhage medication (Oxytocin), snakebite antivenom, or cross-matched blood directly impact clinical outcomes.

Modeled on real-world autonomous medical delivery networks (such as the Ghana Health Service and Zipline logistics framework), this project evaluates **12,500 multi-modal logistics requisitions** spanning **5 central distribution hubs** and **32 rural health clinics** categorized into 3 accessibility tiers.

---

## 2. Architectural Design & Star Schema

The data warehouse follows a **Kimball Dimensional Modeling** methodology structured as a Star Schema:

```
                          ┌───────────────────────────┐
                          │       DIM_CLINICS         │
                          ├───────────────────────────┤
                          │ clinic_id (PK)            │
                          │ clinic_name               │
                          │ region                    │
                          │ latitude, longitude       │
                          │ remote_tier (Tier 1/2/3)  │
                          │ population_served         │
                          │ nearest_hub (FK)          │
                          └─────────────┬─────────────┘
                                        │ 1:N
                                        ▼
┌───────────────────────────┐     ┌─────────────────────────────────┐     ┌───────────────────────────┐
│         DIM_HUBS          │     │         FACT_SHIPMENTS          │     │       DIM_PRODUCTS        │
├───────────────────────────┤     ├─────────────────────────────────┤     ├───────────────────────────┤
│ hub_id (PK)               │ 1:N │ request_id (PK)                 │ N:1 │ product_id (PK)           │
│ hub_name                  │────►│ clinic_id (FK)                  │◄────│ product_name              │
│ region                    │     │ product_id (FK)                 │     │ category (Vaccine/Blood..)│
│ latitude, longitude       │     │ hub_id (FK)                     │     │ storage_requirement       │
│ drone_fleet_size          │     │ requested_timestamp             │     │ urgency_level             │
│ vehicle_fleet_size        │     │ dispatch_timestamp              │     │ unit_cost_usd             │
│ serviced_radius_km        │     │ delivery_timestamp              │     │ target_delivery_hours     │
└───────────────────────────┘     │ distance_km                     │     └───────────────────────────┘
                                  │ transport_mode (Drone vs. Road) │
                                  │ order_status (Fulfilled/Delayed)│
                                  │ units_requested, units_delivered│
                                  │ lead_time_hours                 │
                                  │ is_on_time, cold_chain_breach   │
                                  │ weather_condition               │
                                  └─────────────────────────────────┘
```

### Table Specifications:
- **`fact_shipments` (Fact Table)**: Transactional grain representing an individual medical requisition.
- **`dim_clinics` (Dimension Table)**: Health centers across 6 administrative regions (Ashanti, Eastern, Northern, Volta, Western, Greater Accra) mapped with geospatial coordinates, accessibility tiers, and designated distribution hubs (`nearest_hub`).
- **`dim_products` (Dimension Table)**: Medical cargo classified by thermal storage (Cold Chain $2\text{--}8^\circ\text{C}$ vs. Ambient) and clinical urgency (Emergency, Priority, Routine) with explicit target delivery deadlines (`target_delivery_hours`).
- **`dim_hubs` (Dimension Table)**: Regional distribution fulfillment centers (Omenako, Mpanya, Kukua, Sefwi Wiawso, Ankaful) maintaining drone launch nests and ground vehicle fleets.

---

## 3. Mathematical Formulations & KPI Definitions

### 1. Delivery Classification & Status Separation
Delivery success is separated from timeliness. Delayed shipments are delivered orders that exceeded the delivery SLA:
- **Delivered Orders**: $\text{Status} \in \{\text{'Fulfilled'}, \text{'Delayed'}\} \land \text{Delivery Timestamp is Valid}$
- **Stock-Out Orders**: Orders unfulfilled due to inventory shortage at the distribution hub ($\text{Units Delivered} = 0$).
- **Delivery Success Rate**:
  $$\text{Delivery Success Rate (\%)} = \frac{N_{\text{delivered}}}{N_{\text{total\_requests}}} \times 100$$

### 2. Standard OTIF vs. Quality-Adjusted OTIF (OTIF-Q)
All transport modes (Drone and Road) are evaluated against the **same product target SLA deadline** ($\text{Target Delivery Hours}$):
- **On-Time Condition**: $\text{Lead Time} \le \text{Target Delivery Hours}$
- **In-Full Condition**: $\text{Units Delivered} = \text{Units Requested} \land \text{Is Delivered}$
- **Standard OTIF Rate**:
  $$\text{Standard OTIF (\%)} = \frac{\sum \left( \mathbb{I}(\text{OnTime}) \cdot \mathbb{I}(\text{InFull}) \right)}{N_{\text{total\_requests}}} \times 100$$
- **Quality-Adjusted OTIF (OTIF-Q)**:
  $$\text{OTIF-Q (\%)} = \frac{\sum \left( \mathbb{I}(\text{OnTime}) \cdot \mathbb{I}(\text{InFull}) \cdot \mathbb{I}(\text{QualityPass}) \right)}{N_{\text{total\_requests}}} \times 100$$
  *Where $\text{QualityPass}$ requires verified thermal integrity ($\text{ColdChainBreach} = \text{False}$) for cold cargo, and defaults to True for ambient products. Requisitions with missing or unverified cold-chain telemetry evaluate to quality failure ($\text{QualityPass} = \text{False}$) to prevent unmonitored shipments from erroneously passing quality audits.*

### 3. Cold-Chain Thermal Integrity & Denominator Policy
Calculated strictly among **delivered cold-chain shipments with known, verified sensor telemetry** (excluding stock-outs where no transit took place, ambient cargo, and unverified/null telemetry records):
$$\text{Cold-Chain Breach Rate (\%)} = \frac{\sum \text{ColdBreaches}_{\text{delivered, verified}}}{N_{\text{delivered, verified cold}}} \times 100$$
$$\text{Cold-Chain Integrity (\%)} = 100\% - \text{Cold-Chain Breach Rate (\%)} = \frac{\sum \text{Passes}_{\text{delivered, verified}}}{N_{\text{delivered, verified cold}}} \times 100$$

*Denominator Policy*:
- Packages with missing or unverified cold-chain sensor status ($\text{cold\_chain\_breach is null}$) are strictly excluded from the breach rate denominator to avoid falsely assuming unmonitored cargo maintained temperature compliance.
- Unverified records are explicitly tracked and reported as `unknown_quality_cold_count`.
- If an operational cohort contains zero verified cold-chain records, verified thermal rates evaluate to `N/A` rather than `0.00%`.

### 4. Regional Bottleneck Composite Index (0–100 Scale)
Evaluated across 4 risk factors using a stable operational benchmark ($\bar{T}_{\text{benchmark}} = 12.0\text{ hours}$):
$$\text{Bottleneck Index} = 0.35 \times \text{StockOut\%} + 0.35 \times \text{Delay\%} + 20.0 \times \min\left(1.0, \frac{\bar{T}_{\text{lead}}}{12.0}\right) + 0.10 \times \text{ColdBreach\%}$$
*Note: If a region experiences 100% stock-outs (no delivered lead time), the maximum 20.0-point lead-time penalty is applied.*

---

### 5. Configurable Demonstration Risk Classification Assumptions
*The operational risk tiers modeled in the dashboard and metrics engine represent configurable demonstration and scenario analysis assumptions engineered for interactive operational drill-down across healthcare logistics models, rather than statutory clinical or regulatory mandates:*
- **Optimal Demonstration Benchmark (Standard OTIF $\ge 80\%$)**: Target performance corridor modeled after humanitarian logistics best practices where at least 4 out of 5 critical requisitions arrive strictly on-time and in-full.
- **Moderate Risk (Standard OTIF $65\% \le \text{Rate} < 80\%$)**: Represents an intermediate operational corridor with elevated lead-time volatility requiring higher safety stock buffers.
- **High Risk (Standard OTIF $< 65\%$ or Stockout Rate $> 8\%$)**: Identifies severe delivery bottlenecks and stockout vulnerabilities for targeted resource reallocation (e.g., anti-snake venom, emergency blood transfusion, and neonatal resuscitation).

---

## 4. Simulation Results & Scenario Analysis

The headline metrics generated directly via the reproducible script [`scripts/generate_simulation_table.py`](file:///d:/Rural%20Logistics/scripts/generate_simulation_table.py) calling the metrics engine:

| Metric | Total / Baseline | Autonomous Drone Fleet | Rural Ground Fleet | Modal Comparison (Drone vs. Road) |
| :--- | :---: | :---: | :---: | :---: |
| **Total Requisitions ($N$)** | **12,500** | 10,297 (82.4%) | 2,203 (17.6%) | Denominator basis |
| **Successfully Delivered** | **11,899 (95.19%)** | 9,799 (95.16%) | 2,100 (95.32%) | -0.16 percentage points |
| **Stock-Out Rate** | **601 (4.81%)** | 498 (4.84%) | 103 (4.68%) | +0.16 percentage points |
| **Standard OTIF Rate** | **69.22% (8,653 / 12,500)** | 72.04% (7,418 / 10,297) | 56.06% (1,235 / 2,203) | **+15.98 percentage points** |
| **Quality-Adjusted OTIF (OTIF-Q)** | **68.27% (8,534 / 12,500)** | 71.65% (7,378 / 10,297) | 52.47% (1,156 / 2,203) | **+19.18 percentage points** |
| **Average Simulated Lead Time** | **2.03 hours** | **1.22 hours** | **5.79 hours** | **-4.57 hours (78.9% relative difference)** |
| **Tier 3 (Deep Rural) Lead Time** | **2.75 hours** | **1.54 hours** | **12.30 hours** | **-10.76 hours (87.5% relative difference)** |
| **Cold-Chain Breach Rate** | **3.31% (253 / 7,649)** | **1.03% (63 / 6,137)** | **12.57% (190 / 1,512)** | **-11.54 percentage points** |
| **Unknown Quality Cold Cargo** | **0** | 0 | 0 | Missing/unverified telemetry |

### Stated Denominators & Methodological Notes:
1. Requisitions ($N = 12,500$) represent all logged requests over a 1-year operational window.
2. Lead times are calculated strictly over delivered orders ($N_{\text{delivered}} = 11,899$).
3. Cold-chain breach rates are calculated strictly over delivered cold-chain orders with verified quality ($N_{\text{cold\_delivered, verified}} = 7,649$). Missing quality values are treated as unknown, excluded from the breach denominator, and fail Quality OTIF.
4. Differences between percentage rates are expressed in **percentage points (pp)**. Differences in lead times represent differences in average simulated lead times across transport modes.
5. Both modalities are evaluated against identical product SLA deadlines.

### 6. What-If Scenario Simulator Methodology & Operational Scope

The dashboard integrates an interactive **What-If Scenario Simulator** ([`src/scenario_engine.py`](file:///d:/Rural%20Logistics/src/scenario_engine.py)) allowing logistics planners to evaluate the sensitivity of delivery deadlines to pre-flight drone preparations, ground vehicle staging delays, and seasonal severe weather transit friction.

#### Mathematical Adjustments:
1. **Preparation Time Adjustment**:
   $$T_{\text{new\_prep}} = \max\left(0, T_{\text{base\_prep}} + \Delta_{\text{mode}}\right)$$
   $$\Delta T_{\text{prep}} = T_{\text{new\_prep}} - T_{\text{base\_prep}}$$
   - **Drone Preparation**: $-30$ to $+120$ minutes (default $0$). Simulates automated launch nest battery swaps vs. manual pre-flight avionics checks.
   - **Road Preparation**: $-60$ to $+240$ minutes (default $0$). Simulates expedited warehouse staging vs. mechanical loading delays.
   - *Zero-Floor Invariant*: Preparation reductions never result in negative preparation durations.
2. **Severe Weather Delay**:
   - Added once to transit duration for shipments matching both the selected weather condition (`Heavy Rain`, `Severe Storm/Flood`) and transport mode (`Drone`, `Road`, or both):
   $$T_{\text{scenario}} = T_{\text{lead\_base}} + \Delta T_{\text{prep}} + \Delta T_{\text{weather}}$$
3. **Fulfillment Status Recomputation**:
   - On-time status evaluates strictly against unchanged product deadlines: $\text{Scenario On-Time} \iff T_{\text{scenario}} \le T_{\text{target\_sla}}$. Exact-deadline deliveries count as on time.
   - Standard OTIF: $\text{Scenario On-Time} \land \text{In-Full}$.
   - Quality OTIF (OTIF-Q): $\text{Scenario Standard OTIF} \land \text{QualityPass}$.

#### Stated Denominators:
- **Average Lead Time, 90th-Percentile Lead Time, and On-Time Delivery Rate**: Evaluated strictly over delivered shipments ($N_{\text{delivered}}$).
- **Standard OTIF Rate and Quality-Adjusted OTIF (OTIF-Q)**: Evaluated over all selected requisitions ($N_{\text{total}}$). Differences between rates are reported in **percentage points (pp)**.

#### Boundary Assumptions & Simulator Limitations:
- **Timing Only**: Quality observations (cold-chain breach audit status) and inventory availability (stock-out outcomes) are held constant.
- **Out of Scope**: Fleet capacity constraints (discrete vehicle counts), queuing at launch nests, payload weight feasibility, mode switching, and dynamic cold-chain breach generation or recovery are outside this simulator's scope.

### 7. Clinic & Hub Explorer Purpose, Filter Behaviour & Operational Scope

The dashboard includes a dedicated **Clinic & Hub Explorer** tab allowing supply chain managers and clinicians to drill down into individual destination health clinics and dispatch hubs.

#### Purpose & Capabilities:
- **Granular Scorecard**: Evaluates total requests, delivered orders, actual dispatches, stock-out rate, Standard OTIF, Quality-Adjusted OTIF (OTIF-Q), average and 90th-percentile delivered lead times, verified cold-chain integrity, and unknown-quality telemetry counts.
- **Network Topology Distinction**: Clearly distinguishes a clinic's administratively assigned hub (`dim_clinics.nearest_hub`) from fulfillment hubs that actually handled its requisitions in the selected period.
- **Hub Reach & Utilization Precision**: For hubs, displays the number of unique clinics represented in the active shipment cohort. Request volume share is explicitly reported as demand share and is never conflated with vehicle fleet utilization.
- **Focused Diagnostics**: Provides weekly request volume vs. OTIF trajectories, detailed product-level breakdown (requests, delivered, SLA-delayed, delay rates, stock-outs, unmet units), a granular requisition ledger with audit quality status, and filtered CSV downloads.
- **Local What-If Simulation**: Allows testing drone/road staging adjustments and weather friction directly on the selected location's requisition cohort, with prominent location labeling and local scenario CSV export (`raw_order_status`, `baseline_order_status_display`, `scenario_order_status_display`).

#### Filter Behaviour & State Lifecycle:
- **Hierarchical Intersection**: The location selection applies strictly on top of active sidebar filters (regions, dates, categories, modes, tiers).
- **Local Isolation**: Explorer selections are isolated to the Explorer tab and never silently modify the global dashboard's filter state or KPIs.
- **Safe Handling of Inactive/Empty Locations**: Configured locations with zero matching records (e.g. unlaunched hub `HUB-ANK` or clinics filtered out by date/category) display complete dimensional metadata, a clear "No requests in this selection" notice, zero counts, and `N/A` rates. The system never silently falls back to another location.
- **Automatic Invalidation**: Whenever the selected location or any sidebar filter changes, stored scenario results and downloads are immediately invalidated, ensuring planners never inspect mismatched simulation outputs.

#### Operational Limitations:
- **Simulated Grain**: The explorer analyzes historical requisition batches and simulated timing adjustments; it does not connect to live GPS telematics, active transponders, or dynamic rerouting engines.
- **Static Fleet Allocations**: Vehicle fleet sizes and serviced radii recorded in dimension tables are reference attributes and are not dynamically constrained by vehicle scheduling algorithms.

---

## 5. Repository Structure

```
d:/Rural Logistics/
├── .streamlit/
│   └── config.toml               # Streamlit theme and server configuration
├── data/
│   ├── fact_shipments.csv        # 12,500 multi-modal logistics records
│   ├── dim_clinics.csv           # 32 clinics mapped across 6 administrative regions
│   ├── dim_products.csv          # 14 medical items (antivenom, blood, vaccines, essential meds)
│   └── dim_hubs.csv              # 5 central fulfillment hubs (including inactive HUB-ANK)
├── scripts/
│   └── generate_simulation_table.py # Reproducible script generating Markdown KPI tables
├── src/
│   ├── __init__.py
│   ├── data_generator.py         # Synthetic generation pipeline with uniform SLA deadlines
│   ├── metrics_engine.py         # Star-schema joins, OTIF recomputation, runtime schema validation
│   ├── map_visualizer.py         # PyDeck 3D illustrative corridors & Plotly scatter mapping
│   └── scenario_engine.py        # What-If simulator engine with deterministic sensitivity modeling
├── tests/
│   ├── test_logistics.py         # Data validation, schema integrity & ledger tests
│   ├── test_scenario_simulator.py # Comprehensive scenario simulator test suite
│   └── test_explorer.py          # Clinic & Hub explorer, scenario export, and UI interaction tests
├── app.py                        # Streamlit dashboard entry point with Explorer & What-If tabs
├── requirements.txt              # Dependency specifications
└── README.md                     # Technical architecture documentation
```

---

## 6. Academic CV & Resume Bullet Points

*Pre-formulated for Master of Science applications in Data Science, Data Engineering, and Analytics:*

```markdown
- Architected an end-to-end healthcare logistics analytics platform modeled on Ghana's medical drone distribution network (Zipline/GHS), engineering a dimensional Star Schema joining 12,500+ transactional records across 4 relational tables in Pandas and NumPy with many-to-one validation.
- Formulated supply chain KPI algorithms in Python, demonstrating a +19.18 percentage point advantage in Quality-Adjusted OTIF for autonomous drones (71.65%) over ground vehicles (52.47%) against uniform product SLA targets, and engineered an actionable Regional Bottleneck Vulnerability Index.
- Built an interactive geospatial telemetry dashboard using Streamlit, PyDeck, and Plotly, rendering 3D illustrative supply corridors, dynamic color-tier legends, and distinguishing active dispatches from configured hub capacity across 32 clinics.
- Modeled seasonal monsoon weather disruptions and cold-chain compliance, quantitatively demonstrating that autonomous drones reduce emergency order lead time differences by 78.9% (1.2h vs. 5.8h) and deep-rural lead times by 87.5% (1.5h vs. 12.3h) compared to ground road transport.
- Implemented an automated validation test suite (21 unit tests covering schema validation, primary/foreign key integrity, timestamp ordering, unknown cold-chain handling, and regex-safe search).
```

---

## 7. Validation and Regression Testing

The repository includes a dedicated test suite verifying data integrity, runtime schemas, and analytical correctness:

```bash
python -m unittest tests/test_logistics.py -v
```
Or via pytest:
```bash
pytest tests/test_logistics.py -v
```

### Coverage:
1. `test_duplicate_primary_keys`: Uniqueness across all fact and dimension tables.
2. `test_missing_foreign_keys`: Referential integrity of `clinic_id`, `product_id`, `hub_id`, and `nearest_hub`.
3. `test_timestamp_order`: Verification that $\text{Request} \le \text{Dispatch} \le \text{Delivery}$.
4. `test_delivered_quantities`: Zero units on stock-outs, full units on delivery.
5. `test_deadline_calculations`: Uniform evaluation of SLA deadlines across transport modes.
6. `test_cold_chain_denominator`: Strict evaluation of thermal integrity over delivered cold items only.
7. `test_hub_mapping_preservation`: Verification that clinic assignments preserve valid hubs without fallback collapse.
8. `test_distances_above_300km_retained`: Inclusion of distances $> 300\text{ km}$ in open-ended brackets.
9. `test_empty_filters`: Verification that deselecting filters yields empty data rather than resetting to all records.
10. `test_single_mode_comparisons`: Safe `None` (N/A) handling when comparing single-mode subsets.
11. `test_punctuation_and_regex_searches`: Literal search execution without regex syntax errors.
12. `test_missing_required_column_raises_error`: Assertion that dropped schema columns raise `DataValidationError`.
13. `test_duplicate_primary_key_raises_error`: Assertion that duplicate dimension keys raise `DataValidationError`.
14. `test_null_primary_key_raises_error`: Assertion that null primary keys raise `DataValidationError`.
15. `test_invalid_foreign_key_raises_error`: Assertion that unmapped foreign keys raise `DataValidationError`.
16. `test_invalid_timestamp_order_raises_error`: Assertion that inverted timestamps raise `DataValidationError`.
17. `test_inconsistent_quantities_raises_error`: Assertion that positive units on stockouts raise `DataValidationError`.
18. `test_missing_cold_chain_breach_treated_as_unknown`: Assertion that null breach values evaluate to unknown quality, not quality passes.
19. `test_filter_by_status`: Strict status filtering in the shipment ledger.
20. `test_literal_search_brackets_and_wildcards`: Regex-safe literal matching on brackets and wildcards.
21. `test_case_insensitive_matching`: Consistent case-insensitive string matching.

---

## 8. How to Run Locally

### Prerequisites
- Python 3.10+
- Virtual environment (recommended)

### Installation
```bash
pip install -r requirements.txt
```

### Running the Tests
```bash
python -m unittest tests/test_logistics.py -v
```

### Generating Simulation Results Table
```bash
python scripts/generate_simulation_table.py
```

### Running the Dashboard
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 9. Assumptions and Limitations

1. **Simulation Range & Grain**: The transactional dataset spans a 1-year operational window. Each record represents a single requisition grain; multi-item bundled consignments are modeled as distinct requisitions.
2. **Vehicle & Drone Fleet Constraints**: Drone nest counts, vehicle fleet sizes, maximum payload capacities, and service radii are documented dimension attributes (`dim_hubs.csv`), but **are not yet enforced as dynamic queuing, queuing delay, or payload-splitting constraints in this data pass**.
3. **Weather Disruption Approximations**: Seasonal monsoon effects are simulated as stochastic velocity penalties and ground-stop windows rather than dynamic Doppler radar grid integrations.
4. **Data Preservation**: The supplied dataset in `data/fact_shipments.csv` is preserved. On-time flags are recomputed dynamically in `metrics_engine.py` against the single product SLA target. If regeneration is desired, running `python src/data_generator.py` will regenerate all tables using the updated uniform SLA logic.

