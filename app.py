from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import sqlite3, os, random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'srms-secret-key-2024'
DB_PATH = os.path.join(os.path.dirname(__file__), 'srms.db')

# ─── DB helpers ───────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def query(sql, args=(), one=False, commit=False):
    conn = get_db()
    cur = conn.execute(sql, args)
    if commit:
        conn.commit()
        lastrowid = cur.lastrowid
        conn.close()
        return lastrowid
    rv = cur.fetchone() if one else cur.fetchall()
    conn.close()
    return rv

def execute_many(sql, data):
    conn = get_db()
    conn.executemany(sql, data)
    conn.commit()
    conn.close()

# ─── Grade ────────────────────────────────────────────────────────────────────
def calc_grade(total):
    if total >= 90: return 'O',  10.0
    if total >= 80: return 'A+',  9.0
    if total >= 70: return 'A',   8.0
    if total >= 60: return 'B+',  7.0
    if total >= 50: return 'B',   6.0
    if total >= 40: return 'C',   5.0
    return 'F', 0.0

def calc_sgpa(student_id, semester=None):
    if semester:
        rows = query('''SELECT r.grade_point, s.credits FROM results r
                        JOIN subjects s ON r.subject_id=s.id
                        WHERE r.student_id=? AND r.semester=?''', (student_id, semester))
    else:
        rows = query('''SELECT r.grade_point, s.credits FROM results r
                        JOIN subjects s ON r.subject_id=s.id
                        WHERE r.student_id=?''', (student_id,))
    if not rows: return 0.0
    total_credits = sum(r['credits'] for r in rows)
    weighted = sum(r['grade_point'] * r['credits'] for r in rows)
    return round(weighted / total_credits, 2) if total_credits else 0.0

# ─── Auth helpers ─────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def d(*a, **kw):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*a, **kw)
    return d

def admin_required(f):
    @wraps(f)
    def d(*a, **kw):
        if session.get('role') not in ('admin','teacher'):
            flash('Access denied.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*a, **kw)
    return d

# ─── Routes: Auth ─────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = query('SELECT * FROM users WHERE username=?', (request.form['username'],), one=True)
        if user and check_password_hash(user['password'], request.form['password']):
            session.update({'user_id': user['id'], 'role': user['role'], 'name': user['name']})
            flash(f"Welcome back, {user['name']}!", 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear(); flash('Logged out.', 'info')
    return redirect(url_for('login'))

# ─── Dashboard ────────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    if session['role'] in ('admin','teacher'):
        stats = {
            'students': query('SELECT COUNT(*) c FROM students', one=True)['c'],
            'subjects': query('SELECT COUNT(*) c FROM subjects', one=True)['c'],
            'departments': query('SELECT COUNT(*) c FROM departments', one=True)['c'],
            'results': query('SELECT COUNT(*) c FROM results', one=True)['c'],
        }
        recent = query('''SELECT r.total_marks, r.grade, st.name sname, st.roll_no,
                          su.name subname FROM results r
                          JOIN students st ON r.student_id=st.id
                          JOIN subjects su ON r.subject_id=su.id
                          ORDER BY r.id DESC LIMIT 5''')
        return render_template('dashboard_admin.html', stats=stats, recent_results=recent)
    else:
        student = query('SELECT * FROM students WHERE user_id=?', (session['user_id'],), one=True)
        results = []
        sgpa = 0
        if student:
            results = query('''SELECT r.*, su.name subname, su.code subcode, su.credits
                               FROM results r JOIN subjects su ON r.subject_id=su.id
                               WHERE r.student_id=? ORDER BY r.semester, su.name''', (student['id'],))
            sgpa = calc_sgpa(student['id'])
            dept = query('SELECT * FROM departments WHERE id=?', (student['dept_id'],), one=True)
            return render_template('dashboard_student.html', student=student, dept=dept,
                                   results=results, sgpa=sgpa)
        return render_template('dashboard_student.html', student=None, results=[], sgpa=0)

# ─── Students ─────────────────────────────────────────────────────────────────
@app.route('/students')
@login_required
@admin_required
def students():
    dept_id = request.args.get('dept_id', type=int)
    semester = request.args.get('semester', type=int)
    sql = '''SELECT s.*, d.code dcode, d.name dname FROM students s
             JOIN departments d ON s.dept_id=d.id WHERE 1=1'''
    args = []
    if dept_id: sql += ' AND s.dept_id=?'; args.append(dept_id)
    if semester: sql += ' AND s.semester=?'; args.append(semester)
    sql += ' ORDER BY s.name'
    students = query(sql, args)
    depts = query('SELECT * FROM departments ORDER BY name')
    return render_template('students.html', students=students, departments=depts,
                           dept_id=dept_id, semester=semester)

@app.route('/students/add', methods=['GET','POST'])
@login_required
@admin_required
def add_student():
    if request.method == 'POST':
        f = request.form
        roll = f['roll_no']
        if query('SELECT id FROM students WHERE roll_no=?', (roll,), one=True):
            flash('Roll number already exists!', 'danger')
        else:
            pwd = f.get('password') or roll
            uid = query('INSERT INTO users(username,password,role,name,email) VALUES(?,?,?,?,?)',
                        (roll, generate_password_hash(pwd), 'student', f['name'], f['email']), commit=True)
            query('INSERT INTO students(roll_no,name,email,phone,semester,year,dept_id,user_id) VALUES(?,?,?,?,?,?,?,?)',
                  (roll, f['name'], f['email'], f.get('phone',''), int(f['semester']),
                   int(f['year']), int(f['dept_id']), uid), commit=True)
            flash(f"Student {f['name']} added!", 'success')
            return redirect(url_for('students'))
    return render_template('add_student.html', departments=query('SELECT * FROM departments'))

@app.route('/students/<int:sid>/edit', methods=['GET','POST'])
@login_required
@admin_required
def edit_student(sid):
    student = query('SELECT * FROM students WHERE id=?', (sid,), one=True)
    if request.method == 'POST':
        f = request.form
        query('UPDATE students SET name=?,email=?,phone=?,semester=?,year=?,dept_id=? WHERE id=?',
              (f['name'],f['email'],f.get('phone',''),int(f['semester']),int(f['year']),int(f['dept_id']),sid), commit=True)
        flash('Student updated!', 'success')
        return redirect(url_for('students'))
    return render_template('edit_student.html', student=student,
                           departments=query('SELECT * FROM departments'))

@app.route('/students/<int:sid>/delete', methods=['POST'])
@login_required
@admin_required
def delete_student(sid):
    query('DELETE FROM results WHERE student_id=?', (sid,), commit=True)
    query('DELETE FROM students WHERE id=?', (sid,), commit=True)
    flash('Student deleted.', 'info')
    return redirect(url_for('students'))

@app.route('/students/<int:sid>/results')
@login_required
def student_results(sid):
    if session['role'] == 'student':
        own = query('SELECT * FROM students WHERE user_id=?', (session['user_id'],), one=True)
        if not own or own['id'] != sid:
            flash('Access denied.', 'danger'); return redirect(url_for('dashboard'))
    student = query('SELECT s.*, d.name dname, d.code dcode FROM students s JOIN departments d ON s.dept_id=d.id WHERE s.id=?', (sid,), one=True)
    results = query('''SELECT r.*, su.name subname, su.code subcode, su.credits
                       FROM results r JOIN subjects su ON r.subject_id=su.id
                       WHERE r.student_id=? ORDER BY r.semester, su.name''', (sid,))
    sems = sorted(set(r['semester'] for r in results))
    sgpa_by_sem = {s: calc_sgpa(sid, s) for s in sems}
    cgpa = calc_sgpa(sid)
    return render_template('student_results.html', student=student, results=results,
                           sgpa_by_sem=sgpa_by_sem, overall_cgpa=cgpa, sems=sems)

# ─── Results ──────────────────────────────────────────────────────────────────
@app.route('/results/enter', methods=['GET','POST'])
@login_required
@admin_required
def enter_results():
    if request.method == 'POST':
        f = request.form
        sid, subid = int(f['student_id']), int(f['subject_id'])
        internal, external = float(f.get('internal_marks',0)), float(f.get('external_marks',0))
        total = internal + external
        grade, gp = calc_grade(total)
        sem, yr = int(f['semester']), int(f['exam_year'])
        existing = query('SELECT id FROM results WHERE student_id=? AND subject_id=? AND exam_year=? AND semester=?',
                         (sid,subid,yr,sem), one=True)
        if existing:
            query('UPDATE results SET internal_marks=?,external_marks=?,total_marks=?,grade=?,grade_point=? WHERE id=?',
                  (internal,external,total,grade,gp,existing['id']), commit=True)
            flash('Result updated!', 'success')
        else:
            query('INSERT INTO results(student_id,subject_id,internal_marks,external_marks,total_marks,grade,grade_point,exam_year,semester) VALUES(?,?,?,?,?,?,?,?,?)',
                  (sid,subid,internal,external,total,grade,gp,yr,sem), commit=True)
            flash('Result saved!', 'success')
        return redirect(url_for('enter_results'))
    students = query('SELECT * FROM students ORDER BY name')
    subjects = query('SELECT * FROM subjects ORDER BY name')
    return render_template('enter_results.html', students=students, subjects=subjects,
                           current_year=datetime.now().year)

@app.route('/results/bulk', methods=['GET','POST'])
@login_required
@admin_required
def bulk_results():
    depts = query('SELECT * FROM departments')
    dept_id = request.args.get('dept_id', type=int)
    sem = request.args.get('semester', type=int)
    subj_id = request.args.get('subject_id', type=int)
    students, subjects, subject = [], [], None
    if dept_id and sem:
        students = query('SELECT * FROM students WHERE dept_id=? AND semester=? ORDER BY roll_no', (dept_id, sem))
        subjects = query('SELECT * FROM subjects WHERE dept_id=? AND semester=?', (dept_id, sem))
    if subj_id:
        subject = query('SELECT * FROM subjects WHERE id=?', (subj_id,), one=True)
    if request.method == 'POST':
        f = request.form
        yr, semester_val, s_id = int(f['exam_year']), int(f['semester']), int(f['subject_id'])
        saved = 0
        for key, val in f.items():
            if key.startswith('internal_'):
                sid = int(key.split('_')[1])
                internal = float(val or 0)
                external = float(f.get(f'external_{sid}', 0))
                total = internal + external
                grade, gp = calc_grade(total)
                existing = query('SELECT id FROM results WHERE student_id=? AND subject_id=? AND exam_year=? AND semester=?',
                                 (sid, s_id, yr, semester_val), one=True)
                if existing:
                    query('UPDATE results SET internal_marks=?,external_marks=?,total_marks=?,grade=?,grade_point=? WHERE id=?',
                          (internal,external,total,grade,gp,existing['id']), commit=True)
                else:
                    query('INSERT INTO results(student_id,subject_id,internal_marks,external_marks,total_marks,grade,grade_point,exam_year,semester) VALUES(?,?,?,?,?,?,?,?,?)',
                          (sid,s_id,internal,external,total,grade,gp,yr,semester_val), commit=True)
                saved += 1
        flash(f'{saved} results saved!', 'success')
        return redirect(url_for('bulk_results'))
    return render_template('bulk_results.html', departments=depts, students=students,
                           subjects=subjects, subject=subject, selected_dept=dept_id,
                           selected_sem=sem, selected_subject=subj_id,
                           current_year=datetime.now().year)

# ─── Subjects ─────────────────────────────────────────────────────────────────
@app.route('/subjects')
@login_required
@admin_required
def subjects():
    subjects = query('''SELECT s.*, d.name dname, d.code dcode FROM subjects s
                        JOIN departments d ON s.dept_id=d.id ORDER BY d.name, s.semester, s.name''')
    return render_template('subjects.html', subjects=subjects)

@app.route('/subjects/add', methods=['GET','POST'])
@login_required
@admin_required
def add_subject():
    if request.method == 'POST':
        f = request.form
        if query('SELECT id FROM subjects WHERE code=?', (f['code'],), one=True):
            flash('Code already exists!', 'danger')
        else:
            query('INSERT INTO subjects(name,code,credits,semester,dept_id) VALUES(?,?,?,?,?)',
                  (f['name'],f['code'],int(f['credits']),int(f['semester']),int(f['dept_id'])), commit=True)
            flash('Subject added!', 'success')
            return redirect(url_for('subjects'))
    return render_template('add_subject.html', departments=query('SELECT * FROM departments'))

@app.route('/subjects/<int:sid>/delete', methods=['POST'])
@login_required
@admin_required
def delete_subject(sid):
    query('DELETE FROM results WHERE subject_id=?', (sid,), commit=True)
    query('DELETE FROM subjects WHERE id=?', (sid,), commit=True)
    flash('Subject deleted.', 'info')
    return redirect(url_for('subjects'))

# ─── Departments ──────────────────────────────────────────────────────────────
@app.route('/departments')
@login_required
@admin_required
def departments():
    depts = query('''SELECT d.*,
                     (SELECT COUNT(*) FROM students WHERE dept_id=d.id) student_count,
                     (SELECT COUNT(*) FROM subjects WHERE dept_id=d.id) subject_count
                     FROM departments d''')
    return render_template('departments.html', departments=depts)

@app.route('/departments/add', methods=['GET','POST'])
@login_required
@admin_required
def add_department():
    if request.method == 'POST':
        f = request.form
        if query('SELECT id FROM departments WHERE code=?', (f['code'],), one=True):
            flash('Code already exists!', 'danger')
        else:
            query('INSERT INTO departments(name,code) VALUES(?,?)', (f['name'],f['code']), commit=True)
            flash('Department added!', 'success')
            return redirect(url_for('departments'))
    return render_template('add_department.html')

# ─── Reports ──────────────────────────────────────────────────────────────────
@app.route('/reports')
@login_required
@admin_required
def reports():
    return render_template('reports.html', departments=query('SELECT * FROM departments'))

@app.route('/reports/topper')
@login_required
@admin_required
def topper_report():
    dept_id = request.args.get('dept_id', type=int)
    semester = request.args.get('semester', type=int)
    sql = 'SELECT s.*, d.code dcode FROM students s JOIN departments d ON s.dept_id=d.id WHERE 1=1'
    args = []
    if dept_id: sql += ' AND s.dept_id=?'; args.append(dept_id)
    if semester: sql += ' AND s.semester=?'; args.append(semester)
    students = query(sql, args)
    toppers = [{'student': s, 'cgpa': calc_sgpa(s['id'])} for s in students]
    toppers.sort(key=lambda x: x['cgpa'], reverse=True)
    return render_template('topper_report.html', toppers=toppers,
                           departments=query('SELECT * FROM departments'),
                           dept_id=dept_id, semester=semester)

@app.route('/api/subjects_by_dept_sem')
@login_required
def api_subjects():
    dept_id = request.args.get('dept_id', type=int)
    semester = request.args.get('semester', type=int)
    rows = query('SELECT id,name,code FROM subjects WHERE dept_id=? AND semester=?', (dept_id, semester))
    return jsonify([dict(r) for r in rows])

# ─── DB Init ──────────────────────────────────────────────────────────────────
def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            code TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            semester INTEGER NOT NULL,
            year INTEGER NOT NULL,
            dept_id INTEGER NOT NULL,
            user_id INTEGER,
            FOREIGN KEY(dept_id) REFERENCES departments(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            credits INTEGER NOT NULL DEFAULT 3,
            semester INTEGER NOT NULL,
            dept_id INTEGER NOT NULL,
            FOREIGN KEY(dept_id) REFERENCES departments(id)
        );
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            internal_marks REAL DEFAULT 0,
            external_marks REAL DEFAULT 0,
            total_marks REAL DEFAULT 0,
            grade TEXT,
            grade_point REAL DEFAULT 0,
            exam_year INTEGER NOT NULL,
            semester INTEGER NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        );
    ''')
    conn.commit()
    # Seed data
    if not conn.execute('SELECT id FROM users WHERE username="admin"').fetchone():
        conn.execute('INSERT INTO users(username,password,role,name,email) VALUES(?,?,?,?,?)',
                     ('admin', generate_password_hash('admin123'), 'admin', 'Administrator', 'admin@srms.edu'))
        conn.execute('INSERT INTO users(username,password,role,name,email) VALUES(?,?,?,?,?)',
                     ('teacher1', generate_password_hash('teacher123'), 'teacher', 'Prof. Sharma', 'sharma@srms.edu'))
        conn.execute('INSERT INTO departments(name,code) VALUES(?,?)',
                     ('Master of Computer Applications', 'MCA'))
        conn.commit()
        dept_id = conn.execute('SELECT id FROM departments WHERE code="MCA"').fetchone()[0]
        subjects_data = [
            ('Data Structures & Algorithms', 'MCA101', 4, 1, dept_id),
            ('Database Management Systems', 'MCA102', 4, 1, dept_id),
            ('Computer Networks', 'MCA103', 3, 1, dept_id),
            ('Object Oriented Programming', 'MCA104', 4, 1, dept_id),
            ('Advanced Java Programming', 'MCA201', 4, 2, dept_id),
            ('Software Engineering', 'MCA202', 3, 2, dept_id),
            ('Web Technologies', 'MCA203', 3, 2, dept_id),
        ]
        conn.executemany('INSERT INTO subjects(name,code,credits,semester,dept_id) VALUES(?,?,?,?,?)', subjects_data)
        conn.commit()
        subject_ids_s1 = [r[0] for r in conn.execute('SELECT id FROM subjects WHERE semester=1').fetchall()]
        for i in range(1,5):
            uname = f'MCA2024{i:03d}'
            uid = conn.execute('INSERT INTO users(username,password,role,name,email) VALUES(?,?,?,?,?)',
                               (uname, generate_password_hash(uname), 'student', f'Student {i}', f'student{i}@srms.edu')).lastrowid
            sid = conn.execute('INSERT INTO students(roll_no,name,email,phone,semester,year,dept_id,user_id) VALUES(?,?,?,?,?,?,?,?)',
                               (uname, f'Student {i}', f'student{i}@srms.edu', f'9876543{i:03d}', 1, 2024, dept_id, uid)).lastrowid
            for subj_id in subject_ids_s1:
                internal = round(random.uniform(18, 30), 1)
                external = round(random.uniform(38, 70), 1)
                total = internal + external
                grade, gp = calc_grade(total)
                conn.execute('INSERT INTO results(student_id,subject_id,internal_marks,external_marks,total_marks,grade,grade_point,exam_year,semester) VALUES(?,?,?,?,?,?,?,?,?)',
                             (sid, subj_id, internal, external, total, grade, gp, 2024, 1))
        conn.commit()
        print("✅ Database seeded with sample data.")
    conn.close()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
