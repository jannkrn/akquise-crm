from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # Allows DB initialization before dependencies are installed.
    def load_dotenv(*_args, **_kwargs) -> bool:
        return False


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = BASE_DIR / "exports"
DB_PATH = DATA_DIR / "akquise.db"
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"

load_dotenv(ENV_PATH)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_CONFIGURED = bool(OPENAI_API_KEY)
ENV_FILE_EXISTS = ENV_PATH.exists()

SENDER_NAME = "Jann Körner"
SENDER_PROFILE = (
    "Ich habe bei einer Immobilienfirma im Accounting gearbeitet und kenne daher viele "
    "manuelle Prozesse aus der Praxis, insbesondere rund um ERP-nahe Abläufe, Excel, "
    "Abstimmungen, Abrechnungen und kaufmännische Verwaltung. Momentan mache ich meinen "
    "Master in Wirtschaftsinformatik und arbeite als Werkstudent bei Rossmann im Bereich "
    "Prozessautomatisierung, Datenanalyse und Data Engineering. Ich möchte kleinen "
    "Immobilienunternehmen keine große Beratung verkaufen, sondern kleine Pilotprojekte "
    "anbieten, bei denen 1-2 wiederkehrende Prozesse geprüft und nur bei erkennbarem Nutzen "
    "vereinfacht oder automatisiert werden."
)

SENDER_PROFILE_MAIL_HINT = (
    "Nutze dieses Profil in der Mail konkret, aber knapp. Es soll Substanz vermitteln: "
    "Accounting-Erfahrung in einer Immobilienfirma, aktueller Master in Wirtschaftsinformatik "
    "und Werkstudententätigkeit bei Rossmann in Prozessautomatisierung, Datenanalyse und "
    "Data Engineering. Vermeide Lebenslaufstil; verbinde das Profil mit ERP-/Excel-nahen "
    "Abläufen, Auswertungen, Datenqualität und kleinen Automatisierungen."
)


def env_example_contains_secret() -> bool:
    if not ENV_EXAMPLE_PATH.exists():
        return False
    try:
        content = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    except OSError:
        return False
    return "OPENAI_API_KEY=sk-" in content


def _path_from_env(name: str, default: Path) -> Path:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    path = Path(raw_value)
    return path if path.is_absolute() else BASE_DIR / path


GMAIL_CREDENTIALS_PATH = _path_from_env("GMAIL_CREDENTIALS_PATH", BASE_DIR / "credentials.json")
GMAIL_TOKEN_PATH = _path_from_env("GMAIL_TOKEN_PATH", DATA_DIR / "gmail_token.json")


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
