"""Tests for MockEndpoint and with_endpoints decorator."""

import json

import aiohttp
import pytest

from pymocks import JsonValue, MockEndpoint, with_endpoints


class TestMockEndpoint:
    def test_frozen_dataclass(self) -> None:
        ep = MockEndpoint(
            url="https://example.com/api",
            method="GET",
            json_response={"ok": True},
        )
        with pytest.raises(AttributeError):
            ep.url = "https://other.com"  # type: ignore[misc]

    def test_defaults(self) -> None:
        ep = MockEndpoint(url="https://example.com", method="POST")
        assert ep.json_response is None
        assert ep.body is None


class TestWithEndpointsDecorator:
    @pytest.mark.asyncio
    async def test_mocked_get_returns_json(self) -> None:
        payload: dict[str, JsonValue] = {"status": "ok", "data": [1, 2, 3]}
        endpoint = MockEndpoint(
            url="https://api.example.com/health",
            method="GET",
            json_response=payload,
        )

        @with_endpoints((endpoint,))
        async def inner_test() -> None:
            async with (
                aiohttp.ClientSession() as session,
                session.get("https://api.example.com/health") as resp,
            ):
                text = await resp.text()
                assert json.loads(text) == payload

        await inner_test()


class TestWithEndpointsContextManager:
    @pytest.mark.asyncio
    async def test_async_context_manager_mocks_endpoint(self) -> None:
        payload: dict[str, JsonValue] = {"status": "ok", "data": [1, 2, 3]}
        endpoint = MockEndpoint(
            url="https://api.example.com/health",
            method="GET",
            json_response=payload,
        )

        async with (
            with_endpoints((endpoint,)),
            aiohttp.ClientSession() as session,
            session.get("https://api.example.com/health") as resp,
        ):
            text = await resp.text()
            assert json.loads(text) == payload
