from pathlib import Path
import sqlite3

from app.importing import stage_pdf

def main() -> None:
    root = Path(__file__).resolve().parents[2]
    fixture = root / "fixtures/statements/td/td_full_matrix.pdf"
    database = root / "output/qa04-real/spending_tracker.db"
    temp_root = root / "output/qa04-real/temp"

    with fixture.open("rb") as stream:
        with stage_pdf(
            stream,
            filename=fixture.name,
            content_type="application/pdf",
            temp_root=temp_root,
        ) as document:
            page_texts = [
                (page if isinstance(page, str) else page.text).encode("utf-8")
                for page in document.pages
            ]

    database_bytes = database.read_bytes()
    connection = sqlite3.connect(database)
    tables = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    ]
    columns = {
        table: [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
        for table in tables
    }
    suspicious_columns = [
        (table, column)
        for table, names in columns.items()
        for column in names
        if any(
            marker in column.lower()
            for marker in (
                "pdf_bytes",
                "raw_pdf",
                "extracted_text",
                "page_text",
                "full_text",
            )
        )
    ]

    print("db_bytes", len(database_bytes))
    print("raw_pdf_magic_present", b"%PDF-" in database_bytes)
    print(
        "full_page_text_matches",
        sum(bool(text) and text in database_bytes for text in page_texts),
        "of",
        len(page_texts),
    )
    print("suspicious_payload_columns", suspicious_columns)
    print("temp_files", [str(path) for path in temp_root.rglob("*")])
    print(
        "transactions",
        connection.execute("SELECT count(*) FROM transactions").fetchone()[0],
    )
    print(
        "imports",
        connection.execute(
            "SELECT id, status, duplicate_decision FROM import_batches ORDER BY id"
        ).fetchall(),
    )
    connection.close()


if __name__ == "__main__":
    main()
