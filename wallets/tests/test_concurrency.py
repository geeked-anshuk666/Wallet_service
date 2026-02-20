import threading
import uuid

import pytest

from wallets.models import Wallet
from wallets.services import spend


ALICE_WALLET_ID = '44444444-4444-4444-4444-444444444444'
GOLD_COINS_ID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'


@pytest.mark.django_db(transaction=True)
class TestConcurrency:
    def test_concurrent_spends_correct_balance(self, seeded_db):
        """20 concurrent spends of 10 each on Alice's 500 balance.
        All 20 should succeed, final balance should be 300."""
        results = []

        def do_spend():
            try:
                r = spend(ALICE_WALLET_ID, 10, GOLD_COINS_ID, str(uuid.uuid4()))
                results.append(('ok', r))
            except Exception as e:
                results.append(('err', e))

        threads = [threading.Thread(target=do_spend) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        alice = Wallet.objects.get(id=ALICE_WALLET_ID)
        assert alice.balance == 300
        assert len([r for r in results if r[0] == 'ok']) == 20

    def test_concurrent_overspend_prevents_negative(self, seeded_db):
        """50 concurrent spends of 100 each on Alice's 500 balance.
        Only 5 should succeed, rest should fail with InsufficientBalanceError."""
        results = []

        def do_spend():
            try:
                r = spend(ALICE_WALLET_ID, 100, GOLD_COINS_ID, str(uuid.uuid4()))
                results.append(('ok', r))
            except Exception as e:
                results.append(('err', e))

        threads = [threading.Thread(target=do_spend) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        alice = Wallet.objects.get(id=ALICE_WALLET_ID)
        assert alice.balance == 0
        successes = [r for r in results if r[0] == 'ok']
        assert len(successes) == 5
