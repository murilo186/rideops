from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
from sqlalchemy import create_engine, text

from load_rides import database_url


BEATAPI_URL = "https://api.beatapi.io/v1/systemone"
MODEL = "jev-1.13-free"
DECISION_COLUMNS = [
    "analysis_date",
    "risk_level",
    "risk_confidence",
    "primary_alert",
    "primary_alert_confidence",
    "requires_human_review",
    "review_probability",
    "decision_status",
    "model",
    "decision_id",
]
METRICS = [
    "total_requests",
    "completed_rides",
    "cancelled_rides",
    "cancellation_rate_pct",
    "revenue_brl",
    "avg_wait_minutes",
    "avg_fare_brl",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Gera uma decisão operacional com Jev AI.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("exports/operational_decision.csv"),
        help="Arquivo CSV que receberá a decisão.",
    )
    return parser


def read_recent_operations() -> pd.DataFrame:
    engine = create_engine(database_url())
    try:
        with engine.connect() as connection:
            operations = pd.read_sql_query(
                text(
                    """
                    SELECT ride_date, total_requests, completed_rides, cancelled_rides,
                           cancellation_rate_pct, revenue_brl, avg_wait_minutes, avg_fare_brl
                    FROM vw_daily_operations
                    ORDER BY ride_date DESC
                    LIMIT 8
                    """
                ),
                connection,
            )
    finally:
        engine.dispose()

    if len(operations) < 8:
        raise ValueError("São necessários pelo menos oito dias de operação para gerar a decisão.")
    return operations.sort_values("ride_date").reset_index(drop=True)


def as_number(value: Any) -> int | float:
    number = float(value)
    return int(number) if number.is_integer() else round(number, 2)


def percent_variation(current: Any, baseline: Any) -> float | None:
    baseline_number = float(baseline)
    if baseline_number == 0:
        return None
    return round(100 * (float(current) - baseline_number) / baseline_number, 2)


def build_state(operations: pd.DataFrame) -> dict[str, Any]:
    if len(operations) < 8:
        raise ValueError("São necessários oito dias de operação para montar o contexto.")

    latest = operations.iloc[-1]
    baseline = operations.iloc[-8:-1]
    baseline_average = baseline[METRICS].mean(numeric_only=True)
    current = {metric: as_number(latest[metric]) for metric in METRICS}
    average = {metric: as_number(baseline_average[metric]) for metric in METRICS}
    variation = {
        metric: percent_variation(latest[metric], baseline_average[metric]) for metric in METRICS
    }
    return {
        "analysis_date": str(pd.Timestamp(latest["ride_date"]).date()),
        "current_day": current,
        "prior_7_day_average": average,
        "variation_vs_prior_7_days_pct": variation,
    }


def build_questions() -> dict[str, dict[str, Any]]:
    return {
        "risk_level": {
            "type": "choice",
            "instructions": "Classifique o risco operacional do dia com base nas métricas atuais e na variação frente aos sete dias anteriores.",
            "criteria": {
                "normal": "Métricas próximas do padrão histórico, sem degradação operacional relevante.",
                "atencao": "Há uma degradação relevante em pelo menos uma métrica e ela deve ser acompanhada.",
                "critico": "Há degradação severa ou múltiplos sinais que exigem priorização operacional.",
            },
        },
        "primary_alert": {
            "type": "choice",
            "instructions": "Escolha o principal sinal operacional que merece acompanhamento no dia.",
            "criteria": {
                "cancelamentos": "A taxa ou volume de cancelamentos é o desvio operacional mais relevante.",
                "tempo_de_espera": "O tempo médio de espera é o desvio operacional mais relevante.",
                "demanda": "O volume de solicitações é o desvio operacional mais relevante.",
                "receita": "A receita é o desvio operacional mais relevante.",
            },
        },
        "requires_human_review": {
            "type": "noul",
            "instructions": "O resumo diário indica que uma pessoa deve revisar a operação antes de qualquer ação?",
            "criteria": {
                "true": "Há risco crítico, incerteza relevante ou métricas que exigem validação humana.",
                "false": "A operação pode continuar apenas com acompanhamento normal.",
            },
        },
    }


def request_jev_decision(api_key: str, state: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps({"model": MODEL, "state": state, "questions": build_questions()}).encode()
    request = Request(
        BEATAPI_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "RideOps/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode())
    except HTTPError as error:
        raise RuntimeError(f"BeatAPI respondeu com HTTP {error.code}.") from error
    except URLError as error:
        raise RuntimeError("Não foi possível conectar à BeatAPI.") from error


def is_probability(value: Any) -> bool:
    return isinstance(value, (int, float)) and 0 <= value <= 1


def decision_record(response: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    answers = response.get("answers", {})
    risk = answers.get("risk_level", {})
    alert = answers.get("primary_alert", {})
    review = answers.get("requires_human_review", {})
    valid = (
        risk.get("type") == "choice"
        and risk.get("choice") in {"normal", "atencao", "critico"}
        and is_probability(risk.get("confidence"))
        and alert.get("type") == "choice"
        and alert.get("choice") in {"cancelamentos", "tempo_de_espera", "demanda", "receita"}
        and is_probability(alert.get("confidence"))
        and review.get("type") == "noul"
        and is_probability(review.get("noul"))
    )
    if not valid:
        raise ValueError("A resposta da BeatAPI não corresponde ao contrato esperado.")

    return {
        "analysis_date": state["analysis_date"],
        "risk_level": risk["choice"],
        "risk_confidence": round(float(risk["confidence"]), 4),
        "primary_alert": alert["choice"],
        "primary_alert_confidence": round(float(alert["confidence"]), 4),
        "requires_human_review": bool(review["noul"] >= 0.8),
        "review_probability": round(float(review["noul"]), 4),
        "decision_status": "generated",
        "model": response.get("model", MODEL),
        "decision_id": response.get("id", ""),
    }


def manual_review_record(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "analysis_date": state["analysis_date"],
        "risk_level": "manual_review",
        "risk_confidence": None,
        "primary_alert": "manual_review",
        "primary_alert_confidence": None,
        "requires_human_review": True,
        "review_probability": None,
        "decision_status": "manual_review",
        "model": MODEL,
        "decision_id": "",
    }


def generate_operational_decision(
    operations: pd.DataFrame, api_key: str | None
) -> dict[str, Any]:
    state = build_state(operations)
    if not api_key:
        return manual_review_record(state)
    try:
        return decision_record(request_jev_decision(api_key, state), state)
    except (RuntimeError, ValueError, json.JSONDecodeError):
        return manual_review_record(state)


def write_decision(record: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([record], columns=DECISION_COLUMNS).to_csv(output_path, index=False)


def main() -> None:
    args = build_parser().parse_args()
    record = generate_operational_decision(
        read_recent_operations(), os.environ.get("BEATAPI_API_KEY")
    )
    write_decision(record, args.output)
    print(
        f"Decisão {record['decision_status']}: risco {record['risk_level']}, "
        f"alerta {record['primary_alert']}."
    )


if __name__ == "__main__":
    main()
