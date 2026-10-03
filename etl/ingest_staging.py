"""
Staging Ingestion Module.
Ingests raw/cleaned operational pandas DataFrame into staging schema.
Supports PostgreSQL and SQLite database fallbacks.
"""

import os
import pandas as pd
from sqlalchemy import create_engine, text

def get_db_engine():
    """Retrieve database engine (PostgreSQL if available, SQLite file fallback)."""
    db_user = os.environ.get("POSTGRES_USER", "postgres")
    db_pass = os.environ.get("POSTGRES_PASSWORD", "postgres")
    db_host = os.environ.get("POSTGRES_HOST", "localhost")
    db_port = os.environ.get("POSTGRES_PORT", "5432")
    db_name = os.environ.get("POSTGRES_DB", "analytics_db")
    
    pg_url = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    
    try:
        engine = create_engine(pg_url, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        return engine, "postgresql"
    except Exception as e:
        print(f"⚠️ PostgreSQL connection unavailable ({e}). Using SQLite Data Warehouse fallback.")
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(data_dir, exist_ok=True)
        sqlite_path = os.path.join(data_dir, "analytics_db.sqlite")
        sqlite_url = f"sqlite:///{sqlite_path}"
        engine = create_engine(sqlite_url)
        return engine, "sqlite"

def ingest_to_staging(df: pd.DataFrame, engine, dialect: str = "postgresql") -> int:
    """Load cleaned DataFrame into staging table."""
    table_name = "raw_service_requests"
    schema_name = "staging" if dialect == "postgresql" else None
    
    if dialect == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE staging.raw_service_requests CASCADE;"))
    else:
        # SQLite
        table_name = "staging_raw_service_requests"

    if_exists_mode = "append" if dialect == "postgresql" else "replace"

    df.to_sql(
        name=table_name,
        con=engine,
        schema=schema_name,
        if_exists=if_exists_mode,
        index=False
    )
    
    print(f"✅ Ingested {len(df)} records into {schema_name + '.' if schema_name else ''}{table_name}")
    return len(df)
