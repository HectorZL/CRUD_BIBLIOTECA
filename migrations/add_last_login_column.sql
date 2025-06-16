-- Add last_login column to users table
ALTER TABLE users 
ADD COLUMN last_login DATETIME NULL DEFAULT NULL 
COMMENT 'Stores the timestamp of the user\'s last login' 
AFTER password_hash;

-- Update existing users with a default last_login value (current timestamp for active users)
UPDATE users 
SET last_login = NOW() 
WHERE is_active = 1 AND last_login IS NULL;
