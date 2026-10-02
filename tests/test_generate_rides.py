from pathlib import Path

import pandas as pd
import pytest

from generate_rides import CITY, entity_pool_size, generate_rides, generate_rides_chunks, write_rides


def test_generates_requested_number_of_rides() -> None:
    rides = generate_rides(rows=20, seed=7)

    assert len(rides) == 20
    assert rides["ride_id"].is_unique
    assert rides["city"].eq(CITY).all()
    assert rides["origin_neighborhood"].ne(rides["destination_neighborhood"]).all()


def test_completed_and_cancelled_rides_have_consistent_fields() -> None:
    rides = generate_rides(rows=200, seed=42)
    completed = rides[rides["status"] == "concluída"]
    cancelled = rides[rides["status"] != "concluída"]

    assert completed["finished_at"].notna().all()
    assert completed["fare_brl"].gt(0).all()
    assert cancelled["cancellation_reason"].notna().all()
    assert cancelled["fare_brl"].isna().all()


def test_rejects_non_positive_row_count() -> None:
    with pytest.raises(ValueError, match="maior que zero"):
        generate_rides(rows=0)


def test_generates_reproducible_chunks() -> None:
    chunks = list(generate_rides_chunks(rows=25, chunk_size=10, seed=7))
    rides = pd.concat(chunks, ignore_index=True)

    assert [len(chunk) for chunk in chunks] == [10, 10, 5]
    assert rides["ride_id"].tolist() == [f"RIDE-{number:07d}" for number in range(1, 26)]


def test_writes_rides_in_chunks(tmp_path: Path) -> None:
    output_path = tmp_path / "rides.csv"

    count = write_rides(rows=25, output_path=output_path, chunk_size=10, seed=7)
    saved = pd.read_csv(output_path)

    assert count == 25
    assert len(saved) == 25


def test_caps_entity_pools_for_large_generation() -> None:
    assert entity_pool_size(rows=3_000_000, ratio=10, maximum=20_000) == 20_000
