"""HTTP endpoint mocking utilities using aioresponses."""

from __future__ import annotations

import functools
import json
from dataclasses import dataclass
from inspect import iscoroutinefunction
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    Self,
    TypedDict,
    Unpack,
    overload,
)

from aioresponses import aioresponses

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from types import TracebackType

    from yarl import URL

type JsonValue = (
    str | int | float | bool | None | dict[str, JsonValue] | list[JsonValue]
)


class _AioresponsesCallbackKwargs(TypedDict, total=False):
    """Subset of kwargs aioresponses forwards to our callback."""

    headers: dict[str, str]
    params: dict[str, str]
    data: Any
    json: dict[str, JsonValue]


@dataclass(frozen=True)
class MockedAiohttpRequest:
    """Single request-object passed to MockAiohttpEndpoint.assert_request.

    Wraps the (url, **kwargs) pair that aioresponses hands to its callback
    into one object, so assert_request takes the same single-argument shape
    as MockHttpxEndpoint.assert_request.
    """

    url: URL
    headers: dict[str, str] | None = None
    params: dict[str, str] | None = None
    data: Any = None
    json: dict[str, JsonValue] | None = None


@dataclass(frozen=True)
class MockAiohttpEndpoint:
    """Define an HTTP endpoint mock specification."""

    url: str
    method: Literal["GET", "POST", "PUT", "DELETE"]
    json_response: dict[str, JsonValue] | None = None
    body: str | None = None
    assert_request: Callable[[MockedAiohttpRequest], None] | None = None


class _WithAiohttpEndpoints:
    """Decorator and context manager that mocks HTTP endpoints."""

    __slots__ = ("_endpoints", "_mock_ctx")

    def __init__(self, endpoints: tuple[MockAiohttpEndpoint, ...]) -> None:
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
        assertion_fn: Callable[[MockedAiohttpRequest], None],
    ) -> Callable[..., None]:
        def callback(
            url: URL,
            **kwargs: Unpack[_AioresponsesCallbackKwargs],
        ) -> None:
            assertion_fn(
                MockedAiohttpRequest(
                    url=url,
                    headers=kwargs.get("headers"),
                    params=kwargs.get("params"),
                    data=kwargs.get("data"),
                    json=kwargs.get("json"),
                ),
            )

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


def with_aiohttp_endpoints(
    endpoints: tuple[MockAiohttpEndpoint, ...],
) -> _WithAiohttpEndpoints:
    """Mock HTTP endpoints for the duration of a test."""
    return _WithAiohttpEndpoints(endpoints)
