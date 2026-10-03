"""
Star Schema Transformation ETL Engine.
Extracts raw data from staging, generates Date/Location/Type/Dept/Status
dimensions, and transforms measures into fact table.
Supports PostgreSQL and SQLite engine dialects.
"""

from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text

def populate_date_dimension(conn, min_date_str: str, max_date_str: str, dialect: str = "postgresql"):
    """Generate calendar dimension rows in dim_date for date range."""
    min_date = pd.to_datetime(min_date_str).date() - pd.Timedelta(days=7)
    max_date = pd.to_datetime(max_date_str).date() + pd.Timedelta(days=7)
    
    dates = pd.date_range(start=min_date, end=max_date)
    date_rows = []
    
    for d in dates:
        date_key = int(d.strftime("%Y%m%d"))
        quarter_num = (d.month - 1) // 3 + 1
        date_rows.append({
            "date_key": date_key,
            "full_date": str(d.date()),
            "year": d.year,
            "quarter": quarter_num,
            "quarter_name": f"Q{quarter_num}",
            "month": d.month,
            "month_name": d.strftime("%B"),
            "day_of_month": d.day,
            "day_of_week": d.dayofweek + 1,
            "day_name": d.strftime("%A"),
            "is_weekend": d.dayofweek in [5, 6],
            "fiscal_year": d.year if d.month >= 10 else d.year - 1,
            "fiscal_quarter": ((d.month + 2) % 12 // 3) + 1
        })
        
    df_date = pd.DataFrame(date_rows)
    table_name = "dim_date"
    schema_name = "dw" if dialect == "postgresql" else None
    if dialect == "sqlite":
        table_name = "dw_dim_date"
        
    df_date.to_sql(table_name, con=conn, schema=schema_name, if_exists="append", index=False)
    print(f"  -> Generated {len(df_date)} date dimension rows in {table_name}")

def run_dw_transformations(engine, dialect: str = "postgresql"):
    """Execute SQL transformations from staging to Star Schema dw tables."""
    staging_tbl = "staging.raw_service_requests" if dialect == "postgresql" else "staging_raw_service_requests"
    
    if dialect == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE dw.fact_service_requests CASCADE;"))
            conn.execute(text("TRUNCATE dw.dim_date CASCADE;"))
            conn.execute(text("TRUNCATE dw.dim_location CASCADE;"))
            conn.execute(text("TRUNCATE dw.dim_request_type CASCADE;"))
            conn.execute(text("TRUNCATE dw.dim_department CASCADE;"))
            conn.execute(text("TRUNCATE dw.dim_status CASCADE;"))

            result = conn.execute(text(f"SELECT MIN(created_date)::text, MAX(created_date)::text FROM {staging_tbl};")).fetchone()
            if result and result[0]:
                populate_date_dimension(conn, result[0], result[1], dialect=dialect)

            # Location
            conn.execute(text(f"""
                INSERT INTO dw.dim_location (district_code, neighborhood, zip_code, latitude, longitude, region_zone)
                SELECT DISTINCT district_code, neighborhood, zip_code, AVG(latitude), AVG(longitude),
                    CASE WHEN district_code IN ('DIST-01', 'DIST-02') THEN 'North Region' ELSE 'South Region' END
                FROM {staging_tbl} GROUP BY district_code, neighborhood, zip_code;
            """))

            # Type
            conn.execute(text(f"""
                INSERT INTO dw.dim_request_type (request_category, request_type_name, priority_level, default_sla_hours)
                SELECT DISTINCT request_category, request_type, priority_level, AVG(target_sla_hours)
                FROM {staging_tbl} GROUP BY request_category, request_type, priority_level;
            """))

            # Dept
            conn.execute(text(f"""
                INSERT INTO dw.dim_department (department_name, division_name, department_head, team_capacity)
                SELECT DISTINCT department_name, division_name, 'Dept Director', 30
                FROM {staging_tbl} GROUP BY department_name, division_name;
            """))

            # Status
            conn.execute(text(f"""
                INSERT INTO dw.dim_status (status_name, is_closed, is_active)
                SELECT DISTINCT status, CASE WHEN status LIKE 'Closed%' THEN TRUE ELSE FALSE END,
                    CASE WHEN status NOT LIKE 'Closed%' THEN TRUE ELSE FALSE END
                FROM {staging_tbl};
            """))

            # Fact
            conn.execute(text(f"""
                INSERT INTO dw.fact_service_requests (
                    ticket_number, created_date_key, closed_date_key, location_key, request_type_key,
                    department_key, status_key, created_timestamp, closed_timestamp, resolution_time_hours,
                    target_sla_hours, sla_variance_hours, is_sla_breached, is_repeat_incident, satisfaction_rating
                )
                SELECT 
                    r.ticket_number,
                    CAST(TO_CHAR(r.created_date, 'YYYYMMDD') AS INT),
                    CASE WHEN r.closed_date IS NOT NULL THEN CAST(TO_CHAR(r.closed_date, 'YYYYMMDD') AS INT) ELSE NULL END,
                    loc.location_key, rt.request_type_key, d.department_key, s.status_key,
                    r.created_date, r.closed_date,
                    CASE WHEN r.closed_date IS NOT NULL THEN ROUND(EXTRACT(EPOCH FROM (r.closed_date - r.created_date))::numeric / 3600.0, 2) ELSE NULL END,
                    r.target_sla_hours,
                    CASE WHEN r.closed_date IS NOT NULL THEN ROUND((EXTRACT(EPOCH FROM (r.closed_date - r.created_date))::numeric / 3600.0) - r.target_sla_hours, 2) ELSE NULL END,
                    CASE WHEN r.closed_date IS NOT NULL AND (EXTRACT(EPOCH FROM (r.closed_date - r.created_date))::numeric / 3600.0) > r.target_sla_hours THEN TRUE ELSE FALSE END,
                    COALESCE(r.is_repeat, FALSE), r.satisfaction_rating
                FROM {staging_tbl} r
                JOIN dw.dim_location loc ON r.district_code = loc.district_code AND r.neighborhood = loc.neighborhood
                JOIN dw.dim_request_type rt ON r.request_category = rt.request_category AND r.request_type = rt.request_type_name AND r.priority_level = rt.priority_level
                JOIN dw.dim_department d ON r.department_name = d.department_name AND r.division_name = d.division_name
                JOIN dw.dim_status s ON r.status = s.status_name;
            """))
    else:
        # SQLite Engine Transformation
        with engine.begin() as conn:
            df_stg = pd.read_sql(f"SELECT * FROM {staging_tbl};", con=conn)
            
            # Min/Max dates
            min_dt = df_stg["created_date"].min()
            max_dt = df_stg["created_date"].max()
            populate_date_dimension(conn, min_dt, max_dt, dialect="sqlite")

            # Location dim
            df_loc = df_stg.groupby(["district_code", "neighborhood", "zip_code"]).agg(
                latitude=("latitude", "mean"),
                longitude=("longitude", "mean")
            ).reset_index()
            df_loc["location_key"] = range(1, len(df_loc) + 1)
            df_loc["region_zone"] = df_loc["district_code"].apply(lambda d: "North Region" if d in ["DIST-01", "DIST-02"] else "South Region")
            df_loc.to_sql("dw_dim_location", con=conn, if_exists="replace", index=False)

            # Request Type dim
            df_rt = df_stg.groupby(["request_category", "request_type", "priority_level"]).agg(
                default_sla_hours=("target_sla_hours", "mean")
            ).reset_index()
            df_rt.rename(columns={"request_type": "request_type_name"}, inplace=True)
            df_rt["request_type_key"] = range(1, len(df_rt) + 1)
            df_rt.to_sql("dw_dim_request_type", con=conn, if_exists="replace", index=False)

            # Department dim
            df_dept = df_stg.groupby(["department_name", "division_name"]).size().reset_index().drop(columns=[0])
            df_dept["department_key"] = range(1, len(df_dept) + 1)
            df_dept["department_head"] = "Dept Director"
            df_dept["team_capacity"] = 30
            df_dept.to_sql("dw_dim_department", con=conn, if_exists="replace", index=False)

            # Status dim
            df_status = df_stg[["status"]].drop_duplicates()
            df_status.rename(columns={"status": "status_name"}, inplace=True)
            df_status["status_key"] = range(1, len(df_status) + 1)
            df_status["is_closed"] = df_status["status_name"].str.startswith("Closed")
            df_status["is_active"] = ~df_status["is_closed"]
            df_status.to_sql("dw_dim_status", con=conn, if_exists="replace", index=False)

            # Fact table transformation
            df_fact = df_stg.copy()
            df_fact["created_dt"] = pd.to_datetime(df_fact["created_date"])
            df_fact["closed_dt"] = pd.to_datetime(df_fact["closed_date"])
            
            df_fact["created_date_key"] = df_fact["created_dt"].dt.strftime("%Y%m%d").astype(int)
            df_fact["closed_date_key"] = df_fact["closed_dt"].dt.strftime("%Y%m%d").fillna(-1).astype(int)

            df_fact["resolution_time_hours"] = (df_fact["closed_dt"] - df_fact["created_dt"]).dt.total_seconds() / 3600.0
            df_fact["resolution_time_hours"] = df_fact["resolution_time_hours"].round(2)

            df_fact["sla_variance_hours"] = (df_fact["resolution_time_hours"] - df_fact["target_sla_hours"]).round(2)
            df_fact["is_sla_breached"] = df_fact["resolution_time_hours"] > df_fact["target_sla_hours"]
            df_fact["is_repeat_incident"] = df_fact["is_repeat"].fillna(False)

            # Join keys
            df_fact = df_fact.merge(df_loc[["district_code", "neighborhood", "location_key"]], on=["district_code", "neighborhood"], how="left")
            df_fact = df_fact.merge(df_rt[["request_category", "request_type_name", "priority_level", "request_type_key"]], left_on=["request_category", "request_type", "priority_level"], right_on=["request_category", "request_type_name", "priority_level"], how="left")
            df_fact = df_fact.merge(df_dept[["department_name", "division_name", "department_key"]], on=["department_name", "division_name"], how="left")
            df_fact = df_fact.merge(df_status[["status_name", "status_key"]], left_on="status", right_on="status_name", how="left")

            fact_cols = [
                "ticket_number", "created_date_key", "closed_date_key", "location_key",
                "request_type_key", "department_key", "status_key", "created_date", "closed_date",
                "resolution_time_hours", "target_sla_hours", "sla_variance_hours", "is_sla_breached",
                "is_repeat_incident", "satisfaction_rating"
            ]
            df_fact[fact_cols].to_sql("dw_fact_service_requests", con=conn, if_exists="replace", index=False)

    print("✅ Star Schema Transformations Completed Successfully!")
