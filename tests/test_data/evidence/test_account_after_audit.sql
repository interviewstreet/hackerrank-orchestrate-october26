CREATE TABLE user_profiles (
    user_id TEXT PRIMARY KEY,
    email TEXT,
    phone TEXT,
    name TEXT,
    email_hash TEXT,
    deleted_at TEXT
);

INSERT INTO user_profiles VALUES ('test_user_01', 'user1@example.com', '+1-555-0001', 'User One', 'a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456', NULL);
INSERT INTO user_profiles VALUES ('test_user_02', 'user2@example.com', '+1-555-0002', 'User Two', 'b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234567', NULL);