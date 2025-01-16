import os
from PyPDF2 import PdfReader
from docx import Document
import mammoth

def split_into_chunks(text, chunk_size):
    chunks = []
    while len(text) > chunk_size:
        split_index = text[:chunk_size].rfind(" ")
        if split_index == -1:
            split_index = chunk_size
        chunks.append(text[:split_index].strip())
        text = text[split_index:].strip()
    if text:
        chunks.append(text)
    return chunks


def process_pdf(file_path, chunk_size=4000):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return split_into_chunks(text, chunk_size)


def process_docx(file_path, chunk_size=4000):
    try:
        with open(file_path, "rb") as docx_file:
            result = mammoth.extract_raw_text(docx_file)
            text = result.value
            return split_into_chunks(text, chunk_size)
    except Exception as e:
        print(f"Ошибка при обработке файла DOCX: {e}")
        return []


def process_txt(file_path, chunk_size=4000):
    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()
    return split_into_chunks(text, chunk_size)


def process_file(file_path, chunk_size=4000):
    file_extension = os.path.splitext(file_path)[-1].lower()
    if file_extension == ".pdf":
        return process_pdf(file_path, chunk_size)
    elif file_extension == ".docx":
        return process_docx(file_path, chunk_size)
    elif file_extension == ".txt":
        return process_txt(file_path, chunk_size)
    else:
        raise ValueError(f"Unsupported file format: {file_extension}")