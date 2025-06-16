-- Add is_active column to users table with default value 1 (true)
ALTER TABLE users 
ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL 
COMMENT 'Indica si el usuario está activo (1) o inactivo (0)';

-- Update existing users to be active by default
UPDATE users SET is_active = 1 WHERE is_active IS NULL;
