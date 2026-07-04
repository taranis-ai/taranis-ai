import ast
from pathlib import Path


REQUEST_METHOD_NAMES = {
    "api_delete",
    "api_get",
    "api_patch",
    "api_post",
    "api_put",
    "delete_object",
    "get_first",
    "get_object",
    "get_objects",
    "get_objects_by_endpoint",
    "store_object",
    "update_object",
}

TARGET_PATHS = (
    Path("frontend/auth.py"),
    Path("frontend/views"),
)


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for target in TARGET_PATHS:
        if target.is_file():
            files.append(target)
            continue
        files.extend(sorted(path for path in target.rglob("*.py") if path.is_file()))
    return files


def _contains_request_call(try_node: ast.Try) -> bool:
    for node in try_node.body:
        for nested in ast.walk(node):
            if not isinstance(nested, ast.Call):
                continue
            if isinstance(nested.func, ast.Name) and nested.func.id in {"CoreApi", "DataPersistenceLayer"}:
                return True
            if isinstance(nested.func, ast.Attribute) and nested.func.attr in REQUEST_METHOD_NAMES:
                return True
    return False


def _is_http_exception_type(handler_type: ast.expr | None) -> bool:
    if handler_type is None:
        return False
    if isinstance(handler_type, ast.Name):
        return handler_type.id == "HTTPException"
    if isinstance(handler_type, ast.Attribute):
        return handler_type.attr == "HTTPException"
    if isinstance(handler_type, ast.Tuple):
        return any(_is_http_exception_type(element) for element in handler_type.elts)
    return False


def _is_broad_exception_type(handler_type: ast.expr | None) -> bool:
    if handler_type is None:
        return True
    if isinstance(handler_type, ast.Name):
        return handler_type.id == "Exception"
    if isinstance(handler_type, ast.Attribute):
        return handler_type.attr == "Exception"
    if isinstance(handler_type, ast.Tuple):
        return any(_is_broad_exception_type(element) for element in handler_type.elts)
    return False


def test_request_try_blocks_preserve_http_exceptions():
    violations: list[str] = []

    for path in _iter_python_files():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try) or not _contains_request_call(node):
                continue

            saw_http_exception_handler = False
            for handler in node.handlers:
                if _is_http_exception_type(handler.type):
                    saw_http_exception_handler = True
                    continue
                if _is_broad_exception_type(handler.type) and not saw_http_exception_handler:
                    violations.append(
                        f"{path}:{handler.lineno} catches Exception for a request-making try block without first re-raising HTTPException"
                    )
                    break

    assert not violations, "\n".join(violations)
