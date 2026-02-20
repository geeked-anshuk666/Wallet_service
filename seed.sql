-- seed.sql
-- Run after Django migrations so all tables exist.
-- Uses the same UUIDs as wallets/migrations/0002_seed.py.

-- Asset types
INSERT INTO wallets_assettype (id, name, symbol) VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Gold Coins',     'GLD'),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'Diamonds',       'DIA'),
    ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'Loyalty Points', 'LPT')
ON CONFLICT DO NOTHING;

-- Users (auth_user table — only id, username, and required fields)
INSERT INTO auth_user (username, password, is_superuser, is_staff, is_active, date_joined, first_name, last_name, email) VALUES
    ('system_treasury', '', FALSE, FALSE, FALSE, NOW(), '', '', ''),
    ('system_bonus',    '', FALSE, FALSE, FALSE, NOW(), '', '', ''),
    ('system_revenue',  '', FALSE, FALSE, FALSE, NOW(), '', '', ''),
    ('alice',           '', FALSE, FALSE, TRUE,  NOW(), '', '', ''),
    ('bob',             '', FALSE, FALSE, TRUE,  NOW(), '', '', '')
ON CONFLICT DO NOTHING;

-- System wallets
INSERT INTO wallets_wallet (id, user_id, asset_type_id, balance, is_system) VALUES
    ('11111111-1111-1111-1111-111111111111', (SELECT id FROM auth_user WHERE username = 'system_treasury'), 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 9999300, TRUE),
    ('22222222-2222-2222-2222-222222222222', (SELECT id FROM auth_user WHERE username = 'system_bonus'),    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 5000000, TRUE),
    ('33333333-3333-3333-3333-333333333333', (SELECT id FROM auth_user WHERE username = 'system_revenue'),  'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 0,       TRUE)
ON CONFLICT DO NOTHING;

-- User wallets
INSERT INTO wallets_wallet (id, user_id, asset_type_id, balance, is_system) VALUES
    ('44444444-4444-4444-4444-444444444444', (SELECT id FROM auth_user WHERE username = 'alice'), 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 500, FALSE),
    ('55555555-5555-5555-5555-555555555555', (SELECT id FROM auth_user WHERE username = 'bob'),   'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 200, FALSE)
ON CONFLICT DO NOTHING;

-- Seed transactions
INSERT INTO wallets_wallettransaction (id, type, idempotency_key, status) VALUES
    ('66666666-6666-6666-6666-666666666666', 'TOPUP', 'seed-alice-topup-500', 'COMPLETED'),
    ('77777777-7777-7777-7777-777777777777', 'TOPUP', 'seed-bob-topup-200',   'COMPLETED')
ON CONFLICT DO NOTHING;

-- Ledger entries for seed transactions
INSERT INTO wallets_ledgerentry (id, transaction_id, wallet_id, asset_type_id, direction, amount) VALUES
    (gen_random_uuid(), '66666666-6666-6666-6666-666666666666', '11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'DEBIT',  500),
    (gen_random_uuid(), '66666666-6666-6666-6666-666666666666', '44444444-4444-4444-4444-444444444444', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'CREDIT', 500),
    (gen_random_uuid(), '77777777-7777-7777-7777-777777777777', '11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'DEBIT',  200),
    (gen_random_uuid(), '77777777-7777-7777-7777-777777777777', '55555555-5555-5555-5555-555555555555', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'CREDIT', 200)
ON CONFLICT DO NOTHING;
