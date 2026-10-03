"""
Synthetic Data Generator for Municipal / Operational Service Requests.
Generates realistic 311 service tickets with timestamps, categories, departments,
locations, SLA targets, resolution times, and satisfaction scores.
"""

import os
import random
import uuid
from datetime import datetime, timedelta
import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

# Operational Metadata Configurations
DEPARTMENTS = [
    {"dept": "Public Works", "division": "Roads & Infrastructure", "head": "Eleanor Vance", "capacity": 45},
    {"dept": "Public Works", "division": "Sanitation & Waste", "head": "Marcus Brody", "capacity": 60},
    {"dept": "Water & Utilities", "division": "Water Main Maintenance", "head": "Sarah Jenkins", "capacity": 30},
    {"dept": "Public Safety", "division": "Code Enforcement", "head": "David Rossi", "capacity": 25},
    {"dept": "Parks & Recreation", "division": "Tree Maintenance & Grounds", "head": "Chloe Bennett", "capacity": 20},
    {"dept": "Transportation", "division": "Traffic Signals & Transit", "head": "Carlos Mendez", "capacity": 35},
]

REQUEST_TYPES = [
    {"category": "Infrastructure", "type": "Pothole Repair", "priority": "High", "sla": 48.0},
    {"category": "Infrastructure", "type": "Streetlight Outage", "priority": "Medium", "sla": 72.0},
    {"category": "Sanitation", "type": "Illegal Dumping Cleanup", "priority": "High", "sla": 24.0},
    {"category": "Sanitation", "type": "Missed Trash Pickup", "priority": "Low", "sla": 48.0},
    {"category": "Water & Utilities", "type": "Water Main Leak", "priority": "Critical", "sla": 12.0},
    {"category": "Water & Utilities", "type": "Storm Drain Clog", "priority": "High", "sla": 36.0},
    {"category": "Code Enforcement", "type": "Noise Violation", "priority": "Medium", "sla": 24.0},
    {"category": "Code Enforcement", "type": "Overgrown Lot Hazard", "priority": "Low", "sla": 120.0},
    {"category": "Parks & Grounds", "type": "Fallen Tree Branch", "priority": "Critical", "sla": 12.0},
    {"category": "Parks & Grounds", "type": "Park Facility Damage", "priority": "Medium", "sla": 96.0},
    {"category": "Traffic & Transit", "type": "Traffic Light Malfunction", "priority": "Critical", "sla": 6.0},
    {"category": "Traffic & Transit", "type": "Damaged Signage", "priority": "Low", "sla": 168.0},
]

DISTRICTS = [
    {"district": "DIST-01", "neighborhood": "Downtown Metro", "zip": "36830", "lat": 32.6099, "lng": -85.4808, "zone": "Central"},
    {"district": "DIST-02", "neighborhood": "Northside Heights", "zip": "36831", "lat": 32.6250, "lng": -85.4710, "zone": "North"},
    {"district": "DIST-03", "neighborhood": "University Hills", "zip": "36832", "lat": 32.5980, "lng": -85.4950, "zone": "South"},
    {"district": "DIST-04", "neighborhood": "East Park Industrial", "zip": "36834", "lat": 32.6150, "lng": -85.4410, "zone": "East"},
    {"district": "DIST-05", "neighborhood": "West End Suburbs", "zip": "36835", "lat": 32.6010, "lng": -85.5200, "zone": "West"},
]

CHANNELS = ["Mobile App", "Web Portal", "Phone Call 311", "Walk-in", "Automated Sensor"]

STATUSES = ["Closed - Resolved", "Closed - Duplicate", "In Progress", "Assigned", "Pending Review"]

def generate_raw_operational_data(num_records: int = 5000, start_days_ago: int = 365) -> pd.DataFrame:
    """Generate synthetic 311 operational service request records."""
    data = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=start_days_ago)

    for i in range(num_records):
        ticket_number = f"SR-2025-{100000 + i}"
        
        # Random dates
        random_days = random.uniform(0, start_days_ago)
        created_dt = start_date + timedelta(days=random_days)
        
        # Pick category & department matching
        req_spec = random.choice(REQUEST_TYPES)
        if req_spec["category"] == "Infrastructure":
            dept_spec = DEPARTMENTS[0]
        elif req_spec["category"] == "Sanitation":
            dept_spec = DEPARTMENTS[1]
        elif req_spec["category"] == "Water & Utilities":
            dept_spec = DEPARTMENTS[2]
        elif req_spec["category"] == "Code Enforcement":
            dept_spec = DEPARTMENTS[3]
        elif req_spec["category"] == "Parks & Grounds":
            dept_spec = DEPARTMENTS[4]
        else:
            dept_spec = DEPARTMENTS[5]
            
        dist_spec = random.choice(DISTRICTS)
        target_sla = req_spec["sla"]
        
        # Status logic
        # 85% tickets are closed, 15% open/in-progress
        days_old = (end_date - created_dt).total_seconds() / 3600.0
        if days_old > 168 and random.random() < 0.95:
            status = "Closed - Resolved"
        else:
            status = random.choice(STATUSES)
            
        closed_dt = None
        resolution_hours = None
        satisfaction = None
        
        if "Closed" in status:
            # Simulate realistic resolution time centered around target SLA
            # Introduce occasional SLA breaches (20% chance)
            if random.random() < 0.80:
                # Met SLA
                resolution_hours = round(random.uniform(0.1, target_sla * 0.95), 2)
            else:
                # Breached SLA
                resolution_hours = round(random.uniform(target_sla * 1.05, target_sla * 3.5), 2)
                
            closed_dt = created_dt + timedelta(hours=resolution_hours)
            
            # Satisfaction rating correlated with SLA compliance
            if resolution_hours <= target_sla:
                satisfaction = random.choice([4, 5, 5, 5, 4, 3])
            else:
                satisfaction = random.choice([1, 1, 2, 2, 3, 4])
                
        is_repeat = random.random() < 0.12  # 12% repeat rate
        
        # Perturb lat/lng slightly for neighborhood distribution
        lat = round(dist_spec["lat"] + random.uniform(-0.01, 0.01), 6)
        lng = round(dist_spec["lng"] + random.uniform(-0.01, 0.01), 6)

        data.append({
            "ticket_number": ticket_number,
            "created_date": created_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "closed_date": closed_dt.strftime("%Y-%m-%d %H:%M:%S") if closed_dt else None,
            "target_sla_hours": target_sla,
            "department_name": dept_spec["dept"],
            "division_name": dept_spec["division"],
            "request_category": req_spec["category"],
            "request_type": req_spec["type"],
            "priority_level": req_spec["priority"],
            "status": status,
            "district_code": dist_spec["district"],
            "neighborhood": dist_spec["neighborhood"],
            "zip_code": dist_spec["zip"],
            "latitude": lat,
            "longitude": lng,
            "satisfaction_rating": satisfaction,
            "is_repeat": is_repeat,
            "channel": random.choice(CHANNELS)
        })

    df = pd.DataFrame(data)
    return df

if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "raw_service_requests.csv")
    df = generate_raw_operational_data(5000)
    df.to_csv(csv_path, index=False)
    print(f"✅ Generated 5,000 raw service request records -> {csv_path}")
