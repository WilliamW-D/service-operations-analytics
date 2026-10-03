"""
Unit tests for data generation and data quality audit engine.
"""

import pytest
import pandas as pd
from etl.generator import generate_raw_operational_data
from etl.data_quality import DataQualityEngine

def test_data_generation_columns():
    df = generate_raw_operational_data(50)
    assert len(df) == 50
    expected_cols = [
        "ticket_number", "created_date", "closed_date", "target_sla_hours",
        "department_name", "division_name", "request_category", "request_type",
        "priority_level", "status", "district_code", "neighborhood", "zip_code",
        "latitude", "longitude", "satisfaction_rating", "is_repeat", "channel"
    ]
    for col in expected_cols:
        assert col in df.columns

def test_data_quality_null_check():
    df = generate_raw_operational_data(20)
    dq = DataQualityEngine(df)
    passed, log = dq.run_all_checks()
    assert bool(passed) is True
    assert len(log) > 0

def test_data_quality_sanitization():
    df = pd.DataFrame([{
        "ticket_number": "SR-999",
        "created_date": "2025-01-01 10:00:00",
        "closed_date": "2025-01-01 12:00:00",
        "target_sla_hours": 24.0,
        "department_name": " Public Works  ",
        "division_name": "Roads",
        "request_category": "Infrastructure",
        "request_type": "Pothole",
        "priority_level": "High",
        "status": "Closed - Resolved",
        "district_code": None,
        "neighborhood": None,
        "zip_code": None,
        "latitude": 32.6,
        "longitude": -85.4,
        "satisfaction_rating": 5,
        "is_repeat": False,
        "channel": "Web"
    }])
    
    dq = DataQualityEngine(df)
    cleaned = dq.clean_data()
    assert cleaned["district_code"].iloc[0] == "DIST-UNKNOWN"
    assert cleaned["neighborhood"].iloc[0] == "Unknown Neighborhood"
    assert cleaned["department_name"].iloc[0] == "Public Works"
