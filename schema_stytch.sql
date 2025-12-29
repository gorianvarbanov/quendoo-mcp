-- Add Stytch user ID to existing users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS stytch_user_id VARCHAR(255) UNIQUE;

-- Create index for fast lookup by Stytch user ID
CREATE INDEX IF NOT EXISTS idx_users_stytch_user_id ON users(stytch_user_id);

-- Add comment explaining the column
COMMENT ON COLUMN users.stytch_user_id IS 'Stytch user ID from OAuth authentication';
