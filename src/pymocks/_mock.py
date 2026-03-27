"""Core mocking utilities for monkeypatching module attributes."""

import functools
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from inspect import isclass, iscoroutinefunction, isfunction
from types import ModuleType, TracebackType
from typing import Self, overload

import pytest


def _get_object_type_name(obj: object) -> str:
    return type(obj).__name__


def _get_object_name(obj: object) -> str:
    if name := getattr(obj, "__name__", None):
        return name
    return _get_object_type_name(obj)


def _get_variable_name(module: ModuleType, var: object) -> str:
    """Find the attribute name in a module that refers to the given object."""
    for name in dir(module):
        if getattr(module, name) is var:
            return name
    msg = (
        f"{var!r} not declared nor imported in module {module.__name__}"
        f". Make sure {_get_object_name(var)} is declared or imported in"
        f" {module.__name__}."
    )
    raise ValueError(msg)


@dataclass
class Mock[T_mocked]:
    """Hold a monkeypatch specification for attribute replacement."""

    module_where_used: ModuleType
    current_value: T_mocked
    new_value: T_mocked

    def __post_init__(self) -> None:
        self._validate_var_existence_on_module()
        self._validate_types()
        if isfunction(self.current_value):
            self._validate_signatures()
        elif isclass(self.current_value):
            self._validate_class_replacement()

    def _validate_signatures(self) -> None:
        """Verify that current_value and new_value have identical signatures."""
        try:
            current_sig = inspect.signature(self.current_value)  # pyright: ignore[reportArgumentType]
            new_sig = inspect.signature(self.new_value)  # pyright: ignore[reportArgumentType]
        except (ValueError, TypeError):
            return

        if current_sig != new_sig:
            msg = f"Signature mismatch: {current_sig} != {new_sig}"
            raise TypeError(msg)

    def _validate_types(self) -> None:
        """Verify that current_value and new_value have the same type."""
        current_type = type(self.current_value)
        new_type = type(self.new_value)

        if current_type is not new_type:
            msg = f"Type mismatch: {current_type.__name__} != {new_type.__name__}"
            raise TypeError(msg)

    def _validate_var_existence_on_module(self) -> None:
        """Ensure that current_value is actually an attribute of the target module."""
        _get_variable_name(self.module_where_used, self.current_value)

    def _validate_class_replacement(self) -> None:
        """If replacing a class, ensure the new value is a compatible class."""
        if not issubclass(self.new_value, self.current_value):  # pyright: ignore[reportArgumentType]
            msg = (
                f"New class {_get_object_type_name(self.new_value)} is not a "
                f"subclass of {_get_object_type_name(self.current_value)}"
            )
            raise TypeError(msg)

    @property
    def name(self) -> str:
        """Resolve the attribute name in the target module."""
        if isfunction(self.current_value):
            return self.current_value.__name__
        return _get_variable_name(self.module_where_used, self.current_value)


class _WithMock[T_return]:
    """Decorator and context manager that monkeypatches a module attribute."""

    __slots__ = ("_mock", "_monkeypatch")

    def __init__(self, mock: Mock[T_return]) -> None:
        self._mock = mock
        self._monkeypatch: pytest.MonkeyPatch | None = None

    def __enter__(self) -> Self:
        mp = pytest.MonkeyPatch()
        mp.setattr(
            self._mock.module_where_used,
            self._mock.name,
            self._mock.new_value,
        )
        self._monkeypatch = mp
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._monkeypatch is not None:
            self._monkeypatch.undo()
            self._monkeypatch = None

    async def __aenter__(self) -> Self:
        return self.__enter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.__exit__(exc_type, exc_val, exc_tb)

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
        """Apply monkeypatch around the decorated function."""
        mock = self._mock

        if iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(
                *args: P.args,
                **kwargs: P.kwargs,
            ) -> T:
                with pytest.MonkeyPatch().context() as monkeypatch:
                    monkeypatch.setattr(
                        mock.module_where_used,
                        mock.name,
                        mock.new_value,
                    )
                    return await func(*args, **kwargs)  # pyright: ignore[reportGeneralTypeIssues]

            return async_wrapper  # pyright: ignore[reportReturnType]

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            with pytest.MonkeyPatch().context() as monkeypatch:
                monkeypatch.setattr(
                    mock.module_where_used,
                    mock.name,
                    mock.new_value,
                )
                return func(*args, **kwargs)

        return sync_wrapper


def with_mock[T_return](mock: Mock[T_return]) -> _WithMock[T_return]:
    """Monkeypatch a module attribute for the duration of a test."""
    return _WithMock(mock)
