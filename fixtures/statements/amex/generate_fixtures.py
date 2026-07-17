"""Generate deterministic, entirely synthetic Amex parser PDF fixtures."""

from __future__ import annotations

from pathlib import Path

FIXTURE_DIRECTORY = Path(__file__).resolve().parent


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_bytes(pages: tuple[tuple[str, ...], ...]) -> bytes:
    page_count = len(pages)
    content_start = 3 + page_count
    font_object = content_start + page_count
    kids = " ".join(f"{3 + index} 0 R" for index in range(page_count))
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode(),
    ]
    for index in range(page_count):
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font_object} 0 R >> >> "
                f"/Contents {content_start + index} 0 R >>"
            ).encode()
        )
    for page in pages:
        commands = ["BT /F1 9 Tf 50 750 Td 13 TL"]
        commands.extend(f"({_escape_pdf_text(line)}) Tj T*" for line in page)
        commands.append("ET")
        content = "\n".join(commands).encode()
        objects.append(
            b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n"
            + content
            + b"\nendstream"
        )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    pdf = bytearray(b"%PDF-1.4\n% synthetic fixture\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode()
    )
    return bytes(pdf)


FULL_MATRIX_PAGES = (
    (
        "AMERICAN EXPRESS",
        "COBALT CARD",
        "ACCOUNT NUMBER XXXX-XXXXXX-X1007",
        "STATEMENT PERIOD JUNE 1, 2026 TO JUNE 30, 2026",
        "ACCOUNT SUMMARY",
        "PREVIOUS BALANCE $500.00",
        "PAYMENTS AND CREDITS -$1,525.00",
        "NEW CHARGES $1,486.00",
        "NEW BALANCE $461.00",
        "PAYMENTS AND CREDITS",
        "JUN 04 PAYMENT RECEIVED - THANK YOU $1,500.00",
        "JUN 06 SYNTHETIC RETURN $25.00",
        "CONTINUED ON NEXT PAGE",
    ),
    (
        "AMERICAN EXPRESS",
        "PAGE 2 OF 2",
        "NEW CHARGES",
        "JUN 02 SYNTHETIC MARKET 1,234.56",
        "JUN 08 SYNTHETIC CLOUD $13.45",
        "DESCRIPTION CONTINUED: MONTHLY SERVICE",
        "FOREIGN CURRENCY USD $10.00 AT 1.34500000",
        "JUN 10 ANNUAL MEMBERSHIP FEE $25.65",
        "JUN 12 INTEREST CHARGED $12.34",
        "JUN 14 SYNTHETIC CAFE $100.00",
        "JUN 14 SYNTHETIC CAFE $100.00",
        "MEMBERSHIP REWARDS SUMMARY",
        "IMPORTANT INFORMATION ABOUT THIS SYNTHETIC DOCUMENT",
    ),
)

UNSUPPORTED_PAGES = (
    (
        "AMERICAN EXPRESS",
        "COBALT CARD",
        "ACCOUNT NUMBER XXXX-XXXXXX-X1007",
        "STATEMENT PERIOD JUNE 1, 2026 TO JUNE 30, 2026",
        "ACTIVITY LIST IN AN UNKNOWN FUTURE LAYOUT",
        "SYNTHETIC CONTENT ONLY",
    ),
)

SCANNED_PLACEHOLDER_PAGES = ((),)


def main() -> None:
    fixtures = {
        "amex_full_matrix.pdf": FULL_MATRIX_PAGES,
        "amex_unsupported_layout.pdf": UNSUPPORTED_PAGES,
        "amex_scanned_placeholder.pdf": SCANNED_PLACEHOLDER_PAGES,
    }
    for filename, pages in fixtures.items():
        (FIXTURE_DIRECTORY / filename).write_bytes(_pdf_bytes(pages))


if __name__ == "__main__":
    main()
