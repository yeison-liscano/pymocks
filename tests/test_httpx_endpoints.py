"""Tests for MockHttpxEndpoint and with_httpx_endpoints decorator."""

from http import HTTPStatus

import httpx
import pytest

from pymocks import JsonValue, MockHttpxEndpoint, with_httpx_endpoints


class TestMockHttpxEndpoint:
    def test_frozen_dataclass(self) -> None:
        ep = MockHttpxEndpoint(
            url="https://example.com/api",
            method="GET",
            json_response={"ok": True},
        )
        with pytest.raises(AttributeError):
            ep.url = "https://other.com"  # type: ignore[misc]

    def test_defaults(self) -> None:
        ep = MockHttpxEndpoint(url="https://example.com", method="POST")
        assert ep.json_response is None
        assert ep.body is None
        assert ep.status_code == HTTPStatus.OK
        assert ep.assert_request is None


class TestWithHttpxEndpointsDecorator:
    def test_mocked_get_returns_json_sync(self) -> None:
        payload: dict[str, JsonValue] = {"status": "ok", "data": [1, 2, 3]}
        endpoint = MockHttpxEndpoint(
            url="https://api.example.com/health",
            method="GET",
            json_response=payload,
        )

        @with_httpx_endpoints((endpoint,))
        def inner_test() -> None:
            with httpx.Client() as client:
                response = client.get("https://api.example.com/health")
                assert response.json() == payload

        inner_test()

    @pytest.mark.asyncio
    async def test_mocked_post_returns_json_async(self) -> None:
        payload: dict[str, JsonValue] = {"id": 1, "name": "Bob"}
        endpoint = MockHttpxEndpoint(
            url="https://api.example.com/users",
            method="POST",
            json_response=payload,
            status_code=HTTPStatus.CREATED,
        )

        @with_httpx_endpoints((endpoint,))
        async def inner_test() -> None:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.example.com/users",
                    json={"name": "Bob"},
                )
                assert response.status_code == HTTPStatus.CREATED
                assert response.json() == payload

        await inner_test()

    def test_body_response(self) -> None:
        endpoint = MockHttpxEndpoint(
            url="https://api.example.com/raw",
            method="GET",
            body="plain text body",
        )

        @with_httpx_endpoints((endpoint,))
        def inner_test() -> None:
            with httpx.Client() as client:
                response = client.get("https://api.example.com/raw")
                assert response.text == "plain text body"

        inner_test()


class TestAssertRequest:
    def test_assert_request_receives_httpx_request(self) -> None:
        payload: dict[str, JsonValue] = {"id": 1}
        captured: list[httpx.Request] = []

        def on_request(request: httpx.Request) -> None:
            captured.append(request)

        endpoint = MockHttpxEndpoint(
            url="https://api.example.com/users",
            method="POST",
            json_response=payload,
            assert_request=on_request,
        )

        @with_httpx_endpoints((endpoint,))
        def inner_test() -> None:
            with httpx.Client() as client:
                client.post(
                    "https://api.example.com/users",
                    json={"name": "alice"},
                    headers={"Authorization": "Bearer tok"},
                )

        inner_test()
        assert len(captured) == 1
        request = captured[0]
        assert str(request.url) == "https://api.example.com/users"
        assert request.headers["Authorization"] == "Bearer tok"
        assert request.read() == b'{"name":"alice"}'

    @pytest.mark.asyncio
    async def test_assert_request_none_by_default(self) -> None:
        endpoint = MockHttpxEndpoint(
            url="https://api.example.com/health",
            method="GET",
            json_response={"ok": True},
        )
        assert endpoint.assert_request is None

        @with_httpx_endpoints((endpoint,))
        async def inner_test() -> None:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.example.com/health")
                assert response.json() == {"ok": True}

        await inner_test()


class TestWithHttpxEndpointsContextManager:
    def test_sync_context_manager_mocks_endpoint(self) -> None:
        payload: dict[str, JsonValue] = {"status": "ok"}
        endpoint = MockHttpxEndpoint(
            url="https://api.example.com/health",
            method="GET",
            json_response=payload,
        )

        with with_httpx_endpoints((endpoint,)), httpx.Client() as client:
            response = client.get("https://api.example.com/health")
            assert response.json() == payload

    @pytest.mark.asyncio
    async def test_async_context_manager_mocks_endpoint(self) -> None:
        payload: dict[str, JsonValue] = {"status": "ok", "data": [1, 2, 3]}
        endpoint = MockHttpxEndpoint(
            url="https://api.example.com/health",
            method="GET",
            json_response=payload,
        )

        async with (
            with_httpx_endpoints((endpoint,)),
            httpx.AsyncClient() as client,
        ):
            response = await client.get("https://api.example.com/health")
            assert response.json() == payload


class TestTransportRestoration:
    def test_sync_transport_restored_after_exit(self) -> None:
        original = httpx.HTTPTransport.handle_request
        endpoint = MockHttpxEndpoint(
            url="https://api.example.com/health",
            method="GET",
            json_response={"ok": True},
        )
        with with_httpx_endpoints((endpoint,)), httpx.Client() as client:
            client.get("https://api.example.com/health")
        assert httpx.HTTPTransport.handle_request is original

    def test_async_transport_restored_after_exit(self) -> None:
        original = httpx.AsyncHTTPTransport.handle_async_request
        with with_httpx_endpoints(()):
            pass
        assert httpx.AsyncHTTPTransport.handle_async_request is original


class TestAssertAllResponsesRequested:
    def test_unrequested_mock_raises_at_exit(self) -> None:
        endpoint = MockHttpxEndpoint(
            url="https://api.example.com/never_called",
            method="GET",
            json_response={"ok": True},
        )
        with (
            pytest.raises(AssertionError, match="mocked but not requested"),
            with_httpx_endpoints((endpoint,)),
        ):
            pass
