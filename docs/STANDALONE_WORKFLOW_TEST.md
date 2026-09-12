# Stand-alone workflow testing with the Polarion mock

Goal: run a customer workflow that reads Polarion over the REST API **without
the real server**, changing **nothing but the base URL** in the workflow's
profile overlay. The Personal Access Token (PAT), the `verify-ssl=false`
setting, the project / space / document coordinates and the fetch script all
stay exactly as they are for production.

Reference workflow: `lexion_fsm_polarion_requirements_read`
(customer capsule `v2_vpath_customer_workflows`, project `lexion_fsm_polarion`,
profile `lexion_fsm_polarion_requirements_read_api_test`, contract
CQ-WKP-C-CLAASNEW-LFP-04). Its fetch stage runs
`ground_guidance/scripts/fetch_polarion_document.py`, which issues only GETs:

| Request | Purpose |
|---|---|
| `GET /polarion/rest/v1/projects/{p}/spaces/{space}/documents/{doc}/parts?fields[document_parts]=@all&page[size]=100&page[number]=N` | all document parts, paginated over `links.next`, completeness checked against `meta.totalCount` |
| `GET /polarion/rest/v1/projects/{p}/workitems/{id}?fields[workitems]=id,title,type,outlineNumber,description,status` | one request per referenced work item |

Headers sent: `Authorization: Bearer <PAT>` and `Accept: application/json`.

## 1. What the mock provides

* **The exported document.** `src/mock/mock_data/polarion_dumps/*.json` holds
  raw dumps written by the fetch script (`polarion_document_raw.json`). Every
  dump is loaded at start-up: project, space, document, parts in document
  order, work items with title / type / status / outlineNumber / description.
  Bundled: `VPATHAI / System Layer / Technical_Specification-API_TEST`
  (218 parts, 158 work items, exported 2026-09-11).
* **PAT authentication.** `MOCK_AUTH_MODE=pat` (default) accepts any
  well-formed JWT as bearer token, i.e. the customer PAT from `.env.secrets`
  works unchanged. Expired PATs are accepted (warning in the log) unless
  `MOCK_PAT_CHECK_EXPIRY=true`. Invalid tokens get the same 401 JSON:API error
  as production.
* **HTTPS with a self-signed certificate** (`--ssl`), so the overlay's
  `POLARION_VERIFY_SSL: "false"` is exercised like against production.
* **Dual-stack listener** (IPv4 + IPv6). `localhost` resolves to `::1` first on
  Windows; an IPv4-only server costs ~2 s per request.
* **Polarion response shapes**: `meta.totalCount`, percent-encoded pagination
  links (`page%5Bnumber%5D=2`, `%40all`), `attributes.id/type/content` of
  parts, `relationships.workItem.data.id = "PROJECT/WI-ID"`, `description`
  as `{type: text/html, value}`, absolute `links.self`, UTF-8 as-is.
  The responses validate against `Input/api/polarionrest.json`
  (`tests/mock_unit/test_openapi_contract.py`).

## 2. Run the workflow against the mock

```powershell
# 1. start the mock (repo PolarionMock)
python run_mock.py --ssl            # https://localhost:5001, auth mode pat

# 2. in the customer capsule: change ONLY this line of the profile overlay
#    customers/CLAAS_New/projects/lexion_fsm_polarion/environment.lexion_fsm_polarion_requirements_read_api_test.yaml
#      POLARION_BASE_URL: "https://polarion-d.claas.local"   ->   POLARION_BASE_URL: "https://localhost:5001"

# 3. run the workflow exactly as for production (from the capsule root)
$env:VPATH_CUSTOMERS_ROOT = "$PWD\customers"
python <left_side>\tools\run_workflow.py --customer CLAAS_New --project lexion_fsm_polarion `
       --profile lexion_fsm_polarion_requirements_read_api_test -y
```

The run lands `requirements.yaml` under
`playground/CLAAS_New_lexion_fsm_polarion_requirements_read/.../003_build_requirements/`.
Compared with the production run of 2026-09-11 the `requirements` list is
identical (29 requirements: 10 systemrequirement + 19 componentrequirement,
natural outline order, description verbatim HTML); only `meta.fetched_at`
and `meta.polarion_base_url` differ.

Note for Git Bash users: the MSYS `timeout` command strips the environment
(`VPATH_CUSTOMERS_ROOT`, `USERNAME`, ...). Do not wrap the runner in it.

Plain HTTP works too (`python run_mock.py`, overlay `http://localhost:5001`);
the fetch script ignores `--verify-ssl` for HTTP.

## 3. Serve another document

1. Run the fetch script once against production (or take the
   `polarion_document_raw.json` of a finished run) and copy the file into
   `src/mock/mock_data/polarion_dumps/` (any file name), **or** add a
   directory with dumps via `--dump-dir DIR` / `MOCK_DUMP_DIR`, **or** load it
   at runtime:

   ```bash
   curl -sk -X POST https://localhost:5001/mock/admin/dumps \
        -H "Authorization: Bearer $PAT" -H "Content-Type: application/json" \
        --data-binary @polarion_document_raw.json
   ```

2. Check the coordinates the mock serves:
   `GET /mock/admin/documents` (project, space, document, part / work item
   counts, parts URL) or `GET /health` (`dumps`).
3. Point the overlay's `POLARION_PROJECT_ID`, `POLARION_SPACE_ID`,
   `POLARION_DOCUMENT_NAME` at it (they already match for the bundled dump).

`POST /mock/admin/reset` reseeds the store (dummy data + dumps on disk).

## 4. Tests that pin this contract

```bash
python -m pytest tests/mock_unit -q --env mock
```

| File | What it proves |
|---|---|
| `test_requirements_read_workflow.py` | replay of the fetch sequence == production export; pagination, `totalCount`, sparse fieldsets, includes, 404s, requirement type filter (29 = 10 + 19) |
| `test_fetch_script_live.py` | the **real** customer fetch script (subprocess, unchanged) against a live mock reproduces the export; fails hard without token; 404 for an unknown document |
| `test_auth_and_headers.py` | PAT accepted, expired PAT policy, 401 for garbage / missing / Basic, strict + disabled modes, `Accept` handling (406 for non-JSON) |
| `test_openapi_contract.py` | parts list / single part / work item / error responses validate against `Input/api/polarionrest.json` |
| `test_dump_loader.py` | dumps load at start-up and at runtime, reload replaces, reset restores, invalid dumps rejected |

The live-script test looks for the script at
`C:\Users\E017093\v2_vpath_customer_workflows\customers\CLAAS_New\projects\ground_guidance\scripts\fetch_polarion_document.py`
(override with `VPATH_FETCH_SCRIPT`) and skips when it is absent.

## 5. Matching a newer Polarion release

The contract test validates against the OpenAPI document in
`Input/api/polarionrest.json`. To pin the mock to a newer Polarion (e.g.
25.12), export that server's OpenAPI JSON (Swagger UI -> `/polarion/rest/v1/openapi.json`)
over the file and run the contract tests; differences show up as schema
errors with the JSON path of the offending field.
