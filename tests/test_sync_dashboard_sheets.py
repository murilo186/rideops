from datetime import date

import pandas as pd

from sync_dashboard_sheets import dataframe_to_values, files_to_sync, read_operational_decision, worksheet_name


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


def test_adds_operational_decision_when_available() -> None:
    files = files_to_sync({"operational_decision": pd.DataFrame()})

    assert files["operational_decision"] == "operational_decision.csv"


def test_reads_valid_operational_decision(tmp_path) -> None:
    decision_file = tmp_path / "operational_decision.csv"
    pd.DataFrame(
        [
            {
                "analysis_date": "2025-01-08",
                "risk_level": "atencao",
                "risk_confidence": 0.9,
                "primary_alert": "cancelamentos",
                "primary_alert_confidence": 0.8,
                "requires_human_review": True,
                "review_probability": 0.85,
                "decision_status": "generated",
                "model": "jev-1.13-free",
                "decision_id": "decision-1",
            }
        ]
    ).to_csv(decision_file, index=False)

    decision = read_operational_decision(decision_file)

    assert decision is not None
    assert decision.loc[0, "risk_level"] == "atencao"
