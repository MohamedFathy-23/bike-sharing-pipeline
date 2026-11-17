-- Reporting views for the analytical questions (see docs/Phase1_Proposal.pdf)
-- Q1: vw_hourly_demand | Q2: vw_weather_impact | Q3: vw_monthly_growth + vw_seasonal_demand

-- Q1: hourly demand by day type
CREATE OR REPLACE VIEW marts.vw_hourly_demand AS
SELECT
    f.hour_of_day,
    CASE
        WHEN d.is_holiday     THEN 'Holiday'
        WHEN d.is_working_day THEN 'Working day'
        ELSE 'Weekend'
    END AS day_type,
    ROUND(AVG(f.total_rentals), 1) AS avg_rentals,
    COUNT(*)                       AS hours_observed
FROM core.fact_rentals f
JOIN core.dim_date d USING (date_key)
GROUP BY 1, 2;

-- Q2: weather and temperature impact by user type
-- hours_observed shows how many hours sit behind each average; weather category 4 has only 3 records,
-- so groups with few hours should not support broad conclusions.
CREATE OR REPLACE VIEW marts.vw_weather_impact AS
SELECT
    w.weather_label,
    CASE
        WHEN f.temperature_c < 10 THEN '1 - Cold (below 10 C)'
        WHEN f.temperature_c < 20 THEN '2 - Mild (10 to 20 C)'
        WHEN f.temperature_c < 30 THEN '3 - Warm (20 to 30 C)'
        ELSE '4 - Hot (30 C and above)'
    END AS temp_band,
    ROUND(AVG(f.casual), 1)        AS avg_casual,
    ROUND(AVG(f.registered), 1)    AS avg_registered,
    ROUND(AVG(f.total_rentals), 1) AS avg_total,
    COUNT(*)                       AS hours_observed
FROM core.fact_rentals f
JOIN core.dim_weather w USING (weather_key)
GROUP BY 1, 2;

-- Q3 (monthly demand, user mix, growth): monthly totals, user mix and year-over-year growth
CREATE OR REPLACE VIEW marts.vw_monthly_growth AS
WITH monthly AS (
    SELECT
        d.calendar_year,
        d.calendar_month,
        SUM(f.casual)        AS casual_rentals,
        SUM(f.registered)    AS registered_rentals,
        SUM(f.total_rentals) AS total_rentals
    FROM core.fact_rentals f
    JOIN core.dim_date d USING (date_key)
    GROUP BY d.calendar_year, d.calendar_month
)
SELECT
    calendar_year,
    calendar_month,
    casual_rentals,
    registered_rentals,
    total_rentals,
    ROUND(100.0 * registered_rentals / NULLIF(total_rentals, 0), 1) AS registered_share_pct,
    ROUND(
        100.0 * (total_rentals - LAG(total_rentals, 12) OVER (ORDER BY calendar_year, calendar_month))
        / NULLIF(LAG(total_rentals, 12) OVER (ORDER BY calendar_year, calendar_month), 0),
    1) AS yoy_growth_pct
FROM monthly;

-- Q3 (seasonal pattern): season codes change partway through a month, so seasons get their own view
CREATE OR REPLACE VIEW marts.vw_seasonal_demand AS
SELECT
    d.calendar_year,
    d.season_code,
    d.season_name,
    SUM(f.casual)                   AS casual_rentals,
    SUM(f.registered)               AS registered_rentals,
    SUM(f.total_rentals)            AS total_rentals,
    ROUND(AVG(f.total_rentals), 1)  AS avg_hourly_rentals,
    ROUND(100.0 * SUM(f.registered) / NULLIF(SUM(f.total_rentals), 0), 1) AS registered_share_pct,
    COUNT(*)                        AS hours_observed
FROM core.fact_rentals f
JOIN core.dim_date d USING (date_key)
GROUP BY d.calendar_year, d.season_code, d.season_name;
