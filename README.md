# 🚁 Rural Healthcare Supply Chain & Drone Logistics Analytics (Ghana)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B.svg?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Plotly & PyDeck](https://img.shields.io/badge/Visualization-Plotly%20%7C%20PyDeck-00D2BA.svg)](https://deckgl.readthedocs.io/)
[![Architecture](https://img.shields.io/badge/Data%20Architecture-Star%20Schema-8B5CF6.svg)](#2-architectural-design--star-schema)
[![Target Programs](https://img.shields.io/badge/Portfolio-MSc%20Data%20Science%20(Germany)-10B981.svg)](#6-academic-cv--resume-impact-bullet-points)

An end-to-end Data Engineering and Full-Stack Analytics project modeling multi-modal medical supply chains in the Republic of Ghana. The system compares autonomous aerial drone deliveries against rural ground fleet logistics across diverse regional terrains, evaluating critical cold-chain medicine delivery, emergency blood product dispatches, antivenom supply, and chronic drug replenishment.

---

## 1. Business & Humanitarian Problem Context
In rural Sub-Saharan Africa, seasonal monsoon floods, washed-out infrastructure, and geographical barriers (e.g., Lake Volta islands, dense tropical rainforests) create acute healthcare supply chain bottlenecks. Delays in receiving post-partum hemorrhage medication (Oxytocin), snakebite antivenom, or cross-matched blood directly impact maternal and emergency mortality rates.

Modeled on real-world autonomous medical delivery networks (such as the Ghana Health Service & Zipline public-private partnership), this project analyzes **12,500+ multi-modal logistics transactions** across **5 central distribution hubs** and **32 remote clinics** categorized into 3 accessibility tiers.

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
- **`fact_shipments` (Fact Table)**: Transactional grain representing an individual emergency or routine requisition from a clinic.
- **`dim_clinics` (Dimension Table)**: Health centers across 6 administrative regions (Ashanti, Eastern, Northern, Volta, Western, Greater Accra) mapped with geospatial coordinates and remote access tiers (Tier 1: peri-urban, Tier 2: rural unpaved, Tier 3: deep-forest/island).
- **`dim_products` (Dimension Table)**: Medical cargo classified by thermal storage (Cold Chain $2\text{--}8^\circ\text{C}$ vs. Ambient) and clinical criticality (Emergency, Priority, Routine).
- **`dim_hubs` (Dimension Table)**: Regional distribution centers (Omenako, Mpanya, Kukua, Sefwi Wiawso, Ankaful) maintaining drone nests and refrigerated trucks.

---

## 3. Mathematical & Supply Chain KPI Formulations

### 1. OTIF (On-Time In-Full) Rate
A supply chain gold-standard composite metric. An order is evaluated as OTIF strictly when it satisfies timeliness, quantity completeness, and thermal compliance:
$$\text{OTIF Rate (\%)} = \frac{\sum_{i=1}^{N} \left( \mathbb{I}(\text{OnTime}_i) \cdot \mathbb{I}(\text{InFull}_i) \cdot \mathbb{I}(\text{QualityPass}_i) \right)}{N} \times 100$$
Where:
- $\text{OnTime}_i \iff T_{\text{lead}, i} \le \text{SLA Target Hours}_i$
- $\text{InFull}_i \iff \text{UnitsDelivered}_i = \text{UnitsRequested}_i \land \text{Status}_i \ne \text{'Stock-Out'}$
- $\text{QualityPass}_i \iff \text{ColdChainBreach}_i = \text{False}$

### 2. Physical Distance & Terrain Tortuosity
Geodesic distance is computed via the spherical **Haversine Formula**:
$$d = 2 R \arcsin \left( \sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)} \right)$$
For ground vehicles, realistic road transit distance applies a terrain winding multiplier $\omega \in [1.35, 1.85]$:
$$d_{\text{road}} = d_{\text{geodesic}} \times \omega_{\text{tier}}$$

### 3. Regional Bottleneck Vulnerability Index
A composite index (0–100 scale) identifying high-risk geographic clusters:
$$\text{Bottleneck Index} = 0.35 \times \text{StockOut\%} + 0.35 \times \text{Delay\%} + 20 \times \left( \frac{\bar{T}_{\text{lead}}}{\max(T_{\text{lead}})} \right) + 0.10 \times \text{ColdBreach\%}$$

---

## 4. Key Analytical Insights & Empirical Findings

| Metric | Autonomous Drone Fleet | Ground Road Transport | Performance Delta |
| :--- | :---: | :---: | :---: |
| **Average Order Cycle Time** | **1.22 hours** | **5.79 hours** | **78.9% Reduction** |
| **Tier 3 (Deep Rural) Lead Time** | **1.35 hours** | **8.40 hours** | **83.9% Time Saved** |
| **Severe Storm / Flood Velocity** | **92 km/h (buffered)** | **14 km/h (mud-bound)** | **6.5x Velocity Edge** |
| **Cold-Chain Breaches (Vaccines/Blood)** | **0.2%** | **4.7%** | **95.7% Risk Reduction** |

---

## 5. Repository Structure

```
d:/Rural Logistics/
├── .streamlit/
│   └── config.toml               # Custom dark telemetry theme configuration
├── data/
│   ├── fact_shipments.csv        # 12,500 synthetic multi-modal logistics records
│   ├── dim_clinics.csv           # 32 clinics mapped across 6 Ghanaian administrative regions
│   ├── dim_products.csv          # 14 medical items (antivenom, blood, vaccines, essential meds)
│   └── dim_hubs.csv              # 5 central fulfillment hubs (Omenako, Mpanya, Kukua, etc.)
├── src/
│   ├── __init__.py
│   ├── data_generator.py         # 1-year synthetic data pipeline with seasonal weather shocks
│   ├── metrics_engine.py         # Star schema join, OTIF, lead time, bottleneck calculations
│   └── map_visualizer.py         # PyDeck 3D flight arc engine & Plotly geographic scatter
├── app.py                        # Full-stack interactive Streamlit analytics dashboard
├── requirements.txt              # Project dependencies
└── README.md                     # Comprehensive technical documentation & CV support
```

---

## 6. Academic CV & Resume Impact Bullet Points

*Pre-formulated for Master of Science applications in Data Science, Data Engineering, and Business Analytics in Germany (e.g., TU Munich, LMU Munich, RWTH Aachen, Heidelberg):*

```markdown
- Architected an end-to-end healthcare logistics analytics platform modeled on Ghana's medical drone network (Zipline/GHS), engineering a dimensional Star Schema joining 12,500+ transactional records across 4 relational tables in Pandas and NumPy.
- Formulated supply chain KPI algorithms in Python, including strict multi-condition OTIF (On-Time In-Full) tracking, Haversine geodesic routing with terrain tortuosity penalties, and a composite Regional Bottleneck Vulnerability Index.
- Built an interactive geospatial telemetry dashboard using Streamlit, PyDeck, and Plotly, rendering 3D aerial flight corridors and multi-layer risk classifications across 32 clinics in 6 administrative regions.
- Modeled seasonal monsoon weather disruptions and cold-chain compliance, quantitatively demonstrating that autonomous drones reduce emergency order cycle times by 78.9% (1.2h vs. 5.8h) and cold-chain degradation by 95.7% compared to ground road transit.
```

---

## 7. How to Run Locally

### Prerequisites
- Python 3.10+ installed
- Git

### Step 1: Clone and Navigate
```bash
git clone https://github.com/your-username/rural-healthcare-logistics-analytics.git
cd rural-healthcare-logistics-analytics
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: (Optional) Re-generate Dataset
```bash
python src/data_generator.py
```
*(The repository already includes the pre-generated dataset in `data/`, but running this script will generate fresh deterministic data).*

### Step 4: Launch the Streamlit Dashboard
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.
