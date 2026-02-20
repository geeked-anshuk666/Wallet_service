import logging

from django.db import transaction
from django.db.models import F

from .exceptions import InsufficientBalanceError, WalletNotFoundError
from .models import AssetType, LedgerEntry, Wallet, WalletTransaction

logger = logging.getLogger(__name__)

TREASURY_ID = '11111111-1111-1111-1111-111111111111'
BONUS_POOL_ID = '22222222-2222-2222-2222-222222222222'
REVENUE_ID = '33333333-3333-3333-3333-333333333333'


def _execute_transfer(source_id: str, dest_id: str, amount: int,
                      asset_type_id: str, idempotency_key: str,
                      tx_type: str, check_source_balance: bool = False):
    """
    Core transfer logic used by topup, bonus, and spend.
    Locks wallets in ascending UUID order to prevent deadlocks.
    """
    with transaction.atomic():
        tx, created = WalletTransaction.objects.get_or_create(
            idempotency_key=idempotency_key,
            defaults={'type': tx_type, 'status': 'COMPLETED'},
        )

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

        wallet_ids = sorted([source_id, dest_id])
        wallets = {
            str(w.id): w
            for w in Wallet.objects.select_for_update().filter(
                id__in=wallet_ids
            ).order_by('id')
        }

        if source_id not in wallets:
            raise WalletNotFoundError(f"source wallet {source_id} not found")
        if dest_id not in wallets:
            raise WalletNotFoundError(f"destination wallet {dest_id} not found")

        source = wallets[source_id]
        dest = wallets[dest_id]

        if check_source_balance and source.balance < amount:
            raise InsufficientBalanceError(current=source.balance, requested=amount)

        asset_type = AssetType.objects.get(id=asset_type_id)

        LedgerEntry.objects.create(
            transaction=tx, wallet=source, asset_type=asset_type,
            direction=LedgerEntry.DEBIT, amount=amount,
        )
        LedgerEntry.objects.create(
            transaction=tx, wallet=dest, asset_type=asset_type,
            direction=LedgerEntry.CREDIT, amount=amount,
        )

        Wallet.objects.filter(id=source_id).update(balance=F('balance') - amount)
        Wallet.objects.filter(id=dest_id).update(balance=F('balance') + amount)

        source.refresh_from_db()
        dest.refresh_from_db()

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


def topup(wallet_id: str, amount: int, asset_type_id: str, idempotency_key: str):
    return _execute_transfer(
        source_id=TREASURY_ID, dest_id=wallet_id,
        amount=amount, asset_type_id=asset_type_id,
        idempotency_key=idempotency_key, tx_type=WalletTransaction.TOPUP,
    )


def bonus(wallet_id: str, amount: int, asset_type_id: str, idempotency_key: str):
    return _execute_transfer(
        source_id=BONUS_POOL_ID, dest_id=wallet_id,
        amount=amount, asset_type_id=asset_type_id,
        idempotency_key=idempotency_key, tx_type=WalletTransaction.BONUS,
    )


def spend(wallet_id: str, amount: int, asset_type_id: str, idempotency_key: str):
    return _execute_transfer(
        source_id=wallet_id, dest_id=REVENUE_ID,
        amount=amount, asset_type_id=asset_type_id,
        idempotency_key=idempotency_key, tx_type=WalletTransaction.SPEND,
        check_source_balance=True,
    )
