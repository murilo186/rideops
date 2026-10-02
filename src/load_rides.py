from __future__ import annotations

import argparse
import os
from collections.abc import Iterator
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import URL, create_engine


PROCESSED_COLUMNS = [
    "ride_id",
    "requested_at",
    "city",
    "origin_neighborhood",
    "destination_neighborhood",
    "passenger_id",
    "driver_id",
    "category",
    "status",
    "wait_minutes",
    "payment_method",
    "cancellation_reason",
    "started_at",
    "finished_at",
    "distance_km",
    "duration_minutes",
    "fare_brl",
    "driver_rating",
    "ride_date",
    "request_hour",
    "request_weekday",
    "is_peak_hour",
    "fare_per_km",
]
DATE_COLUMNS = ["requested_at", "started_at", "finished_at"]
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Carrega corridas no PostgreSQL.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/rides.csv"),
        help="Caminho do CSV tratado.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=100_000,
        help="Quantidade de corridas carregadas por lote.",
    )
    return parser


def database_url() -> URL:
    return URL.create(
        "postgresql+psycopg",
        username=os.environ.get("POSTGRES_USER", "rideops"),
        password=os.environ.get("POSTGRES_PASSWORD"),
        host=os.environ.get("DB_HOST", "postgres"),
        port=int(os.environ.get("DB_PORT", "5432")),
        database=os.environ.get("POSTGRES_DB", "rideops"),
    )


def validate_processed_rides(rides: pd.DataFrame) -> pd.DataFrame:
    if list(rides.columns) != PROCESSED_COLUMNS:
        raise ValueError("As colunas do CSV não correspondem à estrutura tratada esperada.")
    rides["ride_date"] = pd.to_datetime(rides["ride_date"], format="%Y-%m-%d", errors="coerce").dt.date
    if rides.empty:
        raise ValueError("O CSV não possui corridas para carregar.")
    if not rides["ride_id"].is_unique:
        raise ValueError("O CSV possui ride_id duplicado.")

    completed = rides["status"].eq("concluída")
    if rides.loc[completed, ["started_at", "finished_at", "fare_brl"]].isna().any().any():
        raise ValueError("Há corrida concluída sem horários ou valor.")
    if rides.loc[~completed, "cancellation_reason"].isna().any():
        raise ValueError("Há corrida cancelada sem motivo de cancelamento.")
    if rides["ride_date"].isna().any() or rides["request_hour"].isna().any():
        raise ValueError("Há atributos de tempo ausentes no CSV tratado.")
    if not rides["request_hour"].between(0, 23).all():
        raise ValueError("Há hora de solicitação inválida no CSV tratado.")
    if rides.loc[completed, "fare_per_km"].isna().any():
        raise ValueError("Há corrida concluída sem valor por quilômetro.")

    return rides.where(pd.notna(rides), None)


def read_and_validate_rides(input_path: Path) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")
    return validate_processed_rides(pd.read_csv(input_path, parse_dates=DATE_COLUMNS))


def read_processed_chunks(input_path: Path, chunk_size: int) -> Iterator[pd.DataFrame]:
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")
    if chunk_size <= 0:
        raise ValueError("O tamanho do lote deve ser maior que zero.")

    for rides in pd.read_csv(input_path, parse_dates=DATE_COLUMNS, chunksize=chunk_size):
        yield validate_processed_rides(rides)


def rides_to_csv(rides: pd.DataFrame) -> str:
    buffer = StringIO()
    rides.to_csv(buffer, index=False, header=False, na_rep="", date_format="%Y-%m-%d %H:%M:%S")
    return buffer.getvalue()


def append_rides(connection: Any, rides: pd.DataFrame) -> None:
    columns = ", ".join(PROCESSED_COLUMNS)
    copy_sql = f"COPY rides ({columns}) FROM STDIN WITH (FORMAT CSV, NULL '')"
    with connection.cursor() as cursor:
        with cursor.copy(copy_sql) as copy:
            copy.write(rides_to_csv(rides))


def load_rides_chunks(rides_chunks: Iterator[pd.DataFrame]) -> int:
    engine = create_engine(database_url())
    connection = engine.raw_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE rides")
        loaded = 0
        for rides in rides_chunks:
            append_rides(connection, rides)
            loaded += len(rides)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
        engine.dispose()
    return loaded


def load_rides(rides: pd.DataFrame) -> int:
    return load_rides_chunks(iter([rides]))


def main() -> None:
    args = build_parser().parse_args()
    count = load_rides_chunks(read_processed_chunks(args.input, args.chunk_size))
    print(f"{count:,} corridas carregadas na tabela rides.")


if __name__ == "__main__":
    main()
