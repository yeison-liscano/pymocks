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


class TestWithMockDecorator:
    def test_sync_monkeypatch_applies_and_reverts(self) -> None:
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

    @pytest.mark.asyncio
    async def test_async_monkeypatch_applies_and_reverts(self) -> None:
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

    def test_sync_multiple_mocks(self) -> None:
        def replacement_func() -> str:
            return "mocked"

        def replacement_another() -> str:
            return "mocked_another"

        m1 = Mock(
            module_where_used=dummy_module,
            current_value=dummy_module.original_func,
            new_value=replacement_func,
        )
        m2 = Mock(
            module_where_used=dummy_module,
            current_value=dummy_module.another_func,
            new_value=replacement_another,
        )

        @with_mock(m1, m2)
        def inner_test() -> None:
            assert getattr(dummy_module, "original_func") is replacement_func
            assert getattr(dummy_module, "another_func") is replacement_another

        inner_test()
        assert getattr(dummy_module, "original_func") is dummy_module.original_func
        assert getattr(dummy_module, "another_func") is dummy_module.another_func

    @pytest.mark.asyncio
    async def test_async_multiple_mocks(self) -> None:
        def replacement_func() -> str:
            return "mocked"

        def replacement_another() -> str:
            return "mocked_another"

        m1 = Mock(
            module_where_used=dummy_module,
            current_value=dummy_module.original_func,
            new_value=replacement_func,
        )
        m2 = Mock(
            module_where_used=dummy_module,
            current_value=dummy_module.another_func,
            new_value=replacement_another,
        )

        @with_mock(m1, m2)
        async def inner_test() -> None:
            assert getattr(dummy_module, "original_func") is replacement_func
            assert getattr(dummy_module, "another_func") is replacement_another

        await inner_test()
        assert getattr(dummy_module, "original_func") is dummy_module.original_func
        assert getattr(dummy_module, "another_func") is dummy_module.another_func


class TestWithMockContextManager:
    def test_sync_context_manager_applies_and_reverts(self) -> None:
        def replacement() -> str:
            return "mocked"

        m = Mock(
            module_where_used=dummy_module,
            current_value=dummy_module.original_func,
            new_value=replacement,
        )

        with with_mock(m):
            assert getattr(dummy_module, "original_func") is replacement

        assert getattr(dummy_module, "original_func") is dummy_module.original_func

    @pytest.mark.asyncio
    async def test_async_context_manager_applies_and_reverts(self) -> None:
        def replacement() -> str:
            return "mocked"

        m = Mock(
            module_where_used=dummy_module,
            current_value=dummy_module.original_func,
            new_value=replacement,
        )

        async with with_mock(m):
            assert getattr(dummy_module, "original_func") is replacement

        assert getattr(dummy_module, "original_func") is dummy_module.original_func

    def test_sync_context_manager_multiple_mocks(self) -> None:
        def replacement_func() -> str:
            return "mocked"

        def replacement_another() -> str:
            return "mocked_another"

        m1 = Mock(
            module_where_used=dummy_module,
            current_value=dummy_module.original_func,
            new_value=replacement_func,
        )
        m2 = Mock(
            module_where_used=dummy_module,
            current_value=dummy_module.another_func,
            new_value=replacement_another,
        )

        with with_mock(m1, m2):
            assert getattr(dummy_module, "original_func") is replacement_func
            assert getattr(dummy_module, "another_func") is replacement_another

        assert getattr(dummy_module, "original_func") is dummy_module.original_func
        assert getattr(dummy_module, "another_func") is dummy_module.another_func

    @pytest.mark.asyncio
    async def test_async_context_manager_multiple_mocks(self) -> None:
        def replacement_func() -> str:
            return "mocked"

        def replacement_another() -> str:
            return "mocked_another"

        m1 = Mock(
            module_where_used=dummy_module,
            current_value=dummy_module.original_func,
            new_value=replacement_func,
        )
        m2 = Mock(
            module_where_used=dummy_module,
            current_value=dummy_module.another_func,
            new_value=replacement_another,
        )

        async with with_mock(m1, m2):
            assert getattr(dummy_module, "original_func") is replacement_func
            assert getattr(dummy_module, "another_func") is replacement_another

        assert getattr(dummy_module, "original_func") is dummy_module.original_func
        assert getattr(dummy_module, "another_func") is dummy_module.another_func
