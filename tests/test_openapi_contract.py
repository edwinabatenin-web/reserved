"""Dependency-free structural checks for the internal OpenAPI inventory.

The document is implementation-derived and must not become a capability wish
list. These checks prove that every documented operation maps to an existing
Flask decorator and that local component references resolve; they do not claim
runtime response conformance or public API stability.
"""

import ast
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC_PATH = ROOT / "docs" / "openapi.json"
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
SOURCE_PREFIXES = {
    ROOT / "reserved" / "api" / "routes.py": "/api",
    ROOT / "reserved" / "web" / "routes.py": "",
    ROOT / "reserved" / "web" / "v2.py": "/v2",
}


def _source_operations():
    operations = set()
    for source_path, prefix in SOURCE_PREFIXES.items():
        tree = ast.parse(source_path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                    continue
                method = decorator.func.attr.lower()
                if method not in HTTP_METHODS | {"route"} or not decorator.args:
                    continue
                route_arg = decorator.args[0]
                if not isinstance(route_arg, ast.Constant) or not isinstance(route_arg.value, str):
                    continue
                methods = {method}
                if method == "route":
                    methods = {"get"}
                    for keyword in decorator.keywords:
                        if keyword.arg == "methods" and isinstance(keyword.value, (ast.List, ast.Tuple)):
                            methods = {
                                item.value.lower()
                                for item in keyword.value.elts
                                if isinstance(item, ast.Constant) and isinstance(item.value, str)
                            }
                path = prefix + route_arg.value
                path = path.replace("<int:scenario_id>", "{scenario_id}")
                operations.update((path, item) for item in methods & HTTP_METHODS)
    return operations


def _documented_operations(spec):
    return {
        (path, method)
        for path, path_item in spec["paths"].items()
        for method in path_item
        if method in HTTP_METHODS
    }


def test_openapi_inventory_is_explicitly_internal_preview():
    spec = json.loads(SPEC_PATH.read_text())
    assert spec["openapi"] == "3.0.3"
    assert spec["x-reserved-contract-status"] == "internal-preview-non-production"
    assert spec["x-reserved-stability"] == "unstable"
    assert "does not create capabilities" in spec["x-reserved-source-of-truth"]
    exclusions = " ".join(spec["x-reserved-exclusions"])
    assert "No public or partner API" in exclusions
    assert "No complete annual tax-position API" in exclusions


def test_every_documented_operation_exists_in_flask_source():
    spec = json.loads(SPEC_PATH.read_text())
    missing = _documented_operations(spec) - _source_operations()
    assert not missing, f"OpenAPI operations without matching Flask routes: {sorted(missing)}"


def test_local_component_references_resolve():
    spec = json.loads(SPEC_PATH.read_text())

    def walk(value):
        if isinstance(value, dict):
            ref = value.get("$ref")
            if ref is not None:
                assert ref.startswith("#/"), f"External OpenAPI reference is not permitted: {ref}"
                target = spec
                for segment in ref[2:].split("/"):
                    target = target[segment.replace("~1", "/").replace("~0", "~")]
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(spec)
