from __future__ import annotations

import json
from typing import Any

from config import OPENAI_API_KEY, OPENAI_MODEL
from prompt_store import get_sender_prompt


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _split_topics(raw_topics: str) -> list[str]:
    normalized = raw_topics.replace(";", ",")
    return [topic.strip() for topic in normalized.split(",") if topic.strip()]


def _topic_text(raw_topics: str) -> str:
    topics = _split_topics(raw_topics)
    if not topics:
        return "kaufmännische Verwaltungsabläufe"
    if len(topics) == 1:
        return topics[0]
    return ", ".join(topics[:-1]) + f" und {topics[-1]}"


def _greeting(contact_name: str) -> str:
    contact_name = _clean(contact_name)
    if not contact_name:
        return "Guten Tag,"
    lowered = contact_name.lower()
    if lowered.startswith("frau ") or lowered.startswith("herr "):
        return f"Sehr geehrte {contact_name},"
    return f"Guten Tag {contact_name},"


def _subject_for_angle(offer_angle: str) -> str:
    angle = _clean(offer_angle)
    if angle == "Daten/Auswertung":
        return "Kleiner Impuls zu Auswertungen und kaufmännischen Abläufen"
    if angle == "Automatisierung":
        return "Kleines Pilotprojekt für wiederkehrende Verwaltungsabläufe"
    return "Kompakter Effizienz-Check für kaufmännische Verwaltungsprozesse"


def generate_template_email(company: dict[str, Any], tone: str = "sachlich") -> dict[str, str]:
    company_name = _clean(company.get("company_name")) or "Ihr Unternehmen"
    contact_name = _clean(company.get("contact_name"))
    relevant_topics = _topic_text(_clean(company.get("relevant_topics")))
    website_notes = _clean(company.get("website_notes"))
    offer_angle = _clean(company.get("offer_angle")) or "Effizienz-Check"
    pain_point = _clean(company.get("pain_point_hypothesis"))

    if website_notes:
        opening = (
            f"auf Ihrer Website bin ich auf mehrere Themen gestoßen, die bei {company_name} "
            f"offenbar eine Rolle spielen: {relevant_topics}. Besonders notiert habe ich: {website_notes}"
        )
    else:
        opening = (
            f"ich bin auf {company_name} aufmerksam geworden, weil Themen wie {relevant_topics} "
            "in Immobilienverwaltungen oft eng mit wiederkehrenden kaufmännischen Abläufen verbunden sind."
        )

    angle_sentence = {
        "Automatisierung": "Dabei geht es mir vor allem um kleine Automatisierungen, die wiederkehrende Schritte rund um ERP, Excel oder Datenabgleiche reduzieren.",
        "Daten/Auswertung": "Dabei geht es mir vor allem um belastbare Auswertungen, saubere Datenflüsse und weniger manuelle Abstimmung zwischen Listen und Systemen.",
        "Effizienz-Check": "Dabei geht es mir vor allem um einen pragmatischen Effizienz-Check: wenige Abläufe ansehen, Reibungspunkte verstehen und nur sinnvolle Vereinfachungen umsetzen.",
    }.get(offer_angle, "Dabei geht es mir vor allem um pragmatische Vereinfachungen in wiederkehrenden Verwaltungsabläufen.")

    pain_sentence = (
        f"Meine Arbeitshypothese wäre, sich zunächst einen Bereich wie {pain_point} anzusehen."
        if pain_point
        else "Meine Arbeitshypothese wäre, zunächst 1-2 wiederkehrende Abläufe anzusehen, bei denen man Aufwand und Fehleranfälligkeit realistisch einschätzen kann."
    )

    if tone == "kurz":
        body = f"""{_greeting(contact_name)}

{opening}

Ich habe in einer Immobilienfirma im Accounting gearbeitet, mache aktuell meinen Master in Wirtschaftsinformatik und arbeite als Werkstudent bei Rossmann im Bereich Prozessautomatisierung sowie Datenanalyse und Data Engineering.

{angle_sentence} {pain_sentence}

Ich möchte kein großes Beratungsprojekt anbieten, sondern einen kleinen Pilot mit klar begrenztem Umfang. Wenn das grundsätzlich interessant ist, freue ich mich über einen kurzen Austausch.

Viele Grüße
Jann Körner"""
    elif tone == "direkt":
        body = f"""{_greeting(contact_name)}

{opening}

Ich melde mich, weil ich in solchen ERP- und Excel-nahen Verwaltungsprozessen häufig kleine, aber spürbare Entlastungsmöglichkeiten sehe, ohne dem Unternehmen ein großes Projekt aufzudrücken.

Kurz zu mir: Ich habe Accounting-Erfahrung aus einer Immobilienfirma, mache aktuell meinen Master in Wirtschaftsinformatik und arbeite als Werkstudent bei Rossmann in Prozessautomatisierung sowie Datenanalyse und Data Engineering.

{angle_sentence} {pain_sentence}

Hätten Sie grundsätzlich Interesse, dazu einmal 15-20 Minuten zu sprechen?

Viele Grüße
Jann Körner"""
    else:
        body = f"""{_greeting(contact_name)}

{opening}

Aus meiner Zeit im Accounting einer Immobilienfirma kenne ich viele manuelle Abläufe rund um ERP, Excel, Abrechnungen und wiederkehrende Abstimmungen. Aktuell mache ich meinen Master in Wirtschaftsinformatik und arbeite als Werkstudent bei Rossmann im Bereich Prozessautomatisierung sowie Datenanalyse und Data Engineering.

{angle_sentence} {pain_sentence}

Mir geht es nicht um ein großes Beratungsmandat, sondern um ein kleines Pilotprojekt mit 1-2 konkreten Prozessen. Wenn sich daraus kein sinnvoller Nutzen ergibt, sollte man es genauso klar erkennen können.

Falls das für Sie grundsätzlich interessant klingt, freue ich mich über einen kurzen Austausch.

Viele Grüße
Jann Körner"""

    return {
        "subject": _subject_for_angle(offer_angle),
        "body": body,
        "variant": f"Template/{tone}/{offer_angle}",
    }


def generate_follow_up_email(company: dict[str, Any], include_no_pressure_line: bool = True) -> dict[str, str]:
    contact_name = _clean(company.get("contact_name"))
    subject = "Kurze Nachfrage zu meiner Nachricht"
    no_pressure = (
        "\n\nFalls das aktuell kein Thema ist, ist das völlig in Ordnung."
        if include_no_pressure_line
        else ""
    )
    body = f"""{_greeting(contact_name)}

ich wollte kurz auf meine letzte Nachricht zurückkommen. Es ging um die Frage, ob sich bei Ihnen 1-2 wiederkehrende Verwaltungsprozesse rund um ERP, Excel, Auswertungen oder Datenabgleiche pragmatisch vereinfachen lassen.

Mir geht es weiterhin nur um einen kleinen, klar abgegrenzten Blick auf mögliche Entlastung, nicht um ein großes Beratungsprojekt.{no_pressure}

Viele Grüße
Jann Körner"""
    return {"subject": subject, "body": body, "variant": "Template/Follow-up"}


def generate_openai_email(company: dict[str, Any], tone: str = "sachlich") -> dict[str, str]:
    if not OPENAI_API_KEY:
        raise RuntimeError("Kein OPENAI_API_KEY konfiguriert.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Das Paket 'openai' ist nicht installiert.") from exc

    client = OpenAI(api_key=OPENAI_API_KEY)
    sender_prompt = get_sender_prompt()
    system_prompt = f"""
Du formulierst kurze deutsche B2B-Akquise-Mails für kleine Immobilienverwaltungen.
Nutze immer diesen bearbeitbaren Absenderprompt:
{sender_prompt}

Regeln:
- Keine übertriebenen Versprechen.
- Keine erfundenen Ansprechpartner, Prozesse oder Probleme.
- Keine Unterstellung, dass das Unternehmen konkrete Probleme hat.
- Bezug nur auf öffentlich sichtbare Themen aus den Eingaben.
- Fokus auf ERP-/Excel-nahe Abläufe, Auswertungen, Datenqualität, kleine Automatisierungen.
- Klarer Call-to-Action für einen kurzen Austausch.
- Signatur exakt:
Viele Grüße
Jann Körner
- Gib ausschließlich valides JSON zurück: {"subject": "...", "body": "..."}.
""".strip()
    user_prompt = json.dumps(
        {
            "company_name": _clean(company.get("company_name")),
            "contact_name": _clean(company.get("contact_name")),
            "contact_role": _clean(company.get("contact_role")),
            "company_type": _clean(company.get("company_type")),
            "city": _clean(company.get("city")),
            "relevant_topics": _clean(company.get("relevant_topics")),
            "website_notes": _clean(company.get("website_notes")),
            "pain_point_hypothesis": _clean(company.get("pain_point_hypothesis")),
            "offer_angle": _clean(company.get("offer_angle")),
            "tone": tone,
            "sender_prompt": sender_prompt,
        },
        ensure_ascii=False,
    )

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.35,
    )
    content = response.choices[0].message.content or ""
    parsed = json.loads(content)
    return {
        "subject": _clean(parsed.get("subject")),
        "body": _clean(parsed.get("body")),
        "variant": f"OpenAI/{OPENAI_MODEL}/{tone}",
    }


def generate_initial_email(
    company: dict[str, Any],
    tone: str = "sachlich",
    use_openai: bool = False,
) -> dict[str, str]:
    if use_openai and OPENAI_API_KEY:
        try:
            return generate_openai_email(company, tone=tone)
        except Exception as exc:
            fallback = generate_template_email(company, tone=tone)
            fallback["variant"] += f" (Fallback nach OpenAI-Fehler: {exc})"
            return fallback
    return generate_template_email(company, tone=tone)


def create_gmail_draft_stub(*_args: Any, **_kwargs: Any) -> dict[str, str | bool]:
    return {
        "implemented": False,
        "message": (
            "Gmail-Drafts können über gmail_service.py erstellt werden. "
            "Es gibt bewusst keinen Gmail-Send-Call."
        ),
    }
