# 📚 Sistema de Gestión de Biblioteca

Aplicación web completa para la gestión de bibliotecas desarrollada con Flask, MySQL y Bootstrap 5. Este sistema permite a los administradores y personal de biblioteca gestionar libros, usuarios, préstamos y reservas de manera eficiente, con una interfaz intuitiva y responsiva.

## 🌟 Características Principales

### 📖 Gestión de Libros
- Catálogo completo de libros con búsqueda avanzada
- Gestión de existencias y disponibilidad
- Seguimiento de movimientos de libros
- Control de géneros literarios

### 👥 Gestión de Usuarios
- Sistema de autenticación seguro
- Roles de usuario (Administrador y Usuario regular)
- Perfiles de usuario personalizables
- Historial de préstamos por usuario

### 🔄 Préstamos y Devoluciones
- Registro de préstamos con fechas de vencimiento
- Sistema de renovación de préstamos
- Notificaciones de vencimientos
- Historial completo de movimientos



## 🛠️ Requisitos del Sistema

- Python 3.8 o superior
- MySQL 8.0 o superior
- pip (gestor de paquetes de Python)
- Navegador web moderno (Chrome, Firefox, Edge, Safari)

## 🚀 Instalación y Configuración

### 1. Clonar el Repositorio
```bash
git clone https://github.com/HectorZL/CRUD_BIBLIOTECA
cd CRUD_BIBLIOTECA
```

### 2. Configuración del Entorno Virtual
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 4. Configuración de la Base de Datos
1. Crea una base de datos MySQL
2. Copia el archivo `.env.example` a `.env`
3. Configura las variables de entorno en `.env` con tus credenciales

### 5. Inicialización de la Base de Datos
```bash
python init_db.py
```

**Credenciales por defecto del administrador:**
- **Usuario:** admin
- **Contraseña:** admin123

### 6. Datos de Prueba (Opcional)
Para poblar la base de datos con datos de prueba:
```bash
python insert_test_data.py
```

### 7. Iniciar la Aplicación
```bash
# Modo desarrollo
python -m flask run --port=5000 --debug

# O usando el script run.py
python run.py
```

Accede a la aplicación en [http://localhost:5000](http://localhost:5000)

## 📂 Estructura del Proyecto

```
.
├── app/                    # Código fuente de la aplicación
│   ├── static/             # Archivos estáticos (CSS, JS, imágenes)
│   ├── templates/          # Plantillas HTML
│   ├── __init__.py         # Inicialización de la aplicación
│   ├── auth.py             # Rutas de autenticación
│   ├── decorators.py       # Decoradores personalizados
│   ├── models.py           # Modelos de la base de datos
│   └── routes.py           # Rutas principales
├── sql/                    # Scripts SQL
├── .env.example            # Plantilla de variables de entorno
├── init_db.py             # Script de inicialización de la base de datos
├── requirements.txt        # Dependencias de Python
└── run.py                 # Punto de entrada de la aplicación
```

## 🔍 Características Técnicas

- **Backend:** Python 3.8+ con Flask
- **Base de Datos:** MySQL 8.0+
- **Frontend:** HTML5, CSS3, JavaScript (jQuery)
- **Framework CSS:** Bootstrap 5
- **Autenticación:** Sistema de sesiones seguro
- **API RESTful** para operaciones CRUD

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más información.

## 🤝 Contribución

Las contribuciones son bienvenidas. Por favor, lee nuestras pautas de contribución antes de enviar pull requests.



