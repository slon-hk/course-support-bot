Create a support chatbot system with an admin panel using the following specifications:

## Project Structure
```
/app
  /static           # Static files for frontend
  /templates        # Jinja2 templates
  /bot             # Telegram bot module
  /models          # Database models
  /services        # Business logic
  /utils           # Utility functions
  config.py        # Configuration
  routes.py        # Flask routes
  __init__.py      # Flask app initialization
requirements.txt    # Project dependencies
run.py             # Application entry point
```

## Technology Stack
1. Backend:
   - Python Flask for the main application
   - python-telegram-bot for Telegram integration
   - SQLAlchemy for database ORM
   - PostgreSQL for data storage
   - FAISS for vector search (in-memory mode)
2. Frontend:
   - Jinja2 templates
   - Bootstrap 5 for styling
   - JavaScript for interactivity

## Setup Instructions

### 1. Initialize the Project
```bash
# Create new Python repl with "Python" template
# In the shell:
pip install flask flask-sqlalchemy flask-login python-telegram-bot psycopg2-binary faiss-cpu python-dotenv Werkzeug

# Create requirements.txt
pip freeze > requirements.txt
```

### 2. Environment Setup
Create `.env` file:
```env
FLASK_APP=run.py
FLASK_ENV=development
DATABASE_URL=postgresql://username:password@localhost/dbname
TELEGRAM_BOT_TOKEN=your_bot_token
SECRET_KEY=your_secret_key
GIGACHAT_API_KEY=your_gigachat_key
```

### 3. Create Flask Application

Create app/__init__.py:
```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    from app.routes import main, auth
    app.register_blueprint(main)
    app.register_blueprint(auth)

    return app
```

Create config.py:
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
```

Create app/models.py:
```python
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    materials = db.relationship('Material', backref='course', lazy=True)

class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text)
    vector = db.Column(db.Text)  # Store vector embeddings as serialized text
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

Create app/routes.py:
```python
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, login_user, logout_user
from app.models import User, Course, Material
from app import db

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)

@main.route('/')
@login_required
def index():
    courses = Course.query.all()
    return render_template('index.html', courses=courses)

@main.route('/course/<int:course_id>')
@login_required
def course(course_id):
    course = Course.query.get_or_404(course_id)
    return render_template('course.html', course=course)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user)
            return redirect(url_for('main.index'))
        flash('Invalid username or password')
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
```

### 4. Create Telegram Bot Module

Create app/bot/bot.py:
```python
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from app.models import Course, Material
from app import db

class CourseBot:
    def __init__(self, token):
        self.application = ApplicationBuilder().token(token).build()
        self.setup_handlers()

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("courses", self.list_courses))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Welcome! I'm your course support bot. Use /help to see available commands."
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
        Available commands:
        /start - Start the bot
        /help - Show this help message
        /courses - Show available courses
        """
        await update.message.reply_text(help_text)

    async def list_courses(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        courses = Course.query.all()
        course_list = "\n".join([f"- {course.title}" for course in courses])
        await update.message.reply_text(f"Available courses:\n{course_list}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Here will be the logic for handling user questions
        await update.message.reply_text("I received your message. Feature in development.")

    def run(self):
        self.application.run_polling()
```

### 5. Create Templates

Create app/templates/base.html:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Course Admin Panel</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('main.index') }}">Admin Panel</a>
            {% if current_user.is_authenticated %}
            <a class="nav-link text-white" href="{{ url_for('auth.logout') }}">Logout</a>
            {% endif %}
        </div>
    </nav>
    <div class="container mt-4">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert alert-info">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

Create app/templates/login.html:
```html
{% extends "base.html" %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h3>Login</h3>
            </div>
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3">
                        <label for="username" class="form-label">Username</label>
                        <input type="text" class="form-control" id="username" name="username" required>
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">Password</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    <button type="submit" class="btn btn-primary">Login</button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### 6. Create Run Script

Create run.py:
```python
from app import create_app, db
from app.bot.bot import CourseBot
import os
from dotenv import load_dotenv
import threading

load_dotenv()

app = create_app()

def run_bot():
    bot = CourseBot(os.getenv('TELEGRAM_BOT_TOKEN'))
    bot.run()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Start bot in a separate thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    # Run Flask application
    app.run(host='0.0.0.0', port=8080, debug=True)
```

## Important Notes for Development:

1. This setup provides a basic monolithic structure
2. The admin panel uses Bootstrap for a clean, responsive interface
3. Authentication is handled by Flask-Login
4. The Telegram bot runs in a separate thread
5. Add proper error handling and logging
6. Implement vector search using FAISS
7. Add file upload and processing functionality

Would you like me to provide more detailed implementation for any specific part?
