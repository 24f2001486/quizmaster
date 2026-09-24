import os

# Use an in-memory database so the tests never touch instance/quizmaster.db
os.environ['DATABASE_URL'] = 'sqlite://'

import pytest  # noqa: E402

from app import app as flask_app, db  # noqa: E402
from app.models import create_default_admin  # noqa: E402


@pytest.fixture
def app():
    flask_app.config['TESTING'] = True
    with flask_app.app_context():
        db.drop_all()
        db.create_all()
        create_default_admin('Admin', 'Admin')
        yield flask_app
        db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()
