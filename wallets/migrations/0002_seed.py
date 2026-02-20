"""
Seed data migration — creates asset types, system users, wallets,
and initial balances for Alice and Bob.
"""
import uuid

from django.db import migrations

GOLD_COINS_ID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
DIAMONDS_ID = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
LOYALTY_PTS_ID = 'cccccccc-cccc-cccc-cccc-cccccccccccc'

TREASURY_ID = '11111111-1111-1111-1111-111111111111'
BONUS_POOL_ID = '22222222-2222-2222-2222-222222222222'
REVENUE_ID = '33333333-3333-3333-3333-333333333333'
ALICE_WALLET_ID = '44444444-4444-4444-4444-444444444444'
BOB_WALLET_ID = '55555555-5555-5555-5555-555555555555'

SEED_TX_ALICE_ID = '66666666-6666-6666-6666-666666666666'
SEED_TX_BOB_ID = '77777777-7777-7777-7777-777777777777'


def seed(apps, schema_editor):
    AssetType = apps.get_model('wallets', 'AssetType')
    Wallet = apps.get_model('wallets', 'Wallet')
    WalletTransaction = apps.get_model('wallets', 'WalletTransaction')
    LedgerEntry = apps.get_model('wallets', 'LedgerEntry')
    User = apps.get_model('auth', 'User')

    # 1. Asset types
    gold = AssetType.objects.create(id=GOLD_COINS_ID, name='Gold Coins', symbol='GLD')
    diamonds = AssetType.objects.create(id=DIAMONDS_ID, name='Diamonds', symbol='DIA')
    loyalty = AssetType.objects.create(id=LOYALTY_PTS_ID, name='Loyalty Points', symbol='LPT')

    # 2. Users
    sys_treasury = User.objects.create(username='system_treasury', is_active=False)
    sys_bonus = User.objects.create(username='system_bonus', is_active=False)
    sys_revenue = User.objects.create(username='system_revenue', is_active=False)
    alice = User.objects.create(username='alice')
    bob = User.objects.create(username='bob')

    # 3. System wallets (can hold negative balances via is_system=True)
    treasury_wallet = Wallet.objects.create(
        id=TREASURY_ID, user=sys_treasury, asset_type=gold,
        balance=10_000_000, is_system=True,
    )
    bonus_wallet = Wallet.objects.create(
        id=BONUS_POOL_ID, user=sys_bonus, asset_type=gold,
        balance=5_000_000, is_system=True,
    )
    revenue_wallet = Wallet.objects.create(
        id=REVENUE_ID, user=sys_revenue, asset_type=gold,
        balance=0, is_system=True,
    )

    # 4. User wallets (start at 0, then seed via transactions)
    alice_wallet = Wallet.objects.create(
        id=ALICE_WALLET_ID, user=alice, asset_type=gold,
        balance=0, is_system=False,
    )
    bob_wallet = Wallet.objects.create(
        id=BOB_WALLET_ID, user=bob, asset_type=gold,
        balance=0, is_system=False,
    )

    # 5. Seed transactions: TOPUP Alice 500, TOPUP Bob 200
    tx_alice = WalletTransaction.objects.create(
        id=SEED_TX_ALICE_ID, type='TOPUP',
        idempotency_key='seed-alice-topup-500', status='COMPLETED',
    )
    LedgerEntry.objects.create(
        transaction=tx_alice, wallet=treasury_wallet,
        asset_type=gold, direction='DEBIT', amount=500,
    )
    LedgerEntry.objects.create(
        transaction=tx_alice, wallet=alice_wallet,
        asset_type=gold, direction='CREDIT', amount=500,
    )

    tx_bob = WalletTransaction.objects.create(
        id=SEED_TX_BOB_ID, type='TOPUP',
        idempotency_key='seed-bob-topup-200', status='COMPLETED',
    )
    LedgerEntry.objects.create(
        transaction=tx_bob, wallet=treasury_wallet,
        asset_type=gold, direction='DEBIT', amount=200,
    )
    LedgerEntry.objects.create(
        transaction=tx_bob, wallet=bob_wallet,
        asset_type=gold, direction='CREDIT', amount=200,
    )

    # 6. Update balances to reflect seed transactions
    alice_wallet.balance = 500
    alice_wallet.save(update_fields=['balance'])
    bob_wallet.balance = 200
    bob_wallet.save(update_fields=['balance'])
    treasury_wallet.balance = 10_000_000 - 700  # 9,999,300
    treasury_wallet.save(update_fields=['balance'])


def unseed(apps, schema_editor):
    """Reverse seed — delete in reverse dependency order."""
    LedgerEntry = apps.get_model('wallets', 'LedgerEntry')
    WalletTransaction = apps.get_model('wallets', 'WalletTransaction')
    Wallet = apps.get_model('wallets', 'Wallet')
    AssetType = apps.get_model('wallets', 'AssetType')
    User = apps.get_model('auth', 'User')

    LedgerEntry.objects.all().delete()
    WalletTransaction.objects.all().delete()
    Wallet.objects.all().delete()
    AssetType.objects.all().delete()
    User.objects.filter(
        username__in=['system_treasury', 'system_bonus', 'system_revenue', 'alice', 'bob']
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('wallets', '0001_initial'),
        ('auth', '__first__'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
