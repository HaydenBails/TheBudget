# Statement fixtures

Test fixtures for the statement parsers. **Privacy policy (product plan §22.1):**

## Rules

1. **Never commit real or unredacted statements.** No real account numbers, real
   names, real addresses, or real transaction histories — ever. This applies to
   PDFs, extracted text, and canonical JSON alike.
2. **Prefer synthetic fixtures.** Generate statements with fabricated but
   realistic data that exercises the parser (multiple issuers, date formats,
   purchases, payments, refunds, cash advances, interest, fees, multi-page,
   edge cases). If a real statement must be used to reproduce a bug, it must be
   fully **redacted** first and reduced to the minimum needed.
3. **Keep expected canonical JSON per fixture.** Each input statement is paired
   with the expected normalized output (canonical transaction JSON) so parser
   tests assert against a known-good result. Regenerate expected JSON only via a
   reviewed change.

## Layout (convention)

```
fixtures/statements/
  <issuer>/
    <fixture-name>.pdf          # synthetic/redacted input statement
    <fixture-name>.expected.json # canonical normalized transactions
```

Amounts in canonical JSON are **integer cents** (see
[`docs/decisions/0003-money-and-accounting.md`](../../docs/decisions/0003-money-and-accounting.md)).
No fixtures exist yet — parsers arrive in a later stage; see
[`docs/parser-notes/README.md`](../../docs/parser-notes/README.md).
