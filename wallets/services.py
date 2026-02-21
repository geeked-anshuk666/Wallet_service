"""
services.py — Core Business Logic for Wallet Mutations

All wallet mutations (topup, bonus, spend) flow through a single function:
_execute_transfer(). This ensures consistent behavior for:
  - Atomic transactions (all-or-nothing via transaction.atomic)
  - Idempotency (duplicate requests return the original result)
  - Concurrency safety (row-level locking via SELECT FOR UPDATE)
  - Double-entry ledger (every mutation creates a balanced debit + credit pair)

The three public functions (topup, bonus, spend) are thin wrappers that
plug in the correct source/destination wallets and transaction type.
"""

import logging

from django.db import transaction
from django.db.models import F

from .exceptions import InsufficientBalanceError, WalletNotFoundError
from .models import AssetType, LedgerEntry, Wallet, WalletTransaction

logger = logging.getLogger(__name__)

# ── System Wallet IDs ─────────────────────────────────────────
# These are the hardcoded UUIDs for the three system wallets created by the seed migration.
# They act as the "other side" of every user-facing transaction:
#   - TREASURY:   funds come from here during topups
#   - BONUS_POOL: funds come from here during bonuses
#   - REVENUE:    funds go here when a user spends

TREASURY_ID = '11111111-1111-1111-1111-111111111111'
BONUS_POOL_ID = '22222222-2222-2222-2222-222222222222'
REVENUE_ID = '33333333-3333-3333-3333-333333333333'


def _execute_transfer(source_id: str, dest_id: str, amount: int,
                      asset_type_id: str, idempotency_key: str,
                      tx_type: str, check_source_balance: bool = False):
    """
    Core transfer logic used by topup, bonus, and spend.

    Wraps the entire operation in a database transaction. If anything fails,
    PostgreSQL rolls back everything — no partial state, ever.
    """

    with transaction.atomic():

        # ── Step 1: Idempotency Check ─────────────────────────
        # Try to create a new transaction record with this key.
        # If it already exists (created=False), this is a replay — return the original result.
        tx, created = WalletTransaction.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults={'type': tx_type, 'status': 'COMPLETED'},
        )

        # If the key already existed, this is a duplicate request.
        # Return the original response without modifying any balances.
        if not created:
            source = Wallet.objects.get(id=source_id)
            dest = Wallet.objects.get(id=dest_id)
            replay_wallet = dest if tx_type in (WalletTransaction.TOPUP, WalletTransaction.BONUS) else source
            asset_type = AssetType.objects.get(id=asset_type_id)
            return {
                'transaction_id': str(tx.id),
                'replayed': True,
                'wallet_id': str(replay_wallet.id),
                'asset_type': asset_type.name,
                'amount': amount,
                'direction': 'CREDIT' if tx_type != WalletTransaction.SPEND else 'DEBIT',
                'new_balance': replay_wallet.balance,
                'created_at': tx.created_at.isoformat(),
            }

        # ── Step 2: Lock Wallets ──────────────────────────────
        # Acquire row-level locks on BOTH wallets using SELECT FOR UPDATE.
        # Critical: sort by UUID so we always lock in the same order.
        # This prevents deadlocks when two concurrent transactions involve the same wallets.
        wallet_ids = sorted([source_id, dest_id])
        wallets = {
            str(w.id): w
            for w in Wallet.objects.select_for_update().filter(
                id__in=wallet_ids
            ).order_by('id')
        }

        # Verify both wallets exist before proceeding
        if source_id not in wallets:
            raise WalletNotFoundError(f"source wallet {source_id} not found")
        if dest_id not in wallets:
            raise WalletNotFoundError(f"destination wallet {dest_id} not found")

        source = wallets[source_id]
        dest = wallets[dest_id]

        # ── Step 3: Balance Guard ─────────────────────────────
        # For spend operations, check that the user has enough funds.
        # Topups and bonuses skip this because the source is a system wallet.
        if check_source_balance and source.balance < amount:
            raise InsufficientBalanceError(current=source.balance, requested=amount)

        asset_type = AssetType.objects.get(id=asset_type_id)

        # ── Step 4: Create Double-Entry Ledger Records ────────
        # Every transaction creates exactly 2 entries:
        #   - DEBIT on the source wallet (money leaves)
        #   - CREDIT on the destination wallet (money arrives)
        # The sum of all ledger entries across all wallets is always zero.
        LedgerEntry.objects.create(
            transaction=tx, wallet=source, asset_type=asset_type,
            direction=LedgerEntry.DEBIT, amount=amount,
        )
        LedgerEntry.objects.create(
            transaction=tx, wallet=dest, asset_type=asset_type,
            direction=LedgerEntry.CREDIT, amount=amount,
        )

        # ── Step 5: Update Balances ───────────────────────────
        # Use F() expressions for atomic DB-level arithmetic.
        # This avoids read-modify-write race conditions at the Python level.
        Wallet.objects.filter(id=source_id).update(balance=F('balance') - amount)
        Wallet.objects.filter(id=dest_id).update(balance=F('balance') + amount)

        # Refresh from DB to get the updated balances for the response
        source.refresh_from_db()
        dest.refresh_from_db()

        # ── Step 6: Build Response ────────────────────────────
        # For topup/bonus → show the user's wallet (destination)
        # For spend → show the user's wallet (source)
        response_wallet = dest if tx_type != WalletTransaction.SPEND else source
        direction = 'CREDIT' if tx_type != WalletTransaction.SPEND else 'DEBIT'

        return {
            'transaction_id': str(tx.id),
            'wallet_id': str(response_wallet.id),
            'asset_type': asset_type.name,
            'amount': amount,
            'direction': direction,
            'new_balance': response_wallet.balance,
            'created_at': tx.created_at.isoformat(),
        }


# ── Public API ────────────────────────────────────────────────
# These three functions are the public interface to the service layer.
# Each one routes to _execute_transfer with the correct source/dest wallets.

def topup(wallet_id: str, amount: int, asset_type_id: str, idempotency_key: str):
    """Credit a user's wallet with funds from the treasury (real-money purchase)."""
    return _execute_transfer(
        source_id=TREASURY_ID, dest_id=wallet_id,
        amount=amount, asset_type_id=asset_type_id,
        idempotency_key=idempotency_key, tx_type=WalletTransaction.TOPUP,
    )


def bonus(wallet_id: str, amount: int, asset_type_id: str, idempotency_key: str):
    """Credit a user's wallet with funds from the bonus pool (promotional reward)."""
    return _execute_transfer(
        source_id=BONUS_POOL_ID, dest_id=wallet_id,
        amount=amount, asset_type_id=asset_type_id,
        idempotency_key=idempotency_key, tx_type=WalletTransaction.BONUS,
    )


def spend(wallet_id: str, amount: int, asset_type_id: str, idempotency_key: str):
    """Debit a user's wallet and credit revenue (in-app purchase). Rejects if insufficient balance."""
    return _execute_transfer(
        source_id=wallet_id, dest_id=REVENUE_ID,
        amount=amount, asset_type_id=asset_type_id,
        idempotency_key=idempotency_key, tx_type=WalletTransaction.SPEND,
        check_source_balance=True,  # only spend checks the user's balance
    )
