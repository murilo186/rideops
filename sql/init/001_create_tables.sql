CREATE TABLE IF NOT EXISTS rides (
    ride_id VARCHAR(20) PRIMARY KEY,

    requested_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,

    city VARCHAR(100) NOT NULL CHECK (city = 'São Paulo'),
    origin_neighborhood VARCHAR(100) NOT NULL,
    destination_neighborhood VARCHAR(100) NOT NULL,

    passenger_id VARCHAR(20) NOT NULL,
    driver_id VARCHAR(20) NOT NULL,

    category VARCHAR(20) NOT NULL
        CHECK (category IN ('econômica', 'conforto', 'premium')),

    status VARCHAR(30) NOT NULL
        CHECK (status IN (
            'concluída',
            'cancelada_passageiro',
            'cancelada_motorista'
        )),

    wait_minutes INTEGER NOT NULL CHECK (wait_minutes >= 0),

    payment_method VARCHAR(30) NOT NULL,

    cancellation_reason VARCHAR(100),

    distance_km NUMERIC(6, 2)
        CHECK (distance_km >= 0),

    duration_minutes INTEGER
        CHECK (duration_minutes >= 0),

    fare_brl NUMERIC(10, 2)
        CHECK (fare_brl >= 0),

    driver_rating NUMERIC(2, 1)
        CHECK (driver_rating BETWEEN 1 AND 5),

    CHECK (origin_neighborhood <> destination_neighborhood),

    CHECK (
        (status = 'concluída'
            AND started_at IS NOT NULL
            AND finished_at IS NOT NULL
            AND distance_km IS NOT NULL
            AND duration_minutes IS NOT NULL
            AND fare_brl IS NOT NULL
            AND driver_rating IS NOT NULL
            AND cancellation_reason IS NULL)
        OR
        (status IN ('cancelada_passageiro', 'cancelada_motorista')
            AND started_at IS NULL
            AND finished_at IS NULL
            AND distance_km IS NULL
            AND duration_minutes IS NULL
            AND fare_brl IS NULL
            AND driver_rating IS NULL
            AND cancellation_reason IS NOT NULL)
    ),

    CHECK (started_at IS NULL OR started_at >= requested_at),
    CHECK (finished_at IS NULL OR finished_at >= started_at)
);