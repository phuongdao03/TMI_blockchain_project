import argparse
import asyncio
import json
from dataclasses import asdict

from app.core.config import get_settings
from app.db.session import create_runtime_engine, create_session_factory
from app.modules.public.backfill import PublicWorkDraftBackfill


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create private draft public-work projections from eligible dossiers."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist drafts. Without this flag the command is a dry run.",
    )
    return parser


async def _run(*, apply: bool) -> int:
    engine = create_runtime_engine(get_settings())
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            report = await PublicWorkDraftBackfill(session).run(dry_run=not apply)
            if apply and session.in_transaction():
                await session.commit()
        print(json.dumps(asdict(report), sort_keys=True))
        return 0
    finally:
        await engine.dispose()


def main() -> int:
    args = _parser().parse_args()
    return asyncio.run(_run(apply=bool(args.apply)))


if __name__ == "__main__":
    raise SystemExit(main())
