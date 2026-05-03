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
    profile_sentence = (
        "Aus meiner Zeit im Accounting einer Immobilienfirma kenne ich ERP- und Excel-nahe "
        "Abstimmungen, Abrechnungen und kaufmännische Verwaltungsabläufe aus der Praxis. "
        "Heute mache ich meinen Master in Wirtschaftsinformatik in Halle und arbeite bei "
        "Rossmann als Werkstudent im Bereich Prozessautomatisierung, Datenanalyse und Data Engineering."
    )

    cleaned = _replace_sales_phrases(cleaned)

    if _should_use_profile_bridge(source):
        cleaned = _merge_profile_bridge(cleaned, profile_sentence)
        cleaned = _remove_duplicate_profile_fragments(cleaned, profile_sentence)

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
    cleaned = _normalize_phone_cta(cleaned, phone)
    if phone and phone not in re.sub(r"\s+", "", cleaned):
        cleaned = _insert_before_signoff(
            cleaned,
            f"Wenn das grundsätzlich interessant ist, freue ich mich über einen kurzen Austausch; Rückmeldung gerne auch per Telefon: {phone}.",
        )

    return _normalize_mail_spacing(cleaned)


def _should_use_profile_bridge(prompt: str) -> bool:
    return all(term in prompt for term in ["Accounting", "Rossmann", "Wirtschaftsinformatik"])


def _merge_profile_bridge(body: str, profile_sentence: str) -> str:
    paragraphs = body.split("\n\n")
    for index, paragraph in enumerate(paragraphs):
        lowered = paragraph.lower()
        if "rossmann" in lowered or "master in wirtschaftsinformatik" in lowered:
            kept_sentences = [
                sentence
                for sentence in re.split(r"(?<=[.!?])\s+", paragraph.strip())
                if not _is_profile_fragment(sentence)
            ]
            if kept_sentences:
                paragraphs[index] = " ".join(kept_sentences)
                paragraphs.insert(index + 1, profile_sentence)
            else:
                paragraphs[index] = profile_sentence
            return "\n\n".join(paragraphs)

    insert_at = 1 if len(paragraphs) > 1 else len(paragraphs)
    paragraphs.insert(insert_at, profile_sentence)
    return "\n\n".join(paragraphs)


def _remove_duplicate_profile_fragments(body: str, profile_sentence: str) -> str:
    paragraphs = []
    profile_seen = False
    for paragraph in body.split("\n\n"):
        if paragraph.strip() == profile_sentence:
            if profile_seen:
                continue
            profile_seen = True
            paragraphs.append(paragraph)
            continue
        if profile_seen and _is_profile_fragment(paragraph):
            continue
        paragraphs.append(paragraph)
    return "\n\n".join(paragraphs)


def _is_profile_fragment(text: str) -> bool:
    lowered = text.lower().strip()
    return "rossmann" in lowered or "master in wirtschaftsinformatik" in lowered


def _normalize_phone_cta(body: str, phone: str) -> str:
    if not phone:
        return body
    body = re.sub(
        r"(?im)^\s*Rufen Sie mich gerne an unter\s+[+\d\s()/.-]+\.?\s*$",
        f"Rückmeldung gerne auch per Telefon: {phone}.",
        body,
    )
    body = re.sub(
        r"(?im)^\s*Rückmeldung gerne auch per Telefon:\s*[+\d\s()/.-]+\.?\s*$",
        f"Rückmeldung gerne auch per Telefon: {phone}.",
        body,
    )
    return body


def _replace_sales_phrases(body: str) -> str:
    replacements = {
        "bin beeindruckt von Ihrem Fokus auf digitale Prozesse": "bin auf Ihre öffentlich sichtbaren Verwaltungsthemen aufmerksam geworden",
        "einen Mehrwert schaffen könnten": "konkret sinnvoll sein könnten",
        "einen Mehrwert schaffen": "konkret sinnvoll sein",
        "Ich würde mich freuen, in einem kurzen Austausch kurz zu besprechen, wie": "Wenn das grundsätzlich interessant ist, können wir kurz besprechen, ob",
        "Ich würde mich freuen, in einem kurzen Austausch zu besprechen, wie": "Wenn das grundsätzlich interessant ist, können wir kurz besprechen, ob",
        "zu erörtern": "kurz zu besprechen",
        "Optimierung Ihrer Verwaltungsprozesse": "Kleiner Blick auf wiederkehrende Verwaltungsprozesse",
    }
    cleaned = body
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    cleaned = cleaned.replace(
        "Ich würde mich freuen, in einem kurzen Austausch kurz zu besprechen, wie",
        "Wenn das grundsätzlich interessant ist, können wir kurz besprechen, ob",
    )
    return cleaned


def _normalize_mail_spacing(body: str) -> str:
    cleaned = re.sub(r"([.!?])\n(Rückmeldung gerne auch per Telefon:)", r"\1\n\n\2", body)
    cleaned = re.sub(r"([.!?])\n(Viele Grüße\nJann Körner)", r"\1\n\n\2", cleaned)
    return cleaned.strip()


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
