# Student Result Management System (SRMS)
### MCA Major Project | Python + Flask + SQLite

---

## 📋 Project Overview

A full-featured web application for managing student academic results, built with Python Flask. Supports three roles: **Admin**, **Teacher**, and **Student** — each with their own dashboard and permissions.

---

## 🏗️ Project Structure

```
student_result_system/
├── app.py                   # Main Flask application
├── requirements.txt         # Python dependencies
├── instance/
│   └── srms.db             # SQLite database (auto-created)
└── templates/
    ├── base.html            # Master layout with sidebar
    ├── login.html           # Login page
    ├── dashboard_admin.html # Admin/Teacher dashboard
    ├── dashboard_student.html
    ├── students.html
    ├── add_student.html
    ├── edit_student.html
    ├── student_results.html
    ├── subjects.html
    ├── add_subject.html
    ├── departments.html
    ├── add_department.html
    ├── enter_results.html
    ├── bulk_results.html
    ├── reports.html
    └── topper_report.html
```

---

## 🚀 Setup & Running

### 1. Install Python (3.9+ required)
### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the application
```bash
python app.py
```

### 4. Open browser
```
http://localhost:5000
```

The database is **auto-initialized** with sample data on first run.

---

## 🔐 Demo Login Credentials

| Role    | Username     | Password     |
|---------|-------------|--------------|
| Admin   | admin        | admin123     |
| Teacher | teacher1     | teacher123   |
| Student | MCA2024001   | MCA2024001   |
| Student | MCA2024002   | MCA2024002   |

---

## ✨ Features

### Admin / Teacher
- **Dashboard** — Stats overview: total students, subjects, results, departments
- **Student Management** — Add, edit, delete students; filter by dept/semester
- **Subject Management** — Add/delete subjects with credits & semester
- **Department Management** — Manage academic departments
- **Single Result Entry** — Enter marks for one student/subject at a time
- **Bulk Result Entry** — Enter marks for entire class in one form
- **Topper Report** — Ranked list by CGPA with filtering
- **Student Result Viewer** — Per-student results with SGPA breakdown

### Student
- **Personal Dashboard** — View own profile, all results, CGPA
- **Semester-wise SGPA** — Breakdown per semester
- **Full Marksheet** — Internal + External + Total + Grade + Grade Point

---

## 📊 Grading System

| Marks    | Grade | Grade Point |
|----------|-------|-------------|
| 90–100   | O     | 10.0        |
| 80–89    | A+    | 9.0         |
| 70–79    | A     | 8.0         |
| 60–69    | B+    | 7.0         |
| 50–59    | B     | 6.0         |
| 40–49    | C     | 5.0         |
| Below 40 | F     | 0.0         |

- **Internal Marks**: out of 30
- **External Marks**: out of 70
- **Total**: out of 100
- **SGPA/CGPA**: Weighted by subject credits

---

## 🗄️ Database Models

| Model      | Description                       |
|------------|-----------------------------------|
| User       | Login accounts for all roles      |
| Department | Academic departments              |
| Student    | Student profiles linked to users  |
| Subject    | Course subjects with credits      |
| Result     | Marks per student per subject     |

---

## 🛠️ Tech Stack

| Component  | Technology          |
|------------|---------------------|
| Backend    | Python 3.x + Flask  |
| ORM        | Flask-SQLAlchemy    |
| Database   | SQLite              |
| Frontend   | HTML5 + CSS3 + Jinja2 |
| Auth       | Werkzeug (hashed passwords) |
| Icons      | Font Awesome 6      |
| Fonts      | Google Fonts (Playfair Display + DM Sans) |

---

## 📝 Key Concepts Demonstrated

1. **MVC Architecture** — Models (SQLAlchemy), Views (Jinja2 templates), Controllers (Flask routes)
2. **Role-Based Access Control** — Decorators for admin/teacher/student separation
3. **One-to-Many Relationships** — Department→Students, Student→Results, Subject→Results
4. **Session Management** — Secure login with Flask sessions
5. **Password Hashing** — Werkzeug PBKDF2 hashing
6. **CRUD Operations** — Full Create/Read/Update/Delete for all entities
7. **Dynamic Grade Calculation** — Auto-computed grades and grade points
8. **CGPA/SGPA Algorithm** — Credit-weighted average calculation
9. **RESTful API endpoint** — `/api/subjects_by_dept_sem` JSON endpoint
10. **Flash Messages** — User feedback on all operations

---

## 🔮 Future Enhancements

- PDF marksheet/report card generation
- Excel import/export for bulk data
- Email notifications for published results
- Attendance tracking module
- Fee management integration
- Chart visualizations for performance trends
- Mobile-responsive PWA

---

*Developed as MCA Major Project — Academic Year 2024–25*
