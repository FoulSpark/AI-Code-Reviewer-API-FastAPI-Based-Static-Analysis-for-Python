# AI Code Reviewer

A lightweight **Python code review service** with:

- A **FastAPI** backend that analyzes submitted Python code.
- A **Streamlit** UI for pasting code and viewing results.
- **SQLite** persistence (`reviews.db`) so you can fetch past reviews by ID.

It performs a basic, deterministic review (no LLM required) across:

- Syntax validity
- Security anti-patterns
- Style / maintainability checks
- Simple complexity heuristics

---

## Features

- **One-click review** from the Streamlit frontend.
- **Structured results**: status (`pass`/`warn`/`fail`), overall score, summary, issues, metrics.
- **Issue severity** levels: `low`, `medium`, `high`.
- **Metrics**:
  - `line_count`
  - `function_count`
  - `complexity_score` (simple nesting/keyword heuristic)
- **History**: every review is saved in SQLite and can be retrieved later.

---

## Project Structure

```text
ai_code_reviewer/
  app/
    main.py                  # FastAPI app (API entrypoint)
    Schema/
      review.py              # Pydantic models (request/response schema)
    Services/
      review_engine.py       # Orchestrates all checks, calculates score/status
      syntax_checker.py      # AST-based syntax validation
      security_checker.py    # AST-based detection of risky patterns
      style_checker.py       # Style + basic complexity heuristics
      scorer.py              # (currently empty)
    db/
      storage.py             # SQLite init + save + fetch
      example.json           # Example response payload
  streamlit_app.py           # Streamlit UI (frontend)
  reviews.db                 # SQLite database (created/used at runtime)
```

---

## How It Works (High Level)

1. The Streamlit UI sends your code to the backend via `POST http://127.0.0.1:8000/review`.
2. The FastAPI backend runs the code through:
   - `check_syntax()`
   - `security_check()`
   - `check_styling()`
3. A combined list of issues is produced.
4. The backend computes:
   - `metrics` (lines, function count, complexity)
   - `overall_score` (starts at 100 and subtracts points by severity)
   - `status` + `summary` (based on whether issues exist and their type)
5. The review is saved into SQLite (`reviews.db`) and returned to the client.

---

## API

### `POST /review`

Creates a new review and persists it.

- **Request body**

```json
{
  "code": "def add(a,b):\n    return a+b\n",
  "language": "python"
}
```

- **Response body (shape)**

```json
{
  "review_id": "rev_1a2b3c4d",
  "status": "warn",
  "overall_score": 72,
  "summary": "Code is syntactically valid but contains risky security patterns.",
  "issues": [
    {
      "type": "security",
      "severity": "high",
      "line": 8,
      "message": "Use of eval() detected.",
      "suggestion": "Avoid eval(). Use safer parsing or explicit logic."
    }
  ],
  "metrics": {
    "line_count": 40,
    "function_count": 3,
    "complexity_score": 6
  }
}
```

### `GET /review/{review_id}`

Fetches a saved review by ID.

- **Example**

`GET http://127.0.0.1:8000/review/rev_1a2b3c4d`

---

## Running Locally

### 1) Create and activate a virtual environment (recommended)

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

This repository currently does **not** include a `requirements.txt`.

Install the minimum required packages:

```powershell
pip install fastapi uvicorn streamlit requests pydantic
```

### 3) Start the FastAPI backend

From the repository root:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 4) Start the Streamlit frontend

In a second terminal:

```powershell
streamlit run streamlit_app.py
```

Open the Streamlit URL shown in your terminal (usually `http://localhost:8501`).

---

## Notes / Known Gaps

- **Endpoint naming mismatch to be aware of**:
  - The Streamlit UI currently calls `GET /reviews/{id}`.
  - The FastAPI backend implements `GET /review/{review_id}`.

If you want the “Fetch Review by ID” section in Streamlit to work without changes, update one side to match the other.

- `app/Services/scorer.py` exists but is currently empty.

---

## Example Payload

A sample output object is provided at:

- `app/db/example.json`

---

## Tech Stack

- **Backend**: FastAPI
- **Frontend**: Streamlit
- **Storage**: SQLite
- **Analysis**: Python `ast` module + simple heuristics

---
