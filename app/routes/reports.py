from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from ..db import get_db_connection, get_cursor
from ..decorators import login_required, admin_required
from datetime import datetime, timedelta
import csv
from io import StringIO
import logging

# Create blueprint
bp = Blueprint('reports', __name__, url_prefix='/reports')

# Configure logging
logger = logging.getLogger(__name__)

# Ruta para el panel de informes
@bp.route('/')
@login_required
@admin_required
def index():
    return render_template('reports/index.html')

# Ruta para generar informes
@bp.route('/generate', methods=['POST'])
@login_required
@admin_required
def generate():
    report_type = request.form.get('report_type')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    output_format = request.form.get('format', 'html')
    
    if not report_type:
        flash('Seleccione un tipo de informe', 'error')
        return redirect(url_for('reports.index'))
    
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        # Convertir fechas a objetos date para validación
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
        
        if start_date_obj and end_date_obj and start_date_obj > end_date_obj:
            flash('La fecha de inicio no puede ser mayor a la fecha de fin', 'error')
            return redirect(url_for('reports.index'))
            
        # Construir la consulta según el tipo de informe
        if report_type == 'loans':
            query = """
                SELECT l.*, 
                       b.title as book_title, b.isbn as book_isbn,
                       u.username as user_name, u.email as user_email
                FROM loans l
                JOIN books b ON l.book_id = b.id
                JOIN users u ON l.user_id = u.id
                WHERE 1=1
            """
            
            params = []
            
            if start_date:
                query += " AND l.loan_date >= %s"
                params.append(start_date)
                
            if end_date:
                query += " AND l.loan_date <= %s"
                params.append(f"{end_date} 23:59:59")
                
            query += " ORDER BY l.loan_date DESC"
            
            cur.execute(query, params)
            data = cur.fetchall()
            
            if output_format == 'csv':
                return generate_csv(
                    data,
                    'prestamos',
                    ['ID', 'Libro', 'ISBN', 'Usuario', 'Email', 'Fecha Préstamo', 'Fecha Devolución', 'Estado'],
                    lambda x: [
                        x['id'],
                        x['book_title'],
                        x['book_isbn'],
                        x['user_name'],
                        x['user_email'],
                        x['loan_date'].strftime('%d/%m/%Y %H:%M') if x['loan_date'] else '',
                        x['return_date'].strftime('%d/%m/%Y %H:%M') if x['return_date'] else 'Pendiente',
                        'Devuelto' if x['return_date'] else ('Vencido' if x['due_date'] < datetime.now().date() else 'Activo')
                    ]
                )
            
            return render_template('reports/loans.html', 
                               data=data, 
                               start_date=start_date, 
                               end_date=end_date)
                               
        elif report_type == 'overdue':
            query = """
                SELECT l.*, 
                       b.title as book_title, b.isbn as book_isbn,
                       u.username as user_name, u.email as user_email,
                       DATEDIFF(CURDATE(), l.due_date) as days_overdue
                FROM loans l
                JOIN books b ON l.book_id = b.id
                JOIN users u ON l.user_id = u.id
                WHERE l.return_date IS NULL 
                AND l.due_date < CURDATE()
            """
            
            if start_date:
                query += " AND l.due_date >= %s"
                
            if end_date:
                query += " AND l.due_date <= %s"
                
            query += " ORDER BY l.due_date DESC, days_overdue DESC"
            
            params = []
            if start_date:
                params.append(start_date)
            if end_date:
                params.append(end_date)
                
            cur.execute(query, params)
            data = cur.fetchall()
            
            if output_format == 'csv':
                return generate_csv(
                    data,
                    'prestamos_vencidos',
                    ['ID', 'Libro', 'ISBN', 'Usuario', 'Días de atraso', 'Fecha Vencimiento'],
                    lambda x: [
                        x['id'],
                        x['book_title'],
                        x['book_isbn'],
                        x['user_name'],
                        x['days_overdue'],
                        x['due_date'].strftime('%d/%m/%Y')
                    ]
                )
            
            return render_template('reports/overdue.html', 
                               data=data, 
                               start_date=start_date, 
                               end_date=end_date)
                               
        elif report_type == 'popular_books':
            query = """
                SELECT b.*, 
                       COUNT(l.id) as loan_count,
                       (SELECT COUNT(*) FROM loans l2 WHERE l2.book_id = b.id AND l2.return_date IS NULL) as active_loans
                FROM books b
                LEFT JOIN loans l ON b.id = l.book_id
                WHERE 1=1
            """
            
            params = []
            
            if start_date:
                query += " AND l.loan_date >= %s"
                params.append(start_date)
                
            if end_date:
                query += " AND l.loan_date <= %s"
                params.append(f"{end_date} 23:59:59")
                
            query += " GROUP BY b.id ORDER BY loan_count DESC, b.title"
            
            cur.execute(query, params)
            data = cur.fetchall()
            
            if output_format == 'csv':
                return generate_csv(
                    data,
                    'libros_populares',
                    ['ID', 'Título', 'Autor', 'ISBN', 'Copias Totales', 'Disponibles', 'Préstamos'],
                    lambda x: [
                        x['id'],
                        x['title'],
                        x['author'],
                        x['isbn'],
                        x['total_copies'],
                        x['available_copies'],
                        x['loan_count'] or 0
                    ]
                )
            
            return render_template('reports/popular_books.html', 
                               data=data, 
                               start_date=start_date, 
                               end_date=end_date)
        
        elif report_type == 'user_activity':
            query = """
                SELECT u.*, 
                       (SELECT COUNT(*) FROM loans l WHERE l.user_id = u.id) as total_loans,
                       (SELECT COUNT(*) FROM loans l WHERE l.user_id = u.id AND l.return_date IS NULL) as active_loans,
                       (SELECT COUNT(*) FROM loans l WHERE l.user_id = u.id AND l.return_date IS NOT NULL AND l.return_date > l.due_date) as overdue_returns
                FROM users u
                WHERE 1=1
            """
            
            params = []
            
            # Solo aplicar filtros de fecha si se proporcionan
            if start_date or end_date:
                date_filter = []
                
                if start_date:
                    date_filter.append("l.loan_date >= %s")
                    params.append(start_date)
                    
                if end_date:
                    date_filter.append("l.loan_date <= %s")
                    params.append(f"{end_date} 23:59:59")
                
                query = f"""
                    SELECT u.*, 
                           COUNT(DISTINCT l1.id) as total_loans,
                           SUM(CASE WHEN l1.return_date IS NULL THEN 1 ELSE 0 END) as active_loans,
                           SUM(CASE WHEN l1.return_date > l1.due_date THEN 1 ELSE 0) as overdue_returns
                    FROM users u
                    LEFT JOIN loans l1 ON u.id = l1.user_id
                    {' AND '.join([f'l1.loan_date >= %s' for _ in date_filter[:1]])}
                    {' AND '.join([f'l1.loan_date <= %s' for _ in date_filter[1:2]])}
                    GROUP BY u.id
                """
            
            query += " ORDER BY total_loans DESC, u.username"
            
            cur.execute(query, params)
            data = cur.fetchall()
            
            if output_format == 'csv':
                return generate_csv(
                    data,
                    'actividad_usuarios',
                    ['ID', 'Usuario', 'Email', 'Total Préstamos', 'Préstamos Activos', 'Devoluciones Tardías', 'Estado'],
                    lambda x: [
                        x['id'],
                        x['username'],
                        x['email'],
                        x['total_loans'] or 0,
                        x['active_loans'] or 0,
                        x['overdue_returns'] or 0,
                        'Activo' if not x['is_banned'] else 'Restringido'
                    ]
                )
            
            return render_template('reports/user_activity.html', 
                               data=data, 
                               start_date=start_date, 
                               end_date=end_date)
        
        else:
            flash('Tipo de informe no válido', 'error')
            return redirect(url_for('reports.index'))
            
    except ValueError as e:
        logger.error(f"Error de formato de fecha: {str(e)}", exc_info=True)
        flash('Formato de fecha inválido. Use YYYY-MM-DD', 'error')
        return redirect(url_for('reports.index'))
    except Exception as e:
        logger.error(f"Error al generar informe: {str(e)}", exc_info=True)
        flash('Error al generar el informe', 'error')
        return redirect(url_for('reports.index'))
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def generate_csv(data, filename, headers, row_mapper):
    """
    Función auxiliar para generar archivos CSV
    """
    si = StringIO()
    cw = csv.writer(si)
    
    # Escribir encabezados
    cw.writerow(headers)
    
    # Escribir datos
    for item in data:
        cw.writerow(row_mapper(item))
    
    # Crear respuesta
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={filename}_{datetime.now().strftime('%Y%m%d')}.csv"
    output.headers["Content-type"] = "text/csv; charset=utf-8"
    
    return output
