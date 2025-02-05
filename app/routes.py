
from datetime import datetime
from app import app, db
from app.models import Admin, User
from flask import make_response, redirect, render_template, request, url_for

@app.route('/')
def index():
    if Admin.query.filter_by(username='Admin').first() is None:
        admin =  Admin(username="Admin",password = "Admin")
        db.session.add(admin)
        db.session.commit()
    return render_template('index.html')

# user_login.html
@app.route('/user_login_page', methods=['GET', 'POST'])
def user_login_page():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
       
        if username == 'Admin' and password == 'Admin':
            resp = make_response(redirect(url_for('admin_dash_page')))
            resp.set_cookie('username', username)
            return resp
        elif username == 'Admin' and password != 'Admin':
            return render_template('user_login_error.html', message='Invalid username and/or password. Please try again.')
        
        # Query the database for the user with the given username
        try:
            user = User.query.filter_by(username=username).one()
        except Exception as e:
            user = None
       
        # Check if the user exists and the password is correct
        if user and user.password == password:
            # Redirect to a different route on successful login
            resp = make_response(redirect(url_for('user_dash_my_books_page')))
            resp.set_cookie('username', username)
            return resp
        
        # Redirect to the login page with an error message
        return render_template('user_login_error.html', message='Invalid username and/or password. Please try again.')
   
    # Render the login page template for GET requests
    return render_template('user_login.html')


@app.route('/user_register_page', methods=['GET', 'POST'])
def user_register_page():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        qualification = request.form['qualification']
        dob_str = request.form['dob']
       
        dob = datetime.strptime(dob_str, '%Y-%m-%dT%H:%M')
        user = User.query.filter_by(username=username).first()
        if user:
            return render_template('user_register_confirmation.html',message = "Username already exists. Please try with different username.")
        
        if username == 'Admin':
            return render_template('user_register_confirmation.html',message = "Username with the name Admin not allowed. Please try with different username.")
        
        new_user = User(username=username,password = password, full_name = full_name,qualification = qualification,dob = dob)
        db.session.add(new_user)
        db.session.commit()
        return render_template('user_register_confirmation.html', message = "User created successfully. Please login to continue.")
    


 # Render the register page template for GET requests
    return render_template('user_register.html')