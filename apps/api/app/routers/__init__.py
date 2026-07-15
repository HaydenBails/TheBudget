"""API routers.

Each feature area gets its own module exposing an ``APIRouter``. ``main.py``
includes health, profile, and profile-scoped account routers explicitly. Later
stages add imports, transactions, categories, budgets, and insights following
the same pattern.
"""
