"""Shared test fixtures for the wallet service test suite."""
import pytest
from django.contrib.auth.models import User

from wallets.models import AssetType, Wallet


GOLD_COINS_ID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
TREASURY_ID = '11111111-1111-1111-1111-111111111111'
BONUS_POOL_ID = '22222222-2222-2222-2222-222222222222'
REVENUE_ID = '33333333-3333-3333-3333-333333333333'
ALICE_WALLET_ID = '44444444-4444-4444-4444-444444444444'
BOB_WALLET_ID = '55555555-5555-5555-5555-555555555555'


@pytest.fixture
def seeded_db(db):
    """Run the seed migration data manually for test isolation."""
    gold = AssetType.objects.create(id=GOLD_COINS_ID, name='Gold Coins', symbol='GLD')

    sys_treasury = User.objects.create(username='system_treasury', is_active=False)
    sys_bonus = User.objects.create(username='system_bonus', is_active=False)
    sys_revenue = User.objects.create(username='system_revenue', is_active=False)
    alice = User.objects.create(username='alice')
    bob = User.objects.create(username='bob')

    Wallet.objects.create(
        id=TREASURY_ID, user=sys_treasury, asset_type=gold,
        balance=10_000_000, is_system=True,
    )
    Wallet.objects.create(
        id=BONUS_POOL_ID, user=sys_bonus, asset_type=gold,
        balance=5_000_000, is_system=True,
    )
    Wallet.objects.create(
        id=REVENUE_ID, user=sys_revenue, asset_type=gold,
        balance=0, is_system=True,
    )
    Wallet.objects.create(
        id=ALICE_WALLET_ID, user=alice, asset_type=gold,
        balance=500, is_system=False,
    )
    Wallet.objects.create(
        id=BOB_WALLET_ID, user=bob, asset_type=gold,
        balance=200, is_system=False,
    )
    return {
        'gold': gold,
        'alice_wallet': Wallet.objects.get(id=ALICE_WALLET_ID),
        'bob_wallet': Wallet.objects.get(id=BOB_WALLET_ID),
    }
