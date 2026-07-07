ALTER TABLE users
ADD COLUMN IF NOT EXISTS oauth_provider TEXT;

ALTER TABLE users
ADD COLUMN IF NOT EXISTS oauth_id TEXT;

ALTER TABLE users
ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user';

UPDATE users
SET role = 'user'
WHERE role IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'users_oauth_provider_oauth_id_key'
    ) THEN
        ALTER TABLE users
        ADD CONSTRAINT users_oauth_provider_oauth_id_key
        UNIQUE(oauth_provider, oauth_id);
    END IF;
END $$;
