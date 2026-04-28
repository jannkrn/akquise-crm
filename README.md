# Akquise-CRM Immobilien

Lokale Streamlit-App zum Recherchieren und Verwalten kleiner Immobilienunternehmen, zum Erstellen personalisierter E-Mail-Entwuerfe und zum Tracken von Follow-ups.

Die App versendet keine E-Mails automatisch. Jeder Entwurf muss manuell geprueft und ausserhalb der App versendet werden. Eine spaetere Gmail-Draft-Funktion ist nur als Stub vorgesehen; ein Gmail-Send-Call ist nicht implementiert.

## Funktionen

- Dashboard mit Lead-Anzahl, Statusverteilung, faelligen Follow-ups, Antwortquote und Gespraechsquote
- Unternehmen anlegen, bearbeiten und loeschen
- Mail-Entwuerfe auf Deutsch generieren
- Template-Fallback ohne OpenAI API-Key
- Optional OpenAI API zur Formulierung, wenn `OPENAI_API_KEY` gesetzt ist
- Optional Gmail-Drafts erstellen mit OAuth-Scope `gmail.compose`
- Erstmail als gesendet markieren und Follow-up automatisch auf +7 Tage setzen
- Follow-up-Liste und Follow-up-Entwurf
- Suche und Filter nach Unternehmen, Stadt, Themen, Status und Angebotswinkel
- CSV-Import mit Spaltenmapping
- CSV-Export aller Unternehmen, Follow-ups und interessierter Leads
- Lokale SQLite-Datenbank unter `data/akquise.db`

## Installation

```powershell
cd C:\Jann\Business\Immobilien\akquise-crm
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Konfiguration

Die App funktioniert ohne OpenAI API-Key und ohne Gmail-Verbindung. Fuer KI-gestuetzte Formulierungen oder Gmail-Drafts kann eine `.env` angelegt werden:

```powershell
Copy-Item .env.example .env
```

Danach optional in `.env` eintragen:

```text
OPENAI_API_KEY=dein_api_key
OPENAI_MODEL=gpt-4o-mini
GMAIL_CREDENTIALS_PATH=credentials.json
GMAIL_TOKEN_PATH=data/gmail_token.json
```

## Gmail-Drafts einrichten

Die App kann Gmail-Entwuerfe erstellen, aber keine E-Mails senden. Dafuer wird nur der Gmail-Scope `https://www.googleapis.com/auth/gmail.compose` genutzt.

1. In der Google Cloud Console ein Projekt erstellen oder ein bestehendes nutzen.
2. Gmail API aktivieren.
3. OAuth-Client fuer eine Desktop-App erstellen.
4. Die heruntergeladene JSON-Datei als `credentials.json` in den Projektordner legen.
5. App starten und im Tab `Mail-Entwuerfe` nach Pruefung des Textes auf `Gmail-Draft erstellen` klicken.
6. Beim ersten Klick oeffnet sich der Google-Login im Browser. Danach wird ein lokales Token unter `data/gmail_token.json` gespeichert.

`credentials.json` und `data/gmail_token.json` sind in `.gitignore` eingetragen und sollten nicht geteilt werden.

## Start

```powershell
cd C:\Jann\Business\Immobilien\akquise-crm
.\.venv\Scripts\Activate.ps1
streamlit run app.py

```
Dann im Browser 
http://localhost:8501

Beim ersten Start wird die SQLite-Datenbank automatisch angelegt. Falls die Datei noch nicht existiert, entsteht sie unter `data/akquise.db`.

## Nutzung

1. Im Tab `Unternehmen` ein Unternehmen anlegen. Pflichtfeld ist nur `company_name`; E-Mail ist optional und wird nur grob validiert.
2. Optional beim Speichern `Nach dem Speichern Gmail-Entwurf vorbereiten` aktivieren. Das erzeugt nur einen lokalen Mailtext und waehlt das Unternehmen im Tab `Mail-Entwuerfe` vor.
3. Im Tab `Mail-Entwuerfe` ein Unternehmen auswaehlen und aus Website-Notizen, relevanten Themen und Angebotswinkel einen Entwurf erzeugen.
4. Den Entwurf pruefen und per Button beim Unternehmen speichern.
5. Optional nach der Pruefung `Gmail-Draft erstellen` klicken. Dadurch entsteht ein Entwurf in Gmail, aber es wird nichts gesendet.
6. Im Tab `Follow-ups` nach manuell versendeter Erstmail den Button `Als Erstmail gesendet markieren` nutzen. Die App setzt dann `first_contact_date`, `last_contact_date` und `follow_up_date` automatisch auf heute plus 7 Tage.
7. Faellige Follow-ups erscheinen im Dashboard und im Follow-up-Tab.
8. Im Tab `Import/Export` Daten als CSV importieren oder exportieren.

## Datenschutz und Grenzen

- Daten werden lokal in SQLite gespeichert.
- Es werden keine Secrets hardcodiert.
- Sammle nur personenbezogene Daten, die du fuer die konkrete Akquise wirklich brauchst.
- Die App ist kein Tool fuer automatisierte Kaltmail-Versandstrecken.
- Versand bleibt manuell und liegt ausserhalb dieser App.
- Gmail-Drafts und Gmail-Versand sind getrennte API-Methoden. Diese App implementiert nur Draft-Erstellung, keinen Send-Call.
