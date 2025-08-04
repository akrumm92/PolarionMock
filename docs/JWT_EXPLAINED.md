# JWT Token Erklärung

## Die Komponenten

```
JWT_SECRET_KEY = "mein-geheimes-passwort-123"  (in .env)
       ↓
    [SIGNIERT]
       ↓
TOKEN = {
  "user_id": "vpathvpath",     ← Der Benutzer
  "username": "vpathvpath", 
  "permissions": ["read", "write", "admin"],
  "exp": 1754332759,
  "iat": 1754246359
}
```

## Beispiel

### Schritt 1: JWT_SECRET_KEY in .env setzen
```env
JWT_SECRET_KEY=super-geheimes-passwort-2024
```

### Schritt 2: Token für verschiedene Benutzer generieren
```bash
# Token für User "alice"
python generate_token_auto.py alice
# → Generiert Token mit user_id="alice", signiert mit "super-geheimes-passwort-2024"

# Token für User "bob"  
python generate_token_auto.py bob
# → Generiert Token mit user_id="bob", signiert mit "super-geheimes-passwort-2024"

# Token für User "vpathvpath"
python generate_token_auto.py vpathvpath
# → Generiert Token mit user_id="vpathvpath", signiert mit "super-geheimes-passwort-2024"
```

### Schritt 3: Server verifiziert
Der Server prüft: "Wurde dieser Token mit meinem JWT_SECRET_KEY signiert?"
- Wenn ja → Token gültig ✓
- Wenn nein → "Signature verification failed" ✗

## Wichtige Punkte

1. **Ein JWT_SECRET_KEY** → **Viele verschiedene Tokens/Benutzer**
2. Der JWT_SECRET_KEY ist NICHT der Benutzername
3. Der JWT_SECRET_KEY sollte:
   - Geheim bleiben
   - Komplex sein (wie ein starkes Passwort)
   - Für alle Tokens gleich sein

## Analogie

Denk dir das wie einen Stempel:
- **JWT_SECRET_KEY** = Der Stempel selbst (nur einer)
- **User ID** = Was auf dem Papier steht (kann variieren)
- **Token** = Das gestempelte Papier (Papier + Stempel = gültig)

Der Server prüft: "Ist das mit MEINEM Stempel gestempelt?"