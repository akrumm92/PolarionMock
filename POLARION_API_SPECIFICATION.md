# Polarion REST API v1 Spezifikation

Basierend auf den Testergebnissen und dem beobachteten Verhalten der Polarion REST API v1.

## Wichtige Erkenntnisse aus Test-Lauf 20250804_121817

### Erfolgreiche Tests (11 von 31):
- Projects API funktioniert vollständig
- Authentifizierung gibt korrekte 401 Fehler zurück
- Pagination und Sortierung funktionieren

### Fehlgeschlagene Tests (5 von 31):
- Documents API: `/all/documents` Endpunkt existiert nicht (404)
- Documents API: `/projects/{id}/spaces/{space}/documents` gibt 405 Method Not Allowed
- Work Items API: `/all/workitems` Endpunkt existiert nicht (404)
- Work Items API: Spezifische Work Items können nicht abgerufen werden (404)

### Übersprungene Tests (15 von 31):
- Mock-only Tests werden korrekt übersprungen

## 1. API-Grundlagen

### 1.1 Basis-URLs
- **Legacy API**: `/polarion/api` - Gibt HTML zurück, nicht für REST geeignet
- **REST API v1**: `/polarion/rest/v1` - JSON:API Format

### 1.2 Authentifizierung
- **Methode**: Bearer Token (Personal Access Token)
- **Header**: `Authorization: Bearer <PAT>`
- **Token-Format**: JWT mit spezifischer Polarion-Struktur

### 1.3 Erforderliche Headers
```http
Authorization: Bearer <PAT>
Content-Type: application/json
Accept: */*
```

**WICHTIG**: Der `Accept` Header MUSS `*/*` sein. Andere Werte (wie `application/json`) führen zu 406 Not Acceptable!

### 1.4 SSL/TLS
- Polarion verwendet oft selbst-signierte Zertifikate
- SSL-Verifikation kann über `POLARION_VERIFY_SSL=false` deaktiviert werden

## 2. Beobachtete API-Endpunkte und Responses

### 2.1 Projects API

#### GET /polarion/rest/v1/projects
**Response**: 200 OK, Content-Length: 2472 bytes
```json
{
  "data": [
    // Projekt-Liste im JSON:API Format
  ],
  "links": {
    "self": "https://polarion-d.claas.local/polarion/rest/v1/projects"
  }
}
```

#### GET /polarion/rest/v1/projects/{projectId}
**Beispiel**: GET /polarion/rest/v1/projects/Python
**Response**: 200 OK, Content-Length: 2473 bytes

#### GET /polarion/rest/v1/projects?page[size]=2&page[number]=1
**Response**: 200 OK, Content-Length: 2473 bytes
- Unterstützt Pagination mit `page[size]` und `page[number]`

#### GET /polarion/rest/v1/projects/{projectId}?fields[projects]=name,created
**Response**: 200 OK, Content-Length: 2472 bytes
- Unterstützt Sparse Fieldsets

#### GET /polarion/rest/v1/projects?sort=name
**Response**: 200 OK, Content-Length: 2472 bytes
- Unterstützt Sortierung

### 2.2 Documents API

#### ❌ GET /polarion/rest/v1/all/documents
**Response**: 404 Not Found
**WICHTIG**: Dieser Endpunkt existiert nicht in Polarion!

#### ❌ GET /polarion/rest/v1/projects/{projectId}/spaces/{spaceId}/documents
**Beispiel**: GET /polarion/rest/v1/projects/Python/spaces/_default/documents
**Response**: 405 Method Not Allowed
**WICHTIG**: Dieser Endpunkt akzeptiert keine GET-Requests!

#### Alternative Document APIs (aus Polarion Dokumentation):
- Dokumente müssen über spezifische IDs abgerufen werden
- Keine "list all documents" Funktionalität in REST API v1

### 2.3 Work Items API

#### ✅ GET /polarion/rest/v1/projects/{projectId}/workitems
**Beispiel**: GET /polarion/rest/v1/projects/Python/workitems
**Response**: 200 OK
- Funktioniert für existierende Projekte
- Gibt leeres data Array zurück wenn keine Work Items vorhanden

#### ❌ GET /polarion/rest/v1/all/workitems
**Response**: 404 Not Found
**WICHTIG**: Dieser Endpunkt existiert nicht in Polarion!

#### ❌ GET /polarion/rest/v1/projects/{projectId}/workitems/{workitemId}
**Beispiel**: GET /polarion/rest/v1/projects/Python/workitems/WI-123
**Response**: 404 Not Found
- Work Item existiert nicht oder
- Format der Work Item ID ist falsch

#### Funktionierende Query-Parameter:
- `page[size]` und `page[number]` für Pagination
- `fields` für Sparse Fieldsets
- `include` für Related Resources
- Query-Parameter müssen auf projekt-spezifische Endpunkte angewendet werden

### 2.4 Spezielle Endpunkte

#### GET /polarion/rest/v1/projects/non_existent_project/workitems
**Response**: 404 Not Found
```json
{
  "errors": [{
    "status": "404",
    "title": "Not Found", 
    "detail": "Project id non_existent_project does not exist."
  }]
}
```
**KORREKTUR**: Polarion gibt jetzt korrekt 404 für nicht existierende Projekte zurück!

## 3. Response-Charakteristiken

### 3.1 Content-Length Muster
- Die meisten Responses haben eine Größe von 2471-2473 bytes
- Dies deutet auf eine konsistente Response-Struktur hin
- Wahrscheinlich gibt Polarion eine Standard-Response mit leerem `data` Array zurück

### 3.2 JSON:API Format
Alle Responses folgen dem JSON:API Standard:
```json
{
  "data": [...],
  "links": {
    "self": "...",
    "first": "...",
    "last": "...",
    "next": "...",
    "prev": "..."
  },
  "meta": {
    "totalCount": 0
  }
}
```

### 3.3 Fehlerbehandlung
- **Nicht existierende Ressourcen**: Inkonsistentes Verhalten!
  - `/projects/non_existent_project/workitems`: 404 Not Found (korrekt)
  - `/all/workitems`: 404 Not Found (Endpunkt existiert nicht in Polarion)
  - `/all/documents`: 404 Not Found (Endpunkt existiert nicht in Polarion)
- **Falsche Accept Header**: 406 Not Acceptable
- **SSL Fehler**: Connection refused bei selbst-signierten Zertifikaten
- **Authentifizierung**: 401 Unauthorized mit JSON:API Error Format

## 4. Mock-Implementierungsanforderungen

### 4.1 URL-Routing
```python
# Korrekte Pfade für REST API v1
@app.route('/polarion/rest/v1/projects', methods=['GET'])
@app.route('/polarion/rest/v1/projects/<project_id>', methods=['GET'])
@app.route('/polarion/rest/v1/projects/<project_id>/workitems', methods=['GET'])
@app.route('/polarion/rest/v1/all/workitems', methods=['GET'])
@app.route('/polarion/rest/v1/all/documents', methods=['GET'])
@app.route('/polarion/rest/v1/projects/<project_id>/spaces/<space_id>/documents', methods=['GET'])
```

### 4.2 Response-Generierung
```python
def generate_empty_response(request_url):
    """Generiere eine Polarion-konforme leere Response"""
    return {
        "data": [],
        "links": {
            "self": request_url
        },
        "meta": {
            "totalCount": 0
        }
    }
```

### 4.3 Content-Length Simulation
Der Mock sollte Responses mit ähnlicher Größe generieren (~2472 bytes), 
um das Polarion-Verhalten genau nachzuahmen.

### 4.4 Query-Parameter Handling
- `page[size]` und `page[number]` für Pagination
- `fields[<type>]` für Sparse Fieldsets
- `sort` für Sortierung
- `query` für Filterung
- `include` für Related Resources

### 4.5 Authentifizierung
- Bearer Token Validierung
- JWT-Struktur mit Polarion-spezifischen Claims

## 5. Testfälle für Mock-Validierung

Der Mock muss folgende Tests bestehen:
1. Alle GET-Requests geben 200 OK zurück (auch für nicht existierende Ressourcen)
2. Content-Length ist konsistent (~2472 bytes)
3. Accept Header `*/*` wird akzeptiert
4. Query-Parameter werden korrekt geparst
5. JSON:API Format wird eingehalten
6. Keine 404 Fehler für nicht existierende Ressourcen

## 6. Umgebungsvariablen

```bash
POLARION_BASE_URL=https://polarion-d.claas.local
POLARION_REST_V1_PATH=/polarion/rest/v1
POLARION_API_PATH=/polarion/api
POLARION_VERIFY_SSL=false
POLARION_PERSONAL_ACCESS_TOKEN=<token>
```

## 7. Reale Polarion Response Beispiele

### 7.1 Erfolgreiche Projects Response
```json
{
  "links": {
    "self": "https://polarion-d.claas.local/polarion/rest/v1/projects",
    "first": "https://polarion-d.claas.local/polarion/rest/v1/projects?page%5Bnumber%5D=1",
    "next": "https://polarion-d.claas.local/polarion/rest/v1/projects?page%5Bnumber%5D=2",
    "last": "https://polarion-d.claas.local/polarion/rest/v1/projects?page%5Bnumber%5D=2"
  },
  "data": [
    {
      "type": "projects",
      "id": "FormsConfigurationTest",
      "links": {
        "self": "https://polarion-d.claas.local/polarion/rest/v1/projects/FormsConfigurationTest"
      }
    }
    // ... weitere Projekte
  ],
  "meta": {
    "totalCount": 186
  }
}
```

### 7.2 Authentifizierungsfehler
```json
{
  "errors": [{
    "status": "401",
    "title": "Unauthorized",
    "detail": "No access token"
  }]
}
```

### 7.3 Nicht gefundene Ressource
```json
{
  "errors": [{
    "status": "404",
    "title": "Not Found",
    "detail": null,
    "source": null
  }]
}
```

## 8. Mock-Implementierungshinweise

### 8.1 Zu implementierende Endpunkte
```python
# Funktionierende Endpunkte
@app.route('/polarion/rest/v1/projects', methods=['GET'])
@app.route('/polarion/rest/v1/projects/<project_id>', methods=['GET'])
@app.route('/polarion/rest/v1/projects/<project_id>/workitems', methods=['GET'])

# NICHT implementieren (existieren nicht in Polarion)
# /polarion/rest/v1/all/documents
# /polarion/rest/v1/all/workitems
# /polarion/rest/v1/projects/<id>/spaces/<space>/documents (405 Method Not Allowed)
```

### 8.2 Pagination-Implementierung
- Default page size: 100 items (wie bei Polarion beobachtet)
- Links müssen korrekt URL-encoded sein (`%5B` für `[`, `%5D` für `]`)
- `meta.totalCount` muss die Gesamtzahl aller Items enthalten

### 8.3 Fehlerbehandlung
- 401 für fehlende/ungültige Authentifizierung
- 404 für nicht existierende Projekte/Ressourcen
- 405 für nicht unterstützte HTTP-Methoden
- Fehler immer im JSON:API Error Format zurückgeben

## 9. Neue Erkenntnisse aus Tests (Stand: 04.08.2025)

### 9.1 CustomFields Format
**Problem**: Die `customFields` Eigenschaft erwartet einen STRING, nicht ein Objekt.

**Fehlermeldung**:
```json
{
  "errors": [{
    "status": "400",
    "title": "Bad Request",
    "detail": "Unexpected token, STRING expected, but was : BEGIN_OBJECT",
    "source": {
      "pointer": "$.data[0].attributes.customFields",
      "parameter": null,
      "resource": null
    }
  }]
}
```

**Status**: Format noch unklar - möglicherweise JSON-String oder einfacher String-Wert

### 9.2 Work Item Types
**Bestätigte Standard-Typen**:
- `requirement` - Funktioniert in allen Tests
- `task` - Funktioniert für Child-Items

**Hinweise**:
- Custom-Typen wie "Functional Safety Requirement 1" existieren möglicherweise nicht in allen Projekten
- Typ-Verfügbarkeit ist projektspezifisch
- Endpunkt für verfügbare Typen: `/projects/{id}/workitemtypes`

### 9.3 Beziehungs-Updates (Relationships)
**Problem**: PATCH-Requests für Beziehungs-Updates geben 400 Bad Request zurück

**Getestete Formate** (alle fehlgeschlagen):
```json
// Format 1: Relationships-Objekt
{
  "data": {
    "type": "workitems",
    "id": "Python/PYTH-123",
    "relationships": {
      "parent": {
        "data": {
          "type": "workitems",
          "id": "Python/PYTH-122"
        }
      }
    }
  }
}

// Format 2: Als Attribut
{
  "data": {
    "type": "workitems",
    "id": "Python/PYTH-123",
    "attributes": {
      "parentWorkItemId": "Python/PYTH-122"
    }
  }
}
```

**Status**: Korrektes Format für Beziehungs-Updates muss noch ermittelt werden

### 9.4 Korrigierte Endpunkt-Informationen
**Funktionierende Endpunkte** (Korrektur zu Abschnitt 8.1):
- `/polarion/rest/v1/all/workitems` - Funktioniert tatsächlich (200 OK)
- Wird für projektübergreifende Queries verwendet: `/all/workitems?query=type:requirement`

**Mock sollte implementieren**:
```python
@app.route('/polarion/rest/v1/all/workitems', methods=['GET'])  # Funktioniert doch!
```