import os
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
from typing import List, Dict, Any
import json
from app.services.vector_db import VectorDB

logger = logging.getLogger(__name__)

# Инициализируем модель для embeddings
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')

def get_embedding(text: str) -> np.ndarray:
    """Получить векторное представление текста"""
    return model.encode([text])[0]

def add_file_to_vector_db(file_path: str, save_path: str) -> bool:
    """
    Обработать файл и добавить его содержимое в векторную базу данных
    """
    try:
        from file_processing import process_file
        documents = process_file(file_path)

        if not documents:
            logger.error(f"No documents extracted from {file_path}")
            return False

        # Создаем или получаем экземпляр VectorDB
        vector_db = VectorDB(
            os.path.join(save_path, "vector_index.faiss"),
            os.path.join(save_path, "documents.json")
        )

        # Добавляем документы в базу
        for doc in documents:
            if isinstance(doc, str):
                text = doc
            else:
                text = doc.get('text', '')

            if text:
                vector_db.add_document(text, file_path)

        logger.info(f"Successfully processed and indexed file: {file_path}")
        return True

    except Exception as e:
        logger.error(f"Error in add_file_to_vector_db: {str(e)}")
        return False

def answer_question(question: str, vector_db_path: str) -> str:
    """
    Ответить на вопрос, используя векторную базу данных
    """
    try:
        # Создаем или получаем экземпляр VectorDB
        vector_db = VectorDB(
            os.path.join(vector_db_path, "vector_index.faiss"),
            os.path.join(vector_db_path, "documents.json")
        )

        # Ищем похожие документы
        results = vector_db.search(question, top_k=3)

        if not results:
            return "К сожалению, не удалось найти релевантную информацию для ответа на ваш вопрос."

        # Формируем ответ из найденных документов
        response = "На основе найденных материалов:\n\n"
        for i, doc in enumerate(results, 1):
            if isinstance(doc, dict) and 'text' in doc:
                response += f"{i}. {doc['text']}\n\n"
            else:
                response += f"{i}. {doc}\n\n"

        return response

    except Exception as e:
        logger.error(f"Error in answer_question: {str(e)}")
        return "Произошла ошибка при поиске ответа на ваш вопрос."

if __name__ == "__main__":
    # Пример использования
    vector_db_path = os.path.join(os.getcwd(), "app", "data")
    question = "Что такое векторная база данных?"
    print(answer_question(question, vector_db_path))