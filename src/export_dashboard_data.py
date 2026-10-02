from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from load_rides import database_url


EXPORT_FILES = {
    "vw_daily_operations": "daily_operations.csv",
    "vw_neighborhood_performance": "neighborhood_performance.csv",
    "vw_cancellation_analysis": "cancellation_analysis.csv",
    "vw_driver_quality": "driver_quality.csv",
}
DASHBOARD_QUERIES = {
    "vw_daily_operations": "SELECT * FROM vw_daily_operations ORDER BY ride_date",
    "vw_neighborhood_performance": """
        SELECT *
        FROM vw_neighborhood_performance
        ORDER BY ride_date, neighborhood_role, neighborhood
    """,
    "vw_cancellation_analysis": """
        WITH daily_demand AS (
            SELECT ride_date, COUNT(*) AS total_requests
            FROM rides
            GROUP BY ride_date
        )
        SELECT
            rides.ride_date,
            rides.cancellation_reason,
            COUNT(*) AS cancellation_count,
            daily_demand.total_requests,
            ROUND(100.0 * COUNT(*) / daily_demand.total_requests, 2) AS cancellation_rate_pct
        FROM rides
        JOIN daily_demand USING (ride_date)
        WHERE rides.status IN ('cancelada_passageiro', 'cancelada_motorista')
        GROUP BY rides.ride_date, rides.cancellation_reason, daily_demand.total_requests
        ORDER BY rides.ride_date, rides.cancellation_reason
    """,
    "vw_driver_quality": """
        SELECT *
        FROM vw_driver_quality
        ORDER BY completed_rides DESC, avg_driver_rating DESC
        LIMIT 100
    """,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exporta as views analíticas para arquivos CSV.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("exports"),
        help="Pasta onde os CSVs do dashboard serão salvos.",
    )
    return parser


def write_exports(dataframes: dict[str, pd.DataFrame], output_dir: Path) -> dict[Path, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    exported: dict[Path, int] = {}

    for view_name, filename in EXPORT_FILES.items():
        output_path = output_dir / filename
        dataframes[view_name].to_csv(output_path, index=False, date_format="%Y-%m-%d")
        exported[output_path] = len(dataframes[view_name])

    return exported


def read_dashboard_views() -> dict[str, pd.DataFrame]:
    engine = create_engine(database_url())
    try:
        with engine.connect() as connection:
            return {
                view_name: pd.read_sql_query(text(query), connection)
                for view_name, query in DASHBOARD_QUERIES.items()
            }
    finally:
        engine.dispose()


def export_dashboard_data(output_dir: Path) -> dict[Path, int]:
    dataframes = read_dashboard_views()
    return write_exports(dataframes, output_dir)


def main() -> None:
    args = build_parser().parse_args()
    exported = export_dashboard_data(args.output_dir)
    for output_path, row_count in exported.items():
        print(f"{row_count:,} linhas exportadas em {output_path}")


if __name__ == "__main__":
    main()
