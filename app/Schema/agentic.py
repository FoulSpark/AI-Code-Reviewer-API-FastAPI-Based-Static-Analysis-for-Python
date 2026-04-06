from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from app.Schema.review import Status, Metrics, Issues

class GenerateRequest(BaseModel):
    user_request: str
    language: str = "python"
    force_run: bool = False

class FixRequest(BaseModel):
    code: str
    issues: List[Issues]
    language: str = "python"
    force_run: bool = False

class AgenticResponse(BaseModel):
    review_id: str
    code: str
    language: str
    retry_count: int
    stages_run: List[str]
    errors_encountered: List[Dict[str, Any]]
    model_used: str = "gemini-1.5-pro"
    status: Status = Status.pass_
    summary: str = "Code generated and validated."
    safety_flag: bool = True
    safety_warning: Optional[str] = None
    requires_confirmation: bool = False
