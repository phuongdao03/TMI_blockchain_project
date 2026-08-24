from datetime import UTC, datetime

from app.modules.certificates.metadata import CertificateMetadataBuilder


def test_metadata_requires_explicit_public_document_access_scope() -> None:
    snapshot: dict[str, object] = {
        "dossier": {
            "code": "TMI-2026-0001",
            "title": "Bộ nhận diện TMI",
            "category": {"code": "BRAND", "name": "Thương hiệu"},
            "dossierType": {
                "formData": {"ownerEmail": "owner-private@example.test"},
                "publicFields": [
                    {
                        "key": "story",
                        "label": "Public story",
                        "value": "Approved public narrative.",
                    },
                    {
                        "key": "ownerEmail",
                        "label": "Owner email",
                        "value": {"email": "owner-private@example.test"},
                    },
                ],
            },
        },
        "evidences": [
            {
                "title": "Tác phẩm công khai",
                "evidenceType": "ARTWORK_IMAGE",
                "accessScope": "PUBLIC",
                "isPublic": False,
                "media": {"sha256": "ab" * 32},
            },
            {
                "title": "Ảnh xem trước",
                "evidenceType": "ARTWORK_PREVIEW",
                "accessScope": "PUBLIC_PREVIEW",
                "isPublic": False,
                "media": {"sha256": "cd" * 32},
            },
            {
                "title": "Snapshot cũ thiếu phạm vi",
                "evidenceType": "LEGACY",
                "isPublic": True,
                "media": {"sha256": "ef" * 32},
            },
            {
                "title": "Tài liệu nội bộ",
                "evidenceType": "IDENTITY_DOCUMENT",
                "accessScope": "INTERNAL",
                "isPublic": True,
                "media": {"sha256": "01" * 32},
            },
        ],
    }

    metadata, _ = CertificateMetadataBuilder().build(
        certificate_number="TMI-2026-000000000001",
        certificate_version=1,
        dossier_version=1,
        snapshot=snapshot,
        issued_at=datetime(2026, 8, 24, tzinfo=UTC),
        expires_at=None,
    )

    assert metadata["publicEvidences"] == [
        {
            "title": "Tác phẩm công khai",
            "type": "ARTWORK_IMAGE",
            "sha256": "ab" * 32,
            "accessScope": "PUBLIC",
        },
        {
            "title": "Ảnh xem trước",
            "type": "ARTWORK_PREVIEW",
            "sha256": "cd" * 32,
            "accessScope": "PUBLIC_PREVIEW",
        },
    ]
    assert metadata["publicFields"] == [
        {
            "key": "story",
            "label": "Public story",
            "value": "Approved public narrative.",
        }
    ]
    assert "owner-private@example.test" not in str(metadata)
