
from datetime import datetime
from app import app, db
from app.models import Admin, Chapter, User, Subject
from flask import jsonify, make_response, redirect, render_template, request, url_for

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
            resp = make_response(redirect(url_for('user_dashboard_page')))
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

@app.route('/admin_dash_page', methods=['GET'])    
def admin_dash_page():
    # get all subjects from subject table
    subjects = Subject.query.all()
    
    '''
        subject_with_chapters = [
            {
                "subjectname": "",
                "subjectdescription": "",
                "chapters": [
                    {
                        "chaptername": "",
                        "chapterdescription": "",
                        "numberofquestions": ""
                    },
                    {}
                ]
            },
            {}
        ]
    '''
    subject_with_chapters = []
    print("subjects: ", subjects)
    for subject in subjects:
        subject_with_chapters.append({
            "subjectname": subject.subject_name,
            "subjectdescription": subject.subject_description,
            "chapters": []
        })
        chapters = Chapter.query.filter_by(subject_id=subject.id).all()
        print("chapters: ", chapters)
        for chapter in chapters:
            subject_with_chapters[-1]["chapters"].append({
                "chaptername": chapter.chapter_name,
                "chapterdescription": chapter.chapter_description,
                "numberofquestions": chapter.no_of_questions
            })
    # print subject_with_chapters in string form
    print("subject_with_chapters: ", subject_with_chapters)

    return render_template('admin_dash_page.html', subject_with_chapters=subject_with_chapters)

@app.route('/auxroute_add_subject', methods=['POST'])
def auxroute_add_subject():
    try:
        data = request.json
        new_subject = Subject(subject_name=data['subject_name'], subject_description=data['subject_description'])
        db.session.add(new_subject)
        db.session.commit()
        return jsonify({'message': 'Subject added successfully'})
    except KeyError as e:
        return jsonify({'error': 'Missing key in request: {}'.format(e)}), 400
    except Exception as e:
        return jsonify({'error': 'An error occurred: {}'.format(e)}), 500

@app.route('/auxroute_add_chapter', methods=['POST'])
def auxroute_add_chapter():
    try:
        data = request.json
        new_chapter = Chapter(
            chapter_name=data['chapter_name'],
            chapter_description=data['chapter_description'],
            no_of_questions=data['no_of_questions'],
            subject_id=data['subject_id']  
        )
        db.session.add(new_chapter)
        db.session.commit()
        return jsonify({'message': 'Chapter added successfully'})
    except KeyError as e:
        return jsonify({'error': 'Missing key in request: {}'.format(e)}), 400
    except Exception as e:
        return jsonify({'error': 'An error occurred: {}'.format(e)}), 500

#create the edit_chapter and the delete_chapter routes
@app.route('/editchapter', methods=['PUT'])
def editchapter():
    try:
        data = request.json
        chapter = Chapter.query.filter_by(id=data['id']).first()
        chapter.chapter_name = data['chapter_name']
        chapter.chapter_description = data['chapter_description']
        chapter.no_of_questions = data['no_of_questions']
        db.session.commit()
        return jsonify({'message': 'Chapter edited successfully'})
    except KeyError as e:
        return jsonify({'error': 'Missing key in request: {}'.format(e)}), 400
    except Exception as e:
        return jsonify({'error': 'An error occurred: {}'.format(e)}), 500

@app.route('/deletechapter', methods=['DELETE'])
def deletechapter():
    try:
        data = request.json
        chapter = Chapter.query.filter_by(id=data['id']).first()
        db.session.delete(chapter)
        db.session.commit()
        return jsonify({'message': 'Chapter deleted successfully'})
    except KeyError as e:
        return jsonify({'error': 'Missing key in request: {}'.format(e)}), 400
    except Exception as e:
        return jsonify({'error': 'An error occurred: {}'.format(e)}), 500

