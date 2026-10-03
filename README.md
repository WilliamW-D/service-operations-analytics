# Service Operations Analytics Warehouse 📊

[![Operations Analytics CI](https://github.com/WilliamW-D/service-operations-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/WilliamW-D/service-operations-analytics/actions)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11+-green.svg)
![Star Schema](https://img.shields.io/badge/Data%20Warehouse-Star%20Schema-purple.svg)

An end-to-end **Operations & SLA Data Analytics Warehouse** designed to model, clean, transform, and analyze high-volume municipal 311 service request and operational incident data.

This project demonstrates production-grade **Data Engineering & Analytics Architecture**:
- **Python ETL & Data Quality Engine**: Synthetic data generation, automated null/range/timestamp auditing, and deduplication.
- **PostgreSQL Star Schema Data Warehouse**: 1 central Fact table (`fact_service_requests`) and 5 Dimension tables (`dim_date`, `dim_location`, `dim_request_type`, `dim_department`, `dim_status`).
- **Advanced SQL Analytical Marts**: Analytical views utilizing SQL window functions (`LAG`, `DENSE_RANK`), CTEs, and conditional aggregations (`FILTER`) for MoM growth, SLA compliance, backlog aging, and repeat incident heatmaps.
- **Interactive Executive Glassmorphism BI Dashboard**: Modern dashboard replicating Power BI / Tableau drill-downs, dynamic filtering, KPI cards, and trend visualizations.
- **CI/CD & Docker Orchestration**: Containerized PostgreSQL 16 DB with automated GitHub Actions CI testing pipeline.

---

## 🏗 Architecture & Data Flow

```
Raw Operational Data (311 / Incidents)
               │
               ▼
┌──────────────────────────────┐
│  Python Data Ingestion &     │  ──> Automated Data Quality Audits
│  Validation Engine           │      (Null checks, Range & Logic checks)
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   PostgreSQL Staging Layer   │  ──> staging.raw_service_requests
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   Star Schema DW Layer       │  ──> dw.fact_service_requests
│  (Dimensions & Fact Tables)  │      dw.dim_date, dw.dim_location, etc.
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│    Analytical KPI Marts      │  ──> marts.vw_kpi_operational_overview
│   (SQL Views & Aggregates)   │      marts.vw_kpi_monthly_trends, etc.
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Interactive BI Dashboard &   │  ──> Power BI / Tableau Desktop
│ Executive Web KPI View       │      Glassmorphism Web Dashboard
└──────────────────────────────┘
```

---

## 📐 Star Schema Data Model

The data warehouse implements a clean, optimized **Dimensional Model**:

### **Fact Table (`dw.fact_service_requests`)**
- `fact_id` (PK)
- `ticket_number` (Business Key)
- `created_date_key` (FK -> `dw.dim_date`)
- `closed_date_key` (FK -> `dw.dim_date`)
- `location_key` (FK -> `dw.dim_location`)
- `request_type_key` (FK -> `dw.dim_request_type`)
- `department_key` (FK -> `dw.dim_department`)
- `status_key` (FK -> `dw.dim_status`)
- **Measures**: `resolution_time_hours`, `target_sla_hours`, `sla_variance_hours`, `is_sla_breached`, `is_repeat_incident`, `satisfaction_rating`

### **Dimension Tables**
- **`dw.dim_date`**: Calendar date attributes (`year`, `quarter`, `month_name`, `day_of_week`, `fiscal_quarter`, `is_weekend`).
- **`dw.dim_location`**: Spatial hierarchy (`district_code`, `neighborhood`, `zip_code`, `latitude`, `longitude`, `region_zone`).
- **`dw.dim_request_type`**: Service catalog metadata (`request_category`, `request_type_name`, `priority_level`, `default_sla_hours`).
- **`dw.dim_department`**: Organizational hierarchy (`department_name`, `division_name`, `department_head`, `team_capacity`).
- **`dw.dim_status`**: Ticket lifecycle flags (`status_name`, `is_closed`, `is_active`).

---

## 📊 Analytical SQL Views & Key Metrics

The database exposes ready-to-query analytical views under the `marts` schema:

1. **`marts.vw_kpi_operational_overview`**: Top-level executive metrics (Total Incidents, SLA Compliance %, Backlog, Avg Resolution Hours).
2. **`marts.vw_kpi_department_performance`**: Department workload ranking (`DENSE_RANK() OVER (ORDER BY ticket_count DESC)`), resolution speed, and SLA compliance.
3. **`marts.vw_kpi_monthly_trends`**: Month-over-Month volume growth (`LAG() OVER (ORDER BY year, month)`), resolution trends, and SLA breach volume.
4. **`marts.vw_kpi_geographic_distribution`**: District/neighborhood request volume heatmaps and location incident density.
5. **`marts.vw_kpi_category_breakdown`**: Request category breakdown, priority distribution, and breach rates.
6. **`marts.vw_kpi_backlog_aging`**: Open incident aging matrix (`0-3 Days`, `4-7 Days`, `8-14 Days`, `>14 Days`).

---

## ⚡ Quickstart & Local Setup

### 1. Prerequisites
- **Python 3.11+**
- **Docker & Docker Compose** (or local PostgreSQL 14+)

### 2. Clone Repository & Install Python Environment
```bash
git clone https://github.com/WilliamW-D/service-operations-analytics.git
cd service-operations-analytics

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 3. Launch PostgreSQL 16 via Docker
```bash
docker-compose up -d
```

### 4. Execute Full Pipeline
```bash
python etl/main.py
```

### 5. Run Unit & Data Quality Tests
```bash
pytest tests/ -v
```

### 6. View Interactive Dashboard
Open `dashboard/index.html` in any modern web browser or serve via HTTP:
```bash
python -m http.server 8000 --directory dashboard
# Open http://localhost:8000
```

---

## 💼 Resume Highlights & Impact Statements

This repository supports the following **Data Analyst / Systems Analyst** resume bullet points:

- **Data Warehouse Engineering**: *"Designed a PostgreSQL star-schema analytics warehouse for operational service data, using Python ETL and SQL window functions to produce reusable KPI datasets for backlog, resolution time, workload, and trend analysis."*
- **BI & Performance Reporting**: *"Built an interactive Power BI / Web Dashboard with drill-down filters and documented KPI definitions to translate 5,000+ operational incidents into actionable performance insights."*
- **Data Quality & Governance**: *"Implemented automated Python data quality pipelines enforcing null rate constraints, logical timestamp validation, and deduplication prior to warehouse ingestion."*
