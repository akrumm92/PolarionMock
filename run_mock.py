#!/usr/bin/env python3
"""
Start the Polarion mock server for stand-alone workflow testing.

Typical use (a workflow that reads a Polarion document over the REST API):

    python run_mock.py --ssl                # https://localhost:5001, self-signed
    python run_mock.py --port 8443 --ssl    # different port
    python run_mock.py                      # plain http://localhost:5001

Then change ONLY the base URL in the workflow's profile overlay, e.g.

    POLARION_BASE_URL: "https://localhost:5001"     (was https://polarion-d.claas.local)

and run the workflow as usual. The PAT from .env.secrets is accepted as-is
(MOCK_AUTH_MODE=pat), the self-signed certificate matches
POLARION_VERIFY_SSL=false, and the document served is the one exported from
production (src/mock/mock_data/polarion_dumps/*.json).
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default=os.getenv("MOCK_HOST", "0.0.0.0"), help="bind address (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=int(os.getenv("MOCK_PORT", "5001")), help="port (default 5001)")
    parser.add_argument("--ssl", action="store_true", help="serve HTTPS with an ad-hoc self-signed certificate")
    parser.add_argument("--cert", help="PEM certificate (with --key) instead of the ad-hoc certificate")
    parser.add_argument("--key", help="PEM private key (with --cert)")
    parser.add_argument("--auth-mode", choices=["pat", "strict", "disabled"], default=os.getenv("MOCK_AUTH_MODE", "pat"),
                        help="pat: accept Polarion PATs (default); strict: mock JWT only; disabled: no auth")
    parser.add_argument("--check-pat-expiry", action="store_true", help="reject expired PATs like production does")
    parser.add_argument("--dump-dir", action="append", default=[],
                        help="additional directory with polarion_document_raw.json dumps (repeatable)")
    parser.add_argument("--debug", action="store_true", help="Flask debug mode")
    parser.add_argument("--log-format", choices=["text", "json"], default=os.getenv("LOG_FORMAT", "text"))
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    os.environ["MOCK_HOST"] = args.host
    os.environ["MOCK_PORT"] = str(args.port)
    os.environ["MOCK_AUTH_MODE"] = args.auth_mode
    os.environ["DISABLE_AUTH"] = "true" if args.auth_mode == "disabled" else "false"
    os.environ["MOCK_DEBUG"] = "true" if args.debug else "false"
    os.environ["LOG_FORMAT"] = args.log_format
    if args.check_pat_expiry:
        os.environ["MOCK_PAT_CHECK_EXPIRY"] = "true"
    if args.ssl:
        os.environ["MOCK_SSL"] = "true"
    if args.cert and args.key:
        os.environ["MOCK_SSL_CERT"] = args.cert
        os.environ["MOCK_SSL_KEY"] = args.key
    if args.dump_dir:
        extra = os.pathsep.join(str(Path(d).resolve()) for d in args.dump_dir)
        current = os.getenv("MOCK_DUMP_DIR", "")
        os.environ["MOCK_DUMP_DIR"] = os.pathsep.join(x for x in (current, extra) if x)

    # Import after the environment is set: the data store seeds on import.
    from src.mock.app import run_server
    from src.mock.storage.data_store import data_store

    scheme = "https" if (args.ssl or (args.cert and args.key)) else "http"
    shown_host = "localhost" if args.host in ("0.0.0.0", "::") else args.host
    print(f"Polarion mock: {scheme}://{shown_host}:{args.port}/polarion/rest/v1  (auth mode: {args.auth_mode})")
    print(f"  put into the workflow overlay:  POLARION_BASE_URL: \"{scheme}://{shown_host}:{args.port}\"")
    if data_store.dump_summaries:
        print("  documents loaded from Polarion dumps:")
        for summary in data_store.dump_summaries:
            print(f"    project={summary['project']!r} space={summary['space']!r} "
                  f"document={summary['document']!r}  ({summary['parts']} parts, {summary['workitems']} work items)")
    else:
        print("  no Polarion dumps loaded (src/mock/mock_data/polarion_dumps is empty)")
    run_server()
    return 0


if __name__ == "__main__":
    sys.exit(main())
