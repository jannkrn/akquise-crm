from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse

from config import OPENAI_API_KEY, OPENAI_MODEL
from crm_service import COMPANY_TYPES, OFFER_ANGLES
from prompt_store import enforce_sender_prompt_in_email, get_sender_prompt


class WebsiteAnalysisError(RuntimeError):
    pass


def normalize_url(url: str) -> str:
    cleaned = url.strip()
    if not cleaned:
        raise WebsiteAnalysisError("Bitte zuerst eine Website-URL eintragen.")
    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"https://{cleaned}"
    parsed = urlparse(cleaned)
    if not parsed.netloc:
        raise WebsiteAnalysisError("Die Website-URL sieht nicht gültig aus.")
    return cleaned


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def fetch_website_text(url: str) -> dict[str, str]:
    normalized_url = normalize_url(url)
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise WebsiteAnalysisError(
            "Für die Website-Analyse fehlen requests/beautifulsoup4. Bitte requirements.txt installieren."
        ) from exc

    try:
        response = requests.get(
            normalized_url,
            timeout=15,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
                )
            },
        )
        response.raise_for_status()
    except Exception as exc:
        raise WebsiteAnalysisError(f"Website konnte nicht gelesen werden: {exc}") from exc

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    title = _clean_text(soup.title.get_text(" ")) if soup.title else ""
    meta_description = ""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        meta_description = _clean_text(str(meta["content"]))

    visible_text = _clean_text(soup.get_text(" "))
    text = "\n".join(part for part in [title, meta_description, visible_text] if part)
    return {"url": normalized_url, "text": text[:18000]}


def _extract_json(raw_content: str) -> dict[str, Any]:
    cleaned = raw_content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def analyze_company_website(url: str) -> dict[str, str]:
    if not OPENAI_API_KEY:
        raise WebsiteAnalysisError("Kein OPENAI_API_KEY konfiguriert. Die KI-Ausfüllfunktion braucht die OpenAI API.")

    page = fetch_website_text(url)

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise WebsiteAnalysisError("Das Paket 'openai' ist nicht installiert.") from exc

    client = OpenAI(api_key=OPENAI_API_KEY)
    sender_prompt = get_sender_prompt()
    system_prompt = f"""
Du analysierst öffentlich sichtbare Websites von Immobilienunternehmen für ein lokales Akquise-CRM.

Fülle CRM-Felder so gut wie möglich aus. Erfinde keine Namen, E-Mail-Adressen, Telefonnummern oder konkreten Prozesse.
Wenn etwas nicht klar aus dem Website-Text hervorgeht, lasse das Feld leer oder formuliere es vorsichtig als Hypothese.

Der folgende bearbeitbare Absenderprompt ist die verbindliche Quelle für Profil, Positionierung, Tonalität und Kontaktangaben:
{sender_prompt}

Erlaubte company_type-Werte: {", ".join(COMPANY_TYPES)}
Erlaubte offer_angle-Werte: {", ".join(OFFER_ANGLES)}

Gib ausschließlich valides JSON zurück mit diesen String-Feldern:
company_name, website, city, contact_name, contact_role, email, phone, company_type,
relevant_topics, website_notes, pain_point_hypothesis, offer_angle,
email_subject, email_body, email_variant, status, next_step, notes.

Mail-Regeln:
- Deutsch
- kurz, sachlich, direkt
- keine übertriebenen Versprechen
- keine Unterstellung konkreter Probleme
- Bezug auf öffentlich sichtbare Themen
- Fokus auf ERP-/Excel-nahe Abläufe, Auswertungen, Datenqualität, kleine Automatisierungen
- klarer Call-to-Action für kurzen Austausch
- konkrete Fakten aus dem Absenderprompt wie Studienort, Rossmann-Rolle und Telefonnummer müssen korrekt übernommen werden
- die Telefonnummer gehört als kurzer Rückmelde-Hinweis vor die Grußformel, nicht als technische Signatur
- Signatur exakt:
Viele Grüße
Jann Körner
""".strip()
    user_prompt = json.dumps(
        {
            "website": page["url"],
            "website_text": page["text"],
        },
        ensure_ascii=False,
    )

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
    except Exception as exc:
        raise WebsiteAnalysisError(f"OpenAI-Analyse fehlgeschlagen: {exc}") from exc
    content = response.choices[0].message.content or ""
    parsed = _extract_json(content)

    allowed_fields = {
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
        "status",
        "next_step",
        "notes",
    }
    result = {field: str(parsed.get(field) or "").strip() for field in allowed_fields}
    result["email_body"] = enforce_sender_prompt_in_email(result["email_body"], sender_prompt)
    result["website"] = result["website"] or page["url"]
    result["email_variant"] = result["email_variant"] or f"OpenAI/Website/{OPENAI_MODEL}"
    result["status"] = result["status"] or "Entwurf erstellt"
    result["next_step"] = result["next_step"] or "Entwurf prüfen und ggf. Gmail-Draft erstellen."
    return result
