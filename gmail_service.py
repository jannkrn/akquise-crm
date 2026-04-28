from __future__ import annotations

import base64
import json
from email.message import EmailMessage
from typing import Any

from config import GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH, ensure_directories


GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


class GmailDraftError(RuntimeError):
    pass


def build_gmail_draft_url(message_id: str = "", draft_id: str = "") -> str:
    if message_id.strip():
        return f"https://mail.google.com/mail/u/0/#drafts?compose={message_id.strip()}"
    if draft_id.strip():
        return "https://mail.google.com/mail/u/0/#drafts"
    return ""


def is_gmail_configured() -> bool:
    return GMAIL_CREDENTIALS_PATH.exists()


def gmail_status() -> dict[str, Any]:
    credentials_valid = False
    credentials_kind = "fehlt"
    credentials_error = ""

    if GMAIL_CREDENTIALS_PATH.exists():
        try:
            payload = json.loads(GMAIL_CREDENTIALS_PATH.read_text(encoding="utf-8"))
            credentials_kind = "installed" if "installed" in payload else "web" if "web" in payload else "unbekannt"
            client_config = payload.get("installed") or payload.get("web") or {}
            required_keys = {"client_id", "client_secret", "auth_uri", "token_uri"}
            credentials_valid = credentials_kind == "installed" and required_keys.issubset(client_config)
            if credentials_kind != "installed":
                credentials_error = "Die Datei muss ein OAuth-Client vom Typ Desktop-App sein."
            elif not credentials_valid:
                credentials_error = "Die OAuth-Datei ist unvollständig."
        except Exception as exc:
            credentials_kind = "unlesbar"
            credentials_error = f"Die OAuth-Datei konnte nicht gelesen werden: {exc}"

    return {
        "credentials_path": str(GMAIL_CREDENTIALS_PATH),
        "credentials_exists": GMAIL_CREDENTIALS_PATH.exists(),
        "credentials_valid": credentials_valid,
        "credentials_kind": credentials_kind,
        "credentials_error": credentials_error,
        "token_path": str(GMAIL_TOKEN_PATH),
        "token_exists": GMAIL_TOKEN_PATH.exists(),
        "scope": GMAIL_SCOPES[0],
    }


def _load_google_modules() -> tuple[Any, Any, Any, Any]:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise GmailDraftError(
            "Gmail-Abhängigkeiten fehlen. Bitte requirements.txt installieren."
        ) from exc
    return Request, Credentials, InstalledAppFlow, build


def _get_gmail_service() -> Any:
    if not GMAIL_CREDENTIALS_PATH.exists():
        raise GmailDraftError(
            f"Keine Google OAuth-Datei gefunden: {GMAIL_CREDENTIALS_PATH}. "
            "Lege dort eine OAuth-Client-Datei aus der Google Cloud Console ab."
        )

    ensure_directories()
    Request, Credentials, InstalledAppFlow, build = _load_google_modules()

    credentials = None
    if GMAIL_TOKEN_PATH.exists():
        credentials = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_PATH), GMAIL_SCOPES)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(GMAIL_CREDENTIALS_PATH),
                GMAIL_SCOPES,
            )
            credentials = flow.run_local_server(port=0)

        GMAIL_TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=credentials)


def create_gmail_draft(to: str, subject: str, body: str) -> dict[str, str]:
    if not to.strip():
        raise GmailDraftError("Für einen Gmail-Entwurf wird eine Empfängeradresse benötigt.")
    if not subject.strip():
        raise GmailDraftError("Für einen Gmail-Entwurf wird ein Betreff benötigt.")
    if not body.strip():
        raise GmailDraftError("Für einen Gmail-Entwurf wird ein E-Mail-Text benötigt.")

    message = EmailMessage()
    message["To"] = to.strip()
    message["Subject"] = subject.strip()
    message.set_content(body.strip())

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    service = _get_gmail_service()
    draft = (
        service.users()
        .drafts()
        .create(userId="me", body={"message": {"raw": raw_message}})
        .execute()
    )
    draft_id = draft.get("id")
    if not draft_id:
        raise GmailDraftError("Gmail hat keine Draft-ID zurückgegeben.")
    draft_message = draft.get("message") or {}
    message_id = str(draft_message.get("id") or "")
    thread_id = str(draft_message.get("threadId") or "")
    return {
        "draft_id": str(draft_id),
        "message_id": message_id,
        "thread_id": thread_id,
        "url": build_gmail_draft_url(message_id=message_id, draft_id=str(draft_id)),
    }
