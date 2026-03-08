import uuid
from app.Schema.review import Status,syntax , Metrics , Severity 
from app.Services.security_checker import security_check
from app.Services.syntax_checker import check_syntax
from app.Services.style_checker import check_styling

def to_review(code:str) -> syntax:
    
    syntax_issues = check_syntax(code)
    security_issues = security_check(code)
    styling_issue = check_styling(code)

    issues = syntax_issues+security_issues+styling_issue

    line_count = len(code.splitlines())
    function_count = code.count("def")
    complexity_score = 1
    complexity_score += sum(1 for line in code.splitlines() if line.strip().startswith(("if ", "for ", "while ", "try:", "except", "with ")))


    overall_score = 100
    for issue in issues:
        if issue.severity == "high":
            overall_score-=25
        if issue.severity == "medium":
            overall_score-=10
        if issue.severity =="low":
            overall_score-=5

    overall_score = max(0,min(100,overall_score))

    if any(issue.type == "syntax" for issue in issues):
        status = Status.fail
        summary = "code contains syntax errors"
    
    elif any(issue.type == "security" for issue in issues):
        status = Status.warn
        summary = "Code is syntactically valid but contains risky security patterns."
    
    elif any(issue.type in {"style","complexity"} for issue in issues):
        status = Status.warn
        summary = "Code is valid but has style or maintainability issues."
    
    else:
        status = Status.pass_
        summary = "Code passed basic review."

    return syntax(
        review_id=f"rev_{uuid.uuid4().hex[:8]}",
        status=status,
        overall_score=overall_score,
        summary = summary,
        issues = issues,
        metrics=Metrics(
            line_count=line_count,
            function_count = function_count,
            complexity_score = complexity_score,
    )
    )

