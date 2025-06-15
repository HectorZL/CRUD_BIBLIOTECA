from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from ..db import get_db_connection, get_cursor
from ..decorators import login_required, admin_required
from datetime import datetime, timedelta
import logging

# Create blueprint
bp = Blueprint('users', __name__, url_prefix='/users')

# Configure logging
logger = logging.getLogger(__name__)

# Ruta para la gestión de usuarios (solo administradores)
@bp.route('/')
@login_required
@admin_required
def manage():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = get_cursor()
        
        # Obtener todos los usuarios
        cur.execute("""
            SELECT u.*, 
                   (SELECT username FROM users WHERE id = u.banned_by) as banned_by_name
            FROM users u
            ORDER BY u.is_banned DESC, u.username
        """)
        
        users = cur.fetchall()
        return render_template('admin/users.html', users=users)
        
    except Exception as e:
        logger.error(f"Error al cargar la lista de usuarios: {str(e)}", exc_info=True)
        flash('Error al cargar la lista de usuarios', 'error')
        return render_template('admin/users.html', users=[])
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# Ruta para restringir un usuario (ban)
@bp.route('/ban/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def ban_user(user_id):
    if not request.form.get('reason'):
        flash('Debe especificar un motivo para la restricción', 'error')
        return redirect(url_for('users.manage'))
        
    duration = int(request.form.get('duration', 0))  # 0 = indefinido
    reason = request.form.get('reason')
    details = request.form.get('details', '')
    
    conn = None
    cur = None
    
    try:
        conn = get_db_connection()
        cur = get_cursor()
        
        # Verificar que el usuario existe y no es administrador
        cur.execute("""
            SELECT id, is_admin FROM users 
            WHERE id = %s AND is_admin = 0
        """, (user_id,))
        user = cur.fetchone()
        
        if not user:
            flash('Usuario no encontrado o no se puede restringir a un administrador', 'error')
            return redirect(url_for('users.manage'))
            
        # Calcular fecha de expiración
        ban_expires_at = None
        if duration > 0:
            ban_expires_at = datetime.now() + timedelta(days=duration)
        
        # Actualizar usuario
        cur.execute("""
            UPDATE users 
            SET is_banned = TRUE,
                ban_reason = %s,
                ban_expires_at = %s,
                banned_at = NOW(),
                banned_by = %s
            WHERE id = %s
        """, (reason, ban_expires_at, session['user_id'], user_id))
        
        conn.commit()
        
        # Registrar la acción
        cur.execute("""
            INSERT INTO user_actions (user_id, action_type, description, ip_address)
            VALUES (%s, 'user_banned', %s, %s)
        """, (session['user_id'], 
              f'Usuario {user_id} restringido. Motivo: {reason}', 
              request.remote_addr))
        conn.commit()
        
        duration_text = 'indefinidamente' if not ban_expires_at else f'por {duration} días'
        flash(f'Usuario restringido {duration_text}.', 'success')
        
    except Exception as e:
        logger.error(f"Error al restringir usuario: {str(e)}", exc_info=True)
        if conn:
            conn.rollback()
        flash('Ocurrió un error al procesar la restricción', 'error')
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    
    return redirect(url_for('users.manage'))

# Ruta para quitar restricción a un usuario (unban)
@bp.route('/unban/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def unban_user(user_id):
    conn = None
    cur = None
    
    try:
        conn = get_db_connection()
        cur = get_cursor()
        
        # Verificar que el usuario existe y está baneado
        cur.execute("""
            SELECT id FROM users 
            WHERE id = %s AND is_banned = TRUE
        """, (user_id,))
        
        if not cur.fetchone():
            flash('Usuario no encontrado o no está restringido', 'warning')
            return redirect(url_for('users.manage'))
            
        # Quitar restricción
        cur.execute("""
            UPDATE users 
            SET is_banned = FALSE,
                ban_reason = NULL,
                ban_expires_at = NULL,
                banned_at = NULL,
                banned_by = NULL
            WHERE id = %s
        """, (user_id,))
        
        conn.commit()
        
        # Registrar la acción
        cur.execute("""
            INSERT INTO user_actions (user_id, action_type, description, ip_address)
            VALUES (%s, 'user_unbanned', %s, %s)
        """, (session['user_id'], 
              f'Se quitó la restricción al usuario {user_id}', 
              request.remote_addr))
        conn.commit()
        
        flash('Restricción eliminada correctamente', 'success')
        
    except Exception as e:
        logger.error(f"Error al quitar restricción de usuario: {str(e)}", exc_info=True)
        if conn:
            conn.rollback()
        flash('Ocurrió un error al quitar la restricción', 'error')
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
    
    return redirect(url_for('users.manage'))

# Ruta para ver el historial de acciones de un usuario
@bp.route('/<int:user_id>/history')
@login_required
@admin_required
def user_history(user_id):
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        # Obtener información del usuario
        cur.execute('SELECT id, username, full_name FROM users WHERE id = %s', (user_id,))
        user = cur.fetchone()
        
        if not user:
            flash('Usuario no encontrado', 'error')
            return redirect(url_for('users.manage'))
            
        # Obtener historial de acciones
        cur.execute("""
            SELECT * FROM user_actions 
            WHERE user_id = %s 
            ORDER BY action_date DESC
            LIMIT 50
        """, (user_id,))
        
        actions = cur.fetchall()
        
        return render_template('users/history.html', 
                             user=user, 
                             actions=actions,
                             title=f'Historial - {user["username"]}')
    except Exception as e:
        logger.error(f"Error al cargar historial de usuario: {str(e)}", exc_info=True)
        flash('Error al cargar el historial del usuario', 'error')
        return redirect(url_for('users.manage'))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# Ruta para eliminar un usuario
@bp.route('/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    from flask import current_app
    conn = None
    cur = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Verificar si el usuario existe
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        
        if not user:
            return jsonify({'success': False, 'message': 'El usuario no existe'}), 404
            
        # No permitir que un usuario se elimine a sí mismo
        if user_id == session['user_id']:
            return jsonify({
                'success': False, 
                'message': 'No puedes eliminar tu propia cuenta'
            }), 400
        
        # Obtener información del usuario antes de eliminarlo para el registro
        username = user['username']
        
        # Solo iniciar transacción si no hay una en curso
        if not conn.in_transaction:
            conn.start_transaction()
        
        # Eliminar registros relacionados en book_movements
        cur.execute("""
            DELETE FROM book_movements 
            WHERE user_id = %s
        """, (user_id,))
        
        # Eliminar registros relacionados en loans
        cur.execute("""
            DELETE FROM loans 
            WHERE user_id = %s
        """, (user_id,))
        
        # Eliminar registros relacionados en reservations
        cur.execute("""
            DELETE FROM reservations 
            WHERE user_id = %s
        """, (user_id,))
        
        # Eliminar registros relacionados en user_actions
        cur.execute("""
            DELETE FROM user_actions 
            WHERE user_id = %s
        """, (user_id,))
        
        # Finalmente, eliminar el usuario
        cur.execute("""
            DELETE FROM users 
            WHERE id = %s
        """, (user_id,))
        
        # Registrar la acción
        cur.execute("""
            INSERT INTO user_actions (user_id, action_type, description, ip_address)
            VALUES (%s, 'user_deleted', %s, %s)
        """, (session['user_id'], 
              f'Usuario eliminado: {username} (ID: {user_id})', 
              request.remote_addr))
        
        # Confirmar la transacción
        conn.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Usuario {username} eliminado correctamente'
        })
        
    except Exception as e:
        if conn and conn.in_transaction:
            conn.rollback()
        current_app.logger.error(f'Error al eliminar usuario: {str(e)}')
        return jsonify({
            'success': False, 
            'message': 'Ocurrió un error al eliminar el usuario. Por favor, inténtalo de nuevo.'
        }), 500
    finally:
        try:
            if cur:
                cur.close()
            if conn and conn.is_connected():
                conn.close()
        except Exception as e:
            current_app.logger.error(f'Error al cerrar la conexión: {str(e)}')
