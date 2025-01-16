from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file, session
from app.models import Course, Material, MaterialFile, User, Notification
from app import db
from app.services.vector_search import VectorSearch
import logging
import os
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

# Устанавливаем админ сессию для всех запросов
@main.before_request
def set_admin_session():
    session['is_admin'] = True

# Путь к векторной базе данных
VECTOR_DB_PATH = os.path.join(os.getcwd(), "app", "data")

@main.route('/')
def index():
    """
    Главная страница со списком курсов
    """
    try:
        courses = Course.query.all()
        return render_template('index.html', courses=courses)
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка курсов: {str(e)}")
        flash('Произошла ошибка при загрузке данных', 'error')
        return render_template('index.html', courses=[])

@main.route('/chat')
def chat():
    """Страница чата с ИИ"""
    try:
        courses = Course.query.all()
        return render_template('chat/index.html', courses=courses)
    except Exception as e:
        logger.error(f"Ошибка при загрузке страницы чата: {str(e)}")
        flash('Произошла ошибка при загрузке чата', 'error')
        return redirect(url_for('main.index'))

@main.route('/chat/ask', methods=['POST'])
def chat_ask():
    """Обработка вопроса в чате"""
    try:
        course_id = request.form.get('course_id')
        question = request.form.get('question')

        if not course_id or not question:
            logger.warning("Отсутствует course_id или вопрос")
            return jsonify({'success': False, 'error': 'Необходимо выбрать курс и задать вопрос'})

        # Инициализация поиска
        vector_search = VectorSearch()

        # Поиск ответа
        results = vector_search.search(question)

        if not results:
            return jsonify({
                'success': True,
                'answer': 'К сожалению, не удалось найти информацию по вашему вопросу в материалах курса.'
            })

        # Форматируем ответ из результатов поиска
        answer = results[0].get('content', 'Информация не найдена')

        return jsonify({
            'success': True,
            'answer': answer
        })

    except Exception as e:
        logger.error(f"Ошибка при обработке вопроса: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Произошла ошибка при обработке вашего вопроса'
        })

@main.route('/notifications')
def notifications():
    """Страница уведомлений"""
    try:
        notifications = Notification.query.filter_by(is_deleted=False).order_by(Notification.created_at.desc()).all()
        return render_template('notifications.html', notifications=notifications)
    except Exception as e:
        logger.error(f"Ошибка при загрузке уведомлений: {str(e)}")
        flash('Произошла ошибка при загрузке уведомлений', 'error')
        return redirect(url_for('main.index'))

@main.route('/course/<int:course_id>')
def course(course_id):
    """Просмотр курса"""
    try:
        course = Course.query.get_or_404(course_id)
        return render_template('course/view.html', course=course)
    except Exception as e:
        logger.error(f"Ошибка при загрузке курса: {str(e)}")
        flash('Произошла ошибка при загрузке курса', 'error')
        return redirect(url_for('main.index'))

@main.route('/course/<int:course_id>/edit', methods=['GET', 'POST'])
def edit_course(course_id):
    """Редактирование курса"""
    try:
        course = Course.query.get_or_404(course_id)
        title = request.form.get('title')
        description = request.form.get('description', '')

        if not title:
            flash('Название курса обязательно', 'error')
            return redirect(url_for('main.course', course_id=course_id))

        course.title = title
        course.description = description
        db.session.commit()

        flash('Курс успешно обновлен', 'success')
        return redirect(url_for('main.course', course_id=course_id))

    except Exception as e:
        logger.error(f"Ошибка при редактировании курса: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при редактировании курса', 'error')
        return redirect(url_for('main.course', course_id=course_id))

@main.route('/course/<int:course_id>/delete', methods=['POST'])
def delete_course(course_id):
    """Удаление курса"""
    try:
        course = Course.query.get_or_404(course_id)

        # Удаляем все файлы курса физически
        for material in course.materials:
            for file in material.files:
                if os.path.exists(file.file_path):
                    os.remove(file.file_path)

        db.session.delete(course)
        db.session.commit()

        flash('Курс успешно удален', 'success')
        return redirect(url_for('main.index'))

    except Exception as e:
        logger.error(f"Ошибка при удалении курса: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при удалении курса', 'error')
        return redirect(url_for('main.index'))

@main.route('/add_course', methods=['POST'])
def add_course():
    """Добавление нового курса"""
    try:
        title = request.form.get('title')
        description = request.form.get('description', '')

        if not title:
            flash('Название курса обязательно', 'error')
            return redirect(url_for('main.index'))

        new_course = Course(
            title=title,
            description=description,
            user_id=1  # Временно используем ID админа
        )
        db.session.add(new_course)
        db.session.commit()

        flash('Курс успешно создан', 'success')
        return redirect(url_for('main.index'))

    except Exception as e:
        logger.error(f"Ошибка при создании курса: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при создании курса', 'error')
        return redirect(url_for('main.index'))

@main.route('/course/<int:course_id>/add_material', methods=['POST'])
def add_material(course_id):
    """Добавление материала к курсу"""
    try:
        logger.info(f"Попытка добавить материал к курсу {course_id}")
        course = Course.query.get_or_404(course_id)
        title = request.form.get('title')
        content = request.form.get('content', '')

        if not title:
            logger.warning("Отсутствует название материала")
            flash('Название материала обязательно', 'error')
            return redirect(url_for('main.course', course_id=course_id))

        material = Material(
            course_id=course_id,
            title=title,
            content=content
        )
        logger.info(f"Создан новый материал: {title}")

        db.session.add(material)
        db.session.commit()
        logger.info(f"Материал {title} успешно добавлен к курсу {course_id}")

        flash('Материал успешно добавлен', 'success')
        return redirect(url_for('main.course', course_id=course_id))

    except Exception as e:
        logger.error(f"Ошибка при добавлении материала: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при добавлении материала', 'error')
        return redirect(url_for('main.course', course_id=course_id))

@main.route('/material/<int:material_id>/upload_file', methods=['POST'])
def upload_file(material_id):
    """Загрузка файла к материалу"""
    try:
        material = Material.query.get_or_404(material_id)
        if 'file' not in request.files:
            flash('Файл не выбран', 'error')
            return redirect(url_for('main.course', course_id=material.course_id))

        file = request.files['file']
        if file.filename == '':
            flash('Файл не выбран', 'error')
            return redirect(url_for('main.course', course_id=material.course_id))

        if file:
            filename = secure_filename(file.filename)
            file_type = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

            if file_type not in ['pdf', 'docx']:
                flash('Неподдерживаемый тип файла. Разрешены только PDF и DOCX', 'error')
                return redirect(url_for('main.course', course_id=material.course_id))

            # Создаем директорию для файлов материала
            file_dir = os.path.join(os.getcwd(), 'app', 'uploads', str(material_id))
            os.makedirs(file_dir, exist_ok=True)

            # Сохраняем файл
            file_path = os.path.join(file_dir, filename)
            file.save(file_path)

            try:
                # Создаем запись в БД
                material_file = MaterialFile(
                    material_id=material_id,
                    filename=filename,
                    file_path=file_path,
                    file_type=file_type
                )
                db.session.add(material_file)
                db.session.commit()

                # Создаем экземпляр FileProcessor для индексации
                from app.services.file_processor import FileProcessor
                processor = FileProcessor(vector_db_path=VECTOR_DB_PATH)

                # Индексируем файл
                if processor.process_file(file_path):
                    logger.info(f"Файл {filename} успешно проиндексирован")
                    flash('Файл успешно загружен и проиндексирован', 'success')
                else:
                    logger.warning(f"Ошибка при индексации файла {filename}")
                    flash('Файл загружен, но возникла ошибка при индексации', 'warning')

            except Exception as e:
                logger.error(f"Ошибка при обработке файла: {str(e)}")
                flash('Произошла ошибка при обработке файла', 'error')

            return redirect(url_for('main.course', course_id=material.course_id))

    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {str(e)}")
        if 'material' in locals():
            db.session.rollback()
            return redirect(url_for('main.course', course_id=material.course_id))
        return redirect(url_for('main.index'))

@main.route('/file/<int:file_id>/download')
def download_file(file_id):
    """Скачивание файла"""
    try:
        file = MaterialFile.query.get_or_404(file_id)
        return send_file(file.file_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Ошибка при скачивании файла: {str(e)}")
        flash('Произошла ошибка при скачивании файла', 'error')
        return redirect(url_for('main.course', course_id=file.material.course_id))

@main.route('/file/<int:file_id>/delete', methods=['POST'])
def delete_file(file_id):
    """Удаление файла"""
    try:
        file = MaterialFile.query.get_or_404(file_id)
        course_id = file.material.course_id

        if os.path.exists(file.file_path):
            os.remove(file.file_path)

        db.session.delete(file)
        db.session.commit()

        flash('Файл успешно удален', 'success')
        return redirect(url_for('main.course', course_id=course_id))

    except Exception as e:
        logger.error(f"Ошибка при удалении файла: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при удалении файла', 'error')
        return redirect(url_for('main.course', course_id=file.material.course_id))

@main.route('/users')
def users():
    """Страница управления пользователями"""
    try:
        users = User.query.all()
        return render_template('admin/users.html', users=users)
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка пользователей: {str(e)}")
        flash('Произошла ошибка при загрузке данных', 'error')
        return redirect(url_for('main.index'))

@main.route('/materials')
def materials():
    """Страница управления материалами"""
    try:
        materials = Material.query.all()
        return render_template('admin/materials.html', materials=materials)
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка материалов: {str(e)}")
        flash('Произошла ошибка при загрузке данных', 'error')
        return redirect(url_for('main.index'))

@main.route('/files')
def files():
    """Страница управления файлами"""
    try:
        files = MaterialFile.query.all()
        return render_template('admin/files.html', files=files)
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка файлов: {str(e)}")
        flash('Произошла ошибка при загрузке данных', 'error')
        return redirect(url_for('main.index'))

@main.route('/material/<int:material_id>/edit', methods=['GET', 'POST'])
def edit_material(material_id):
    """Редактирование материала"""
    try:
        material = Material.query.get_or_404(material_id)
        title = request.form.get('title')
        content = request.form.get('content', '')

        if not title:
            flash('Название материала обязательно', 'error')
            return redirect(url_for('main.course', course_id=material.course_id))

        material.title = title
        material.content = content
        db.session.commit()

        flash('Материал успешно обновлен', 'success')
        return redirect(url_for('main.course', course_id=material.course_id))

    except Exception as e:
        logger.error(f"Ошибка при редактировании материала: {str(e)}")
        db.session.rollback()
        flash('Произошла ошибка при редактировании материала', 'error')
        return redirect(url_for('main.course', course_id=material.course_id))