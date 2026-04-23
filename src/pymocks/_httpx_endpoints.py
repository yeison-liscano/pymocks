"""HTTP endpoint mocking utilities for httpx via pytest-httpx.

Reuses pytest_httpx's HTTPXMock matching engine but drives it as a decorator
and context manager rather than a pytest fixture, so it composes with the
existing with_aiohttp_endpoints style. The transport monkeypatch mirrors what
pytest_httpx.httpx_mock installs via pytest's monkeypatch fixture.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from inspect import iscoroutinefunction
from typing import (
    TYPE_CHECKING,
    Literal,
    Self,
    overload,
)

import httpx
from pytest_httpx import HTTPXMock
from pytest_httpx._options import (
    _HTTPXMockOptions,  # pyright: ignore[reportPrivateUsage]
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from types import TracebackType

    from pymocks._endpoints import JsonValue


HttpxMethod = Literal[
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
    "HEAD",
    "OPTIONS",
]


@dataclass(frozen=True)
class MockHttpxEndpoint:
    """Define an httpx endpoint mock specification."""

    url: str
    method: HttpxMethod
    json_response: dict[str, JsonValue] | None = None
    body: str | None = None
    status_code: int = 200
    assert_request: Callable[[httpx.Request], None] | None = None


class _WithHttpxEndpoints:
    """Decorator and context manager that mocks httpx endpoints."""

    __slots__ = (
        "_endpoints",
        "_mock",
        "_real_async_handle_request",
        "_real_sync_handle_request",
    )

    def __init__(self, endpoints: tuple[MockHttpxEndpoint, ...]) -> None:
        self._endpoints = endpoints
        self._mock: HTTPXMock | None = None
        self._real_sync_handle_request: (
            Callable[[httpx.HTTPTransport, httpx.Request], httpx.Response] | None
        ) = None
        self._real_async_handle_request: (
            Callable[
                [httpx.AsyncHTTPTransport, httpx.Request],
                Awaitable[httpx.Response],
            ]
            | None
        ) = None

    def __enter__(self) -> Self:
        options = _HTTPXMockOptions()
        mock = HTTPXMock(options)

        real_sync = httpx.HTTPTransport.handle_request
        real_async = httpx.AsyncHTTPTransport.handle_async_request

        def sync_wrapper(
            transport: httpx.HTTPTransport,
            request: httpx.Request,
        ) -> httpx.Response:
            if options.should_mock(request):
                return mock._handle_request(transport, request)  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
            return real_sync(transport, request)

        async def async_wrapper(
            transport: httpx.AsyncHTTPTransport,
            request: httpx.Request,
        ) -> httpx.Response:
            if options.should_mock(request):
                return await mock._handle_async_request(transport, request)  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
            return await real_async(transport, request)

        httpx.HTTPTransport.handle_request = sync_wrapper  # type: ignore[method-assign]
        httpx.AsyncHTTPTransport.handle_async_request = async_wrapper  # type: ignore[method-assign]

        self._real_sync_handle_request = real_sync
        self._real_async_handle_request = real_async
        self._mock = mock
        self._setup_mocks(mock)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        del exc_type, exc_val, exc_tb
        mock = self._mock
        real_sync = self._real_sync_handle_request
        real_async = self._real_async_handle_request
        self._mock = None
        self._real_sync_handle_request = None
        self._real_async_handle_request = None
        try:
            if mock is not None:
                try:
                    mock._assert_options()  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
                finally:
                    mock.reset()
        finally:
            if real_sync is not None:
                httpx.HTTPTransport.handle_request = real_sync  # type: ignore[method-assign]
            if real_async is not None:
                httpx.AsyncHTTPTransport.handle_async_request = real_async  # type: ignore[method-assign]

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
        endpoint: MockHttpxEndpoint,
    ) -> Callable[[httpx.Request], httpx.Response]:
        def callback(request: httpx.Request) -> httpx.Response:
            if endpoint.assert_request is not None:
                endpoint.assert_request(request)
            if endpoint.json_response is not None:
                return httpx.Response(
                    endpoint.status_code,
                    json=endpoint.json_response,
                )
            if endpoint.body is not None:
                return httpx.Response(endpoint.status_code, text=endpoint.body)
            return httpx.Response(endpoint.status_code)

        return callback

    def _setup_mocks(self, mock: HTTPXMock) -> None:
        """Register all endpoints on the mock."""
        for endpoint in self._endpoints:
            mock.add_callback(
                self._make_callback(endpoint),
                url=endpoint.url,
                method=endpoint.method,
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
                with _WithHttpxEndpoints(self._endpoints):
                    return await func(*args, **kwargs)  # pyright: ignore[reportGeneralTypeIssues]

            return async_wrapper  # pyright: ignore[reportReturnType]

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            with _WithHttpxEndpoints(self._endpoints):
                return func(*args, **kwargs)

        return sync_wrapper


def with_httpx_endpoints(
    endpoints: tuple[MockHttpxEndpoint, ...],
) -> _WithHttpxEndpoints:
    """Mock httpx endpoints for the duration of a test."""
    return _WithHttpxEndpoints(endpoints)
