
import time
from collections import Counter

from flask import flash, g, redirect, render_template, request, session, url_for
from sqlalchemy import or_

from app import app, db
from app.models import Chapter, Quiz, Scores, Subject
from app.routes import user_required

# Extra seconds allowed after the timer ends, to cover the automatic submission
SUBMIT_GRACE_SECONDS = 30


def attemptable_quizzes():
    """Quizzes that have at least one question, newest first."""
    return (Quiz.query.join(Quiz.chapter).join(Chapter.subject)
            .filter(Quiz.questions.any())
            .order_by(Quiz.date_of_quiz.desc(), Quiz.id.desc()))


def user_quiz_stats(user):
    """Maps quiz id -> (number of attempts, best percentage) for the given user."""
    stats = {}
    for score in user.scores:
        attempts, best = stats.get(score.quiz_id, (0, 0))
        stats[score.quiz_id] = (attempts + 1, max(best, score.percentage))
    return stats


@app.route('/user_dashboard_page', methods=['GET'])
@user_required
def user_dashboard_page():
    quizzes = attemptable_quizzes().all()
    return render_template('user_dashboard.html',
                           open_quizzes=[quiz for quiz in quizzes if quiz.is_open],
                           upcoming_quizzes=[quiz for quiz in quizzes if not quiz.is_open],
                           stats=user_quiz_stats(g.user))


@app.route('/quiz/<int:quiz_id>', methods=['GET'])
@user_required
def user_quiz_view(quiz_id):
    quiz = db.get_or_404(Quiz, quiz_id)
    attempts, best = user_quiz_stats(g.user).get(quiz.id, (0, None))
    return render_template('user_quiz_view.html', quiz=quiz, attempts=attempts, best=best)


@app.route('/quiz/<int:quiz_id>/start', methods=['GET'])
@user_required
def user_quiz_start(quiz_id):
    quiz = db.get_or_404(Quiz, quiz_id)
    if not quiz.questions:
        flash('This quiz does not have any questions yet.', 'warning')
        return redirect(url_for('user_dashboard_page'))
    if not quiz.is_open:
        flash('This quiz opens on {}.'.format(quiz.date_of_quiz.strftime('%d %b %Y')), 'warning')
        return redirect(url_for('user_dashboard_page'))

    # Keep the running attempt on a page refresh so the timer does not restart
    now = time.time()
    limit = quiz.time_duration * 60
    attempt = session.get('attempt')
    if not attempt or attempt.get('quiz_id') != quiz.id or now - attempt['started_at'] >= limit:
        attempt = {'quiz_id': quiz.id, 'started_at': now}
        session['attempt'] = attempt
    remaining_seconds = max(1, int(limit - (now - attempt['started_at'])))
    return render_template('user_quiz_attempt.html', quiz=quiz, remaining_seconds=remaining_seconds)


@app.route('/quiz/<int:quiz_id>/submit', methods=['POST'])
@user_required
def user_quiz_submit(quiz_id):
    quiz = db.get_or_404(Quiz, quiz_id)
    attempt = session.get('attempt')
    if not attempt or attempt.get('quiz_id') != quiz.id:
        flash('Please start the quiz from your dashboard before submitting.', 'warning')
        return redirect(url_for('user_dashboard_page'))
    session.pop('attempt')

    if time.time() - attempt['started_at'] > quiz.time_duration * 60 + SUBMIT_GRACE_SECONDS:
        flash('Time limit exceeded. Your submission was not recorded.', 'danger')
        return redirect(url_for('user_dashboard_page'))

    review = []
    for question in quiz.questions:
        answer = request.form.get('question_{}'.format(question.id), type=int)
        review.append({
            'question': question,
            'answer': answer,
            'is_correct': answer == question.correct_option,
        })
    score = Scores(user_id=g.user.id, quiz_id=quiz.id,
                   total_scored=sum(item['is_correct'] for item in review),
                   total_questions=len(review))
    db.session.add(score)
    db.session.commit()
    return render_template('user_quiz_result.html', quiz=quiz, score=score, review=review)


@app.route('/scores', methods=['GET'])
@user_required
def user_scores():
    scores = (Scores.query.filter_by(user_id=g.user.id)
              .order_by(Scores.time_stamp_of_attempt.desc())
              .all())
    return render_template('user_scores.html', scores=scores)


@app.route('/summary', methods=['GET'])
@user_required
def user_summary():
    scores = (Scores.query.filter_by(user_id=g.user.id)
              .order_by(Scores.time_stamp_of_attempt)
              .all())
    subject_attempts = Counter(score.quiz.chapter.subject.subject_name for score in scores)
    month_attempts = Counter(score.time_stamp_of_attempt.strftime('%b %Y') for score in scores)
    percentages = [score.percentage for score in scores]
    stats = {
        'attempts': len(scores),
        'quizzes': len({score.quiz_id for score in scores}),
        'average': round(sum(percentages) / len(percentages)) if percentages else 0,
        'best': max(percentages, default=0),
    }
    chart = {
        'subject_labels': list(subject_attempts.keys()),
        'subject_counts': list(subject_attempts.values()),
        'month_labels': list(month_attempts.keys()),
        'month_counts': list(month_attempts.values()),
        'score_labels': [score.time_stamp_of_attempt.strftime('%d %b') for score in scores],
        'score_values': percentages,
    }
    return render_template('user_summary.html', stats=stats, chart=chart)


@app.route('/search', methods=['GET'])
@user_required
def user_search():
    query = request.args.get('q', '').strip()
    quizzes = []
    if query:
        columns = (Quiz.quiz_name, Quiz.remarks, Chapter.chapter_name, Subject.subject_name)
        quizzes = attemptable_quizzes().filter(
            or_(*(column.icontains(query, autoescape=True) for column in columns))
        ).all()
    return render_template('user_search.html', query=query, quizzes=quizzes,
                           stats=user_quiz_stats(g.user))
