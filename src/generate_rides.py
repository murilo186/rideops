from __future__ import annotations

import argparse
import random
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


CITY = "São Paulo"
DEFAULT_ROWS = 3_000_000
NEIGHBORHOODS = (
    "Bela Vista",
    "Brás",
    "Butantã",
    "Campo Belo",
    "Campo Grande",
    "Consolação",
    "Freguesia do Ó",
    "Higienópolis",
    "Interlagos",
    "Itaim Bibi",
    "Jabaquara",
    "Jardins",
    "Lapa",
    "Liberdade",
    "Mandaqui",
    "Moema",
    "Mooca",
    "Morumbi",
    "Pacaembu",
    "Perdizes",
    "Pinheiros",
    "Santo Amaro",
    "Santana",
    "Sé",
    "Tatuapé",
    "Vila Leopoldina",
    "Vila Madalena",
    "Vila Mariana",
)
NEIGHBORHOOD_WEIGHTS = (
    5,
    4,
    5,
    4,
    4,
    7,
    3,
    5,
    4,
    10,
    4,
    9,
    5,
    7,
    3,
    10,
    5,
    5,
    3,
    6,
    10,
    8,
    7,
    5,
    6,
    4,
    7,
    8,
)
CATEGORIES = ("econômica", "conforto", "premium")
PAYMENT_METHODS = ("cartão de crédito", "cartão de débito", "carteira digital", "dinheiro")
CANCELLATION_REASONS = {
    "cancelada_passageiro": (
        "motorista demorou para chegar",
        "mudança de planos",
        "encontrei outro transporte",
    ),
    "cancelada_motorista": (
        "passageiro não apareceu",
        "local de embarque inacessível",
        "distância até o embarque",
    ),
}
PEAK_HOURS = {7, 8, 9, 17, 18, 19}
HOURS = tuple(range(24))
HOUR_WEIGHTS = (1, 1, 1, 1, 1, 2, 5, 10, 12, 8, 5, 5, 6, 7, 6, 5, 6, 10, 13, 10, 6, 4, 3, 2)
START_DATE = datetime(2025, 1, 1)
WEEKDAY_DEMAND_WEIGHTS = (115, 120, 118, 116, 128, 82, 68)
DEMAND_DAYS = tuple(
    day
    for offset in range(365)
    for day in (START_DATE + timedelta(days=offset),)
    for _ in range(WEEKDAY_DEMAND_WEIGHTS[day.weekday()])
)
MAX_PASSENGERS = 500_000
MAX_DRIVERS = 20_000


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera dados sintéticos de corridas em São Paulo.")
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS, help="Quantidade de corridas a gerar.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/raw/rides.csv"),
        help="Caminho do arquivo CSV de saída.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Semente para resultados reproduzíveis.")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=100_000,
        help="Quantidade de corridas gravadas por lote.",
    )
    return parser


def choose_request_time(rng: random.Random) -> datetime:
    day = rng.choice(DEMAND_DAYS)
    hour = rng.choices(HOURS, weights=HOUR_WEIGHTS, k=1)[0]
    return day.replace(hour=hour, minute=rng.randrange(60), second=rng.randrange(60))


def choose_status(rng: random.Random, requested_at: datetime) -> str:
    if requested_at.hour in PEAK_HOURS:
        weights = [86, 10, 4]
    elif requested_at.weekday() >= 5:
        weights = [92, 6, 2]
    else:
        weights = [90, 7, 3]
    return rng.choices(["concluída", "cancelada_passageiro", "cancelada_motorista"], weights=weights, k=1)[0]


def choose_neighborhood(rng: random.Random, excluded: str | None = None) -> str:
    neighborhood = rng.choices(NEIGHBORHOODS, weights=NEIGHBORHOOD_WEIGHTS, k=1)[0]
    while neighborhood == excluded:
        neighborhood = rng.choices(NEIGHBORHOODS, weights=NEIGHBORHOOD_WEIGHTS, k=1)[0]
    return neighborhood


def entity_pool_size(rows: int, ratio: int, maximum: int) -> int:
    return min(maximum, max(1, rows // ratio))


def generate_records(start: int, count: int, rows: int, rng: random.Random) -> list[dict[str, object]]:
    passenger_count = entity_pool_size(rows, ratio=4, maximum=MAX_PASSENGERS)
    driver_count = entity_pool_size(rows, ratio=10, maximum=MAX_DRIVERS)
    records: list[dict[str, object]] = []

    for number in range(start, start + count):
        requested_at = choose_request_time(rng)
        origin = choose_neighborhood(rng)
        destination = choose_neighborhood(rng, excluded=origin)
        status = choose_status(rng, requested_at)
        category = rng.choices(CATEGORIES, weights=[70, 23, 7], k=1)[0]
        wait_minutes = rng.randint(5, 18) if requested_at.hour in PEAK_HOURS else rng.randint(2, 12)
        distance_km = round(rng.uniform(1.2, 24.0), 2)
        duration_minutes = max(5, round(distance_km * rng.uniform(2.4, 4.6)))
        surge_multiplier = 1.0
        if requested_at.hour in PEAK_HOURS:
            surge_multiplier = rng.choice([1.0, 1.1, 1.2, 1.3])
        category_multiplier = {"econômica": 1.0, "conforto": 1.35, "premium": 1.9}[category]
        fare = round((7.0 + distance_km * 2.8 + duration_minutes * 0.45) * surge_multiplier * category_multiplier, 2)

        record: dict[str, object] = {
            "ride_id": f"RIDE-{number:07d}",
            "requested_at": requested_at,
            "city": CITY,
            "origin_neighborhood": origin,
            "destination_neighborhood": destination,
            "passenger_id": f"PAX-{rng.randint(1, passenger_count):06d}",
            "driver_id": f"DRV-{rng.randint(1, driver_count):05d}",
            "category": category,
            "status": status,
            "wait_minutes": wait_minutes,
            "payment_method": rng.choice(PAYMENT_METHODS),
            "cancellation_reason": None,
            "started_at": None,
            "finished_at": None,
            "distance_km": None,
            "duration_minutes": None,
            "fare_brl": None,
            "driver_rating": None,
        }
        if status == "concluída":
            started_at = requested_at + timedelta(minutes=wait_minutes)
            record.update(
                {
                    "started_at": started_at,
                    "finished_at": started_at + timedelta(minutes=duration_minutes),
                    "distance_km": distance_km,
                    "duration_minutes": duration_minutes,
                    "fare_brl": fare,
                    "driver_rating": round(rng.uniform(3.8, 5.0), 1),
                }
            )
        else:
            record["cancellation_reason"] = rng.choice(CANCELLATION_REASONS[status])

        records.append(record)

    return records


def generate_rides_chunks(rows: int, chunk_size: int = 100_000, seed: int = 42) -> Iterator[pd.DataFrame]:
    if rows <= 0:
        raise ValueError("A quantidade de corridas deve ser maior que zero.")
    if chunk_size <= 0:
        raise ValueError("O tamanho do lote deve ser maior que zero.")

    rng = random.Random(seed)
    for start in range(1, rows + 1, chunk_size):
        count = min(chunk_size, rows - start + 1)
        yield pd.DataFrame.from_records(generate_records(start, count, rows, rng))


def generate_rides(rows: int, seed: int = 42) -> pd.DataFrame:
    return next(generate_rides_chunks(rows=rows, chunk_size=rows, seed=seed))


def write_rides(rows: int, output_path: Path, chunk_size: int, seed: int) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    for index, rides in enumerate(generate_rides_chunks(rows=rows, chunk_size=chunk_size, seed=seed)):
        rides.to_csv(
            output_path,
            mode="w" if index == 0 else "a",
            header=index == 0,
            index=False,
            date_format="%Y-%m-%d %H:%M:%S",
        )
        written += len(rides)
    return written


def main() -> None:
    args = build_parser().parse_args()
    count = write_rides(args.rows, args.output, args.chunk_size, args.seed)
    print(f"{count:,} corridas geradas em {args.output}")


if __name__ == "__main__":
    main()
