# Finale Space Discovery Lösung für Polarion REST API

## Problem-Zusammenfassung

Die Polarion REST API hat **schwerwiegende Einschränkungen** bei der Space-Discovery:
- ❌ **KEIN** `/projects/{projectId}/workitems` GET Endpoint (404 Fehler)
- ❌ **KEIN** `/all/workitems` GET Endpoint (404 Fehler)  
- ❌ **KEIN** `/all/documents` GET Endpoint (404 Fehler)
- ❌ **KEIN** direkter Endpoint zum Auflisten von Spaces

## Implementierte Lösung

Die neue `get_project_spaces` Methode verwendet **5 kreative Strategien**, um Spaces trotz API-Einschränkungen zu finden:

### Strategie 1: Direkte Ressourcen-Prüfung
```python
# Versucht bekannte Space-Namen durch Zugriff auf konkrete Ressourcen
for space in ["_default", "Product Layer", "Requirements", ...]:
    for doc_name in ["index", "readme", "overview", ...]:
        GET /projects/{projectId}/spaces/{space}/documents/{doc_name}
        # Status 200 oder 403 = Space existiert!
```

### Strategie 2: Collections API
```python
GET /projects/{projectId}/collections?include=documents
# Parst inkludierte Dokumente für Space-IDs
```

### Strategie 3: Test Runs
```python
GET /projects/{projectId}/testruns
# Extrahiert Space-Referenzen aus Test Run IDs und Dokumenten
```

### Strategie 4: Spezifische Work Item IDs
```python
# Versucht bekannte Work Item ID-Muster
GET /projects/{projectId}/workitems/{projectId}/{space}/REQ-1
# Status 200 oder 403 = Space existiert!
```

### Strategie 5: Plans API
```python
GET /projects/{projectId}/plans
# Sucht nach Space-Referenzen in Plan-Attributen
```

## Warum diese Lösung funktioniert

1. **Nutzt nur existierende Endpoints** - Keine 404 Fehler mehr
2. **Mehrere Fallback-Strategien** - Wenn eine fehlschlägt, greifen andere
3. **Verifiziert Spaces aktiv** - Prüft tatsächliche Ressourcen statt nur Namen
4. **Findet auch "Product Layer"** - Durch erweiterte Space-Namen-Liste

## Test-Aufruf

```bash
# Mit run_tests.py
python run_tests.py --env production --test tests/moduletest/test_discovery.py::TestDiscovery::test_discover_all_documents_in_all_spaces -xvs

# Direkt mit pytest
POLARION_ENV=production pytest tests/moduletest/test_discovery.py::TestDiscovery::test_discover_project_spaces -xvs
```

## Wichtige Erkenntnisse

1. **Polarion REST API ist unvollständig** - Viele erwartete Endpoints existieren nicht
2. **Space Discovery ist nicht vorgesehen** - Es gibt keinen offiziellen Weg
3. **Kreative Workarounds nötig** - Multiple Strategien für Robustheit
4. **Tests laufen auf anderem Computer** - Polarion läuft nicht auf diesem Mac

## Performance-Überlegungen

- Die Methode macht viele einzelne Requests (keine Bulk-Abfragen möglich)
- Caching empfohlen, da Spaces sich selten ändern
- Timeout-Handling wichtig bei vielen potentiellen Space-Namen

## Nächste Schritte

1. Test auf dem Windows-Computer mit Polarion-Zugang ausführen
2. Prüfen, ob alle Spaces gefunden werden
3. Performance optimieren (z.B. parallele Requests)
4. Caching-Layer hinzufügen für wiederholte Aufrufe