"""The OpenAPI schema: the committed openapi.json is current, and every error is a Problem with a known code."""

import json
from pathlib import Path

from apply.cli import openapi_schema
from apply.errors import ErrorCode

COMMITTED = Path(__file__).parents[2] / "openapi.json"


def test_the_committed_schema_is_current():
    current = openapi_schema()
    assert COMMITTED.exists(), "Run: uv run apply openapi --out openapi.json"
    assert json.loads(COMMITTED.read_text(encoding="utf-8")) == current, (
        "The API changed: run `uv run apply openapi --out openapi.json` (the web app's client is made from it)"
    )


def test_every_error_is_a_problem_with_a_code_from_the_enum():
    schema = openapi_schema()
    problem = schema["components"]["schemas"]["Problem"]
    assert problem["properties"]["code"]["$ref"].endswith("/ErrorCode")
    assert set(schema["components"]["schemas"]["ErrorCode"]["enum"]) == {c.value for c in ErrorCode}
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            responses = operation["responses"]
            assert "422" not in responses, f"{method} {path} still has FastAPI's own 422"
            for status in ("4XX", "5XX"):
                assert responses[status]["content"] == {
                    "application/problem+json": {"schema": {"$ref": "#/components/schemas/Problem"}}
                }
    assert "HTTPValidationError" not in schema["components"]["schemas"]
