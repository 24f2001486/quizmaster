import time
from datetime import date, timedelta

from app import db
from app.admin_routes import parse_duration
from app.models import Chapter, Question, Quiz, Scores, Subject, User


def login(client, username, password):
    return client.post('/user_login_page', data={'username': username, 'password': password})


def register(client, username='student', password='secret'):
    return client.post('/user_register_page', data={
        'username': username,
        'password': password,
        'full_name': 'Test Student',
        'qualification': 'B.Sc',
        'dob': '2000-01-15',
    })


def make_quiz(date_of_quiz=None, time_duration=10):
    subject = Subject(subject_name='Physics', subject_description='Science subject')
    chapter = Chapter(chapter_name='Force', chapter_description='Chapter I', subject=subject)
    quiz = Quiz(quiz_name='Force Basics', chapter=chapter, time_duration=time_duration,
                date_of_quiz=date_of_quiz or date.today())
    quiz.questions = [
        Question(question_statement='Unit of force?', option1='Newton', option2='Joule',
                 option3='Watt', option4='Pascal', correct_option=1),
        Question(question_statement='F = ?', option1='mv', option2='ma',
                 option3='mgh', option4='mv^2', correct_option=2),
    ]
    db.session.add(subject)
    db.session.commit()
    return quiz


def test_public_pages_render(client):
    for url in ('/', '/user_login_page', '/user_register_page'):
        assert client.get(url).status_code == 200


def test_register_and_login_user(client):
    response = register(client)
    assert b'User created successfully' in response.data
    user = User.query.filter_by(username='student').one()
    assert user.password != 'secret'  # stored as a hash

    response = login(client, 'student', 'secret')
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/user_dashboard_page')
    assert b'Welcome Test Student' in client.get('/user_dashboard_page').data


def test_register_rejects_duplicate_and_reserved_usernames(client):
    register(client)
    assert b'Username already exists' in register(client).data
    assert b'This username is reserved' in register(client, username='admin').data
    # Users may share a qualification
    assert b'User created successfully' in register(client, username='another').data


def test_invalid_login(client):
    register(client)
    assert b'Invalid username and/or password' in login(client, 'student', 'wrong').data
    assert b'Invalid username and/or password' in login(client, 'Admin', 'wrong').data


def test_access_control(client):
    assert client.get('/admin_dash_page').status_code == 302
    assert client.get('/user_dashboard_page').status_code == 302

    register(client)
    login(client, 'student', 'secret')
    assert client.get('/admin_dash_page').status_code == 302
    assert client.post('/admin/subject/new', data={'subject_name': 'X', 'subject_description': 'Y'}).status_code == 302
    assert Subject.query.count() == 0

    client.get('/logout')
    login(client, 'Admin', 'Admin')
    assert client.get('/admin_dash_page').status_code == 200
    assert client.get('/user_dashboard_page').status_code == 302


def test_admin_manages_subjects_chapters_quizzes_and_questions(client):
    login(client, 'Admin', 'Admin')

    client.post('/admin/subject/new', data={'subject_name': 'Physics', 'subject_description': 'Science'})
    subject = Subject.query.one()
    response = client.post('/admin/subject/new', data={'subject_name': 'physics', 'subject_description': 'Dup'})
    assert b'already exists' in response.data

    client.post('/admin/subject/{}/chapter/new'.format(subject.id),
                data={'chapter_name': 'Force', 'chapter_description': 'Chapter I'})
    chapter = Chapter.query.one()

    client.post('/admin/quiz/new', data={'quiz_name': 'Quiz 1', 'chapter_id': chapter.id,
                                         'date_of_quiz': date.today().isoformat(),
                                         'time_duration': '01:30', 'remarks': ''})
    quiz = Quiz.query.one()
    assert quiz.time_duration == 90
    assert quiz.duration_hhmm == '01:30'

    response = client.post('/admin/quiz/{}/question/new'.format(quiz.id), data={
        'question_statement': 'Unit of force?', 'option1': 'Newton', 'option2': 'Joule',
        'option3': 'Watt', 'option4': 'Pascal', 'correct_option': '1'})
    assert response.status_code == 302
    question = Question.query.one()
    assert question.correct_option == 1
    assert chapter.no_of_questions == 1

    response = client.post('/admin/question/{}/edit'.format(question.id), data={
        'question_statement': 'Unit of force?', 'option1': 'Newton', 'option2': 'Newton',
        'option3': 'Watt', 'option4': 'Pascal', 'correct_option': '1'})
    assert b'must be different' in response.data

    client.post('/admin/subject/{}/edit'.format(subject.id),
                data={'subject_name': 'Physics II', 'subject_description': 'Updated'})
    assert db.session.get(Subject, subject.id).subject_name == 'Physics II'

    for url in ('/admin_dash_page', '/admin/quizzes', '/admin/quizzes?chapter_id={}'.format(chapter.id),
                '/admin/users', '/admin/summary', '/admin/search?q=force',
                '/admin/quiz/{}/edit'.format(quiz.id), '/admin/question/{}/edit'.format(question.id)):
        assert client.get(url).status_code == 200, url

    # Deleting a subject removes everything under it
    client.post('/admin/subject/{}/delete'.format(subject.id))
    assert Subject.query.count() == Chapter.query.count() == Quiz.query.count() == Question.query.count() == 0


def test_admin_search_finds_users_and_content(client):
    make_quiz()
    register(client, username='findme')
    login(client, 'Admin', 'Admin')
    data = client.get('/admin/search?q=findme').data
    assert b'findme' in data
    data = client.get('/admin/search?q=newton').data
    assert b'Unit of force?' not in data  # options are not searched
    data = client.get('/admin/search?q=unit of').data
    assert b'Unit of force?' in data
    assert b'No results found' in client.get('/admin/search?q=zzz%25').data


def test_user_attempts_quiz_and_score_is_recorded(client):
    quiz = make_quiz()
    first, second = quiz.questions
    register(client)
    login(client, 'student', 'secret')

    assert b'Force Basics' in client.get('/user_dashboard_page').data
    response = client.get('/quiz/{}/start'.format(quiz.id))
    assert response.status_code == 200
    assert b'Unit of force?' in response.data

    response = client.post('/quiz/{}/submit'.format(quiz.id), data={
        'question_{}'.format(first.id): '1',
        'question_{}'.format(second.id): '3',
    })
    assert response.status_code == 200
    assert b'1 / 2' in response.data

    score = Scores.query.one()
    assert (score.total_scored, score.total_questions, score.percentage) == (1, 2, 50)

    # The attempt is used up, so submitting again is rejected
    response = client.post('/quiz/{}/submit'.format(quiz.id), data={})
    assert response.status_code == 302
    assert Scores.query.count() == 1

    for url in ('/scores', '/summary', '/search?q=physics', '/quiz/{}'.format(quiz.id)):
        response = client.get(url)
        assert response.status_code == 200, url
        assert b'Force Basics' in response.data or b'subjectChart' in response.data


def test_submit_after_time_limit_is_rejected(client):
    quiz = make_quiz(time_duration=1)
    register(client)
    login(client, 'student', 'secret')
    client.get('/quiz/{}/start'.format(quiz.id))
    with client.session_transaction() as session:
        session['attempt'] = {'quiz_id': quiz.id, 'started_at': time.time() - 60 - 31}
    client.post('/quiz/{}/submit'.format(quiz.id), data={})
    assert Scores.query.count() == 0


def test_refreshing_quiz_keeps_timer_running(client):
    quiz = make_quiz(time_duration=10)
    register(client)
    login(client, 'student', 'secret')
    client.get('/quiz/{}/start'.format(quiz.id))
    with client.session_transaction() as session:
        session['attempt'] = {'quiz_id': quiz.id, 'started_at': time.time() - 120}
    response = client.get('/quiz/{}/start'.format(quiz.id))
    assert b'data-remaining="480"' in response.data or b'data-remaining="479"' in response.data


def test_upcoming_and_empty_quizzes_cannot_be_started(client):
    quiz = make_quiz(date_of_quiz=date.today() + timedelta(days=3))
    empty = Quiz(quiz_name='Empty', chapter=quiz.chapter, time_duration=5)
    db.session.add(empty)
    db.session.commit()
    register(client)
    login(client, 'student', 'secret')

    dashboard = client.get('/user_dashboard_page').data
    assert b'Upcoming Quizzes' in dashboard
    assert b'Empty' not in dashboard
    for quiz_id in (quiz.id, empty.id):
        assert client.get('/quiz/{}/start'.format(quiz_id)).status_code == 302


def test_deleting_user_removes_scores(client):
    quiz = make_quiz()
    register(client)
    user = User.query.one()
    db.session.add(Scores(user_id=user.id, quiz_id=quiz.id, total_scored=1, total_questions=2))
    db.session.commit()

    login(client, 'Admin', 'Admin')
    assert b'student' in client.get('/admin/users').data
    client.post('/admin/user/{}/delete'.format(user.id))
    assert User.query.count() == Scores.query.count() == 0


def test_parse_duration():
    assert parse_duration('00:30') == 30
    assert parse_duration('2:05') == 125
    assert parse_duration('00:00') is None
    assert parse_duration('1:75') is None
    assert parse_duration('abc') is None
