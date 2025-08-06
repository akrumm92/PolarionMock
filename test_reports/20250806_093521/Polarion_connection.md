(venv) PS C:\Users\E017093\gitRepos\PolarionMock> python scripts/diagnose_connection.py
✅ Loaded .env from: C:\Users\E017093\gitRepos\PolarionMock\.env
======================================================================
POLARION CONNECTION DIAGNOSTICS
======================================================================

5. Environment Variables Check
--------------------------------------------------

Required variables:
  ✅ POLARION_BASE_URL: https://polarion-d.claas.local (Base URL of Polarion server)
  ✅ POLARION_PERSONAL_ACCESS_TOKEN: eyJraWQiOi... (Personal Access Token for authentication)

Optional variables:
  ✅ POLARION_REST_V1_PATH: /polarion/rest/v1 (Path to REST API v1 (default: /polarion/rest/v1))
  ✅ POLARION_API_PATH: /polarion/api (Path to legacy API (default: /polarion/api))
  ✅ POLARION_VERIFY_SSL: false (SSL verification (default: true))
  ✅ POLARION_ENV: production (Environment (mock/production))
  ✅ TEST_PROJECT_ID: Python (Test project ID)

Target server: polarion-d.claas.local
Base URL: https://polarion-d.claas.local

1. DNS Resolution Check for: polarion-d.claas.local
--------------------------------------------------
✅ DNS resolution successful: polarion-d.claas.local -> 10.1.5.170
   All IPs: ['10.1.5.170']

3. Ping Test to polarion-d.claas.local
--------------------------------------------------
Exception in thread Thread-1 (_readerthread):
Traceback (most recent call last):
  File "C:\Users\E017093\AppData\Local\Programs\Python\Python313\Lib\threading.py", line 1041, in _bootstrap_inner
    self.run()
    ~~~~~~~~^^
  File "C:\Users\E017093\AppData\Local\Programs\Python\Python313\Lib\threading.py", line 992, in run
    self._target(*self._args, **self._kwargs)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\E017093\AppData\Local\Programs\Python\Python313\Lib\subprocess.py", line 1609, in _readerthread
    buffer.append(fh.read())
                  ~~~~~~~^^
  File "C:\Users\E017093\AppData\Local\Programs\Python\Python313\Lib\encodings\cp1252.py", line 23, in decode
    return codecs.charmap_decode(input,self.errors,decoding_table)[0]
           ~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeDecodeError: 'charmap' codec can't decode byte 0x81 in position 18: character maps to <undefined>
✅ Ping successful
⚠️  Could not run ping: 'NoneType' object has no attribute 'split'

2. Network Connectivity Check to polarion-d.claas.local:443
--------------------------------------------------
✅ TCP connection successful to polarion-d.claas.local:443

4. API Endpoint Check
--------------------------------------------------

   Testing: https://polarion-d.claas.local/polarion/rest/v1
   ✅ Success (200 OK)

   Testing: https://polarion-d.claas.local/polarion/api
   ✅ Success (200 OK)

   Testing: https://polarion-d.claas.local/polarion/rest/projects
   ⚠️  Endpoint not found (404)

======================================================================
SUMMARY
======================================================================
✅ All checks passed! Connection to Polarion should work.