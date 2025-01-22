from app import app, db

if __name__ == '__main__':
    with app.app_context():
        # Create the SQLite database and tables
        db.create_all()
    app.run(debug=True)