import argparse
import asyncio
import json
from dataclasses import asdict

from app.core.config import get_settings
from app.db.session import create_runtime_engine, create_session_factory
from app.modules.certificates.rebrand import CertificateRebrandService
from app.workers.certificate_tasks import render_certificate_version


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Revoke active TMI certificates and issue CNS replacements."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist the cutover. Without this flag the command is a dry run.",
    )
    return parser


async def _run(*, apply: bool) -> int:
    settings = get_settings()
    engine = create_runtime_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            report = await CertificateRebrandService(
                session,
                public_base_url=settings.app_base_url,
                environment=settings.app_env,
                validity_days=settings.certificate_validity_days,
            ).run(dry_run=not apply)
        if apply:
            for version_id in report.replacement_version_ids:
                render_certificate_version.delay(str(version_id))
        payload = asdict(report)
        payload["replacement_version_ids"] = [
            str(value) for value in report.replacement_version_ids
        ]
        print(json.dumps(payload, sort_keys=True))
        return 0
    finally:
        await engine.dispose()


def main() -> int:
    args = _parser().parse_args()
    return asyncio.run(_run(apply=bool(args.apply)))


if __name__ == "__main__":
    raise SystemExit(main())
