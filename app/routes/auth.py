from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from ..db import get_db_connection, get_cursor
from ..decorators import login_required, admin_required
from datetime import datetime, timedelta
import logging

# Create blueprint
bp = Blueprint('auth', __name__)

# Configure logging
logger = logging.getLogger(__name__)

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
            
            # Verificar si el usuario está baneado
            if user.get('is_banned'):
                ban_message = 'Su cuenta está restringida.'
                if user.get('ban_reason'):
                    ban_message += f" Motivo: {user['ban_reason']}"
                if user.get('ban_expires_at'):
                    ban_message += f" La restricción finaliza el: {user['ban_expires_at'].strftime('%d/%m/%Y')}"
                flash(ban_message, 'error')
                return redirect(url_for('auth.login'))
            
            # Configurar la sesión del usuario
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user.get('is_admin', False))
            session.permanent = True
            
            flash(f'¡Bienvenido de nuevo, {user["username"]}!', 'success')
            return redirect(url_for('dashboard.index'))
            
        except Exception as e:
            logger.error(f"Error en login: {str(e)}", exc_info=True)
            flash(f'Error al iniciar sesión: {str(e)}', 'error')
            return redirect(url_for('auth.login'))
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()
    
    # Si es GET, mostrar el formulario de login
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))

# Ruta para el registro de nuevos usuarios (solo administradores)
@bp.route('/register', methods=['GET', 'POST'])
@login_required
@admin_required
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        is_admin = 1 if request.form.get('is_admin') else 0
        
        # Validaciones
        if not all([username, password, confirm_password, email]):
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('auth.register'))
            
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'error')
            return redirect(url_for('auth.register'))
            
        conn = get_db_connection()
        cur = get_cursor()
        
        try:
            # Verificar si el usuario ya existe
            cur.execute('SELECT id FROM users WHERE username = %s', (username,))
            if cur.fetchone():
                flash('El nombre de usuario ya está en uso', 'error')
                return redirect(url_for('auth.register'))
                
            # Crear el nuevo usuario
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            cur.execute("""
                INSERT INTO users (username, password_hash, email, full_name, is_admin)
                VALUES (%s, %s, %s, %s, %s)
            """, (username, hashed_password, email, full_name, is_admin))
            
            conn.commit()
            flash('Usuario registrado exitosamente', 'success')
            return redirect(url_for('users.manage'))
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error al registrar usuario: {str(e)}", exc_info=True)
            flash(f'Error al registrar usuario: {str(e)}', 'error')
            return redirect(url_for('auth.register'))
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()
    
    # Si es GET, mostrar el formulario de registro
    return render_template('auth/register.html')

# Ruta para el perfil de usuario
@bp.route('/profile')
@login_required
def profile():
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
        user = cur.fetchone()
        
        if not user:
            flash('Usuario no encontrado', 'error')
            return redirect(url_for('dashboard.index'))
            
        return render_template('auth/profile.html', user=user)
        
    except Exception as e:
        logger.error(f"Error al cargar perfil: {str(e)}", exc_info=True)
        flash('Error al cargar el perfil', 'error')
        return redirect(url_for('dashboard.index'))
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para actualizar el perfil de usuario
@bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        # Obtener el usuario actual
        cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
        user = cur.fetchone()
        
        if not user:
            flash('Usuario no encontrado', 'error')
            return redirect(url_for('auth.profile'))
        
        # Verificar contraseña actual si se intenta cambiar la contraseña
        if new_password:
            if not current_password or not check_password_hash(user['password_hash'], current_password):
                flash('La contraseña actual es incorrecta', 'error')
                return redirect(url_for('auth.profile'))
                
            if new_password != confirm_password:
                flash('Las nuevas contraseñas no coinciden', 'error')
                return redirect(url_for('auth.profile'))
                
            # Actualizar contraseña
            hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
            cur.execute("""
                UPDATE users 
                SET password_hash = %s, full_name = %s, email = %s
                WHERE id = %s
            """, (hashed_password, full_name, email, session['user_id']))
        else:
            # Actualizar solo nombre y correo
            cur.execute("""
                UPDATE users 
                SET full_name = %s, email = %s
                WHERE id = %s
            """, (full_name, email, session['user_id']))
        
        conn.commit()
        flash('Perfil actualizado correctamente', 'success')
        return redirect(url_for('auth.profile'))
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error al actualizar perfil: {str(e)}", exc_info=True)
        flash('Error al actualizar el perfil', 'error')
        return redirect(url_for('auth.profile'))
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
