
from datetime import date, datetime

from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class PasswordMixin:
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


# User model
class User(PasswordMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    qualification = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    scores = db.relationship('Scores', backref='user', lazy=True, cascade='all, delete-orphan')

# Admin model
class Admin(PasswordMixin, db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)

#subject model
class Subject(db.Model):
    __tablename__ = 'subject'
    id = db.Column(db.Integer, primary_key=True)
    subject_name = db.Column(db.String(50), unique=True, nullable=False)
    subject_description = db.Column(db.String(200), nullable=False)
    chapters = db.relationship('Chapter', backref='subject', lazy=True,
                               cascade='all, delete-orphan', order_by='Chapter.id')

#chapter model
class Chapter(db.Model):
    __tablename__ = 'chapter'
    # A chapter name only has to be unique within its subject
    __table_args__ = (db.UniqueConstraint('subject_id', 'chapter_name'),)
    id = db.Column(db.Integer, primary_key=True)
    chapter_name = db.Column(db.String(50), nullable=False)
    chapter_description = db.Column(db.String(200), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    quizzes = db.relationship('Quiz', backref='chapter', lazy=True,
                              cascade='all, delete-orphan', order_by='Quiz.date_of_quiz')

    @property
    def no_of_questions(self):
        return sum(len(quiz.questions) for quiz in self.quizzes)

#quiz model
class Quiz(db.Model):
    __tablename__ = 'quiz'
    id = db.Column(db.Integer, primary_key=True)
    quiz_name = db.Column(db.String(100), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    date_of_quiz = db.Column(db.Date, nullable=False, default=date.today)
    time_duration = db.Column(db.Integer, nullable=False)  # in minutes
    remarks = db.Column(db.String(200))
    questions = db.relationship('Question', backref='quiz', lazy=True,
                                cascade='all, delete-orphan', order_by='Question.id')
    scores = db.relationship('Scores', backref='quiz', lazy=True, cascade='all, delete-orphan')

    @property
    def duration_hhmm(self):
        return '{:02d}:{:02d}'.format(*divmod(self.time_duration, 60))

    @property
    def is_open(self):
        return self.date_of_quiz <= date.today()

#question model
class Question(db.Model):
    __tablename__ = 'question'
    id = db.Column(db.Integer, primary_key=True)
    question_statement = db.Column(db.Text, nullable=False)
    option1 = db.Column(db.String(200), nullable=False)
    option2 = db.Column(db.String(200), nullable=False)
    option3 = db.Column(db.String(200), nullable=False)
    option4 = db.Column(db.String(200), nullable=False)
    correct_option = db.Column(db.Integer, nullable=False)  # 1 to 4
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)

    @property
    def options(self):
        return [self.option1, self.option2, self.option3, self.option4]

#Scores model
class Scores(db.Model):
    __tablename__ = 'scores'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    total_scored = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    time_stamp_of_attempt = db.Column(db.DateTime, default=datetime.now)

    @property
    def percentage(self):
        if not self.total_questions:
            return 0
        return round(100 * self.total_scored / self.total_questions)


def create_default_admin(username, password):
    """The admin has no registration page, so it is created along with the database."""
    if Admin.query.first() is None:
        admin = Admin(username=username)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
