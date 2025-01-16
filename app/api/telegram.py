from flask import Blueprint, jsonify, request
from app.models import User, db
from werkzeug.security import generate_password_hash
import logging

logger = logging.getLogger(__name__)

telegram_api = Blueprint('telegram_api', __name__)

@telegram_api.route('/api/telegram/register', methods=['POST'])
def register():
    """Регистрация пользователя через Telegram"""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        username = data.get('username')
        email = data.get('email')

        if not all([telegram_id, username, email]):
            return jsonify({
                'success': False,
                'error': 'Не все обязательные поля заполнены'
            }), 400

        # Проверяем существование пользователя
        existing_user = User.query.filter(
            (User.telegram_id == str(telegram_id)) | 
            (User.email == email)
        ).first()

        if existing_user:
            if existing_user.telegram_id == str(telegram_id):
                return jsonify({
                    'success': False,
                    'error': 'Пользователь с таким Telegram ID уже существует'
                }), 400
            else:
                return jsonify({
                    'success': False,
                    'error': 'Пользователь с таким email уже существует'
                }), 400

        # Создаем нового пользователя
        user = User(
            username=username,
            email=email,
            telegram_id=str(telegram_id)
        )
        
        # Генерируем временный пароль
        temp_password = f"tg_{telegram_id}"
        user.set_password(temp_password)

        db.session.add(user)
        db.session.commit()

        logger.info(f"Пользователь {username} успешно зарегистрирован через Telegram")

        return jsonify({
            'success': True,
            'message': 'Регистрация успешно завершена'
        })

    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя через Telegram: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Произошла ошибка при регистрации'
        }), 500

@telegram_api.route('/api/telegram/auth', methods=['POST'])
def auth():
    """Аутентификация пользователя через Telegram ID"""
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')

        if not telegram_id:
            return jsonify({
                'success': False,
                'error': 'Telegram ID не указан'
            }), 400

        user = User.query.filter_by(telegram_id=str(telegram_id)).first()
        if not user:
            return jsonify({
                'success': False,
                'error': 'Пользователь не найден'
            }), 404

        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        })

    except Exception as e:
        logger.error(f"Ошибка при аутентификации через Telegram: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Произошла ошибка при аутентификации'
        }), 500
