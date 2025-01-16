import os
import json
import faiss
from sentence_transformers import SentenceTransformer
from file_processing import process_file 


class VectorDB:
    def __init__(
        self,
        embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
        embedding_dim=384,
        index_file="db/vector_index.faiss",
        documents_file="db/documents.json",
    ):
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.embedding_dim = embedding_dim
        self.index_file = index_file
        self.documents_file = documents_file

        self.index = self._load_index()
        self.documents = self._load_documents()

    def add_document(self, file_path):
        print(f"Обработка файла: {file_path}")
        try:
            chunks = process_file(file_path)
            for chunk in chunks:
                if chunk.strip():
                    self.documents.append(chunk)
                    embedding = self.embedding_model.encode(chunk)
                    self.index.add(embedding.reshape(1, -1))
            print(f"Файл '{file_path}' успешно добавлен в базу.")
        except Exception as e:
            print(f"Ошибка при обработке файла: {e}")

    def search(self, query, top_k=3):
        query_embedding = self.embedding_model.encode(query).reshape(1, -1)
        distances, indices = self.index.search(query_embedding, top_k)
        return [self.documents[i] for i in indices[0] if i < len(self.documents)]

    def save(self):
        self._save_index()
        self._save_documents()

    def _load_index(self):
        if os.path.exists(self.index_file):
            print(f"Загрузка индекса из файла: {self.index_file}")
            return faiss.read_index(self.index_file)
        print("Файл индекса не найден. Создаётся новый индекс.")
        return faiss.IndexFlatL2(self.embedding_dim)

    def _save_index(self):
        faiss.write_index(self.index, self.index_file)
        print(f"Индекс сохранён в файл: {self.index_file}")

    def _load_documents(self):
        if os.path.exists(self.documents_file):
            print(f"Загрузка документов из файла: {self.documents_file}")
            with open(self.documents_file, "r", encoding="utf-8") as f:
                return json.load(f)
        print("Файл с документами не найден. Используется пустой список.")
        return []

    def _save_documents(self):
        with open(self.documents_file, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=4)
        print(f"Документы сохранены в файл: {self.documents_file}")