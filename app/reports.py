from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime, timedelta
from .db import get_db_connection, get_cursor

def generate_pdf_report(report_type, period=None):
    """
    Generate a PDF report based on the specified type and period
    
    Args:
        report_type (str): Type of report to generate
        period (str, optional): Time period for the report (day, week, year)
        
    Returns:
        BytesIO: PDF file in memory
    """
    buffer = BytesIO()
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter) if report_type == 'loans_by_genre' else letter,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )
    
    # Get the data for the report
    data = []
    title = ""
    
    if report_type == 'popular_books':
        title = f"Libros más populares ({period.capitalize()})"
        data = get_popular_books(period)
    elif report_type == 'loans_by_genre':
        title = f"Préstamos por género ({period.capitalize()})"
        data = get_loans_by_genre(period)
    
    # Prepare the document elements
    elements = []
    styles = getSampleStyleSheet()
    
    # Add title
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        alignment=1  # Center alignment
    )
    elements.append(Paragraph(title, title_style))
    
    # Add date and time
    date_style = ParagraphStyle(
        'Date',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=20,
        alignment=2  # Right alignment
    )
    elements.append(Paragraph(
        f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        date_style
    ))
    
    # Add data table
    if data:
        # Create table
        table = Table(data)
        
        # Add style to table
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
        
        # Alternate row colors
        for i in range(1, len(data)):
            if i % 2 == 1:
                style.add('BACKGROUND', (0, i), (-1, i), colors.lightgrey)
        
        table.setStyle(style)
        elements.append(table)
    else:
        elements.append(Paragraph("No hay datos disponibles para el informe seleccionado.", styles['Normal']))
    
    # Build the PDF
    doc.build(elements)
    
    # Reset buffer position to the beginning
    buffer.seek(0)
    return buffer

def get_popular_books(period):
    """Get the most popular books for a given period"""
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        # Calculate date range based on period
        end_date = datetime.now()
        if period == 'day':
            start_date = end_date - timedelta(days=1)
        elif period == 'week':
            start_date = end_date - timedelta(weeks=1)
        else:  # year
            start_date = end_date - timedelta(days=365)
        
        query = """
            SELECT 
                b.title,
                b.author,
                COUNT(l.id) as loan_count
            FROM loans l
            JOIN books b ON l.book_id = b.id
            WHERE l.loan_date BETWEEN %s AND %s
            GROUP BY b.id, b.title, b.author
            ORDER BY loan_count DESC
            LIMIT 20
        """
        
        cur.execute(query, (start_date, end_date))
        results = cur.fetchall()
        
        # Prepare data for the table
        data = [['#', 'Título', 'Autor', 'Número de Préstamos']]
        
        for i, row in enumerate(results, 1):
            data.append([
                str(i),
                row['title'],
                row['author'],
                str(row['loan_count'])
            ])
            
        return data
        
    except Exception as e:
        print(f"Error generating popular books report: {str(e)}")
        return []
    finally:
        cur.close()
        conn.close()

def get_loans_by_genre(period):
    """Get loans grouped by genre for a given period"""
    conn = get_db_connection()
    cur = get_cursor()
    
    try:
        # Calculate date range based on period
        end_date = datetime.now()
        if period == 'day':
            start_date = end_date - timedelta(days=1)
        elif period == 'week':
            start_date = end_date - timedelta(weeks=1)
        else:  # year
            start_date = end_date - timedelta(days=365)
        
        query = """
            SELECT 
                COALESCE(g.name, 'Sin género') as genre_name,
                COUNT(l.id) as loan_count,
                COUNT(DISTINCT l.user_id) as unique_users,
                ROUND(AVG(DATEDIFF(COALESCE(l.return_date, NOW()), l.loan_date)), 1) as avg_loan_days
            FROM loans l
            JOIN books b ON l.book_id = b.id
            LEFT JOIN genres g ON b.genre_id = g.id
            WHERE l.loan_date BETWEEN %s AND %s
            GROUP BY g.id, g.name
            ORDER BY loan_count DESC
        """
        
        cur.execute(query, (start_date, end_date))
        results = cur.fetchall()
        
        # Prepare data for the table
        data = [['Género', 'Total Préstamos', 'Usuarios Únicos', 'Días Promedio de Préstamo']]
        
        for row in results:
            data.append([
                row['genre_name'],
                str(row['loan_count']),
                str(row['unique_users']),
                str(row['avg_loan_days'])
            ])
            
        return data
        
    except Exception as e:
        print(f"Error generating loans by genre report: {str(e)}")
        return []
    finally:
        cur.close()
        conn.close()
