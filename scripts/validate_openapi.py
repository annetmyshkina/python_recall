"""Validate the design-first OpenAPI contract for implemented releases."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml
from fastapi.openapi.models import OpenAPI
from yaml.resolver import BaseResolver

ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = ROOT / "docs" / "openapi.yaml"
API_DOC_PATH = ROOT / "docs" / "api.md"

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
EXPECTED_OPERATIONS = {
    ("/categories", "get"),
    ("/categories", "post"),
    ("/categories/{category_id}", "get"),
    ("/categories/{category_id}", "patch"),
    ("/categories/{category_id}", "delete"),
    ("/topics", "get"),
    ("/topics", "post"),
    ("/topics/{topic_id}", "get"),
    ("/topics/{topic_id}", "patch"),
    ("/topics/{topic_id}", "delete"),
    ("/tags", "get"),
    ("/tags", "post"),
    ("/tags/{tag_id}", "get"),
    ("/tags/{tag_id}", "patch"),
    ("/tags/{tag_id}", "delete"),
    ("/cards", "get"),
    ("/cards", "post"),
    ("/cards/{card_id}", "get"),
    ("/cards/{card_id}", "patch"),
    ("/cards/{card_id}", "delete"),
    ("/reviews/due", "get"),
    ("/reviews/session", "post"),
    ("/reviews/{card_id}/reference", "get"),
    ("/reviews/{card_id}/attempts", "post"),
    ("/reviews/{card_id}/complete", "post"),
    ("/reviews/history", "get"),
    ("/statistics/overview", "get"),
    ("/statistics/topics", "get"),
    ("/statistics/activity", "get"),
    ("/adaptive/topics", "get"),
    ("/ai/providers", "get"),
    ("/ai/usage", "get"),
    ("/ai/evaluate-answer", "post"),
    ("/ai/answer-evaluations", "get"),
    ("/ai/answer-evaluations/{evaluation_id}", "get"),
    ("/ai/analyze-card", "post"),
    ("/ai/card-analyses", "get"),
    ("/ai/card-analyses/{analysis_id}", "get"),
    ("/ai/generate-cards", "post"),
    ("/ai/card-suggestions", "get"),
    ("/ai/card-suggestions/{suggestion_id}", "get"),
    ("/ai/card-suggestions/{suggestion_id}/accept", "post"),
    ("/ai/card-suggestions/{suggestion_id}/reject", "post"),
    ("/health", "get"),
    ("/health/database", "get"),
    ("/health/ai", "get"),
}
INPUT_SCHEMAS = {
    "CategoryCreate",
    "CategoryPatch",
    "TopicCreate",
    "TopicPatch",
    "TagCreate",
    "TagPatch",
    "CardCreate",
    "CardPatch",
    "DueSessionRequest",
    "TopicSessionRequest",
    "DifficultSessionRequest",
    "ManualSessionRequest",
    "AnswerAttemptCreate",
    "AnswerEvaluationCreate",
    "CardAnalysisCreate",
    "CardGenerationCreate",
    "ReviewComplete",
}
PATH_PARAMETER_PATTERN = re.compile(r"\{([^{}]+)\}")


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def construct_unique_mapping(
    loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    """Build a mapping while treating duplicate keys as an error."""
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate YAML key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping
)


def load_yaml(source: str) -> dict[str, Any]:
    """Load an OpenAPI YAML document without allowing duplicate keys."""
    document = yaml.load(source, Loader=UniqueKeyLoader)
    assert isinstance(document, dict), "OpenAPI root must be an object"
    return document


def walk(value: Any) -> Iterator[Any]:
    """Yield every nested mapping and sequence value."""
    yield value
    if isinstance(value, dict):
        for nested in value.values():
            yield from walk(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from walk(nested)


def resolve_local_ref(document: dict[str, Any], reference: str) -> Any:
    """Resolve a local JSON Pointer and fail on an external reference."""
    assert reference.startswith("#/"), f"external reference is not allowed: {reference}"
    current: Any = document
    for raw_part in reference[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        assert isinstance(current, dict) and part in current, (
            f"unresolved reference: {reference}"
        )
        current = current[part]
    return current


def iter_operations(
    document: dict[str, Any],
) -> Iterator[tuple[str, str, dict[str, Any]]]:
    """Yield path, method, and operation objects."""
    for path, path_item in document["paths"].items():
        for method, operation in path_item.items():
            if method in HTTP_METHODS:
                yield path, method, operation


def operation_parameters(
    document: dict[str, Any], path: str, method: str
) -> set[tuple[str, str, bool]]:
    """Return the externally relevant parameter signature of one operation."""
    path_item = document["paths"][path]
    parameters = path_item.get("parameters", []) + path_item[method].get(
        "parameters", []
    )
    resolved = [
        resolve_local_ref(document, parameter["$ref"])
        if "$ref" in parameter
        else parameter
        for parameter in parameters
    ]
    return {
        (parameter["name"], parameter["in"], parameter.get("required") is True)
        for parameter in resolved
    }


def validate_runtime_contract(document: dict[str, Any]) -> None:
    """Ensure FastAPI registers the design-first operation inventory."""
    from backend.app.core.config import Settings
    from backend.app.main import create_app

    application = create_app(Settings(_env_file=None))
    try:
        runtime = application.openapi()
    finally:
        application.state.database.dispose()

    prefix = document["servers"][0]["url"]
    expected = {
        (path, method): operation["operationId"]
        for path, method, operation in iter_operations(document)
    }
    actual: dict[tuple[str, str], str] = {}
    runtime_paths: dict[tuple[str, str], str] = {}
    for path, method, operation in iter_operations(runtime):
        assert path.startswith(prefix), f"runtime path is outside {prefix}: {path}"
        contract_path = path.removeprefix(prefix)
        actual[(contract_path, method)] = operation["operationId"]
        runtime_paths[(contract_path, method)] = path

    assert actual == expected, "runtime operation inventory differs from OpenAPI"
    for (path, method), _ in expected.items():
        runtime_path = runtime_paths[(path, method)]
        assert operation_parameters(document, path, method) == operation_parameters(
            runtime, runtime_path, method
        ), f"runtime parameter mismatch: {method} {path}"
        expected_body = document["paths"][path][method].get("requestBody")
        runtime_body = runtime["paths"][runtime_path][method].get("requestBody")
        assert bool(expected_body) == bool(runtime_body), (
            f"runtime request body mismatch: {method} {path}"
        )
        expected_success = {
            code
            for code in document["paths"][path][method]["responses"]
            if code.startswith("2")
        }
        runtime_success = {
            code
            for code in runtime["paths"][runtime_path][method]["responses"]
            if code.startswith("2")
        }
        assert runtime_success <= expected_success, (
            f"runtime success response mismatch: {method} {path}"
        )


def validate() -> tuple[int, int, int]:
    """Validate syntax, OpenAPI structure, and project-specific invariants."""
    document = load_yaml(OPENAPI_PATH.read_text(encoding="utf-8"))

    OpenAPI.model_validate(document)
    assert document["openapi"] == "3.1.0"
    assert document["servers"] == [{"url": "/api/v1", "description": "Local API v1"}]

    for value in walk(document):
        if isinstance(value, dict) and "$ref" in value:
            resolve_local_ref(document, value["$ref"])

    for path, path_item in document["paths"].items():
        expected_path_parameters = set(PATH_PARAMETER_PATTERN.findall(path))
        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue
            parameters = [
                resolve_local_ref(document, parameter["$ref"])
                if "$ref" in parameter
                else parameter
                for parameter in (
                    path_item.get("parameters", []) + operation.get("parameters", [])
                )
            ]
            actual_path_parameters = {
                parameter["name"]
                for parameter in parameters
                if parameter.get("in") == "path"
            }
            assert actual_path_parameters == expected_path_parameters, (
                f"path parameter mismatch: {method} {path}"
            )
            assert all(
                parameter.get("required") is True
                for parameter in parameters
                if parameter.get("in") == "path"
            ), f"path parameters must be required: {method} {path}"

    operations = list(iter_operations(document))
    actual_inventory = {(path, method) for path, method, _ in operations}
    missing_operations = EXPECTED_OPERATIONS - actual_inventory
    unexpected_operations = actual_inventory - EXPECTED_OPERATIONS
    assert actual_inventory == EXPECTED_OPERATIONS, (
        f"operation inventory mismatch: expected={missing_operations}, "
        f"unexpected={unexpected_operations}"
    )

    operation_ids = [operation.get("operationId") for _, _, operation in operations]
    assert all(operation_ids), "every operation must define operationId"
    assert len(operation_ids) == len(set(operation_ids)), (
        "operationId values must be unique"
    )

    for path in document["paths"]:
        assert path != "/statistics/weak-areas"

    idempotency_users = []
    for path, method, operation in operations:
        for parameter in operation.get("parameters", []):
            if parameter.get("$ref") == "#/components/parameters/IdempotencyKey":
                idempotency_users.append((path, method))
    assert set(idempotency_users) == {
        ("/reviews/{card_id}/complete", "post"),
        ("/ai/evaluate-answer", "post"),
        ("/ai/analyze-card", "post"),
        ("/ai/generate-cards", "post"),
    }

    schemas = document["components"]["schemas"]
    for name in INPUT_SCHEMAS:
        assert schemas[name].get("additionalProperties") is False, (
            f"input schema must reject unknown fields: {name}"
        )

    problem_responses = {
        "BadRequest",
        "PayloadTooLarge",
        "NotFound",
        "Conflict",
        "ValidationError",
        "InternalError",
        "DatabaseUnavailable",
        "AiUnavailable",
        "AiInvalidResponse",
        "AiTimeout",
    }
    for name in problem_responses:
        content = document["components"]["responses"][name]["content"]
        assert set(content) == {"application/problem+json"}

    for path, method, operation in operations:
        if path in {"/health", "/ai/providers"}:
            continue
        responses = operation["responses"]
        assert "503" in responses, f"503 response is missing: {method} {path}"
        if "422" in responses:
            assert "400" in responses, f"400 response is missing: {method} {path}"
        if "requestBody" in operation:
            assert responses.get("413") == {
                "$ref": "#/components/responses/PayloadTooLarge"
            }, f"413 response is missing: {method} {path}"

    api_documentation = API_DOC_PATH.read_text(encoding="utf-8")
    for path, _ in EXPECTED_OPERATIONS:
        assert path in api_documentation, f"path is missing from api.md: {path}"

    validate_runtime_contract(document)

    return (
        len(operations),
        len(schemas),
        sum(
            1 for value in walk(document) if isinstance(value, dict) and "$ref" in value
        ),
    )


if __name__ == "__main__":
    operation_count, schema_count, reference_count = validate()
    print(
        "OpenAPI contract is valid: "
        f"{operation_count} operations, {schema_count} schemas, "
        f"{reference_count} references checked."
    )
