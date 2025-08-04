# Polarion API Module Tests

Umfassende Test-Suite für das polarion_api Python-Modul.

## Übersicht

Diese Tests verifizieren alle Methoden und Funktionen des polarion_api Moduls. Die Tests können sowohl gegen den Mock-Server als auch gegen eine echte Polarion-Instanz ausgeführt werden.

## Test-Struktur

```
tests/moduletest/
├── conftest.py          # Gemeinsame Fixtures und Konfiguration
├── test_config.py       # Tests für Konfigurationsmodul
├── test_client.py       # Tests für Client-Klasse
├── test_work_items.py   # Tests für Work Items API
├── test_documents.py    # Tests für Documents API
├── test_utils.py        # Tests für Utility-Funktionen
└── test_exceptions.py   # Tests für Exception-Klassen
```

## Test-Kategorien

### Unit Tests (@pytest.mark.unit)
- Testen isolierte Funktionen ohne API-Zugriff
- Verwenden Mocks für externe Abhängigkeiten
- Schnell und unabhängig von der Umgebung

### Integration Tests (@pytest.mark.integration)
- Testen echte API-Interaktionen
- Erfordern laufenden Mock-Server oder Polarion-Zugriff
- Verifizieren End-to-End-Funktionalität

### Umgebungsspezifische Tests
- `@pytest.mark.mock_only`: Nur gegen Mock-Server
- `@pytest.mark.production_only`: Nur gegen echtes Polarion
- `@pytest.mark.destructive`: Tests die Ressourcen erstellen/ändern/löschen (werden in Production übersprungen außer ALLOW_DESTRUCTIVE_TESTS=true)

## Ausführen der Tests

### Alle Tests
```bash
# Gegen Mock (Standard)
pytest tests/moduletest/

# Gegen Production
export POLARION_ENV=production
pytest tests/moduletest/
```

### Spezifische Test-Module
```bash
# Nur Work Items Tests
pytest tests/moduletest/test_work_items.py

# Nur Unit Tests
pytest tests/moduletest/ -m unit

# Nur Integration Tests
pytest tests/moduletest/ -m integration
```

### Mit Coverage
```bash
pytest tests/moduletest/ --cov=src/polarion_api --cov-report=html
```

### Verbose Output
```bash
pytest tests/moduletest/ -v -s
```

## Konfiguration

### Umgebungsvariablen

Erstelle eine `.env` Datei im Projekt-Root:

```env
# Für Mock-Tests
POLARION_ENV=mock
MOCK_URL=http://localhost:5001
MOCK_AUTH_TOKEN=your-mock-token

# Für Production-Tests
POLARION_ENV=production
POLARION_BASE_URL=https://polarion.example.com
POLARION_PERSONAL_ACCESS_TOKEN=your-pat-token
POLARION_VERIFY_SSL=false
TEST_PROJECT_ID=myproject
# VORSICHT: Erlaubt destruktive Tests (create/update/delete) in Production
ALLOW_DESTRUCTIVE_TESTS=false  # Auf true setzen nur wenn sicher!
```

### Test-Fixtures

Die wichtigsten Fixtures aus `conftest.py`:

- `polarion_client`: Konfigurierter Client für Tests
- `test_project_id`: Projekt-ID für Tests
- `unique_suffix`: Eindeutiger Suffix für Test-Daten
- `test_work_item_data`: Vorgefertigte Work Item Daten
- `test_document_data`: Vorgefertigte Document Daten
- `created_work_items`: Tracker für Cleanup von Work Items
- `created_documents`: Tracker für Cleanup von Documents

## Test-Daten Cleanup

Die Tests verwenden automatisches Cleanup:
- Erstellte Work Items werden nach dem Test gelöscht
- Erstellte Documents werden nach dem Test gelöscht
- Cleanup erfolgt auch bei Test-Fehlern

## Beispiel-Testlauf

```bash
# Mock-Server starten
cd /path/to/PolarionMock
python -m src.mock

# In anderem Terminal: Tests ausführen
export POLARION_ENV=mock
pytest tests/moduletest/ -v

# Ausgabe:
tests/moduletest/test_config.py::TestPolarionConfig::test_default_config_values PASSED
tests/moduletest/test_config.py::TestPolarionConfig::test_config_from_environment PASSED
tests/moduletest/test_client.py::TestPolarionClient::test_get_projects PASSED
tests/moduletest/test_work_items.py::TestWorkItemsMixin::test_create_work_item PASSED
...
```

## Troubleshooting

### Mock-Server nicht erreichbar
```
ERROR: Mock server not running at http://localhost:5001
```
**Lösung**: Mock-Server starten mit `python -m src.mock`

### Authentifizierungsfehler
```
PolarionAuthError: Authentication failed
```
**Lösung**: 
- Für Mock: Token mit `python generate_token_auto.py` generieren
- Für Production: Gültigen PAT in .env setzen

### SSL-Zertifikatsfehler
```
SSL: CERTIFICATE_VERIFY_FAILED
```
**Lösung**: `POLARION_VERIFY_SSL=false` in .env setzen

### Test-Projekt nicht gefunden
```
pytest.skip: Test project 'myproject' not found
```
**Lösung**: Existierendes Projekt in `TEST_PROJECT_ID` angeben

## Erweitern der Tests

### Neuen Test hinzufügen
```python
@pytest.mark.integration
def test_new_feature(self, polarion_client):
    """Test new feature."""
    result = polarion_client.new_method()
    assert result is not None
```

### Neue Fixture hinzufügen
```python
@pytest.fixture
def custom_data(unique_suffix):
    """Generate custom test data."""
    return {
        "field": f"value_{unique_suffix}"
    }
```

## CI/CD Integration

Die Tests können einfach in CI/CD-Pipelines integriert werden:

```yaml
# GitHub Actions Beispiel
- name: Run Module Tests
  env:
    POLARION_ENV: mock
  run: |
    python -m src.mock &
    sleep 5
    pytest tests/moduletest/ --junit-xml=test-results.xml
```