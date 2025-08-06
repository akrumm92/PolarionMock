# Lösung für DNS/Netzwerk-Problem mit Polarion

## Problem
Der Test schlägt fehl mit:
```
NameResolutionError: Failed to resolve 'polarion-d.claas.local' ([Errno 11001] getaddrinfo failed)
```

## Lösungsansätze

### 1. VPN-Verbindung prüfen
Stellen Sie sicher, dass Sie mit dem Firmennetzwerk/VPN verbunden sind, um auf `polarion-d.claas.local` zugreifen zu können.

### 2. Hosts-Datei bearbeiten (temporäre Lösung)

**Windows** (als Administrator):
Öffnen Sie `C:\Windows\System32\drivers\etc\hosts` und fügen Sie hinzu:
```
<IP-ADRESSE>    polarion-d.claas.local
```

**Mac/Linux**:
```bash
sudo nano /etc/hosts
# Hinzufügen:
<IP-ADRESSE>    polarion-d.claas.local
```

Sie müssen die tatsächliche IP-Adresse von `polarion-d.claas.local` kennen.

### 3. IP-Adresse direkt verwenden

Ändern Sie in `.env` oder `.env.PolarionConfig`:
```bash
# Statt:
POLARION_BASE_URL=https://polarion-d.claas.local

# Verwenden Sie die IP-Adresse:
POLARION_BASE_URL=https://<IP-ADRESSE>
```

**WICHTIG**: Bei direkter IP-Nutzung kann es SSL-Zertifikatsprobleme geben. Stellen Sie sicher:
```bash
POLARION_VERIFY_SSL=false
```

### 4. DNS-Server prüfen

Testen Sie die DNS-Auflösung:
```bash
# Windows
nslookup polarion-d.claas.local

# Mac/Linux  
dig polarion-d.claas.local
```

Falls das fehlschlägt, ist der DNS-Server nicht korrekt konfiguriert.

### 5. Alternative: Lokaler Polarion Mock verwenden

Für Entwicklung ohne Netzwerkzugriff:
```bash
# Mock-Server starten
MOCK_PORT=5001 python -m src.mock

# Tests gegen Mock ausführen
python run_tests.py --env mock --test tests/moduletest/test_discovery.py::TestDiscovery::test_discover_project_spaces -xvs
```

## Empfohlene Schritte

1. **VPN verbinden** (falls im Homeoffice)
2. **IP-Adresse erfragen** bei IT oder Kollegen
3. **Hosts-Datei anpassen** mit der korrekten IP
4. **Test erneut ausführen**:
```bash
python run_tests.py --env production --test tests/moduletest/test_discovery.py::TestDiscovery::test_discover_project_spaces -xvs
```

## Diagnose-Befehle

```bash
# Testen ob Polarion erreichbar ist
curl -k https://polarion-d.claas.local/polarion/api

# Oder mit Python
python -c "import requests; print(requests.get('https://polarion-d.claas.local/polarion/api', verify=False).status_code)"
```

Wenn diese Befehle fehlschlagen, ist es definitiv ein Netzwerk/DNS-Problem und kein Code-Problem.