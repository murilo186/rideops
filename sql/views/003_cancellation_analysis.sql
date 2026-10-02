CREATE OR REPLACE VIEW vw_cancellation_analysis AS
WITH demand_by_slice AS (
    SELECT
        ride_date,
        request_hour,
        category,
        COUNT(*) AS total_requests
    FROM rides
    GROUP BY ride_date, request_hour, category
),
cancellations AS (
    SELECT
        ride_date,
        request_hour,
        category,
        status,
        cancellation_reason,
        COUNT(*) AS cancellation_count
    FROM rides
    WHERE status IN ('cancelada_passageiro', 'cancelada_motorista')
    GROUP BY ride_date, request_hour, category, status, cancellation_reason
)
SELECT
    cancellations.ride_date,
    cancellations.request_hour,
    cancellations.category,
    cancellations.status,
    cancellations.cancellation_reason,
    cancellations.cancellation_count,
    demand_by_slice.total_requests,
    ROUND(
        100.0 * cancellations.cancellation_count / NULLIF(demand_by_slice.total_requests, 0),
        2
    ) AS cancellation_rate_pct
FROM cancellations
JOIN demand_by_slice
    ON cancellations.ride_date = demand_by_slice.ride_date
    AND cancellations.request_hour = demand_by_slice.request_hour
    AND cancellations.category = demand_by_slice.category;
