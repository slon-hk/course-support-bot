import os
import logging
import requests
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

class GigaChatAPI:
    """Класс для работы с GigaChat API"""

    def __init__(self):
        # Используем GIGACHAT_CREDENTIALS вместо GIGACHAT_API_KEY
        self.credentials = os.environ.get('GIGACHAT_CREDENTIALS')
        if not self.credentials:
            logger.warning("GIGACHAT_CREDENTIALS не найден в переменных окружения")

        self.token_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"  # URL для получения токена
        self.base_url = "https://gigachat.devices.sberbank.ru/api/v1"  # Базовый URL для API
        self.token = None

    def _get_token(self) -> Optional[str]:
        """Получение токена для доступа к API"""
        try:
            # Генерация уникального RqUID
            rquid = str(uuid.uuid4())

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
                'RqUID': rquid,  # Уникальный идентификатор запроса
                'Authorization': f'Basic {self.credentials}'  # Используем GIGACHAT_CREDENTIALS
            }

            # Тело запроса с scope
            payload = {
                'scope': 'GIGACHAT_API_PERS'
            }

            response = requests.post(
                self.token_url,
                headers=headers,
                data=payload,
                verify=False  # Отключаем проверку SSL-сертификатов (только для тестовых целей)
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('access_token')  # Предполагаем, что токен возвращается в поле 'access_token'
            else:
                logger.error(f"Ошибка получения токена: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Ошибка при получении токена: {str(e)}")
            return None

    def generate_response(self, prompt: str) -> Optional[str]:
        """Генерация ответа с использованием GigaChat API"""
        try:
            if not self.token:
                self.token = self._get_token()
                if not self.token:
                    logger.error("Не удалось получить токен для доступа к API")
                    return None

            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }

            data = {
                'model': 'GigaChat:latest',
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': 0.7,
                'max_tokens': 1500
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                verify=False  # Отключаем проверку SSL-сертификатов (только для тестовых целей)
            )

            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                logger.error(f"Ошибка генерации ответа: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {str(e)}")
            return None