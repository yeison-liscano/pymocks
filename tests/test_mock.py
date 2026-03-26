"""Tests for the core Mock dataclass and with_mock decorator."""

import pytest

import tests.dumy_module as dummy_module
from pymocks import Mock, with_mock


class TestMockName:
    def test_name_from_function(self) -> None:
        def replacement() -> str:
            return "mocked"

        m = Mock(
            module_where_used=dummy_module,
            current_value=dummy_module.original_func,
            new_value=replacement,
        )
        assert m.name == "original_func"

    def test_name_from_variable(self) -> None:
        m: Mock[str] = Mock(
            module_where_used=dummy_module,
            current_value=dummy_module.MY_VAR,
            new_value="replaced",
        )
        assert m.name == "MY_VAR"

    def test_name_not_found_raises(self) -> None:
        sentinel = object()
        with pytest.raises(ValueError, match="not declared nor imported in module"):
            Mock(
                module_where_used=dummy_module,
                current_value=sentinel,
                new_value=sentinel,
            )


class TestMockValidation:
    def test_matching_signatures_accepted(self) -> None:
        def new(x: int, y: str) -> bool:
            return True

        Mock(
            module_where_used=dummy_module,
            current_value=dummy_module.func_two_params,
            new_value=new,
        )

    def test_signature_param_count_mismatch_raises(self) -> None:
        def new(x: int, y: str) -> None:
            pass

        with pytest.raises(TypeError, match="Signature mismatch"):
            Mock(
                module_where_used=dummy_module,
                current_value=dummy_module.func_one_int_param,
                new_value=new,
            )

    def test_signature_param_name_mismatch_raises(self) -> None:
        def new(y: int) -> None:
            pass

        with pytest.raises(TypeError, match="Signature mismatch"):
            Mock(
                module_where_used=dummy_module,
                current_value=dummy_module.func_one_int_param,
                new_value=new,
            )

    def test_signature_annotation_mismatch_raises(self) -> None:
        def new(x: str) -> str:
            return x

        with pytest.raises(TypeError, match="Signature mismatch"):
            Mock(
                module_where_used=dummy_module,
                current_value=dummy_module.func_int_to_str,
                new_value=new,
            )

    def test_return_annotation_mismatch_raises(self) -> None:
        def new() -> int:
            return 0

        with pytest.raises(TypeError, match="Signature mismatch"):
            Mock(
                module_where_used=dummy_module,
                current_value=dummy_module.original_func,
                new_value=new,
            )

    def test_callable_vs_noncallable_raises(self) -> None:
        with pytest.raises(TypeError, match="Type mismatch: function != str"):
            Mock(
                module_where_used=dummy_module,
                current_value=dummy_module.original_func,
                new_value="not a callable",
            )

    def test_noncallable_vs_callable_raises(self) -> None:
        def new() -> None:
            pass

        with pytest.raises(TypeError, match="mismatch: str != function"):
            Mock(
                module_where_used=dummy_module,
                current_value=dummy_module.MY_VAR,
                new_value=new,
            )

    def test_type_mismatch_raises(self) -> None:
        with pytest.raises(TypeError, match="Type mismatch"):
            Mock(
                module_where_used=dummy_module,
                current_value=dummy_module.MY_VAR,
                new_value=42,
            )

    def test_matching_types_accepted_primitives(self) -> None:
        primitives = (
            dummy_module.STRING,
            dummy_module.FLOAT,
            dummy_module.INT,
            dummy_module.BOOL,
            dummy_module.NONE,
        )
        for value in primitives:
            assert Mock(
                module_where_used=dummy_module,
                current_value=value,
                new_value=value,
            ).name

    def test_mismatched_rejected_classes(self) -> None:
        class MockClassA:
            def non_existent_method(self) -> None:
                pass

        with pytest.raises(TypeError, match="is not a subclass of"):
            Mock(
                module_where_used=dummy_module,
                current_value=dummy_module.DummyClass,
                new_value=MockClassA,
            )

    def test_compatible_class_accepted(self) -> None:
        class MockClassB(dummy_module.DummyClass):
            def method(self) -> str:
                return "mocked"

        Mock(
            module_where_used=dummy_module,
            current_value=dummy_module.DummyClass,
            new_value=MockClassB,
        )


class TestWithMockSync:
    def test_monkeypatch_applies_and_reverts(self) -> None:
        def replacement() -> str:
            return "mocked"

        m = Mock(
            module_where_used=dummy_module,
            current_value=dummy_module.original_func,
            new_value=replacement,
        )

        @with_mock(m)
        def inner_test() -> None:
            assert getattr(dummy_module, "original_func") is replacement

        inner_test()
        assert getattr(dummy_module, "original_func") is dummy_module.original_func


class TestWithMockAsync:
    @pytest.mark.asyncio
    async def test_monkeypatch_applies_and_reverts(self) -> None:
        def replacement() -> str:
            return "mocked"

        m = Mock(
            module_where_used=dummy_module,
            current_value=dummy_module.original_func,
            new_value=replacement,
        )

        @with_mock(m)
        async def inner_test() -> None:
            assert getattr(dummy_module, "original_func") is replacement

        await inner_test()
        assert getattr(dummy_module, "original_func") is dummy_module.original_func
