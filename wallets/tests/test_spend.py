import pytest
from wallets.models import LedgerEntry, Wallet, WalletTransaction


ALICE_WALLET_ID = '44444444-4444-4444-4444-444444444444'
REVENUE_ID = '33333333-3333-3333-3333-333333333333'
GOLD_COINS_ID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'


@pytest.mark.django_db
class TestSpend:
    def test_spend_success(self, client, seeded_db):
        response = client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/spend',
            data={'amount': 30, 'asset_type_id': GOLD_COINS_ID},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='spend-test-001',
        )
        assert response.status_code == 201
        data = response.json()
        assert data['amount'] == 30
        assert data['direction'] == 'DEBIT'
        assert data['new_balance'] == 470

    def test_spend_credits_revenue(self, client, seeded_db):
        revenue_before = Wallet.objects.get(id=REVENUE_ID).balance
        client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/spend',
            data={'amount': 30, 'asset_type_id': GOLD_COINS_ID},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='spend-test-002',
        )
        revenue_after = Wallet.objects.get(id=REVENUE_ID).balance
        assert revenue_after == revenue_before + 30

    def test_overspend_rejected(self, client, seeded_db):
        response = client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/spend',
            data={'amount': 999999, 'asset_type_id': GOLD_COINS_ID},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='spend-test-overspend',
        )
        assert response.status_code == 422
        data = response.json()
        assert data['error'] == 'INSUFFICIENT_BALANCE'

    def test_overspend_balance_unchanged(self, client, seeded_db):
        balance_before = Wallet.objects.get(id=ALICE_WALLET_ID).balance
        client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/spend',
            data={'amount': 999999, 'asset_type_id': GOLD_COINS_ID},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='spend-test-unchanged',
        )
        balance_after = Wallet.objects.get(id=ALICE_WALLET_ID).balance
        assert balance_after == balance_before

    def test_overspend_no_ledger_entries(self, client, seeded_db):
        entries_before = LedgerEntry.objects.count()
        client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/spend',
            data={'amount': 999999, 'asset_type_id': GOLD_COINS_ID},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='spend-test-no-ledger',
        )
        entries_after = LedgerEntry.objects.count()
        assert entries_after == entries_before

    def test_spend_creates_balanced_ledger(self, client, seeded_db):
        client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/spend',
            data={'amount': 50, 'asset_type_id': GOLD_COINS_ID},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='spend-test-ledger',
        )
        tx = WalletTransaction.objects.get(idempotency_key='spend-test-ledger')
        entries = LedgerEntry.objects.filter(transaction=tx)
        assert entries.count() == 2

        debit = entries.get(direction='DEBIT')
        credit = entries.get(direction='CREDIT')
        assert debit.amount == credit.amount == 50
        assert str(debit.wallet_id) == ALICE_WALLET_ID
        assert str(credit.wallet_id) == REVENUE_ID
