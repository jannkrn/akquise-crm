from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from config import (
    DB_PATH,
    ENV_FILE_EXISTS,
    ENV_PATH,
    EXPORTS_DIR,
    OPENAI_API_KEY,
    ensure_directories,
    env_example_contains_secret,
)
from company_discovery_service import CompanyDiscoveryError, discover_company_candidates
from crm_service import (
    COMPANY_FIELDS,
    COMPANY_TYPES,
    OFFER_ANGLES,
    RESPONSE_TYPES,
    STATUSES,
    companies_df,
    create_company,
    dashboard_stats,
    delete_company,
    due_followups,
    followups_df,
    get_company,
    import_companies,
    interested_leads_df,
    list_companies,
    mark_first_mail_sent,
    mark_status,
    update_company,
    update_follow_up,
)
from db import init_db
from email_generator import (
    generate_follow_up_email,
    generate_initial_email,
)
from gmail_service import (
    GmailDraftError,
    build_gmail_draft_url,
    create_gmail_draft,
    gmail_status,
)
from prompt_store import (
    DEFAULT_SENDER_PROMPT,
    get_sender_prompt,
    reset_sender_prompt,
    save_sender_prompt,
)
from website_ai_service import WebsiteAnalysisError, analyze_company_website


DISPLAY_COLUMNS = [
    "id",
    "company_name",
    "city",
    "contact_name",
    "email",
    "company_type",
    "relevant_topics",
    "offer_angle",
    "action_type",
    "gmail_draft_url",
    "status",
    "follow_up_date",
    "response_type",
    "next_step",
]


def setup() -> None:
    ensure_directories()
    init_db()
    st.set_page_config(
        page_title="Akquise-CRM Immobilien",
        layout="wide",
    )


def to_df(rows: list[dict[str, Any]]) -> pd.DataFrame:
    enriched_rows = []
    for row in rows:
        item = dict(row)
        item["gmail_draft_url"] = build_gmail_draft_url(
            message_id=str(item.get("gmail_draft_message_id") or ""),
            draft_id=str(item.get("gmail_draft_id") or ""),
        )
        enriched_rows.append(item)

    df = pd.DataFrame(enriched_rows)
    if df.empty:
        return pd.DataFrame(columns=DISPLAY_COLUMNS)
    return df


def display_table(rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    df = to_df(rows)
    selected_columns = columns or DISPLAY_COLUMNS
    available = [column for column in selected_columns if column in df.columns]
    column_config = {}
    if "gmail_draft_url" in available:
        column_config["gmail_draft_url"] = st.column_config.LinkColumn(
            "Gmail-Draft",
            display_text="öffnen",
            help="Direktlink ist ein Gmail-Weblink auf Basis der von der API gelieferten Message-ID.",
        )
    st.dataframe(
        df[available],
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
    )


def company_options(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        f"{row.get('company_name', '')} | {row.get('city', '')} | #{row.get('id')}": int(row["id"])
        for row in rows
    }


def select_index(options: list[str], current_value: str) -> int:
    return options.index(current_value) if current_value in options else 0


def form_defaults(company: dict[str, Any] | None = None) -> dict[str, str]:
    company = company or {}
    defaults = {field: str(company.get(field) or "") for field in COMPANY_FIELDS}
    if not company:
        prefill = st.session_state.get("company_ai_prefill", {})
        for field, value in prefill.items():
            if field in defaults and value:
                defaults[field] = str(value)
    return defaults


def render_ai_prefill_box() -> None:
    with st.expander("Automatisch mit KI ausfüllen", expanded=False):
        st.caption(
            "Die App liest die angegebene Website, extrahiert öffentlich sichtbare Informationen "
            "und füllt das Formular als Vorschlag vor. Bitte danach alles kurz prüfen."
        )
        url = st.text_input(
            "Website für KI-Analyse",
            value=st.session_state.get("ai_prefill_url", ""),
            placeholder="https://www.beispiel-hausverwaltung.de",
            key="ai_prefill_url",
        )

        col1, col2 = st.columns([1, 2])
        disabled = not bool(OPENAI_API_KEY)
        if col1.button("Automatisch mit KI ausfüllen", disabled=disabled):
            try:
                with st.spinner("Website wird gelesen und Felder werden ausgefüllt..."):
                    st.session_state["company_ai_prefill"] = analyze_company_website(url)
                    st.session_state["company_form_version"] = st.session_state.get("company_form_version", 0) + 1
                st.success("KI-Vorschlag erstellt. Das Formular darunter wurde vorbefüllt.")
                st.rerun()
            except WebsiteAnalysisError as exc:
                st.error(str(exc))

        if col2.button("KI-Vorschlag zurücksetzen"):
            st.session_state.pop("company_ai_prefill", None)
            st.session_state["company_form_version"] = st.session_state.get("company_form_version", 0) + 1
            st.success("KI-Vorschlag zurückgesetzt.")
            st.rerun()

        if disabled:
            st.info(
                "Kein OpenAI API-Key konfiguriert. Trage einen Key in `.env` ein und starte Streamlit neu."
            )
        elif st.session_state.get("company_ai_prefill"):
            st.success("Aktueller KI-Vorschlag ist geladen und kann unten bearbeitet werden.")


def render_company_discovery_box() -> None:
    with st.expander("Weitere passende Unternehmen finden", expanded=False):
        st.caption(
            "Die App sucht öffentlich sichtbare Hausverwaltungen, Immobilienverwaltungen und WEG-Verwaltungen "
            "im angegebenen Umfeld, filtert bereits gespeicherte Websites heraus und analysiert neue Kandidaten per KI."
        )
        col1, col2, col3 = st.columns([2, 1, 1])
        location = col1.text_input(
            "Ort oder Region",
            value=st.session_state.get("discovery_location", ""),
            placeholder="z. B. Leipzig, Halle, Sachsen-Anhalt",
            key="discovery_location",
        )
        radius_km = col2.number_input("Umkreis in km", min_value=5, max_value=250, value=30, step=5)
        max_candidates = col3.number_input("Vorschläge", min_value=1, max_value=10, value=5, step=1)

        disabled = not bool(OPENAI_API_KEY)
        if st.button("Passende Unternehmen suchen", disabled=disabled):
            try:
                with st.spinner("Suche läuft, Websites werden geprüft und per KI analysiert..."):
                    st.session_state["company_discovery_results"] = discover_company_candidates(
                        location=location,
                        radius_km=int(radius_km),
                        max_candidates=int(max_candidates),
                    )
                st.success("Suche abgeschlossen.")
                st.rerun()
            except CompanyDiscoveryError as exc:
                st.error(str(exc))

        if disabled:
            st.info("Kein OpenAI API-Key konfiguriert. Die Suche mit KI-Analyse ist deshalb deaktiviert.")

        candidates = st.session_state.get("company_discovery_results", [])
        if not candidates:
            return

        st.write(f"{len(candidates)} neue Kandidaten gefunden:")
        for index, candidate in enumerate(candidates, start=1):
            analysis = candidate.get("analysis") or {}
            title = analysis.get("company_name") or candidate.get("title") or "Unbekanntes Unternehmen"
            with st.container(border=True):
                st.markdown(f"**{index}. {title}**")
                st.write(candidate.get("website", ""))
                if candidate.get("snippet"):
                    st.caption(candidate["snippet"])
                if candidate.get("error"):
                    st.warning(f"KI-Analyse nicht vollständig: {candidate['error']}")
                elif analysis:
                    st.write("Themen:", analysis.get("relevant_topics") or "-")
                    st.write("Ansatz:", analysis.get("offer_angle") or "-")
                    st.caption(analysis.get("website_notes") or "")

                if st.button("Ins Formular übernehmen", key=f"use_discovery_candidate_{index}"):
                    prefill = {
                        "company_name": title,
                        "website": candidate.get("website", ""),
                        "status": "Entwurf erstellt" if analysis.get("email_body") else "Recherchiert",
                    }
                    prefill.update(analysis)
                    st.session_state["company_ai_prefill"] = prefill
                    st.session_state["company_form_version"] = st.session_state.get("company_form_version", 0) + 1
                    st.success("Kandidat wurde ins Formular übernommen.")
                    st.rerun()


def render_company_form(company: dict[str, Any] | None = None) -> None:
    defaults = form_defaults(company)
    is_edit = company is not None
    form_version = st.session_state.get("company_form_version", 0)
    form_key = f"company_form_{company['id']}" if is_edit else f"company_form_new_{form_version}"

    with st.form(form_key):
        st.subheader("Stammdaten")
        company_name = st.text_input("Unternehmensname *", value=defaults["company_name"])
        website = st.text_input("Website", value=defaults["website"])
        city = st.text_input("Stadt", value=defaults["city"])

        col1, col2, col3 = st.columns(3)
        with col1:
            contact_name = st.text_input("Ansprechpartner", value=defaults["contact_name"])
        with col2:
            contact_role = st.text_input("Rolle", value=defaults["contact_role"])
        with col3:
            email = st.text_input("E-Mail", value=defaults["email"])

        col1, col2, col3 = st.columns(3)
        with col1:
            phone = st.text_input("Telefon", value=defaults["phone"])
        with col2:
            company_type = st.selectbox(
                "Unternehmenstyp",
                COMPANY_TYPES,
                index=select_index(COMPANY_TYPES, defaults["company_type"]),
            )
        with col3:
            offer_angle = st.selectbox(
                "Angebotswinkel",
                OFFER_ANGLES,
                index=select_index(OFFER_ANGLES, defaults["offer_angle"]),
            )

        relevant_topics = st.text_input(
            "Relevante Themen",
            value=defaults["relevant_topics"],
            placeholder="Betriebskosten, WEG, Forderungsmanagement, Monatsabschluss, ERP, Excel",
        )
        website_notes = st.text_area("Website-Notizen", value=defaults["website_notes"], height=100)
        pain_point_hypothesis = st.text_area(
            "Pain-Point-Hypothese",
            value=defaults["pain_point_hypothesis"],
            height=80,
        )

        st.subheader("Akquise")
        col1, col2, col3 = st.columns(3)
        with col1:
            status = st.selectbox("Status", STATUSES, index=select_index(STATUSES, defaults["status"]))
        with col2:
            response_type = st.selectbox(
                "Antworttyp",
                RESPONSE_TYPES,
                index=select_index(RESPONSE_TYPES, defaults["response_type"]),
            )
        with col3:
            email_variant = st.text_input("Mail-Variante", value=defaults["email_variant"])

        col1, col2, col3 = st.columns(3)
        with col1:
            first_contact_date = st.text_input("Erstkontakt-Datum", value=defaults["first_contact_date"], placeholder="YYYY-MM-DD")
        with col2:
            follow_up_date = st.text_input("Follow-up-Datum", value=defaults["follow_up_date"], placeholder="YYYY-MM-DD")
        with col3:
            last_contact_date = st.text_input("Letzter Kontakt", value=defaults["last_contact_date"], placeholder="YYYY-MM-DD")

        email_subject = st.text_input("Betreff", value=defaults["email_subject"])
        email_body = st.text_area("E-Mail-Text", value=defaults["email_body"], height=180)
        next_step = st.text_input("Nächster Schritt", value=defaults["next_step"])
        notes = st.text_area("Notizen", value=defaults["notes"], height=100)
        prepare_gmail_draft = st.checkbox(
            "Nach dem Speichern Gmail-Entwurf vorbereiten",
            value=False,
            help=(
                "Erzeugt nur den Mailtext und merkt das Unternehmen für den Tab Mail-Entwürfe vor. "
                "Der Gmail-Draft wird erst nach sichtbarer Prüfung per Button erstellt."
            ),
        )

        submitted = st.form_submit_button("Speichern")

    if submitted:
        payload = {
            "company_name": company_name,
            "website": website,
            "city": city,
            "contact_name": contact_name,
            "contact_role": contact_role,
            "email": email,
            "phone": phone,
            "company_type": company_type,
            "relevant_topics": relevant_topics,
            "website_notes": website_notes,
            "pain_point_hypothesis": pain_point_hypothesis,
            "offer_angle": offer_angle,
            "email_subject": email_subject,
            "email_body": email_body,
            "email_variant": email_variant,
            "status": status,
            "first_contact_date": first_contact_date,
            "follow_up_date": follow_up_date,
            "last_contact_date": last_contact_date,
            "response_type": response_type,
            "next_step": next_step,
            "notes": notes,
        }
        try:
            if is_edit:
                update_company(int(company["id"]), payload, require_name=True)
                saved_id = int(company["id"])
                message = "Unternehmen aktualisiert."
            else:
                saved_id = create_company(payload)
                message = "Unternehmen angelegt."
                st.session_state.pop("company_ai_prefill", None)
                st.session_state["company_form_version"] = form_version + 1

            if prepare_gmail_draft:
                saved_company = get_company(saved_id) or payload
                draft = generate_initial_email(saved_company, tone="sachlich", use_openai=False)
                update_company(
                    saved_id,
                    {
                        "email_subject": draft["subject"],
                        "email_body": draft["body"],
                        "email_variant": draft["variant"],
                        "status": "Entwurf erstellt",
                    },
                )
                st.session_state[f"draft_{saved_id}"] = draft
                st.session_state["draft_company_id"] = saved_id
                message += " Mail-Entwurf wurde vorbereitet und ist im Tab Mail-Entwürfe vorausgewählt."

            st.session_state["flash_success"] = message
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))


def render_dashboard() -> None:
    stats = dashboard_stats()
    due = stats["due_followups"]
    action_items = stats["dashboard_action_items"]

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Unternehmen gesamt", stats["total"])
    col2.metric("Offene Entwürfe", stats["open_draft_count"])
    col3.metric("Follow-ups fällig", len(due))
    col4.metric("Antwortquote", f"{stats['response_rate']:.1%}")
    col5.metric("Gesprächsquote", f"{stats['conversation_rate']:.1%}")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Status")
        status_df = pd.DataFrame(stats["status_counts"])
        if status_df.empty:
            st.info("Noch keine Unternehmen angelegt.")
        else:
            st.dataframe(status_df, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("Wichtigste Leads")
        display_table(list_companies(), DISPLAY_COLUMNS)

    st.subheader("Heute oder überfällig")
    if action_items:
        display_table(action_items, DISPLAY_COLUMNS)
        draft_items = [item for item in action_items if item.get("status") == "Entwurf erstellt"]
        if draft_items:
            st.caption("Nach manuellem Versand in Gmail hier als Erstmail gesendet markieren.")
            for item in draft_items:
                label = f"{item.get('company_name', 'Unternehmen')} als Erstmail gesendet markieren"
                if st.button(label, key=f"dashboard_first_mail_sent_{item['id']}"):
                    mark_first_mail_sent(int(item["id"]))
                    st.session_state["flash_success"] = (
                        f"{item.get('company_name', 'Unternehmen')} wurde als Erstmail gesendet markiert. "
                        "Follow-up wurde auf +7 Tage gesetzt."
                    )
                    st.rerun()
    else:
        st.success("Keine offenen Entwürfe oder fälligen Follow-ups.")


def render_companies() -> None:
    st.subheader("Suchen und filtern")
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    search = col1.text_input("Suche", placeholder="Unternehmen, Stadt, Thema, E-Mail")
    status = col2.selectbox("Statusfilter", [""] + STATUSES, format_func=lambda value: value or "Alle")
    offer_angle = col3.selectbox("Winkel", [""] + OFFER_ANGLES, format_func=lambda value: value or "Alle")
    overdue_only = col4.checkbox("Nur fällige Follow-ups")

    rows = list_companies(search=search, status=status, offer_angle=offer_angle, overdue_only=overdue_only)
    display_table(rows)

    create_tab, edit_tab = st.tabs(["Anlegen", "Bearbeiten/Löschen"])
    with create_tab:
        render_company_discovery_box()
        render_ai_prefill_box()
        render_company_form()

    with edit_tab:
        all_rows = list_companies()
        options = company_options(all_rows)
        if not options:
            st.info("Noch keine Unternehmen vorhanden.")
            return
        selected_label = st.selectbox("Unternehmen auswählen", list(options.keys()))
        selected_id = options[selected_label]
        company = get_company(selected_id)
        if company:
            render_company_form(company)
            st.divider()
            confirm_delete = st.checkbox("Ich möchte dieses Unternehmen löschen.")
            if st.button("Unternehmen löschen", disabled=not confirm_delete):
                delete_company(selected_id)
                st.success("Unternehmen gelöscht.")
                st.rerun()


def render_email_drafts() -> None:
    rows = list_companies()
    options = company_options(rows)
    if not options:
        st.info("Lege zuerst ein Unternehmen an.")
        return

    labels = list(options.keys())
    requested_id = st.session_state.get("draft_company_id")
    default_index = 0
    if requested_id:
        for index, label in enumerate(labels):
            if options[label] == requested_id:
                default_index = index
                break

    selected_label = st.selectbox("Unternehmen", labels, index=default_index, key="draft_company")
    selected_id = options[selected_label]
    company = get_company(selected_id) or {}

    with st.form("draft_generation_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            contact_name = st.text_input("Ansprechpartner", value=str(company.get("contact_name") or ""))
        with col2:
            tone = st.selectbox("Ton", ["sachlich", "kurz", "direkt"])
        with col3:
            offer_angle = st.selectbox(
                "Winkel",
                OFFER_ANGLES,
                index=select_index(OFFER_ANGLES, str(company.get("offer_angle") or "")),
            )

        relevant_topics = st.text_input("Relevante Themen", value=str(company.get("relevant_topics") or ""))
        website_notes = st.text_area("Website-Notizen", value=str(company.get("website_notes") or ""), height=100)
        pain_point_hypothesis = st.text_area(
            "Pain-Point-Hypothese",
            value=str(company.get("pain_point_hypothesis") or ""),
            height=80,
        )
        use_openai = st.checkbox(
            "OpenAI zur Formulierung nutzen",
            value=False,
            disabled=not bool(OPENAI_API_KEY),
            help="Ohne OPENAI_API_KEY wird immer die Template-Generierung genutzt.",
        )
        generated = st.form_submit_button("Mail-Entwurf generieren")

    if generated:
        draft_company = {
            **company,
            "contact_name": contact_name,
            "relevant_topics": relevant_topics,
            "website_notes": website_notes,
            "pain_point_hypothesis": pain_point_hypothesis,
            "offer_angle": offer_angle,
        }
        st.session_state[f"draft_{selected_id}"] = generate_initial_email(
            draft_company,
            tone=tone,
            use_openai=use_openai,
        )

    draft = st.session_state.get(
        f"draft_{selected_id}",
        {
            "subject": str(company.get("email_subject") or ""),
            "body": str(company.get("email_body") or ""),
            "variant": str(company.get("email_variant") or ""),
        },
    )

    st.subheader("Entwurf prüfen")
    subject = st.text_input("Betreff", value=draft.get("subject", ""), key=f"subject_{selected_id}")
    body = st.text_area("E-Mail-Text", value=draft.get("body", ""), height=320, key=f"body_{selected_id}")
    variant = st.text_input("Variante", value=draft.get("variant", ""), key=f"variant_{selected_id}")

    col1, col2 = st.columns([1, 1])
    if col1.button("Entwurf beim Unternehmen speichern"):
        update_company(
            selected_id,
            {
                "email_subject": subject,
                "email_body": body,
                "email_variant": variant,
                "offer_angle": offer_angle if "offer_angle" in locals() else str(company.get("offer_angle") or ""),
                "status": "Entwurf erstellt",
            },
        )
        st.success("Entwurf gespeichert.")
        st.rerun()

    with col2:
        gmail_config = gmail_status()
        has_recipient = bool(str(company.get("email") or "").strip())
        can_create_draft = bool(subject.strip() and body.strip() and has_recipient)

        if st.button("Gmail-Draft erstellen", disabled=not can_create_draft):
            try:
                gmail_draft = create_gmail_draft(
                    to=str(company.get("email") or ""),
                    subject=subject,
                    body=body,
                )
                update_company(
                    selected_id,
                    {
                        "email_subject": subject,
                        "email_body": body,
                        "email_variant": variant,
                        "gmail_draft_id": gmail_draft["draft_id"],
                        "gmail_draft_message_id": gmail_draft["message_id"],
                        "gmail_draft_thread_id": gmail_draft["thread_id"],
                        "status": "Entwurf erstellt",
                    },
                )
                st.session_state["flash_success"] = (
                    f"Gmail-Draft erstellt. Draft-ID: {gmail_draft['draft_id']}"
                )
                st.rerun()
            except GmailDraftError as exc:
                st.error(str(exc))

        if company.get("gmail_draft_id"):
            st.caption(f"Gmail-Draft-ID: {company['gmail_draft_id']}")
            draft_url = build_gmail_draft_url(
                message_id=str(company.get("gmail_draft_message_id") or ""),
                draft_id=str(company.get("gmail_draft_id") or ""),
            )
            if draft_url:
                st.link_button("Gmail-Draft öffnen", draft_url)
        elif not gmail_config["credentials_exists"]:
            st.caption("Gmail ist noch nicht konfiguriert. Lege credentials.json im Projektordner ab.")
        elif not has_recipient:
            st.caption("Für Gmail-Drafts braucht das Unternehmen eine E-Mail-Adresse.")
        else:
            st.caption("Gmail-Drafts nutzen nur den Scope gmail.compose. Es gibt keinen Send-Call.")


def render_followups() -> None:
    st.subheader("Fällige Follow-ups")
    due = due_followups()
    if due:
        display_table(due)
    else:
        st.success("Keine fälligen Follow-ups.")

    rows = list_companies()
    options = company_options(rows)
    if not options:
        return

    st.subheader("Status aktualisieren")
    selected_label = st.selectbox("Unternehmen auswählen", list(options.keys()), key="followup_company")
    selected_id = options[selected_label]
    company = get_company(selected_id) or {}

    col1, col2, col3, col4, col5 = st.columns(5)
    if col1.button("Als Erstmail gesendet markieren"):
        mark_first_mail_sent(selected_id)
        st.success("Erstmail markiert, Follow-up auf +7 Tage gesetzt.")
        st.rerun()
    if col2.button("Follow-up fällig"):
        mark_status(selected_id, "Follow-up fällig")
        st.success("Status aktualisiert.")
        st.rerun()
    if col3.button("Antwort erhalten"):
        mark_status(selected_id, "Antwort erhalten")
        st.success("Status aktualisiert.")
        st.rerun()
    if col4.button("Gespräch geplant"):
        mark_status(selected_id, "Gespräch geplant")
        st.success("Status aktualisiert.")
        st.rerun()
    if col5.button("Kein Interesse"):
        mark_status(selected_id, "Kein Interesse")
        st.success("Status aktualisiert.")
        st.rerun()

    with st.form("followup_date_form"):
        col1, col2 = st.columns([1, 3])
        follow_up_date = col1.text_input(
            "Neues Follow-up-Datum",
            value=str(company.get("follow_up_date") or ""),
            placeholder="YYYY-MM-DD",
        )
        next_step = col2.text_input("Nächster Schritt", value=str(company.get("next_step") or ""))
        submitted = st.form_submit_button("Follow-up speichern")
    if submitted:
        try:
            update_follow_up(selected_id, follow_up_date, next_step)
            st.success("Follow-up gespeichert.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    st.subheader("Follow-up-Entwurf")
    include_no_pressure = st.checkbox(
        'Satz "Falls aktuell kein Thema..." aufnehmen',
        value=True,
    )
    if st.button("Follow-up-Text generieren"):
        st.session_state[f"followup_draft_{selected_id}"] = generate_follow_up_email(
            company,
            include_no_pressure_line=include_no_pressure,
        )

    followup_draft = st.session_state.get(f"followup_draft_{selected_id}")
    if followup_draft:
        subject = st.text_input("Follow-up-Betreff", value=followup_draft["subject"])
        body = st.text_area("Follow-up-Text", value=followup_draft["body"], height=220)
        if st.button("Follow-up-Entwurf speichern"):
            update_company(
                selected_id,
                {
                    "email_subject": subject,
                    "email_body": body,
                    "email_variant": followup_draft["variant"],
                },
            )
            st.success("Follow-up-Entwurf gespeichert.")
            st.rerun()


def save_export(df: pd.DataFrame, prefix: str) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = EXPORTS_DIR / f"{prefix}_{timestamp}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def render_import_export() -> None:
    st.subheader("Export")
    export_sets = {
        "alle_unternehmen": companies_df(),
        "followups": followups_df(),
        "interessierte_leads": interested_leads_df(),
    }
    for name, df in export_sets.items():
        col1, col2 = st.columns([1, 2])
        col1.download_button(
            f"{name}.csv herunterladen",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{name}.csv",
            mime="text/csv",
            disabled=df.empty,
        )
        if col2.button(f"{name}.csv lokal in exports speichern", disabled=df.empty):
            path = save_export(df, name)
            st.success(f"Export gespeichert: {path}")

    st.divider()
    st.subheader("Import")
    uploaded = st.file_uploader("CSV-Datei hochladen", type=["csv"])
    if not uploaded:
        return

    try:
        source_df = pd.read_csv(uploaded)
    except Exception as exc:
        st.error(f"CSV konnte nicht gelesen werden: {exc}")
        return

    st.dataframe(source_df.head(20), use_container_width=True)
    st.caption("Ordne mindestens company_name zu. Duplikate werden über E-Mail oder Unternehmensname + Website erkannt.")

    columns = ["Nicht importieren"] + list(source_df.columns)
    required_mapping = {
        "company_name": "company_name",
        "website": "website",
        "city": "city",
        "contact_name": "contact_name",
        "email": "email",
        "company_type": "company_type",
        "relevant_topics": "relevant_topics",
        "website_notes": "website_notes",
    }

    mapping: dict[str, str] = {}
    for field, preferred in required_mapping.items():
        default_index = columns.index(preferred) if preferred in columns else 0
        mapping[field] = st.selectbox(field, columns, index=default_index, key=f"map_{field}")

    if st.button("CSV importieren"):
        rows: list[dict[str, Any]] = []
        for _, source_row in source_df.iterrows():
            mapped = {
                field: source_row[column]
                for field, column in mapping.items()
                if column != "Nicht importieren"
            }
            rows.append(mapped)

        result = import_companies(rows)
        st.success(f"Importiert: {result['imported']}; übersprungen: {result['skipped']}")
        for error in result["errors"]:
            st.warning(error)


def render_settings() -> None:
    st.subheader("Lokale Konfiguration")
    st.write(f"Datenbank: `{DB_PATH}`")
    st.write(f"Exports: `{EXPORTS_DIR}`")
    st.write(f".env-Datei: `{ENV_PATH}`")
    st.write(".env vorhanden:", "ja" if ENV_FILE_EXISTS else "nein")
    st.write("OpenAI API-Key:", "konfiguriert" if OPENAI_API_KEY else "nicht konfiguriert")
    if env_example_contains_secret():
        st.error(
            "In .env.example scheint ein echter OpenAI-Key zu stehen. Bitte dort entfernen und den Key nur in .env speichern."
        )
    if ENV_FILE_EXISTS and not OPENAI_API_KEY:
        st.warning("Die .env-Datei existiert, aber OPENAI_API_KEY ist leer. Nach dem Eintragen Streamlit neu starten.")

    st.subheader("KI-Prompt")
    st.caption(
        "Dieser Prompt wird bei der Website-Analyse und bei KI-generierten Mailentwürfen immer mitgegeben."
    )
    current_prompt = get_sender_prompt()
    edited_prompt = st.text_area(
        "Bearbeitbarer Profil- und Schreibprompt",
        value=current_prompt,
        height=320,
        key="sender_prompt_editor",
    )
    col1, col2 = st.columns([1, 2])
    if col1.button("Prompt speichern"):
        save_sender_prompt(edited_prompt)
        st.success("Prompt gespeichert. Neue KI-Entwürfe nutzen ab sofort diesen Text.")
        st.rerun()
    if col2.button("Standardprompt wiederherstellen"):
        reset_sender_prompt()
        st.success("Standardprompt wiederhergestellt.")
        st.rerun()
    with st.expander("Standardprompt anzeigen"):
        st.code(DEFAULT_SENDER_PROMPT, language="text")

    st.subheader("Gmail-Drafts")
    gmail_config = gmail_status()
    st.write(f"Gmail Credentials: `{gmail_config['credentials_path']}`")
    st.write(f"Gmail Token: `{gmail_config['token_path']}`")
    st.write(f"Gmail Scope: `{gmail_config['scope']}`")

    if not gmail_config["credentials_exists"]:
        st.warning("OAuth-Datei nicht gefunden. Lege credentials.json im Projektordner ab.")
    elif not gmail_config["credentials_valid"]:
        st.error(gmail_config["credentials_error"] or "OAuth-Datei gefunden, aber nicht als Desktop-App erkannt.")
    elif not gmail_config["token_exists"]:
        st.success("OAuth-Datei gefunden und als Desktop-App erkannt.")
        st.info(
            "Der Gmail-Login ist noch nicht erledigt. Er startet automatisch beim ersten Klick auf "
            "`Gmail-Draft erstellen`."
        )
        st.caption(
            "Falls Google 403 access_denied meldet: In der Google Cloud Console unter "
            "Google Auth Platform > Audience/Test users die eigene Gmail-Adresse als Testnutzer hinzufügen."
        )
    else:
        st.success("Gmail ist verbunden. Drafts können erstellt werden.")

    st.subheader("Sicherheit")
    st.info(
        "Diese App versendet keine E-Mails automatisch. Mailtexte werden lokal gespeichert und müssen manuell geprüft werden."
    )
    st.write(
        "Gmail-Drafts werden ausschließlich über gmail.compose erstellt. Ein Gmail-Send-Call ist bewusst nicht implementiert."
    )


def main() -> None:
    setup()
    st.title("Akquise-CRM für Immobilienunternehmen")
    st.caption("Lokale Verwaltung von Leads, Mailentwürfen und Follow-ups.")
    if st.session_state.get("flash_success"):
        st.success(st.session_state.pop("flash_success"))

    tabs = st.tabs(
        [
            "Dashboard",
            "Unternehmen",
            "Mail-Entwürfe",
            "Follow-ups",
            "Import/Export",
            "Einstellungen",
        ]
    )
    with tabs[0]:
        render_dashboard()
    with tabs[1]:
        render_companies()
    with tabs[2]:
        render_email_drafts()
    with tabs[3]:
        render_followups()
    with tabs[4]:
        render_import_export()
    with tabs[5]:
        render_settings()


if __name__ == "__main__":
    main()
