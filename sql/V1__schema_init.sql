-- Operations Analytics Warehouse SQL Schema
-- Target: PostgreSQL 14+

-- 1. Create Schemas
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS dw;
CREATE SCHEMA IF NOT EXISTS marts;

-- 2. Staging Table (Raw Ingestion Target)
DROP TABLE IF EXISTS staging.raw_service_requests CASCADE;
CREATE TABLE staging.raw_service_requests (
    raw_id SERIAL PRIMARY KEY,
    ticket_number VARCHAR(50),
    created_date TIMESTAMP,
    closed_date TIMESTAMP,
    target_sla_hours NUMERIC(10,2),
    department_name VARCHAR(100),
    division_name VARCHAR(100),
    request_category VARCHAR(100),
    request_type VARCHAR(150),
    priority_level VARCHAR(20),
    status VARCHAR(50),
    district_code VARCHAR(20),
    neighborhood VARCHAR(100),
    zip_code VARCHAR(20),
    latitude NUMERIC(10,6),
    longitude NUMERIC(10,6),
    satisfaction_rating INT,
    is_repeat BOOLEAN,
    channel VARCHAR(50),
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Star Schema Dimension Tables
DROP TABLE IF EXISTS dw.fact_service_requests CASCADE;
DROP TABLE IF EXISTS dw.dim_date CASCADE;
DROP TABLE IF EXISTS dw.dim_location CASCADE;
DROP TABLE IF EXISTS dw.dim_request_type CASCADE;
DROP TABLE IF EXISTS dw.dim_department CASCADE;
DROP TABLE IF EXISTS dw.dim_status CASCADE;

CREATE TABLE dw.dim_date (
    date_key INT PRIMARY KEY, -- YYYYMMDD
    full_date DATE NOT NULL UNIQUE,
    year INT NOT NULL,
    quarter INT NOT NULL,
    quarter_name VARCHAR(10) NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    day_of_month INT NOT NULL,
    day_of_week INT NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    fiscal_year INT NOT NULL,
    fiscal_quarter INT NOT NULL
);

CREATE TABLE dw.dim_location (
    location_key SERIAL PRIMARY KEY,
    district_code VARCHAR(20) NOT NULL,
    neighborhood VARCHAR(100) NOT NULL,
    zip_code VARCHAR(20),
    latitude NUMERIC(10,6),
    longitude NUMERIC(10,6),
    region_zone VARCHAR(50) NOT NULL,
    CONSTRAINT idx_location_unique UNIQUE(district_code, neighborhood)
);

CREATE TABLE dw.dim_request_type (
    request_type_key SERIAL PRIMARY KEY,
    request_category VARCHAR(100) NOT NULL,
    request_type_name VARCHAR(150) NOT NULL,
    priority_level VARCHAR(20) NOT NULL,
    default_sla_hours NUMERIC(10,2) NOT NULL,
    CONSTRAINT idx_reqtype_unique UNIQUE(request_category, request_type_name, priority_level)
);

CREATE TABLE dw.dim_department (
    department_key SERIAL PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL,
    division_name VARCHAR(100) NOT NULL,
    department_head VARCHAR(100),
    team_capacity INT,
    CONSTRAINT idx_dept_unique UNIQUE(department_name, division_name)
);

CREATE TABLE dw.dim_status (
    status_key SERIAL PRIMARY KEY,
    status_name VARCHAR(50) NOT NULL UNIQUE,
    is_closed BOOLEAN NOT NULL,
    is_active BOOLEAN NOT NULL
);

-- 4. Star Schema Fact Table
CREATE TABLE dw.fact_service_requests (
    fact_id SERIAL PRIMARY KEY,
    ticket_number VARCHAR(50) UNIQUE NOT NULL,
    created_date_key INT NOT NULL REFERENCES dw.dim_date(date_key),
    closed_date_key INT REFERENCES dw.dim_date(date_key),
    location_key INT NOT NULL REFERENCES dw.dim_location(location_key),
    request_type_key INT NOT NULL REFERENCES dw.dim_request_type(request_type_key),
    department_key INT NOT NULL REFERENCES dw.dim_department(department_key),
    status_key INT NOT NULL REFERENCES dw.dim_status(status_key),
    
    created_timestamp TIMESTAMP NOT NULL,
    closed_timestamp TIMESTAMP,
    
    -- Metrics
    resolution_time_hours NUMERIC(10,2),
    target_sla_hours NUMERIC(10,2) NOT NULL,
    sla_variance_hours NUMERIC(10,2),
    is_sla_breached BOOLEAN NOT NULL DEFAULT FALSE,
    is_repeat_incident BOOLEAN NOT NULL DEFAULT FALSE,
    satisfaction_rating INT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for DW Performance
CREATE INDEX idx_fact_created_date ON dw.fact_service_requests(created_date_key);
CREATE INDEX idx_fact_dept ON dw.fact_service_requests(department_key);
CREATE INDEX idx_fact_location ON dw.fact_service_requests(location_key);
CREATE INDEX idx_fact_reqtype ON dw.fact_service_requests(request_type_key);
CREATE INDEX idx_fact_status ON dw.fact_service_requests(status_key);
CREATE INDEX idx_fact_sla ON dw.fact_service_requests(is_sla_breached);
