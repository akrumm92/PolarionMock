# Troubleshooting Polarion Connection Issues

## Common Problems and Solutions

### 1. DNS Resolution Error (NameResolutionError)

**Error Message:**
```
Failed to resolve 'polarion-d.claas.local' ([Errno 11001] getaddrinfo failed)
```

**Problem:** Your computer cannot resolve the hostname to an IP address.

**Solutions:**

#### Option A: Add to Hosts File
1. **Windows:** Edit `C:\Windows\System32\drivers\etc\hosts` (as Administrator)
2. **Mac/Linux:** Edit `/etc/hosts` (with sudo)
3. Add line: `<POLARION_IP_ADDRESS> polarion-d.claas.local`

Example:
```
192.168.1.100 polarion-d.claas.local
```

#### Option B: Use IP Address Directly
Update `.env` file:
```bash
# Instead of hostname
POLARION_BASE_URL=https://192.168.1.100
```

#### Option C: Connect to VPN
If Polarion is in an internal network, ensure VPN connection is active.

### 2. Running Diagnostics

Use the diagnostic script to identify issues:

```bash
# Run comprehensive diagnostics
python scripts/diagnose_connection.py
```

This will check:
- DNS resolution
- Network connectivity
- API endpoints
- Environment variables

### 3. Different Test Environments

#### Development Machine (Mac) - Mock Only
```bash
# .env configuration for Mac development
POLARION_ENV=mock
MOCK_PORT=5001
DISABLE_AUTH=true

# Run mock server
python -m src.mock

# Run tests against mock
pytest
```

#### Test Machine (Windows) - Production Access
```bash
# .env configuration for Windows test machine
POLARION_ENV=production
POLARION_BASE_URL=https://polarion-d.claas.local
POLARION_PERSONAL_ACCESS_TOKEN=your-pat-here
POLARION_VERIFY_SSL=false

# Test connection first
python scripts/diagnose_connection.py

# If successful, run tests
python run_tests.py --env production
```

### 4. Network Configuration Issues

#### Behind Corporate Proxy
Add to `.env`:
```bash
HTTP_PROXY=http://proxy.company.com:8080
HTTPS_PROXY=http://proxy.company.com:8080
NO_PROXY=localhost,127.0.0.1
```

#### Self-Signed SSL Certificate
```bash
# Disable SSL verification
POLARION_VERIFY_SSL=false
```

### 5. Authentication Issues

#### Invalid Personal Access Token
1. Generate new PAT in Polarion UI
2. Ensure PAT has API permissions
3. Update `.env` file

#### Test authentication:
```bash
python scripts/test_polarion_connection.py
```

### 6. API Endpoint Issues

#### REST API Not Enabled
Contact Polarion administrator to enable REST API.

#### Wrong API Path
Try different paths:
```bash
# Standard paths
POLARION_REST_V1_PATH=/polarion/rest/v1
POLARION_API_PATH=/polarion/api

# Some installations might use
POLARION_REST_V1_PATH=/rest/v1
POLARION_API_PATH=/api
```

### 7. Quick Fixes Checklist

- [ ] Can you ping the server? `ping polarion-d.claas.local`
- [ ] Is VPN connected (if needed)?
- [ ] Is the hostname in hosts file?
- [ ] Is the Personal Access Token valid?
- [ ] Is SSL verification configured correctly?
- [ ] Are you using the correct API paths?
- [ ] Is the REST API enabled in Polarion?

### 8. Test Connection Step by Step

```bash
# 1. Check DNS
nslookup polarion-d.claas.local

# 2. Check network
ping polarion-d.claas.local

# 3. Check HTTPS port
telnet polarion-d.claas.local 443

# 4. Test with curl
curl -k -H "Authorization: Bearer YOUR_PAT" \
     -H "Accept: */*" \
     https://polarion-d.claas.local/polarion/rest/v1/projects

# 5. Run diagnostic script
python scripts/diagnose_connection.py

# 6. Test with Python script
python scripts/test_polarion_connection.py
```

### 9. Environment-Specific Issues

#### Windows Specific
- Check Windows Firewall settings
- Run Command Prompt as Administrator for hosts file edits
- Use `ipconfig /flushdns` after hosts file changes

#### Mac Specific
- Use `sudo dscacheutil -flushcache` after hosts file changes
- Check if port 5001 conflicts with AirPlay (for mock)

#### Linux Specific
- Use `sudo systemctl restart systemd-resolved` after hosts file changes
- Check SELinux/AppArmor permissions

### 10. Getting Help

If issues persist:
1. Run `python scripts/diagnose_connection.py` and save output
2. Check `test_reports/*/logs/pytest.log` for detailed errors
3. Verify with Polarion administrator:
   - REST API is enabled
   - Your PAT has correct permissions
   - No firewall blocks API access
4. Try accessing Polarion web UI from the same machine