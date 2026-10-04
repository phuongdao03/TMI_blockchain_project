# Certificate PDF title and drum watermark

## Objective

Make the recorded work title the main content of the generated establishment PDF and use the same Dong Son drum artwork shown on the public certificate. Explain the origins of certificate and dossier identifiers without changing their values.

## Commands and structure

- Tests: `cd backend && python -m pytest app/tests/test_certificate_generation.py -q`
- Lint: `cd backend && python -m ruff check app/modules/certificates/pdf.py app/tests/test_certificate_generation.py`
- Renderer: `backend/app/modules/certificates/pdf.py`; tests: `backend/app/tests/test_certificate_generation.py`; artwork: `backend/app/assets/images/`.

## Style, testing, and boundaries

Keep the existing ReportLab canvas. Use embedded Noto Serif Bold for the certificate heading, Noto Serif Regular for the work title, and Noto Sans for small details. Both serif font files come from the official Noto Fonts repository under the included OFL license. Test the type roles and the drum image. Render a representative Vietnamese PDF and inspect it visually. Keep certificate numbering, metadata, QR destination, and issued files unchanged; existing PDF versions remain historical records.

## Success criteria and plan

1. The title is visibly larger and wraps without truncation for representative long Vietnamese titles.
2. A faint drum watermark uses the public certificate artwork without reducing text or QR legibility.
3. Vietnamese text with decomposed Unicode accents is normalized for PDF display without changing signed metadata.
4. Existing PDF content and deterministic output tests pass.
5. Existing issued PDF media is not silently replaced; new rendering applies to new versions or explicit reissuance.

Implement a focused renderer test, add the artwork and layout, then run tests and inspect a generated page.
