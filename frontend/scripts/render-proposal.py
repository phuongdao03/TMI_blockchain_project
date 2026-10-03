"""Render the proposal PDF into page images and searchable page text.

Run with PyMuPDF and Pillow installed:
    python scripts/render-proposal.py
"""

from pathlib import Path
import json

import pymupdf
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/assets/institution/proposal-2026.pdf"
OUTPUT = ROOT / "public/assets/institution/proposal-pages"
TEXT_OUTPUT = ROOT / "src/components/public/proposal-page-text.json"
WIDTH = 1600


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open(SOURCE)
    page_text = []

    for number, page in enumerate(document, start=1):
        scale = WIDTH / page.rect.width
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        image.save(OUTPUT / f"page-{number:02}.webp", "WEBP", quality=83, method=6)
        page_text.append(page.get_text(sort=True).strip())

    TEXT_OUTPUT.write_text(json.dumps(page_text, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Rendered {len(document)} pages at {WIDTH}px to {OUTPUT}")


if __name__ == "__main__":
    main()
