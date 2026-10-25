CREATE TABLE backups (
    backup_id TEXT PRIMARY KEY,
    user_id TEXT,
    email TEXT,
    phone TEXT,
    name TEXT,
    email_hash TEXT,
    created_at TEXT,
    restorable INTEGER
);

INSERT INTO backups VALUES ('backup_test_01', 'test_user_01', 'user1@example.com', '+1-555-0001', 'User One', 'a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456', '2026-01-10T10:00:00Z', 1);
INSERT INTO backups VALUES ('backup_test_02', 'test_user_02', 'user2@example.com', '+1-555-0002', 'User Two', 'b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234567', '2026-01-10T10:00:00Z', 1);
INSERT INTO backups VALUES ('backup_test_03', 'test_user_03', 'user3@example.com', '+1-555-0003', 'User Three', 'c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678', '2026-01-10T10:00:00Z', 1);