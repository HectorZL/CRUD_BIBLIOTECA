from flask import Blueprint, render_template, redirect, url_for, flash, session
from ..db import get_db_connection, get_cursor
from ..decorators import login_required
import logging

# Create blueprint with url_prefix
bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# Configure logging
logger = logging.getLogger(__name__)

# Ruta del dashboard principal
@bp.route('/')
@login_required
def index():
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        # Obtener estadísticas generales
        stats = {}
        
        # Total de libros
        cur.execute("SELECT COUNT(*) as total_books FROM books")
        stats['total_books'] = cur.fetchone()['total_books']
        
        # Libros disponibles
        cur.execute("""
            SELECT COUNT(*) as available_books 
            FROM books 
            WHERE available_copies > 0
        """)
        stats['available_books'] = cur.fetchone()['available_books']
        
        # Préstamos activos
        cur.execute("""
            SELECT COUNT(*) as active_loans 
            FROM loans 
            WHERE return_date IS NULL
        """)
        stats['active_loans'] = cur.fetchone()['active_loans']
        
        # Usuarios registrados
        cur.execute("SELECT COUNT(*) as total_users FROM users")
        stats['total_users'] = cur.fetchone()['total_users']
        
        # Próximas devoluciones (próximos 7 días)
        cur.execute("""
            SELECT l.*, b.title as book_title, u.username as user_name
            FROM loans l
            JOIN books b ON l.book_id = b.id
            JOIN users u ON l.user_id = u.id
            WHERE l.return_date IS NULL 
            AND l.due_date BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 7 DAY)
            ORDER BY l.due_date ASC
            LIMIT 10
        """)
        upcoming_returns = cur.fetchall()
        
        # Préstamos recientes
        cur.execute("""
            SELECT l.*, b.title as book_title, u.username as user_name
            FROM loans l
            JOIN books b ON l.book_id = b.id
            JOIN users u ON l.user_id = u.id
            ORDER BY l.loan_date DESC
            LIMIT 5
        """)
        recent_loans = cur.fetchall()
        
        # Libros más populares (más prestados)
        cur.execute("""
            SELECT b.*, COUNT(l.id) as loan_count
            FROM books b
            LEFT JOIN loans l ON b.id = l.book_id
            GROUP BY b.id
            ORDER BY loan_count DESC, b.title
            LIMIT 5
        """)
        popular_books = cur.fetchall()
        
        # Usuarios con más préstamos
        cur.execute("""
            SELECT u.id, u.username, u.full_name, COUNT(l.id) as loan_count
            FROM users u
            LEFT JOIN loans l ON u.id = l.user_id
            GROUP BY u.id
            ORDER BY loan_count DESC
            LIMIT 5
        """)
        top_users = cur.fetchall()
        
        return render_template('dashboard_new.html',
                           stats=stats,
                           upcoming_returns=upcoming_returns,
                           recent_loans=recent_loans,
                           popular_books=popular_books,
                           top_users=top_users)
                           
    except Exception as e:
        logger.error(f"Error al cargar el dashboard: {str(e)}", exc_info=True)
        flash('Error al cargar el panel de control', 'error')
        return render_template('dashboard_new.html',
                            stats={},
                            upcoming_returns=[],
                            recent_loans=[],
                            popular_books=[],
                            top_users=[])
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# Ruta para la página de inicio del dashboard
@bp.route('/')
@login_required
def home():
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        # Obtener estadísticas generales
        stats = {}
        
        # Total de libros
        cur.execute("SELECT COUNT(*) as total_books FROM books")
        stats['total_books'] = cur.fetchone()['total_books']
        
        # Libros disponibles
        cur.execute("""
            SELECT COUNT(*) as available_books 
            FROM books 
            WHERE available_copies > 0
        """)
        stats['available_books'] = cur.fetchone()['available_books']
        
        # Préstamos activos
        cur.execute("""
            SELECT COUNT(*) as active_loans 
            FROM loans 
            WHERE return_date IS NULL
        """)
        stats['active_loans'] = cur.fetchone()['active_loans']
        
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
        
        return render_template('dashboard/index.html', 
                             stats=stats, 
                             recent_loans=recent_loans)
    except Exception as e:
        logger.error(f"Error al cargar el dashboard: {e}", exc_info=True)
        flash("Ocurrió un error al cargar el dashboard", "error")
        return redirect(url_for('main.index'))
    finally:
        if 'conn' in locals():
            conn.close()
