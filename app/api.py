from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user
from app.models import Course, User, Notification
from app import db
import logging
import secrets
import os

logger = logging.getLogger(__name__)
api = Blueprint('api', __name__)

@api.route('/api/telegram/register', methods=['POST'])
def telegram_register():
    """Register user through Telegram"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        telegram_id = data.get('telegram_id')
        username = data.get('username')
        email = data.get('email')

        if not all([telegram_id, username, email]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({
                'success': False,
                'error': 'User with this email already exists'
            }), 409

        # Create new user
        user = User(
            username=username,
            email=email,
            telegram_id=telegram_id
        )
        # Generate random password for user
        password = secrets.token_urlsafe(12)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        logger.info(f"New user registered via Telegram: {username}")

        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        })

    except Exception as e:
        logger.error(f"Error in telegram registration: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/telegram/auth', methods=['POST'])
def telegram_auth():
    """Authenticate user through Telegram"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        telegram_id = data.get('telegram_id')
        if not telegram_id:
            return jsonify({
                'success': False,
                'error': 'Telegram ID is required'
            }), 400

        user = User.query.filter_by(telegram_id=telegram_id).first()
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        login_user(user)
        user.update_last_login()
        db.session.commit()

        logger.info(f"User {user.username} authenticated via Telegram")

        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin
            }
        })

    except Exception as e:
        logger.error(f"Error in telegram authentication: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/telegram/check_user', methods=['POST'])
def check_telegram_user():
    """Check if user exists by Telegram ID"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        telegram_id = data.get('telegram_id')
        if not telegram_id:
            return jsonify({
                'success': False,
                'error': 'Telegram ID is required'
            }), 400

        user = User.query.filter_by(telegram_id=telegram_id).first()

        return jsonify({
            'success': True,
            'exists': bool(user),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            } if user else None
        })

    except Exception as e:
        logger.error(f"Error checking telegram user: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/user/profile', methods=['GET'])
@login_required
def get_user_profile():
    """Get current user profile information"""
    try:
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'error': 'User not authenticated'
            }), 401

        user_data = {
            'success': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'is_admin': current_user.is_admin,
                'created_at': current_user.created_at.isoformat(),
                'last_login': current_user.last_login.isoformat() if current_user.last_login else None,
                'unread_notifications': current_user.get_unread_notifications_count()
            }
        }
        return jsonify(user_data)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/courses', methods=['GET'])
@login_required
def get_courses():
    """Get all available courses for current user"""
    try:
        if current_user.is_admin:
            courses = Course.query.all()
        else:
            courses = current_user.available_courses.all()

        return jsonify({
            'success': True,
            'courses': [
                {
                    'id': course.id,
                    'title': course.title,
                    'description': course.description,
                    'created_at': course.created_at.isoformat(),
                    'author': {
                        'id': course.author.id,
                        'username': course.author.username
                    },
                    'materials_count': len(course.materials)
                } for course in courses
            ]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/courses/<int:course_id>', methods=['GET'])
@login_required
def get_course(course_id):
    """Get specific course details with materials"""
    try:
        course = Course.query.get_or_404(course_id)

        # Проверяем права доступа
        if not current_user.is_admin and not current_user.has_access_to_course(course):
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403

        return jsonify({
            'success': True,
            'course': {
                'id': course.id,
                'title': course.title,
                'description': course.description,
                'created_at': course.created_at.isoformat(),
                'author': {
                    'id': course.author.id,
                    'username': course.author.username
                },
                'materials': [
                    {
                        'id': material.id,
                        'title': material.title,
                        'content': material.content,
                        'created_at': material.created_at.isoformat(),
                        'files': [
                            {
                                'id': file.id,
                                'filename': file.filename,
                                'file_type': file.file_type,
                                'uploaded_at': file.uploaded_at.isoformat()
                            } for file in material.files
                        ]
                    } for material in course.materials
                ]
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/api/notifications', methods=['GET'])
@login_required
def get_notifications():
    """Get user notifications"""
    try:
        notifications = Notification.query.filter_by(
            user_id=current_user.id,
            is_deleted=False
        ).order_by(Notification.created_at.desc()).all()

        return jsonify({
            'success': True,
            'notifications': [notification.to_dict() for notification in notifications]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.errorhandler(404)
def not_found_error(error):
    return jsonify({
        'success': False,
        'error': 'Resource not found'
    }), 404

@api.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500