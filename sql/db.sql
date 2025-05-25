-- Si necesitas crear la base de datos 'library_db' primero, descomenta las siguientes dos líneas:
-- CREATE DATABASE IF NOT EXISTS library_db;
-- USE library_db;

-- 1. Tabla users (Usuarios)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL, -- Almacena el hash de la contraseña (¡nunca la contraseña en texto plano!)
    email VARCHAR(255) UNIQUE,
    full_name VARCHAR(255),
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabla genres (Géneros Literarios) - Creada antes de books para establecer FK
CREATE TABLE genres (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

-- 3. Tabla books (Libros)
CREATE TABLE books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    isbn VARCHAR(20) UNIQUE,
    publication_year INT,
    publisher VARCHAR(255),
    genre_id INT, -- Esta columna será la clave foránea (FK)
    total_copies INT NOT NULL DEFAULT 1,
    available_copies INT NOT NULL DEFAULT 1,
    description TEXT,
    FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE SET NULL -- RELACIÓN: books.genre_id se refiere a genres.id
);

-- 4. Tabla loans (Préstamos)
CREATE TABLE loans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL, -- Esta columna será la clave foránea (FK)
    book_id INT NOT NULL, -- Esta columna será la clave foránea (FK)
    loan_date DATE NOT NULL,
    due_date DATE NOT NULL,
    return_date DATE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE, -- RELACIÓN: loans.user_id se refiere a users.id
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE RESTRICT -- RELACIÓN: loans.book_id se refiere a books.id
);

-- 5. Tabla reservations (Reservas)
CREATE TABLE reservations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL, -- Esta columna será la clave foránea (FK)
    book_id INT NOT NULL, -- Esta columna será la clave foránea (FK)
    reservation_date DATE NOT NULL,
    status ENUM('pending', 'ready_for_pickup', 'cancelled', 'fulfilled') DEFAULT 'pending',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE, -- RELACIÓN: reservations.user_id se refiere a users.id
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE -- RELACIÓN: reservations.book_id se refiere a books.id
);

-- 6. Tabla book_movements (Movimientos de libros)
CREATE TABLE IF NOT EXISTS book_movements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    book_id INT NOT NULL,
    user_id INT NOT NULL,
    movement_type VARCHAR(20) NOT NULL,
    quantity INT NOT NULL,
    description VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (book_id) REFERENCES books(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 7. Tabla loan_history (Historial de Préstamos)
CREATE TABLE IF NOT EXISTS loan_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    loan_id INT NOT NULL,
    user_id INT NOT NULL,
    book_id INT NOT NULL,
    action_type ENUM('checkout', 'return', 'renewal', 'overdue') NOT NULL,
    action_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);