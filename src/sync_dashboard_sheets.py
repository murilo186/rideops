from __future__ import annotations

import argparse
import os
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from export_dashboard_data import EXPORT_FILES, read_dashboard_views
from generate_operational_decision import DECISION_COLUMNS


if TYPE_CHECKING:
    import gspread


SCOPES = ("https://www.googleapis.com/auth/spreadsheets",)
OPERATIONAL_DECISION_FILE = Path("exports/operational_decision.csv")


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


def files_to_sync(dataframes: dict[str, pd.DataFrame]) -> dict[str, str]:
    files = EXPORT_FILES.copy()
    if "operational_decision" in dataframes:
        files["operational_decision"] = OPERATIONAL_DECISION_FILE.name
    return files


def sync_dataframes(
    spreadsheet: "gspread.Spreadsheet", dataframes: dict[str, pd.DataFrame]
) -> dict[str, int]:
    import gspread

    synchronized: dict[str, int] = {}
    for view_name, filename in files_to_sync(dataframes).items():
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


def read_operational_decision(input_path: Path = OPERATIONAL_DECISION_FILE) -> pd.DataFrame | None:
    if not input_path.is_file():
        return None
    decision = pd.read_csv(input_path)
    if decision.columns.tolist() != DECISION_COLUMNS:
        raise ValueError("O arquivo de decisão operacional possui colunas inválidas.")
    return decision


def sync_dashboard_sheets(
    credentials_file: Path, spreadsheet_id: str, decision_path: Path = OPERATIONAL_DECISION_FILE
) -> dict[str, int]:
    import gspread
    from google.oauth2.service_account import Credentials

    if not spreadsheet_id:
        raise ValueError("Defina GOOGLE_SHEETS_SPREADSHEET_ID no arquivo .env.")
    if not credentials_file.is_file():
        raise FileNotFoundError(f"Arquivo de credenciais não encontrado: {credentials_file}")

    credentials = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(spreadsheet_id)
    dataframes = read_dashboard_views()
    decision = read_operational_decision(decision_path)
    if decision is not None:
        dataframes["operational_decision"] = decision
    return sync_dataframes(spreadsheet, dataframes)


def main() -> None:
    args = build_parser().parse_args()
    synchronized = sync_dashboard_sheets(args.credentials_file, args.spreadsheet_id)
    for name, row_count in synchronized.items():
        print(f"{row_count:,} linhas sincronizadas na aba {name}")


if __name__ == "__main__":
    main()
