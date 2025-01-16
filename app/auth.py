from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app import db
import logging
from datetime import datetime
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)
auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        # Валидация данных
        errors = []
        if not username or len(username) < 3:
            errors.append('Имя пользователя должно содержать минимум 3 символа')

        if not password or len(password) < 6:
            errors.append('Пароль должен содержать минимум 6 символов')

        if password != password_confirm:
            errors.append('Пароли не совпадают')

        try:
            valid = validate_email(email)
            email = valid.email
        except EmailNotValidError:
            errors.append('Указан некорректный email адрес')

        # Проверка существующих пользователей
        if User.query.filter_by(username=username).first():
            errors.append('Пользователь с таким именем уже существует')

        if User.query.filter_by(email=email).first():
            errors.append('Пользователь с таким email уже существует')

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html')

        try:
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            logger.info(f"Зарегистрирован новый пользователь: {username}")
            flash('Регистрация успешна! Теперь вы можете войти в систему', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            logger.error(f"Ошибка при регистрации пользователя: {str(e)}")
            db.session.rollback()
            flash('Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.', 'error')

    return render_template('auth/register.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    logger.debug("Entering login route")

    if current_user.is_authenticated:
        logger.debug("User already authenticated, redirecting to index")
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        logger.debug(f"Login attempt for username: {username}")

        if not username or not password:
            flash('Пожалуйста, заполните все поля', 'error')
            return render_template('auth/login.html')

        try:
            user = User.query.filter_by(username=username).first()
            logger.debug(f"Found user: {user is not None}")

            if user and user.check_password(password):
                logger.debug(f"Password check passed for user: {username}")

                # Вход пользователя
                login_user(user, remember=remember)

                # Обновляем время последнего входа
                user.last_login = datetime.utcnow()
                db.session.commit()

                logger.info(f"Успешный вход пользователя: {username}")
                flash('Вы успешно вошли в систему!', 'success')

                # Проверяем, есть ли сохраненный URL для перенаправления
                next_page = request.args.get('next')
                if not next_page or not next_page.startswith('/'):
                    next_page = url_for('main.index')

                logger.debug(f"Redirecting authenticated user to: {next_page}")
                return redirect(next_page)

            flash('Неверное имя пользователя или пароль', 'error')
            logger.warning(f"Неудачная попытка входа для пользователя: {username}")

        except Exception as e:
            logger.error(f"Ошибка при входе в систему: {str(e)}")
            flash('Произошла ошибка при входе в систему', 'error')
            db.session.rollback()

    return render_template('auth/login.html')

@auth.route('/logout')
@login_required
def logout():
    try:
        username = current_user.username
        logout_user()
        logger.info(f"Пользователь {username} вышел из системы")
        flash('Вы успешно вышли из системы', 'info')
    except Exception as e:
        logger.error(f"Ошибка при выходе из системы: {str(e)}")
        flash('Произошла ошибка при выходе из системы', 'error')

    return redirect(url_for('auth.login'))