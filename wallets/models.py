"""
models.py — Database Models for the Wallet Service

Defines the five core tables:
  - AssetType:          Types of virtual currency (e.g., Gold Coins)
  - Wallet:             A user's balance container for a specific asset type
  - WalletTransaction:  An immutable record of a mutation (topup/bonus/spend)
  - LedgerEntry:        Double-entry bookkeeping — every transaction creates a debit + credit pair
  - AuditLog:           Append-only log of every API request for compliance and debugging
"""

import uuid

from django.db import models


# ── Asset Type ────────────────────────────────────────────────
# Represents a type of virtual currency in the system.
# Each asset type has a unique name and trading symbol (e.g., "Gold Coins" / "GLD").

class AssetType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    symbol = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ── Wallet ────────────────────────────────────────────────────
# Holds the balance of a single asset type for a single user.
# System wallets (treasury, bonus pool, revenue) have is_system=True
# and are allowed to go negative — normal user wallets cannot.

class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # PROTECT prevents accidental deletion of users/asset types that have wallets
    user = models.ForeignKey('auth.User', on_delete=models.PROTECT, related_name='wallets')
    asset_type = models.ForeignKey(AssetType, on_delete=models.PROTECT)

    # Balance stored as integer (minor units) to avoid floating point issues
    balance = models.BigIntegerField(default=0)

    # System wallets (treasury, bonus pool, revenue) are exempt from the non-negative balance check
    is_system = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Each user can have at most one wallet per asset type
        unique_together = [('user', 'asset_type')]

        constraints = [
            # DB-level guard: user wallets can never go negative.
            # System wallets (treasury etc.) are exempt because they're the "source of funds".
            models.CheckConstraint(
                check=models.Q(balance__gte=0) | models.Q(is_system=True),
                name='chk_balance_non_negative',
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.asset_type.name}"


# ── Wallet Transaction ───────────────────────────────────────
# An immutable record of a single mutation (topup, bonus, or spend).
# The idempotency_key (unique) is what prevents duplicate processing —
# if the same key is sent twice, the second request returns the original result.

class WalletTransaction(models.Model):
    TOPUP = 'TOPUP'
    BONUS = 'BONUS'
    SPEND = 'SPEND'
    TYPE_CHOICES = [(TOPUP, 'Top-up'), (BONUS, 'Bonus'), (SPEND, 'Spend')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    # Unique constraint on this field is what makes idempotency work.
    # get_or_create() in services.py checks this before processing.
    idempotency_key = models.CharField(max_length=255, unique=True)

    status = models.CharField(max_length=20, default='COMPLETED')
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} - {self.idempotency_key}"


# ── Ledger Entry ──────────────────────────────────────────────
# Double-entry bookkeeping: every transaction produces exactly 2 entries —
# a DEBIT on the source wallet and a CREDIT on the destination wallet.
# The sum of all entries across all wallets should always be zero.

class LedgerEntry(models.Model):
    DEBIT = 'DEBIT'
    CREDIT = 'CREDIT'
    DIRECTION_CHOICES = [(DEBIT, 'Debit'), (CREDIT, 'Credit')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(WalletTransaction, on_delete=models.PROTECT, related_name='entries')
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='ledger_entries')
    asset_type = models.ForeignKey(AssetType, on_delete=models.PROTECT)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)

    # Stored as positive integer — the direction field tells you if it's a debit or credit
    amount = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Indexes speed up the most common queries: "show me all entries for wallet X"
        # and "show me all entries for transaction Y", both sorted by newest first
        indexes = [
            models.Index(fields=['wallet']),
            models.Index(fields=['transaction']),
            models.Index(fields=['-created_at']),
        ]
        constraints = [
            # Amounts must always be positive — direction handles debit vs credit
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='chk_ledger_amount_positive',
            )
        ]


# ── Audit Log ─────────────────────────────────────────────────
# Append-only log of every API request (successful or not).
# Used for debugging, compliance, and abuse detection.
# Writes happen OUTSIDE the main transaction so rolled-back operations still get logged.

class AuditLog(models.Model):
    # Action types — one for each API endpoint
    TOPUP = 'TOPUP'
    BONUS = 'BONUS'
    SPEND = 'SPEND'
    BALANCE_READ = 'BALANCE_READ'
    TRANSACTION_HISTORY = 'TRANSACTION_HISTORY'
    HEALTH_CHECK = 'HEALTH_CHECK'
    ACTION_CHOICES = [
        (TOPUP, 'Top-up'),
        (BONUS, 'Bonus'),
        (SPEND, 'Spend'),
        (BALANCE_READ, 'Balance Read'),
        (TRANSACTION_HISTORY, 'Transaction History'),
        (HEALTH_CHECK, 'Health Check'),
    ]

    # Outcome of the request
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'
    STATUS_CHOICES = [(SUCCESS, 'Success'), (FAILED, 'Failed')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)

    # Stored as a plain UUID (not a FK) because we want to log even if the wallet doesn't exist
    wallet_id = models.UUIDField(null=True, blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    request_body = models.JSONField(null=True, blank=True)
    response_status = models.IntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Indexes support common audit queries: recent logs, per-wallet, per-action, by outcome
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['wallet_id']),
            models.Index(fields=['action']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.action} {self.status} {self.created_at}"
