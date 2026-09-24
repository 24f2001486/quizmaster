from app import app

if __name__ == '__main__':
    # The database tables and the admin account are created in app/__init__.py
    app.run(debug=True)
