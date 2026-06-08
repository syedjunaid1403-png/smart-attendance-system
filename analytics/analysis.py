import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
import os
import matplotlib
matplotlib.use('Agg') # Required for headless environment (not showing plot windows)

DB_PATH = os.path.join('database', 'attendance.db')

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def get_kpis(today_date):
    conn = get_db_connection()
    
    # Total Students
    students_df = pd.read_sql_query('SELECT * FROM students', conn)
    total_students = len(students_df)
    
    # Today's Attendance
    today_df = pd.read_sql_query(f'SELECT * FROM attendance WHERE date = "{today_date}"', conn)
    
    if len(today_df) > 0:
        present_today = len(today_df[today_df['status'] == 'Present'])
        absent_today = len(today_df[today_df['status'] == 'Absent'])
    else:
        present_today = 0
        absent_today = 0
        
    # Overall Attendance Percentage
    all_attendance_df = pd.read_sql_query('SELECT * FROM attendance', conn)
    if len(all_attendance_df) > 0:
        total_records = len(all_attendance_df)
        total_present = len(all_attendance_df[all_attendance_df['status'] == 'Present'])
        overall_percentage = round((total_present / total_records) * 100, 2)
    else:
        overall_percentage = 0.0
        
    conn.close()
    
    return {
        'total_students': total_students,
        'present_today': present_today,
        'absent_today': absent_today,
        'attendance_percentage': overall_percentage
    }

def get_reports_data():
    conn = get_db_connection()
    
    query = '''
    SELECT s.name as student_name, a.status 
    FROM students s
    LEFT JOIN attendance a ON s.id = a.student_id
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if len(df) == 0 or df['status'].isna().all():
        return []
        
    # Group by student name
    reports = []
    for name, group in df.groupby('student_name'):
        # Drop rows where status is NaN (students with no attendance records yet)
        valid_records = group.dropna(subset=['status'])
        
        if len(valid_records) > 0:
            present_days = len(valid_records[valid_records['status'] == 'Present'])
            absent_days = len(valid_records[valid_records['status'] == 'Absent'])
            total_days = present_days + absent_days
            percentage = round((present_days / total_days) * 100, 2)
        else:
            present_days = 0
            absent_days = 0
            percentage = 0.0
            
        reports.append({
            'name': name,
            'present_days': present_days,
            'absent_days': absent_days,
            'percentage': percentage
        })
        
    return reports

def generate_charts():
    conn = get_db_connection()
    df = pd.read_sql_query('''
        SELECT s.department, a.status 
        FROM students s
        JOIN attendance a ON s.id = a.student_id
    ''', conn)
    conn.close()
    
    charts_dir = os.path.join('static', 'charts')
    os.makedirs(charts_dir, exist_ok=True)
    
    if len(df) == 0:
        return
        
    # 1. Pie Chart: Overall Present vs Absent
    status_counts = df['status'].value_counts()
    
    plt.figure(figsize=(6, 6))
    # Colors for Present (Green/Blue) and Absent (Red/Orange)
    colors = ['#28a745', '#dc3545'] if 'Present' in status_counts.index and 'Absent' in status_counts.index else None
    
    # Create pie chart
    plt.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', startangle=90, colors=colors)
    plt.title('Overall Attendance (Present vs Absent)')
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, 'pie_chart.png'))
    plt.close()
    
    # 2. Bar Chart: Department-wise Attendance
    # Group by department and status
    dept_status = df.groupby(['department', 'status']).size().unstack(fill_value=0)
    
    # Plot bar chart
    if not dept_status.empty:
        ax = dept_status.plot(kind='bar', figsize=(8, 6), stacked=False)
        plt.title('Department-wise Attendance')
        plt.xlabel('Department')
        plt.ylabel('Count')
        plt.xticks(rotation=45)
        plt.legend(title='Status')
        plt.tight_layout()
        plt.savefig(os.path.join(charts_dir, 'bar_chart.png'))
        plt.close()
