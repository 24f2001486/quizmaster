import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, static_folder='static', template_folder='templates')
# The SQLite file is created inside the Flask "instance" folder.
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///quizmaster.db')
# Set SECRET_KEY in the environment for any real deployment.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'quizmaster-dev-secret-key')
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
db = SQLAlchemy(app)

from app import models, routes, admin_routes, user_routes  # noqa: E402,F401

# Create the database tables programmatically and make sure the admin exists.
with app.app_context():
    db.create_all()
    models.create_default_admin(
        os.environ.get('ADMIN_USERNAME', 'Admin'),
        os.environ.get('ADMIN_PASSWORD', 'Admin'),
    )
