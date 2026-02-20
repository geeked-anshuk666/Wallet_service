import uuid

from django.db import models


class AssetType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    symbol = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('auth.User', on_delete=models.PROTECT, related_name='wallets')
    asset_type = models.ForeignKey(AssetType, on_delete=models.PROTECT)
    balance = models.BigIntegerField(default=0)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('user', 'asset_type')]
        constraints = [
            models.CheckConstraint(
                check=models.Q(balance__gte=0) | models.Q(is_system=True),
                name='chk_balance_non_negative',
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.asset_type.name}"


class WalletTransaction(models.Model):
    TOPUP = 'TOPUP'
    BONUS = 'BONUS'
    SPEND = 'SPEND'
    TYPE_CHOICES = [(TOPUP, 'Top-up'), (BONUS, 'Bonus'), (SPEND, 'Spend')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    idempotency_key = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, default='COMPLETED')
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} - {self.idempotency_key}"


class LedgerEntry(models.Model):
    DEBIT = 'DEBIT'
    CREDIT = 'CREDIT'
    DIRECTION_CHOICES = [(DEBIT, 'Debit'), (CREDIT, 'Credit')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(WalletTransaction, on_delete=models.PROTECT, related_name='entries')
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='ledger_entries')
    asset_type = models.ForeignKey(AssetType, on_delete=models.PROTECT)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    amount = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['wallet']),
            models.Index(fields=['transaction']),
            models.Index(fields=['-created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='chk_ledger_amount_positive',
            )
        ]


class AuditLog(models.Model):
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

    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'
    STATUS_CHOICES = [(SUCCESS, 'Success'), (FAILED, 'Failed')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    wallet_id = models.UUIDField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    request_body = models.JSONField(null=True, blank=True)
    response_status = models.IntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['wallet_id']),
            models.Index(fields=['action']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.action} {self.status} {self.created_at}"
