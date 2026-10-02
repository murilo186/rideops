ALTER TABLE rides
    ADD COLUMN IF NOT EXISTS ride_date DATE,
    ADD COLUMN IF NOT EXISTS request_hour SMALLINT CHECK (request_hour BETWEEN 0 AND 23),
    ADD COLUMN IF NOT EXISTS request_weekday VARCHAR(20),
    ADD COLUMN IF NOT EXISTS is_peak_hour BOOLEAN,
    ADD COLUMN IF NOT EXISTS fare_per_km NUMERIC(10, 2) CHECK (fare_per_km >= 0);
