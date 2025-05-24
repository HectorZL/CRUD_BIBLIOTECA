from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from .db import get_db_connection, get_cursor

bp = Blueprint('auth', __name__)

# Ruta para el login
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Por favor ingrese usuario y contraseña', 'error')
            return redirect(url_for('auth.login'))
        
        conn = get_db_connection()
        cur = get_cursor()
        
        try:
            # Buscar usuario en la base de datos
            cur.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cur.fetchone()
            
            if not user or not check_password_hash(user['password_hash'], password):
                flash('Usuario o contraseña incorrectos', 'error')
                return redirect(url_for('auth.login'))
            
            # Configurar la sesión del usuario
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user.get('is_admin', False))
            session.permanent = True
            
            flash(f'¡Bienvenido de nuevo, {user["username"]}!', 'success')
            return redirect(url_for('main.index'))
            
        except Exception as e:
            flash(f'Error al iniciar sesión: {str(e)}', 'error')
            return redirect(url_for('auth.login'))
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()
    
    # Si es GET, mostrar el formulario de login
    return render_template('auth/login.html')

# Ruta para cerrar sesión
@bp.route('/logout')
def logout():
    # Eliminar datos de la sesión
    session.clear()
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('auth.login'))

# Ruta para el registro de nuevos usuarios (solo administradores)
@bp.route('/register', methods=['GET', 'POST'])
def register():
    # Verificar si el usuario está autenticado y es administrador
    if 'user_id' not in session or not session.get('is_admin', False):
        flash('No tienes permiso para acceder a esta página', 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        is_admin = 'is_admin' in request.form
        
        if not all([username, password, email]):
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('auth.register'))
        
        conn = get_db_connection()
        cur = get_cursor()
        
        try:
            # Verificar si el usuario ya existe
            cur.execute('SELECT id FROM users WHERE username = %s OR email = %s', 
                       (username, email))
            if cur.fetchone():
                flash('El nombre de usuario o correo electrónico ya está en uso', 'error')
                return redirect(url_for('auth.register'))
            
            # Crear el nuevo usuario
            hashed_password = generate_password_hash(password, method='sha256')
            cur.execute("""
                INSERT INTO users (username, password_hash, email, full_name, is_admin)
                VALUES (%s, %s, %s, %s, %s)
            """, (username, hashed_password, email, full_name, is_admin))
            
            conn.commit()
            flash('Usuario registrado exitosamente', 'success')
            return redirect(url_for('auth.register'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error al registrar el usuario: {str(e)}', 'error')
            return redirect(url_for('auth.register'))
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()
    
    # Si es GET, mostrar el formulario de registro
    return render_template('auth/register.html')
