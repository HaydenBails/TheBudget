"""Generic, brand-level merchant → category seed rules.

These are well-known merchants mapped to the default categories, shipped so a
new profile auto-categorizes common charges out of the box. They are curated
for precision (distinctive brand tokens only) — the user's own history teaches
the long tail via learned rules. Never seed anything derived from a specific
user's private statement here.

Each entry is (keyword, default-category slug). Matching is case-insensitive
"contains" against the normalized merchant/description text.
"""

from __future__ import annotations

# (keyword, category slug)
DEFAULT_MERCHANT_RULES: tuple[tuple[str, str], ...] = (
    # Dining & takeaway
    ("UBEREATS", "dining"),
    ("UBER EATS", "dining"),
    ("DOORDASH", "dining"),
    ("SKIPTHEDISHES", "dining"),
    ("TIM HORTONS", "dining"),
    ("STARBUCKS", "dining"),
    ("MCDONALD", "dining"),
    ("DOMINOS", "dining"),
    ("CHICK FIL A", "dining"),
    ("SUBWAY", "dining"),
    ("KRISPY KREME", "dining"),
    ("BASKIN ROBBINS", "dining"),
    ("POPEYES", "dining"),
    ("WENDYS", "dining"),
    ("BURGER KING", "dining"),
    ("DAIRY QUEEN", "dining"),
    ("PITA PIT", "dining"),
    # Transport & fuel
    ("UBERTRIP", "transport"),
    ("UBERONE", "transport"),
    ("LYFT", "transport"),
    ("PRESTO", "transport"),
    ("PETRO CANADA", "transport"),
    ("ESSO", "transport"),
    ("SHELL", "transport"),
    ("CIRCLE K", "transport"),
    ("ONROUTE", "transport"),
    ("MEGABUS", "transport"),
    ("COACH CANADA", "transport"),
    ("GO TRANSIT", "transport"),
    # Groceries & household
    ("METRO", "groceries"),
    ("FOOD BASICS", "groceries"),
    ("FORTINO", "groceries"),
    ("LOBLAWS", "groceries"),
    ("NO FRILLS", "groceries"),
    ("COSTCO", "groceries"),
    ("BULK BARN", "groceries"),
    ("DOLLARAMA", "groceries"),
    ("WALMART", "groceries"),
    ("SOBEYS", "groceries"),
    ("FRESHCO", "groceries"),
    ("SUPERSTORE", "groceries"),
    ("FARM BOY", "groceries"),
    # Health
    ("SHOPPERS DRUG MART", "health"),
    ("DRUGSMART", "health"),
    ("ANYTIME FITNESS", "health"),
    ("GOODLIFE", "health"),
    ("OURARING", "health"),
    # Shopping
    ("AMAZON", "shopping"),
    ("ZARA", "shopping"),
    ("ADIDAS", "shopping"),
    ("NIKE", "shopping"),
    ("SHEIN", "shopping"),
    ("LEGO", "shopping"),
    ("ROOTS", "shopping"),
    ("BEST BUY", "shopping"),
    ("IKEA", "shopping"),
    ("INDIGO", "shopping"),
    ("WINNERS", "shopping"),
    # Entertainment & subscriptions
    ("SPOTIFY", "entertainment"),
    ("NETFLIX", "entertainment"),
    ("DISNEY", "entertainment"),
    ("STEAMGAMES", "entertainment"),
    ("CINEPLEX", "entertainment"),
    ("OPENAI", "entertainment"),
    ("CHATGPT", "entertainment"),
    ("APPLE COM BILL", "entertainment"),
    # Fees & interest
    ("INTEREST CHARGE", "fees"),
    ("CASH ADVANCE FEE", "fees"),
    ("ANNUAL FEE", "fees"),
    ("MEMBERSHIP FEE", "fees"),
)
