
from datetime import date, datetime
from functools import wraps

from flask import flash, g, redirect, render_template, request, session, url_for
from sqlalchemy import func

from app import app, db
from app.models import Admin, User


@app.before_request
def load_logged_in_user():
    g.user = None
    g.is_admin = False
    if request.endpoint == 'static':
        return
    role = session.get('role')
    if role == 'admin':
        g.is_admin = db.session.get(Admin, session.get('user_id')) is not None
    elif role == 'user':
        g.user = db.session.get(User, session.get('user_id'))


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not g.is_admin:
            flash('Please login as admin to continue.', 'warning')
            return redirect(url_for('user_login_page'))
        return view(*args, **kwargs)
    return wrapped_view


def user_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('user_login_page'))
        return view(*args, **kwargs)
    return wrapped_view


@app.route('/')
def index():
    if g.is_admin:
        return redirect(url_for('admin_dash_page'))
    if g.user:
        return redirect(url_for('user_dashboard_page'))
    return render_template('index.html')

# user_login.html (the admin logs in from the same page)
@app.route('/user_login_page', methods=['GET', 'POST'])
def user_login_page():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            session.clear()
            session['role'] = 'admin'
            session['user_id'] = admin.id
            return redirect(url_for('admin_dash_page'))

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session.clear()
            session['role'] = 'user'
            session['user_id'] = user.id
            return redirect(url_for('user_dashboard_page'))

        return render_template('user_login_error.html', message='Invalid username and/or password. Please try again.')

    return render_template('user_login.html')


@app.route('/user_register_page', methods=['GET', 'POST'])
def user_register_page():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        qualification = request.form.get('qualification', '').strip()
        dob_str = request.form.get('dob', '')

        if not all([username, password, full_name, qualification, dob_str]):
            return render_template('user_register_confirmation.html', message="All fields are required. Please try again.")

        try:
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        except ValueError:
            return render_template('user_register_confirmation.html', message="Invalid date of birth. Please try again.")
        if dob >= date.today():
            return render_template('user_register_confirmation.html', message="Date of birth must be in the past.")

        if Admin.query.filter(func.lower(Admin.username) == username.lower()).first():
            return render_template('user_register_confirmation.html', message="This username is reserved. Please try with different username.")

        if User.query.filter_by(username=username).first():
            return render_template('user_register_confirmation.html', message="Username already exists. Please try with different username.")

        new_user = User(username=username, full_name=full_name, qualification=qualification, dob=dob)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        return render_template('user_register_confirmation.html', message="User created successfully. Please login to continue.")

    return render_template('user_register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))
