import pytest

from scripts.validate_openapi import (
    EXPECTED_OPERATIONS,
    load_yaml,
    resolve_local_ref,
    validate,
)


def test_release_1_openapi_contract_is_valid() -> None:
    operation_count, schema_count, reference_count = validate()

    assert operation_count == len(EXPECTED_OPERATIONS)
    assert schema_count > 0
    assert reference_count > 0


def test_openapi_validator_rejects_an_unresolved_reference() -> None:
    document = {"components": {"schemas": {}}}

    with pytest.raises(AssertionError, match="unresolved reference"):
        resolve_local_ref(document, "#/components/schemas/Missing")


def test_openapi_validator_rejects_external_references() -> None:
    with pytest.raises(AssertionError, match="external reference"):
        resolve_local_ref({}, "https://example.com/schema.yaml")


def test_openapi_validator_rejects_duplicate_yaml_keys() -> None:
    with pytest.raises(ValueError, match="duplicate YAML key"):
        load_yaml("openapi: 3.1.0\nopenapi: 3.0.3\n")
