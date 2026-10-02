from pathlib import Path

import pytest

from generate_rides import generate_rides
from load_rides import read_and_validate_rides, read_processed_chunks
from transform_rides import transform_rides


def test_reads_processed_file(tmp_path: Path) -> None:
    input_path = tmp_path / "rides_processed.csv"
    transform_rides(generate_rides(rows=20, seed=42)).to_csv(input_path, index=False)

    rides = read_and_validate_rides(input_path)

    assert len(rides) == 20
    assert "fare_per_km" in rides.columns


def test_rejects_raw_file(tmp_path: Path) -> None:
    input_path = tmp_path / "rides_raw.csv"
    generate_rides(rows=20, seed=42).to_csv(input_path, index=False)

    with pytest.raises(ValueError, match="estrutura tratada"):
        read_and_validate_rides(input_path)


def test_reads_processed_file_in_chunks(tmp_path: Path) -> None:
    input_path = tmp_path / "rides_processed.csv"
    transform_rides(generate_rides(rows=20, seed=42)).to_csv(input_path, index=False)

    chunks = list(read_processed_chunks(input_path, chunk_size=7))

    assert [len(chunk) for chunk in chunks] == [7, 7, 6]
    assert all("fare_per_km" in chunk for chunk in chunks)
