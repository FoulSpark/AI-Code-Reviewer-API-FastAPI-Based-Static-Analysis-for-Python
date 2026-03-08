import ast
from typing import List,Dict
from app.Schema.review import Issues,Severity


def check_syntax(code : str) -> List[Issues]:
    try:
        ast.parse(code)
        return []
    except SyntaxError as e:
        return [Issues(type="syntax error",
                       severity= Severity.high,
                       line=e.lineno or 1,
                       message=e.msg,
                       suggestion="Fix the syntax error and try again",
                       )]

