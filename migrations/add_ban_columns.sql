-- Add ban/suspend related columns to users table
ALTER TABLE users
ADD COLUMN is_banned BOOLEAN DEFAULT FALSE COMMENT 'Indica si el usuario está baneado',
ADD COLUMN ban_reason VARCHAR(255) DEFAULT NULL COMMENT 'Razón de la restricción',
ADD COLUMN ban_expires_at DATETIME DEFAULT NULL COMMENT 'Fecha de expiración de la restricción',
ADD COLUMN banned_at DATETIME DEFAULT NULL COMMENT 'Fecha en que se aplicó la restricción',
ADD COLUMN banned_by INT DEFAULT NULL COMMENT 'ID del administrador que aplicó la restricción',
ADD COLUMN suspension_type ENUM('none', 'temporary', 'permanent') DEFAULT 'none' COMMENT 'Tipo de suspensión',
ADD COLUMN suspension_until DATETIME DEFAULT NULL COMMENT 'Hasta cuándo está suspendido el usuario';

-- Add foreign key for banned_by
ALTER TABLE users
ADD CONSTRAINT fk_banned_by
FOREIGN KEY (banned_by) REFERENCES users(id)
ON DELETE SET NULL;

-- Update existing users to have default values
UPDATE users SET 
    is_banned = COALESCE(is_banned, FALSE),
    suspension_type = 'none';

-- Create an index for better performance on ban-related queries
CREATE INDEX idx_user_ban_status ON users(is_banned, suspension_type, ban_expires_at, suspension_until);
