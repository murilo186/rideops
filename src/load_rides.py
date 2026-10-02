from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import Boolean, Date, Numeric, SmallInteger, URL, create_engine, text


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
DATABASE_TYPES = {
    "ride_date": Date(),
    "request_hour": SmallInteger(),
    "is_peak_hour": Boolean(),
    "fare_per_km": Numeric(10, 2),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Carrega corridas no PostgreSQL.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/rides.csv"),
        help="Caminho do CSV tratado.",
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


def read_and_validate_rides(input_path: Path) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")

    rides = pd.read_csv(input_path, parse_dates=DATE_COLUMNS)
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


def load_rides(rides: pd.DataFrame) -> int:
    engine = create_engine(database_url())
    try:
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE TABLE rides"))
            rides.to_sql(
                "rides",
                con=connection,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=1_000,
                dtype=DATABASE_TYPES,
            )
    finally:
        engine.dispose()
    return len(rides)


def main() -> None:
    args = build_parser().parse_args()
    rides = read_and_validate_rides(args.input)
    count = load_rides(rides)
    print(f"{count:,} corridas carregadas na tabela rides.")


if __name__ == "__main__":
    main()
