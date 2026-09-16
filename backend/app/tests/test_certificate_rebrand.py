from datetime import UTC, datetime

from app.modules.certificates.rebrand import replacement_metadata


def test_replacement_metadata_uses_cns_identity_without_mutating_source() -> None:
    source: dict[str, object] = {
        "certificateNumber": "TMI-2026-OLD",
        "certificateVersion": 3,
        "dossierCode": "TMI-2026-DOSSIER",
        "asset": {"title": "Tác phẩm", "subject": "Chủ thể hồ sơ TMI"},
    }

    metadata, digest = replacement_metadata(
        source,
        certificate_number="CNS-2026-NEW",
        issued_at=datetime(2026, 9, 16, tzinfo=UTC),
        expires_at=datetime(2027, 9, 16, tzinfo=UTC),
    )

    assert metadata["certificateNumber"] == "CNS-2026-NEW"
    assert metadata["certificateVersion"] == 1
    assert metadata["dossierCode"] == "CNS-2026-DOSSIER"
    assert metadata["asset"] == {
        "title": "Tác phẩm",
        "subject": "Chủ thể hồ sơ CNS",
    }
    assert len(digest) == 64
    assert source["certificateNumber"] == "TMI-2026-OLD"
