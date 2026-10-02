from datetime import date, timedelta

import pandas as pd

from generate_operational_decision import (
    DECISION_COLUMNS,
    build_state,
    decision_record,
    generate_operational_decision,
    write_decision,
)


def operations() -> pd.DataFrame:
    rows = []
    for offset in range(8):
        rows.append(
            {
                "ride_date": date(2025, 1, 1) + timedelta(days=offset),
                "total_requests": 1000 + offset * 10,
                "completed_rides": 880 + offset * 10,
                "cancelled_rides": 120,
                "cancellation_rate_pct": 12.0,
                "revenue_brl": 20000 + offset * 100,
                "avg_wait_minutes": 7.0,
                "avg_fare_brl": 22.5,
            }
        )
    return pd.DataFrame(rows)


def test_builds_state_with_current_day_and_baseline() -> None:
    state = build_state(operations())

    assert state["analysis_date"] == "2025-01-08"
    assert state["current_day"]["total_requests"] == 1070
    assert state["prior_7_day_average"]["total_requests"] == 1030
    assert state["variation_vs_prior_7_days_pct"]["total_requests"] == 3.88


def test_validates_typed_jev_response() -> None:
    state = build_state(operations())
    response = {
        "id": "decision-1",
        "model": "jev-1.13-free",
        "answers": {
            "risk_level": {"type": "choice", "choice": "atencao", "confidence": 0.91},
            "primary_alert": {
                "type": "choice",
                "choice": "cancelamentos",
                "confidence": 0.83,
            },
            "requires_human_review": {"type": "noul", "noul": 0.84},
        },
    }

    record = decision_record(response, state)

    assert record["risk_level"] == "atencao"
    assert record["requires_human_review"] is True
    assert record["decision_status"] == "generated"


def test_uses_manual_review_without_api_key() -> None:
    record = generate_operational_decision(operations(), api_key=None)

    assert record["decision_status"] == "manual_review"
    assert record["requires_human_review"] is True


def test_writes_decision_csv(tmp_path) -> None:
    output = tmp_path / "operational_decision.csv"
    record = generate_operational_decision(operations(), api_key=None)

    write_decision(record, output)

    saved = pd.read_csv(output)
    assert saved.columns.tolist() == DECISION_COLUMNS
    assert saved.loc[0, "risk_level"] == "manual_review"
