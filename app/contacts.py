from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from . import db

main = Blueprint('main', __name__)

# Get mysql instance
mysql = db.mysql

@main.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html')

@main.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html')

@main.route('/books')
def books():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        cur = mysql.connection.cursor()
        
        # Get current user info
        cur.execute('''
            SELECT id, username, email, CONCAT(first_name, ' ', last_name) as full_name 
            FROM users 
            WHERE id = %s
        ''', (session['user_id'],))
        user = cur.fetchone()
        
        if not user:
            flash('Usuario no encontrado', 'error')
            return redirect(url_for('auth.logout'))
        
        # Base query for books with available copies
        query = '''
            SELECT b.*, g.name as genre_name,
                   b.quantity - IFNULL((SELECT COUNT(*) FROM loans l 
                                      WHERE l.book_id = b.id AND l.return_date IS NULL), 0) as available_copies
            FROM books b 
            LEFT JOIN genres g ON b.genre_id = g.id
        '''
        
        # Get search and filter parameters
        search = request.args.get('search', '')
        selected_genre = request.args.get('genre', '')
        
        # Build where conditions
        conditions = []
        params = []
        
        if search:
            conditions.append("(b.title LIKE %s OR b.author LIKE %s OR b.isbn = %s)")
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search])
            
        if selected_genre:
            conditions.append("b.genre_id = %s")
            params.append(selected_genre)
        
        # Add conditions to query
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        # Add ordering
        query += " ORDER BY b.title"
        
        # Execute query
        cur.execute(query, params)
        books = cur.fetchall()
        
        # Get genres for the filter
        cur.execute('SELECT * FROM genres ORDER BY name')
        genres = cur.fetchall()
        
        return render_template('books.html', 
                            books=books,
                            user=user,  # Changed from current_user to user
                            genres=genres,
                            search=search,
                            selected_genre=selected_genre)
    
    except Exception as e:
        print(f"Error in books route: {str(e)}")
        flash('Ocurrió un error al cargar los libros', 'error')
        return redirect(url_for('main.dashboard'))
    finally:
        if 'cur' in locals():
            cur.close()

@main.route('/loans')
def loans():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # Get active loans
    cur = mysql.connection.cursor()
    
    # Get active loans (not returned yet)
    cur.execute('''
        SELECT l.*, b.title as book_title, u.username as user_name,
               DATEDIFF(l.due_date, CURDATE()) as days_remaining
        FROM loans l 
        JOIN books b ON l.book_id = b.id 
        JOIN users u ON l.user_id = u.id
        WHERE l.return_date IS NULL
        ORDER BY l.due_date
    ''')
    active_loans = cur.fetchall()
    
    # Get overdue loans
    cur.execute('''
        SELECT l.*, b.title as book_title, u.username as user_name,
               DATEDIFF(l.due_date, CURDATE()) as days_remaining
        FROM loans l 
        JOIN books b ON l.book_id = b.id 
        JOIN users u ON l.user_id = u.id
        WHERE l.return_date IS NULL 
        AND l.due_date < CURDATE()
        ORDER BY l.due_date
    ''')
    overdue_loans = cur.fetchall()
    
    # Get returned loans (history)
    cur.execute('''
        SELECT l.*, b.title as book_title, u.username as user_name
        FROM loans l 
        JOIN books b ON l.book_id = b.id 
        JOIN users u ON l.user_id = u.id
        WHERE l.return_date IS NOT NULL
        ORDER BY l.return_date DESC
        LIMIT 50
    ''')
    returned_loans = cur.fetchall()
    
    # Get available books for the new loan form
    cur.execute('''
        SELECT b.*, COUNT(l.id) as loaned_copies,
               b.quantity - COUNT(l.id) as available_copies
        FROM books b
        LEFT JOIN loans l ON b.id = l.book_id AND l.return_date IS NULL
        GROUP BY b.id
        HAVING available_copies > 0
    ''')
    available_books = cur.fetchall()
    
    # Get users for the new loan form
    cur.execute('SELECT id, username, email, CONCAT(first_name, " ", last_name) as full_name FROM users WHERE is_active = 1')
    users = cur.fetchall()
    
    cur.close()
    
    return render_template('loans.html', 
                         active_loans=active_loans,
                         overdue_loans=overdue_loans,
                         returned_loans=returned_loans,
                         available_books=available_books,
                         users=users,
                         active_tab=request.args.get('tab', 'active'))

@main.route('/loans/new', methods=['GET', 'POST'])
def new_loan():
    if 'user_id' not in session:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Sesión no válida'}), 401
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        try:
            # Get form data
            book_id = request.form.get('book_id')
            user_id = request.form.get('user_id')
            loan_date = request.form.get('loan_date')
            due_date = request.form.get('due_date')
            notes = request.form.get('notes', '')
            
            # Validate required fields
            if not all([book_id, user_id, loan_date, due_date]):
                error_msg = 'Todos los campos obligatorios deben ser completados'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'error')
                return redirect(url_for('main.loans'))
            
            cur = mysql.connection.cursor()
            
            # Verify book exists and get current availability
            cur.execute('''
                SELECT b.*, 
                       b.quantity - IFNULL((SELECT COUNT(*) FROM loans l WHERE l.book_id = b.id AND l.return_date IS NULL), 0) as available_copies
                FROM books b
                WHERE b.id = %s
                GROUP BY b.id
                HAVING available_copies > 0
                FOR UPDATE
            ''', (book_id,))
            
            book = cur.fetchone()
            
            if not book:
                error_msg = 'No hay copias disponibles de este libro o el libro no existe'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'error')
                return redirect(url_for('main.loans'))
                
            # Check if user exists and is active
            cur.execute('SELECT id FROM users WHERE id = %s AND is_active = 1', (user_id,))
            if not cur.fetchone():
                error_msg = 'El usuario seleccionado no es válido o está inactivo'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': error_msg}), 400
                flash(error_msg, 'error')
                return redirect(url_for('main.loans'))
            
            # Create new loan
            cur.execute('''
                INSERT INTO loans (book_id, user_id, loan_date, due_date, notes)
                VALUES (%s, %s, %s, %s, %s)
            ''', (book_id, user_id, loan_date, due_date, notes))
            
            # Update the book's last_updated timestamp
            cur.execute('''
                UPDATE books 
                SET updated_at = NOW() 
                WHERE id = %s
            ''', (book_id,))
            
            mysql.connection.commit()
            
            # If it's an AJAX request, return JSON response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'message': 'Préstamo registrado exitosamente',
                    'available_copies': book['available_copies'] - 1
                })
                
            flash('Préstamo registrado exitosamente', 'success')
            return redirect(url_for('main.loans'))
            
        except Exception as e:
            mysql.connection.rollback()
            error_message = str(e)
            print(f"Error en new_loan: {error_message}")
            
            # If it's an AJAX request, return JSON response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': f'Error al registrar el préstamo: {error_message}'
                }), 500
                
            flash(f'Error al registrar el préstamo: {error_message}', 'error')
            return redirect(url_for('main.loans'))
            
    # GET request handling
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'message': 'Método no permitido'}), 405
    return redirect(url_for('main.loans'))

@contacts.route('/add_contact', methods=['POST'])
def add_contact():
    if request.method == 'POST':
        fullname = request.form['fullname']
        phone = request.form['phone']
        email = request.form['email']
        try:
            cur = mysql.connection.cursor()
            cur.execute(
                "INSERT INTO contacts (fullname, phone, email) VALUES (%s,%s,%s)", (fullname, phone, email))
            mysql.connection.commit()
            flash('Contact Added successfully')
            return redirect(url_for('contacts.Index'))
        except Exception as e:
            flash(e.args[1])
            return redirect(url_for('contacts.Index'))


@contacts.route('/edit/<id>', methods=['POST', 'GET'])
def get_contact(id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM contacts WHERE id = %s', (id))
    data = cur.fetchall()
    cur.close()
    print(data[0])
    return render_template('edit-contact.html', contact=data[0])


@contacts.route('/update/<id>', methods=['POST'])
def update_contact(id):
    if request.method == 'POST':
        fullname = request.form['fullname']
        phone = request.form['phone']
        email = request.form['email']
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE contacts
            SET fullname = %s,
                email = %s,
                phone = %s
            WHERE id = %s
        """, (fullname, email, phone, id))
        flash('Contact Updated Successfully')
        mysql.connection.commit()
        return redirect(url_for('contacts.Index'))


@contacts.route('/delete/<string:id>', methods=['POST', 'GET'])
def delete_contact(id):
    cur = mysql.connection.cursor()
    cur.execute('DELETE FROM contacts WHERE id = {0}'.format(id))
    mysql.connection.commit()
    flash('Contact Removed Successfully')
    return redirect(url_for('contacts.Index'))
