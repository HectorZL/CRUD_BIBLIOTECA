from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from .db import get_db_connection, get_cursor
from datetime import datetime, timedelta
import json
import logging
from functools import wraps

# Configurar logging
logger = logging.getLogger(__name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

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
        
        # Construir la consulta base
        base_query = """
            FROM books b
            LEFT JOIN genres g ON b.genre_id = g.id
            WHERE 1=1
        """
        
        # Construir la consulta de conteo
        count_query = "SELECT COUNT(*) as total " + base_query
        
        # Construir la consulta de datos
        data_query = """
            SELECT b.*, g.name as genre_name, 
                   (SELECT COUNT(*) FROM loans WHERE book_id = b.id AND return_date IS NULL) as active_loans
            """ + base_query
        
        # Añadir filtros
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
        
        # Crear objeto de paginación vacío si no hay resultados
        if total == 0:
            pagination = Pagination([], page, per_page, 0)
        else:
            # Añadir orden y paginación
            data_query += " ORDER BY b.title"
            data_query += " LIMIT %s OFFSET %s"
            params.extend([per_page, (page - 1) * per_page])
            
            # Ejecutar consulta de datos
            cur.execute(data_query, tuple(params))
            books = cur.fetchall()
            
            # Crear objeto de paginación
            pagination = Pagination(books, page, per_page, total)
        
        return render_template('books.html', 
                             books=pagination, 
                             genres=genres,
                             search=search,
                             selected_genre=genre)
    except Exception as e:
        logger.error(f"Error en la ruta de libros: {str(e)}", exc_info=True)
        flash('Error al cargar los libros. Por favor, intente nuevamente.', 'error')
        return render_template('books.html', 
                           books=Pagination([], 1, 10, 0),
                           genres=[],
                           search=search,
                           selected_genre=genre)
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para mostrar los préstamos
@bp.route('/loans')
def loans():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    tab = request.args.get('tab', 'active')
    
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        # Obtener préstamos activos
        active_loans = []
        overdue_loans = []
        returned_loans = []
        
        if tab in ['active', 'all']:
            cur.execute("""
                SELECT l.*, b.title as book_title, u.username as user_name 
                FROM loans l
                JOIN books b ON l.book_id = b.id
                JOIN users u ON l.user_id = u.id
                WHERE l.return_date IS NULL
                ORDER BY l.due_date
            """)
            active_loans = cur.fetchall()
            
            # Identificar préstamos vencidos
            today = datetime.now().date()
            for loan in active_loans:
                if loan['due_date'] < today:
                    overdue_loans.append(loan)
            
            # Remover préstamos vencidos de la lista de activos
            active_loans = [loan for loan in active_loans if loan['due_date'] >= today]
        
        if tab in ['overdue', 'all'] and tab != 'active':
            cur.execute("""
                SELECT l.*, b.title as book_title, u.username as user_name 
                FROM loans l
                JOIN books b ON l.book_id = b.id
                JOIN users u ON l.user_id = u.id
                WHERE l.return_date IS NULL AND l.due_date < CURDATE()
                ORDER BY l.due_date
            """)
            overdue_loans = cur.fetchall()
        
        if tab in ['returned', 'all']:
            cur.execute("""
                SELECT l.*, b.title as book_title, u.username as user_name 
                FROM loans l
                JOIN books b ON l.book_id = b.id
                JOIN users u ON l.user_id = u.id
                WHERE l.return_date IS NOT NULL
                ORDER BY l.return_date DESC
                LIMIT 50
            """)
            returned_loans = cur.fetchall()
        
        return render_template('loans.html',
                             active_loans=active_loans,
                             overdue_loans=overdue_loans,
                             returned_loans=returned_loans,
                             active_tab=tab)
    except Exception as e:
        flash(f'Error al cargar los préstamos: {str(e)}', 'error')
        return render_template('loans.html', 
                             active_loans=[], 
                             overdue_loans=[], 
                             returned_loans=[])
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para registrar un nuevo préstamo
@bp.route('/loans/new', methods=['POST'])
def new_loan():
    if 'user_id' not in session or not session.get('is_admin', False):
        flash('No tienes permiso para realizar esta acción', 'error')
        return redirect(url_for('main.loans'))
    
    book_id = request.form.get('book_id')
    user_id = request.form.get('user_id')
    due_date = request.form.get('due_date')
    
    if not all([book_id, user_id, due_date]):
        flash('Todos los campos son obligatorios', 'error')
        return redirect(url_for('main.loans'))
    
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        # Verificar si el libro está disponible
        cur.execute("SELECT available_copies FROM books WHERE id = %s", (book_id,))
        book = cur.fetchone()
        
        if not book or book['available_copies'] <= 0:
            flash('El libro no está disponible para préstamo', 'error')
            return redirect(url_for('main.loans'))
        
        # Crear el préstamo
        cur.execute("""
            INSERT INTO loans (user_id, book_id, loan_date, due_date)
            VALUES (%s, %s, CURDATE(), %s)
        """, (user_id, book_id, due_date))
        
        # Actualizar el contador de copias disponibles
        cur.execute("""
            UPDATE books 
            SET available_copies = available_copies - 1 
            WHERE id = %s
        """, (book_id,))
        
        conn.commit()
        flash('Préstamo registrado exitosamente', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error al registrar el préstamo: {str(e)}', 'error')
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
    
    return redirect(url_for('main.loans'))

# Ruta para registrar la devolución de un libro
@bp.route('/loans/return/<int:loan_id>', methods=['POST'])
def return_loan(loan_id):
    if 'user_id' not in session or not session.get('is_admin', False):
        flash('No tienes permiso para realizar esta acción', 'error')
        return redirect(url_for('main.loans'))
    
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
            flash('Préstamo no encontrado o ya fue devuelto', 'error')
            return redirect(url_for('main.loans'))
        
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
        
        conn.commit()
        flash('Devolución registrada exitosamente', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error al registrar la devolución: {str(e)}', 'error')
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
    
    return redirect(url_for('main.loans'))

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
