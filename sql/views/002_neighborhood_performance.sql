CREATE OR REPLACE VIEW vw_neighborhood_performance AS
WITH neighborhood_rides AS (
    SELECT
        ride_date,
        origin_neighborhood AS neighborhood,
        'origem' AS neighborhood_role,
        status,
        fare_brl,
        wait_minutes
    FROM rides

    UNION ALL

    SELECT
        ride_date,
        destination_neighborhood AS neighborhood,
        'destino' AS neighborhood_role,
        status,
        fare_brl,
        wait_minutes
    FROM rides
)
SELECT
    ride_date,
    neighborhood,
    neighborhood_role,
    COUNT(*) AS total_requests,
    COUNT(*) FILTER (WHERE status = 'concluída') AS completed_rides,
    COUNT(*) FILTER (
        WHERE status IN ('cancelada_passageiro', 'cancelada_motorista')
    ) AS cancelled_rides,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE status IN ('cancelada_passageiro', 'cancelada_motorista')
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_rate_pct,
    ROUND(COALESCE(SUM(fare_brl), 0), 2) AS revenue_brl,
    ROUND(AVG(wait_minutes), 2) AS avg_wait_minutes
FROM neighborhood_rides
GROUP BY ride_date, neighborhood, neighborhood_role;
