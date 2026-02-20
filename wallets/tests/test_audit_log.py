import pytest
from wallets.models import AuditLog


ALICE_WALLET_ID = '44444444-4444-4444-4444-444444444444'
GOLD_COINS_ID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'


@pytest.mark.django_db
class TestAuditLog:
    def test_successful_topup_creates_audit_log(self, client, seeded_db):
        client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/topup',
            data={'amount': 100, 'asset_type_id': GOLD_COINS_ID},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='audit-topup-001',
        )
        log = AuditLog.objects.get(action=AuditLog.TOPUP)
        assert log.status == AuditLog.SUCCESS
        assert log.response_status == 201
        assert str(log.wallet_id) == ALICE_WALLET_ID

    def test_failed_overspend_creates_audit_log(self, client, seeded_db):
        client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/spend',
            data={'amount': 999999, 'asset_type_id': GOLD_COINS_ID},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='audit-overspend-001',
        )
        log = AuditLog.objects.get(action=AuditLog.SPEND)
        assert log.status == AuditLog.FAILED
        assert log.response_status == 422
        assert log.error_message is not None

    def test_missing_header_creates_audit_log(self, client, seeded_db):
        client.post(
            f'/api/v1/wallets/{ALICE_WALLET_ID}/topup',
            data={'amount': 100, 'asset_type_id': GOLD_COINS_ID},
            content_type='application/json',
        )
        log = AuditLog.objects.get(action=AuditLog.TOPUP)
        assert log.status == AuditLog.FAILED
        assert log.response_status == 400

    def test_balance_read_creates_audit_log(self, client, seeded_db):
        client.get(f'/api/v1/wallets/{ALICE_WALLET_ID}/balance')
        log = AuditLog.objects.get(action=AuditLog.BALANCE_READ)
        assert log.status == AuditLog.SUCCESS
        assert log.response_status == 200

    def test_health_check_creates_audit_log(self, client, seeded_db):
        client.get('/health')
        log = AuditLog.objects.get(action=AuditLog.HEALTH_CHECK)
        assert log.status == AuditLog.SUCCESS
        assert log.response_status == 200

    def test_transaction_history_creates_audit_log(self, client, seeded_db):
        client.get(f'/api/v1/wallets/{ALICE_WALLET_ID}/transactions')
        log = AuditLog.objects.get(action=AuditLog.TRANSACTION_HISTORY)
        assert log.status == AuditLog.SUCCESS
        assert log.response_status == 200
