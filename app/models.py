from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
from enum import Enum

class NotificationType(Enum):
    INFO = 'info'
    SUCCESS = 'success'
    WARNING = 'warning'
    ERROR = 'error'

# Таблица для связи many-to-many между пользователями и курсами
course_users = db.Table('course_users',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'), primary_key=True),
    db.Column('granted_at', db.DateTime, default=datetime.utcnow),
    db.Column('granted_by', db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
)

class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Relationships
    materials = db.relationship('Material', backref='course', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Course {self.title}>'

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    telegram_id = db.Column(db.String(32), unique=True, nullable=True, index=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    courses_created = db.relationship('Course', backref='author', lazy=True, 
                                    foreign_keys='Course.user_id',
                                    cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, 
                                  cascade='all, delete-orphan')

    # Доступные курсы (для обычных пользователей)
    courses = db.relationship('Course', 
                            secondary=course_users,
                            primaryjoin=(id == course_users.c.user_id),
                            secondaryjoin=(id == course_users.c.course_id),
                            backref=db.backref('users', lazy='dynamic'),
                            lazy='dynamic')

    def set_password(self, password):
        if not password:
            raise ValueError("Password cannot be empty")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not password:
            return False
        return check_password_hash(self.password_hash, password)

    def get_unread_notifications_count(self):
        return Notification.query.filter_by(user_id=self.id, is_read=False).count()

    def has_access_to_course(self, course):
        """Проверяет, имеет ли пользователь доступ к курсу"""
        if self.is_admin or course.user_id == self.id:
            return True
        return self.courses.filter_by(id=course.id).first() is not None

    def grant_course_access(self, course):
        """Предоставляет доступ к курсу"""
        if not self.has_access_to_course(course):
            self.courses.append(course)
            return True
        return False

    def revoke_course_access(self, course):
        """Отзывает доступ к курсу"""
        if self.has_access_to_course(course):
            self.courses.remove(course)
            return True
        return False

    def __repr__(self):
        return f'<User {self.username}>'

class Material(db.Model):
    __tablename__ = 'materials'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    vector = db.Column(db.Text)  # Для хранения векторных эмбеддингов

    # Relationships
    files = db.relationship('MaterialFile', backref='material', lazy=True, cascade='all, delete-orphan')

    def set_vector(self, vector_data):
        self.vector = json.dumps(vector_data)

    def get_vector(self):
        return json.loads(self.vector) if self.vector else None

class MaterialFile(db.Model):
    __tablename__ = 'material_files'

    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id', ondelete='CASCADE'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_indexed = db.Column(db.Boolean, default=False)
    vector = db.Column(db.Text)

    def set_vector(self, vector_data):
        self.vector = json.dumps(vector_data)
        self.is_indexed = True

    def get_vector(self):
        return json.loads(self.vector) if self.vector else None

class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    type = db.Column(db.String(20), nullable=False, default=NotificationType.INFO.value)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
            db.session.commit()

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
            'read_at': self.read_at.isoformat() if self.read_at else None
        }