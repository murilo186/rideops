from datetime import date

import pandas as pd

from sync_dashboard_sheets import dataframe_to_values, worksheet_name


def test_serializes_headers_dates_and_missing_values() -> None:
    dataframe = pd.DataFrame(
        {
            "ride_date": [date(2025, 1, 1)],
            "revenue_brl": [23.5],
            "fare_per_km": [None],
        }
    )

    values = dataframe_to_values(dataframe)

    assert values[0] == ["ride_date", "revenue_brl", "fare_per_km"]
    assert values[1] == ["2025-01-01", 23.5, ""]


def test_uses_csv_file_name_as_worksheet_name() -> None:
    assert worksheet_name("daily_operations.csv") == "daily_operations"
