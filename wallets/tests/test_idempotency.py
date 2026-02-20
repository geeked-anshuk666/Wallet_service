import pytest
from wallets.models import WalletTransaction


ALICE_WALLET_ID = '44444444-4444-4444-4444-444444444444'
GOLD_COINS_ID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'


@pytest.mark.django_db
class TestIdempotency:
    def test_duplicate_topup_returns_replayed(self, client, seeded_db):
        payload = {'amount': 100, 'asset_type_id': GOLD_COINS_ID}
        key = 'idempotency-test-001'

        r1 = client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/topup',
            data=payload, content_type='application/json',
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert r1.status_code == 201

        r2 = client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/topup',
            data=payload, content_type='application/json',
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert r2.status_code == 200
        assert r2.json()['replayed'] is True

    def test_duplicate_does_not_create_extra_transaction(self, client, seeded_db):
        payload = {'amount': 50, 'asset_type_id': GOLD_COINS_ID}
        key = 'idempotency-test-002'

        client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/topup',
            data=payload, content_type='application/json',
            HTTP_IDEMPOTENCY_KEY=key,
        )
        client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/topup',
            data=payload, content_type='application/json',
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert WalletTransaction.objects.filter(idempotency_key=key).count() == 1

    def test_duplicate_spend_returns_replayed(self, client, seeded_db):
        payload = {'amount': 10, 'asset_type_id': GOLD_COINS_ID}
        key = 'idempotency-spend-001'

        r1 = client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/spend',
            data=payload, content_type='application/json',
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert r1.status_code == 201

        r2 = client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/spend',
            data=payload, content_type='application/json',
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert r2.status_code == 200
        assert r2.json()['replayed'] is True
