import numpy as np
import logging
from app.models import Material
from app.ai import get_embedding, add_file_to_vector_db, answer_question
import os

logger = logging.getLogger(__name__)

class VectorSearch:
    def __init__(self):
        self.vector_db_path = os.path.join(os.getcwd(), "app", "data")
        logger.info("Vector search initialized with path: %s", self.vector_db_path)

    def create_embedding(self, text):
        """
        Создание векторного представления текста используя функцию из ai.py
        """
        try:
            return get_embedding(text)
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            return None

    def add_to_index(self, file_path):
        """Добавление файла в индекс"""
        try:
            success = add_file_to_vector_db(file_path, self.vector_db_path)
            if success:
                logger.info(f"File added to vector db: {file_path}")
            else:
                logger.error(f"Failed to add file to vector db: {file_path}")
            return success
        except Exception as e:
            logger.error(f"Error adding file to index: {e}")
            return False

    def search(self, query, k=5):
        """Поиск похожих материалов"""
        try:
            response = answer_question(query, self.vector_db_path)
            return [{'content': response}] if response else []
        except Exception as e:
            logger.error(f"Error during vector search: {e}")
            return []

    def rebuild_index(self):
        """Перестроение индекса из базы данных"""
        try:
            materials = Material.query.all()
            success_count = 0

            for material in materials:
                if material.file_path and os.path.exists(material.file_path):
                    if self.add_to_index(material.file_path):
                        success_count += 1

            logger.info(f"Index rebuilt successfully. Processed {success_count} out of {len(materials)} materials")
            return True
        except Exception as e:
            logger.error(f"Error rebuilding index: {e}")
            return False