from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

from flask import render_template

@app.route('/')
def home():
    return render_template('index.html')

app = Flask(__name__)
CORS(app)

# Database Path
DB_PATH = "attendance.db"


# -----------------------------
# DATABASE CONNECTION
# -----------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------
# DATABASE INITIALIZATION
# -----------------------------
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        email TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        date TEXT,
        status TEXT,
        FOREIGN KEY(student_id) REFERENCES students(id)
    )
    """)

    conn.commit()
    conn.close()


init_db()


# -----------------------------
# HOME ROUTE
# -----------------------------
@app.route('/')
def home():
    return jsonify({
        "message": "Smart Attendance Analytics System API Running"
    })


# -----------------------------
# ADD STUDENT
# -----------------------------
@app.route('/add_student', methods=['POST'])
def add_student():
    data = request.json

    name = data.get('name')
    department = data.get('department')
    email = data.get('email')

    conn = get_db_connection()

    conn.execute(
        "INSERT INTO students(name, department, email) VALUES(?,?,?)",
        (name, department, email)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Student added successfully"
    })


# -----------------------------
# VIEW STUDENTS
# -----------------------------
@app.route('/students', methods=['GET'])
def get_students():

    conn = get_db_connection()

    students = conn.execute(
        "SELECT * FROM students"
    ).fetchall()

    conn.close()

    return jsonify([dict(student) for student in students])


# -----------------------------
# DELETE STUDENT
# -----------------------------
@app.route('/delete_student/<int:id>', methods=['DELETE'])
def delete_student(id):

    conn = get_db_connection()

    conn.execute(
        "DELETE FROM attendance WHERE student_id=?",
        (id,)
    )

    conn.execute(
        "DELETE FROM students WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Student deleted successfully"
    })


# -----------------------------
# SEARCH STUDENT
# -----------------------------
@app.route('/search', methods=['GET'])
def search_student():

    query = request.args.get('query', '')

    conn = get_db_connection()

    students = conn.execute("""
        SELECT * FROM students
        WHERE name LIKE ?
        OR department LIKE ?
    """, (f'%{query}%', f'%{query}%')).fetchall()

    conn.close()

    return jsonify([dict(student) for student in students])


# -----------------------------
# MARK ATTENDANCE
# -----------------------------
@app.route('/attendance', methods=['POST'])
def mark_attendance():

    data = request.json

    student_id = data.get('student_id')
    status = data.get('status')

    today = datetime.now().strftime("%Y-%m-%d")

    conn = get_db_connection()

    existing = conn.execute("""
        SELECT * FROM attendance
        WHERE student_id=? AND date=?
    """, (student_id, today)).fetchone()

    if existing:
        conn.execute("""
            UPDATE attendance
            SET status=?
            WHERE id=?
        """, (status, existing['id']))
    else:
        conn.execute("""
            INSERT INTO attendance(student_id,date,status)
            VALUES(?,?,?)
        """, (student_id, today, status))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Attendance saved successfully"
    })


# -----------------------------
# VIEW ATTENDANCE
# -----------------------------
@app.route('/attendance', methods=['GET'])
def get_attendance():

    conn = get_db_connection()

    attendance = conn.execute("""
        SELECT students.name,
               students.department,
               attendance.date,
               attendance.status
        FROM attendance
        JOIN students
        ON students.id = attendance.student_id
    """).fetchall()

    conn.close()

    return jsonify([dict(row) for row in attendance])


# -----------------------------
# DASHBOARD KPIs
# -----------------------------
@app.route('/dashboard', methods=['GET'])
def dashboard():

    conn = get_db_connection()

    total_students = conn.execute(
        "SELECT COUNT(*) FROM students"
    ).fetchone()[0]

    today = datetime.now().strftime("%Y-%m-%d")

    present = conn.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE date=? AND status='Present'
    """, (today,)).fetchone()[0]

    absent = conn.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE date=? AND status='Absent'
    """, (today,)).fetchone()[0]

    attendance_percentage = 0

    if total_students > 0:
        attendance_percentage = round(
            (present / total_students) * 100,
            2
        )

    conn.close()

    return jsonify({
        "total_students": total_students,
        "present_today": present,
        "absent_today": absent,
        "attendance_percentage": attendance_percentage
    })


# -----------------------------
# REPORTS
# -----------------------------
@app.route('/reports', methods=['GET'])
def reports():

    conn = get_db_connection()

    report_data = conn.execute("""
        SELECT
            students.name,
            SUM(CASE WHEN attendance.status='Present' THEN 1 ELSE 0 END) as present_days,
            SUM(CASE WHEN attendance.status='Absent' THEN 1 ELSE 0 END) as absent_days
        FROM students
        LEFT JOIN attendance
        ON students.id = attendance.student_id
        GROUP BY students.id
    """).fetchall()

    result = []

    for row in report_data:

        total = row['present_days'] + row['absent_days']

        percentage = 0

        if total > 0:
            percentage = round(
                (row['present_days'] / total) * 100,
                2
            )

        result.append({
            "name": row['name'],
            "present_days": row['present_days'],
            "absent_days": row['absent_days'],
            "attendance_percentage": percentage
        })

    conn.close()

    return jsonify(result)


# -----------------------------
# RUN APP
# -----------------------------
if __name__ == '__main__':
    app.run(debug=True)