"""
urls.py — Wallet App URL Configuration

Maps API endpoints to their view classes. All routes are prefixed with
/api/v1/ by the root URL config (wallet_service/urls.py).

Endpoints:
  POST /api/v1/wallets/<uuid>/topup         → TopupView
  POST /api/v1/wallets/<uuid>/bonus         → BonusView
  POST /api/v1/wallets/<uuid>/spend         → SpendView
  GET  /api/v1/wallets/<uuid>/balance       → BalanceView
  GET  /api/v1/wallets/<uuid>/transactions  → TransactionHistoryView
"""

from django.urls import path

from .views import (
    BalanceView,
    BonusView,
    SpendView,
    TopupView,
    TransactionHistoryView,
)

urlpatterns = [
    # ── Mutation endpoints (require Idempotency-Key header) ───
    path('wallets/<uuid:wallet_id>/topup', TopupView.as_view()),
    path('wallets/<uuid:wallet_id>/bonus', BonusView.as_view()),
    path('wallets/<uuid:wallet_id>/spend', SpendView.as_view()),

    # ── Read endpoints (no auth, higher rate limit) ───────────
    path('wallets/<uuid:wallet_id>/balance', BalanceView.as_view()),
    path('wallets/<uuid:wallet_id>/transactions', TransactionHistoryView.as_view()),
]
