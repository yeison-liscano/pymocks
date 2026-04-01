# pymocks

Testing utility decorators and context managers for mocking functions, variables, and HTTP endpoints in Python.

Works with both synchronous and asynchronous test functions. Sync/async is detected automatically. All mocking utilities can be used as decorators or context managers.

## Installation

```bash
pip install pymocks
```

Or with uv:

```bash
uv add pymocks
```

## Usage

### Mocking Functions and Variables

Use `Mock` with `with_mock` to monkeypatch module attributes for the duration of a test. Accepts one or more `Mock` objects. Works as a decorator or context manager:

```python
import my_module
from pymocks import Mock, with_mock


# Mock a function — the replacement must have the same signature
def fake_function(x: int, y: str) -> bool:
    return True


mock = Mock(
    module_where_used=my_module,
    current_value=my_module.some_function,
    new_value=fake_function,
)


@with_mock(mock)
def test_with_mocked_function():
    result = my_module.some_function(1, "a")
    assert result is True


# Mock a variable — the replacement must have the same type
var_mock = Mock(
    module_where_used=my_module,
    current_value=my_module.API_URL,
    new_value="https://mock.example.com",
)


@with_mock(var_mock)
def test_with_mocked_variable():
    assert my_module.API_URL == "https://mock.example.com"
```

Pass multiple mocks to apply them all at once — they are all reverted together when the scope exits:

```python
@with_mock(mock, var_mock)
def test_with_multiple_mocks():
    result = my_module.some_function(1, "a")
    assert result is True
    assert my_module.API_URL == "https://mock.example.com"
```

The same works for async tests:

```python
@with_mock(mock)
async def test_async_with_mock():
    result = my_module.some_function(1, "a")
    assert result is True
```

Or use it as a context manager for more flexible scoping:

```python
def test_with_context_manager():
    with with_mock(mock, var_mock):
        result = my_module.some_function(1, "a")
        assert result is True
    # mocks are reverted here


async def test_async_with_context_manager():
    async with with_mock(mock):
        result = my_module.some_function(1, "a")
        assert result is True
```

### Mocking Classes

Use `Mock` to replace a class with a subclass. The replacement must be a subclass of the original:

```python
import my_module
from pymocks import Mock, with_mock


class FakeService(my_module.Service):
    def fetch(self) -> str:
        return "fake data"


mock = Mock(
    module_where_used=my_module,
    current_value=my_module.Service,
    new_value=FakeService,
)


@with_mock(mock)
def test_with_mocked_class():
    svc = my_module.Service()
    assert svc.fetch() == "fake data"
```

Replacing a class with an unrelated class raises `TypeError`:

```python
class Unrelated:
    pass


# Raises TypeError — Unrelated is not a subclass of Service
Mock(
    module_where_used=my_module,
    current_value=my_module.Service,
    new_value=Unrelated,
)
```

### Signature and Type Validation

`Mock` validates compatibility between `current_value` and `new_value` at construction time:

- **Callables**: signatures must match exactly (parameter count, names, kinds, annotations, and return annotation)
- **Classes**: `new_value` must be a subclass of `current_value`
- **Non-callables**: `type(current_value)` must be the same as `type(new_value)`
- **Mixed**: replacing a callable with a non-callable (or vice versa) raises `TypeError`

```python
def original(x: int) -> str:
    return str(x)


# Signature mismatch — raises TypeError immediately
Mock(
    module_where_used=my_module,
    current_value=original,
    new_value=lambda x: str(x),  # missing annotations
)

# Type mismatch — raises TypeError immediately
Mock(
    module_where_used=my_module,
    current_value="a string",
    new_value=42,
)
```

### Mocking HTTP Endpoints

Use `MockEndpoint` with `with_endpoints` to mock HTTP calls via `aioresponses`. Works as a decorator or context manager:

```python
import aiohttp
from pymocks import MockEndpoint, with_endpoints

endpoints = (
    MockEndpoint(
        url="https://api.example.com/users",
        method="GET",
        json_response={"users": [{"id": 1, "name": "Alice"}]},
    ),
    MockEndpoint(
        url="https://api.example.com/users",
        method="POST",
        json_response={"id": 2, "name": "Bob"},
    ),
)


# As a decorator
@with_endpoints(endpoints)
async def test_api_calls():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com/users") as resp:
            data = await resp.json()
            assert len(data["users"]) == 1


# As a context manager
async def test_api_calls_ctx():
    async with with_endpoints(endpoints):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.example.com/users") as resp:
                data = await resp.json()
                assert len(data["users"]) == 1
```

## API Reference

### `Mock[T_mocked]`

A dataclass that defines a monkeypatch specification. Validates compatibility on construction.

| Field              | Type         | Description                                 |
|--------------------|--------------|---------------------------------------------|
| `module_where_used`| `ModuleType` | The module containing the attribute to patch |
| `current_value`    | `T_mocked`   | The current value (used to find its name)    |
| `new_value`        | `T_mocked`   | The replacement value during the test        |

### `MockEndpoint`

A frozen dataclass defining an HTTP endpoint mock.

| Field           | Type                                      | Description                   |
|-----------------|-------------------------------------------|-------------------------------|
| `url`           | `str`                                     | The URL to mock               |
| `method`        | `Literal["GET", "POST", "PUT", "DELETE"]` | HTTP method                   |
| `json_response` | `dict[str, JsonValue] \| None`            | JSON response body (optional) |
| `body`          | `str \| None`                             | Raw string body (optional)    |

### `with_mock(*mocks)` / `with_endpoints(endpoints)`

Both can be used as **decorators** or **context managers** (sync and async):

```python
# Decorator — single mock
@with_mock(mock)
def test_decorated(): ...

# Decorator — multiple mocks
@with_mock(mock, var_mock)
def test_decorated(): ...

# Sync context manager
with with_mock(mock, var_mock):
    ...

# Async context manager
async with with_mock(mock):
    ...
```

When used as decorators, sync/async is detected automatically.

## Requirements

- Python >= 3.12
- pytest
- aioresponses

## License

MIT
