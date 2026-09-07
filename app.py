import os
from datetime import datetime

from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret-key-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'school.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'teacher', 'student'

    # Courses this user teaches (if teacher)
    courses_taught = db.relationship('Course', backref='teacher', lazy=True)

    # Enrollments (if student)
    enrollments = db.relationship('Enrollment', backref='student', lazy=True,
                                   cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    enrollments = db.relationship('Enrollment', backref='course', lazy=True,
                                   cascade='all, delete-orphan')


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    grade = db.Column(db.String(5), nullable=True)  # e.g. "A", "B+", or a numeric score
    comment = db.Column(db.String(255), nullable=True)


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------------------------------------------------------------------
# Access-control helper
# ---------------------------------------------------------------------------

def role_required(*roles):
    def decorator(f):
        from functools import wraps

        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return decorator


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        username = request.form['username'].strip().lower()
        password = request.form['password']
        role = request.form['role']

        if role not in ('student', 'teacher'):
            # Admin accounts are not self-service; only these two can self-register
            flash('Invalid role selected.', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('That username is already taken.', 'error')
            return redirect(url_for('register'))

        user = User(full_name=full_name, username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))

        flash('Invalid username or password.', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ---------------------------------------------------------------------------
# Dashboard router (sends each role to its own view)
# ---------------------------------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(10).all()

    if current_user.role == 'admin':
        users = User.query.order_by(User.role, User.full_name).all()
        courses = Course.query.all()
        return render_template('admin_dashboard.html', users=users, courses=courses,
                                announcements=announcements)

    if current_user.role == 'teacher':
        courses = Course.query.filter_by(teacher_id=current_user.id).all()
        return render_template('teacher_dashboard.html', courses=courses,
                                announcements=announcements)

    # student
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    return render_template('student_dashboard.html', enrollments=enrollments,
                            announcements=announcements)


# ---------------------------------------------------------------------------
# Admin actions
# ---------------------------------------------------------------------------

@app.route('/admin/course/new', methods=['POST'])
@role_required('admin')
def new_course():
    name = request.form['name'].strip()
    code = request.form['code'].strip().upper()
    teacher_id = request.form.get('teacher_id') or None

    if Course.query.filter_by(code=code).first():
        flash('A course with that code already exists.', 'error')
        return redirect(url_for('dashboard'))

    course = Course(name=name, code=code, teacher_id=teacher_id)
    db.session.add(course)
    db.session.commit()
    flash(f'Course "{name}" created.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/admin/enroll', methods=['POST'])
@role_required('admin')
def enroll_student():
    student_id = request.form['student_id']
    course_id = request.form['course_id']

    exists = Enrollment.query.filter_by(student_id=student_id, course_id=course_id).first()
    if exists:
        flash('Student is already enrolled in that course.', 'error')
        return redirect(url_for('dashboard'))

    enrollment = Enrollment(student_id=student_id, course_id=course_id)
    db.session.add(enrollment)
    db.session.commit()
    flash('Student enrolled.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@role_required('admin')
def delete_user(user_id):
    if user_id == current_user.id:
        flash("You can't delete your own account.", 'error')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'User "{user.full_name}" deleted.', 'success')
    return redirect(url_for('dashboard'))


# ---------------------------------------------------------------------------
# Teacher actions
# ---------------------------------------------------------------------------

@app.route('/teacher/grade', methods=['POST'])
@role_required('teacher')
def submit_grade():
    enrollment_id = request.form['enrollment_id']
    grade = request.form['grade'].strip()
    comment = request.form.get('comment', '').strip()

    enrollment = Enrollment.query.get_or_404(enrollment_id)

    # make sure this teacher actually owns the course
    if enrollment.course.teacher_id != current_user.id:
        abort(403)

    enrollment.grade = grade
    enrollment.comment = comment
    db.session.commit()
    flash('Grade updated.', 'success')
    return redirect(url_for('dashboard'))


# ---------------------------------------------------------------------------
# Shared: announcements (admin + teacher can post)
# ---------------------------------------------------------------------------

@app.route('/announcement/new', methods=['POST'])
@role_required('admin', 'teacher')
def new_announcement():
    title = request.form['title'].strip()
    body = request.form['body'].strip()

    announcement = Announcement(title=title, body=body, author_id=current_user.id)
    db.session.add(announcement)
    db.session.commit()
    flash('Announcement posted.', 'success')
    return redirect(url_for('dashboard'))


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403,
                            message="You don't have permission to do that."), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message="Page not found."), 404


# ---------------------------------------------------------------------------
# CLI helper: create the database and a default admin account
# ---------------------------------------------------------------------------

@app.cli.command('init-db')
def init_db():
    """Create tables and a default admin (username: admin / password: admin123)."""
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(full_name='Site Administrator', username='admin', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('Database created. Default admin login -> username: admin / password: admin123')
    else:
        print('Database already initialized.')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(full_name='Site Administrator', username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('Created default admin -> username: admin / password: admin123')
    app.run(debug=True)
