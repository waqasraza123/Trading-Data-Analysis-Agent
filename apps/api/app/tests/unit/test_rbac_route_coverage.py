import ast
from dataclasses import dataclass
from pathlib import Path

MUTATING_METHODS = {"DELETE", "PATCH", "POST", "PUT"}
ROUTE_METHODS = {method.lower() for method in MUTATING_METHODS}
ROUTES_ROOT = Path(__file__).resolve().parents[2] / "modules"

MUTATING_ROUTE_EXEMPTIONS: dict[tuple[str, str], str] = {
    ("POST", "/chart-screenshot-runs/image/preview"): "write-free image extraction preview",
    ("POST", "/data-contracts/validate"): "payload validation only",
    ("POST", "/data-contracts/validate-source"): "source payload validation only",
    ("POST", "/safety-policies/evaluate-action"): "policy evaluation only",
    ("POST", "/safety-policies/evaluate-payload"): "policy evaluation only",
    ("POST", "/safety-policies/evaluate-text"): "policy evaluation only",
    ("POST", "/state-machines/validate-transition"): "transition validation only",
}


def test_mutating_routes_declare_permission_or_exemption() -> None:
    missing_guards: list[str] = []
    seen_exemptions: set[tuple[str, str]] = set()

    for route_file in sorted(ROUTES_ROOT.rglob("routes.py")):
        for route in _mutating_routes(route_file):
            route_key = (route.method, route.path)
            if route_key in MUTATING_ROUTE_EXEMPTIONS:
                seen_exemptions.add(route_key)
                continue
            if route.has_permission_guard:
                continue
            missing_guards.append(
                f"{route.method} {route.path} -> {route_file}:{route.function_name}"
            )

    assert missing_guards == []
    assert set(MUTATING_ROUTE_EXEMPTIONS) == seen_exemptions


@dataclass(frozen=True)
class RouteCoverage:
    method: str
    path: str
    function_name: str
    has_permission_guard: bool


def _mutating_routes(route_file: Path) -> list[RouteCoverage]:
    tree = ast.parse(route_file.read_text())
    prefix = _router_prefix(tree)
    routes: list[RouteCoverage] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not _is_route_decorator(decorator):
                continue
            method = decorator.func.attr.upper()
            path = _route_path(prefix, decorator)
            routes.append(
                RouteCoverage(
                    method=method,
                    path=path,
                    function_name=node.name,
                    has_permission_guard=_has_permission_guard(decorator),
                )
            )
    return routes


def _router_prefix(tree: ast.Module) -> str:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "router" for target in node.targets
        ):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        for keyword in node.value.keywords:
            if keyword.arg == "prefix" and isinstance(keyword.value, ast.Constant):
                return str(keyword.value.value)
    return ""


def _is_route_decorator(decorator: ast.AST) -> bool:
    return (
        isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and decorator.func.attr in ROUTE_METHODS
    )


def _route_path(prefix: str, decorator: ast.Call) -> str:
    path = ""
    if decorator.args and isinstance(decorator.args[0], ast.Constant):
        path = str(decorator.args[0].value)
    if not prefix:
        return path or "/"
    return f"{prefix}{path}"


def _has_permission_guard(decorator: ast.Call) -> bool:
    dependencies = next(
        (keyword.value for keyword in decorator.keywords if keyword.arg == "dependencies"),
        None,
    )
    if dependencies is None:
        return False
    return _contains_name(dependencies, {"require_admin", "require_permission"})


def _contains_name(node: ast.AST, names: set[str]) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id in names:
            return True
        if isinstance(child, ast.Attribute) and child.attr in names:
            return True
    return False
