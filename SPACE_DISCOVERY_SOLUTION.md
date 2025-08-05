# Dynamische Space Discovery Lösung für Polarion

## Problem
Es gibt **keinen direkten API Endpoint** in Polarion REST API, um alle Spaces eines Projekts aufzulisten. Die ursprüngliche Implementierung hatte zwei Hauptprobleme:
1. Verwendete nicht-existierende Endpoints (`/all/documents`, `/all/workitems`)
2. Verließ sich auf eine vordefinierte Liste von Space-Namen

## Lösung: Vollständig dynamische Space-Entdeckung

Die neue Implementierung nutzt **ausschließlich gültige Polarion REST API Endpoints** und entdeckt Spaces dynamisch ohne vordefinierte Listen.

### Implementierte Strategie

#### 1. Alle Work Items des Projekts durchsuchen
```python
endpoint = f"/projects/{project_id}/workitems"
```
- Paginiert durch ALLE Work Items des Projekts
- Extrahiert Space-IDs aus Work Item IDs (Format: `projectId/spaceId/workItemType/workItemId`)
- Der zweite Teil der ID ist **immer** die Space-ID

#### 2. Module URIs analysieren
Work Items, die zu Dokumenten gehören, haben `moduleURI` Attribute:
- Format 1: `subterra:data-service:objects:default/projectId_spaceId$documentId`
- Format 2: `subterra:data-service:objects:default/projectId/spaceId/documentId`

Beide Formate werden geparst, um zusätzliche Spaces zu finden.

#### 3. Dokument-Relationships untersuchen
```python
query = f"project.id:{project_id} AND HAS_VALUE:moduleURI"
```
- Fragt Work Items mit Modul-Beziehungen ab
- Untersucht `included` Dokumente für Space-Informationen
- Prüft `spaceId` Attribute in Dokumenten

#### 4. Space-Varianten erkennen
Wenn Spaces gefunden wurden, werden automatisch Varianten geprüft:
- `Product_Layer` → auch prüfen: `Product-Layer`, `ProductLayer`
- `test-cases` → auch prüfen: `test_cases`, `testcases`

## Vorteile der neuen Lösung

✅ **Keine vordefinierten Listen** - Findet ALLE Spaces dynamisch  
✅ **Nutzt nur gültige API Endpoints** - Keine 404 Fehler mehr  
✅ **Vollständige Abdeckung** - Durchsucht alle Work Items und Dokumente  
✅ **Erkennt Space-Varianten** - Findet auch ähnlich benannte Spaces  
✅ **Skalierbar** - Funktioniert mit beliebig vielen Spaces  

## Code-Beispiel

```python
from polarion_api.client import PolarionClient
from polarion_api.config import PolarionConfig

config = PolarionConfig()
client = PolarionClient(config=config)

# Findet ALLE Spaces im Projekt dynamisch
spaces = client.get_project_spaces("MyProject")
print(f"Gefundene Spaces: {spaces}")

# Beispiel-Output:
# Gefundene Spaces: ['Architecture', 'Design', 'Product Layer', 'Requirements', 'Testing']
```

## Technische Details

### Work Item ID Struktur
```
projectId/spaceId/workItemType/workItemId
└─────┘   └────┘   └──────────┘ └────────┘
   1        2           3           4
```
Position 2 ist **immer** die Space-ID.

### Module URI Parsing
```python
# Beispiel moduleURI
"subterra:data-service:objects:default/Python_Product Layer$REQ-123"
                                        └────┘ └───────────┘ └──────┘
                                      project    space      document
```

### Pagination
Die Methode paginiert automatisch durch alle Work Items:
- Page Size: 100 Items
- Stoppt, wenn `totalCount` erreicht ist
- Robust gegen Fehler einzelner Pages

## Performance

- **Erste Abfrage**: Kann bei großen Projekten einige Sekunden dauern
- **Caching empfohlen**: Spaces ändern sich selten
- **Optimierung**: Kann nach ersten Funden abbrechen, wenn gewünscht

## Fehlerbehandlung

- Jede Strategie ist unabhängig in try-except gekapselt
- Fehler stoppen nicht die gesamte Discovery
- Detailliertes Logging auf verschiedenen Levels
- Leere Liste zurückgeben statt Annahmen zu treffen

Diese Lösung ist robust, vollständig dynamisch und nutzt ausschließlich dokumentierte Polarion REST API Endpoints.