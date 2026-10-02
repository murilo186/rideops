from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from generate_rides import CITY, generate_rides  # noqa: E402


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
