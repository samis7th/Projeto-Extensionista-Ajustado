from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import sqlite3
from pathlib import Path
import csv, io
from auth import login_role

DB_PATH = Path(__file__).parent / "students.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not DB_PATH.exists():
        conn = get_db_connection()
        conn.execute("""CREATE TABLE students (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT UNIQUE NOT NULL, name TEXT NOT NULL, email TEXT, course TEXT, marks INTEGER);""")
        conn.commit()
        conn.close()

app = Flask(__name__, template_folder='.', static_folder='.')
app.config['SECRET_KEY'] = 'dev-demo-key'

# Ensure the database file exists before the first request.
init_db()

# Demo login: choose role from dropdown. For Student role, you can optionally enter a student_id to view.
@app.route('/login', methods=('GET','POST'))
def login():
    if request.method == 'POST':
        role = request.form.get('role','').strip()
        student_id = request.form.get('student_id','').strip()
        allowed_roles = {'Admin', 'Teacher', 'Student'}
        if role not in allowed_roles:
            flash('Invalid role. Choose Admin, Teacher, or Student.', 'warning')
            return redirect(url_for('login'))
        session.clear()
        session['role'] = role
        if role == 'Student' and student_id:
            session['student_id'] = student_id
        flash(f'Logged in as {role}', 'success')
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/')
def index():
    role = session.get('role')
    if not role:
        return redirect(url_for('login'))
    # Redirect to role dashboard
    if role == 'Admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'Teacher':
        return redirect(url_for('teacher_dashboard'))
    elif role == 'Student':
        return redirect(url_for('student_dashboard'))
    else:
        return redirect(url_for('login'))

# Admin dashboard: full CRUD + import/export
@app.route('/admin', methods=('GET','POST'))
@login_role('Admin')
def admin_dashboard():
    q = request.args.get('q','').strip()
    conn = get_db_connection()
    if q:
        like = f'%{q}%'
        students = conn.execute('SELECT * FROM students WHERE student_id LIKE ? OR name LIKE ? ORDER BY id DESC', (like, like)).fetchall()
    else:
        students = conn.execute('SELECT * FROM students ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin_dashboard.html', students=students, q=q)

# Teacher dashboard: teacher sees all students
@app.route('/teacher')
@login_role('Teacher')
def teacher_dashboard():
    selected_course = request.args.get('course','').strip()
    conn = get_db_connection()
    courses = conn.execute("SELECT DISTINCT course FROM students WHERE course IS NOT NULL AND course != '' ORDER BY course").fetchall()
    if selected_course:
        students = conn.execute('SELECT * FROM students WHERE course = ? ORDER BY id DESC', (selected_course,)).fetchall()
    else:
        students = conn.execute('SELECT * FROM students ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('teacher_dashboard.html', students=students, courses=[c['course'] for c in courses], selected_course=selected_course)

# Student dashboard: view own record (student_id provided at login)
@app.route('/student')
@login_role('Student')
def student_dashboard():
    student_id = session.get('student_id')
    conn = get_db_connection()
    student = None
    if student_id:
        student = conn.execute('SELECT * FROM students WHERE student_id = ?', (student_id,)).fetchone()
    conn.close()
    return render_template('student_dashboard.html', student=student)

# CRUD routes (admin only)
@app.route('/add', methods=('GET','POST'))
@login_role('Admin')
def add():
    if request.method == 'POST':
        student_id = request.form.get('student_id','').strip()
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        course = request.form.get('course','').strip()
        marks = request.form.get('marks') or None
        if student_id and name:
            conn = get_db_connection()
            try:
                conn.execute('INSERT INTO students (student_id, name, email, course, marks) VALUES (?, ?, ?, ?, ?)', (student_id, name, email, course, marks))
                conn.commit()
            except sqlite3.IntegrityError:
                flash('Student ID already exists.', 'warning')
            conn.close()
            return redirect(url_for('admin_dashboard'))
    return render_template('add.html')

@app.route('/edit/<int:stu_id>', methods=('GET','POST'))
@login_role('Teacher')
def edit(stu_id):
    teacher_mode = session.get('role') == 'Teacher'
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (stu_id,)).fetchone()
    if request.method == 'POST':
        if teacher_mode:
            marks = request.form.get('marks') or None
            if marks is not None and marks != '':
                conn.execute('UPDATE students SET marks=? WHERE id=?', (marks, stu_id))
                conn.commit()
                flash('Marks updated.', 'success')
            else:
                flash('Marks is required.', 'warning')
            conn.close()
            return redirect(url_for('teacher_dashboard'))
        student_id = request.form.get('student_id','').strip()
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        course = request.form.get('course','').strip()
        marks = request.form.get('marks') or None
        if student_id and name:
            try:
                conn.execute('UPDATE students SET student_id=?, name=?, email=?, course=?, marks=? WHERE id=?', (student_id, name, email, course, marks, stu_id))
                conn.commit()
            except sqlite3.IntegrityError:
                flash('Student ID conflict.', 'warning')
            conn.close()
            return redirect(url_for('admin_dashboard'))
    conn.close()
    return render_template('edit.html', student=student, teacher_mode=teacher_mode)

@app.route('/delete/<int:stu_id>')
@login_role('Admin')
def delete(stu_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM students WHERE id = ?', (stu_id,))
    conn.commit()
    conn.close()
    flash('Student deleted.', 'info')
    return redirect(url_for('admin_dashboard'))

# CSV import (Teacher or Admin)
@app.route('/import', methods=('POST',))
@login_role('Teacher')
def import_csv():
    file = request.files.get('file')
    if not file:
        flash('No file uploaded.', 'warning')
        return redirect(url_for('admin_dashboard'))
    stream = io.StringIO(file.stream.read().decode('utf-8'))
    reader = csv.DictReader(stream)
    conn = get_db_connection()
    count = 0
    for row in reader:
        sid = row.get('student_id','').strip()
        name = row.get('name','').strip()
        email = row.get('email','').strip()
        course = row.get('course','').strip()
        marks = row.get('marks') or None
        if sid and name:
            try:
                conn.execute('INSERT INTO students (student_id, name, email, course, marks) VALUES (?, ?, ?, ?, ?)', (sid, name, email, course, marks))
                count += 1
            except sqlite3.IntegrityError:
                # skip duplicates
                pass
    conn.commit()
    conn.close()
    flash(f'Imported {count} students.', 'success')
    return redirect(url_for('admin_dashboard'))

# CSV export (admin)
@app.route('/export')
@login_role('Admin')
def export_csv():
    conn = get_db_connection()
    students = conn.execute('SELECT student_id, name, email, course, marks FROM students ORDER BY id').fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['student_id','name','email','course','marks'])
    for s in students:
        writer.writerow([s['student_id'], s['name'], s['email'] or '', s['course'] or '', s['marks'] or ''])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='students_export.csv')

if __name__ == '__main__':
    app.run(debug=True)
