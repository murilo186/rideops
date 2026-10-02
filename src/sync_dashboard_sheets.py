from __future__ import annotations

import argparse
import os
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from export_dashboard_data import EXPORT_FILES, read_dashboard_views


if TYPE_CHECKING:
    import gspread


SCOPES = ("https://www.googleapis.com/auth/spreadsheets",)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sincroniza as views analíticas com uma planilha Google.")
    parser.add_argument(
        "--credentials-file",
        type=Path,
        default=Path(os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "")),
        help="Caminho do arquivo JSON da conta de serviço.",
    )
    parser.add_argument(
        "--spreadsheet-id",
        default=os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID", ""),
        help="ID da planilha Google que receberá os dados.",
    )
    return parser


def dataframe_to_values(dataframe: pd.DataFrame) -> list[list[Any]]:
    values: list[list[Any]] = [dataframe.columns.tolist()]
    for row in dataframe.itertuples(index=False, name=None):
        serialized_row: list[Any] = []
        for value in row:
            if value is None or pd.isna(value):
                serialized_row.append("")
            elif isinstance(value, (date, datetime, pd.Timestamp)):
                serialized_row.append(value.strftime("%Y-%m-%d"))
            elif hasattr(value, "item"):
                serialized_row.append(value.item())
            else:
                serialized_row.append(value)
        values.append(serialized_row)
    return values


def worksheet_name(filename: str) -> str:
    return Path(filename).stem


def sync_dataframes(
    spreadsheet: "gspread.Spreadsheet", dataframes: dict[str, pd.DataFrame]
) -> dict[str, int]:
    import gspread

    synchronized: dict[str, int] = {}
    for view_name, filename in EXPORT_FILES.items():
        values = dataframe_to_values(dataframes[view_name])
        name = worksheet_name(filename)
        try:
            worksheet = spreadsheet.worksheet(name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=name,
                rows=max(len(values), 1_000),
                cols=len(values[0]),
            )

        worksheet.resize(rows=max(len(values), 1_000), cols=len(values[0]))
        worksheet.clear()
        worksheet.update(values=values, range_name="A1", value_input_option="RAW")
        synchronized[name] = len(dataframes[view_name])

    return synchronized


def sync_dashboard_sheets(credentials_file: Path, spreadsheet_id: str) -> dict[str, int]:
    import gspread
    from google.oauth2.service_account import Credentials

    if not spreadsheet_id:
        raise ValueError("Defina GOOGLE_SHEETS_SPREADSHEET_ID no arquivo .env.")
    if not credentials_file.is_file():
        raise FileNotFoundError(f"Arquivo de credenciais não encontrado: {credentials_file}")

    credentials = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(spreadsheet_id)
    return sync_dataframes(spreadsheet, read_dashboard_views())


def main() -> None:
    args = build_parser().parse_args()
    synchronized = sync_dashboard_sheets(args.credentials_file, args.spreadsheet_id)
    for name, row_count in synchronized.items():
        print(f"{row_count:,} linhas sincronizadas na aba {name}")


if __name__ == "__main__":
    main()
