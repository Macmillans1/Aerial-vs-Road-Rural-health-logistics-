# 🚁 Rural Healthcare Supply Chain & Drone Logistics Analytics (Ghana)

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
  $$\text{OTIF-Q (\%)} = \frac{\sum \left( \mathbb{I}(\text{OnTime}) \cdot \mathbb{I}(\text{InFull}) \cdot \mathbb{I}(\neg \text{ColdChainBreach}) \right)}{N_{\text{total\_requests}}} \times 100$$

### 3. Cold-Chain Thermal Integrity
Calculated strictly among **delivered cold-chain shipments** (excluding stock-outs where no transit took place and ambient cargo):
$$\text{Cold-Chain Integrity (\%)} = \left( 1 - \frac{\sum \text{ColdBreaches}_{\text{delivered}}}{\text{Total Delivered Cold Shipments}} \right) \times 100$$

### 4. Regional Bottleneck Composite Index (0–100 Scale)
Evaluated across 4 risk factors using a stable operational benchmark ($\bar{T}_{\text{benchmark}} = 12.0\text{ hours}$):
$$\text{Bottleneck Index} = 0.35 \times \text{StockOut\%} + 0.35 \times \text{Delay\%} + 20.0 \times \min\left(1.0, \frac{\bar{T}_{\text{lead}}}{12.0}\right) + 0.10 \times \text{ColdBreach\%}$$
*Note: If a region experiences 100% stock-outs (no delivered lead time), the maximum 20.0-point lead-time penalty is applied.*

---

## 4. Simulation Results & Scenario Analysis

The headline metrics computed directly from the 12,500 simulation records (using uniform product target deadlines across all modes):

| Metric | Total / Baseline | Autonomous Drone Fleet | Rural Ground Fleet | Modal Comparison |
| :--- | :---: | :---: | :---: | :---: |
| **Total Requisitions ($N$)** | **12,500** | 10,297 (82.4%) | 2,203 (17.6%) | — |
| **Successfully Delivered** | **11,899 (95.2%)** | 9,799 (95.2%) | 2,100 (95.3%) | Similar delivery fulfillment |
| **Stock-Out Rate** | **601 (4.81%)** | 498 (4.84%) | 103 (4.68%) | Inventory driven |
| **Standard OTIF Rate** | **69.22% (8,653 / 12,500)** | 72.04% (7,418 / 10,297) | 56.06% (1,235 / 2,203) | **+16.0% Drone SLA edge** |
| **Quality-Adjusted OTIF (OTIF-Q)** | **68.27% (8,534 / 12,500)** | 71.43% (7,355 / 10,297) | 53.52% (1,179 / 2,203) | **+17.9% Drone OTIF-Q edge** |
| **Average Order Lead Time** | **2.03 hours** | **1.22 hours** | **5.79 hours** | **4.57 hours saved per trip (78.9%)** |
| **Tier 3 (Deep Rural) Lead Time** | **2.76 hours** | **1.54 hours** | **12.30 hours** | **10.76 hours saved per trip (87.5%)** |
| **Cold-Chain Breach Rate** | **3.31% (253 / 7,649)** | **1.03% (63 / 6,137)** | **12.57% (190 / 1,512)** | **12.2x lower breach rate with drones** |

### Stated Denominators & Methodological Notes:
1. Requisitions ($N = 12,500$) represent requests over a 1-year operational window.
2. Lead times are calculated strictly over delivered orders ($N_{\text{delivered}} = 11,899$).
3. Cold-chain breach rates are calculated only over delivered cold-chain orders ($N_{\text{cold\_delivered}} = 7,649$).
4. The 2.2x deadline multiplier previously assigned to road shipments has been removed; both modalities are evaluated against identical product SLA deadlines.

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
│   └── dim_hubs.csv              # 5 central fulfillment hubs
├── src/
│   ├── __init__.py
│   ├── data_generator.py         # Synthetic generation pipeline with uniform SLA deadlines
│   ├── metrics_engine.py         # Star-schema joins, OTIF recomputation, bottleneck engine
│   └── map_visualizer.py         # PyDeck 3D illustrative corridors & Plotly scatter mapping
├── tests/
│   └── test_logistics.py         # 11 regression & validation unit tests
├── app.py                        # Streamlit dashboard entry point
├── requirements.txt              # Dependency specifications
└── README.md                     # Technical architecture documentation
```

---

## 6. Academic CV & Resume Bullet Points

*Pre-formulated for Master of Science applications in Data Science, Data Engineering, and Analytics:*

```markdown
- Architected an end-to-end healthcare logistics analytics platform modeled on Ghana's medical drone distribution network (Zipline/GHS), engineering a dimensional Star Schema joining 12,500+ transactional records across 4 relational tables in Pandas and NumPy.
- Formulated supply chain KPI algorithms in Python, including dual-track Standard OTIF and Quality-Adjusted OTIF (OTIF-Q) tracking against uniform product SLA deadlines, and a benchmarked Regional Bottleneck Vulnerability Index.
- Built an interactive geospatial telemetry dashboard using Streamlit, PyDeck, and Plotly, rendering 3D illustrative supply corridors and multi-layer risk classifications across 32 clinics and 5 regional distribution centers.
- Modeled seasonal monsoon weather disruptions and cold-chain compliance, quantitatively demonstrating that autonomous drones reduce emergency order cycle times by 78.9% (1.2h vs. 5.8h) and deep-rural lead times by 87.5% (1.5h vs. 12.3h) compared to ground road transport.
- Implemented an automated validation test suite (11 unit tests covering primary/foreign key integrity, timestamp ordering, denominator correctness, open-ended distance banding, and regex search safety).
```

---

## 7. Validation and Regression Testing

The repository includes a dedicated test suite verifying data integrity and analytical correctness:

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

### Running the Dashboard
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 9. Assumptions and Limitations

1. **Simulation Range & Grain**: The transactional dataset spans a 1-year operational window. Each record represents a single requisition grain; multi-item bundled consignments are modeled as distinct requisitions.
2. **Vehicle & Drone Fleet Capacity**: Drone nests have finite fleet sizes (18–32 drones per hub) modeled as queue prep delays during peak hours, but battery degradation over multi-year cycles is not simulated.
3. **Weather Disruption Approximations**: Seasonal monsoon effects are simulated as stochastic velocity penalties and ground-stop windows rather than dynamic Doppler radar grid integrations.
4. **Data Preservation**: The supplied dataset in `data/fact_shipments.csv` is preserved. On-time flags are recomputed dynamically in `metrics_engine.py` against the single product SLA target. If regeneration is desired, running `python src/data_generator.py` will regenerate all tables using the updated uniform SLA logic.
