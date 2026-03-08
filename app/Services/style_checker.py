import ast 
from typing import List

from app.Schema.review import Issues , Severity

MAX_ARGS = 5 
MAx_Line_LENGTH = 88
MAX_NESTING = 3


class Style_Checker(ast.NodeVisitor):
    def __init__(self)->None:
        self.issues: List[Issues] = []

    def visit_FunctionDef(self, node:ast.FunctionDef) -> None:
        arg_count = len(node.args.args)
        if arg_count > MAX_ARGS:
            self.issues.append(Issues(
                type="style",
                severity=Severity.medium,
                line=node.lineno,
                message=f"Function '{node.name}' has too many arguments ({arg_count}).",
                suggestion="Reduce the number of parameters or group related values into a class/dataclass."

            ))
        
        if ast.get_docstring(node) is None:
            self.issues.append(
                Issues(
                    type="style",
                    severity=Severity.low,
                    line=node.lineno,
                    message=f"Function '{node.name}' is missing a docstring.",
                    suggestion="Add a short docstring explaining the function purpose, inputs, and output."
                )
            )
            
def check_nesting(node : ast.AST , curr_depth : int=0 ) -> int:
    nesting_calls = (ast.For , ast.If,ast.While,ast.Try,ast.With,ast.Match)
    max_depth = curr_depth

    for calls in ast.iter_child_nodes(node):
        if isinstance(calls,nesting_calls):
            calls_depth = check_nesting(calls,curr_depth+1)
        else:
            calls_depth = check_nesting(calls,curr_depth)
    
        max_depth = max(max_depth,calls_depth)
        
    return max_depth

def check_styling(code:str) -> List[Issues]:
    issue : List[Issues] = []
    for i , line in enumerate(code.splitlines() , start=1):
        if len(line) > MAx_Line_LENGTH:
            issue.append(
                Issues(
                    type="style",
                    severity=Severity.low,
                    line=i,
                    message=f"Line too long ({len(line)} characters).",
                    suggestion=f"Keep line length under {MAx_Line_LENGTH} characters for readability."
                )
            )


    try:
        tree = ast.parse(code)
    except SyntaxError:
        return issue
    
    visitor = Style_Checker()
    visitor.visit(tree)
    issue.extend(visitor.issues)

    max_depth = check_nesting(tree)
    if max_depth > MAX_NESTING:
        issue.append(Issues(
            type = "complexity",
            severity=Severity.medium,
            line=1,
            message=f"Code nesting is too deep (depth={max_depth}).",
            suggestion="Refactor nested logic into smaller helper functions or early returns."
        ))

    return issue