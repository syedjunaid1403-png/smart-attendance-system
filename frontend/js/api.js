const API_BASE = 'http://127.0.0.1:5000/api';

// --- Utility: Show Flash Messages ---
function showAlert(message, type = 'success') {
    const alertContainer = document.getElementById('alert-container');
    if (!alertContainer) return;
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show shadow-sm`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    alertContainer.appendChild(alertDiv);
    
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alertDiv);
        bsAlert.close();
    }, 5000);
}

// --- Dashboard Logic ---
async function loadDashboard() {
    try {
        const res = await fetch(`${API_BASE}/dashboard`);
        const kpis = await res.json();
        
        document.getElementById('kpi-total').textContent = kpis.total_students;
        document.getElementById('kpi-present').textContent = kpis.present_today;
        document.getElementById('kpi-absent').textContent = kpis.absent_today;
        document.getElementById('kpi-percent').textContent = kpis.attendance_percentage + '%';
        
        const dataAvailable = (kpis.present_today + kpis.absent_today) > 0;
        document.getElementById('today-badge').textContent = dataAvailable ? 'Today: Data Available' : 'Today: No Data';
        
        // Add cache buster to images so they refresh
        const timestamp = new Date().getTime();
        document.getElementById('bar-chart').src = `http://127.0.0.1:5000/static/charts/bar_chart.png?t=${timestamp}`;
        document.getElementById('pie-chart').src = `http://127.0.0.1:5000/static/charts/pie_chart.png?t=${timestamp}`;
    } catch (e) {
        console.error("Error loading dashboard", e);
    }
}

// --- Students Logic ---
async function loadStudents(query = '') {
    try {
        const res = await fetch(`${API_BASE}/students${query ? '?query=' + query : ''}`);
        const students = await res.json();
        const tbody = document.getElementById('students-tbody');
        tbody.innerHTML = '';
        
        if (students.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center py-5 text-muted">No students found.</td></tr>`;
            return;
        }
        
        students.forEach(student => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="ps-4 fw-bold text-muted">#${student.id}</td>
                <td class="fw-semibold">
                    <div class="d-flex align-items-center">
                        <div class="avatar-circle bg-primary-subtle text-primary me-3 fw-bold">
                            ${student.name.charAt(0).toUpperCase()}
                        </div>
                        ${student.name}
                    </div>
                </td>
                <td><span class="badge bg-secondary-subtle text-secondary px-3 py-2 rounded-pill">${student.department}</span></td>
                <td class="text-muted">${student.email}</td>
                <td class="text-end pe-4">
                    <button class="btn btn-sm btn-outline-danger rounded-pill px-3" onclick="deleteStudent(${student.id})">
                        <i class="fa-solid fa-trash me-1"></i> Delete
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Error loading students", e);
    }
}

async function deleteStudent(id) {
    if (!confirm('Are you sure you want to delete this student?')) return;
    try {
        const res = await fetch(`${API_BASE}/students/${id}`, { method: 'DELETE' });
        if (res.ok) {
            showAlert('Student deleted successfully!');
            loadStudents();
        }
    } catch (e) {
        console.error(e);
    }
}

// --- Add Student Logic ---
async function handleAddStudent(e) {
    e.preventDefault();
    const data = {
        name: document.getElementById('name').value,
        department: document.getElementById('department').value,
        email: document.getElementById('email').value
    };
    
    try {
        const res = await fetch(`${API_BASE}/students`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            window.location.href = 'students.html?added=true';
        }
    } catch (e) {
        console.error(e);
    }
}

// --- Attendance Logic ---
async function loadAttendance() {
    const dateInput = document.getElementById('date_select');
    let date = dateInput.value;
    
    // Set max date to today
    const today = new Date().toISOString().split('T')[0];
    dateInput.max = today;
    if (!date) {
        date = today;
        dateInput.value = date;
    }
    
    try {
        // Fetch students and attendance records
        const [studentsRes, attendanceRes] = await Promise.all([
            fetch(`${API_BASE}/students`),
            fetch(`${API_BASE}/attendance?date=${date}`)
        ]);
        const students = await studentsRes.json();
        const attendanceData = await attendanceRes.json();
        
        // Create map of existing records
        const recordMap = {};
        attendanceData.records.forEach(r => recordMap[r.student_id] = r.status);
        
        const tbody = document.getElementById('attendance-tbody');
        tbody.innerHTML = '';
        
        if (students.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center py-5 text-muted">No students found.</td></tr>`;
            document.getElementById('save-attendance-btn').style.display = 'none';
            return;
        }
        
        document.getElementById('save-attendance-btn').style.display = 'inline-block';
        
        students.forEach(student => {
            const status = recordMap[student.id];
            const isPresent = status === 'Present';
            const isAbsent = status === 'Absent';
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="ps-4 fw-bold text-muted">#${student.id}</td>
                <td class="fw-semibold">${student.name}</td>
                <td><span class="badge bg-secondary-subtle text-secondary px-3 py-2 rounded-pill">${student.department}</span></td>
                <td class="text-center pe-4">
                    <div class="btn-group rounded-pill shadow-sm" role="group">
                        <input type="radio" class="btn-check" name="status_${student.id}" id="present_${student.id}" value="Present" ${isPresent ? 'checked' : ''} required>
                        <label class="btn btn-outline-success px-4 rounded-start-pill" for="present_${student.id}"><i class="fa-solid fa-check me-1"></i> Present</label>

                        <input type="radio" class="btn-check" name="status_${student.id}" id="absent_${student.id}" value="Absent" ${isAbsent ? 'checked' : ''}>
                        <label class="btn btn-outline-danger px-4 rounded-end-pill" for="absent_${student.id}"><i class="fa-solid fa-xmark me-1"></i> Absent</label>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Error loading attendance", e);
    }
}

async function handleSaveAttendance(e) {
    e.preventDefault();
    const date = document.getElementById('date_select').value;
    const status_map = {};
    
    // Find all checked radio buttons
    const radios = document.querySelectorAll('input[type="radio"]:checked');
    radios.forEach(radio => {
        const studentId = radio.name.split('_')[1];
        status_map[studentId] = radio.value;
    });
    
    try {
        const res = await fetch(`${API_BASE}/attendance`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date, status_map })
        });
        if (res.ok) {
            showAlert(`Attendance saved for ${date}!`);
        }
    } catch (e) {
        console.error(e);
    }
}

// --- Reports Logic ---
async function loadReports() {
    try {
        const res = await fetch(`${API_BASE}/reports`);
        const reports = await res.json();
        const tbody = document.getElementById('reports-tbody');
        tbody.innerHTML = '';
        
        if (reports.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center py-5 text-muted">No attendance records available.</td></tr>`;
            return;
        }
        
        reports.forEach(report => {
            let bgClass = report.percentage >= 75 ? 'bg-success' : (report.percentage >= 50 ? 'bg-warning' : 'bg-danger');
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="ps-4 fw-semibold">
                    <div class="d-flex align-items-center">
                        <div class="avatar-circle bg-primary-subtle text-primary me-3 fw-bold">
                            ${report.name.charAt(0).toUpperCase()}
                        </div>
                        ${report.name}
                    </div>
                </td>
                <td class="text-center fw-bold text-success">${report.present_days}</td>
                <td class="text-center fw-bold text-danger">${report.absent_days}</td>
                <td class="text-end pe-4">
                    <div class="d-flex align-items-center justify-content-end">
                        <div class="progress me-3 w-50" style="height: 10px;">
                            <div class="progress-bar ${bgClass}" role="progressbar" style="width: ${report.percentage}%;"></div>
                        </div>
                        <span class="badge ${bgClass} rounded-pill py-2 px-3">${report.percentage}%</span>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Error loading reports", e);
    }
}

// --- Routing ---
document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;
    
    // Check url params for alerts
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('added') === 'true') {
        showAlert('Student added successfully!');
        window.history.replaceState(null, '', window.location.pathname);
    }
    
    if (path.includes('dashboard.html')) {
        loadDashboard();
    } else if (path.includes('students.html')) {
        loadStudents();
        
        // Search form listener
        const searchForm = document.getElementById('search-form');
        if (searchForm) {
            searchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const query = document.getElementById('search-input').value;
                loadStudents(query);
            });
        }
    } else if (path.includes('add_student.html')) {
        const form = document.getElementById('add-student-form');
        if (form) form.addEventListener('submit', handleAddStudent);
    } else if (path.includes('attendance.html')) {
        loadAttendance();
        const dateSelect = document.getElementById('date_select');
        if (dateSelect) dateSelect.addEventListener('change', loadAttendance);
        
        const form = document.getElementById('attendance-form');
        if (form) form.addEventListener('submit', handleSaveAttendance);
    } else if (path.includes('reports.html')) {
        loadReports();
    }
});
