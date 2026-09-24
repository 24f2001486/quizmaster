
import re
from datetime import date, datetime

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy import func, or_

from app import app, db
from app.models import Chapter, Question, Quiz, Scores, Subject, User
from app.routes import admin_required

# A score as a percentage of the questions in the quiz, usable inside SQL queries
SCORE_PERCENT = Scores.total_scored * 100.0 / Scores.total_questions


def parse_duration(value):
    """Convert an 'HH:MM' string into minutes. Returns None when invalid or zero."""
    match = re.fullmatch(r'(\d{1,2}):([0-5]\d)', value.strip())
    if not match:
        return None
    minutes = int(match.group(1)) * 60 + int(match.group(2))
    return minutes or None


def quiz_redirect(quiz):
    return redirect(url_for('admin_quizzes', _anchor='quiz-{}'.format(quiz.id)))


@app.route('/admin_dash_page', methods=['GET'])
@admin_required
def admin_dash_page():
    subjects = Subject.query.order_by(Subject.subject_name).all()
    return render_template('admin_dash_page.html', subjects=subjects)

# ---------- Subjects ----------

def validate_subject(values, subject=None):
    if not values['subject_name'] or not values['subject_description']:
        return 'Subject name and description are required.'
    existing = Subject.query.filter(func.lower(Subject.subject_name) == values['subject_name'].lower()).first()
    if existing and existing is not subject:
        return 'A subject with this name already exists.'
    return None


def subject_form_values(subject=None):
    if request.method == 'POST':
        return {
            'subject_name': request.form.get('subject_name', '').strip(),
            'subject_description': request.form.get('subject_description', '').strip(),
        }
    return {
        'subject_name': subject.subject_name if subject else '',
        'subject_description': subject.subject_description if subject else '',
    }


@app.route('/admin/subject/new', methods=['GET', 'POST'])
@admin_required
def admin_add_subject():
    values = subject_form_values()
    if request.method == 'POST':
        error = validate_subject(values)
        if error:
            flash(error, 'danger')
        else:
            db.session.add(Subject(**values))
            db.session.commit()
            flash('Subject added successfully.', 'success')
            return redirect(url_for('admin_dash_page'))
    return render_template('admin_subject_form.html', values=values, subject=None)


@app.route('/admin/subject/<int:subject_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_subject(subject_id):
    subject = db.get_or_404(Subject, subject_id)
    values = subject_form_values(subject)
    if request.method == 'POST':
        error = validate_subject(values, subject)
        if error:
            flash(error, 'danger')
        else:
            subject.subject_name = values['subject_name']
            subject.subject_description = values['subject_description']
            db.session.commit()
            flash('Subject updated successfully.', 'success')
            return redirect(url_for('admin_dash_page'))
    return render_template('admin_subject_form.html', values=values, subject=subject)


@app.route('/admin/subject/<int:subject_id>/delete', methods=['POST'])
@admin_required
def admin_delete_subject(subject_id):
    subject = db.get_or_404(Subject, subject_id)
    name = subject.subject_name
    db.session.delete(subject)
    db.session.commit()
    flash('Subject "{}" deleted.'.format(name), 'success')
    return redirect(url_for('admin_dash_page'))

# ---------- Chapters ----------

def validate_chapter(values, subject, chapter=None):
    if not values['chapter_name'] or not values['chapter_description']:
        return 'Chapter name and description are required.'
    existing = Chapter.query.filter(
        Chapter.subject_id == subject.id,
        func.lower(Chapter.chapter_name) == values['chapter_name'].lower(),
    ).first()
    if existing and existing is not chapter:
        return 'This subject already has a chapter with this name.'
    return None


def chapter_form_values(chapter=None):
    if request.method == 'POST':
        return {
            'chapter_name': request.form.get('chapter_name', '').strip(),
            'chapter_description': request.form.get('chapter_description', '').strip(),
        }
    return {
        'chapter_name': chapter.chapter_name if chapter else '',
        'chapter_description': chapter.chapter_description if chapter else '',
    }


@app.route('/admin/subject/<int:subject_id>/chapter/new', methods=['GET', 'POST'])
@admin_required
def admin_add_chapter(subject_id):
    subject = db.get_or_404(Subject, subject_id)
    values = chapter_form_values()
    if request.method == 'POST':
        error = validate_chapter(values, subject)
        if error:
            flash(error, 'danger')
        else:
            db.session.add(Chapter(subject_id=subject.id, **values))
            db.session.commit()
            flash('Chapter added successfully.', 'success')
            return redirect(url_for('admin_dash_page'))
    return render_template('admin_chapter_form.html', values=values, subject=subject, chapter=None)


@app.route('/admin/chapter/<int:chapter_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_chapter(chapter_id):
    chapter = db.get_or_404(Chapter, chapter_id)
    values = chapter_form_values(chapter)
    if request.method == 'POST':
        error = validate_chapter(values, chapter.subject, chapter)
        if error:
            flash(error, 'danger')
        else:
            chapter.chapter_name = values['chapter_name']
            chapter.chapter_description = values['chapter_description']
            db.session.commit()
            flash('Chapter updated successfully.', 'success')
            return redirect(url_for('admin_dash_page'))
    return render_template('admin_chapter_form.html', values=values, subject=chapter.subject, chapter=chapter)


@app.route('/admin/chapter/<int:chapter_id>/delete', methods=['POST'])
@admin_required
def admin_delete_chapter(chapter_id):
    chapter = db.get_or_404(Chapter, chapter_id)
    name = chapter.chapter_name
    db.session.delete(chapter)
    db.session.commit()
    flash('Chapter "{}" deleted.'.format(name), 'success')
    return redirect(url_for('admin_dash_page'))

# ---------- Quizzes ----------

@app.route('/admin/quizzes', methods=['GET'])
@admin_required
def admin_quizzes():
    chapter_id = request.args.get('chapter_id', type=int)
    query = Quiz.query
    if chapter_id:
        query = query.filter_by(chapter_id=chapter_id)
    quizzes = query.order_by(Quiz.date_of_quiz.desc(), Quiz.id.desc()).all()
    subjects = Subject.query.order_by(Subject.subject_name).all()
    return render_template('admin_quiz_page.html', quizzes=quizzes, subjects=subjects,
                           selected_chapter_id=chapter_id)


def quiz_form_values(quiz=None):
    if request.method == 'POST':
        return {
            'quiz_name': request.form.get('quiz_name', '').strip(),
            'chapter_id': request.form.get('chapter_id', type=int),
            'date_of_quiz': request.form.get('date_of_quiz', ''),
            'time_duration': request.form.get('time_duration', '').strip(),
            'remarks': request.form.get('remarks', '').strip(),
        }
    if quiz:
        return {
            'quiz_name': quiz.quiz_name,
            'chapter_id': quiz.chapter_id,
            'date_of_quiz': quiz.date_of_quiz.isoformat(),
            'time_duration': quiz.duration_hhmm,
            'remarks': quiz.remarks or '',
        }
    return {
        'quiz_name': '',
        'chapter_id': request.args.get('chapter_id', type=int),
        'date_of_quiz': date.today().isoformat(),
        'time_duration': '00:10',
        'remarks': '',
    }


def parse_quiz_form(values):
    """Returns (data, error) where data holds the validated column values."""
    if not values['quiz_name']:
        return None, 'Quiz name is required.'
    if not values['chapter_id'] or db.session.get(Chapter, values['chapter_id']) is None:
        return None, 'Please choose a valid chapter.'
    try:
        date_of_quiz = datetime.strptime(values['date_of_quiz'], '%Y-%m-%d').date()
    except ValueError:
        return None, 'Please enter a valid quiz date.'
    time_duration = parse_duration(values['time_duration'])
    if time_duration is None:
        return None, 'Duration must be in HH:MM format and more than zero.'
    return {
        'quiz_name': values['quiz_name'],
        'chapter_id': values['chapter_id'],
        'date_of_quiz': date_of_quiz,
        'time_duration': time_duration,
        'remarks': values['remarks'] or None,
    }, None


@app.route('/admin/quiz/new', methods=['GET', 'POST'])
@admin_required
def admin_add_quiz():
    subjects = Subject.query.order_by(Subject.subject_name).all()
    if not any(subject.chapters for subject in subjects):
        flash('Create a subject and a chapter before adding a quiz.', 'warning')
        return redirect(url_for('admin_dash_page'))
    values = quiz_form_values()
    if request.method == 'POST':
        data, error = parse_quiz_form(values)
        if error:
            flash(error, 'danger')
        else:
            quiz = Quiz(**data)
            db.session.add(quiz)
            db.session.commit()
            flash('Quiz created. Now add some questions to it.', 'success')
            return quiz_redirect(quiz)
    return render_template('admin_quiz_form.html', values=values, subjects=subjects, quiz=None)


@app.route('/admin/quiz/<int:quiz_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_quiz(quiz_id):
    quiz = db.get_or_404(Quiz, quiz_id)
    subjects = Subject.query.order_by(Subject.subject_name).all()
    values = quiz_form_values(quiz)
    if request.method == 'POST':
        data, error = parse_quiz_form(values)
        if error:
            flash(error, 'danger')
        else:
            for key, value in data.items():
                setattr(quiz, key, value)
            db.session.commit()
            flash('Quiz updated successfully.', 'success')
            return quiz_redirect(quiz)
    return render_template('admin_quiz_form.html', values=values, subjects=subjects, quiz=quiz)


@app.route('/admin/quiz/<int:quiz_id>/delete', methods=['POST'])
@admin_required
def admin_delete_quiz(quiz_id):
    quiz = db.get_or_404(Quiz, quiz_id)
    name = quiz.quiz_name
    db.session.delete(quiz)
    db.session.commit()
    flash('Quiz "{}" deleted.'.format(name), 'success')
    return redirect(url_for('admin_quizzes'))

# ---------- Questions ----------

def question_form_values(question=None):
    if request.method == 'POST':
        values = {'question_statement': request.form.get('question_statement', '').strip()}
        for number in range(1, 5):
            values['option{}'.format(number)] = request.form.get('option{}'.format(number), '').strip()
        values['correct_option'] = request.form.get('correct_option', type=int)
        return values
    values = {'question_statement': question.question_statement if question else ''}
    for number in range(1, 5):
        values['option{}'.format(number)] = getattr(question, 'option{}'.format(number)) if question else ''
    values['correct_option'] = question.correct_option if question else None
    return values


def validate_question(values):
    options = [values['option{}'.format(number)] for number in range(1, 5)]
    if not values['question_statement'] or not all(options):
        return 'The question statement and all four options are required.'
    if len({option.lower() for option in options}) < 4:
        return 'All four options must be different.'
    if values['correct_option'] not in (1, 2, 3, 4):
        return 'Please choose the correct option.'
    return None


@app.route('/admin/quiz/<int:quiz_id>/question/new', methods=['GET', 'POST'])
@admin_required
def admin_add_question(quiz_id):
    quiz = db.get_or_404(Quiz, quiz_id)
    values = question_form_values()
    if request.method == 'POST':
        error = validate_question(values)
        if error:
            flash(error, 'danger')
        else:
            db.session.add(Question(quiz_id=quiz.id, **values))
            db.session.commit()
            flash('Question added successfully.', 'success')
            if 'add_another' in request.form:
                return redirect(url_for('admin_add_question', quiz_id=quiz.id))
            return quiz_redirect(quiz)
    return render_template('admin_question_form.html', values=values, quiz=quiz, question=None)


@app.route('/admin/question/<int:question_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_question(question_id):
    question = db.get_or_404(Question, question_id)
    values = question_form_values(question)
    if request.method == 'POST':
        error = validate_question(values)
        if error:
            flash(error, 'danger')
        else:
            for key, value in values.items():
                setattr(question, key, value)
            db.session.commit()
            flash('Question updated successfully.', 'success')
            return quiz_redirect(question.quiz)
    return render_template('admin_question_form.html', values=values, quiz=question.quiz, question=question)


@app.route('/admin/question/<int:question_id>/delete', methods=['POST'])
@admin_required
def admin_delete_question(question_id):
    question = db.get_or_404(Question, question_id)
    quiz = question.quiz
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted.', 'success')
    return quiz_redirect(quiz)

# ---------- Users ----------

@app.route('/admin/users', methods=['GET'])
@admin_required
def admin_users():
    rows = (db.session.query(User, func.count(Scores.id), func.avg(SCORE_PERCENT))
            .outerjoin(Scores, Scores.user_id == User.id)
            .group_by(User.id)
            .order_by(User.username)
            .all())
    return render_template('admin_users.html', rows=rows)


@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    user = db.get_or_404(User, user_id)
    name = user.username
    db.session.delete(user)
    db.session.commit()
    flash('User "{}" deleted.'.format(name), 'success')
    return redirect(url_for('admin_users'))

# ---------- Search & Summary ----------

@app.route('/admin/search', methods=['GET'])
@admin_required
def admin_search():
    query = request.args.get('q', '').strip()
    results = {}
    if query:
        def matches(*columns):
            return or_(*(column.icontains(query, autoescape=True) for column in columns))

        results = {
            'users': User.query.filter(matches(User.username, User.full_name, User.qualification))
                               .order_by(User.username).all(),
            'subjects': Subject.query.filter(matches(Subject.subject_name, Subject.subject_description))
                                     .order_by(Subject.subject_name).all(),
            'chapters': Chapter.query.filter(matches(Chapter.chapter_name, Chapter.chapter_description))
                                     .order_by(Chapter.chapter_name).all(),
            'quizzes': Quiz.query.filter(matches(Quiz.quiz_name, Quiz.remarks))
                                 .order_by(Quiz.quiz_name).all(),
            'questions': Question.query.filter(matches(Question.question_statement))
                                       .order_by(Question.id).all(),
        }
    return render_template('admin_search.html', query=query, results=results)


@app.route('/admin/summary', methods=['GET'])
@admin_required
def admin_summary():
    rows = (db.session.query(Subject.subject_name, func.count(Scores.id), func.max(SCORE_PERCENT))
            .outerjoin(Chapter, Chapter.subject_id == Subject.id)
            .outerjoin(Quiz, Quiz.chapter_id == Chapter.id)
            .outerjoin(Scores, Scores.quiz_id == Quiz.id)
            .group_by(Subject.id)
            .order_by(Subject.subject_name)
            .all())
    chart = {
        'labels': [name for name, _, _ in rows],
        'attempts': [attempts for _, attempts, _ in rows],
        'top_scores': [round(top or 0) for _, _, top in rows],
    }
    counts = {
        'Users': User.query.count(),
        'Subjects': Subject.query.count(),
        'Chapters': Chapter.query.count(),
        'Quizzes': Quiz.query.count(),
        'Questions': Question.query.count(),
        'Attempts': Scores.query.count(),
    }
    return render_template('admin_summary.html', chart=chart, counts=counts)
