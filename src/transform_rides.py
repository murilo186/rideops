from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


RAW_COLUMNS = [
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
]
DATE_COLUMNS = ["requested_at", "started_at", "finished_at"]
PEAK_HOURS = {7, 8, 9, 17, 18, 19}
WEEKDAYS = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Trata dados sintéticos de corridas.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw/rides.csv"),
        help="Caminho do CSV bruto.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/rides.csv"),
        help="Caminho do CSV tratado.",
    )
    return parser


def read_raw_rides(input_path: Path) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")
    return pd.read_csv(input_path, parse_dates=DATE_COLUMNS)


def validate_raw_rides(rides: pd.DataFrame) -> None:
    if list(rides.columns) != RAW_COLUMNS:
        raise ValueError("As colunas do CSV não correspondem à estrutura bruta esperada.")
    if rides.empty:
        raise ValueError("O CSV não possui corridas para tratar.")
    if rides["ride_id"].isna().any() or not rides["ride_id"].is_unique:
        raise ValueError("Cada corrida deve possuir um ride_id único.")
    if rides["requested_at"].isna().any():
        raise ValueError("Toda corrida deve possuir data de solicitação.")
    if not rides["city"].eq("São Paulo").all():
        raise ValueError("O tratamento aceita somente corridas de São Paulo.")
    if rides["origin_neighborhood"].eq(rides["destination_neighborhood"]).any():
        raise ValueError("Origem e destino não podem ser iguais.")
    if rides["wait_minutes"].lt(0).any():
        raise ValueError("O tempo de espera não pode ser negativo.")

    completed = rides["status"].eq("concluída")
    cancelled = rides["status"].isin({"cancelada_passageiro", "cancelada_motorista"})
    if (~(completed | cancelled)).any():
        raise ValueError("Há status de corrida inválido.")
    if rides.loc[completed, ["started_at", "finished_at", "distance_km", "duration_minutes", "fare_brl"]].isna().any().any():
        raise ValueError("Há corrida concluída com informações obrigatórias ausentes.")
    if rides.loc[cancelled, "cancellation_reason"].isna().any():
        raise ValueError("Há corrida cancelada sem motivo de cancelamento.")
    if rides.loc[cancelled, ["started_at", "finished_at", "distance_km", "duration_minutes", "fare_brl"]].notna().any().any():
        raise ValueError("Corridas canceladas não podem possuir dados de conclusão.")
    if (rides.loc[completed, "started_at"] < rides.loc[completed, "requested_at"]).any():
        raise ValueError("Há início anterior à solicitação da corrida.")
    if (rides.loc[completed, "finished_at"] < rides.loc[completed, "started_at"]).any():
        raise ValueError("Há fim anterior ao início da corrida.")
    if rides.loc[completed, ["distance_km", "duration_minutes", "fare_brl"]].lt(0).any().any():
        raise ValueError("As métricas de uma corrida concluída não podem ser negativas.")


def transform_rides(rides: pd.DataFrame) -> pd.DataFrame:
    validate_raw_rides(rides)
    treated = rides.copy()

    for column in ("city", "origin_neighborhood", "destination_neighborhood", "category", "payment_method"):
        treated[column] = treated[column].str.strip()

    treated["ride_date"] = treated["requested_at"].dt.date
    treated["request_hour"] = treated["requested_at"].dt.hour
    treated["request_weekday"] = treated["requested_at"].dt.dayofweek.map(lambda day: WEEKDAYS[day])
    treated["is_peak_hour"] = treated["request_hour"].isin(PEAK_HOURS)
    treated["fare_per_km"] = (treated["fare_brl"] / treated["distance_km"]).round(2)

    return treated


def process_file(input_path: Path, output_path: Path) -> int:
    rides = read_raw_rides(input_path)
    treated = transform_rides(rides)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    treated.to_csv(output_path, index=False, date_format="%Y-%m-%d %H:%M:%S")
    return len(treated)


def main() -> None:
    args = build_parser().parse_args()
    count = process_file(args.input, args.output)
    print(f"{count:,} corridas tratadas em {args.output}")


if __name__ == "__main__":
    main()
