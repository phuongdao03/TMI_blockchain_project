import json
import sqlite3
from pathlib import Path

from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_cms_guide_migration_seeds_roles_and_round_trips(
    tmp_path: Path, monkeypatch
) -> None:
    database_path = tmp_path / "cms-guides.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    try:
        command.upgrade(config, "0111_public_profile_identity")
        command.upgrade(config, "head")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            rows = connection.execute(
                "SELECT slug, audiences, status, search_text, created_by, search_title "
                "FROM cms_guide_articles ORDER BY sort_order"
            ).fetchall()
            categories = dict(
                connection.execute(
                    "SELECT slug, category FROM cms_guide_articles"
                ).fetchall()
            )
            indexes = {
                row[1]
                for row in connection.execute("PRAGMA index_list('cms_guide_articles')")
            }
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info('cms_guide_articles')")
            }
            public_faq = connection.execute(
                "SELECT body_html FROM cms_guide_articles "
                "WHERE slug = 'common-account-and-guide-questions'"
            ).fetchone()[0]
            dossier_body = connection.execute(
                "SELECT body_html FROM cms_guide_articles "
                "WHERE slug = 'create-and-submit-a-dossier'"
            ).fetchone()[0]
            verification_body = connection.execute(
                "SELECT body_html FROM cms_guide_articles "
                "WHERE slug = 'verify-a-certificate'"
            ).fetchone()[0]
            viewer_body = connection.execute(
                "SELECT body_html FROM cms_guide_articles "
                "WHERE slug = 'viewer-account-basics'"
            ).fetchone()[0]
            employee_body = connection.execute(
                "SELECT body_html FROM cms_guide_articles "
                "WHERE slug = 'attendance-and-employee-requests'"
            ).fetchone()[0]
            payment_body = connection.execute(
                "SELECT body_html FROM cms_guide_articles "
                "WHERE slug = 'dossier-payment-guide'"
            ).fetchone()[0]
            admin_fee_guide = connection.execute(
                "SELECT body_html FROM cms_guide_articles "
                "WHERE slug = 'admin-payment-requests'"
            ).fetchone()[0]
            new_guides = dict(
                connection.execute(
                    "SELECT slug, audiences FROM cms_guide_articles WHERE slug IN "
                    "('moderator-work-allocations', 'employee-attendance', "
                    "'employee-leave-request', 'employee-overtime-request', "
                    "'admin-review-assignments', 'admin-payment-requests', "
                    "'admin-guide-publishing')"
                ).fetchall()
            )
        assert {"cms_guide_articles", "cms_guide_feedback"} <= tables
        assert len(rows) == 46
        assert "PayOS" not in payment_body
        assert "Thanh toán trực tuyến" in payment_body
        assert '<a href="/admin/payments">Thu phí</a>' in admin_fee_guide
        assert '<a href="/admin/payments">Tài chính</a>' not in admin_fee_guide
        assert rows[0][0] == "explore-nominations"
        assert json.loads(rows[0][1]) == ["PUBLIC"]
        assert rows[0][2] == "PUBLISHED"
        assert any(
            json.loads(audiences) == ["EMPLOYEE"]
            and slug == "attendance-and-employee-requests"
            for slug, audiences, *_ in rows
        )
        assert any(
            json.loads(audiences) == ["VIEWER"] and slug == "viewer-account-basics"
            for slug, audiences, *_ in rows
        )
        assert any(
            json.loads(audiences) == ["USER"] and slug == "my-certificates"
            for slug, audiences, *_ in rows
        )
        assert categories["review-an-assigned-dossier"] == "review-workflows"
        assert categories["common-account-and-guide-questions"] == "faq"
        assert categories["my-certificates"] == "certificates"
        assert any("bang xac lap" in search_text for _, _, _, search_text, _, _ in rows)
        assert all(created_by is None for _, _, _, _, created_by, _ in rows)
        assert any(
            slug == "create-and-submit-a-dossier"
            and "tao va gui ho so de cu" in search_title
            for slug, _, _, _, _, search_title in rows
        )
        assert "<h3>" in public_faq
        assert "hàng đợi" not in public_faq
        assert "nhân sự" not in public_faq
        assert "<h2>Điều kiện sử dụng</h2>" in dossier_body
        assert "Kết quả tra cứu cho biết điều gì?" in verification_body
        assert "Blockchain" not in verification_body
        assert "dấu vân tay số" not in verification_body
        assert "vai trò USER" not in viewer_body
        assert "/help/employee-attendance" in employee_body
        assert "<h2>Chấm công</h2>" not in employee_body
        assert len(new_guides) == 7
        assert json.loads(new_guides["moderator-work-allocations"]) == ["MODERATOR"]
        assert json.loads(new_guides["employee-attendance"]) == ["EMPLOYEE"]
        assert json.loads(new_guides["admin-review-assignments"]) == ["SUPER_ADMIN"]
        with sqlite3.connect(database_path) as connection:
            account_guide = connection.execute(
                "SELECT audiences, body_html FROM cms_guide_articles "
                "WHERE slug = 'personal-profile-settings'"
            ).fetchone()
        assert json.loads(account_guide[0]) == [
            "VIEWER",
            "USER",
            "MODERATOR",
            "SUPER_ADMIN",
        ]
        assert "Tên hiển thị công khai" in account_guide[1]
        assert "Thay ảnh đại diện" in account_guide[1]
        with sqlite3.connect(database_path) as connection:
            detailed_guides = dict(
                connection.execute(
                    "SELECT slug, body_html FROM cms_guide_articles "
                    "WHERE slug IN ('dossier-payment-guide', "
                    "'review-process-and-scorecard', "
                    "'admin-attendance-configuration', 'admin-allocation-process')"
                ).fetchall()
            )
        assert len(detailed_guides) == 4
        assert "Chờ thanh toán" in detailed_guides["dossier-payment-guide"]
        assert "Tính minh bạch" in detailed_guides["review-process-and-scorecard"]
        assert "chính sách vùng" in detailed_guides["admin-attendance-configuration"]
        assert "đầu việc chung" in detailed_guides["admin-allocation-process"]
        assert any(
            slug == "review-process-and-scorecard"
            and json.loads(audiences) == ["MODERATOR"]
            for slug, audiences, *_ in rows
        )
        assert any(
            slug == "admin-attendance-corrections"
            and json.loads(audiences) == ["SUPER_ADMIN"]
            for slug, audiences, *_ in rows
        )
        with sqlite3.connect(database_path) as connection:
            faq_bodies = dict(
                connection.execute(
                    "SELECT slug, body_html FROM cms_guide_articles "
                    "WHERE slug IN ('dossier-faq', 'review-exceptions-faq')"
                ).fetchall()
            )
        assert all(
            "<h2>Câu hỏi thường gặp</h2>" in body and "<h3>" in body
            for body in faq_bodies.values()
        )
        with sqlite3.connect(database_path) as connection:
            account_admin_body = connection.execute(
                "SELECT body_html FROM cms_guide_articles "
                "WHERE slug = 'admin-user-accounts'"
            ).fetchone()[0]
        assert "Tạm đình chỉ" in account_admin_body
        assert "trang Người dùng không có thao tác này" in account_admin_body
        with sqlite3.connect(database_path) as connection:
            applicant_guide = connection.execute(
                "SELECT body_html FROM cms_guide_articles "
                "WHERE slug = 'applicant-process-overview'"
            ).fetchone()[0]
            viewer_guide = connection.execute(
                "SELECT body_html FROM cms_guide_articles "
                "WHERE slug = 'viewer-account-basics'"
            ).fetchone()[0]
            initiative_schema = connection.execute(
                "SELECT v.schema_json FROM dossier_type_versions v "
                "JOIN dossier_types t ON t.id = v.dossier_type_id "
                "WHERE t.code = 'INITIATIVE' LIMIT 1"
            ).fetchone()[0]
        assert "người thẩm định và người quyết định" not in applicant_guide
        assert "/help/create-and-submit-a-dossier" not in viewer_guide
        assert any(
            field.get("key") == "proposer" and field.get("label") == "Tác giả"
            for field in json.loads(initiative_schema)["fields"]
        )
        assert {
            "ix_cms_guide_articles_status_order",
            "ix_cms_guide_articles_search_text",
        } <= indexes
        assert {"search_title", "search_summary"} <= columns

        command.downgrade(config, "0111_public_profile_identity")
        with sqlite3.connect(database_path) as connection:
            remaining = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        assert not {"cms_guide_articles", "cms_guide_feedback"}.intersection(remaining)
        assert "cms_posts" in remaining
    finally:
        get_settings.cache_clear()


def test_guide_content_migration_preserves_edited_articles(
    tmp_path: Path, monkeypatch
) -> None:
    database_path = tmp_path / "cms-guides-edited.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    try:
        command.upgrade(config, "0113_help_center_role_audit")
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "UPDATE cms_guide_articles SET body_html = ?, version = 2 "
                "WHERE slug = ?",
                (
                    "<h2>Author revision</h2><p>Keep this copy.</p>",
                    "review-an-assigned-dossier",
                ),
            )
            connection.execute(
                "UPDATE cms_guide_articles SET body_html = ?, version = 2 "
                "WHERE slug IN ('verify-a-certificate', 'viewer-account-basics', "
                "'attendance-and-employee-requests')",
                ("<h2>Edited guide</h2><p>Keep this copy.</p>",),
            )
            connection.commit()
        command.upgrade(config, "head")
        with sqlite3.connect(database_path) as connection:
            row = connection.execute(
                "SELECT body_html, version FROM cms_guide_articles "
                "WHERE slug = 'review-an-assigned-dossier'"
            ).fetchone()
            edited_rows = connection.execute(
                "SELECT body_html, version FROM cms_guide_articles "
                "WHERE slug IN ('verify-a-certificate', 'viewer-account-basics', "
                "'attendance-and-employee-requests')"
            ).fetchall()
        assert row == ("<h2>Author revision</h2><p>Keep this copy.</p>", 2)
        assert edited_rows == [("<h2>Edited guide</h2><p>Keep this copy.</p>", 2)] * 3
    finally:
        get_settings.cache_clear()
