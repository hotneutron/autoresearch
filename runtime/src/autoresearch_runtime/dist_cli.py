"""Opt-in distributed POC command-line interface; legacy execution is unchanged."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .artifacts import ArtifactStore
from .contracts import canonical
from .control_plane import ControlPlane
from .global_store import GlobalStore
from .hosting import server
from .host_agent import Client, HostAgent
from .supervisor import SystemdSupervisor


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve")
    serve.add_argument("--bind", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8766)
    serve.add_argument("--tls-cert"); serve.add_argument("--tls-key"); serve.add_argument("--authority")
    submit = sub.add_parser("call"); submit.add_argument("operation"); submit.add_argument("document", type=Path)
    sub.add_parser("status")
    agent = sub.add_parser("agent"); agent.add_argument("config", type=Path); agent.add_argument("--once", action="store_true")
    sub.add_parser("preflight")
    backup = sub.add_parser("backup"); backup.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "agent":
            config = json.loads(args.config.read_text())
            client = Client(config["coordinator_url"])
            supervisor = SystemdSupervisor(args.store / "supervisor", user=config.get("systemd_user", True))
            instance = HostAgent(client, supervisor, args.store / "agent", config["host"], config["roots"])
            instance.service(config["round_id"], once=args.once)
            return 0
        if args.command == "preflight":
            from .capabilities import probe
            print(canonical({"capabilities": probe(), "supervisor": SystemdSupervisor(args.store / "supervisor").qualification()}))
            return 0
        store = GlobalStore(args.store)
        archive = ArtifactStore(args.archive or args.store / "archive")
        if args.command == "serve":
            with store.leadership():
                httpd = server(store, archive, host=args.bind, port=args.port, tls_cert=args.tls_cert, tls_key=args.tls_key, authority=args.authority)
                print(canonical({"url": ("https" if args.tls_cert else "http") + f"://{args.bind}:{httpd.server_port}", "access_mode": "anonymous_poc", "qualification": "POC; infrastructure conformance deferred"}), flush=True)
                try: httpd.serve_forever()
                finally: httpd.server_close()
        elif args.command == "call": print(canonical(ControlPlane(store, archive).call(args.operation, json.loads(args.document.read_text()))))
        elif args.command == "status": print(canonical(store.snapshot()))
        elif args.command == "backup":
            from .migration import recovery_catalog
            print(canonical(recovery_catalog(store, archive, args.destination)))
        return 0
    except KeyboardInterrupt: return 130
    except (OSError, ValueError, KeyError) as error:
        print(canonical({"error": str(error)}), file=sys.stderr); return 1


if __name__ == "__main__": raise SystemExit(main())
