CREATE OR REPLACE VIEW vw_driver_quality AS
SELECT
    driver_id,
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
    ROUND(AVG(driver_rating) FILTER (WHERE status = 'concluída'), 2) AS avg_driver_rating,
    ROUND(AVG(wait_minutes), 2) AS avg_wait_minutes,
    ROUND(AVG(fare_brl) FILTER (WHERE status = 'concluída'), 2) AS avg_fare_brl
FROM rides
GROUP BY driver_id;
