import pytest
from wallets.models import LedgerEntry, Wallet, WalletTransaction


ALICE_WALLET_ID = '44444444-4444-4444-4444-444444444444'
BONUS_POOL_ID = '22222222-2222-2222-2222-222222222222'
GOLD_COINS_ID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'


@pytest.mark.django_db
class TestBonus:
    def test_bonus_success(self, client, seeded_db):
        response = client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/bonus',
            data={'amount': 50, 'asset_type_id': GOLD_COINS_ID},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='bonus-test-001',
        )
        assert response.status_code == 201
        data = response.json()
        assert data['amount'] == 50
        assert data['direction'] == 'CREDIT'
        assert data['new_balance'] == 550

    def test_bonus_debits_bonus_pool(self, client, seeded_db):
        pool_before = Wallet.objects.get(id=BONUS_POOL_ID).balance
        client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/bonus',
            data={'amount': 50, 'asset_type_id': GOLD_COINS_ID},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='bonus-test-002',
        )
        pool_after = Wallet.objects.get(id=BONUS_POOL_ID).balance
        assert pool_after == pool_before - 50

    def test_bonus_creates_balanced_ledger(self, client, seeded_db):
        client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/bonus',
            data={'amount': 75, 'asset_type_id': GOLD_COINS_ID},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='bonus-test-003',
        )
        tx = WalletTransaction.objects.get(idempotency_key='bonus-test-003')
        entries = LedgerEntry.objects.filter(transaction=tx)
        assert entries.count() == 2

        debit = entries.get(direction='DEBIT')
        credit = entries.get(direction='CREDIT')
        assert debit.amount == credit.amount == 75
        assert str(debit.wallet_id) == BONUS_POOL_ID
        assert str(credit.wallet_id) == ALICE_WALLET_ID
