import pytest
from wallets.models import AuditLog


ALICE_WALLET_ID = '44444444-4444-4444-4444-444444444444'
GOLD_COINS_ID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'


@pytest.mark.django_db
class TestRateLimit:
    def test_spend_rate_limit(self, client, seeded_db):
        """61 spend requests from the same IP — first 60 should pass, 61st should be 429."""
        responses = []
        for i in range(61):
            r = client.post(
                f'/api/v1/wallets/{ALICE_WALLET_ID}/spend',
                data={'amount': 1, 'asset_type_id': GOLD_COINS_ID},
                content_type='application/json',
                HTTP_IDEMPOTENCY_KEY=f'rate-limit-test-{i}',
                REMOTE_ADDR='1.2.3.4',
            )
            responses.append(r.status_code)

        assert responses[-1] == 429
        assert responses.count(429) == 1

    def test_rate_limit_creates_audit_log(self, client, seeded_db):
        """The 429 response must produce an audit log entry."""
        for i in range(61):
            client.post(
                f'/api/v1/wallets/{ALICE_WALLET_ID}/spend',
                data={'amount': 1, 'asset_type_id': GOLD_COINS_ID},
                content_type='application/json',
                HTTP_IDEMPOTENCY_KEY=f'rate-audit-test-{i}',
                REMOTE_ADDR='1.2.3.4',
            )

        assert AuditLog.objects.filter(response_status=429).exists()
        log = AuditLog.objects.filter(response_status=429).first()
        assert log.status == AuditLog.FAILED
        assert log.error_message == 'rate limit exceeded'

    def test_topup_rate_limit(self, client, seeded_db):
        """Topup has its own rate limit group — separate counter."""
        responses = []
        for i in range(61):
            r = client.post(
                f'/api/v1/wallets/{ALICE_WALLET_ID}/topup',
                data={'amount': 1, 'asset_type_id': GOLD_COINS_ID},
                content_type='application/json',
                HTTP_IDEMPOTENCY_KEY=f'rate-topup-test-{i}',
                REMOTE_ADDR='1.2.3.4',
            )
            responses.append(r.status_code)

        assert responses[-1] == 429

    def test_balance_rate_limit(self, client, seeded_db):
        """Balance read has 200/m limit — 201 requests should trigger 429."""
        responses = []
        for i in range(201):
            r = client.get(
                f'/api/v1/wallets/{ALICE_WALLET_ID}/balance',
                REMOTE_ADDR='1.2.3.4',
            )
            responses.append(r.status_code)

        assert responses[-1] == 429
