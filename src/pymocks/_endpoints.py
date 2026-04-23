"""HTTP endpoint mocking utilities using aioresponses."""

from __future__ import annotations

import functools
import json
from dataclasses import dataclass
from inspect import iscoroutinefunction
from typing import TYPE_CHECKING, Any, Literal, Self, Unpack, overload

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from types import TracebackType

    from yarl import URL

from aioresponses import aioresponses
from typing_extensions import TypedDict

type JsonValue = (
    str | int | float | bool | None | dict[str, JsonValue] | list[JsonValue]
)


class RequestData(TypedDict, total=False):
    """Typed representation of the request data passed to assert_request."""

    headers: dict[str, str]
    params: dict[str, str]
    data: Any
    json: dict[str, JsonValue]


@dataclass(frozen=True)
class MockEndpoint:
    """Define an HTTP endpoint mock specification."""

    url: str
    method: Literal["GET", "POST", "PUT", "DELETE"]
    json_response: dict[str, JsonValue] | None = None
    body: str | None = None
    assert_request: Callable[[URL, RequestData], None] | None = None


class _WithEndpoints:
    """Decorator and context manager that mocks HTTP endpoints."""

    __slots__ = ("_endpoints", "_mock_ctx")

    def __init__(self, endpoints: tuple[MockEndpoint, ...]) -> None:
        self._endpoints = endpoints
        self._mock_ctx: aioresponses | None = None

    def __enter__(self) -> Self:
        ctx = aioresponses()
        mock = ctx.__enter__()
        self._setup_mocks(mock)
        self._mock_ctx = ctx
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._mock_ctx is not None:
            self._mock_ctx.__exit__(exc_type, exc_val, exc_tb)
            self._mock_ctx = None

    async def __aenter__(self) -> Self:
        return self.__enter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.__exit__(exc_type, exc_val, exc_tb)

    @staticmethod
    def _make_callback(
        assertion_fn: Callable[[URL, RequestData], None],
    ) -> Callable[..., None]:
        def callback(url: URL, **kwargs: Unpack[RequestData]) -> None:
            assertion_fn(url, RequestData(**kwargs))

        return callback

    def _setup_mocks(self, mock: aioresponses) -> None:
        """Register all endpoints on the mock context."""
        for endpoint in self._endpoints:
            response_body = (
                endpoint.body
                if endpoint.body is not None
                else json.dumps(endpoint.json_response)
            )
            mock.add(  # pyright: ignore[reportUnknownMemberType]
                endpoint.url,
                endpoint.method,
                body=response_body,
                callback=(
                    self._make_callback(endpoint.assert_request)
                    if endpoint.assert_request is not None
                    else None
                ),
            )

    @overload
    def __call__[**P, T](
        self,
        func: Callable[P, Awaitable[T]],
    ) -> Callable[P, Awaitable[T]]: ...

    @overload
    def __call__[**P](
        self,
        func: Callable[P, None],
    ) -> Callable[P, None]: ...

    def __call__[**P, T](
        self,
        func: Callable[P, T],
    ) -> Callable[P, T]:
        """Apply endpoint mocks around the decorated function."""
        if iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(
                *args: P.args,
                **kwargs: P.kwargs,
            ) -> T:
                with aioresponses() as mock:
                    self._setup_mocks(mock)
                    return await func(*args, **kwargs)  # pyright: ignore[reportGeneralTypeIssues]

            return async_wrapper  # pyright: ignore[reportReturnType]

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            with aioresponses() as mock:
                self._setup_mocks(mock)
                return func(*args, **kwargs)

        return sync_wrapper


def with_endpoints(
    endpoints: tuple[MockEndpoint, ...],
) -> _WithEndpoints:
    """Mock HTTP endpoints for the duration of a test."""
    return _WithEndpoints(endpoints)
