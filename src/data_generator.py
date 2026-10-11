"""Synthetic Logistics & Healthcare Supply Chain Data Generator.

Models multi-modal medical supply chain operations in Ghana, comparing autonomous
drone deliveries against rural ground fleet logistics across diverse regional terrains.
Generates a 1-year star-schema dataset with realistic physical, seasonal, and operational dynamics.
"""

import math
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on Earth in kilometers."""
    r = 6371.0  # Earth radius in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r * c, 2)


def generate_dimension_tables() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate dimension tables for Hubs, Clinics, and Products."""
    # 1. Distribution Hubs (Inspired by actual Ghana Zipline & regional medical distribution centers)
    hubs_data = [
        {
            "hub_id": "HUB-OMN",
            "hub_name": "Omenako Distribution Center",
            "region": "Eastern",
            "latitude": 6.0385,
            "longitude": -0.4578,
            "drone_fleet_size": 28,
            "vehicle_fleet_size": 12,
            "serviced_radius_km": 120,
        },
        {
            "hub_id": "HUB-MPN",
            "hub_name": "Mpanya Medical Nest",
            "region": "Ashanti",
            "latitude": 6.8924,
            "longitude": -1.4125,
            "drone_fleet_size": 32,
            "vehicle_fleet_size": 14,
            "serviced_radius_km": 130,
        },
        {
            "hub_id": "HUB-KUK",
            "hub_name": "Kukua Fulfillment Hub",
            "region": "Northern",
            "latitude": 10.3541,
            "longitude": -0.8123,
            "drone_fleet_size": 24,
            "vehicle_fleet_size": 8,
            "serviced_radius_km": 150,
        },
        {
            "hub_id": "HUB-SFW",
            "hub_name": "Sefwi Wiawso Depot",
            "region": "Western",
            "latitude": 6.2081,
            "longitude": -2.4839,
            "drone_fleet_size": 20,
            "vehicle_fleet_size": 10,
            "serviced_radius_km": 110,
        },
        {
            "hub_id": "HUB-ANK",
            "hub_name": "Ankaful Coastal Center",
            "region": "Central",
            "latitude": 5.1472,
            "longitude": -1.2986,
            "drone_fleet_size": 18,
            "vehicle_fleet_size": 12,
            "serviced_radius_km": 100,
        },
    ]
    df_hubs = pd.DataFrame(hubs_data)

    # 2. Clinics across Ghanaian Administrative Regions
    clinics_data = [
        # Eastern Region
        {"clinic_id": "CLN-EAS-001", "clinic_name": "Suhum Community Hospital", "region": "Eastern", "latitude": 6.0402, "longitude": -0.4501, "remote_tier": "Tier 1", "population_served": 45000, "nearest_hub": "HUB-OMN"},
        {"clinic_id": "CLN-EAS-002", "clinic_name": "Begoro District Clinic", "region": "Eastern", "latitude": 6.3889, "longitude": -0.3789, "remote_tier": "Tier 2", "population_served": 28000, "nearest_hub": "HUB-OMN"},
        {"clinic_id": "CLN-EAS-003", "clinic_name": "Donkorkrom Afram Plains Center", "region": "Eastern", "latitude": 6.9189, "longitude": -0.0825, "remote_tier": "Tier 3", "population_served": 19500, "nearest_hub": "HUB-OMN"},
        {"clinic_id": "CLN-EAS-004", "clinic_name": "Asamankese Health Post", "region": "Eastern", "latitude": 5.8601, "longitude": -0.6635, "remote_tier": "Tier 1", "population_served": 34000, "nearest_hub": "HUB-OMN"},
        {"clinic_id": "CLN-EAS-005", "clinic_name": "Kwahu Tafo Rural Outreach", "region": "Eastern", "latitude": 6.6120, "longitude": -0.6120, "remote_tier": "Tier 2", "population_served": 14200, "nearest_hub": "HUB-OMN"},
        {"clinic_id": "CLN-EAS-006", "clinic_name": "Tease Island Aid Post", "region": "Eastern", "latitude": 6.8400, "longitude": -0.1600, "remote_tier": "Tier 3", "population_served": 8900, "nearest_hub": "HUB-OMN"},

        # Ashanti Region
        {"clinic_id": "CLN-ASH-001", "clinic_name": "Mampong Municipal Hospital", "region": "Ashanti", "latitude": 7.0625, "longitude": -1.4002, "remote_tier": "Tier 1", "population_served": 52000, "nearest_hub": "HUB-MPN"},
        {"clinic_id": "CLN-ASH-002", "clinic_name": "Ejura Agricultural Clinic", "region": "Ashanti", "latitude": 7.3856, "longitude": -1.3654, "remote_tier": "Tier 2", "population_served": 31000, "nearest_hub": "HUB-MPN"},
        {"clinic_id": "CLN-ASH-003", "clinic_name": "Agogo Presbyterian Clinic", "region": "Ashanti", "latitude": 6.8012, "longitude": -1.0824, "remote_tier": "Tier 1", "population_served": 38000, "nearest_hub": "HUB-MPN"},
        {"clinic_id": "CLN-ASH-004", "clinic_name": "Bosome Freho Forest Post", "region": "Ashanti", "latitude": 6.4215, "longitude": -1.3850, "remote_tier": "Tier 3", "population_served": 11500, "nearest_hub": "HUB-MPN"},
        {"clinic_id": "CLN-ASH-005", "clinic_name": "Drobonso Savanna Health Center", "region": "Ashanti", "latitude": 7.1150, "longitude": -1.0250, "remote_tier": "Tier 3", "population_served": 12800, "nearest_hub": "HUB-MPN"},
        {"clinic_id": "CLN-ASH-006", "clinic_name": "Juaben Methodist Clinic", "region": "Ashanti", "latitude": 6.8167, "longitude": -1.4333, "remote_tier": "Tier 1", "population_served": 29000, "nearest_hub": "HUB-MPN"},

        # Northern & Upper Regions
        {"clinic_id": "CLN-NOR-001", "clinic_name": "Walewale District Hospital", "region": "Northern", "latitude": 10.3524, "longitude": -0.7984, "remote_tier": "Tier 1", "population_served": 61000, "nearest_hub": "HUB-KUK"},
        {"clinic_id": "CLN-NOR-002", "clinic_name": "Nalerigu Baptist Medical Post", "region": "Northern", "latitude": 10.5312, "longitude": -0.3705, "remote_tier": "Tier 2", "population_served": 27500, "nearest_hub": "HUB-KUK"},
        {"clinic_id": "CLN-NOR-003", "clinic_name": "Bunkpurugu Border Clinic", "region": "Northern", "latitude": 10.5510, "longitude": 0.0980, "remote_tier": "Tier 3", "population_served": 18200, "nearest_hub": "HUB-KUK"},
        {"clinic_id": "CLN-NOR-004", "clinic_name": "Chereponi Riverway Post", "region": "Northern", "latitude": 10.1340, "longitude": 0.2840, "remote_tier": "Tier 3", "population_served": 15400, "nearest_hub": "HUB-KUK"},
        {"clinic_id": "CLN-NOR-005", "clinic_name": "Savelugu Polyclinic", "region": "Northern", "latitude": 9.6247, "longitude": -0.8258, "remote_tier": "Tier 1", "population_served": 48000, "nearest_hub": "HUB-KUK"},
        {"clinic_id": "CLN-NOR-006", "clinic_name": "Gushegu Rural Aid", "region": "Northern", "latitude": 9.9214, "longitude": -0.2185, "remote_tier": "Tier 2", "population_served": 21000, "nearest_hub": "HUB-KUK"},

        # Western & Western North
        {"clinic_id": "CLN-WES-001", "clinic_name": "Juaboso Goldfields Hospital", "region": "Western", "latitude": 6.3389, "longitude": -2.8341, "remote_tier": "Tier 2", "population_served": 32000, "nearest_hub": "HUB-SFW"},
        {"clinic_id": "CLN-WES-002", "clinic_name": "Bia West Rainforest Clinic", "region": "Western", "latitude": 6.5512, "longitude": -3.0541, "remote_tier": "Tier 3", "population_served": 14100, "nearest_hub": "HUB-SFW"},
        {"clinic_id": "CLN-WES-003", "clinic_name": "Bibiani Municipal Health Center", "region": "Western", "latitude": 6.4635, "longitude": -2.3194, "remote_tier": "Tier 1", "population_served": 41000, "nearest_hub": "HUB-SFW"},
        {"clinic_id": "CLN-WES-004", "clinic_name": "Enchi Remote Clinic", "region": "Western", "latitude": 5.8214, "longitude": -2.8250, "remote_tier": "Tier 3", "population_served": 17800, "nearest_hub": "HUB-SFW"},
        {"clinic_id": "CLN-WES-005", "clinic_name": "Asankragwa Community Post", "region": "Western", "latitude": 5.8021, "longitude": -2.4352, "remote_tier": "Tier 2", "population_served": 24500, "nearest_hub": "HUB-SFW"},

        # Volta & Oti
        {"clinic_id": "CLN-VOL-001", "clinic_name": "Ho Municipal Hospital", "region": "Volta", "latitude": 6.6110, "longitude": 0.4710, "remote_tier": "Tier 1", "population_served": 55000, "nearest_hub": "HUB-OMN"},
        {"clinic_id": "CLN-VOL-002", "clinic_name": "Kpandu Mountain Clinic", "region": "Volta", "latitude": 6.9950, "longitude": 0.2930, "remote_tier": "Tier 2", "population_served": 29000, "nearest_hub": "HUB-OMN"},
        {"clinic_id": "CLN-VOL-003", "clinic_name": "Nkwanta Northern Ridge Post", "region": "Volta", "latitude": 8.2570, "longitude": 0.5210, "remote_tier": "Tier 3", "population_served": 16400, "nearest_hub": "HUB-OMN"},
        {"clinic_id": "CLN-VOL-004", "clinic_name": "Dambai Lake Ferry Aid Center", "region": "Volta", "latitude": 8.0667, "longitude": 0.1833, "remote_tier": "Tier 3", "population_served": 13900, "nearest_hub": "HUB-OMN"},
        {"clinic_id": "CLN-VOL-005", "clinic_name": "Sogakope Riverside Clinic", "region": "Volta", "latitude": 5.9990, "longitude": 0.5980, "remote_tier": "Tier 1", "population_served": 31200, "nearest_hub": "HUB-OMN"},

        # Greater Accra Peri-Urban & Remote Enclaves
        {"clinic_id": "CLN-GAC-001", "clinic_name": "Amabor Rural Health Center", "region": "Greater Accra", "latitude": 5.7820, "longitude": -0.3450, "remote_tier": "Tier 1", "population_served": 42000, "nearest_hub": "HUB-OMN"},
        {"clinic_id": "CLN-GAC-002", "clinic_name": "Dodowa Forest Perimeter Post", "region": "Greater Accra", "latitude": 5.8820, "longitude": -0.0980, "remote_tier": "Tier 2", "population_served": 26000, "nearest_hub": "HUB-OMN"},
        {"clinic_id": "CLN-GAC-003", "clinic_name": "Ada Foah Estuary Clinic", "region": "Greater Accra", "latitude": 5.7910, "longitude": 0.6320, "remote_tier": "Tier 3", "population_served": 18500, "nearest_hub": "HUB-OMN"},
        {"clinic_id": "CLN-GAC-004", "clinic_name": "Prampram Coastal Aid Post", "region": "Greater Accra", "latitude": 5.7140, "longitude": 0.1240, "remote_tier": "Tier 1", "population_served": 35000, "nearest_hub": "HUB-OMN"},
    ]
    df_clinics = pd.DataFrame(clinics_data)

    # 3. Medical Products Dimension Table
    products_data = [
        # Antivenoms (Emergency, Ambient / cool room)
        {"product_id": "PRD-AVM-001", "product_name": "Polyvalent Snake Antivenom", "category": "Antivenom", "storage_requirement": "Ambient", "urgency_level": "Emergency", "unit_cost_usd": 120.0, "shelf_life_days": 730, "target_delivery_hours": 1.0},
        {"product_id": "PRD-AVM-002", "product_name": "Echis Ocellatus Monovalent Antivenom", "category": "Antivenom", "storage_requirement": "Ambient", "urgency_level": "Emergency", "unit_cost_usd": 145.0, "shelf_life_days": 730, "target_delivery_hours": 1.0},

        # Vaccines (Cold Chain 2-8°C)
        {"product_id": "PRD-VAC-001", "product_name": "Rabies Post-Exposure Vaccine", "category": "Vaccine", "storage_requirement": "Cold Chain", "urgency_level": "Emergency", "unit_cost_usd": 48.0, "shelf_life_days": 365, "target_delivery_hours": 1.5},
        {"product_id": "PRD-VAC-002", "product_name": "Yellow Fever Routine Vaccine (10-dose)", "category": "Vaccine", "storage_requirement": "Cold Chain", "urgency_level": "Routine", "unit_cost_usd": 18.0, "shelf_life_days": 180, "target_delivery_hours": 8.0},
        {"product_id": "PRD-VAC-003", "product_name": "Pentavalent DTP-HepB-Hib Vaccine", "category": "Vaccine", "storage_requirement": "Cold Chain", "urgency_level": "Routine", "unit_cost_usd": 22.5, "shelf_life_days": 180, "target_delivery_hours": 8.0},
        {"product_id": "PRD-VAC-004", "product_name": "Oral Polio Vaccine (OPV)", "category": "Vaccine", "storage_requirement": "Cold Chain", "urgency_level": "Routine", "unit_cost_usd": 12.0, "shelf_life_days": 90, "target_delivery_hours": 6.0},

        # Blood Products (Cold Chain 1-6°C, Extreme Urgency)
        {"product_id": "PRD-BLD-001", "product_name": "Whole Blood O-Negative (Emergency Reserve)", "category": "Blood Products", "storage_requirement": "Cold Chain", "urgency_level": "Emergency", "unit_cost_usd": 85.0, "shelf_life_days": 35, "target_delivery_hours": 0.75},
        {"product_id": "PRD-BLD-002", "product_name": "Packed Red Blood Cells (PRBC Type A+)", "category": "Blood Products", "storage_requirement": "Cold Chain", "urgency_level": "Emergency", "unit_cost_usd": 90.0, "shelf_life_days": 42, "target_delivery_hours": 1.0},
        {"product_id": "PRD-BLD-003", "product_name": "Fresh Frozen Plasma (FFP)", "category": "Blood Products", "storage_requirement": "Cold Chain", "urgency_level": "Priority", "unit_cost_usd": 110.0, "shelf_life_days": 365, "target_delivery_hours": 2.0},

        # Essential Medicines (Routine Replenishment & Maternal Health)
        {"product_id": "PRD-MED-001", "product_name": "Oxytocin Injectable (Postpartum Hemorrhage)", "category": "Essential Meds", "storage_requirement": "Cold Chain", "urgency_level": "Emergency", "unit_cost_usd": 8.5, "shelf_life_days": 180, "target_delivery_hours": 1.0},
        {"product_id": "PRD-MED-002", "product_name": "Artesunate IV (Severe Malaria)", "category": "Essential Meds", "storage_requirement": "Ambient", "urgency_level": "Emergency", "unit_cost_usd": 15.0, "shelf_life_days": 730, "target_delivery_hours": 1.5},
        {"product_id": "PRD-MED-003", "product_name": "Amoxicillin Pediatric Suspension (Bulk)", "category": "Essential Meds", "storage_requirement": "Ambient", "urgency_level": "Routine", "unit_cost_usd": 4.5, "shelf_life_days": 540, "target_delivery_hours": 12.0},
        {"product_id": "PRD-MED-004", "product_name": "Magnesium Sulfate 50% (Eclampsia Protocol)", "category": "Essential Meds", "storage_requirement": "Ambient", "urgency_level": "Priority", "unit_cost_usd": 11.0, "shelf_life_days": 730, "target_delivery_hours": 2.5},
        {"product_id": "PRD-MED-005", "product_name": "Insulin Glargine Pen Cartridges", "category": "Essential Meds", "storage_requirement": "Cold Chain", "urgency_level": "Priority", "unit_cost_usd": 35.0, "shelf_life_days": 180, "target_delivery_hours": 4.0},
    ]
    df_products = pd.DataFrame(products_data)

    return df_hubs, df_clinics, df_products


def generate_fact_shipments(
    df_hubs: pd.DataFrame,
    df_clinics: pd.DataFrame,
    df_products: pd.DataFrame,
    n_shipments: int = 12500,
    random_seed: int = 42,
) -> pd.DataFrame:
    """Generate realistic 1-year transactional shipment logs with seasonal weather, terrain bottlenecks, and modal divergence."""
    np.random.seed(random_seed)

    # Precompute distances from each clinic to hubs
    hubs_dict = df_hubs.set_index("hub_id").to_dict("index")
    clinics_dict = df_clinics.set_index("clinic_id").to_dict("index")
    products_dict = df_products.set_index("product_id").to_dict("index")

    clinic_ids = df_clinics["clinic_id"].values
    product_ids = df_products["product_id"].values

    # Realistic request timestamp distribution over 1 full year (2025)
    start_date = datetime(2025, 1, 1, 6, 0, 0)
    total_seconds_in_year = 365 * 24 * 3600

    # Weight products by request frequency
    product_weights = [
        0.06, 0.04,  # Antivenom
        0.08, 0.12, 0.10, 0.08,  # Vaccines
        0.05, 0.04, 0.03,  # Blood
        0.10, 0.12, 0.07, 0.06, 0.05  # Essential Meds
    ]
    product_weights = np.array(product_weights) / sum(product_weights)

    # Weight clinics (higher remote tier clinics request slightly more frequent emergency deliveries due to lack of local storage)
    clinic_weight_map = {"Tier 1": 1.0, "Tier 2": 1.2, "Tier 3": 1.5}
    raw_weights = [clinic_weight_map[clinics_dict[cid]["remote_tier"]] for cid in clinic_ids]
    clinic_weights = np.array(raw_weights) / sum(raw_weights)

    records = []

    for i in range(1, n_shipments + 1):
        req_id = f"REQ-2025-{i:06d}"
        clinic_id = np.random.choice(clinic_ids, p=clinic_weights)
        product_id = np.random.choice(product_ids, p=product_weights)

        clinic = clinics_dict[clinic_id]
        product = products_dict[product_id]
        hub_id = clinic["nearest_hub"]
        hub = hubs_dict[hub_id]

        # Distance calculation with real coordinates + winding factor for road
        direct_dist_km = haversine_distance(
            hub["latitude"], hub["longitude"],
            clinic["latitude"], clinic["longitude"]
        )
        if direct_dist_km < 5.0:
            direct_dist_km = 5.0

        # Request timestamp with Poisson arrival profile (peaks during daytime, but emergencies happen 24/7)
        offset_sec = np.random.uniform(0, total_seconds_in_year)
        req_dt = start_date + timedelta(seconds=offset_sec)
        month = req_dt.month

        # Seasonal Weather Modeling in Ghana:
        # Major Rainy Season: April (4) - July (7)
        # Minor Rainy Season: September (9) - November (11)
        # Dry Harmattan: December (12) - February (2)
        is_monsoon = month in [4, 5, 6, 7]
        is_minor_rain = month in [9, 10, 11]

        if is_monsoon:
            weather_p = [0.45, 0.35, 0.20]  # Clear, Heavy Rain/Squall, Severe Flood
        elif is_minor_rain:
            weather_p = [0.65, 0.25, 0.10]
        else:
            weather_p = [0.85, 0.12, 0.03]

        weather_condition = np.random.choice(["Clear", "Heavy Rain", "Severe Storm/Flood"], p=weather_p)

        # Transport mode selection:
        # Drone is heavily prioritized for Emergency items, high remote tiers, and rainy season washed-out roads.
        # Road is prioritized for bulk routine meds in Tier 1 accessible zones.
        drone_prob = 0.50
        if product["urgency_level"] == "Emergency":
            drone_prob += 0.35
        elif product["urgency_level"] == "Priority":
            drone_prob += 0.15

        if clinic["remote_tier"] == "Tier 3":
            drone_prob += 0.25
        elif clinic["remote_tier"] == "Tier 2":
            drone_prob += 0.10

        if weather_condition in ["Heavy Rain", "Severe Storm/Flood"]:
            # Road roads get washed out, but severe storm also affects drones.
            # In moderate rain drones excel; in severe storms, drone flights delay until window clears.
            drone_prob += 0.10

        drone_prob = min(max(drone_prob, 0.15), 0.95)
        transport_mode = "Drone" if np.random.rand() < drone_prob else "Road"

        # Hub stock availability simulation (Stock-Out rate ~4-7% overall, higher in remote clinics requesting rare antivenom/blood)
        stock_out_prob = 0.035
        if product["category"] in ["Blood Products", "Antivenom"]:
            stock_out_prob += 0.030
        if is_monsoon:
            stock_out_prob += 0.015

        is_stock_out = np.random.rand() < stock_out_prob

        units_requested = int(np.random.choice([1, 2, 4, 10, 20], p=[0.40, 0.30, 0.15, 0.10, 0.05]))

        if is_stock_out:
            order_status = "Stock-Out"
            dispatch_dt = pd.NaT
            delivery_dt = pd.NaT
            lead_time_hours = np.nan
            is_on_time = False
            cold_chain_breach = False
            units_delivered = 0
            transit_distance_km = direct_dist_km
        else:
            units_delivered = units_requested
            # Dispatch preparation time (picking, cold box packaging, flight programming / vehicle loading)
            if transport_mode == "Drone":
                prep_minutes = np.random.uniform(8, 22)
            else:
                prep_minutes = np.random.uniform(30, 110)  # Road logistics require batching & manifesting

            dispatch_dt = req_dt + timedelta(minutes=prep_minutes)

            # Transit travel physics:
            if transport_mode == "Drone":
                transit_distance_km = direct_dist_km  # Direct aerial path
                # Autonomous medical fixed-wing drone cruising speed ~100-110 km/h
                drone_speed_kmh = np.random.uniform(95, 115)
                transit_hours = transit_distance_km / drone_speed_kmh

                # Weather friction for drone:
                if weather_condition == "Heavy Rain":
                    transit_hours += np.random.uniform(0.15, 0.35)  # minor hold or reroute
                elif weather_condition == "Severe Storm/Flood":
                    # Drone ground-stop delay waiting for squall line to pass
                    transit_hours += np.random.uniform(0.5, 1.5)

            else:
                # Road travel: Winding factor is 1.35x for Tier 1, up to 1.85x for Tier 3 rural dirt tracks
                winding_factor = {"Tier 1": 1.35, "Tier 2": 1.55, "Tier 3": 1.85}[clinic["remote_tier"]]
                transit_distance_km = round(direct_dist_km * winding_factor, 2)

                # Road vehicle speed (km/h) heavily dependent on tier & weather
                base_road_speed = {"Tier 1": 55.0, "Tier 2": 38.0, "Tier 3": 24.0}[clinic["remote_tier"]]
                road_speed_kmh = np.random.uniform(base_road_speed * 0.85, base_road_speed * 1.15)

                if weather_condition == "Heavy Rain":
                    road_speed_kmh *= 0.65  # Potholes, mud, low visibility
                elif weather_condition == "Severe Storm/Flood":
                    road_speed_kmh *= 0.35  # Washed out bridges, river crossing delays

                transit_hours = transit_distance_km / max(road_speed_kmh, 8.0)

                # Road route bottlenecks & mechanical issues
                if np.random.rand() < (0.15 if clinic["remote_tier"] == "Tier 3" else 0.05):
                    transit_hours += np.random.uniform(1.5, 4.0)

            total_lead_time_hours = round((prep_minutes / 60.0) + transit_hours, 2)
            delivery_dt = dispatch_dt + timedelta(hours=transit_hours)
            lead_time_hours = total_lead_time_hours

            # On-time performance evaluated against consistent product SLA delivery deadline
            effective_sla = product["target_delivery_hours"]
            is_on_time = lead_time_hours <= effective_sla
            order_status = "Fulfilled" if is_on_time else "Delayed"

            # Cold chain compliance:
            # Breaches occur if cold-chain item takes > 4.5 hours in unconditioned road transit or severe heat delay
            cold_chain_breach = False
            if product["storage_requirement"] == "Cold Chain":
                if transport_mode == "Road" and lead_time_hours > 3.5:
                    cold_chain_breach = np.random.rand() < 0.22
                elif transport_mode == "Drone" and lead_time_hours > 2.0:
                    cold_chain_breach = np.random.rand() < 0.03
                else:
                    cold_chain_breach = np.random.rand() < 0.005

        records.append({
            "request_id": req_id,
            "clinic_id": clinic_id,
            "product_id": product_id,
            "hub_id": hub_id,
            "requested_timestamp": req_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "dispatch_timestamp": dispatch_dt.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(dispatch_dt) else None,
            "delivery_timestamp": delivery_dt.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(delivery_dt) else None,
            "distance_km": round(transit_distance_km, 2),
            "transport_mode": transport_mode,
            "order_status": order_status,
            "units_requested": units_requested,
            "units_delivered": units_delivered,
            "lead_time_hours": lead_time_hours,
            "is_on_time": is_on_time,
            "cold_chain_breach": cold_chain_breach,
            "weather_condition": weather_condition,
        })

    df_fact = pd.DataFrame(records)
    return df_fact


def run_pipeline(output_dir: str = "data", n_shipments: int = 12500) -> None:
    """Generate all star-schema dimension and fact tables and persist to CSV files."""
    os.makedirs(output_dir, exist_ok=True)

    print("Generating Dimension Tables (Clinics, Products, Distribution Hubs)...")
    df_hubs, df_clinics, df_products = generate_dimension_tables()

    print(f"Generating Fact Table with {n_shipments:,} shipment records...")
    df_fact = generate_fact_shipments(df_hubs, df_clinics, df_products, n_shipments=n_shipments)

    # Export to CSV
    hubs_path = os.path.join(output_dir, "dim_hubs.csv")
    clinics_path = os.path.join(output_dir, "dim_clinics.csv")
    products_path = os.path.join(output_dir, "dim_products.csv")
    fact_path = os.path.join(output_dir, "fact_shipments.csv")

    df_hubs.to_csv(hubs_path, index=False)
    df_clinics.to_csv(clinics_path, index=False)
    df_products.to_csv(products_path, index=False)
    df_fact.to_csv(fact_path, index=False)

    print(f"[OK] Successfully saved: {hubs_path} ({len(df_hubs)} hubs)")
    print(f"[OK] Successfully saved: {clinics_path} ({len(df_clinics)} clinics)")
    print(f"[OK] Successfully saved: {products_path} ({len(df_products)} products)")
    print(f"[OK] Successfully saved: {fact_path} ({len(df_fact):,} shipments)")


if __name__ == "__main__":
    run_pipeline()
