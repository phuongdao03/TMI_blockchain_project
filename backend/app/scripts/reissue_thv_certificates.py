"""Stage THV numbers against confirmed dossier proofs and queue PDF cutover."""

import argparse
import asyncio
import json
from dataclasses import asdict

from app.core.config import get_settings
from app.db.session import create_runtime_engine, create_session_factory
from app.modules.certificates.rebrand import CertificateRebrandService
from app.workers.celery_app import celery_app


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reissue legacy certificates as THV numbers."
    )
    parser.add_argument("phase", choices=("prepare", "render"))
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply this phase; otherwise show a dry run.",
    )
    return parser


async def _run(*, phase: str, apply: bool) -> int:
    settings = get_settings()
    engine = create_runtime_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            reissue = CertificateRebrandService(
                session,
                public_base_url=settings.app_base_url,
                environment=settings.app_env,
                validity_days=settings.certificate_validity_days,
            )
            if phase == "prepare":
                report = await reissue.run(dry_run=not apply)
                payload = asdict(report)
                payload["replacement_version_ids"] = [
                    str(value) for value in report.replacement_version_ids
                ]
                print(json.dumps(payload, sort_keys=True))
                return 0
            targets = await reissue.ready_to_render()
        if not apply:
            print(
                json.dumps(
                    {"phase": phase, "candidates": len(targets), "dry_run": True}
                )
            )
            return 0
        for version_id in targets:
            celery_app.send_task(
                "app.workers.certificate_tasks.render_certificate_version",
                args=[str(version_id)],
            )
        print(json.dumps({"phase": phase, "queued": len(targets)}))
        return 0
    finally:
        await engine.dispose()


def main() -> int:
    args = _parser().parse_args()
    return asyncio.run(_run(phase=args.phase, apply=bool(args.apply)))


if __name__ == "__main__":
    raise SystemExit(main())
