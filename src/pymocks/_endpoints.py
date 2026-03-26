"""HTTP endpoint mocking utilities using aioresponses."""
from __future__ import annotations

import functools
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from inspect import iscoroutinefunction
from typing import Literal, overload

from aioresponses import aioresponses

type JsonValue = (
    str | int | float | bool | None | dict[str, JsonValue] | list[JsonValue]
)


@dataclass(frozen=True)
class MockEndpoint:
    """Define an HTTP endpoint mock specification."""

    url: str
    method: Literal["GET", "POST", "PUT", "DELETE"]
    json_response: dict[str, JsonValue] | None = None
    body: str | None = None


class _WithEndpoints:
    """Decorator that mocks HTTP endpoints during a test."""

    __slots__ = ("_endpoints",)

    def __init__(self, endpoints: tuple[MockEndpoint, ...]) -> None:
        self._endpoints = endpoints

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
