import argparse
import asyncio
import json
from dataclasses import asdict

from app.workers.certificate_tasks import _repair_publication


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Resume confirmed certificate issuance and restore missing private "
            "publication drafts."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Required safety switch before production data is repaired.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if not args.apply:
        _parser().error("--apply is required")
    report = asyncio.run(_repair_publication())
    print(json.dumps(asdict(report), sort_keys=True))
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
