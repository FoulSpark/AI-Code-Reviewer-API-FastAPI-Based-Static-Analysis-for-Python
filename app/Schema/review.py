from pydantic import BaseModel
from enum import Enum
from typing import List

class Status(str,Enum):
    pass_ = "pass"
    warn = "warn"
    fail = "fail"
    
class Severity(str,Enum):
    low = "low"
    medium = "medium"
    high = "high"

class Issues(BaseModel):
    type:str
    severity : Severity
    line : int
    message : str
    suggestion : str

class Metrics(BaseModel):
    line_count : int
    function_count : int
    complexity_score : int

class ReviewRequest(BaseModel):
    code: str
    language: str = "python"

class syntax(BaseModel):
    review_id : str
    status : Status
    overall_score : int
    summary : str
    issues : List[Issues]
    metrics : Metrics

