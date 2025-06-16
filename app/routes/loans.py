from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from ..db import get_db_connection, get_cursor
from ..decorators import login_required, admin_required
from datetime import datetime, timedelta
import logging

# Create blueprint
bp = Blueprint('loans', __name__, url_prefix='/loans')

# Configure logging
logger = logging.getLogger(__name__)

# Ruta para listar préstamos
@bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 15
    status = request.args.get('status', 'all')  # all, active, overdue, returned
    
    # Calcular fechas por defecto para el formulario
    today = datetime.now().date()
    due_date = today + timedelta(days=15)  # 15 días por defecto para la devolución
    
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        # Construir consulta base
        query = """
            SELECT l.*, 
                   b.title as book_title, b.isbn as book_isbn,
                   u.username as user_name, u.email as user_email,
                   DATEDIFF(l.due_date, CURDATE()) as days_remaining
            FROM loans l
            JOIN books b ON l.book_id = b.id
            JOIN users u ON l.user_id = u.id
            WHERE 1=1
        """
        
        params = []
        
        # Filtrar por estado
        if status == 'active':
            query += " AND l.return_date IS NULL AND l.due_date >= CURDATE()"
        elif status == 'overdue':
            query += " AND l.return_date IS NULL AND l.due_date < CURDATE()"
        elif status == 'returned':
            query += " AND l.return_date IS NOT NULL"
        
        # Mostrar todos los préstamos a todos los usuarios
        # La restricción de edición se manejará en la plantilla
        
        # Contar total de resultados
        count_query = f"SELECT COUNT(*) as total FROM ({query}) as subquery"
        cur.execute(count_query, params)
        total = cur.fetchone()['total']
        
        # Añadir ordenación y paginación
        query += " ORDER BY l.due_date ASC, l.loan_date DESC LIMIT %s OFFSET %s"
        offset = (page - 1) * per_page
        params.extend([per_page, offset])
        
        # Ejecutar consulta principal
        cur.execute(query, params)
        loans = cur.fetchall()
        
        # Calcular páginas para la paginación
        total_pages = (total + per_page - 1) // per_page
        
        # Get user information from session
        user = {
            'id': session.get('user_id'),
            'username': session.get('username'),
            'is_admin': session.get('is_admin', False)
        }
        
        # Obtener libros disponibles para préstamo
        cur.execute("""
            SELECT b.id, b.title, b.author, b.available_copies 
            FROM books b 
            WHERE b.available_copies > 0
            ORDER BY b.title
        """)
        available_books = cur.fetchall()
        
        return render_template('loans.html',
                             loans=loans,
                             page=page,
                             total_pages=total_pages,
                             status=status,
                             user=user,
                             today=today.strftime('%Y-%m-%d'),
                             due_date=due_date.strftime('%Y-%m-%d'),
                             available_books=available_books,
                             active_loans=[l for l in loans if l.get('return_date') is None and (l.get('due_date') and l.get('due_date') >= datetime.now().date())],
                             overdue_loans=[l for l in loans if l.get('return_date') is None and (l.get('due_date') and l.get('due_date') < datetime.now().date())],
                             returned_loans=[l for l in loans if l.get('return_date') is not None])
                             
    except Exception as e:
        logger.error(f"Error al cargar préstamos: {str(e)}", exc_info=True)
        flash('Error al cargar la lista de préstamos', 'error')
        # Get user information from session
        user = {
            'id': session.get('user_id'),
            'username': session.get('username'),
            'is_admin': session.get('is_admin', False)
        }
        
        return render_template('loans.html',
                            loans=[],
                            page=1,
                            total_pages=1,
                            status=status,
                            user=user,
                            active_loans=[],
                            overdue_loans=[],
                            returned_loans=[])
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para registrar un nuevo préstamo
@bp.route('/new', methods=['POST'])
@login_required
def new():
    try:
        # Get form data
        book_id = request.form.get('book_id')
        user_id = session.get('user_id')
        username = session.get('username')
        due_date = request.form.get('due_date')
        loan_date = request.form.get('loan_date')  # Get loan_date from form
        notes = request.form.get('notes', '')
        
        logger.info(f"Iniciando nuevo préstamo - Usuario: {username} (ID: {user_id}), Libro ID: {book_id}")
        logger.debug(f"Datos del formulario: {dict(request.form)}")
        
        # Validate required fields
        if not all([book_id, user_id, due_date, loan_date]):
            error_msg = 'Faltan campos obligatorios en la solicitud de préstamo'
            logger.warning(f"{error_msg} - Usuario: {username}, Datos: {dict(request.form)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 400
            flash(error_msg, 'error')
            return redirect(request.referrer or url_for('books.index'))
            
        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = get_cursor()
            
            # Verificar si el usuario está suspendido o baneado
            logger.debug(f"Verificando estado de suspensión para el usuario: {username}")
            cur.execute("""
                SELECT is_banned, suspension_type, 
                       COALESCE(suspension_until, '2000-01-01') as suspension_until
                FROM users 
                WHERE id = %s
            """, (user_id,))
            user_status = cur.fetchone()
            
            if not user_status:
                error_msg = 'Usuario no encontrado'
                logger.warning(f"{error_msg} - ID: {user_id}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False,
                        'message': error_msg
                    }), 400
                flash(error_msg, 'error')
                return redirect(request.referrer or url_for('books.index'))
                
            current_time = datetime.now()
            is_suspended = (
                user_status['is_banned'] or
                (user_status['suspension_type'] == 'temporary' and 
                 user_status['suspension_until'] > current_time) or
                user_status['suspension_type'] == 'permanent'
            )
            
            if is_suspended:
                error_msg = 'Su cuenta está suspendida. No puede realizar préstamos.'
                logger.warning(f"Usuario suspendido intentó hacer un préstamo - ID: {user_id}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False,
                        'message': error_msg,
                        'is_suspended': True
                    }), 403
                flash(error_msg, 'error')
                return redirect(request.referrer or url_for('books.index'))
            
            # Obtener información del libro
            logger.debug(f"Verificando disponibilidad del libro ID: {book_id}")
            cur.execute("""
                SELECT id, title, available_copies 
                FROM books 
                WHERE id = %s AND available_copies > 0
                FOR UPDATE
            """, (book_id,))
            book = cur.fetchone()
            
            if not book:
                error_msg = 'El libro no está disponible para préstamo'
                logger.warning(f"{error_msg} - Libro ID: {book_id}, Solicitado por: {username}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False,
                        'message': error_msg
                    }), 400
                flash(error_msg, 'error')
                return redirect(request.referrer or url_for('books.index'))
                
            # Verificar si el usuario ya tiene un préstamo activo de este libro
            logger.debug(f"Verificando préstamos activos para el usuario: {username}")
            cur.execute("""
                SELECT id, loan_date 
                FROM loans 
                WHERE book_id = %s AND user_id = %s AND return_date IS NULL
                LIMIT 1
            """, (book_id, user_id))
            
            existing_loan = cur.fetchone()
            if existing_loan:
                error_msg = f'Ya tienes un préstamo activo de este libro desde {existing_loan["loan_date"].strftime("%Y-%m-%d")}'
                logger.warning(f"{error_msg} - Usuario: {username}, Libro ID: {book_id}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False,
                        'message': error_msg
                    }), 400
                flash(error_msg, 'warning')
                return redirect(request.referrer or url_for('books.index'))
                
            # Insertar el préstamo
            logger.info(f"Registrando nuevo préstamo - Libro: {book['title']} (ID: {book_id}) para {username}")
            logger.debug(f"Datos del préstamo - Fecha préstamo: {loan_date}, Fecha devolución: {due_date}")
            
            try:
                conn = get_db_connection()
                cur = get_cursor()
                
                # Convert string dates to date objects
                try:
                    loan_date_obj = datetime.strptime(loan_date, '%Y-%m-%d').date()
                    due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                except ValueError as e:
                    error_msg = f'Formato de fecha inválido: {str(e)}'
                    logger.error(error_msg)
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({
                            'success': False,
                            'message': error_msg
                        }), 400
                    flash(error_msg, 'error')
                    return redirect(request.referrer or url_for('books.index'))
                
                cur.execute("""
                    INSERT INTO loans (book_id, user_id, loan_date, due_date)
                    VALUES (%s, %s, %s, %s)
                """, (book_id, user_id, loan_date_obj, due_date_obj))
                
                # Obtener el ID del préstamo recién creado
                loan_id = cur.lastrowid
                
                # Actualizar el contador de copias disponibles
                cur.execute("""
                    UPDATE books 
                    SET available_copies = available_copies - 1 
                    WHERE id = %s
                """, (book_id,))
                
                # Registrar la acción detallada
                action_description = (
                    f"Nuevo préstamo - "
                    f"Préstamo ID: {loan_id}, "
                    f"Libro: {book['title']} (ID: {book_id}), "
                    f"Usuario: {username} (ID: {user_id}), "
                    f"Fecha préstamo: {loan_date}, "
                    f"Fecha vencimiento: {due_date}"
                )
                
                # Insertar en user_actions (sin loan_id y book_id que no existen en la tabla)
                cur.execute("""
                    INSERT INTO user_actions 
                    (user_id, action_type, description, ip_address)
                    VALUES (%s, 'new_loan', %s, %s)
                """, (
                    user_id,
                    action_description,
                    request.remote_addr
                ))
                
                conn.commit()
                success_msg = f'Préstamo registrado exitosamente. ID: {loan_id}'
                logger.info(success_msg)
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': True,
                        'message': 'Préstamo registrado exitosamente',
                        'loan_id': loan_id
                    })
                    
                flash(success_msg, 'success')
                return redirect(url_for('loans.index'))
                
            except Exception as e:
                if 'conn' in locals():
                    conn.rollback()
                error_msg = f'Error al insertar el préstamo en la base de datos: {str(e)}'
                logger.error(error_msg, exc_info=True)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False,
                        'message': error_msg
                    }), 500
                flash(error_msg, 'error')
                return redirect(request.referrer or url_for('books.index'))
            
            finally:
                if 'cur' in locals() and cur:
                    cur.close()
                if 'conn' in locals() and conn:
                    conn.close()
                    
        except Exception as e:
            error_msg = f'Error inesperado al procesar la solicitud: {str(e)}'
            logger.error(error_msg, exc_info=True)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': 'Error inesperado al procesar la solicitud'
                }), 500
            flash(error_msg, 'error')
            return redirect(url_for('loans.new'))
            
    except Exception as e:
        error_msg = f'Error en el servidor: {str(e)}'
        logger.error(error_msg, exc_info=True)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'Error en el servidor'
            }), 500
        flash('Error en el servidor. Por favor, intente nuevamente.', 'error')
        return redirect(url_for('loans.new'))
    
    # Si es GET, redirigir al índice de préstamos
    return redirect(url_for('loans.index'))

# Ruta para registrar la devolución de un libro
@bp.route('/<int:loan_id>/return', methods=['POST'])
@login_required
@admin_required
def return_loan(loan_id):
    logger.info(f"Iniciando devolución de préstamo ID: {loan_id}")
    
    # Verificar si es una petición AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    try:
        conn = get_db_connection()
        cur = get_cursor()
        
        logger.debug(f"Buscando préstamo con ID: {loan_id}")
        
        # Verificar que el préstamo existe y no ha sido devuelto
        cur.execute("""
            SELECT l.*, b.id as book_id, b.title as book_title, 
                   u.username as user_username, u.id as user_id
            FROM loans l
            JOIN books b ON l.book_id = b.id
            JOIN users u ON l.user_id = u.id
            WHERE l.id = %s AND l.return_date IS NULL
            FOR UPDATE
        """, (loan_id,))
        
        loan = cur.fetchone()
        
        if not loan:
            error_msg = f'Préstamo no encontrado o ya fue devuelto (ID: {loan_id})'
            logger.warning(error_msg)
            if is_ajax:
                return jsonify({'success': False, 'message': error_msg}), 404
            flash(error_msg, 'error')
            return redirect(url_for('loans.index'))
        
        logger.info(f"Registrando devolución del préstamo: {loan}")
            
        # Registrar la devolución
        cur.execute("""
            UPDATE loans 
            SET return_date = CURDATE() 
            WHERE id = %s
        """, (loan_id,))
        
        # Actualizar contador de copias disponibles
        cur.execute("""
            UPDATE books 
            SET available_copies = available_copies + 1 
            WHERE id = %s
        """, (loan['book_id'],))
        
        # Obtener el nuevo contador de copias disponibles
        cur.execute("SELECT available_copies FROM books WHERE id = %s", (loan['book_id'],))
        updated_book = cur.fetchone()
        
        # Registrar la acción
        action_description = (
            f"Devolución registrada - Préstamo ID: {loan_id}, "
            f"Libro: {loan['book_title']} (ID: {loan['book_id']}), "
            f"Usuario: {loan['user_username']} (ID: {loan['user_id']}), "
            f"Copias disponibles: {updated_book['available_copies'] if updated_book else 'N/A'}"
        )
        
        cur.execute("""
            INSERT INTO user_actions (user_id, action_type, description, ip_address)
            VALUES (%s, 'return_loan', %s, %s)
        """, (session['user_id'], action_description, request.remote_addr))
        
        conn.commit()
        
        success_msg = f'Devolución registrada exitosamente. Libro: {loan["book_title"]}'
        logger.info(success_msg)
        
        if is_ajax:
            return jsonify({
                'success': True,
                'message': success_msg,
                'book_id': loan['book_id'],
                'available_copies': updated_book['available_copies'] if updated_book else None
            })
            
        flash(success_msg, 'success')
        
    except Exception as e:
        error_msg = f'Error al registrar devolución: {str(e)}'
        logger.error(error_msg, exc_info=True)
        
        if 'conn' in locals():
            conn.rollback()
            
        if is_ajax:
            return jsonify({'success': False, 'message': error_msg}), 500
            
        flash(error_msg, 'error')
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
    
    if is_ajax:
        return jsonify({'success': False, 'message': 'Error inesperado'}), 500
        
    return redirect(url_for('loans.index'))

# Ruta para renovar un préstamo
@bp.route('/<int:loan_id>/renew', methods=['POST'])
@login_required
def renew_loan(loan_id):
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        # Verificar que el préstamo existe, no ha sido devuelto y pertenece al usuario (o es admin)
        query = """
            SELECT l.*, b.id as book_id
            FROM loans l
            JOIN books b ON l.book_id = b.id
            WHERE l.id = %s 
            AND l.return_date IS NULL
        """
        
        params = [loan_id]
        
        # Si no es administrador, verificar que el préstamo sea del usuario
        if not session.get('is_admin'):
            query += " AND l.user_id = %s"
            params.append(session['user_id'])
            
        query += " FOR UPDATE"
        
        cur.execute(query, params)
        loan = cur.fetchone()
        
        if not loan:
            flash('Préstamo no encontrado, ya fue devuelto o no tienes permiso para renovarlo', 'error')
            return redirect(url_for('loans.index'))
            
        # Calcular nueva fecha de vencimiento (30 días desde hoy o desde la fecha de vencimiento, la que sea mayor)
        new_due_date = max(
            datetime.now().date() + timedelta(days=30),
            loan['due_date'] + timedelta(days=30)
        )
        
        # Actualizar la fecha de vencimiento
        cur.execute("""
            UPDATE loans 
            SET due_date = %s,
                renewal_count = renewal_count + 1
            WHERE id = %s
        """, (new_due_date, loan_id))
        
        # Registrar la acción
        cur.execute("""
            INSERT INTO user_actions (user_id, action_type, description, ip_address)
            VALUES (%s, 'renew_loan', %s, %s)
        """, (session['user_id'], 
              f'Préstamo renovado - ID: {loan_id}, Nueva fecha: {new_due_date}', 
              request.remote_addr))
        
        conn.commit()
        flash('Préstamo renovado exitosamente', 'success')
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error al renovar préstamo: {str(e)}", exc_info=True)
        flash('Error al renovar el préstamo', 'error')
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
    
    return redirect(url_for('loans.index'))
