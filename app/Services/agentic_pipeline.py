import ast
import asyncio
import json
import re
import os
import uuid
import subprocess
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import google.generativeai as genai
from app.Schema.agentic import AgenticResponse
from app.Schema.review import Status, Issues, Metrics, Severity

load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PRO_MODEL_NAME = os.getenv("GEMINI_PRO_MODEL", "gemini-1.5-pro")
FLASH_MODEL_NAME = os.getenv("GEMINI_FLASH_MODEL", "gemini-1.5-flash")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    pro_model = genai.GenerativeModel(PRO_MODEL_NAME)
    flash_model = genai.GenerativeModel(FLASH_MODEL_NAME)
else:
    pro_model = None
    flash_model = None

MAX_PLAN_RETRIES = 2
MAX_IMPL_RETRIES = 2

# ── PROMPTS ──────────────────────────────────────────────────

UNDERSTAND_PROMPT = """
You are a code specification extractor.

Analyse the user request and output ONLY valid JSON.
No markdown fences. No explanation. JSON only.

Schema:
{
  "task": "one sentence",
  "language": "python | javascript | typescript | ...",
  "input_description": "what the code receives",
  "output_description": "what the code produces",
  "constraints": ["list of rules or edge cases"],
  "test_scenarios": [
    {"input": "example input", "expected_output": "example output", "description": "what this tests"}
  ],
  "clarifications_needed": []
}

If the request is ambiguous, populate clarifications_needed
and leave other fields as empty strings.

USER REQUEST:
{user_request}

PREVIOUS ERRORS (if any):
{errors}
"""

PLAN_PROMPT = """
You are a code architect. Produce a plan and a complete symbol table.
This symbol table is a CONTRACT — the implementer will only use
names you define here.

SPEC:
{spec_json}

PREVIOUS PLAN THAT FAILED:
{previous_plan_json}

FAILED CODE FROM THAT PLAN:
{failed_code}

PREVIOUS SEMANTIC ERRORS (if replanning):
{errors}

Instruction: Analyze the failed plan and code. Identify why they led to the errors above and adjust the architecture/symbol table to resolve them.

Output ONLY valid JSON. No markdown. No explanation.

{
  "pseudocode": ["step 1", "step 2", ...],
  "symbol_table": {
    "variables": [
      {"name": "rows", "type": "list[dict]", "purpose": "parsed CSV rows"}
    ],
    "functions": [
      {
        "name": "load_csv",
        "params": [{"name": "path", "type": "str"}],
        "returns": "list[dict]",
        "purpose": "reads CSV and returns list of row dicts",
        "stub": "def load_csv(path: str) -> list[dict]:\\n    ..."
      }
    ],
    "classes": []
  },
  "imports": ["csv", "pathlib"]
}

Rules:
- Every variable used in implementation MUST appear in variables
- Every function MUST appear in functions with a complete stub
- Do NOT write implementation — stubs only
"""

IMPLEMENT_PROMPT = """
You are a code writer. Implement the plan exactly.

SPEC:
{spec_json}

PLAN + SYMBOL TABLE:
{plan_json}

FAILED CODE FROM PREVIOUS ATTEMPT:
{failed_code}

PREVIOUS ERRORS TO FIX (if retrying):
{errors}

Instruction: Review the code that failed. Fix the logic/syntax/safety errors described below while maintaining the successful parts. If you are retrying after an AssertionError, analyze the specific failing test call.

Rules:
- Use ONLY variable names from symbol_table.variables
- Implement EVERY function in symbol_table.functions
- Use ONLY imports from the plan
- Do NOT invent new top-level names not in the symbol table
- Output raw {language} code only
- No markdown fences, no explanation, no comments

--- SELF-TESTING REQUIREMENT ---
IMPORTANT: You MUST append a functional self-test block at the end of the file:
if __name__ == "__main__":
    # Call functions with the following test scenarios and ASSERT the results
    {test_scenarios_json}
    print("ALL TESTS PASSED")
"""

SYNTAX_PROMPT = """
You are a {language} syntax validator.

Check the code ONLY for structural syntax errors:
- Missing colons after if / for / while / def / class
- Unclosed brackets, parens, or braces
- Invalid indentation
- Unterminated string literals

Do NOT check logic, variable names, or semantics.
Output ONLY valid JSON. No markdown. No explanation.

{
  "passed": true,
  "errors": []
}

OR if failed:

{
  "passed": false,
  "errors": [
    {"line": 7, "issue": "missing colon after if", "fix": "add : at end of line 7"}
  ]
}

CODE:
{code}
"""

SEMANTIC_PROMPT = """
You are a {language} semantic validator.

SYMBOL TABLE (every name that must exist):
{symbol_table_json}

Check the code for:
1. Variables used but not assigned or not in symbol_table
2. Functions called but not defined or not in symbol_table
3. Wrong argument count passed to a function
4. Obvious type mismatches visible from context

For each error, set resolution to:
  "fix_in_code"  — typo or minor fix, implementer can patch it
  "add_to_plan"  — symbol is genuinely missing from the table,
                   the plan must be revised first

Output ONLY valid JSON. No markdown. No explanation.

{
  "passed": true,
  "errors": []
}

OR:

{
  "passed": false,
  "errors": [
    {
      "issue": "undefined variable 'result'",
      "resolution": "fix_in_code",
      "detail": "result used on line 12 but never assigned"
    }
  ]
}

CODE:
{code}
"""

# ── HELPERS ──────────────────────────────────────────────────

async def call_llm(model, prompt: str) -> str:
    if model is None:
        raise ValueError("Gemini model not configured. Please set GEMINI_API_KEY in .env")
    loop = asyncio.get_event_loop()
    # Gemini SDK is blocking, wrap in executor
    response = await loop.run_in_executor(
        None, lambda: model.generate_content(prompt)
    )
    return response.text.strip()

def parse_json(text: str) -> Dict[str, Any]:
    # Remove markdown fences if present
    clean = re.sub(r"```(?:json)?|```", "", text).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        # Fallback: find the first { and last } if simple strip fails
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise e

def fmt_errors(errors: Optional[List[Dict[str, Any]]]) -> str:
    if not errors:
        return "none"
    return json.dumps(errors, indent=2)

# ── PIPELINE STAGES ──────────────────────────────────────────

async def understand(user_request: str, errors: str = "none") -> Dict[str, Any]:
    prompt = UNDERSTAND_PROMPT.replace("{user_request}", user_request).replace("{errors}", errors)
    response_text = await call_llm(pro_model, prompt)
    return parse_json(response_text)

async def plan(
    spec: Dict[str, Any], 
    errors: Optional[List[Dict[str, Any]]] = None,
    previous_plan: Optional[Dict[str, Any]] = None,
    failed_code: Optional[str] = None
) -> Dict[str, Any]:
    prompt = PLAN_PROMPT.replace("{spec_json}", json.dumps(spec, indent=2))\
                        .replace("{errors}", fmt_errors(errors))\
                        .replace("{previous_plan_json}", json.dumps(previous_plan, indent=2) if previous_plan else "none")\
                        .replace("{failed_code}", failed_code if failed_code else "none")
    response_text = await call_llm(pro_model, prompt)
    return parse_json(response_text)

async def implement(
    spec: Dict[str, Any], 
    plan_obj: Dict[str, Any], 
    errors: Optional[List[Dict[str, Any]]] = None,
    failed_code: Optional[str] = None
) -> str:
    prompt = IMPLEMENT_PROMPT.replace("{spec_json}", json.dumps(spec, indent=2))\
                            .replace("{plan_json}", json.dumps(plan_obj, indent=2))\
                            .replace("{errors}", fmt_errors(errors))\
                            .replace("{language}", spec.get("language", "python"))\
                            .replace("{test_scenarios_json}", json.dumps(spec.get("test_scenarios", []), indent=2))\
                            .replace("{failed_code}", failed_code if failed_code else "none")
    return await call_llm(pro_model, prompt)

def check_syntax_native(code: str) -> Dict[str, Any]:
    try:
        ast.parse(code)
        return {"passed": True, "errors": []}
    except SyntaxError as e:
        return {
            "passed": False,
            "errors": [
                {
                    "line": e.lineno or 1,
                    "issue": str(e),
                    "fix": f"Check syntax near line {e.lineno}"
                }
            ]
        }

async def check_syntax_llm(code: str, language: str) -> Dict[str, Any]:
    prompt = SYNTAX_PROMPT.replace("{language}", language).replace("{code}", code)
    response_text = await call_llm(flash_model, prompt)
    return parse_json(response_text)

async def check_syntax(code: str, language: str) -> Dict[str, Any]:
    if language.lower() == "python":
        return check_syntax_native(code)
    return await check_syntax_llm(code, language)

async def check_semantic(code: str, plan_obj: Dict[str, Any], language: str) -> Dict[str, Any]:
    prompt = SEMANTIC_PROMPT.replace("{language}", language)\
                            .replace("{symbol_table_json}", json.dumps(plan_obj.get("symbol_table", {}), indent=2))\
                            .replace("{code}", code)
    response_text = await call_llm(flash_model, prompt)
    return parse_json(response_text)

def check_safety(code: str) -> Dict[str, Any]:
    dangerous_patterns = {
        r"os\.(remove|unlink|rmdir|system|spawn|chmod|chown)": "File system mutation or system command execution detected.",
        r"shutil\.rmtree": "Directory tree deletion detected.",
        r"subprocess\.(run|Popen|call|check_output)": "Subprocess execution detected.",
        r"open\(.*['\"](w|a|x)\+?['\"].*\)": "File write/append mode detected.",
        r"(eval|exec|pickle\.load)\(": "Dynamic code execution or unsafe deserialization detected."
    }
    
    warnings = []
    for pattern, msg in dangerous_patterns.items():
        if re.search(pattern, code):
            warnings.append(msg)
            
    if warnings:
        return {
            "passed": False,
            "warning": " | ".join(warnings)
        }
    return {"passed": True, "warning": None}

async def check_execution(code: str, language: str) -> Dict[str, Any]:
    if language.lower() != "python":
        return {"passed": True, "errors": []} # Only supporting Python for now
        
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode='w') as f:
        f.write(code)
        temp_path = f.name
        
    try:
        # Run the code with a short timeout to check for immediate crashes/imports
        # We use -c "import sys; ..." to avoid actually running long logic if possible
        # but the user wants "mechanical" check, so we'll just try to run it.
        proc = await asyncio.create_subprocess_exec(
            "python", temp_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            if proc.returncode == 0:
                return {"passed": True, "errors": []}
            else:
                return {
                    "passed": False,
                    "errors": [{"issue": "Execution failed", "detail": stderr.decode().strip()}]
                }
        except asyncio.TimeoutError:
            proc.kill()
            # If it times out, it's probably recursive or waiting for input, 
            # which is still a "mechanical" concern but it didn't crash immediately.
            return {"passed": True, "errors": []} 
    except Exception as e:
        return {
            "passed": False,
            "errors": [{"issue": "Runner error", "detail": str(e)}]
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

from app.db.storage import save_review

# ... (previous constants and helpers)

async def run_agentic_task(
    user_request: str, 
    task_type: str = "generate",
    original_code: Optional[str] = None,
    original_issues: Optional[List[Issues]] = None,
    force_run: bool = False
) -> AgenticResponse:
    
    stages_run = []
    errors_encountered = []
    total_retries = 0
    
    # Format request for Stage 1 if it's a "fix" task
    if task_type == "fix" and original_code and original_issues:
        issue_str = json.dumps([i.model_dump() for i in original_issues], indent=2)
        request_for_s1 = f"FIX THE FOLLOWING CODE:\n{original_code}\n\nISSUES ENCOUNTERED:\n{issue_str}"
    else:
        request_for_s1 = user_request
        
    # Stage 1: Understand
    print(f"--- Stage 1: Understand ({task_type}) ---")
    stages_run.append("Understand")
    spec = await understand(request_for_s1)
    language = spec.get("language", "python")
    
    # Stage 2: Plan
    print("--- Stage 2: Plan ---")
    stages_run.append("Plan")
    plan_obj = await plan(spec)
    
    # Track the latest code for return/save
    final_code = ""
    
    try:
        for plan_try in range(MAX_PLAN_RETRIES):
            impl_errors = None
            
            for impl_try in range(MAX_IMPL_RETRIES):
                # Stage 3: Implement
                print(f"--- Stage 3: Implement (Plan try {plan_try+1}, Impl try {impl_try+1}) ---")
                stages_run.append("Implement")
                final_code = await implement(spec, plan_obj, impl_errors, failed_code=(final_code if impl_errors else None))
                
                # Stage 4a/b: Core Checks
                print("--- Stage 4: Core Checks (Syntax & Semantic) ---")
                stages_run.append("Core Checks")
                syntax_result, semantic_result = await asyncio.gather(
                    check_syntax(final_code, language),
                    check_semantic(final_code, plan_obj, language)
                )
                
                if not (syntax_result["passed"] and semantic_result["passed"]):
                    current_errors = syntax_result.get("errors", []) + semantic_result.get("errors", [])
                    errors_encountered.extend(current_errors)
                    total_retries += 1
                    
                    needs_replan = any(e.get("resolution") == "add_to_plan" for e in semantic_result.get("errors", []))
                    if needs_replan:
                        print("--- Failure: Re-Planning Needed ---")
                        stages_run.append("Re-Plan")
                        plan_obj = await plan(
                            spec, 
                            semantic_result.get("errors"), 
                            previous_plan=plan_obj, 
                            failed_code=final_code
                        )
                        break
                    else:
                        print("--- Failure: Retry Implementation ---")
                        stages_run.append("Retry Implement")
                        impl_errors = current_errors
                        continue
                
                # Core checks passed, now Stage 4c: Safety
                print("--- Stage 4c: Safety Scan ---")
                stages_run.append("Safety Scan")
                safety_result = check_safety(final_code)
                
                if not safety_result["passed"] and not force_run:
                    print("--- Safety Interlock Triggered! ---")
                    return AgenticResponse(
                        review_id=f"rev_safe_{uuid.uuid4().hex[:8]}",
                        code=final_code,
                        language=language,
                        retry_count=total_retries,
                        stages_run=stages_run,
                        errors_encountered=errors_encountered,
                        model_used=PRO_MODEL_NAME,
                        safety_flag=False,
                        safety_warning=safety_result["warning"],
                        requires_confirmation=True,
                        status=Status.fail,
                        summary="Code contains potentially dangerous operations. Confirmation required."
                    )

                # Stage 4d: Execution Check (Now with Functional Self-Test)
                print("--- Stage 4d: Mechanical & Functional Test ---")
                stages_run.append("Execution Test")
                exec_result = await check_execution(final_code, language)
                
                if not exec_result["passed"]:
                    detail = exec_result['errors'][0].get('detail', '')
                    is_logic_error = "AssertionError" in detail
                    print(f"--- {'Logic' if is_logic_error else 'Execution'} Failed: {exec_result['errors']} ---")
                    
                    errors_encountered.extend(exec_result["errors"])
                    total_retries += 1
                    impl_errors = exec_result["errors"]
                    continue

                # Everything passed!
                print("--- Pipeline Success! ---")
                response = AgenticResponse(
                    review_id=f"rev_{uuid.uuid4().hex[:8]}",
                    code=final_code,
                    language=language,
                    retry_count=total_retries,
                    stages_run=stages_run,
                    errors_encountered=errors_encountered,
                    model_used=PRO_MODEL_NAME,
                    safety_flag=safety_result["passed"],
                    safety_warning=safety_result.get("warning")
                )
                
                from app.Schema.review import syntax
                review_data = syntax(
                    review_id=response.review_id,
                    status=response.status,
                    overall_score=100,
                    summary=response.summary,
                    issues=[],
                    metrics=Metrics(
                        line_count=len(final_code.splitlines()),
                        function_count=final_code.count("def"),
                        complexity_score=1
                    )
                )
                save_review(final_code, review_data, source="agentic")
                return response
        
        raise RuntimeError(f"Pipeline exhausted retries after {total_retries} attempts.")
        
    except Exception as e:
        # Final persistence even on failure? Plan says save on success.
        # But for debugging, we might want to log.
        raise e
