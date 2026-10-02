from pathlib import Path

import pandas as pd
import pytest

from generate_rides import generate_rides
from transform_rides import process_file, transform_rides


def test_adds_analytical_columns() -> None:
    treated = transform_rides(generate_rides(rows=100, seed=42))

    assert {"ride_date", "request_hour", "request_weekday", "is_peak_hour", "fare_per_km"}.issubset(treated.columns)
    assert treated["request_hour"].between(0, 23).all()
    assert treated.loc[treated["status"].eq("concluída"), "fare_per_km"].notna().all()
    assert treated.loc[treated["status"].ne("concluída"), "fare_per_km"].isna().all()


def test_rejects_duplicate_ride_ids() -> None:
    rides = generate_rides(rows=2, seed=42)
    rides.loc[1, "ride_id"] = rides.loc[0, "ride_id"]

    with pytest.raises(ValueError, match="ride_id único"):
        transform_rides(rides)


def test_writes_processed_file(tmp_path: Path) -> None:
    input_path = tmp_path / "rides_raw.csv"
    output_path = tmp_path / "rides_processed.csv"
    generate_rides(rows=10, seed=42).to_csv(input_path, index=False)

    count = process_file(input_path, output_path, chunk_size=3)
    saved = pd.read_csv(output_path)

    assert count == 10
    assert len(saved) == 10
    assert "is_peak_hour" in saved.columns
