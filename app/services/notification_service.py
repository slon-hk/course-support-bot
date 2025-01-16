from app import db
from app.models import Notification, NotificationType
from datetime import datetime

class NotificationService:
    @staticmethod
    def create_notification(user, title, message, notification_type=NotificationType.INFO):
        """Создает новое уведомление для пользователя"""
        notification = Notification(
            user_id=user.id,
            title=title,
            message=message,
            type=notification_type.value
        )
        db.session.add(notification)
        db.session.commit()
        return notification

    @staticmethod
    def get_user_notifications(user, include_read=False, limit=10):
        """Получает уведомления пользователя"""
        query = Notification.query.filter_by(
            user_id=user.id,
            is_deleted=False
        )
        
        if not include_read:
            query = query.filter_by(is_read=False)
        
        return query.order_by(Notification.created_at.desc()).limit(limit).all()

    @staticmethod
    def mark_as_read(notification_id, user_id):
        """Отмечает уведомление как прочитанное"""
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=user_id
        ).first()
        
        if notification:
            notification.mark_as_read()
            return True
        return False

    @staticmethod
    def mark_all_as_read(user_id):
        """Отмечает все уведомления пользователя как прочитанные"""
        notifications = Notification.query.filter_by(
            user_id=user_id,
            is_read=False,
            is_deleted=False
        ).all()
        
        for notification in notifications:
            notification.mark_as_read()
        
        db.session.commit()
