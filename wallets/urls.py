from django.urls import path

from .views import (
    BalanceView,
    BonusView,
    SpendView,
    TopupView,
    TransactionHistoryView,
)

urlpatterns = [
    path('wallets/<uuid:wallet_id>/topup', TopupView.as_view()),
    path('wallets/<uuid:wallet_id>/bonus', BonusView.as_view()),
    path('wallets/<uuid:wallet_id>/spend', SpendView.as_view()),
    path('wallets/<uuid:wallet_id>/balance', BalanceView.as_view()),
    path('wallets/<uuid:wallet_id>/transactions', TransactionHistoryView.as_view()),
]
