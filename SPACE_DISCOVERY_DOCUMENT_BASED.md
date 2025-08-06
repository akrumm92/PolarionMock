# Document-basierte Space Discovery für Polarion

## Das Problem

Die Polarion REST API bietet **keinen direkten Endpoint** zum Auflisten aller Spaces in einem Projekt. Spaces sind nur als Teil von Document-URLs verfügbar, jedoch nicht als eigenständige Ressource.

## Die Lösung

Spaces werden indirekt durch Analyse der Document-IDs extrahiert, die dem Muster `projectId/spaceId/documentId` folgen.

## Implementierung

### Hauptmethode: `get_all_project_documents_and_spaces()`

```python
def get_all_project_documents_and_spaces(project_id, page_size=100, max_pages=None):
    """
    Holt alle Dokumente eines Projekts und extrahiert die Spaces.
    
    Returns:
        {
            'spaces': ['space1', 'space2', ...],
            'documents': [...],
            'meta': {...}
        }
    """
```

### Funktionsweise

1. **Primärer Ansatz**: `/projects/{projectId}/documents` mit Pagination
   - Iteriert durch alle Seiten von Dokumenten
   - Extrahiert Space-ID aus jedem Document-ID String
   - Format: `projectId/spaceId/documentId`

2. **Fallback-Methode**: Wenn Hauptendpoint 404 zurückgibt
   - Testet bekannte Space-Namen
   - Versucht `/projects/{projectId}/spaces/{spaceId}/documents`
   - Sammelt Spaces, die erfolgreich antworten

## Test-Aufruf

```bash
# Haupttest für Space Discovery
python run_tests.py --env production --test tests/moduletest/test_discovery.py::TestDiscovery::test_discover_project_spaces -xvs

# Test für alle Dokumente in allen Spaces
python run_tests.py --env production --test tests/moduletest/test_discovery.py::TestDiscovery::test_discover_all_documents_in_all_spaces -xvs
```

## Erwartete Ausgabe

```
Discovered 3 spaces: ['Default', 'Product Layer', 'Requirements']
Found 42 documents across all spaces
```

## Wichtige Erkenntnisse

1. **API-Limitierungen**: Viele erwartete Endpoints existieren nicht
   - ❌ GET `/projects/{projectId}/workitems` 
   - ❌ GET `/all/workitems`
   - ❌ GET `/all/documents`

2. **Document ID Pattern**: Immer `projectId/spaceId/documentId`
   - Space-ID ist IMMER der zweite Teil nach Split auf `/`

3. **Performance**: 
   - Pagination mit max 100 Dokumenten pro Seite
   - Bei großen Projekten kann Discovery langsam sein
   - Caching empfohlen

4. **Fallback wichtig**: Hauptendpoint funktioniert nicht immer
   - Manche Polarion-Instanzen haben den Endpoint deaktiviert
   - Fallback testet bekannte Space-Namen direkt

## Convenience-Methode

```python
# Nur Spaces abrufen (ohne Dokument-Details)
spaces = polarion_client.get_project_spaces(project_id)
```

Diese ruft intern `get_all_project_documents_and_spaces()` auf und gibt nur die Spaces zurück.

## Fehlerbehandlung

- **404**: Endpoint existiert nicht → Fallback-Methode
- **401**: Nicht autorisiert → Token prüfen
- **403**: Zugriff verweigert → Berechtigungen prüfen
- **429**: Rate Limit → Retry-Logik implementieren

## Zusammenfassung

Die document-basierte Space Discovery ist der **einzig zuverlässige Weg**, alle Spaces in einem Polarion-Projekt zu finden, da die API keinen direkten Endpoint dafür bereitstellt.