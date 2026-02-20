-- schema.sql
-- Reference schema for the wallet service.
-- To apply via Django (recommended): python manage.py migrate
-- This file is for manual inspection only.

CREATE TABLE IF NOT EXISTS wallets_assettype (
    id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name       VARCHAR(100) NOT NULL,
    symbol     VARCHAR(20)  NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT wallets_assettype_name_key   UNIQUE (name),
    CONSTRAINT wallets_assettype_symbol_key UNIQUE (symbol)
);

CREATE TABLE IF NOT EXISTS wallets_wallet (
    id            UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       INTEGER NOT NULL REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED,
    asset_type_id UUID    NOT NULL REFERENCES wallets_assettype(id) DEFERRABLE INITIALLY DEFERRED,
    balance       BIGINT  NOT NULL DEFAULT 0,
    is_system     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT wallets_wallet_user_asset_type_key UNIQUE (user_id, asset_type_id),
    CONSTRAINT chk_balance_non_negative CHECK (balance >= 0 OR is_system = TRUE)
);

CREATE TABLE IF NOT EXISTS wallets_wallettransaction (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    type            VARCHAR(20)  NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL,
    status          VARCHAR(20)  NOT NULL DEFAULT 'COMPLETED',
    metadata        JSONB,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT wallets_wallettransaction_idempotency_key_key UNIQUE (idempotency_key)
);

CREATE TABLE IF NOT EXISTS wallets_ledgerentry (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID        NOT NULL REFERENCES wallets_wallettransaction(id) DEFERRABLE INITIALLY DEFERRED,
    wallet_id      UUID        NOT NULL REFERENCES wallets_wallet(id) DEFERRABLE INITIALLY DEFERRED,
    asset_type_id  UUID        NOT NULL REFERENCES wallets_assettype(id) DEFERRABLE INITIALLY DEFERRED,
    direction      VARCHAR(10) NOT NULL,
    amount         BIGINT      NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_ledger_amount_positive CHECK (amount > 0)
);

CREATE TABLE IF NOT EXISTS wallets_auditlog (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    action          VARCHAR(30)  NOT NULL,
    wallet_id       UUID,                         -- nullable, no FK — intentional
    status          VARCHAR(10)  NOT NULL,
    request_body    JSONB,
    response_status INTEGER      NOT NULL,
    ip_address      INET,
    error_message   TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- LedgerEntry indexes
CREATE INDEX IF NOT EXISTS wallets_ledgerentry_wallet_id      ON wallets_ledgerentry(wallet_id);
CREATE INDEX IF NOT EXISTS wallets_ledgerentry_transaction_id ON wallets_ledgerentry(transaction_id);
CREATE INDEX IF NOT EXISTS wallets_ledgerentry_created_at     ON wallets_ledgerentry(created_at DESC);

-- AuditLog indexes
CREATE INDEX IF NOT EXISTS wallets_auditlog_created_at  ON wallets_auditlog(created_at DESC);
CREATE INDEX IF NOT EXISTS wallets_auditlog_wallet_id   ON wallets_auditlog(wallet_id);
CREATE INDEX IF NOT EXISTS wallets_auditlog_action      ON wallets_auditlog(action);
CREATE INDEX IF NOT EXISTS wallets_auditlog_status      ON wallets_auditlog(status);

-- NOTE: auth_user is created by Django's built-in auth migrations.
-- Run `python manage.py migrate` first, then use this file for reference.
