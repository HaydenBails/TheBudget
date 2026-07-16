"""Generate deterministic, entirely synthetic TD parser PDF fixtures."""

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
        "TD CANADA TRUST",
        "CREDIT CARD STATEMENT",
        "ACCOUNT NUMBER **** **** **** 4821",
        "STATEMENT PERIOD JUNE 1, 2026 - JUNE 30, 2026",
        "ACCOUNT ACTIVITY SUMMARY",
        "PAYMENTS AND CREDITS -$1,525.00",
        "PURCHASES AND OTHER CHARGES $1,448.01",
        "INTEREST CHARGES $12.34",
        "FEES $25.65",
        "NEW BALANCE $2,461.00",
        "TRANSACTION DATE POSTING DATE ACTIVITY DESCRIPTION AMOUNT",
        "JUN 02 JUN 03 SYNTHETIC MARKET 1,234.56",
        "JUN 04 JUN 05 PAYMENT - THANK YOU -1,500.00",
        "CONTINUED ON NEXT PAGE",
        "PAYMENT SLIP",
        "MINIMUM PAYMENT $25.00",
    ),
    (
        "TD CREDIT CARD",
        "PAGE 2 OF 3",
        "TRANSACTION DATE POSTING DATE ACTIVITY DESCRIPTION AMOUNT",
        "JUN 06 JUN 07 SYNTHETIC RETURN -25.00",
        "JUN 08 JUN 09 SYNTHETIC CLOUD $13.45",
        "DESCRIPTION CONTINUED: MONTHLY SERVICE",
        "FOREIGN CURRENCY USD $10.00",
        "EXCHANGE RATE 1.34500000",
        "JUN 10 JUN 11 ANNUAL FEE $25.65",
        "REWARDS SUMMARY",
        "REWARD BALANCE 999",
    ),
    (
        "TD CREDIT CARD",
        "PAGE 3 OF 3",
        "TRANSACTION DATE POSTING DATE ACTIVITY DESCRIPTION AMOUNT",
        "JUN 12 JUN 13 INTEREST CHARGE $12.34",
        "JUN 14 JUN 15 SYNTHETIC CAFE $100.00",
        "JUN 14 JUN 15 SYNTHETIC CAFE $100.00",
        "LEGAL INFORMATION",
        "IMPORTANT INFORMATION ABOUT THIS SYNTHETIC DOCUMENT",
    ),
)

UNSUPPORTED_PAGES = (
    (
        "TD CANADA TRUST",
        "CREDIT CARD STATEMENT",
        "ACCOUNT NUMBER **** **** **** 4821",
        "STATEMENT PERIOD JUNE 1, 2026 - JUNE 30, 2026",
        "ACTIVITY LIST IN AN UNKNOWN FUTURE LAYOUT",
        "SYNTHETIC CONTENT ONLY",
    ),
)

SCANNED_PLACEHOLDER_PAGES = ((),)


def main() -> None:
    fixtures = {
        "td_full_matrix.pdf": FULL_MATRIX_PAGES,
        "td_unsupported_layout.pdf": UNSUPPORTED_PAGES,
        "td_scanned_placeholder.pdf": SCANNED_PLACEHOLDER_PAGES,
    }
    for filename, pages in fixtures.items():
        (FIXTURE_DIRECTORY / filename).write_bytes(_pdf_bytes(pages))


if __name__ == "__main__":
    main()
