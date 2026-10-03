-- Analytical SQL Views for Operations KPI Reporting
-- Schema: marts

-- 1. Operational Overview KPI Summary
CREATE OR REPLACE VIEW marts.vw_kpi_operational_overview AS
SELECT 
    COUNT(f.fact_id) AS total_requests,
    COUNT(CASE WHEN s.is_closed THEN 1 END) AS total_closed_requests,
    COUNT(CASE WHEN NOT s.is_closed THEN 1 END) AS current_backlog,
    ROUND(AVG(f.resolution_time_hours), 2) AS avg_resolution_hours,
    ROUND(AVG(f.satisfaction_rating), 2) AS avg_satisfaction_rating,
    COUNT(CASE WHEN f.is_sla_breached THEN 1 END) AS total_sla_breaches,
    ROUND(
        100.0 * COUNT(CASE WHEN NOT f.is_sla_breached AND s.is_closed THEN 1 END) / 
        NULLIF(COUNT(CASE WHEN s.is_closed THEN 1 END), 0), 2
    ) AS sla_compliance_pct,
    COUNT(CASE WHEN f.is_repeat_incident THEN 1 END) AS total_repeat_incidents,
    ROUND(
        100.0 * COUNT(CASE WHEN f.is_repeat_incident THEN 1 END) / NULLIF(COUNT(f.fact_id), 0), 2
    ) AS repeat_incident_pct
FROM dw.fact_service_requests f
JOIN dw.dim_status s ON f.status_key = s.status_key;

-- 2. Department Workload & Resolution Metrics
CREATE OR REPLACE VIEW marts.vw_kpi_department_performance AS
SELECT 
    d.department_name,
    d.division_name,
    COUNT(f.fact_id) AS total_tickets,
    COUNT(CASE WHEN s.is_closed THEN 1 END) AS closed_tickets,
    COUNT(CASE WHEN NOT s.is_closed THEN 1 END) AS open_backlog,
    ROUND(AVG(f.resolution_time_hours), 2) AS avg_resolution_hours,
    ROUND(AVG(f.target_sla_hours), 2) AS avg_target_sla_hours,
    COUNT(CASE WHEN f.is_sla_breached THEN 1 END) AS sla_breach_count,
    ROUND(
        100.0 * COUNT(CASE WHEN NOT f.is_sla_breached AND s.is_closed THEN 1 END) / 
        NULLIF(COUNT(CASE WHEN s.is_closed THEN 1 END), 0), 2
    ) AS sla_compliance_pct,
    ROUND(AVG(f.satisfaction_rating), 2) AS avg_satisfaction,
    DENSE_RANK() OVER (ORDER BY COUNT(f.fact_id) DESC) AS workload_rank
FROM dw.fact_service_requests f
JOIN dw.dim_department d ON f.department_key = d.department_key
JOIN dw.dim_status s ON f.status_key = s.status_key
GROUP BY d.department_name, d.division_name;

-- 3. Monthly Trends & MoM Growth (Window Functions)
CREATE OR REPLACE VIEW marts.vw_kpi_monthly_trends AS
WITH monthly_summary AS (
    SELECT 
        dt.year,
        dt.month,
        dt.month_name,
        dt.year || '-' || LPAD(dt.month::text, 2, '0') AS year_month,
        COUNT(f.fact_id) AS ticket_volume,
        COUNT(CASE WHEN f.is_sla_breached THEN 1 END) AS sla_breaches,
        ROUND(AVG(f.resolution_time_hours), 2) AS avg_resolution_hours
    FROM dw.fact_service_requests f
    JOIN dw.dim_date dt ON f.created_date_key = dt.date_key
    GROUP BY dt.year, dt.month, dt.month_name
)
SELECT 
    year_month,
    year,
    month,
    month_name,
    ticket_volume,
    LAG(ticket_volume, 1) OVER (ORDER BY year, month) AS prev_month_volume,
    ROUND(
        100.0 * (ticket_volume - LAG(ticket_volume, 1) OVER (ORDER BY year, month)) / 
        NULLIF(LAG(ticket_volume, 1) OVER (ORDER BY year, month), 0), 2
    ) AS mom_volume_growth_pct,
    avg_resolution_hours,
    sla_breaches
FROM monthly_summary
ORDER BY year, month;

-- 4. Geographic & District Heatmap Metrics
CREATE OR REPLACE VIEW marts.vw_kpi_geographic_distribution AS
SELECT 
    loc.district_code,
    loc.neighborhood,
    loc.region_zone,
    COUNT(f.fact_id) AS total_requests,
    COUNT(CASE WHEN f.is_sla_breached THEN 1 END) AS sla_breaches,
    ROUND(AVG(f.resolution_time_hours), 2) AS avg_resolution_hours,
    COUNT(CASE WHEN f.is_repeat_incident THEN 1 END) AS repeat_count,
    ROUND(AVG(loc.latitude), 6) AS district_lat,
    ROUND(AVG(loc.longitude), 6) AS district_lng
FROM dw.fact_service_requests f
JOIN dw.dim_location loc ON f.location_key = loc.location_key
GROUP BY loc.district_code, loc.neighborhood, loc.region_zone
ORDER BY total_requests DESC;

-- 5. Category Breakdown & Priority Distribution
CREATE OR REPLACE VIEW marts.vw_kpi_category_breakdown AS
SELECT 
    rt.request_category,
    rt.request_type_name,
    rt.priority_level,
    COUNT(f.fact_id) AS request_count,
    ROUND(AVG(f.resolution_time_hours), 2) AS avg_resolution_hours,
    COUNT(CASE WHEN f.is_sla_breached THEN 1 END) AS sla_breached_count,
    ROUND(
        100.0 * COUNT(CASE WHEN f.is_sla_breached THEN 1 END) / NULLIF(COUNT(f.fact_id), 0), 2
    ) AS breach_rate_pct
FROM dw.fact_service_requests f
JOIN dw.dim_request_type rt ON f.request_type_key = rt.request_type_key
GROUP BY rt.request_category, rt.request_type_name, rt.priority_level
ORDER BY request_count DESC;

-- 6. Backlog Aging Analysis (Open Tickets)
CREATE OR REPLACE VIEW marts.vw_kpi_backlog_aging AS
SELECT 
    d.department_name,
    rt.request_category,
    COUNT(f.fact_id) AS total_backlog_tickets,
    COUNT(CASE WHEN (CURRENT_DATE - dt.full_date) <= 3 THEN 1 END) AS aging_0_to_3_days,
    COUNT(CASE WHEN (CURRENT_DATE - dt.full_date) BETWEEN 4 AND 7 THEN 1 END) AS aging_4_to_7_days,
    COUNT(CASE WHEN (CURRENT_DATE - dt.full_date) BETWEEN 8 AND 14 THEN 1 END) AS aging_8_to_14_days,
    COUNT(CASE WHEN (CURRENT_DATE - dt.full_date) > 14 THEN 1 END) AS aging_over_14_days,
    MAX(CURRENT_DATE - dt.full_date) AS max_open_days
FROM dw.fact_service_requests f
JOIN dw.dim_status s ON f.status_key = s.status_key
JOIN dw.dim_department d ON f.department_key = d.department_key
JOIN dw.dim_request_type rt ON f.request_type_key = rt.request_type_key
JOIN dw.dim_date dt ON f.created_date_key = dt.date_key
WHERE NOT s.is_closed
GROUP BY d.department_name, rt.request_category;
