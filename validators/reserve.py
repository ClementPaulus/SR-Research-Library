"""Command-line reservation client for direct (Codespaces / PR) contributors.

Usage:
    python -m validators.reserve NAMESPACE --purpose "text" [--operation-key KEY] [--notes "text"]
    python -m validators.reserve --publish VALUE --record PATH
    python -m validators.reserve --withdraw VALUE
    python -m validators.reserve --next NAMESPACE

NAMESPACE is one of AUTH, SR-OBJ, SRC, REL, RCPT, SR-GOV. The reservation is
written to registry/reservations/<value>.json and must be committed with the
work it reserves. Repeating a call with the same --operation-key returns the
existing reservation rather than allocating another value.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import allocation


def main(argv: list = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m validators.reserve", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("namespace", nargs="?", choices=sorted(allocation.NAMESPACES))
    parser.add_argument("--purpose")
    parser.add_argument("--operation-key")
    parser.add_argument("--notes")
    parser.add_argument("--route", default="cli", choices=["cli", "portal"])
    parser.add_argument("--next", metavar="NAMESPACE", choices=sorted(allocation.NAMESPACES),
                        help="print the next free value without reserving it")
    parser.add_argument("--publish", metavar="VALUE", help="mark a reservation published")
    parser.add_argument("--record", metavar="PATH", help="repository-relative record path for --publish")
    parser.add_argument("--withdraw", metavar="VALUE", help="mark a reservation withdrawn (never reused)")
    args = parser.parse_args(argv)

    if args.next:
        print(allocation.next_free(args.next))
        return 0
    if args.publish:
        if not args.record:
            parser.error("--publish requires --record PATH")
        print(json.dumps(allocation.mark_state(args.publish, "published", published_record_path=args.record), indent=2))
        return 0
    if args.withdraw:
        print(json.dumps(allocation.mark_state(args.withdraw, "withdrawn"), indent=2))
        return 0
    if not args.namespace or not args.purpose:
        parser.error("NAMESPACE and --purpose are required to reserve a value")
    record = allocation.reserve(args.namespace, args.purpose, operation_key=args.operation_key,
                                route=args.route, notes=args.notes)
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
