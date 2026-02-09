# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Always use `uv` to run Python files and add dependencies.

```bash
# Install dependencies
uv sync

# Add a dependency
uv add <package>

# Run a Python file
uv run python <file>

# Start the server (from backend/ directory)
cd backend
uv run uvicorn app:app --reload --port 8000
```

Web interface: <http://localhost:8000>
API docs: <http://localhost:8000/docs>

## Environment

Requires a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=...
ANTHROPIC_BASE_URL=...   # optional, defaults to Anthropic's endpoint
```

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot for course materials. FastAPI backend + static HTML/JS frontend.

### Query Flow

Frontend `POST /api/query` → `app.py` → `RAGSystem.query()` → `AIGenerator.generate_response()` → Claude API with tool-use. Claude decides whether to call `search_course_content` tool or answer directly. If the tool is called, `CourseSearchTool` runs a vector search against ChromaDB, results are fed back to Claude in a second API call for the final answer.

### Key Components (all in `backend/`)

- **`rag_system.py`** — Central orchestrator. Wires together all components. Entry point is `query()` for user questions, `add_course_folder()` for document ingestion.
- **`ai_generator.py`** — Anthropic client wrapper. Handles single-turn and tool-use (two-turn) Claude API calls. System prompt is a static class variable.
- **`vector_store.py`** — ChromaDB wrapper with **two collections**: `course_catalog` (one doc per course for fuzzy name resolution) and `course_content` (chunked text for semantic search). Embeddings via `sentence-transformers/all-MiniLM-L6-v2`.
- **`document_processor.py`** — Parses structured `.txt` files (header metadata + `Lesson N:` markers) and chunks text on sentence boundaries (800 char chunks, 100 char overlap).
- **`search_tools.py`** — Tool abstraction for Claude's tool-use. `CourseSearchTool` implements the `Tool` ABC. `ToolManager` registers tools and dispatches calls by name.
- **`session_manager.py`** — In-memory conversation history (not persisted across restarts). History is formatted as text and appended to the system prompt.
- **`models.py`** — Pydantic models: `Course`, `Lesson`, `CourseChunk`.

### Document Format

Course `.txt` files in `docs/` follow a specific format: 3 header lines (`Course Title:`, `Course Link:`, `Course Instructor:`), then `Lesson N: Title` markers with optional `Lesson Link:` lines. Content between markers is that lesson's text.

### Data Flow at Startup

`app.py` startup event → `rag_system.add_course_folder("../docs/")` → for each `.txt` file: parse headers + lessons → chunk lesson text → store in ChromaDB (skips courses already in the catalog).

### ChromaDB Collections

The vector database has two collections (both embedded via `sentence-transformers/all-MiniLM-L6-v2`):

**`course_catalog`** — stores course titles for name resolution
- Document: course title (used for embedding)
- ID: course title
- Metadata: `title`, `instructor`, `course_link`, `lesson_count`, `lessons_json` (JSON array of `{lesson_number, lesson_title, lesson_link}`)

**`course_content`** — stores text chunks for semantic search
- Document: chunk text (with lesson/course prefix baked in)
- ID: `{title_with_underscores}_{chunk_index}`
- Metadata: `course_title`, `lesson_number`, `chunk_index`

Search uses a two-step approach: first vector-search `course_catalog` to resolve a fuzzy course name to an exact title, then filter `course_content` by that title. This lets users say "MCP course" instead of the exact title.
