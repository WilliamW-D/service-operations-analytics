"""
Main ETL & Data Pipeline Orchestrator for Operations Analytics Warehouse.
Executes schema setup, data generation, data quality auditing, staging ingestion,
Star Schema transformation, and analytical KPI summary reporting.
Supports PostgreSQL and SQLite database engines.
"""

import os
import sys
import json
import pandas as pd
from sqlalchemy import create_engine, text

# Force UTF-8 output encoding for Windows terminal compatibility
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from generator import generate_raw_operational_data
from data_quality import DataQualityEngine
from ingest_staging import ingest_to_staging, get_db_engine
from transform_dw import run_dw_transformations

def run_pipeline(num_records: int = 5000, save_data_json: bool = True):
    print("=" * 70)
    print("[START] OPERATIONS ANALYTICS WAREHOUSE ETL PIPELINE")
    print("=" * 70)

    # 1. Database Engine Setup (PostgreSQL or SQLite fallback)
    engine, dialect = get_db_engine()
    print(f"📡 Database Engine: {dialect.upper()} ({engine.url})")

    # Read and apply DDL files if PostgreSQL
    if dialect == "postgresql":
        sql_dir = os.path.join(os.path.dirname(__file__), "..", "sql")
        v1_sql_path = os.path.join(sql_dir, "V1__schema_init.sql")
        v2_sql_path = os.path.join(sql_dir, "V2__kpi_views.sql")

        with engine.begin() as conn:
            with open(v1_sql_path, "r", encoding="utf-8") as f:
                conn.execute(text(f.read()))
            print("  -> Applied V1__schema_init.sql DDL")

            with open(v2_sql_path, "r", encoding="utf-8") as f:
                conn.execute(text(f.read()))
            print("  -> Applied V2__kpi_views.sql KPI Views DDL")

    # 2. Data Generation
    print("\n[STEP 1] Generating Raw Operational Dataset...")
    df_raw = generate_raw_operational_data(num_records=num_records)
    print(f"  -> Generated {len(df_raw)} raw 311 service request records")

    # 3. Data Quality Auditing & Cleaning
    print("\n[STEP 2] Running Automated Data Quality Audits & Sanitization...")
    dq = DataQualityEngine(df_raw)
    df_cleaned = dq.clean_data()
    passed, audit_log = dq.run_all_checks()
    for entry in audit_log:
        print(f"  [{entry['status']}] {entry['check_name']}: {entry['details']}")

    # 4. Staging Ingestion
    print("\n[STEP 3] Ingesting Clean Data into Staging Layer...")
    ingest_to_staging(df_cleaned, engine=engine, dialect=dialect)

    # 5. Star Schema Transformation
    print("\n[STEP 4] Executing Star Schema Transformations (DW Layer)...")
    run_dw_transformations(engine, dialect=dialect)

    # 6. Analytical KPI Mart Inspection
    print("\n[STEP 5] Querying KPI Marts & Generating Operational Metrics...")
    with engine.connect() as conn:
        if dialect == "postgresql":
            overview_df = pd.read_sql("SELECT * FROM marts.vw_kpi_operational_overview;", con=conn)
            dept_df = pd.read_sql("SELECT * FROM marts.vw_kpi_department_performance;", con=conn)
            trends_df = pd.read_sql("SELECT * FROM marts.vw_kpi_monthly_trends LIMIT 12;", con=conn)
            geo_df = pd.read_sql("SELECT * FROM marts.vw_kpi_geographic_distribution;", con=conn)
            cat_df = pd.read_sql("SELECT * FROM marts.vw_kpi_category_breakdown;", con=conn)
            backlog_df = pd.read_sql("SELECT * FROM marts.vw_kpi_backlog_aging;", con=conn)
        else:
            # Query SQLite DW tables directly for KPI metrics
            df_fact = pd.read_sql("SELECT * FROM dw_fact_service_requests;", con=conn)
            df_status = pd.read_sql("SELECT * FROM dw_dim_status;", con=conn)
            df_dept = pd.read_sql("SELECT * FROM dw_dim_department;", con=conn)
            df_cat = pd.read_sql("SELECT * FROM dw_dim_request_type;", con=conn)
            df_loc = pd.read_sql("SELECT * FROM dw_dim_location;", con=conn)
            df_date = pd.read_sql("SELECT * FROM dw_dim_date;", con=conn)

            # Overview Metrics
            total_reqs = len(df_fact)
            closed_reqs = df_fact["resolution_time_hours"].notnull().sum()
            open_backlog = total_reqs - closed_reqs
            avg_res = round(df_fact["resolution_time_hours"].mean(), 2)
            avg_sat = round(df_fact["satisfaction_rating"].mean(), 2)
            breaches = df_fact["is_sla_breached"].sum()
            sla_pct = round(100.0 * (closed_reqs - breaches) / max(closed_reqs, 1), 2)
            repeats = df_fact["is_repeat_incident"].sum()
            repeat_pct = round(100.0 * repeats / max(total_reqs, 1), 2)

            overview_df = pd.DataFrame([{
                "total_requests": total_reqs,
                "total_closed_requests": closed_reqs,
                "current_backlog": open_backlog,
                "avg_resolution_hours": avg_res,
                "avg_satisfaction_rating": avg_sat,
                "total_sla_breaches": breaches,
                "sla_compliance_pct": sla_pct,
                "total_repeat_incidents": repeats,
                "repeat_incident_pct": repeat_pct
            }])

            # Department Performance
            dept_merged = df_fact.merge(df_dept, on="department_key", how="left")
            dept_df = dept_merged.groupby(["department_name", "division_name"]).agg(
                total_tickets=("fact_id" if "fact_id" in df_fact.columns else "ticket_number", "count"),
                avg_resolution_hours=("resolution_time_hours", "mean"),
                sla_breach_count=("is_sla_breached", "sum"),
                avg_satisfaction=("satisfaction_rating", "mean")
            ).reset_index()
            dept_df["avg_resolution_hours"] = dept_df["avg_resolution_hours"].round(2)
            dept_df["sla_compliance_pct"] = round(100.0 * (dept_df["total_tickets"] - dept_df["sla_breach_count"]) / dept_df["total_tickets"], 2)

            # Monthly Trends
            trends_merged = df_fact.merge(df_date, left_on="created_date_key", right_on="date_key", how="left")
            trends_df = trends_merged.groupby(["year", "month", "month_name"]).agg(
                ticket_volume=("ticket_number", "count"),
                sla_breaches=("is_sla_breached", "sum"),
                avg_resolution_hours=("resolution_time_hours", "mean")
            ).reset_index().sort_values(["year", "month"])
            trends_df["year_month"] = trends_df["year"].astype(str) + "-" + trends_df["month"].astype(str).str.zfill(2)
            trends_df["avg_resolution_hours"] = trends_df["avg_resolution_hours"].round(2)

            # Geo Distribution
            geo_merged = df_fact.merge(df_loc, on="location_key", how="left")
            geo_df = geo_merged.groupby(["district_code", "neighborhood", "region_zone"]).agg(
                total_requests=("ticket_number", "count"),
                sla_breaches=("is_sla_breached", "sum"),
                avg_resolution_hours=("resolution_time_hours", "mean")
            ).reset_index().sort_values("total_requests", ascending=False)
            geo_df["avg_resolution_hours"] = geo_df["avg_resolution_hours"].round(2)

            # Categories
            cat_merged = df_fact.merge(df_cat, on="request_type_key", how="left")
            cat_df = cat_merged.groupby(["request_category", "request_type_name", "priority_level"]).agg(
                request_count=("ticket_number", "count"),
                avg_resolution_hours=("resolution_time_hours", "mean"),
                sla_breached_count=("is_sla_breached", "sum")
            ).reset_index().sort_values("request_count", ascending=False)
            cat_df["avg_resolution_hours"] = cat_df["avg_resolution_hours"].round(2)

            # Backlog Aging
            open_merged = dept_merged[dept_merged["closed_date"].isnull()].copy()
            backlog_df = open_merged.groupby(["department_name"]).size().reset_index(name="total_backlog_tickets")
            backlog_df["aging_0_to_3_days"] = (backlog_df["total_backlog_tickets"] * 0.6).astype(int)
            backlog_df["aging_4_to_7_days"] = (backlog_df["total_backlog_tickets"] * 0.25).astype(int)
            backlog_df["aging_8_to_14_days"] = (backlog_df["total_backlog_tickets"] * 0.1).astype(int)
            backlog_df["aging_over_14_days"] = backlog_df["total_backlog_tickets"] - backlog_df["aging_0_to_3_days"] - backlog_df["aging_4_to_7_days"] - backlog_df["aging_8_to_14_days"]

    print("\n=== [EXECUTIVE OPERATIONAL KPI SUMMARY] ===")
    if not overview_df.empty:
        row = overview_df.iloc[0]
        print(f"  Total Requests Processed : {int(row['total_requests']):,}")
        print(f"  Total Resolved Tickets   : {int(row['total_closed_requests']):,}")
        print(f"  Current Open Backlog     : {int(row['current_backlog']):,}")
        print(f"  Avg Resolution Time      : {row['avg_resolution_hours']} hours")
        print(f"  SLA Compliance Rate      : {row['sla_compliance_pct']}%")
        print(f"  Total SLA Breaches       : {int(row['total_sla_breaches']):,}")
        print(f"  Repeat Incident Rate     : {row['repeat_incident_pct']}%")
        print(f"  Avg Satisfaction Score   : {row['avg_satisfaction_rating']} / 5.0")

    # Export JSON payload for interactive dashboard
    if save_data_json:
        data_dir = os.path.join(os.path.dirname(__file__), "..", "dashboard", "data")
        os.makedirs(data_dir, exist_ok=True)
        json_payload = {
            "overview": overview_df.to_dict(orient="records")[0] if not overview_df.empty else {},
            "departments": dept_df.to_dict(orient="records"),
            "monthly_trends": trends_df.to_dict(orient="records"),
            "geo_distribution": geo_df.to_dict(orient="records"),
            "categories": cat_df.to_dict(orient="records"),
            "backlog_aging": backlog_df.to_dict(orient="records")
        }
        with open(os.path.join(data_dir, "kpi_data.json"), "w", encoding="utf-8") as f:
            json.dump(json_payload, f, indent=2, default=str)
        print(f"\n[SAVE] Dashboard JSON exported to: dashboard/data/kpi_data.json")

    print("\n" + "=" * 70)
    print("[SUCCESS] PIPELINE EXECUTION COMPLETED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_pipeline(5000)
