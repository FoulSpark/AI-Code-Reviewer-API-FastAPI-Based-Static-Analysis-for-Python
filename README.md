# 🚀 Agentic AI Code Reviewer & Generator

A high-performance, **Agent-Driven Code Analysis and Generation** system. This platform combines traditional AST-based static analysis with a cutting-edge **4-Stage Agentic Pipeline** to not only find issues but autonomously fix them and verify the logic.

---

## 🌟 Key Features

### 🧠 Agentic AI Studio (New)
A dedicated environment for **Autonomous Code Generation**. Provide a requirement, and the AI orchestrator will:
1.  **Understand**: Extract core logic, constraints, and test scenarios.
2.  **Plan**: Design a symbol table and architectural contract.
3.  **Implement**: Write the code including a functional self-test footer.
4.  **Check**: Parallelize Syntax & Semantic validation.

### 🛡️ Safety Interlock
Every line of AI-generated code passes through a **Static Safety Scan**. 
- Flags dangerous patterns: `os.remove`, `rmtree`, `subprocess`, `eval`, and unsafe file writes.
- Requires explicit user confirmation via the UI if risky operations are detected.

### ⚙️ Mechanical & Functional Validation
We don't just generate code; we prove it works.
- **Touch Test**: Automatically executes the code in a secure subprocess.
- **Logic Assertions**: Uses the generated self-test footer to verify that the code handles real inputs correctly before delivery.

### 🔄 Context-Aware Retries
The pipeline learns from its own failures. If a check fails, the next retry receives the **Failed Code** and **Previous Plan**, allowing the AI to "Refine" instead of just "Repeat."

---

## 🛠️ Tech Stack

- **Core**: FastAPI (Backend), Streamlit (Frontend)
- **AI Models**: 
  - **Gemini 1.5 Pro**: Complex Reasoning (Planning, Implementation)
  - **Gemini 1.5 Flash**: High-speed Validation (Semantic & Syntax Checks)
- **Analysis**: Python `ast` module, Subprocess Execution Runner
- **Storage**: SQLite with `agentic` source tracking

---

## 📂 Project Structure

```text
ai_code_reviewer/
  app/
    main.py                  # API Endpoints (/review, /generate, /fix)
    Schema/
      agentic.py             # Agentic Request/Response models
      review.py              # Static review schemas
    Services/
      agentic_pipeline.py    # The 4-Stage Orchestrator (The "Brain")
      review_engine.py       # Static Analysis Orchestrator
      syntax_checker.py      # AST-based validation
      security_checker.py    # Detection of risky patterns
    db/
      storage.py             # SQLite persistence with source tracking
  streamlit_app.py           # Premium UI with Agentic Studio Tab
  .env                       # API Configuration (Excluded from Git)
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.9+
- A Google Gemini API Key

### 2. Installation
```powershell
# Clone the repo
git clone https://github.com/FoulSpark/AI-Code-Reviewer-API-FastAPI-Based-Static-Analysis-for-Python.git
cd AI-Code-Reviewer-API-FastAPI-Based-Static-Analysis-for-Python

# Install dependencies
pip install fastapi uvicorn streamlit requests pydantic google-generativeai python-dotenv
```

### 3. Configuration
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_key_here
GEMINI_PRO_MODEL=gemini-2.5-flash
GEMINI_FLASH_MODEL=gemini-2.5-flash
```

### 4. Running the App
**Terminal 1 (Backend):**
```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

```

**Terminal 2 (Frontend):**
```powershell
streamlit run streamlit_app.py
```

---

## 📖 API Documentation

### `POST /generate`
Triggers the full 4-stage agentic generation pipeline.
- **Payload**: `{"user_request": "string", "language": "python"}`
- **Response**: Robust code + execution metadata.

### `POST /fix`
Accepts existing code and a list of issues, then autonomously fixes and validates them.
- **Payload**: `{"code": "...", "issues": [...], "language": "python"}`

### `POST /review`
Standard AST-based static analysis review.

---

<<<<<<< HEAD
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
=======
## ⚖️ License
This project is licensed under the MIT License - see the LICENSE file for details.
>>>>>>> b86db29 (feat: Integrated full Agentic AI Pipeline with Safety Interlock and Functional Validation. Optimized retries for self-correction and refined README for premium branding.)
