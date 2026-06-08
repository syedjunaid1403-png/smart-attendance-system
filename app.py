import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
from analytics.analysis import generate_charts, get_kpis, get_reports_data

app = Flask(__name__)
CORS(app) # Allow Live Server to communicate with Flask API

DB_PATH = os.path.join('database', 'attendance.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            email TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TEXT,
            status TEXT,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    ''')
    
    # Check if we should populate with sample data
    c.execute('SELECT COUNT(*) FROM students')
    if c.fetchone()[0] == 0:
        import pandas as pd
        csv_path = os.path.join('dataset', 'attendance.csv')
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            for _, row in df.iterrows():
                # Add student if not exists
                c.execute('SELECT id FROM students WHERE name=? AND department=?', (row['Name'], row['Department']))
                student = c.fetchone()
                if not student:
                    c.execute('INSERT INTO students (name, department, email) VALUES (?, ?, ?)', 
                              (row['Name'], row['Department'], f"{row['Name'].lower()}@example.com"))
                    student_id = c.lastrowid
                else:
                    student_id = student['id']
                
                # Add attendance record
                c.execute('INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)',
                          (student_id, row['Date'], row['Status']))

    conn.commit()
    conn.close()

# Initialize the database when the app starts
init_db()

@app.route('/api/students', methods=['GET', 'POST'])
def api_students():
    conn = get_db_connection()
    if request.method == 'POST':
        data = request.json
        conn.execute('INSERT INTO students (name, department, email) VALUES (?, ?, ?)', (data['name'], data['department'], data['email']))
        conn.commit()
        conn.close()
        return jsonify({"message": "Student added successfully!"}), 201
    
    # GET with optional search query
    query = request.args.get('query', '')
    if query:
        students = conn.execute('''
            SELECT * FROM students 
            WHERE name LIKE ? OR department LIKE ?
        ''', (f'%{query}%', f'%{query}%')).fetchall()
    else:
        students = conn.execute('SELECT * FROM students').fetchall()
    
    conn.close()
    return jsonify([dict(s) for s in students])

@app.route('/api/students/<int:id>', methods=['DELETE'])
def api_delete_student(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM attendance WHERE student_id = ?', (id,))
    conn.execute('DELETE FROM students WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Student deleted successfully!"}), 200

@app.route('/api/attendance', methods=['GET', 'POST'])
def api_attendance():
    conn = get_db_connection()
    if request.method == 'POST':
        data = request.json
        date = data.get('date')
        status_map = data.get('status_map', {})
        for student_id_str, status in status_map.items():
            student_id = int(student_id_str)
            existing = conn.execute('SELECT id FROM attendance WHERE student_id = ? AND date = ?', (student_id, date)).fetchone()
            if existing:
                conn.execute('UPDATE attendance SET status = ? WHERE id = ?', (status, existing['id']))
            else:
                conn.execute('INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)', (student_id, date, status))
        conn.commit()
        conn.close()
        return jsonify({"message": f"Attendance saved for {date}!"}), 200
        
    date_to_view = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    attendance_records = conn.execute('SELECT student_id, status FROM attendance WHERE date = ?', (date_to_view,)).fetchall()
    conn.close()
    return jsonify({
        "date": date_to_view,
        "records": [dict(r) for r in attendance_records]
    })

@app.route('/api/dashboard', methods=['GET'])
def api_dashboard():
    today = datetime.now().strftime('%Y-%m-%d')
    generate_charts()
    kpis = get_kpis(today)
    return jsonify(kpis)

@app.route('/api/reports', methods=['GET'])
def api_reports():
    reports_data = get_reports_data()
    return jsonify(reports_data)

@app.route('/static/charts/<path:filename>')
def serve_charts(filename):
    return send_from_directory(os.path.join(app.root_path, 'static', 'charts'), filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
