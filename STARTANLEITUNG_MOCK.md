# Startanleitung: Workflow gegen den Polarion-Mock testen

Diese Anleitung beschreibt Schritt für Schritt, wie ein Polarion-Lese-Workflow
(Beispiel: `lexion_fsm_polarion_requirements_read`) **ohne Zugriff auf
polarion-d.claas.local** gegen den Mock läuft. Es muss **genau eine Zeile**
in der Kundenkonfiguration geändert werden: die Base-URL.

Verifiziert am 2026-09-12: Der komplette Lauf über `run_workflow.py` gegen den
Mock lieferte ein `requirements.yaml`, das mit dem Produktionslauf identisch
ist (29 Anforderungen, nur `fetched_at` und `polarion_base_url` weichen ab).
Beweismittel: `test_reports/20260912_mock_workflow_run/`.

---

## 1. Voraussetzungen (einmalig)

```powershell
cd C:\Users\E017093\gitRepos\PolarionMock
pip install -r requirements.txt          # enthält cryptography für HTTPS
python -m pytest tests/mock_unit -q --env mock    # Selbsttest, ~6 s, 61 Tests grün
```

Das Kunden-Repo (`v2_vpath_customer_workflows`) und `left_side_clean` müssen
wie für den Produktionslauf eingerichtet sein (Editable-Install von left_side,
`.env.secrets` mit dem PAT). Daran ändert sich **nichts**.

## 2. Mock starten

Terminal 1 (bleibt offen):

```powershell
cd C:\Users\E017093\gitRepos\PolarionMock
python run_mock.py --ssl
```

Ausgabe beim Start:

```
Polarion mock: https://localhost:5001/polarion/rest/v1  (auth mode: pat)
  put into the workflow overlay:  POLARION_BASE_URL: "https://localhost:5001"
  documents loaded from Polarion dumps:
    project='VPATHAI' space='System Layer' document='Technical_Specification-API_TEST'  (218 parts, 158 work items)
```

Kontrolle im Browser oder per curl: `https://localhost:5001/health`
(Zertifikatswarnung ist erwartet, das Zertifikat ist selbstsigniert wie bei
polarion-d).

Varianten:

| Aufruf | Wirkung |
|---|---|
| `python run_mock.py --ssl` | HTTPS auf Port 5001 (empfohlen, entspricht der Produktion mit `POLARION_VERIFY_SSL=false`) |
| `python run_mock.py` | HTTP auf Port 5001 (Overlay dann `http://localhost:5001`) |
| `python run_mock.py --ssl --port 8443` | anderer Port |
| `python run_mock.py --ssl --dump-dir D:\exports` | zusätzliche Dokument-Exporte laden |
| `python run_mock.py --ssl --check-pat-expiry` | abgelaufene PATs ablehnen wie die Produktion |
| `python run_mock.py --auth-mode disabled` | ohne Authentifizierung |

## 3. Konfiguration im Kunden-Repo (die einzige Änderung)

Datei:
`C:\Users\E017093\v2_vpath_customer_workflows\customers\CLAAS_New\projects\lexion_fsm_polarion\environment.lexion_fsm_polarion_requirements_read_api_test.yaml`

```yaml
# vorher (Produktion)
POLARION_BASE_URL: "https://polarion-d.claas.local"

# für den Mock
POLARION_BASE_URL: "https://localhost:5001"
```

Alle anderen Werte bleiben **unverändert**, weil der Mock genau diese
Koordinaten bedient:

```yaml
POLARION_PROJECT_ID: VPATHAI
POLARION_SPACE_ID: "System Layer"
POLARION_DOCUMENT_NAME: Technical_Specification-API_TEST
POLARION_VERIFY_SSL: "false"          # passt zum selbstsignierten Zertifikat des Mocks
```

Der PAT bleibt, wo er ist:
`customers/CLAAS_New/.env.secrets` mit `POLARION_PERSONAL_ACCESS_TOKEN=...`.
Der Mock akzeptiert ihn unverändert (auch nach Ablauf, siehe Abschnitt 7).

Hinweis: Die Overlay-Datei ist im Kunden-Repo (noch) nicht getrackt. Vor der
Änderung eine Kopie anlegen oder die Zeile nach dem Test von Hand
zurücksetzen.

## 4. Workflow ausführen

Terminal 2, aus der **Kapselwurzel**:

PowerShell:

```powershell
cd C:\Users\E017093\v2_vpath_customer_workflows
$env:VPATH_CUSTOMERS_ROOT = "$PWD\customers"
python C:\Users\E017093\gitRepos\left_side_clean\tools\run_workflow.py `
    --customer CLAAS_New --project lexion_fsm_polarion `
    --profile lexion_fsm_polarion_requirements_read_api_test -y
```

Git Bash:

```bash
cd /c/Users/E017093/v2_vpath_customer_workflows
export VPATH_CUSTOMERS_ROOT="C:/Users/E017093/v2_vpath_customer_workflows/customers"
python /c/Users/E017093/gitRepos/left_side_clean/tools/run_workflow.py \
    --customer CLAAS_New --project lexion_fsm_polarion \
    --profile lexion_fsm_polarion_requirements_read_api_test -y
```

Achtung Git Bash: **nicht** in `timeout ...` einpacken. Das MSYS-`timeout`
löscht die Umgebung des Kindprozesses (`VPATH_CUSTOMERS_ROOT` fehlt dann).

Erwartete Zeilen im Runner-Output:

```
RunScriptProcessor: running scripts/fetch_polarion_document.py as a stage
playground\lexion_fsm_polarion_derived\api_test\fetch\polarion_document_raw.json: 218 of 218 reported parts, 158 work items
...
Workflow finished (completed) in ~4 seconds
```

Wenn die Fetch-Stage aus dem Stage-Cache bedient wird (kein Request beim
Mock, alter `base_url` im Rohabzug), vorher den Instanzordner
`playground/CLAAS_New_lexion_fsm_polarion_requirements_read/` löschen oder
verschieben.

## 5. Ergebnis prüfen

```
playground/CLAAS_New_lexion_fsm_polarion_requirements_read/
  lexion_fsm_polarion_requirements_read_claas_new_lexion_fsm_polarion_requirements_read_api_test/
    002_stage_raw_for_requirements/polarion_document_raw.json   # base_url = https://localhost:5001
    003_build_requirements/requirements.yaml                    # 29 Anforderungen
```

Erwartung in `requirements.yaml`:

```yaml
meta:
  polarion_base_url: https://localhost:5001
  counts:
    work_items_total: 158
    requirements: 29
    systemrequirement: 10
    componentrequirement: 19
```

Danach im Overlay die Base-URL wieder auf `https://polarion-d.claas.local`
setzen.

## 6. Ein anderes Dokument bereitstellen

1. Einmal gegen die Produktion holen (oder den Rohabzug eines fertigen Laufs
   nehmen):

   ```powershell
   $env:POLARION_PERSONAL_ACCESS_TOKEN = "<PAT>"
   python customers\CLAAS_New\projects\ground_guidance\scripts\fetch_polarion_document.py `
       --base-url https://polarion-d.claas.local --project VPATHAI `
       --space "System Layer" --document "<Dokumentname>" `
       --out-dir C:\temp\export --verify-ssl false
   ```

2. Die Datei `polarion_document_raw.json` nach
   `src\mock\mock_data\polarion_dumps\` kopieren (beliebiger Dateiname) und den
   Mock neu starten, **oder** ohne Neustart laden:

   ```powershell
   curl.exe -sk -X POST https://localhost:5001/mock/admin/dumps `
       -H "Authorization: Bearer <PAT>" -H "Content-Type: application/json" `
       --data-binary "@C:\temp\export\polarion_document_raw.json"
   ```

3. Kontrolle: `https://localhost:5001/mock/admin/documents` listet Projekt,
   Space, Dokument, Anzahl Parts und Work Items.

4. Im Overlay `POLARION_PROJECT_ID`, `POLARION_SPACE_ID`,
   `POLARION_DOCUMENT_NAME` auf das Dokument setzen.

## 7. Konfiguration des Mocks (optional, `.env` oder Umgebungsvariablen)

| Variable | Default | Bedeutung |
|---|---|---|
| `MOCK_PORT` | `5001` | Port |
| `MOCK_HOST` | `0.0.0.0` | Bind-Adresse; `0.0.0.0` bindet IPv4 **und** IPv6 (sonst 2 s Verzögerung pro Request über `localhost`) |
| `MOCK_SSL` | `false` | `true` = HTTPS mit selbstsigniertem Zertifikat (entspricht `--ssl`) |
| `MOCK_SSL_CERT` / `MOCK_SSL_KEY` | leer | eigenes PEM-Zertifikat statt ad-hoc |
| `MOCK_AUTH_MODE` | `pat` | `pat`: Polarion-PATs und Mock-JWTs; `strict`: nur Mock-JWTs (`JWT_SECRET_KEY`); `disabled`: keine Auth |
| `MOCK_PAT_CHECK_EXPIRY` | `false` | `true` = abgelaufene PATs mit 401 ablehnen |
| `MOCK_ACCEPTED_TOKENS` | leer | kommagetrennte Liste beliebiger Tokens, die immer akzeptiert werden |
| `MOCK_DUMP_DIR` | leer | zusätzliche Verzeichnisse mit Exporten (`;`-getrennt) |
| `LOG_FORMAT` | `json` | `text` für lesbare Konsole (`run_mock.py` setzt `text`) |

Die `.env` im Repo wird von `run_mock.py` gelesen, Kommandozeilenoptionen haben
Vorrang.

## 8. Fehlerbilder

| Symptom | Ursache / Abhilfe |
|---|---|
| `HTTP 401` im Fetch-Skript | `POLARION_PERSONAL_ACCESS_TOKEN` fehlt in der Prozessumgebung oder ist kein JWT. Bei `--auth-mode strict` nur Mock-JWTs. |
| `HTTP 404 ... /documents/<name>/parts` | Dokument nicht geladen. `https://localhost:5001/mock/admin/documents` prüfen, Koordinaten im Overlay vergleichen (Space mit Leerzeichen exakt schreiben). |
| `HTTP 406` | Accept-Header ohne JSON (`*/*` oder `application/json` verwenden). |
| `[SSL: WRONG_VERSION_NUMBER]` | Mock läuft ohne `--ssl`, Overlay sagt `https`; oder ein alter Server hält den Port (`netstat -ano \| findstr :5001`). |
| jeder Request dauert ~2 s | Server lauscht nur auf IPv4. `run_mock.py` bindet beide Familien; sonst `127.0.0.1` statt `localhost` verwenden. |
| `VPATH_CUSTOMERS_ROOT is not set` | Variable nicht gesetzt oder Runner in Git Bash mit `timeout` gestartet. |
| Fetch-Stage läuft nicht (Cache) | Instanzordner unter `playground/` entfernen, siehe Abschnitt 4. |

## 9. Tests, die diesen Vertrag absichern

```powershell
python -m pytest tests/mock_unit -q --env mock
```

| Datei | Prüft |
|---|---|
| `test_requirements_read_workflow.py` | Replay der Fetch-Sequenz == Produktionsexport; Pagination, `totalCount`, Sparse Fieldsets, Typ-Filter (29 = 10 + 19) |
| `test_fetch_script_live.py` | das **echte** Kunden-Fetch-Skript (unverändert, Subprozess) gegen einen Live-Mock |
| `test_auth_and_headers.py` | PAT-Akzeptanz, Ablauf-Policy, 401/406-Verhalten |
| `test_openapi_contract.py` | Antworten gegen die OpenAPI-Spec `Input/api/polarionrest.json` |
| `test_dump_loader.py` | Laden/Ersetzen/Reset von Exporten |

Weitere Details (englisch): `docs/STANDALONE_WORKFLOW_TEST.md`.
