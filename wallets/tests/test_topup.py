import pytest
from wallets.models import LedgerEntry, Wallet, WalletTransaction


ALICE_WALLET_ID = '44444444-4444-4444-4444-444444444444'
TREASURY_ID = '11111111-1111-1111-1111-111111111111'
GOLD_COINS_ID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'


@pytest.mark.django_db
class TestTopup:
    def test_topup_success(self, client, seeded_db):
        response = client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/topup',
            data={'amount': 100, 'asset_type_id': GOLD_COINS_ID},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='topup-test-001',
        )
        assert response.status_code == 201
        data = response.json()
        assert data['amount'] == 100
        assert data['direction'] == 'CREDIT'
        assert data['new_balance'] == 600

    def test_topup_updates_balance(self, client, seeded_db):
        client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/topup',
            data={'amount': 250, 'asset_type_id': GOLD_COINS_ID},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='topup-test-002',
        )
        wallet = Wallet.objects.get(id=ALICE_WALLET_ID)
        assert wallet.balance == 750

    def test_topup_creates_balanced_ledger(self, client, seeded_db):
        client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/topup',
            data={'amount': 100, 'asset_type_id': GOLD_COINS_ID},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='topup-test-003',
        )
        tx = WalletTransaction.objects.get(idempotency_key='topup-test-003')
        entries = LedgerEntry.objects.filter(transaction=tx)
        assert entries.count() == 2

        debit = entries.get(direction='DEBIT')
        credit = entries.get(direction='CREDIT')
        assert debit.amount == credit.amount == 100
        assert str(debit.wallet_id) == TREASURY_ID
        assert str(credit.wallet_id) == ALICE_WALLET_ID

    def test_topup_debits_treasury(self, client, seeded_db):
        treasury_before = Wallet.objects.get(id=TREASURY_ID).balance
        client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/topup',
            data={'amount': 100, 'asset_type_id': GOLD_COINS_ID},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='topup-test-004',
        )
        treasury_after = Wallet.objects.get(id=TREASURY_ID).balance
        assert treasury_after == treasury_before - 100

    def test_topup_missing_idempotency_key(self, client, seeded_db):
        response = client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/topup',
            data={'amount': 100, 'asset_type_id': GOLD_COINS_ID},
            content_type='application/json',
        )
        assert response.status_code == 400

    def test_topup_invalid_amount(self, client, seeded_db):
        response = client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/topup',
            data={'amount': -50, 'asset_type_id': GOLD_COINS_ID},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='topup-test-neg',
        )
        assert response.status_code == 400
