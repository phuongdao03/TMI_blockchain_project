"""Store the public display name with the platform profile.

Revision ID: 0111_public_profile_identity
Revises: 0110_community_avatar_media
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "0111_public_profile_identity"
down_revision: str | None = "0110_community_avatar_media"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.add_column(sa.Column("display_name", sa.String(length=120)))
        batch_op.add_column(sa.Column("avatar_url", sa.String(length=500)))

    op.execute(
        sa.text(
            """
            INSERT INTO user_profiles (
                user_id, display_name, avatar_media_id, avatar_url
            )
            SELECT cp.user_id, cp.display_name, cp.avatar_media_id, cp.avatar_url
            FROM community_profiles AS cp
            LEFT JOIN user_profiles AS up ON up.user_id = cp.user_id
            WHERE up.user_id IS NULL
              AND (cp.display_name IS NOT NULL OR cp.avatar_media_id IS NOT NULL
                   OR cp.avatar_url IS NOT NULL)
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE user_profiles
            SET display_name = COALESCE(
                    display_name,
                    (SELECT cp.display_name FROM community_profiles AS cp
                     WHERE cp.user_id = user_profiles.user_id)
                ),
                avatar_media_id = COALESCE(
                    avatar_media_id,
                    (SELECT cp.avatar_media_id FROM community_profiles AS cp
                     WHERE cp.user_id = user_profiles.user_id)
                ),
                avatar_url = COALESCE(
                    avatar_url,
                    (SELECT cp.avatar_url FROM community_profiles AS cp
                     WHERE cp.user_id = user_profiles.user_id)
                )
            WHERE EXISTS (
                SELECT 1 FROM community_profiles AS cp
                WHERE cp.user_id = user_profiles.user_id
            )
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    identity_rows = bind.execute(
        sa.text(
            """
            SELECT up.user_id, up.display_name, up.avatar_media_id, up.avatar_url
            FROM user_profiles AS up
            LEFT JOIN community_profiles AS cp ON cp.user_id = up.user_id
            WHERE cp.user_id IS NULL
              AND (up.display_name IS NOT NULL OR up.avatar_media_id IS NOT NULL
                   OR up.avatar_url IS NOT NULL)
            """
        )
    ).all()
    community_profiles = sa.table(
        "community_profiles",
        sa.column("user_id", sa.Uuid()),
        sa.column("username", sa.String(length=64)),
        sa.column("display_name", sa.String(length=120)),
        sa.column("avatar_media_id", sa.Uuid()),
        sa.column("avatar_url", sa.String(length=500)),
    )
    for user_id, display_name, avatar_media_id, avatar_url in identity_rows:
        parsed_id = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
        op.bulk_insert(
            community_profiles,
            [
                {
                    "user_id": parsed_id,
                    "username": f"member-{parsed_id.hex}",
                    "display_name": display_name,
                    "avatar_media_id": avatar_media_id,
                    "avatar_url": avatar_url,
                }
            ],
        )

    op.execute(
        sa.text(
            """
            UPDATE community_profiles
            SET display_name = COALESCE(
                    display_name,
                    (SELECT up.display_name FROM user_profiles AS up
                     WHERE up.user_id = community_profiles.user_id)
                ),
                avatar_media_id = COALESCE(
                    avatar_media_id,
                    (SELECT up.avatar_media_id FROM user_profiles AS up
                     WHERE up.user_id = community_profiles.user_id)
                ),
                avatar_url = COALESCE(
                    avatar_url,
                    (SELECT up.avatar_url FROM user_profiles AS up
                     WHERE up.user_id = community_profiles.user_id)
                )
            WHERE EXISTS (
                SELECT 1 FROM user_profiles AS up
                WHERE up.user_id = community_profiles.user_id
            )
            """
        )
    )
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.drop_column("display_name")
        batch_op.drop_column("avatar_url")
