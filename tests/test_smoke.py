"""Smoke test executed against the built wheel/sdist in an isolated environment."""

import pymocks

PUBLIC_API = ["JsonValue", "Mock", "MockEndpoint", "with_endpoints", "with_mock"]

# Every name listed in __all__ must be importable.
for name in PUBLIC_API:
    obj = getattr(pymocks, name, None)
    assert obj is not None, f"pymocks.{name} should be importable"

# Decorators should be callable.
assert callable(pymocks.with_mock), "with_mock should be callable"
assert callable(pymocks.with_endpoints), "with_endpoints should be callable"

# Mock and MockEndpoint should be dataclasses.
assert hasattr(pymocks.Mock, "__dataclass_fields__"), "Mock should be a dataclass"
assert hasattr(
    pymocks.MockEndpoint,
    "__dataclass_fields__",
), "MockEndpoint should be a dataclass"

print("smoke test passed")  # noqa: T201
