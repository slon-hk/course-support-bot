from flask import Blueprint

api = Blueprint('api', __name__)

# Import routes after creating the blueprint
from app.api.telegram import telegram_api
