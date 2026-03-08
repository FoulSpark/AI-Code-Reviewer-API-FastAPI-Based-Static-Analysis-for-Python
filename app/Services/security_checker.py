import ast
from typing import List
from app.Schema.review import Issues, Severity


class Security_Checker(ast.NodeVisitor):
    def __init__(self):
        self.issues: List[Issues] = []

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "eval":
            self.issues.append(
                Issues(
                    type="security",
                    severity=Severity.high,
                    line=node.lineno,
                    message="Use of eval() detected.",
                    suggestion="Avoid eval(). Use safer parsing or explicit logic."
                )
            )

        if isinstance(node.func, ast.Name) and node.func.id == "exec":
            self.issues.append(
                Issues(
                    type="security",
                    severity=Severity.high,
                    line=node.lineno,
                    message="Use of exec() detected.",
                    suggestion="Avoid exec(). Use safer explicit logic."
                )
            )

        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "os"
            and node.func.attr == "system"
        ):
            self.issues.append(
                Issues(
                    type="security",
                    severity=Severity.high,
                    line=node.lineno,
                    message="Use of os.system() detected.",
                    suggestion="Prefer subprocess.run() with validated arguments."
                )
            )

        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
        ):
            for keyword in node.keywords:
                if (
                    keyword.arg == "shell"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                ):
                    self.issues.append(
                        Issues(
                            type="security",
                            severity=Severity.high,
                            line=node.lineno,
                            message="subprocess call with shell=True detected.",
                            suggestion="Avoid shell=True. Pass arguments as a list."
                        )
                    )

        self.generic_visit(node)


def security_check(code: str) -> List[Issues]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    checker = Security_Checker()
    checker.visit(tree)
    return checker.issues