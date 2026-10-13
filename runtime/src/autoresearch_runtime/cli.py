"""Command-line entry point for the research runtime and its built-in inbox."""
import argparse
import json
from pathlib import Path
import sys
import threading

from .controller import Controller
from .review import Inbox, encode, server
from .store import migrate


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", type=Path, required=True)
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Freeze a project adapter's campaign contract")
    init.add_argument("contract", type=Path)
    submit = sub.add_parser("submit", help="Submit a declared unit; no arbitrary argv or gate overrides")
    submit.add_argument("task")
    submit.add_argument("--unit")
    sub.add_parser("status")
    sub.add_parser("step")
    for name in ("run", "resume"):
        run = sub.add_parser(name, help="Service the queue and built-in inbox; human branch holds remain effective")
        run.add_argument("--idle-timeout", type=float, default=0)
        run.add_argument("--port", type=int, default=8765)
    review = sub.add_parser("review")
    review.add_argument("operation", choices=("serve", "status", "export", "publish", "overview"))
    review.add_argument("document", type=Path, nargs="?", help="Packet JSON for publish, workflow JSON for overview")
    review.add_argument("--repo", type=Path, help="Released evidence root (default: store)")
    review.add_argument("--port", type=int, default=8765)
    review.add_argument("--output", type=Path)
    goal = sub.add_parser("goal", help="Persistent goal steering above campaign execution")
    goal.add_argument("operation", choices=("anchor", "proposal", "assess", "control", "checkpoint", "reorient", "status"))
    goal.add_argument("document", type=Path, nargs="?")
    steering = sub.add_parser("steer")
    steering.add_argument("record", type=Path)
    migration = sub.add_parser("migrate")
    migration.add_argument("source", type=Path)
    migration.add_argument("--project", type=Path, required=True)
    args = p.parse_args()
    httpd = None
    try:
        if args.command == "migrate":
            result = migrate(args.source, args.store, args.project)
        elif args.command == "goal":
            from .goals import GoalLedger
            ledger = GoalLedger(args.store)
            if args.operation == "status":
                result = ledger.snapshot()
            else:
                if args.document is None:
                    raise ValueError("A goal record JSON document is required")
                result = getattr(ledger, args.operation)(json.loads(args.document.read_text()))
        elif args.command == "review":
            # Prototype inboxes have no runtime contract. Review reads immutable
            # stored snapshots and does not dispatch experimental jobs.
            inbox = Inbox(args.store, args.repo or args.store)
            if args.operation in {"publish", "overview"}:
                if args.document is None:
                    raise ValueError("A JSON document is required")
                document = json.loads(args.document.read_text())
                if args.operation == "overview":
                    from .workflow import publish_overview
                    result = publish_overview(inbox, document)
                else:
                    result = inbox.publish(document)
            elif args.operation == "status":
                result = inbox.snapshot()
            elif args.operation == "export":
                if args.output is None:
                    raise ValueError("--output is required")
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(inbox.html(offline=True))
                result = {"output": str(args.output)}
            else:
                httpd = server(inbox, args.port)
                print(f"Review inbox: http://127.0.0.1:{httpd.server_port}", flush=True)
                httpd.serve_forever()
                result = {}
        else:
            c = Controller(args.store, json.loads(args.contract.read_text()) if args.command == "init" else None)
            if args.command == "init":
                result = {"campaign": c.contract["id"], "store": str(c.directory)}
            elif args.command == "submit":
                result = c.submit(args.task, args.unit)
            elif args.command == "status":
                result = c.status()
            elif args.command == "step":
                result = c.step()
            elif args.command == "steer":
                result = c.steer(json.loads(args.record.read_text()))
            elif args.command in {"run", "resume"}:
                httpd = server(c.inbox, args.port)
                threading.Thread(target=httpd.serve_forever, daemon=True).start()
                print(f"Review inbox: http://127.0.0.1:{httpd.server_port}", file=sys.stderr, flush=True)
                result = c.run(idle_timeout=args.idle_timeout)
        print(encode(result))
        return 0
    except KeyboardInterrupt:
        print("Controller stopped. Detached units retain their receipts and leases; resume to reconcile.", file=sys.stderr)
        return 130
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(encode({"error": str(error)}), file=sys.stderr)
        return 1
    finally:
        if httpd:
            # serve_forever in the current thread already exited on interrupt.
            if args.command in {"run", "resume"}:
                httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
