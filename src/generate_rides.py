from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


CITY = "São Paulo"
NEIGHBORHOODS = (
    "Bela Vista",
    "Butantã",
    "Consolação",
    "Itaim Bibi",
    "Jardins",
    "Liberdade",
    "Moema",
    "Morumbi",
    "Perdizes",
    "Pinheiros",
    "Santana",
    "Tatuapé",
    "Vila Madalena",
    "Vila Mariana",
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera dados sintéticos de corridas em São Paulo.")
    parser.add_argument("--rows", type=int, default=100_000, help="Quantidade de corridas a gerar.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/raw/rides.csv"),
        help="Caminho do arquivo CSV de saída.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Semente para resultados reproduzíveis.")
    return parser


def choose_request_time(rng: random.Random) -> datetime:
    start = datetime(2025, 1, 1)
    day = start + timedelta(days=rng.randrange(365))
    hour = rng.choices(
        population=[7, 8, 9, 12, 13, 17, 18, 19, 20, *range(24)],
        weights=[7, 10, 6, 4, 4, 8, 12, 8, 5, *([1] * 24)],
        k=1,
    )[0]
    return day.replace(hour=hour, minute=rng.randrange(60), second=rng.randrange(60))


def generate_rides(rows: int, seed: int = 42) -> pd.DataFrame:
    if rows <= 0:
        raise ValueError("A quantidade de corridas deve ser maior que zero.")

    rng = random.Random(seed)
    records: list[dict[str, object]] = []

    for number in range(1, rows + 1):
        requested_at = choose_request_time(rng)
        origin = rng.choice(NEIGHBORHOODS)
        destination = rng.choice([item for item in NEIGHBORHOODS if item != origin])
        status = rng.choices(
            ["concluída", "cancelada_passageiro", "cancelada_motorista"],
            weights=[90, 7, 3],
            k=1,
        )[0]
        category = rng.choices(CATEGORIES, weights=[70, 23, 7], k=1)[0]
        wait_minutes = rng.randint(2, 12)
        distance_km = round(rng.uniform(1.2, 24.0), 2)
        duration_minutes = max(5, round(distance_km * rng.uniform(2.4, 4.6)))
        surge_multiplier = 1.0
        if requested_at.hour in {7, 8, 9, 17, 18, 19}:
            surge_multiplier = rng.choice([1.0, 1.1, 1.2, 1.3])
        category_multiplier = {"econômica": 1.0, "conforto": 1.35, "premium": 1.9}[category]
        fare = round((7.0 + distance_km * 2.8 + duration_minutes * 0.45) * surge_multiplier * category_multiplier, 2)

        record: dict[str, object] = {
            "ride_id": f"RIDE-{number:07d}",
            "requested_at": requested_at,
            "city": CITY,
            "origin_neighborhood": origin,
            "destination_neighborhood": destination,
            "passenger_id": f"PAX-{rng.randint(1, max(100, rows // 4)):06d}",
            "driver_id": f"DRV-{rng.randint(1, max(50, rows // 10)):05d}",
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

    return pd.DataFrame.from_records(records)


def main() -> None:
    args = build_parser().parse_args()
    rides = generate_rides(rows=args.rows, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rides.to_csv(args.output, index=False, date_format="%Y-%m-%d %H:%M:%S")
    print(f"{len(rides):,} corridas geradas em {args.output}")


if __name__ == "__main__":
    main()
