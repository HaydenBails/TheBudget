"""API routers.

Each feature area gets its own module exposing an ``APIRouter``. ``main.py``
includes them explicitly. Stage 0 ships only :mod:`app.routers.health`; later
stages add ``profiles``, ``accounts``, ``imports``, ``transactions``,
``categories``, ``budgets``, and ``insights`` following the same pattern.
"""
