from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from .db import get_db_connection, get_cursor
from .decorators import login_required, admin_required

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

# Ruta para el perfil de usuario
@bp.route('/profile')
@login_required
def profile():
    conn = get_db_connection()
    cur = get_cursor()
    try:
        cur.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
        user = cur.fetchone()
        return render_template('auth/profile.html', user=user)
    except Exception as e:
        flash(f'Error al cargar el perfil: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para la administración de usuarios (solo administradores)
@bp.route('/admin/users')
@login_required
@admin_required
def manage_users():
    conn = get_db_connection()
    cur = get_cursor()
    try:
        cur.execute('SELECT id, username, email, full_name, is_admin FROM users ORDER BY username')
        users = cur.fetchall()
        return render_template('admin/users.html', users=users)
    except Exception as e:
        flash(f'Error al cargar la lista de usuarios: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para la administración de géneros (solo administradores)
@bp.route('/admin/genres')
@login_required
@admin_required
def manage_genres():
    conn = get_db_connection()
    cur = get_cursor()
    try:
        cur.execute('SELECT * FROM genres ORDER BY name')
        genres = cur.fetchall()
        return render_template('admin/genres.html', genres=genres)
    except Exception as e:
        flash(f'Error al cargar la lista de géneros: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para actualizar el perfil de usuario
@bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    if request.method == 'POST':
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
            
            # Verificar si se está intentando cambiar la contraseña
            if current_password or new_password or confirm_password:
                if not all([current_password, new_password, confirm_password]):
                    flash('Todos los campos de contraseña son obligatorios para cambiar la contraseña', 'error')
                    return redirect(url_for('auth.profile'))
                
                if new_password != confirm_password:
                    flash('Las contraseñas nuevas no coinciden', 'error')
                    return redirect(url_for('auth.profile'))
                
                if len(new_password) < 8:
                    flash('La nueva contraseña debe tener al menos 8 caracteres', 'error')
                    return redirect(url_for('auth.profile'))
                
                if not check_password_hash(user['password_hash'], current_password):
                    flash('La contraseña actual es incorrecta', 'error')
                    return redirect(url_for('auth.profile'))
                
                # Actualizar la contraseña
                hashed_password = generate_password_hash(new_password, method='sha256')
                cur.execute('UPDATE users SET password_hash = %s WHERE id = %s', 
                           (hashed_password, session['user_id']))
            
            # Actualizar otros datos del perfil
            cur.execute('UPDATE users SET full_name = %s, email = %s WHERE id = %s',
                       (full_name, email, session['user_id']))
            
            conn.commit()
            flash('Perfil actualizado correctamente', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Error al actualizar el perfil: {str(e)}', 'error')
            return redirect(url_for('auth.profile'))
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()
    
    return redirect(url_for('auth.profile'))

# Ruta para agregar un nuevo género (AJAX)
@bp.route('/admin/genres/add', methods=['POST'])
@login_required
@admin_required
def add_genre():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        if not name:
            return jsonify({'success': False, 'message': 'El nombre del género es obligatorio'}), 400
        
        conn = get_db_connection()
        cur = get_cursor()
        
        try:
            # Verificar si el género ya existe
            cur.execute('SELECT id FROM genres WHERE name = %s', (name,))
            if cur.fetchone():
                return jsonify({'success': False, 'message': 'El género ya existe'}), 400
            
            # Insertar el nuevo género
            cur.execute('INSERT INTO genres (name, description) VALUES (%s, %s)', 
                       (name, description))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Género agregado correctamente'})
            
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': f'Error al agregar el género: {str(e)}'}), 500
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()
    
    return jsonify({'success': False, 'message': 'Método no permitido'}), 405

# Ruta para editar un género (AJAX)
@bp.route('/admin/genres/<int:genre_id>', methods=['PUT'])
@login_required
@admin_required
def edit_genre(genre_id):
    if request.method == 'PUT':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        if not name:
            return jsonify({'success': False, 'message': 'El nombre del género es obligatorio'}), 400
        
        conn = get_db_connection()
        cur = get_cursor()
        
        try:
            # Verificar si el género existe
            cur.execute('SELECT id FROM genres WHERE id = %s', (genre_id,))
            if not cur.fetchone():
                return jsonify({'success': False, 'message': 'Género no encontrado'}), 404
            
            # Verificar si ya existe otro género con el mismo nombre
            cur.execute('SELECT id FROM genres WHERE name = %s AND id != %s', (name, genre_id))
            if cur.fetchone():
                return jsonify({'success': False, 'message': 'Ya existe otro género con ese nombre'}), 400
            
            # Actualizar el género
            cur.execute('UPDATE genres SET name = %s, description = %s WHERE id = %s', 
                       (name, description, genre_id))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Género actualizado correctamente'})
            
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': f'Error al actualizar el género: {str(e)}'}), 500
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()
    
    return jsonify({'success': False, 'message': 'Método no permitido'}), 405

# Ruta para eliminar un género (AJAX)
@bp.route('/admin/genres/<int:genre_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_genre(genre_id):
    if request.method == 'DELETE':
        conn = get_db_connection()
        cur = get_cursor()
        
        try:
            # Verificar si el género existe
            cur.execute('SELECT id, name FROM genres WHERE id = %s', (genre_id,))
            genre = cur.fetchone()
            
            if not genre:
                return jsonify({'success': False, 'message': 'Género no encontrado'}), 404
            
            # Verificar si hay libros asociados a este género
            cur.execute('SELECT COUNT(*) as count FROM books WHERE genre_id = %s', (genre_id,))
            book_count = cur.fetchone()['count']
            
            if book_count > 0:
                return jsonify({
                    'success': False, 
                    'message': f'No se puede eliminar el género "{genre["name"]}" porque tiene {book_count} libro(s) asociado(s)'
                }), 400
            
            # Eliminar el género
            cur.execute('DELETE FROM genres WHERE id = %s', (genre_id,))
            conn.commit()
            
            return jsonify({
                'success': True, 
                'message': f'Género "{genre["name"]}" eliminado correctamente'
            })
            
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': f'Error al eliminar el género: {str(e)}'}), 500
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()
    
    return jsonify({'success': False, 'message': 'Método no permitido'}), 405
