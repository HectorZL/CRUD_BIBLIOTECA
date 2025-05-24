# Sistema de Gestión de Biblioteca

Aplicación web para la gestión de una biblioteca desarrollada con Flask y MySQL. Permite administrar libros, usuarios, préstamos y reservas de manera eficiente.

## Características

- Autenticación de usuarios (administradores y usuarios regulares)
- Gestión de libros (CRUD completo)
- Control de préstamos y devoluciones
- Búsqueda y filtrado de libros
- Panel de administración
- Interfaz responsiva con Bootstrap 5

## Requisitos

- Python 3.8 o superior
- MySQL 8.0 o superior
- pip (gestor de paquetes de Python)

## Instalación

1. Clona este repositorio:
   ```bash
   git clone https://github.com/tu-usuario/flask-crud-contacts-app.git
   cd flask-crud-contacts-app
   ```

2. Crea y activa un entorno virtual:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Configura la base de datos:
   - Crea una base de datos MySQL
   - Configura las variables de entorno en un archivo `.env` basado en `.env.example`

5. Inicializa la base de datos:
   ```bash
   python init_db.py
   ```
   Esto creará las tablas necesarias y un usuario administrador por defecto:
   - Usuario: admin
   - Contraseña: admin123

6. Ejecuta la aplicación:
   ```bash
   python -m flask run --port=5000
   ```

7. Abre tu navegador en [http://localhost:5000](http://localhost:5000)

