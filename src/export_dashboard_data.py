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
                view_name: pd.read_sql_query(text(f"SELECT * FROM {view_name}"), connection)
                for view_name in EXPORT_FILES
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
