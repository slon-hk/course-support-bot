import click
from flask.cli import with_appcontext
from app.models import User
from app import db
import logging

logger = logging.getLogger(__name__)

@click.command('create-admin')
@click.argument('username')
@click.argument('email')
@click.argument('password')
@with_appcontext
def create_admin(username, email, password):
    """Создать администратора"""
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            logger.error(f"Пользователь {username} уже существует")
            return

        admin = User(
            username=username,
            email=email,
            is_admin=True
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        logger.info(f"Администратор {username} успешно создан")
    except Exception as e:
        logger.error(f"Ошибка при создании администратора: {str(e)}")
        db.session.rollback()
