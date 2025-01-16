import os
import logging
from typing import List, Dict, Any
from docx import Document
import PyPDF2
import mammoth
import numpy as np
from sentence_transformers import SentenceTransformer
from app.services.vector_db import VectorDB
import hashlib

logger = logging.getLogger(__name__)

class FileProcessor:
    def __init__(self, vector_db_path: str):
        """Initialize FileProcessor with vector database path"""
        self.vector_db_path = vector_db_path
        os.makedirs(vector_db_path, exist_ok=True)

        # Инициализация модели для эмбеддингов
        self.embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')

        # Initialize VectorDB with specific paths for index and documents
        self.vector_db = VectorDB(
            index_path=os.path.join(vector_db_path, "vector_index.faiss"),
            documents_path=os.path.join(vector_db_path, "documents.json")
        )
        logger.info(f"FileProcessor initialized with vector DB path: {vector_db_path}")

    def extract_text(self, file_path: str, file_type: str) -> str:
        """Extract text content from a file based on its type"""
        try:
            if file_type == 'docx':
                return self._extract_text_from_docx(file_path)
            elif file_type == 'pdf':
                return self._extract_text_from_pdf(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
        except Exception as e:
            logger.error(f"Error extracting text from file: {str(e)}")
            raise

    def _extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            with open(file_path, "rb") as docx_file:
                result = mammoth.extract_raw_text(docx_file)
                return result.value
        except Exception as e:
            logger.error(f"Error processing DOCX file {file_path}: {str(e)}")
            raise

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error(f"Error processing PDF file {file_path}: {str(e)}")
            raise

    def create_embedding(self, text: str) -> np.ndarray:
        """Create vector embedding for text using sentence transformer"""
        try:
            return self.embedding_model.encode(text)
        except Exception as e:
            logger.error(f"Error creating embedding: {str(e)}")
            raise

    def _generate_document_id(self, file_path: str, text: str) -> str:
        """Generate a unique document ID based on file path and content"""
        hash_input = f"{file_path}:{text}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def process_file(self, file_path: str) -> bool:
        """Process and index a file into the vector database"""
        try:
            logger.info(f"Processing file: {file_path}")
            # Get file extension
            file_ext = os.path.splitext(file_path)[1].lower().replace('.', '')

            # Extract text based on file type
            text = self.extract_text(file_path, file_ext)

            if not text:
                logger.warning(f"No text content extracted from file: {file_path}")
                return False

            # Generate unique document ID
            document_id = self._generate_document_id(file_path, text)

            # Add to vector database
            self.vector_db.add_document(text, document_id)
            logger.info(f"Successfully processed file: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return False