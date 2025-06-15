from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from ..db import get_db_connection, get_cursor
from ..decorators import login_required, admin_required
from datetime import datetime
import logging
import sys

# Configure logging to show output in console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# Create blueprint
bp = Blueprint('books', __name__, url_prefix='/books')

# Configure logging
logger = logging.getLogger(__name__)

# Ruta para mostrar el catálogo de libros
@bp.route('/')
@login_required
def index():
    print("\n=== Starting books.index() ===")
    page = request.args.get('page', 1, type=int)
    per_page = 10
    search = request.args.get('search', '')
    
    print(f"Connecting to database...")
    conn = get_db_connection()
    print(f"Database connection: {conn}")
    
    cur = get_cursor()
    print(f"Database cursor: {cur}")
    
    try:
        # Test database connection
        print("Testing database connection...")
        cur.execute("SELECT DATABASE() as db")
        db_name = cur.fetchone()['db']
        print(f"Connected to database: {db_name}")
        
        # Check if books table exists
        cur.execute("SHOW TABLES LIKE 'books'")
        tables = cur.fetchall()
        print(f"Books table exists: {len(tables) > 0}")
        
        # Count total books in database
        cur.execute("SELECT COUNT(*) as count FROM books")
        count = cur.fetchone()['count']
        print(f"Total books in database: {count}")
        
        if count == 0:
            print("WARNING: No books found in the database!")
            print("This could be why no books are displaying.")
            
            # Try to get some sample data to see what's in the database
            print("\nChecking for any tables with data...")
            cur.execute("SHOW TABLES")
            all_tables = cur.fetchall()
            for table in all_tables:
                table_name = table[f'Tables_in_{db_name}']
                cur.execute(f"SELECT COUNT(*) as c FROM `{table_name}`")
                count = cur.fetchone()['c']
                print(f"Table: {table_name} - Rows: {count}")
        # Build search query with genre name
        logger.info("Building search query...")
        query = """
            SELECT b.*, 
                   g.name as genre_name,
                   (SELECT COUNT(*) FROM loans l WHERE l.book_id = b.id AND l.return_date IS NULL) as borrowed_copies
            FROM books b
            LEFT JOIN genres g ON b.genre_id = g.id
            WHERE 1=1
        """
        logger.debug(f"Base query: {query}")
        
        # Get all books for debugging
        logger.info("Fetching all books for debugging...")
        cur.execute("SELECT * FROM books LIMIT 5")
        sample_books = cur.fetchall()
        logger.info(f"Sample books from database (first 5): {sample_books}")
        
        logger.info(f"Initial query: {query}")
        params = []
        
        if search:
            query += " AND (b.title LIKE %s OR b.author LIKE %s OR b.isbn LIKE %s)"
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term])
        
        # Contar total de resultados
        count_query = f"SELECT COUNT(*) as total FROM ({query}) as subquery"
        cur.execute(count_query, params)
        total = cur.fetchone()['total']
        
        # Añadir ordenación y paginación
        query += " ORDER BY b.title LIMIT %s OFFSET %s"
        offset = (page - 1) * per_page
        params.extend([per_page, offset])
        
        # Execute main query
        logger.info("Executing main query with pagination...")
        logger.debug(f"Final query: {query}")
        logger.debug(f"Query parameters: {params}")
        
        try:
            # Execute count query first with the same conditions as the main query
            count_query = """
                SELECT COUNT(*) as total 
                FROM books b
                LEFT JOIN genres g ON b.genre_id = g.id
                WHERE 1=1
            """
            if search:
                count_query += " AND (b.title LIKE %s OR b.author LIKE %s OR b.isbn LIKE %s)"
                
            logger.debug(f"Executing count query: {count_query}")
            cur.execute(count_query, params[:-2] if search else [])  # Remove LIMIT and OFFSET from params
            total = cur.fetchone()['total']
            logger.info(f"Total books matching criteria: {total}")
            
            # Execute main query
            logger.info("Executing paginated query...")
            cur.execute(query, params)
            books = cur.fetchall()
            
            logger.info(f"Successfully retrieved {len(books)} books (page {page} of {((total + per_page - 1) // per_page)})")
            
            if not books:
                logger.warning("No books found matching the criteria")
            else:
                # Log first few books for debugging
                logger.info(f"Sample books (first 3 of {len(books)}):")
                for i, book in enumerate(books[:3]):
                    logger.info(f"  Book {i+1}: ID={book.get('id')}, Title='{book.get('title')}', Author='{book.get('author')}'")
                    
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}", exc_info=True)
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
        
        # Calcular páginas para la paginación
        total_pages = (total + per_page - 1) // per_page
        logger.debug(f"Total pages: {total_pages}, Total books: {total}")
        
        # Crear un objeto de paginación compatible con el template
        class Pagination:
            def __init__(self, items, page, per_page, total):
                self.items = items
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = (total + per_page - 1) // per_page
                self.prev_num = page - 1 if page > 1 else None
                self.next_num = page + 1 if page < self.pages else None
                self.has_prev = page > 1
                self.has_next = page < self.pages
                
            def iter_pages(self, left_edge=2, left_current=2, right_current=4, right_edge=2):
                last = 0
                for num in range(1, self.pages + 1):
                    if (num <= left_edge or 
                        (num > self.page - left_current - 1 and 
                         num < self.page + right_current) or 
                        num > self.pages - right_edge):
                        if last + 1 != num:
                            yield None
                        yield num
                        last = num
        
        pagination = Pagination(books, page, per_page, total)
        
        # Get user information from session
        user = {
            'id': session.get('user_id'),
            'username': session.get('username'),
            'is_admin': session.get('is_admin', False)
        }
        
        # Get current year for publication year max value
        current_year = datetime.now().year
        now = datetime.now()  # Add this line to include current datetime in the template
        
        # Generate CSRF token
        from flask_wtf.csrf import generate_csrf
        
        return render_template('books.html',
                             books=pagination,
                             search=search,
                             user=user,
                             current_year=current_year)
                             
    except Exception as e:
        logger.error(f"Error al cargar libros: {str(e)}", exc_info=True)
        flash('Error al cargar la lista de libros', 'error')
        # Create an empty pagination object for error case
        class Pagination:
            def __init__(self):
                self.items = []
                self.page = 1
                self.per_page = 10
                self.total = 0
                self.pages = 1
                self.prev_num = None
                self.next_num = None
                self.has_prev = False
                self.has_next = False
                
            def iter_pages(self, *args, **kwargs):
                return []
        
        # Get user information from session
        user = {
            'id': session.get('user_id'),
            'username': session.get('username'),
            'is_admin': session.get('is_admin', False)
        }
        
        return render_template('books.html', 
                            books=Pagination(), 
                            search=search,
                            user=user)
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para ver detalles de un libro
@bp.route('/<int:book_id>')
@login_required
def view(book_id):
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        # Obtener información del libro
        cur.execute("""
            SELECT b.*, 
                   (SELECT COUNT(*) FROM loans l WHERE l.book_id = b.id AND l.return_date IS NULL) as borrowed_copies
            FROM books b 
            WHERE b.id = %s
        """, (book_id,))
        
        book = cur.fetchone()
        
        if not book:
            flash('Libro no encontrado', 'error')
            return redirect(url_for('books.index'))
            
        # Obtener historial de préstamos
        cur.execute("""
            SELECT l.*, u.username, u.full_name
            FROM loans l
            JOIN users u ON l.user_id = u.id
            WHERE l.book_id = %s
            ORDER BY l.loan_date DESC
            LIMIT 10
        """, (book_id,))
        
        loan_history = cur.fetchall()
        
        return render_template('books/view.html', book=book, loan_history=loan_history)
        
    except Exception as e:
        logger.error(f"Error al cargar libro {book_id}: {str(e)}", exc_info=True)
        flash('Error al cargar los detalles del libro', 'error')
        return redirect(url_for('books.index'))
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para agregar un nuevo libro
@bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add():
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        isbn = request.form.get('isbn')
        publisher = request.form.get('publisher')
        publication_year = request.form.get('publication_year')
        total_copies = int(request.form.get('total_copies', 1))
        
        if not all([title, author, isbn, str(total_copies)]):
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('books.add'))
            
        conn = get_db_connection()
        cur = get_cursor()
        
        try:
            # Verificar si ya existe un libro con el mismo ISBN
            cur.execute('SELECT id FROM books WHERE isbn = %s', (isbn,))
            if cur.fetchone():
                flash('Ya existe un libro con este ISBN', 'error')
                return redirect(url_for('books.add'))
                
            # Insertar el nuevo libro
            cur.execute("""
                INSERT INTO books (title, author, isbn, publisher, publication_year, total_copies, available_copies)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (title, author, isbn, publisher, publication_year, total_copies, total_copies))
            
            conn.commit()
            flash('Libro agregado exitosamente', 'success')
            return redirect(url_for('books.index'))
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error al agregar libro: {str(e)}", exc_info=True)
            flash('Error al agregar el libro', 'error')
            return redirect(url_for('books.add'))
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()
    
    # Si es GET, mostrar el formulario
    return render_template('books/add.html')

# Ruta para editar un libro existente
@bp.route('/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(book_id):
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        # Obtener el libro actual
        cur.execute('SELECT * FROM books WHERE id = %s', (book_id,))
        book = cur.fetchone()
        
        if not book:
            flash('Libro no encontrado', 'error')
            return redirect(url_for('books.index'))
            
        if request.method == 'POST':
            title = request.form.get('title')
            author = request.form.get('author')
            isbn = request.form.get('isbn')
            publisher = request.form.get('publisher')
            publication_year = request.form.get('publication_year')
            total_copies = int(request.form.get('total_copies', 1))
            
            if not all([title, author, isbn, str(total_copies)]):
                flash('Todos los campos son obligatorios', 'error')
                return redirect(url_for('books.edit', book_id=book_id))
                
            # Verificar si el ISBN ya está en uso por otro libro
            cur.execute('SELECT id FROM books WHERE isbn = %s AND id != %s', (isbn, book_id))
            if cur.fetchone():
                flash('Ya existe otro libro con este ISBN', 'error')
                return redirect(url_for('books.edit', book_id=book_id))
                
            # Calcular la diferencia en copias
            copies_diff = total_copies - book['total_copies']
            
            # Actualizar el libro
            cur.execute("""
                UPDATE books 
                SET title = %s, author = %s, isbn = %s, 
                    publisher = %s, publication_year = %s, 
                    total_copies = %s,
                    available_copies = available_copies + %s
                WHERE id = %s
            """, (title, author, isbn, publisher, publication_year, 
                 total_copies, copies_diff, book_id))
            
            conn.commit()
            flash('Libro actualizado exitosamente', 'success')
            return redirect(url_for('books.view', book_id=book_id))
            
        # Si es GET, mostrar el formulario con los datos actuales
        return render_template('books/edit.html', book=book)
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.error(f"Error al editar libro {book_id}: {str(e)}", exc_info=True)
        flash('Error al editar el libro', 'error')
        return redirect(url_for('books.index'))
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para eliminar un libro
@bp.route('/delete/<int:book_id>', methods=['POST'])
@login_required
@admin_required
def delete(book_id):
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        # Verificar si el libro existe y no tiene préstamos activos
        cur.execute("""
            SELECT b.*, COUNT(l.id) as active_loans
            FROM books b
            LEFT JOIN loans l ON b.id = l.book_id AND l.return_date IS NULL
            WHERE b.id = %s
            GROUP BY b.id
        """, (book_id,))
        
        book = cur.fetchone()
        
        if not book:
            flash('Libro no encontrado', 'error')
            return redirect(url_for('books.index'))
            
        if book['active_loans'] > 0:
            flash('No se puede eliminar el libro porque tiene préstamos activos', 'error')
            return redirect(url_for('books.view', book_id=book_id))
        
        # Eliminar el libro
        cur.execute('DELETE FROM books WHERE id = %s', (book_id,))
        conn.commit()
        
        flash('Libro eliminado exitosamente', 'success')
        return redirect(url_for('books.index'))
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        logger.error(f"Error al eliminar libro {book_id}: {str(e)}", exc_info=True)
        flash('Error al eliminar el libro', 'error')
        return redirect(url_for('books.view', book_id=book_id))
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para buscar libros (AJAX)
@bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    
    if not query or len(query) < 2:
        return jsonify([])
        
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        search_term = f"%{query}%"
        cur.execute("""
            SELECT id, title, author, isbn, 
                   (total_copies - (SELECT COUNT(*) FROM loans WHERE book_id = books.id AND return_date IS NULL)) as available
            FROM books 
            WHERE title LIKE %s OR author LIKE %s OR isbn LIKE %s
            ORDER BY title
            LIMIT 10
        """, (search_term, search_term, search_term))
        
        books = [
            {
                'id': book['id'],
                'title': book['title'],
                'author': book['author'],
                'isbn': book['isbn'],
                'available': book['available']
            }
            for book in cur.fetchall()
        ]
        
        return jsonify(books)
        
    except Exception as e:
        logger.error(f"Error en búsqueda de libros: {str(e)}", exc_info=True)
        return jsonify([])
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
