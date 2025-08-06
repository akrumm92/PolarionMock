# Polarion Document Structure Extraction - Implementation Guide

## Übersicht
Diese Anleitung beschreibt, wie die Dokumentstruktur mit Headers aus Polarion extrahiert wird und wie WorkItems korrekt unter Headers in Dokumenten verlinkt werden.

## Kritische Erkenntnisse

### WICHTIGSTE ERKENNTNISSE:

#### 1. WorkItems müssen im gleichen Dokument sein wie ihre Parent-Header!
Basierend auf der Analyse von PYTH-9368/9369:
- PYTH-9368 ist ein Header in `Python/_default/Functional Concept - Template` 
- PYTH-9369 ist ein Child WorkItem im GLEICHEN Dokument
- Beide haben das gleiche `module` Attribut

#### 2. outlineNumber ist READ-ONLY und der Schlüssel zur Sichtbarkeit!
- **NIEMALS** `outlineNumber` beim Erstellen setzen - es ist read-only!
- Polarion vergibt `outlineNumber` automatisch basierend auf der Dokumentstruktur
- **PROBLEM**: WorkItems ohne `outlineNumber` erscheinen NICHT im Dokument!
- Warnung "This Work Item was unmarked in the Document" = kein outlineNumber

#### 3. WorkItem-Erstellung ≠ Dokument-Sichtbarkeit
- API-Erstellung (HTTP 201) bedeutet NICHT automatische Dokument-Positionierung
- WorkItems existieren im System, aber ohne `outlineNumber` sind sie nicht im Dokument sichtbar
- Parent-Child-Verlinkung allein reicht NICHT für Sichtbarkeit

### 1. Document Parts API Response Format
Die Polarion Document Parts API (`/projects/{projectId}/spaces/{spaceId}/documents/{documentName}/parts`) gibt eine **minimale** Response zurück:

```json
{
  "data": [
    {
      "type": "document_parts",
      "id": "Python/Functional Layer/Functional Concept/heading_FCTS-9183",
      "links": {
        "self": "https://polarion.../parts/heading_FCTS-9183"
      }
    },
    {
      "type": "document_parts", 
      "id": "Python/Functional Layer/Functional Concept/polarion_92",
      "links": {
        "self": "https://polarion.../parts/polarion_92"
      }
    }
  ]
}
```

**WICHTIG**: 
- Es gibt KEINE `attributes` oder `relationships` in der Response
- Die WorkItem-Information ist in der `id` kodiert
- Format: `{project}/{space}/{document}/{type}_{workitem-id}`

### 2. Header Identifikation
Headers werden durch das Präfix `heading_` in der Part-ID identifiziert:
- `heading_FCTS-9183` = Header WorkItem mit ID FCTS-9183
- `polarion_XX` = Andere Dokumentteile (Text, Bilder, etc.)

### 3. WorkItem-Header Verlinkung
WorkItems werden über `linkedWorkItems` mit Headers verknüpft:
```json
{
  "linkedWorkItems": {
    "data": [
      {
        "type": "linkedworkitems",
        "id": "Python/PYTH-9397/parent/Python/PYTH-9394"
      }
    ]
  }
}
```
Format: `{child_id}/parent/{parent_id}`

## Implementierung

### Schritt 1: Document Parts abrufen und Header-IDs extrahieren

```python
def get_document_structure(self, project_id: str, space_id: str, document_name: str):
    # URL encode space and document names (wichtig bei Spaces mit Leerzeichen!)
    from urllib.parse import quote
    space_encoded = quote(space_id, safe='')
    doc_encoded = quote(document_name, safe='')
    
    endpoint = f"/projects/{project_id}/spaces/{space_encoded}/documents/{doc_encoded}/parts"
    response = self._request("GET", endpoint)
    parts_data = response.json()
    
    header_workitem_ids = []
    
    if "data" in parts_data:
        for part in parts_data["data"]:
            part_id = part.get("id", "")
            
            # Extract the last part of the ID (e.g., "heading_FCTS-9183")
            if "/" in part_id:
                part_suffix = part_id.split("/")[-1]
                
                # Check if this is a heading
                if part_suffix.startswith("heading_"):
                    # Extract the workitem ID (e.g., "FCTS-9183")
                    workitem_id_part = part_suffix.replace("heading_", "")
                    # Construct full workitem ID with project prefix
                    workitem_id = f"{project_id}/{workitem_id_part}"
                    header_workitem_ids.append(workitem_id)
    
    return {"header_workitem_ids": header_workitem_ids}
```

### Schritt 2: Header-Details aus WorkItems abrufen

```python
def extract_header_details(header_ids, all_workitems):
    headers_in_doc = []
    
    for wi_id in header_ids:
        # Find this workitem in all_workitems to get title and details
        for wi in all_workitems:
            if wi.get("id") == wi_id:
                attrs = wi.get("attributes", {})
                headers_in_doc.append({
                    "id": wi_id,
                    "title": attrs.get("title", ""),
                    "outlineNumber": attrs.get("outlineNumber", ""),
                    "type": "heading",
                    "children": []
                })
                break
    
    # Sort headers by outline number for proper document structure
    headers_in_doc.sort(key=lambda x: x.get("outlineNumber", ""))
    return headers_in_doc
```

### Schritt 3: WorkItem unter Header verlinken

```python
def link_workitem_to_header(child_workitem_id: str, parent_header_id: str):
    """
    Verlinkt ein WorkItem mit einem Header-WorkItem als Parent.
    
    WICHTIG: Verwende PATCH auf den linkedWorkItems relationship endpoint
    """
    # Format: {child_id}/parent/{parent_id}
    link_data = {
        "data": [{
            "type": "linkedworkitems",
            "id": f"{child_workitem_id}/parent/{parent_header_id}"
        }]
    }
    
    # Extract short ID (e.g., "PYTH-9397" from "Python/PYTH-9397")
    child_short_id = child_workitem_id.split('/')[-1]
    
    # Use PATCH to update the relationship
    endpoint = f"projects/{project_id}/workitems/{child_short_id}/relationships/linkedWorkItems"
    response = client._request("PATCH", endpoint, json=link_data)
    
    return response
```

## Wichtige Details

### URL Building mit urljoin
**Problem**: `urljoin()` behandelt Pfade mit führendem `/` als absolut und ersetzt den gesamten Pfad.

```python
# FALSCH - verliert /polarion/rest/v1
urljoin('https://host/polarion/rest/v1', '/projects/id/workitems')
# Ergebnis: https://host/projects/id/workitems ❌

# RICHTIG - behält vollständigen Pfad
urljoin('https://host/polarion/rest/v1/', 'projects/id/workitems')  
# Ergebnis: https://host/polarion/rest/v1/projects/id/workitems ✅
```

**Lösung**: Stelle sicher, dass `rest_api_url` mit `/` endet (in config.py).

### HTTP Client Details

```python
# PolarionClient hat KEIN .client Attribut!
# FALSCH:
polarion_client.client.request("PATCH", url, data)

# RICHTIG:
polarion_client._request("PATCH", url, data)
```

### Parameter Unpacking
```python
# FALSCH - übergibt params als einzelnes Dictionary
result = self.get_work_items(project_id=project_id, params=params)

# RICHTIG - entpackt params als Keyword-Argumente
result = self.get_work_items(project_id=project_id, **params)
```

## Vollständige Dokumentstruktur Output

Die extrahierte Struktur sollte so aussehen:

```json
{
  "id": "Python/Functional Layer/Functional Concept",
  "structure": {
    "headers": [
      {
        "id": "Python/FCTS-9183",
        "title": "Functional Concept - Template",
        "outlineNumber": "",
        "type": "heading",
        "children": []
      },
      {
        "id": "Python/FCTS-9184", 
        "title": "Introduction",
        "outlineNumber": "1",
        "type": "heading",
        "children": []
      },
      {
        "id": "Python/FCTS-9185",
        "title": "About this document",
        "outlineNumber": "1.1",
        "type": "heading",
        "children": []
      }
    ],
    "total_headers": 26,
    "structure_summary": [
      " Functional Concept - Template",
      "1 Introduction",
      "  1.1 About this document",
      "  1.2 Responsibilities",
      "  1.3 Summary of the Function",
      "2 General Information",
      "  2.1 System Environment"
    ]
  }
}
```

## Testing und Debugging

### Debug-Output aktivieren
```python
import json
import os

# Speichere erste Document Parts Response für Debugging
debug_file = "tests/moduletest/outputdata/debug_document_parts.json"
if not os.path.exists(debug_file):
    with open(debug_file, 'w') as f:
        json.dump(parts_data, f, indent=2)
```

### Logging für Struktur-Extraktion
```python
logger.info(f"\n=== Document Structure: {doc_id} ===")
for line in structure_summary[:20]:  # Erste 20 Headers zeigen
    logger.info(line)
if len(structure_summary) > 20:
    logger.info(f"  ... and {len(structure_summary) - 20} more headers")
```

## Häufige Fehler und Lösungen

1. **Headers werden nicht gefunden**
   - Prüfe ob Document Parts API erreichbar ist (HTTP 200)
   - Prüfe ob Part-IDs das Format `heading_XXX` haben
   - Stelle sicher, dass alle WorkItems geladen wurden (Pagination!)

2. **WorkItem-Verlinkung schlägt fehl**
   - Verwende POST zu `/workitems/{id}/linkedworkitems`, NICHT PATCH auf relationships!
   - Format muss genau sein: `{child_id}/parent/{parent_id}`
   - Prüfe Berechtigungen für linkedWorkItems Updates

3. **Document Parts API gibt 404**
   - Space-Name muss URL-encoded sein (besonders bei Leerzeichen)
   - Prüfe ob Dokument existiert
   - Prüfe REST API v1 Pfad in Konfiguration

4. **WorkItems erscheinen nicht im Dokument trotz erfolgreicher Erstellung**
   - **HAUPTPROBLEM**: WorkItem hat kein `outlineNumber`
   - Polarion vergibt `outlineNumber` nur bei korrekter Dokument-Integration
   - Versuche POST zu `/spaces/{space}/documents/{doc}/parts` mit WorkItem
   - Parent-Child-Verlinkung allein reicht NICHT aus

## Zusammenfassung der Implementierung

1. **Hole alle WorkItems** mit Pagination (wichtig: alle laden!)
2. **Rufe Document Parts API** für jedes Dokument auf
3. **Extrahiere Header-IDs** aus Part-IDs mit Präfix `heading_`
4. **Suche Header-WorkItems** in all_workitems für Details
5. **Baue Dokumentstruktur** sortiert nach outlineNumber
6. **Verlinke neue WorkItems** mit Headers via linkedWorkItems PATCH

Diese Implementierung stellt sicher, dass:
- Die komplette Dokumentstruktur mit allen Headers extrahiert wird
- WorkItems korrekt unter den richtigen Headers erscheinen
- Die Hierarchie durch outlineNumber erhalten bleibt
- Alle Titel und Details der Headers verfügbar sind