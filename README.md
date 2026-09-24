# QuizMaster

A multi-user exam preparation app built with Flask. The **admin** (quiz master) organises
subjects, chapters, quizzes and multiple choice questions. **Users** register, attempt
timed quizzes and track their scores.

## Features

**Admin**
- Pre-created account (no registration). Default login: `Admin` / `Admin`
- Create, edit and delete subjects, chapters, quizzes and questions
- Quizzes have a date (users can attempt them from that date), a duration (`HH:MM`) and remarks
- View and delete registered users, with their number of attempts and average score
- Search across users, subjects, chapters, quizzes and questions
- Summary page with counts and charts (subject wise top scores and attempts)

**User**
- Register and login
- Dashboard of available and upcoming quizzes, with the best score for each
- Attempt a quiz with a countdown timer; it is submitted automatically when time runs out
  (the time limit is also enforced on the server)
- Result page with a review of every answer
- Past scores, and a summary page with charts (subject wise, month wise and score trend)
- Search quizzes by subject, chapter or quiz name

## Tech stack

Flask, Flask-SQLAlchemy, SQLite, Jinja2, Bootstrap 5 and Chart.js (loaded from a CDN).
Passwords are stored as salted hashes and logins use Flask's signed session.

## Running the app

```bash
python -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:5000. The database (`instance/quizmaster.db`) and the admin account
are created automatically on the first run.

Optional environment variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `SECRET_KEY` | Signs the session cookie. Set this for any real deployment. | a development key |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Credentials of the admin created with the database | `Admin` / `Admin` |
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///quizmaster.db` |

## Running the tests

```bash
pip install pytest
python -m pytest
```

## Project structure

```
run.py                  Starts the development server
app/__init__.py         App configuration, database setup and default admin
app/models.py           User, Admin, Subject, Chapter, Quiz, Question, Scores
app/routes.py           Home, login, register, logout and access control
app/admin_routes.py     Admin dashboard, CRUD pages, users, search and summary
app/user_routes.py      User dashboard, quiz attempt, scores, search and summary
app/templates/          Jinja2 templates (base.html holds the shared layout)
app/static/             CSS and images
tests/                  Pytest test suite
```

## Database schema

- **User**: username, password (hash), full name, qualification, date of birth
- **Admin**: username, password (hash)
- **Subject**: name, description
- **Chapter**: subject, name, description (the number of questions is calculated from its quizzes)
- **Quiz**: chapter, name, date of quiz, duration in minutes, remarks
- **Question**: quiz, statement, four options, correct option (1 to 4)
- **Scores**: user, quiz, total scored, total questions, time of attempt

Deleting a subject, chapter or quiz also deletes everything under it, including scores.
