# AI Document Assistant (Telegram Bot + Web)

**A RAG-powered assistant that lets users ask questions about their documents in natural language — available as both a Telegram bot and a web app.**

Users upload documents, and the assistant answers questions using the content of those documents. It combines document processing, vector embeddings, and semantic search so that the language model responds with grounded, relevant answers instead of generic ones.

---

## Features

- **Ask questions about your documents** — Natural-language Q&A over uploaded files.
- **RAG pipeline** — Documents are processed, embedded, and indexed; on each query the system retrieves the **single best-matching** chunk and passes only that context to the LLM.
- **Two interfaces** — Works as a Telegram bot and as a web application from the same backend.
- **Document management** — Upload and process files for later querying.
- **LLM integration** — Connects to a language-model API for answer generation.

---

## Tech Stack

| Layer            | Technology                                  |
| ---------------- | ------------------------------------------- |
| **Language**     | Python                                      |
| **AI / RAG**     | LLM API, vector embeddings, semantic search |
| **Interfaces**   | Telegram bot + web (HTML templates)         |
| **File handling**| Document parsing & processing               |

---

## How It Works

1. A user uploads a document (via the bot or the website).
2. The document is parsed and split into chunks.
3. Each chunk is converted into a vector embedding.
4. When the user asks a question, the system runs a semantic search and selects the best-matching passage.
5. Only that passage is sent to the LLM as context, producing a focused, grounded answer.

---

## Project Structure

```
.
├── app/                 # Application package
├── ai.py                # LLM integration + answer generation
├── file_processing.py   # Document parsing, chunking, embeddings
├── main.py              # Web entry point
├── run_bot.py           # Telegram bot entry point
├── run.py               # Runner
└── pyproject.toml       # Dependencies (managed with uv)
```

---

## Quick Start

**Prerequisites:** Python 3.11+ and [uv](https://github.com/astral-sh/uv)

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment variables
cp .env.example .env
# Set your LLM_API_KEY, TELEGRAM_BOT_TOKEN, and database credentials

# 3. Run the web app
python main.py

# 4. Or run the Telegram bot
python run_bot.py
```

---

## Configuration

| Variable             | Description                          |
| -------------------- | ------------------------------------ |
| `LLM_API_KEY`        | API key for the language model       |
| `TELEGRAM_BOT_TOKEN` | Token from BotFather (for bot mode)  |
| `DATABASE_URL`       | Connection string for the database   |

---

## License

MIT
