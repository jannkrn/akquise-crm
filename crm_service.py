from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

import pandas as pd

from db import execute, fetch_all, fetch_one


STATUSES = [
    "Recherchiert",
    "Entwurf erstellt",
    "Erstmail gesendet",
    "Follow-up fällig",
    "Antwort erhalten",
    "Gespräch geplant",
    "Kein Interesse",
    "Später melden",
    "Pilot möglich",
]

RESPONSE_TYPES = ["Keine Antwort", "Interesse", "Absage", "Später", "Unklar"]

COMPANY_TYPES = [
    "Hausverwaltung",
    "Immobilienverwaltung",
    "WEG-Verwaltung",
    "Property Management",
    "Bestandshalter",
    "Makler",
    "Sonstiges",
]

OFFER_ANGLES = ["Automatisierung", "Daten/Auswertung", "Effizienz-Check"]

COMPANY_FIELDS = [
    "company_name",
    "website",
    "city",
    "contact_name",
    "contact_role",
    "email",
    "phone",
    "company_type",
    "relevant_topics",
    "website_notes",
    "pain_point_hypothesis",
    "offer_angle",
    "email_subject",
    "email_body",
    "email_variant",
    "gmail_draft_id",
    "gmail_draft_message_id",
    "gmail_draft_thread_id",
    "status",
    "first_contact_date",
    "follow_up_date",
    "last_contact_date",
    "response_type",
    "next_step",
    "notes",
]

DATE_FIELDS = {"first_contact_date", "follow_up_date", "last_contact_date"}
TERMINAL_STATUSES = {"Kein Interesse"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def clean_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def normalize_company_data(data: dict[str, Any]) -> dict[str, str]:
    normalized = {field: clean_value(data.get(field, "")) for field in COMPANY_FIELDS}
    normalized["status"] = normalized["status"] or "Recherchiert"
    normalized["response_type"] = normalized["response_type"] or "Keine Antwort"
    return normalized


def validate_company_data(data: dict[str, Any], require_name: bool = True) -> list[str]:
    errors: list[str] = []
    company_name = clean_value(data.get("company_name"))
    email = clean_value(data.get("email"))

    if require_name and not company_name:
        errors.append("Der Unternehmensname ist ein Pflichtfeld.")
    if email and not EMAIL_RE.match(email):
        errors.append("Die E-Mail-Adresse sieht nicht gültig aus.")

    for field in DATE_FIELDS:
        value = clean_value(data.get(field))
        if value:
            try:
                date.fromisoformat(value)
            except ValueError:
                errors.append(f"{field} muss im Format YYYY-MM-DD vorliegen.")

    return errors


def create_company(data: dict[str, Any]) -> int:
    normalized = normalize_company_data(data)
    errors = validate_company_data(normalized)
    if errors:
        raise ValueError(" ".join(errors))

    fields = COMPANY_FIELDS
    placeholders = ", ".join(["?"] * len(fields))
    field_sql = ", ".join(fields)
    values = [normalized[field] for field in fields]
    return execute(
        f"INSERT INTO companies ({field_sql}) VALUES ({placeholders})",
        values,
    )


def update_company(company_id: int, data: dict[str, Any], require_name: bool = False) -> None:
    normalized = normalize_company_data(data)
    errors = validate_company_data(normalized, require_name=require_name)
    if errors:
        raise ValueError(" ".join(errors))

    fields = [field for field in COMPANY_FIELDS if field in data]
    if not fields:
        return

    assignments = ", ".join([f"{field} = ?" for field in fields])
    values = [normalized[field] for field in fields]
    values.append(company_id)
    execute(
        f"UPDATE companies SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        values,
    )


def delete_company(company_id: int) -> None:
    execute("DELETE FROM companies WHERE id = ?", [company_id])


def get_company(company_id: int) -> dict[str, Any] | None:
    return fetch_one("SELECT * FROM companies WHERE id = ?", [company_id])


def list_companies(
    search: str = "",
    status: str = "",
    offer_angle: str = "",
    overdue_only: bool = False,
) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[str] = []

    if search:
        like = f"%{search.lower()}%"
        where.append(
            """(
                lower(company_name) LIKE ?
                OR lower(city) LIKE ?
                OR lower(relevant_topics) LIKE ?
                OR lower(status) LIKE ?
                OR lower(website_notes) LIKE ?
                OR lower(email) LIKE ?
            )"""
        )
        params.extend([like] * 6)

    if status:
        where.append("status = ?")
        params.append(status)

    if offer_angle:
        where.append("offer_angle = ?")
        params.append(offer_angle)

    if overdue_only:
        where.append("follow_up_date IS NOT NULL AND follow_up_date != ''")
        where.append("date(follow_up_date) <= date('now', 'localtime')")
        where.append("status NOT IN ({})".format(",".join(["?"] * len(TERMINAL_STATUSES))))
        params.extend(sorted(TERMINAL_STATUSES))

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    return fetch_all(
        f"""
        SELECT * FROM companies
        {where_sql}
        ORDER BY
            CASE WHEN follow_up_date IS NULL OR follow_up_date = '' THEN 1 ELSE 0 END,
            follow_up_date ASC,
            updated_at DESC
        """,
        params,
    )


def companies_df(rows: list[dict[str, Any]] | None = None) -> pd.DataFrame:
    rows = rows if rows is not None else list_companies()
    return pd.DataFrame(rows)


def due_followups() -> list[dict[str, Any]]:
    placeholders = ",".join(["?"] * len(TERMINAL_STATUSES))
    return fetch_all(
        f"""
        SELECT * FROM companies
        WHERE follow_up_date IS NOT NULL
          AND follow_up_date != ''
          AND date(follow_up_date) <= date('now', 'localtime')
          AND status NOT IN ({placeholders})
        ORDER BY follow_up_date ASC, company_name ASC
        """,
        sorted(TERMINAL_STATUSES),
    )


def dashboard_action_items() -> list[dict[str, Any]]:
    placeholders = ",".join(["?"] * len(TERMINAL_STATUSES))
    return fetch_all(
        f"""
        SELECT *,
            CASE
                WHEN status = 'Entwurf erstellt' THEN 'Entwurf prüfen'
                WHEN follow_up_date IS NOT NULL
                  AND follow_up_date != ''
                  AND date(follow_up_date) <= date('now', 'localtime')
                  THEN 'Follow-up fällig'
                ELSE 'Prüfen'
            END AS action_type
        FROM companies
        WHERE (
            status = 'Entwurf erstellt'
            OR (
                follow_up_date IS NOT NULL
                AND follow_up_date != ''
                AND date(follow_up_date) <= date('now', 'localtime')
            )
        )
        AND status NOT IN ({placeholders})
        ORDER BY
            CASE WHEN status = 'Entwurf erstellt' THEN 0 ELSE 1 END,
            CASE WHEN follow_up_date IS NULL OR follow_up_date = '' THEN 1 ELSE 0 END,
            follow_up_date ASC,
            updated_at DESC
        """,
        sorted(TERMINAL_STATUSES),
    )


def followups_df() -> pd.DataFrame:
    rows = fetch_all(
        """
        SELECT * FROM companies
        WHERE follow_up_date IS NOT NULL AND follow_up_date != ''
        ORDER BY follow_up_date ASC, company_name ASC
        """
    )
    return companies_df(rows)


def interested_leads_df() -> pd.DataFrame:
    rows = fetch_all(
        """
        SELECT * FROM companies
        WHERE status IN ('Antwort erhalten', 'Gespräch geplant', 'Pilot möglich')
           OR response_type = 'Interesse'
        ORDER BY updated_at DESC
        """
    )
    return companies_df(rows)


def dashboard_stats() -> dict[str, Any]:
    all_rows = list_companies()
    total = len(all_rows)
    status_counts = fetch_all(
        "SELECT status, COUNT(*) AS count FROM companies GROUP BY status ORDER BY count DESC"
    )
    due = due_followups()
    action_items = dashboard_action_items()
    open_drafts = [row for row in all_rows if row.get("status") == "Entwurf erstellt"]
    contacted = [
        row
        for row in all_rows
        if clean_value(row.get("first_contact_date"))
        or row.get("status") in {"Erstmail gesendet", "Follow-up fällig", "Antwort erhalten", "Gespräch geplant", "Pilot möglich"}
    ]
    responses = [
        row
        for row in contacted
        if clean_value(row.get("response_type")) not in {"", "Keine Antwort"}
        or row.get("status") in {"Antwort erhalten", "Gespräch geplant", "Pilot möglich"}
    ]
    conversations = [
        row for row in contacted if row.get("status") in {"Gespräch geplant", "Pilot möglich"}
    ]
    contacted_count = len(contacted)
    return {
        "total": total,
        "status_counts": status_counts,
        "due_followups": due,
        "dashboard_action_items": action_items,
        "open_draft_count": len(open_drafts),
        "response_rate": len(responses) / contacted_count if contacted_count else 0,
        "conversation_rate": len(conversations) / contacted_count if contacted_count else 0,
    }


def mark_first_mail_sent(company_id: int) -> None:
    today = date.today()
    update_company(
        company_id,
        {
            "status": "Erstmail gesendet",
            "first_contact_date": today.isoformat(),
            "last_contact_date": today.isoformat(),
            "follow_up_date": (today + timedelta(days=7)).isoformat(),
            "response_type": "Keine Antwort",
        },
    )


def mark_status(company_id: int, status: str) -> None:
    today = date.today().isoformat()
    payload: dict[str, str] = {"status": status}

    if status in {"Antwort erhalten", "Gespräch geplant", "Kein Interesse", "Später melden", "Pilot möglich"}:
        payload["last_contact_date"] = today
    if status == "Antwort erhalten":
        payload["response_type"] = "Unklar"
    elif status == "Gespräch geplant":
        payload["response_type"] = "Interesse"
    elif status == "Kein Interesse":
        payload["response_type"] = "Absage"
    elif status == "Später melden":
        payload["response_type"] = "Später"
    elif status == "Pilot möglich":
        payload["response_type"] = "Interesse"

    update_company(company_id, payload)


def update_follow_up(company_id: int, follow_up_date: str, next_step: str = "") -> None:
    update_company(
        company_id,
        {"follow_up_date": follow_up_date, "next_step": next_step},
    )


def find_duplicate(data: dict[str, Any]) -> dict[str, Any] | None:
    email = clean_value(data.get("email")).lower()
    company_name = clean_value(data.get("company_name")).lower()
    website = clean_value(data.get("website")).lower()

    if email:
        duplicate = fetch_one("SELECT * FROM companies WHERE lower(email) = ?", [email])
        if duplicate:
            return duplicate

    if company_name and website:
        return fetch_one(
            "SELECT * FROM companies WHERE lower(company_name) = ? AND lower(website) = ?",
            [company_name, website],
        )
    return None


def import_companies(rows: list[dict[str, Any]]) -> dict[str, Any]:
    imported = 0
    skipped = 0
    errors: list[str] = []

    for index, row in enumerate(rows, start=1):
        normalized = normalize_company_data(row)
        normalized["status"] = normalized.get("status") or "Recherchiert"

        validation_errors = validate_company_data(normalized)
        if validation_errors:
            skipped += 1
            errors.append(f"Zeile {index}: {' '.join(validation_errors)}")
            continue

        if find_duplicate(normalized):
            skipped += 1
            continue

        create_company(normalized)
        imported += 1

    return {"imported": imported, "skipped": skipped, "errors": errors}
