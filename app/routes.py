from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from .db import get_db_connection, get_cursor
from .decorators import login_required, admin_required
from datetime import datetime, timedelta
import json
import logging

# Configurar logging
logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__, url_prefix='')

# Ruta principal - Redirige al dashboard
@bp.route('/')
@login_required
def index():
    return redirect(url_for('main.dashboard'))

# Ruta del dashboard
@bp.route('/dashboard')
@login_required
def dashboard():
    try:
        conn = get_db_connection()
        cur = get_cursor()
        # Obtener estadísticas
        cur.execute("SELECT COUNT(*) as total_books FROM books")
        total_books = cur.fetchone()['total_books']
        
        cur.execute("""
            SELECT COUNT(*) as available_books 
            FROM books 
            WHERE available_copies > 0
        """)
        available_books = cur.fetchone()['available_books']
        
        cur.execute("""
            SELECT COUNT(*) as active_loans 
            FROM loans 
            WHERE return_date IS NULL
        """)
        active_loans = cur.fetchone()['active_loans']
        
        # Obtener préstamos recientes
        cur.execute("""
            SELECT l.*, b.title as book_title, u.username as user_name 
            FROM loans l
            JOIN books b ON l.book_id = b.id
            JOIN users u ON l.user_id = u.id
            ORDER BY l.loan_date DESC 
            LIMIT 5
        """)
        recent_loans = cur.fetchall()
        
        # Obtener libros más populares
        cur.execute("""
            SELECT b.*, COUNT(l.id) as loan_count
            FROM books b
            LEFT JOIN loans l ON b.id = l.book_id
            GROUP BY b.id
            ORDER BY loan_count DESC
            LIMIT 5
        """)
        popular_books = cur.fetchall()
        
        # Obtener próximas devoluciones (préstamos no devueltos con fecha de vencimiento próxima)
        cur.execute("""
            SELECT COUNT(*) as upcoming_returns 
            FROM loans 
            WHERE return_date IS NULL 
            AND due_date <= DATE_ADD(CURDATE(), INTERVAL 7 DAY)
        """)
        upcoming_returns = cur.fetchone()['upcoming_returns']
        
        return render_template('dashboard.html', 
                           total_books=total_books,
                           available_books=available_books,
                           active_loans=active_loans,
                           recent_loans=recent_loans,
                           popular_books=popular_books,
                           upcoming_returns=upcoming_returns)
        
    except Exception as e:
        logger.error(f"Error en la ruta del dashboard: {str(e)}", exc_info=True)
        flash('Error al cargar el dashboard. Por favor, intente nuevamente.', 'error')
        return render_template('dashboard.html', 
                            total_books=0,
                            available_books=0,
                            active_loans=0,
                            recent_loans=[],
                            popular_books=[],
                            upcoming_returns=0)
    finally:
        if 'cur' in locals() and cur is not None:
            try:
                cur.close()
            except Exception as e:
                logger.error(f"Error al cerrar el cursor: {e}")
        # La conexión se cierra automáticamente cuando termina la solicitud

class Pagination:
    def __init__(self, items, page, per_page, total):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = (total + per_page - 1) // per_page if total > 0 else 1
        self.has_prev = page > 1
        self.has_next = page < self.pages
        self.prev_num = page - 1 if page > 1 else None
        self.next_num = page + 1 if page < self.pages else None
    
    def iter_pages(self, left_edge=2, left_current=3, right_current=4, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if (num <= left_edge or 
                (num > self.page - left_current - 1 and num < self.page + right_current) or 
                num > self.pages - right_edge):
                if last and num - last > 1:
                    yield None
                yield num
                last = num

# Ruta para mostrar el catálogo de libros
@bp.route('/books')
def books():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    search = request.args.get('search', '')
    genre = request.args.get('genre', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Número de libros por página
    
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        # Obtener géneros para el filtro
        cur.execute("SELECT * FROM genres ORDER BY name")
        genres = cur.fetchall()
        
        # Consulta base para traer SIEMPRE el número actualizado de copias
        base_query = """
            FROM books b
            LEFT JOIN genres g ON b.genre_id = g.id
            WHERE 1=1
        """
        count_query = "SELECT COUNT(*) as total " + base_query
        data_query = """
            SELECT b.*, g.name as genre_name,
                   (SELECT COUNT(*) FROM loans WHERE book_id = b.id AND return_date IS NULL) as active_loans
            """ + base_query
        params = []
        if search:
            search_condition = " AND (b.title LIKE %s OR b.author LIKE %s OR b.isbn = %s)"
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search])
            count_query += search_condition
            data_query += search_condition
        if genre and genre.isdigit():
            genre_condition = " AND b.genre_id = %s"
            params.append(genre)
            count_query += genre_condition
            data_query += genre_condition
        # Obtener el total de registros
        cur.execute(count_query, tuple(params))
        total = cur.fetchone()['total']
        if total == 0:
            pagination = Pagination([], page, per_page, 0)
        else:
            data_query += " ORDER BY b.title"
            data_query += " LIMIT %s OFFSET %s"
            params.extend([per_page, (page - 1) * per_page])
            cur.execute(data_query, tuple(params))
            books = cur.fetchall()
            pagination = Pagination(books, page, per_page, total)
        # Obtener usuario actual
        cur.execute('SELECT id, username, full_name, email FROM users WHERE id = %s', (session['user_id'],))
        user = cur.fetchone()
        return render_template('books.html',
                              books=pagination,
                              genres=genres,
                              search=search,
                              selected_genre=genre,
                              user=user,
                              current_user=user)
    except Exception as e:
        logger.error(f"Error en la ruta de libros: {str(e)}", exc_info=True)
        flash('Error al cargar los libros. Por favor, intente nuevamente.', 'error')
        user = None
        if 'user_id' in session:
            cur.execute('SELECT id, username, full_name, email FROM users WHERE id = %s', (session['user_id'],))
            user = cur.fetchone()
        return render_template('books.html',
                               books=Pagination([], 1, 10, 0),
                               genres=[],
                               search=search,
                               selected_genre=genre,
                               user=user,
                               current_user=user)
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para mostrar los préstamos
@bp.route('/loans')
@login_required
def loans():
    # Obtener parámetros de filtrado
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        is_admin = session.get('is_admin', False)
        user_id = session.get('user_id')
        active_loans = []
        overdue_loans = []
        returned_loans = []
        search_conditions = []
        params = []
        if search:
            search_conditions.append("""
                (b.title LIKE %s OR 
                b.author LIKE %s OR 
                u.username LIKE %s OR 
                u.full_name LIKE %s)
            """)
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term, search_term])
        # Si no es admin, solo mostrar los préstamos del usuario actual
        if not is_admin:
            search_conditions.append("l.user_id = %s")
            params.append(user_id)
        base_query = """
            SELECT l.*, b.title as book_title, b.available_copies,
                   u.username as user_name, u.full_name as user_full_name,
                   DATEDIFF(l.due_date, CURDATE()) as days_remaining,
                   l.due_date < CURDATE() as is_overdue,
                   b.author as book_author, b.isbn
            FROM loans l
            JOIN books b ON l.book_id = b.id
            JOIN users u ON l.user_id = u.id
            WHERE 1=1
        """
        if search_conditions:
            base_query += " AND " + " AND ".join(search_conditions)
        # Consulta para préstamos activos y vencidos
        active_query = base_query + " AND l.return_date IS NULL ORDER BY l.due_date ASC"
        cur.execute(active_query, params)
        all_loans = cur.fetchall()
        for loan in all_loans:
            if loan['is_overdue']:
                overdue_loans.append(loan)
            else:
                active_loans.append(loan)
        # Consulta para préstamos devueltos
        returned_query = base_query + " AND l.return_date IS NOT NULL ORDER BY l.return_date DESC"
        cur.execute(returned_query, params)
        returned_loans = cur.fetchall()
        # Aplicar filtro de estado si está presente
        if status_filter == 'active':
            returned_loans = []
            overdue_loans = []
        elif status_filter == 'overdue':
            active_loans = []
            returned_loans = []
        elif status_filter == 'returned':
            active_loans = []
            overdue_loans = []
        return render_template(
            'loans.html',
            active_loans=active_loans,
            overdue_loans=overdue_loans,
            returned_loans=returned_loans,
            search=search,
            status_filter=status_filter,
            is_admin=is_admin
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        current_app.logger.error(f'Error al obtener préstamos: {str(e)}\n{error_details}')
        
        # Log the query that was being executed
        current_app.logger.error(f'Query: {active_query if "active_query" in locals() else "No query generated"}')
        current_app.logger.error(f'Params: {params if "params" in locals() else "No params"}')
        
        # If in development, show more details
        if current_app.config.get('ENV') == 'development':
            flash(f'Error al cargar los préstamos: {str(e)}', 'error')
        else:
            flash('Ocurrió un error al cargar los préstamos. Por favor, intente nuevamente.', 'error')
            
        # Return empty results instead of redirecting to show the error message
        return render_template(
            'loans.html',
            active_loans=[],
            overdue_loans=[],
            returned_loans=[],
            search=search if 'search' in locals() else '',
            status_filter=status_filter if 'status_filter' in locals() else '',
            is_admin=is_admin if 'is_admin' in locals() else False,
            error=str(e)
        )
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para registrar un nuevo préstamo
@bp.route('/loans/new', methods=['POST'])
@login_required
def new_loan():
    if 'user_id' not in session:
        flash('Debes iniciar sesión para realizar esta acción', 'error')
        return redirect(url_for('auth.login'))
    
    book_id = request.form.get('book_id')
    due_date = request.form.get('due_date')
    
    # Si es admin, puede especificar el usuario, si no, usa el usuario actual
    is_admin = session.get('is_admin', False)
    # Solo los administradores pueden asignar el user_id desde el formulario
    if is_admin:
        user_id = request.form.get('user_id')
        if not user_id:
            flash('Debes seleccionar un usuario para el préstamo', 'error')
            return redirect(url_for('main.loans'))
    else:
        # Forzamos el user_id al de la sesión para usuarios normales
        user_id = str(session['user_id'])
    
    # Seguridad extra: si por alguna razón el user_id no es válido
    if not user_id:
        flash('No se pudo identificar el usuario para el préstamo', 'error')
        return redirect(url_for('main.loans'))
    
    if not all([book_id, due_date]):
        flash('Todos los campos son obligatorios', 'error')
        return redirect(url_for('main.loans'))
    
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        # Validar existencia y disponibilidad de copias del libro
        cur.execute("SELECT id, available_copies, title FROM books WHERE id = %s FOR UPDATE", (book_id,))
        book = cur.fetchone()
        if not book:
            flash('El libro seleccionado no existe.', 'error')
            return redirect(url_for('main.books'))
        if book['available_copies'] <= 0:
            flash('No hay ejemplares disponibles para este libro.', 'error')
            return redirect(url_for('main.books'))

        # Verificar si el usuario ya tiene un préstamo activo de este libro
        cur.execute("""
            SELECT id FROM loans 
            WHERE user_id = %s AND book_id = %s AND return_date IS NULL
            LIMIT 1
        """, (user_id, book_id))
        if cur.fetchone():
            flash('Ya tienes un préstamo activo de este libro', 'error')
            return redirect(url_for('main.books'))

        # Registrar el préstamo
        cur.execute("""
            INSERT INTO loans (user_id, book_id, loan_date, due_date)
            VALUES (%s, %s, CURDATE(), %s)
        """, (user_id, book_id, due_date))

        # Descontar una copia disponible
        cur.execute("""
            UPDATE books 
            SET available_copies = available_copies - 1 
            WHERE id = %s AND available_copies > 0
        """, (book_id,))

        # Registrar movimiento en book_movements (préstamo)
        cur.execute("""
            INSERT INTO book_movements (book_id, user_id, movement_type, quantity, description, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (book_id, user_id, 'prestamo', 1, 'Préstamo registrado desde el sistema'))

        # Registrar la acción en el log
        current_app.logger.info(
            f"Nuevo préstamo - Libro ID: {book_id}, Usuario ID: {user_id}, "
            f"Título: {book['title']}, Fecha de vencimiento: {due_date}"
        )

        conn.commit()
        flash('Préstamo registrado exitosamente', 'success')

    except Exception as e:
        conn.rollback()
        current_app.logger.error(f'Error al registrar préstamo: {str(e)}')
        flash('Ocurrió un error al registrar el préstamo. Por favor, intente nuevamente.', 'error')
        return redirect(url_for('main.books'))

    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
    
    return redirect(url_for('main.loans'))

# Ruta para renovar un préstamo
@bp.route('/loans/renew/<int:loan_id>', methods=['POST'])
@login_required
def renew_loan(loan_id):
    if not session.get('is_admin', False):
        return jsonify({'success': False, 'message': 'No tienes permiso para realizar esta acción'}), 403
    
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        # Verificar si el préstamo existe y está activo
        cur.execute("""
            SELECT l.*, b.available_copies 
            FROM loans l
            JOIN books b ON l.book_id = b.id
            WHERE l.id = %s AND l.return_date IS NULL
        """, (loan_id,))
        
        loan = cur.fetchone()
        
        if not loan:
            return jsonify({'success': False, 'message': 'Préstamo no encontrado o ya fue devuelto'}), 404
        
        # Calcular la nueva fecha de vencimiento (15 días a partir de hoy)
        new_due_date = datetime.now().date() + timedelta(days=15)
        
        # Actualizar la fecha de vencimiento del préstamo
        cur.execute("""
            UPDATE loans 
            SET due_date = %s, 
                renewal_count = COALESCE(renewal_count, 0) + 1,
                last_renewal_date = CURDATE()
            WHERE id = %s
        """, (new_due_date, loan_id))
        
        conn.commit()
        return jsonify({
            'success': True,
            'message': 'Préstamo renovado exitosamente',
            'new_due_date': new_due_date.strftime('%d/%m/%Y')
        })
        
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f'Error al renovar préstamo: {str(e)}')
        return jsonify({'success': False, 'message': 'Error al renovar el préstamo'}), 500
        
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para registrar la devolución de un libro
@bp.route('/loans/return/<int:loan_id>', methods=['POST'])
@login_required
def return_loan(loan_id):
    if not session.get('is_admin', False):
        return jsonify({'success': False, 'message': 'No tienes permiso para realizar esta acción'}), 403
    
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        # Obtener el préstamo y el libro asociado
        cur.execute("""
            SELECT l.*, b.id as book_id 
            FROM loans l
            JOIN books b ON l.book_id = b.id
            WHERE l.id = %s AND l.return_date IS NULL
        """, (loan_id,))
        
        loan = cur.fetchone()
        
        if not loan:
            return jsonify({'success': False, 'message': 'Préstamo no encontrado o ya fue devuelto'}), 404
        
        # Registrar la devolución
        cur.execute("""
            UPDATE loans 
            SET return_date = CURDATE() 
            WHERE id = %s
        """, (loan_id,))
        
        # Actualizar el contador de copias disponibles
        cur.execute("""
            UPDATE books 
            SET available_copies = available_copies + 1 
            WHERE id = %s
        """, (loan['book_id'],))

        # Registrar movimiento en book_movements (devolución)
        cur.execute("""
            INSERT INTO book_movements (book_id, user_id, movement_type, quantity, description, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (loan['book_id'], loan['user_id'], 'devolucion', 1, 'Devolución registrada desde el sistema'))

        # Registrar el historial de devolución
        cur.execute("""
            INSERT INTO loan_history (
                loan_id, user_id, book_id, action_type, action_date, notes
            )
            SELECT 
                id, user_id, book_id, 'return', NOW(), 
                CONCAT('Devolución registrada. Fecha de préstamo: ', loan_date, ', Fecha de vencimiento: ', due_date)
            FROM loans 
            WHERE id = %s
        """, (loan_id,))

        conn.commit()
        return jsonify({
            'success': True,
            'message': 'Devolución registrada exitosamente',
            'return_date': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        })
        
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f'Error al registrar devolución: {str(e)}')
        return jsonify({'success': False, 'message': 'Error al registrar la devolución'}), 500
        
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para buscar usuarios (usada en autocompletado)
@bp.route('/api/search_users')
def search_users():
    if 'user_id' not in session or not session.get('is_admin', False):
        return jsonify({'error': 'No autorizado'}), 403
    
    query = request.args.get('q', '')
    
    if not query or len(query) < 2:
        return jsonify([])
    
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        search_term = f"%{query}%"
        cur.execute("""
            SELECT id, username, full_name, email 
            FROM users 
            WHERE username LIKE %s OR full_name LIKE %s OR email LIKE %s
            LIMIT 10
        """, (search_term, search_term, search_term))
        
        users = [{
            'id': user['id'],
            'text': f"{user['username']} - {user.get('full_name', '')} ({user.get('email', '')})"
        } for user in cur.fetchall()]
        
        return jsonify(users)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para obtener el historial de movimientos de un libro
@bp.route('/api/books/<int:book_id>/movements', methods=['GET'])
@login_required
def get_book_movements(book_id):
    conn = get_db_connection()
    cur = get_cursor()
    try:
        cur.execute('''
            SELECT bm.id, bm.book_id, bm.user_id, u.username, bm.movement_type, bm.quantity, bm.created_at, bm.description
            FROM book_movements bm
            JOIN users u ON bm.user_id = u.id
            WHERE bm.book_id = %s
            ORDER BY bm.created_at DESC
        ''', (book_id,))
        movements = cur.fetchall()
        # Serializar created_at a string legible
        for mv in movements:
            if isinstance(mv['created_at'], datetime):
                mv['created_at'] = mv['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify({'success': True, 'movements': movements})
    except Exception as e:
        current_app.logger.error(f'Error al obtener historial de movimientos: {str(e)}')
        return jsonify({'success': False, 'message': 'Error al obtener historial de movimientos'}), 500
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para agregar un nuevo libro
@bp.route('/books/add', methods=['POST'])
@login_required
def add_book():
    if not session.get('is_admin', False):
        flash('No tienes permiso para realizar esta acción', 'error')
        return redirect(url_for('main.books'))
    
    try:
        # Obtener datos del formulario
        title = request.form.get('title')
        author = request.form.get('author')
        isbn = request.form.get('isbn')
        publication_year = request.form.get('publication_year')
        publisher = request.form.get('publisher')
        genre_id = request.form.get('genre_id')
        total_copies = int(request.form.get('total_copies', 1))
        description = request.form.get('description', '')
        
        # Validar campos requeridos
        if not all([title, author]):
            flash('Título y autor son campos requeridos', 'error')
            return redirect(url_for('main.books'))
        
        # Insertar el nuevo libro en la base de datos
        conn = get_db_connection()
        cur = get_cursor()
        
        query = """
            INSERT INTO books 
            (title, author, isbn, publication_year, publisher, genre_id, total_copies, available_copies, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            title, 
            author, 
            isbn if isbn else None,
            int(publication_year) if publication_year and publication_year.isdigit() else None,
            publisher if publisher else None,
            int(genre_id) if genre_id and genre_id.isdigit() else None,
            max(1, total_copies),  # Asegurar al menos 1 copia
            max(1, total_copies),  # Copias disponibles igual al total
            description if description else None
        )
        
        cur.execute(query, params)
        conn.commit()
        
        flash('Libro agregado exitosamente', 'success')
        return redirect(url_for('main.books'))
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error al agregar libro: {str(e)}")
        flash('Error al agregar el libro. Por favor, intente nuevamente.', 'error')
        return redirect(url_for('main.books'))
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para buscar libros (usada en autocompletado)
@bp.route('/api/search_books')
def search_books():
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 403
    
    query = request.args.get('q', '')
    
    if not query or len(query) < 2:
        return jsonify([])
    
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        search_term = f"%{query}%"
        cur.execute("""
            SELECT id, title, author, isbn 
            FROM books 
            WHERE (title LIKE %s OR author LIKE %s OR isbn = %s)
            AND available_copies > 0
            LIMIT 10
        """, (search_term, search_term, query))
        
        books = [{
            'id': book['id'],
            'text': f"{book['title']} - {book['author']} (ISBN: {book.get('isbn', 'N/A')})"
        } for book in cur.fetchall()]
        
        return jsonify(books)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
