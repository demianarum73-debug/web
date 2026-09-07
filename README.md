# School Portal

A full-featured school portal with real authentication, a SQLite database, and
three roles: **Admin**, **Teacher**, and **Student**.

## Features

- Secure login/registration (passwords are hashed, never stored in plain text)
- **Admin**: create courses, assign teachers, enroll students, delete users, post announcements
- **Teacher**: view their courses, enter/update grades and comments per student, post announcements
- **Student**: view enrolled courses, grades, and comments
- Shared announcements board visible to everyone
- Role-based access control (each route checks the logged-in user's role)

## Setup

1. **Install Python 3.9+** if you don't already have it.

2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app:**
   ```bash
   python app.py
   ```
   On first run this automatically creates `school.db` (SQLite) and a default
   admin account:
   - Username: `admin`
   - Password: `admin123`

5. Open your browser to **http://127.0.0.1:5000**

## Typical workflow

1. Log in as `admin` / `admin123`.
2. Register a teacher and a few student accounts from the **Register** page
   (or have them self-register — students/teachers can sign themselves up;
   only admin accounts must be created directly).
3. As admin, create a course and assign it to the teacher.
4. As admin, enroll students into that course.
5. Log in as the teacher to enter grades and comments.
6. Log in as a student to see their grades.

## Important notes before deploying publicly

This is a solid local/learning-project foundation, but before putting it on
the open internet you should:

- Change `app.config['SECRET_KEY']` in `app.py` to a long random value (never
  commit the real value to a public repo).
- Turn off debug mode (`app.run(debug=True)` → `app.run(debug=False)`) — debug
  mode can leak sensitive data and allow code execution if the debugger PIN
  is exposed.
- Use a production database (PostgreSQL/MySQL) instead of SQLite once you
  have concurrent users.
- Run behind a real WSGI server (e.g. `gunicorn`) rather than Flask's
  built-in dev server.
- Add HTTPS (most hosts like Render, Railway, or PythonAnywhere provide this
  automatically).
- Add rate-limiting/CAPTCHA on login and registration to deter brute-force
  and spam sign-ups.

## Project structure

```
school_portal/
├── app.py                  # Flask app: models, routes, auth
├── requirements.txt
├── school.db                # created automatically on first run
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── login.html
    ├── register.html
    ├── admin_dashboard.html
    ├── teacher_dashboard.html
    ├── student_dashboard.html
    ├── _announcements.html
    └── error.html
```
