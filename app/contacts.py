from flask import Blueprint, render_template, redirect, url_for, flash, request, session
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
    cur = mysql.connection.cursor()
    cur.execute('SELECT b.*, g.name as genre_name FROM books b LEFT JOIN genres g ON b.genre_id = g.id')
    books = cur.fetchall()
    cur.close()
    return render_template('books.html', books=books)

@main.route('/loans')
def loans():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cur = mysql.connection.cursor()
    cur.execute('''
        SELECT l.*, b.title as book_title, u.username as user_name 
        FROM loans l 
        JOIN books b ON l.book_id = b.id 
        JOIN users u ON l.user_id = u.id
    ''')
    loans = cur.fetchall()
    cur.close()
    return render_template('loans.html', loans=loans)


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
