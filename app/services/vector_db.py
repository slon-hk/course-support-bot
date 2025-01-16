import os
import json
import faiss
import numpy as np
import logging
from sentence_transformers import SentenceTransformer
import traceback

logger = logging.getLogger(__name__)

class VectorDB:
    def __init__(self, index_path, documents_path):
        """Initialize vector database with paths for index and documents"""
        self.index_path = index_path
        self.documents_path = documents_path
        self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
        self.embedding_dim = 768  # Размерность для модели paraphrase-multilingual-mpnet-base-v2

        # Создаем директории если они не существуют
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        os.makedirs(os.path.dirname(documents_path), exist_ok=True)

        self.documents = []
        self.index = None

        # Пытаемся загрузить существующий индекс и документы
        self.load()

        # Если индекс не существует, создаем новый
        if self.index is None:
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            logger.info(f"Created new FAISS index with dimension {self.embedding_dim}")
            # Сразу сохраняем пустой индекс
            self.save()

    def load(self):
        """Load index and documents from files"""
        try:
            if os.path.exists(self.index_path):
                try:
                    self.index = faiss.read_index(self.index_path)
                    logger.info("Successfully loaded index")
                except Exception as e:
                    logger.error(f"Error reading index: {str(e)}")
                    self.index = None
            else:
                logger.info(f"Index file not found at: {self.index_path}")

            if os.path.exists(self.documents_path):
                try:
                    with open(self.documents_path, 'r', encoding='utf-8') as f:
                        self.documents = json.load(f)
                    logger.info(f"Successfully loaded documents, count: {len(self.documents)}")
                except Exception as e:
                    logger.error(f"Error reading documents: {str(e)}")
                    self.documents = []
            else:
                logger.info(f"Documents file not found at: {self.documents_path}")

        except Exception as e:
            logger.error(f"Error loading database: {e}\n{traceback.format_exc()}")
            self.index = None
            self.documents = []

    def save(self):
        """Save index and documents to files"""
        try:
            # Сохраняем индекс
            try:
                faiss.write_index(self.index, self.index_path)
                logger.info(f"Index saved to {self.index_path}")
            except Exception as e:
                logger.error(f"Error saving index: {e}\n{traceback.format_exc()}")
                return False

            # Сохраняем документы в JSON формате
            try:
                with open(self.documents_path, 'w', encoding='utf-8') as f:
                    json.dump(self.documents, f, ensure_ascii=False, indent=2)
                logger.info(f"Documents saved to {self.documents_path}")
            except Exception as e:
                logger.error(f"Error saving documents: {e}\n{traceback.format_exc()}")
                return False

            return True
        except Exception as e:
            logger.error(f"Error saving database: {e}\n{traceback.format_exc()}")
            return False

    def add_document(self, text, document_id):
        """Add document to index"""
        try:
            if not text or not isinstance(text, str):
                logger.error(f"Invalid text for document {document_id}")
                return False

            # Создаем embedding
            embedding = self.model.encode([text])[0]
            if embedding is None:
                logger.error(f"Failed to create embedding for document {document_id}")
                return False

            # Проверяем размерность embedding
            if embedding.shape[0] != self.embedding_dim:
                logger.error(f"Wrong embedding dimension: {embedding.shape[0]}, expected {self.embedding_dim}")
                return False

            # Добавляем документ в список
            self.documents.append({
                'id': document_id,
                'text': text
            })

            try:
                # Добавляем embedding в индекс
                embedding_array = np.array([embedding]).astype('float32')
                self.index.add(embedding_array)
            except Exception as e:
                logger.error(f"Error adding embedding to index: {e}\n{traceback.format_exc()}")
                # Удаляем документ из списка, так как не удалось добавить в индекс
                self.documents.pop()
                return False

            # Сохраняем изменения
            if not self.save():
                # Если не удалось сохранить, откатываем изменения
                self.documents.pop()
                return False

            logger.info(f"Document {document_id} successfully added to database")
            return True

        except Exception as e:
            logger.error(f"Error adding document: {e}\n{traceback.format_exc()}")
            return False

    def search(self, query, top_k=3):
        """Search for similar documents"""
        try:
            if not query or not isinstance(query, str):
                logger.error("Invalid query for search")
                return []

            if self.index.ntotal == 0:
                logger.warning("Database is empty")
                return []

            # Создаем embedding запроса
            query_embedding = self.model.encode([query])[0]
            if query_embedding is None:
                logger.error("Failed to create embedding for query")
                return []

            query_embedding = np.array([query_embedding]).astype('float32')

            # Ищем похожие документы
            try:
                distances, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))
                logger.info(f"Found {len(indices[0])} documents for query")
            except Exception as e:
                logger.error(f"Error searching in index: {e}\n{traceback.format_exc()}")
                return []

            results = []
            for idx in indices[0]:
                if idx >= 0 and idx < len(self.documents):
                    results.append(self.documents[idx])
            return results
        except Exception as e:
            logger.error(f"Error during search: {e}\n{traceback.format_exc()}")
            return []

    def remove_document(self, document_id):
        """Удаление документа из индекса"""
        try:
            # Находим индекс документа в списке
            doc_idx = None
            for idx, doc in enumerate(self.documents):
                if doc['id'] == document_id:
                    doc_idx = idx
                    break

            if doc_idx is not None:
                # Удаляем документ из списка
                self.documents.pop(doc_idx)

                # Создаем новый индекс
                new_index = faiss.IndexFlatL2(self.embedding_dim)

                # Переиндексируем оставшиеся документы
                for doc in self.documents:
                    embedding = self.model.encode([doc['text']])[0]
                    embedding_array = np.array([embedding]).astype('float32')
                    new_index.add(embedding_array)

                # Заменяем старый индекс новым
                self.index = new_index
                self.save()

                logger.info(f"Документ {document_id} успешно удален из базы")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при удалении документа: {e}")
            return False