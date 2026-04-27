# Akquise-CRM Immobilien

Lokale Streamlit-App zum Recherchieren und Verwalten kleiner Immobilienunternehmen, zum Erstellen personalisierter E-Mail-Entwuerfe und zum Tracken von Follow-ups.

Die App versendet keine E-Mails automatisch. Jeder Entwurf muss manuell geprueft und ausserhalb der App versendet werden. Eine spaetere Gmail-Draft-Funktion ist nur als Stub vorgesehen; ein Gmail-Send-Call ist nicht implementiert.

## Funktionen

- Dashboard mit Lead-Anzahl, Statusverteilung, faelligen Follow-ups, Antwortquote und Gespraechsquote
- Unternehmen anlegen, bearbeiten und loeschen
- Mail-Entwuerfe auf Deutsch generieren
- Template-Fallback ohne OpenAI API-Key
- Optional OpenAI API zur Formulierung, wenn `OPENAI_API_KEY` gesetzt ist
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

Die App funktioniert ohne OpenAI API-Key. Fuer KI-gestuetzte Formulierungen kann eine `.env` angelegt werden:

```powershell
Copy-Item .env.example .env
```

Danach optional in `.env` eintragen:

```text
OPENAI_API_KEY=dein_api_key
OPENAI_MODEL=gpt-4o-mini
```

## Start

```powershell
streamlit run app.py
```

Beim ersten Start wird die SQLite-Datenbank automatisch angelegt. Falls die Datei noch nicht existiert, entsteht sie unter `data/akquise.db`.

## Nutzung

1. Im Tab `Unternehmen` ein Unternehmen anlegen. Pflichtfeld ist nur `company_name`; E-Mail ist optional und wird nur grob validiert.
2. Im Tab `Mail-Entwuerfe` ein Unternehmen auswaehlen und aus Website-Notizen, relevanten Themen und Angebotswinkel einen Entwurf erzeugen.
3. Den Entwurf pruefen und per Button beim Unternehmen speichern.
4. Im Tab `Follow-ups` nach manuell versendeter Erstmail den Button `Als Erstmail gesendet markieren` nutzen. Die App setzt dann `first_contact_date`, `last_contact_date` und `follow_up_date` automatisch auf heute plus 7 Tage.
5. Faellige Follow-ups erscheinen im Dashboard und im Follow-up-Tab.
6. Im Tab `Import/Export` Daten als CSV importieren oder exportieren.

## Datenschutz und Grenzen

- Daten werden lokal in SQLite gespeichert.
- Es werden keine Secrets hardcodiert.
- Sammle nur personenbezogene Daten, die du fuer die konkrete Akquise wirklich brauchst.
- Die App ist kein Tool fuer automatisierte Kaltmail-Versandstrecken.
- Versand bleibt manuell und liegt ausserhalb dieser App.
