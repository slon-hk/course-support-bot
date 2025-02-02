from flask import Blueprint, render_template, flash, redirect, url_for, request, session
from app.models import User, Course, Material, MaterialFile
from app import db
import logging
from functools import wraps

logger = logging.getLogger(__name__)
admin = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('У вас нет прав для доступа к этой странице', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/')
@admin_required
def index():
    """Главная страница административной панели"""
    try:
        stats = {
            'users_count': User.query.count(),
            'courses_count': Course.query.count(),
            'materials_count': Material.query.count(),
            'files_count': MaterialFile.query.count()
        }
        return render_template('admin/index.html', stats=stats)
    except Exception as e:
        logger.error(f"Ошибка при загрузке статистики: {str(e)}")
        flash('Ошибка при загрузке статистики', 'error')
        return redirect(url_for('main.index'))

@admin.route('/users')
@admin_required
def users():
    """Список всех пользователей"""
    try:
        users = User.query.order_by(User.id.desc()).all()
        return render_template('admin/users.html', users=users)
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка пользователей: {str(e)}")
        flash('Ошибка при загрузке списка пользователей', 'error')
        return redirect(url_for('admin.index'))

@admin.route('/users/add', methods=['POST'])
@admin_required
def add_user():
    """Добавление нового пользователя"""
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = request.form.get('is_admin') == 'on'

        if not username or not email or not password:
            flash('Все поля обязательны для заполнения', 'error')
            return redirect(url_for('admin.users'))

        user = User(username=username, email=email, is_admin=is_admin)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Пользователь успешно добавлен', 'success')
        return redirect(url_for('admin.users'))
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя: {str(e)}")
        db.session.rollback()
        flash('Ошибка при добавлении пользователя', 'error')
        return redirect(url_for('admin.users'))

@admin.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Удаление пользователя"""
    try:
        user = User.query.get_or_404(user_id)
        if user.is_admin and User.query.filter_by(is_admin=True).count() <= 1:
            flash('Невозможно удалить последнего администратора', 'error')
            return redirect(url_for('admin.users'))

        db.session.delete(user)
        db.session.commit()
        flash('Пользователь успешно удален', 'success')
        return redirect(url_for('admin.users'))
    except Exception as e:
        logger.error(f"Ошибка при удалении пользователя: {str(e)}")
        db.session.rollback()
        flash('Ошибка при удалении пользователя', 'error')
        return redirect(url_for('admin.users'))

@admin.route('/courses')
@admin_required
def courses():
    """Список всех курсов"""
    try:
        courses = Course.query.order_by(Course.created_at.desc()).all()
        return render_template('admin/courses.html', courses=courses)
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка курсов: {str(e)}")
        flash('Ошибка при загрузке списка курсов', 'error')
        return redirect(url_for('admin.index'))

@admin.route('/materials')
@admin_required
def materials():
    """Список всех материалов"""
    try:
        materials = Material.query.order_by(Material.created_at.desc()).all()
        return render_template('admin/materials.html', materials=materials)
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка материалов: {str(e)}")
        flash('Ошибка при загрузке списка материалов', 'error')
        return redirect(url_for('admin.index'))

@admin.route('/files')
@admin_required
def files():
    """Список всех файлов"""
    try:
        files = MaterialFile.query.all()
        return render_template('admin/files.html', files=files)
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка файлов: {str(e)}")
        flash('Ошибка при загрузке списка файлов', 'error')
        return redirect(url_for('admin.index'))

@admin.route('/course/<int:course_id>/access', methods=['GET', 'POST'])
@admin_required
def manage_course_access(course_id):
    """Управление доступом к курсу"""
    try:
        course = Course.query.get_or_404(course_id)
        if request.method == 'POST':
            user_id = request.form.get('user_id')
            action = request.form.get('action')

            user = User.query.get_or_404(user_id)

            if action == 'grant':
                if not user.has_access_to_course(course):
                    course.allowed_users.append(user)
                    db.session.commit()
                    flash(f'Доступ предоставлен пользователю {user.username}', 'success')
            elif action == 'revoke':
                if user.has_access_to_course(course):
                    course.allowed_users.remove(user)
                    db.session.commit()
                    flash(f'Доступ отозван у пользователя {user.username}', 'success')

            return redirect(url_for('admin.manage_course_access', course_id=course_id))

        users = User.query.all()
        return render_template('admin/course/manage_access.html', course=course, users=users)
    except Exception as e:
        logger.error(f"Ошибка при управлении доступом к курсу: {str(e)}")
        flash('Произошла ошибка при управлении доступом', 'error')
        return redirect(url_for('admin.courses'))