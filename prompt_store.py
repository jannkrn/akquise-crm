from __future__ import annotations

from config import DATA_DIR


PROMPT_PATH = DATA_DIR / "sender_prompt.txt"

DEFAULT_SENDER_PROMPT = """Profil und Positionierung von Jann Körner:

Ich habe bei einer Immobilienfirma im Accounting gearbeitet und kenne daher viele manuelle Prozesse aus der Praxis, insbesondere rund um ERP-nahe Abläufe, Excel, Abstimmungen, Abrechnungen und kaufmännische Verwaltung.

Momentan mache ich meinen Master in Wirtschaftsinformatik und arbeite als Werkstudent bei Rossmann im Bereich Prozessautomatisierung, Datenanalyse und Data Engineering.

Ich möchte kleinen Immobilienunternehmen keine große Beratung verkaufen, sondern kleine Pilotprojekte anbieten, bei denen 1-2 wiederkehrende Prozesse geprüft und nur bei erkennbarem Nutzen vereinfacht oder automatisiert werden.

Wie die KI dieses Profil in Mails nutzen soll:
- Das Profil soll Substanz vermitteln, aber nicht wie ein Lebenslauf klingen.
- Stelle den Bezug zu ERP-/Excel-nahen Abläufen, Datenqualität, Auswertungen, wiederkehrenden Abstimmungen und kleinen Automatisierungen her.
- Keine übertriebenen Versprechen.
- Keine Unterstellung, dass das Unternehmen konkrete Probleme hat.
- Immer auf öffentlich sichtbare Themen der Website beziehen.
- Kurz, sachlich und direkt schreiben.
- Signatur immer:
Viele Grüße
Jann Körner
"""


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
