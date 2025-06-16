-- Agregar columna puede_prestar a la tabla users
ALTER TABLE users 
ADD COLUMN puede_prestar BOOLEAN DEFAULT TRUE NOT NULL 
COMMENT 'Indica si el usuario puede realizar préstamos de libros';

-- Establecer valor predeterminado para usuarios existentes
UPDATE users SET puede_prestar = TRUE WHERE puede_prestar IS NULL;
