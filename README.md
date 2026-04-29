# Akquise-CRM Immobilien

Lokale Streamlit-App zum Recherchieren und Verwalten kleiner Immobilienunternehmen, zum Erstellen personalisierter E-Mail-Entwuerfe und zum Tracken von Follow-ups.

Die App versendet keine E-Mails automatisch. Jeder Entwurf muss manuell geprueft und ausserhalb der App versendet werden. Eine spaetere Gmail-Draft-Funktion ist nur als Stub vorgesehen; ein Gmail-Send-Call ist nicht implementiert.

## Funktionen

- Dashboard mit Lead-Anzahl, Statusverteilung, faelligen Follow-ups, Antwortquote und Gespraechsquote
- Offene Entwuerfe erscheinen im Dashboard unter `Heute oder ueberfaellig`
- Unternehmen anlegen, bearbeiten und loeschen
- Mail-Entwuerfe auf Deutsch generieren
- Template-Fallback ohne OpenAI API-Key
- Optional OpenAI API zur Formulierung, wenn `OPENAI_API_KEY` gesetzt ist
- Optional Gmail-Drafts erstellen mit OAuth-Scope `gmail.compose`
- Website per KI analysieren und Formularfelder inklusive E-Mail-Text vorbefüllen
- Weitere passende Unternehmen per Websuche und KI-Analyse finden, mit Filter gegen bereits gespeicherte Websites
- Erstmail als gesendet markieren und Follow-up automatisch auf +7 Tage setzen
- Follow-up-Liste und Follow-up-Entwurf
- Suche und Filter nach Unternehmen, Stadt, Themen, Status und Angebotswinkel
- CSV-Import mit Spaltenmapping
- CSV-Export aller Unternehmen, Follow-ups und interessierter Leads
- Lokale SQLite-Datenbank unter `data/akquise.db`

## Installation

```powershell
cd ...\akquise-crm
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

### Fehler 403 access_denied beim Google-Login

Wenn Google meldet, dass die App noch nicht verifiziert wurde und nur genehmigte Tester Zugriff haben, ist dein Google-Konto noch nicht als Testnutzer eingetragen.

Loesung:

1. Google Cloud Console oeffnen.
2. Das Projekt aus `credentials.json` auswaehlen.
3. Zu `Google Auth Platform` wechseln.
4. Unter `Audience` beziehungsweise `Test users` die eigene Gmail-Adresse hinzufuegen.
5. Speichern und den Login in der Streamlit-App erneut starten.

## Start

```powershell
cd ...\akquise-crm
.\.venv\Scripts\Activate.ps1
streamlit run app.py

```
Dann im Browser 
http://localhost:8501

Beim ersten Start wird die SQLite-Datenbank automatisch angelegt. Falls die Datei noch nicht existiert, entsteht sie unter `data/akquise.db`.

## Nutzung

1. Im Tab `Unternehmen` ein Unternehmen anlegen. Pflichtfeld ist nur `company_name`; E-Mail ist optional und wird nur grob validiert.
2. Optional im Anlegen-Tab `Weitere passende Unternehmen finden` nutzen. Dazu Ort/Region, Umkreis und Anzahl der Vorschlaege eintragen. Die App sucht passende Verwaltungsunternehmen, filtert bereits gespeicherte Websites heraus und analysiert neue Kandidaten per KI.
3. Optional im Anlegen-Tab `Automatisch mit KI ausfuellen` nutzen. Die App liest eine konkrete Website, erstellt einen Vorschlag fuer Stammdaten, relevante Themen, Website-Notizen, Hypothese, Angebotswinkel und E-Mail-Text. Der Vorschlag muss vor dem Speichern manuell geprueft werden.
4. Optional beim Speichern `Nach dem Speichern Gmail-Entwurf vorbereiten` aktivieren. Das erzeugt nur einen lokalen Mailtext und waehlt das Unternehmen im Tab `Mail-Entwuerfe` vor.
5. Im Tab `Mail-Entwuerfe` ein Unternehmen auswaehlen und aus Website-Notizen, relevanten Themen und Angebotswinkel einen Entwurf erzeugen.
6. Den Entwurf pruefen und per Button beim Unternehmen speichern.
7. Optional nach der Pruefung `Gmail-Draft erstellen` klicken. Dadurch entsteht ein Entwurf in Gmail, aber es wird nichts gesendet. Die App speichert die Gmail-Draft-ID und, sofern von Gmail geliefert, eine Message-ID fuer einen Gmail-Weblink.
8. Im Tab `Follow-ups` nach manuell versendeter Erstmail den Button `Als Erstmail gesendet markieren` nutzen. Die App setzt dann `first_contact_date`, `last_contact_date` und `follow_up_date` automatisch auf heute plus 7 Tage.
9. Faellige Follow-ups erscheinen im Dashboard und im Follow-up-Tab.
10. Im Tab `Import/Export` Daten als CSV importieren oder exportieren.

## Datenschutz und Grenzen

- Daten werden lokal in SQLite gespeichert.
- Es werden keine Secrets hardcodiert.
- Sammle nur personenbezogene Daten, die du fuer die konkrete Akquise wirklich brauchst.
- Die App ist kein Tool fuer automatisierte Kaltmail-Versandstrecken.
- Versand bleibt manuell und liegt ausserhalb dieser App.
- Gmail-Drafts und Gmail-Versand sind getrennte API-Methoden. Diese App implementiert nur Draft-Erstellung, keinen Send-Call.
