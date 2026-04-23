"""Smoke test executed against the built wheel/sdist in an isolated environment."""

import pymocks

PUBLIC_API = [
    "JsonValue",
    "Mock",
    "MockAiohttpEndpoint",
    "MockHttpxEndpoint",
    "MockedAiohttpRequest",
    "with_aiohttp_endpoints",
    "with_httpx_endpoints",
    "with_mock",
]

# Every name listed in __all__ must be importable.
for name in PUBLIC_API:
    obj = getattr(pymocks, name, None)
    assert obj is not None, f"pymocks.{name} should be importable"

# Decorators should be callable.
assert callable(pymocks.with_mock), "with_mock should be callable"
assert callable(
    pymocks.with_aiohttp_endpoints,
), "with_aiohttp_endpoints should be callable"
assert callable(
    pymocks.with_httpx_endpoints,
), "with_httpx_endpoints should be callable"

# Mock and endpoint specs should be dataclasses.
assert hasattr(pymocks.Mock, "__dataclass_fields__"), "Mock should be a dataclass"
assert hasattr(
    pymocks.MockAiohttpEndpoint,
    "__dataclass_fields__",
), "MockAiohttpEndpoint should be a dataclass"
assert hasattr(
    pymocks.MockHttpxEndpoint,
    "__dataclass_fields__",
), "MockHttpxEndpoint should be a dataclass"

print("smoke test passed")  # noqa: T201
