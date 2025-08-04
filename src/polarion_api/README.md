# Polarion API Python Client

Ein sauberes, wartbares Python-Modul für die Interaktion mit der Polarion ALM REST API.

## Features

- ✅ Vollständige Unterstützung für Work Items API
- ✅ Vollständige Unterstützung für Documents API  
- ✅ Projekt-Management Funktionen
- ✅ Authentifizierung via Personal Access Token (PAT)
- ✅ Type Hints und Pydantic Models
- ✅ Umfangreiches Error Handling
- ✅ Konfiguration via Umgebungsvariablen (.env)
- ✅ Retry-Mechanismus und Session-Management
- ✅ Async-ready Architektur

## Installation

```bash
pip install python-dotenv requests pydantic
```

## Konfiguration

Erstelle eine `.env` Datei:

```env
# Polarion Verbindung
POLARION_BASE_URL=https://polarion.example.com
POLARION_PERSONAL_ACCESS_TOKEN=your-pat-token-here
POLARION_VERIFY_SSL=false  # Bei selbst-signierten Zertifikaten

# Optional
POLARION_DEFAULT_PROJECT_ID=myproject
POLARION_TIMEOUT=30
POLARION_MAX_RETRIES=3
POLARION_PAGE_SIZE=100
POLARION_DEBUG=false
```

## Verwendung

### Basis-Beispiel

```python
from polarion_api import PolarionClient

# Client initialisieren
client = PolarionClient()

# Projekte auflisten
projects = client.get_projects()
for project in projects["data"]:
    print(f"Project: {project['id']} - {project['attributes']['name']}")

# Work Item erstellen
work_item = client.create_work_item(
    project_id="myproject",
    title="Neue Anforderung",
    work_item_type="requirement",
    description="Detaillierte Beschreibung der Anforderung",
    priority="high",
    status="open"
)
print(f"Created: {work_item['id']}")
```

### Work Items

```python
# Work Items suchen
items = client.query_work_items(
    query="type:requirement AND status:open",
    project_id="myproject"
)

# Einzelnes Work Item abrufen
item = client.get_work_item("myproject/REQ-123")

# Work Item aktualisieren
client.update_work_item(
    work_item_id="myproject/REQ-123",
    status="in_progress",
    priority="critical"
)

# Work Item löschen
client.delete_work_item("myproject/REQ-123")
```

### Dokumente

```python
# Dokument erstellen
doc = client.create_document(
    project_id="myproject",
    space_id="_default",
    module_name="requirements_spec",
    title="Anforderungsspezifikation",
    home_page_content="<h1>Übersicht</h1><p>Dies ist unsere Spec.</p>"
)

# Dokument abrufen
document = client.get_document("myproject/_default/requirements_spec")

# Work Item zu Dokument hinzufügen
client.add_work_item_to_document(
    document_id="myproject/_default/requirements_spec",
    work_item_id="myproject/REQ-123"
)
```

### Error Handling

```python
from polarion_api import PolarionClient, PolarionNotFoundError, PolarionAuthError

try:
    client = PolarionClient()
    item = client.get_work_item("myproject/REQ-999")
except PolarionNotFoundError as e:
    print(f"Work Item nicht gefunden: {e}")
except PolarionAuthError as e:
    print(f"Authentifizierung fehlgeschlagen: {e}")
```

### Context Manager

```python
with PolarionClient() as client:
    projects = client.get_projects()
    # Client wird automatisch geschlossen
```

## API Referenz

### PolarionClient

**Methoden:**

#### Work Items
- `get_work_items(project_id=None, **params)` - Work Items abrufen
- `get_work_item(work_item_id, **params)` - Einzelnes Work Item
- `query_work_items(query, project_id=None, **params)` - Work Items suchen
- `create_work_item(project_id, title, work_item_type, **attributes)` - Work Item erstellen
- `update_work_item(work_item_id, **attributes)` - Work Item aktualisieren
- `delete_work_item(work_item_id)` - Work Item löschen

#### Dokumente
- `get_document(document_id, **params)` - Dokument abrufen
- `create_document(project_id, space_id, module_name, title, **attributes)` - Dokument erstellen
- `update_document(document_id, **attributes)` - Dokument aktualisieren
- `delete_document(document_id)` - Dokument löschen
- `get_document_parts(document_id, **params)` - Dokumentteile abrufen
- `add_work_item_to_document(document_id, work_item_id)` - Work Item hinzufügen

#### Projekte
- `get_projects(**params)` - Alle Projekte
- `get_project(project_id)` - Einzelnes Projekt

## Erweiterte Features

### Pagination

```python
# Seite 2 mit 50 Items pro Seite
items = client.get_work_items(
    project_id="myproject",
    **{"page[size]": 50, "page[number]": 2}
)
```

### Include Related Resources

```python
# Work Item mit Modul und Autor
item = client.get_work_item(
    "myproject/REQ-123",
    include="module,author"
)
```

### Sparse Fieldsets

```python
# Nur bestimmte Felder abrufen
items = client.get_work_items(
    project_id="myproject",
    **{"fields[workitems]": "title,status,priority"}
)
```

## Entwicklung

Das Modul ist so strukturiert, dass es einfach erweitert werden kann:

- `config.py` - Konfiguration und Umgebungsvariablen
- `client.py` - Haupt-Client-Klasse
- `work_items.py` - Work Items API Methoden (Mixin)
- `documents.py` - Documents API Methoden (Mixin)
- `models.py` - Pydantic Datenmodelle
- `exceptions.py` - Custom Exception-Klassen
- `utils.py` - Hilfsfunktionen

## MCP Server Integration

Dieses Modul wurde speziell entwickelt, um als Basis für einen MCP (Model Context Protocol) Server zu dienen. Die saubere Architektur und Type Hints machen die Integration einfach.

## License

MIT