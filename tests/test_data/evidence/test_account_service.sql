CREATE TABLE user_profiles (
    user_id TEXT PRIMARY KEY,
    email TEXT,
    phone TEXT,
    name TEXT,
    email_hash TEXT,
    deleted_at TEXT
);

INSERT INTO user_profiles VALUES ('test_user_01', 'user1@example.com', '+1-555-0001', 'User One', 'a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456', '2026-01-16T10:00:00Z');
INSERT INTO user_profiles VALUES ('test_user_02', 'user2@example.com', '+1-555-0002', 'User Two', 'b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234567', NULL);
INSERT INTO user_profiles VALUES ('test_user_03', 'user3@example.com', '+1-555-0003', 'User Three', 'c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678', '2026-01-16T10:00:00Z');
INSERT INTO user_profiles VALUES ('test_user_11', 'user11@example.com', '+1-555-0011', 'User Eleven', 'k12345678901234567890abcdef1234567890abcdef1234567890abcdef1', NULL);

CREATE TABLE account_tombstones (
    user_id TEXT PRIMARY KEY,
    deleted_at TEXT
);

INSERT INTO account_tombstones VALUES ('test_user_01', '2026-01-16T10:00:00Z');
INSERT INTO account_tombstones VALUES ('test_user_03', '2026-01-16T10:00:00Z');