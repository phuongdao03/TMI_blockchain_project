"""Export local migration seed articles for the read-only guide preview."""

import json
import os
import re
import sqlite3
import sys
import tempfile
from html import unescape
from pathlib import Path

from alembic import command
from alembic.config import Config

BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))


def main(output: Path) -> None:
    with tempfile.TemporaryDirectory(
        prefix="guide-preview-", ignore_cleanup_errors=True
    ) as directory:
        database = Path(directory) / "preview.sqlite3"
        os.environ["DATABASE_DIRECT_URL"] = f"sqlite+aiosqlite:///{database.as_posix()}"
        os.environ["BLOCKCHAIN_NETWORK"] = "local"
        os.environ["BLOCKCHAIN_CHAIN_ID"] = "31337"
        command.upgrade(Config(BACKEND_ROOT / "alembic.ini"), "head")
        with sqlite3.connect(database) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT id, title, slug, summary, category, audiences, "
                "body_html, status, sort_order, version, published_at, "
                "created_at, updated_at FROM cms_guide_articles "
                "ORDER BY sort_order, slug"
            ).fetchall()
            articles = []
            for row in rows:
                body = row["body_html"]
                plain = unescape(re.sub(r"<[^>]+>", " ", body))
                articles.append(
                    {
                        "id": str(row["id"]),
                        "title": row["title"],
                        "slug": row["slug"],
                        "summary": row["summary"],
                        "category": row["category"],
                        "audiences": json.loads(row["audiences"]),
                        "bodyHtml": body,
                        "status": row["status"],
                        "sortOrder": row["sort_order"],
                        "version": row["version"],
                        "readingMinutes": max(1, (len(plain.split()) + 199) // 200),
                        "publishedAt": row["published_at"],
                        "createdAt": row["created_at"],
                        "updatedAt": row["updated_at"],
                    }
                )
    output.write_text(json.dumps(articles, ensure_ascii=False), encoding="utf-8")
    print(f"Exported {len(articles)} local guide articles to {output}")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
