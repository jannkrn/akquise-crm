from __future__ import annotations

import re

from config import DATA_DIR


PROMPT_PATH = DATA_DIR / "sender_prompt.txt"

DEFAULT_SENDER_PROMPT = """Profil und Positionierung von Jann Körner:

Ich habe bei einer Immobilienfirma im Accounting gearbeitet und kenne daher viele manuelle Prozesse aus der Praxis, insbesondere rund um ERP-nahe Abläufe, Excel, Abstimmungen, Abrechnungen und kaufmännische Verwaltung.

Momentan mache ich meinen Master in Wirtschaftsinformatik in Halle und arbeite als Werkstudent bei Rossmann im Bereich Prozessautomatisierung, Datenanalyse und Data Engineering.

Ich möchte kleinen Immobilienunternehmen keine große Beratung verkaufen, sondern kleine Pilotprojekte anbieten, bei denen 1-2 wiederkehrende Prozesse geprüft und nur bei erkennbarem Nutzen vereinfacht oder automatisiert werden.

Wie die KI dieses Profil in Mails nutzen soll:
- Das Profil soll Substanz vermitteln, aber nicht wie ein Lebenslauf klingen.
- Stelle den Bezug zu ERP-/Excel-nahen Abläufen, Datenqualität, Auswertungen, wiederkehrenden Abstimmungen und kleinen Automatisierungen her.
- Keine übertriebenen Versprechen.
- Keine Unterstellung, dass das Unternehmen konkrete Probleme hat.
- Immer auf öffentlich sichtbare Themen der Website beziehen.
- Kurz, sachlich und direkt schreiben.
- Rückmeldung gerne auch per Telefon: 01732117579
- Signatur immer:
Viele Grüße
Jann Körner
"""


def get_sender_phone(prompt: str | None = None) -> str:
    source = prompt if prompt is not None else get_sender_prompt()
    match = re.search(r"(?:\+49|0)[\d \t()/.-]{6,}", source)
    return re.sub(r"[^\d+]", "", match.group(0)) if match else ""


def enforce_sender_prompt_in_email(body: str, prompt: str | None = None) -> str:
    """Keep concrete sender facts from the editable prompt in generated drafts."""
    cleaned = body.strip().replace("\r\n", "\n").replace("\r", "\n")
    source = prompt if prompt is not None else get_sender_prompt()

    if "Halle" in source and "Halle" not in cleaned:
        if "Master in Wirtschaftsinformatik" in cleaned:
            cleaned = cleaned.replace(
                "Master in Wirtschaftsinformatik",
                "Master in Wirtschaftsinformatik in Halle",
                1,
            )
        else:
            cleaned = _insert_before_signoff(
                cleaned,
                "Ich mache meinen Master in Wirtschaftsinformatik in Halle.",
            )

    phone = get_sender_phone(source)
    if phone and phone not in re.sub(r"\s+", "", cleaned):
        cleaned = _insert_before_signoff(
            cleaned,
            f"Rückmeldung gerne auch per Telefon: {phone}",
        )

    return cleaned


def _insert_before_signoff(body: str, sentence: str) -> str:
    signoff = "Viele Grüße\nJann Körner"
    if signoff in body:
        return body.replace(signoff, f"{sentence}\n\n{signoff}", 1)
    return f"{body.rstrip()}\n\n{sentence}"


def ensure_prompt_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PROMPT_PATH.exists():
        PROMPT_PATH.write_text(DEFAULT_SENDER_PROMPT, encoding="utf-8")


def get_sender_prompt() -> str:
    ensure_prompt_file()
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def save_sender_prompt(prompt: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_PATH.write_text(prompt.strip() + "\n", encoding="utf-8")


def reset_sender_prompt() -> None:
    save_sender_prompt(DEFAULT_SENDER_PROMPT)
