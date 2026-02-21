"""
0002_seed.py — Seed Data Migration

Creates the initial dataset needed for the wallet service to function:
  1. Three asset types (Gold Coins, Diamonds, Loyalty Points)
  2. Five users (3 system users + Alice + Bob)
  3. Five wallets (3 system wallets + 2 user wallets)
  4. Seed transactions: Top-up Alice with 500 GLD, Bob with 200 GLD

All IDs are hardcoded UUIDs so they stay consistent across environments
and can be referenced in tests, documentation, and the seed.sql file.

The unseed() function reverses everything for clean rollback if needed.
"""

import uuid

from django.db import migrations


# ── Hardcoded UUIDs ───────────────────────────────────────────
# Using fixed UUIDs ensures consistency across environments (local, Docker, Render).
# These same values appear in seed.sql, services.py, tests, and the README.

# Asset type IDs
GOLD_COINS_ID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
DIAMONDS_ID = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
LOYALTY_PTS_ID = 'cccccccc-cccc-cccc-cccc-cccccccccccc'

# System wallet IDs (must match services.py TREASURY_ID, BONUS_POOL_ID, REVENUE_ID)
TREASURY_ID = '11111111-1111-1111-1111-111111111111'
BONUS_POOL_ID = '22222222-2222-2222-2222-222222222222'
REVENUE_ID = '33333333-3333-3333-3333-333333333333'

# User wallet IDs (used in tests and the Test Suite config)
ALICE_WALLET_ID = '44444444-4444-4444-4444-444444444444'
BOB_WALLET_ID = '55555555-5555-5555-5555-555555555555'

# Seed transaction IDs (so seed topups are also idempotent)
SEED_TX_ALICE_ID = '66666666-6666-6666-6666-666666666666'
SEED_TX_BOB_ID = '77777777-7777-7777-7777-777777777777'


def seed(apps, schema_editor):
    """Populate the database with initial asset types, users, wallets, and balances."""

    AssetType = apps.get_model('wallets', 'AssetType')
    Wallet = apps.get_model('wallets', 'Wallet')
    WalletTransaction = apps.get_model('wallets', 'WalletTransaction')
    LedgerEntry = apps.get_model('wallets', 'LedgerEntry')
    User = apps.get_model('auth', 'User')

    # ── Step 1: Create asset types ────────────────────────────
    # These define the types of virtual currency available in the system
    gold = AssetType.objects.create(id=GOLD_COINS_ID, name='Gold Coins', symbol='GLD')
    diamonds = AssetType.objects.create(id=DIAMONDS_ID, name='Diamonds', symbol='DIA')
    loyalty = AssetType.objects.create(id=LOYALTY_PTS_ID, name='Loyalty Points', symbol='LPT')

    # ── Step 2: Create users ──────────────────────────────────
    # System users are set to is_active=False because they're internal accounts,
    # not real people who should be able to log in
    sys_treasury = User.objects.create(username='system_treasury', is_active=False)
    sys_bonus = User.objects.create(username='system_bonus', is_active=False)
    sys_revenue = User.objects.create(username='system_revenue', is_active=False)
    alice = User.objects.create(username='alice')
    bob = User.objects.create(username='bob')

    # ── Step 3: Create system wallets ─────────────────────────
    # System wallets are the "other side" of every transaction:
    #   Treasury  → funds source for topups
    #   Bonus Pool → funds source for bonuses
    #   Revenue   → funds sink for spends
    # They have is_system=True so they can go negative (unlimited source of funds)
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

    # ── Step 4: Create user wallets ───────────────────────────
    # Start at 0 balance — their starting balances come from seed transactions below
    alice_wallet = Wallet.objects.create(
        id=ALICE_WALLET_ID, user=alice, asset_type=gold,
        balance=0, is_system=False,
    )
    bob_wallet = Wallet.objects.create(
        id=BOB_WALLET_ID, user=bob, asset_type=gold,
        balance=0, is_system=False,
    )

    # ── Step 5: Seed transactions ─────────────────────────────
    # Create proper TOPUP transactions with double-entry ledger entries
    # so the seed data follows the same rules as normal API usage

    # Alice gets 500 Gold Coins from treasury
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

    # Bob gets 200 Gold Coins from treasury
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

    # ── Step 6: Update wallet balances ────────────────────────
    # Manually set balances to match the seed transactions above
    alice_wallet.balance = 500
    alice_wallet.save(update_fields=['balance'])
    bob_wallet.balance = 200
    bob_wallet.save(update_fields=['balance'])
    treasury_wallet.balance = 10_000_000 - 700  # 9,999,300 after funding both users
    treasury_wallet.save(update_fields=['balance'])


def unseed(apps, schema_editor):
    """Reverse the seed — deletes all seeded data in reverse dependency order."""

    LedgerEntry = apps.get_model('wallets', 'LedgerEntry')
    WalletTransaction = apps.get_model('wallets', 'WalletTransaction')
    Wallet = apps.get_model('wallets', 'Wallet')
    AssetType = apps.get_model('wallets', 'AssetType')
    User = apps.get_model('auth', 'User')

    # Delete in reverse order to respect foreign key constraints
    LedgerEntry.objects.all().delete()
    WalletTransaction.objects.all().delete()
    Wallet.objects.all().delete()
    AssetType.objects.all().delete()
    User.objects.filter(
        username__in=['system_treasury', 'system_bonus', 'system_revenue', 'alice', 'bob']
    ).delete()


class Migration(migrations.Migration):
    """Depends on the initial schema migration and Django's auth module."""

    dependencies = [
        ('wallets', '0001_initial'),
        ('auth', '__first__'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
