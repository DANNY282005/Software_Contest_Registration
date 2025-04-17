from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import os
import MySQLdb
from openpyxl import Workbook
from datetime import datetime
import io

app = Flask(__name__)

# Configure MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Daniel@MYSQL'
app.config['MYSQL_DB'] = 'Software_Contest'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'  # This will return results as dictionaries

# Secret key for session and flash messages
app.secret_key = 'your_secret_key_here'  # Replace with a secure secret key

# Initialize MySQL
mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        roll_number = request.form['rollNumber']
        register_number = request.form['registerNumber']
        department = request.form['department']

        print(f"Attempting to register: {name}, {roll_number}, {register_number}, {department}")  # Debug print

        try:
            # Create cursor
            cur = mysql.connection.cursor()

            # Test database connection
            cur.execute("SELECT 1")
            print("Database connection successful")  # Debug print

            # Execute query with explicit column names
            insert_query = """
                INSERT INTO Students (name, rollNumber, registerNumber, department)
                VALUES (%s, %s, %s, %s)
            """
            cur.execute(insert_query, (name, roll_number, register_number, department))
            print("Query executed successfully")  # Debug print

            # Commit to DB
            mysql.connection.commit()
            print("Changes committed to database")  # Debug print

            # Verify the insertion
            cur.execute("SELECT * FROM Students WHERE rollNumber = %s", [roll_number])
            result = cur.fetchone()
            print(f"Verification query result: {result}")  # Debug print

            # Close connection
            cur.close()
            
            if result:
                flash('Registration successful!', 'success')
            else:
                flash('Registration might have failed. Please check with admin.', 'warning')
            
            return redirect(url_for('index'))

        except MySQLdb.Error as e:
            print(f"MySQL Error: {e}")  # Debug print
            if e.args[0] == 1062:  # Duplicate entry error
                if 'rollNumber' in str(e):
                    flash('Roll number already registered. Please use a different roll number.', 'error')
                elif 'registerNumber' in str(e):
                    flash('Register number already registered. Please use a different register number.', 'error')
                else:
                    flash('This entry already exists in the database.', 'error')
            else:
                flash(f'Database error: {str(e)}', 'error')
            return redirect(url_for('index'))

        except Exception as e:
            print(f"General Error: {e}")  # Debug print
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('index'))

@app.route('/admin-login')
def admin_login():
    return render_template('admin-login.html')

@app.route('/admin-auth', methods=['POST'])
def admin_auth():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']

            cur = mysql.connection.cursor()
            
            # Check if admin exists
            cur.execute("SELECT * FROM Admin WHERE name = %s", [username])
            admin = cur.fetchone()
            cur.close()

            if admin and admin['password'] == password:  # For now, using plain password comparison
                session['admin_logged_in'] = True
                flash('Login successful!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid username or password!', 'error')
                return redirect(url_for('admin_login'))

        except Exception as e:
            flash(f'An error occurred during login: {str(e)}', 'error')
            return redirect(url_for('admin_login'))

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash('Please login first!', 'error')
        return redirect(url_for('admin_login'))

    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM Students ORDER BY rollNumber")
        registrations = cur.fetchall()
        cur.close()
        return render_template('admin-dashboard.html', registrations=registrations)

    except Exception as e:
        flash(f'Error fetching registrations: {str(e)}', 'error')
        return redirect(url_for('admin_login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/export-excel')
def export_excel():
    if not session.get('admin_logged_in'):
        flash('Please login first!', 'error')
        return redirect(url_for('admin_login'))

    try:
        # Create a new workbook and select the active sheet
        wb = Workbook()
        ws = wb.active
        ws.title = "Registered Students"

        # Add headers
        headers = ['Name', 'Roll Number', 'Register Number', 'Department', 'Registration Date', 'Last Updated']
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)

        # Get data from database
        cur = mysql.connection.cursor()
        cur.execute("SELECT name, rollNumber, registerNumber, department, created_at, updated_at FROM Students ORDER BY name")
        students = cur.fetchall()
        cur.close()

        # Add data to worksheet
        for row, student in enumerate(students, 2):
            ws.cell(row=row, column=1, value=student['name'])
            ws.cell(row=row, column=2, value=student['rollNumber'])
            ws.cell(row=row, column=3, value=student['registerNumber'])
            ws.cell(row=row, column=4, value=student['department'])
            ws.cell(row=row, column=5, value=student['created_at'].strftime('%Y-%m-%d %H:%M:%S'))
            ws.cell(row=row, column=6, value=student['updated_at'].strftime('%Y-%m-%d %H:%M:%S'))

        # Create a BytesIO object to store the Excel file
        excel_file = io.BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)

        # Generate filename with current date
        current_date = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'registered_students_{current_date}.xlsx'

        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        flash(f'Error exporting data: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    # Test database connection on startup
    try:
        with app.app_context():
            cur = mysql.connection.cursor()
            cur.execute("SELECT 1")
            print("Database connection test successful on startup")
            cur.close()
    except Exception as e:
        print(f"Database connection test failed on startup: {e}")

    app.run(debug=True, port=5000) 