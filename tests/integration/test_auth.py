"""
tests/integration/test_auth.py
================================
Integration tests for /api/v1/auth/* endpoints.

Spring Boot equivalent
-----------------------
  AuthControllerTest.java using MockMvc or TestRestTemplate.
  @SpringBootTest(webEnvironment=RANDOM_PORT)
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "password": "Pass@1234",
        })
        assert resp.status_code == 201
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["user"]["email"] == "jane@example.com"
        assert body["user"]["role"] == "student"
        assert "hashed_password" not in body["user"]  # never exposed

    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {"full_name": "Dup User", "email": "dup@example.com", "password": "Pass@1234"}
        await client.post("/api/v1/auth/register", json=payload)
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409

    async def test_register_short_password(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "full_name": "Short", "email": "short@example.com", "password": "ab",
        })
        assert resp.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "full_name": "Bad Email", "email": "not-an-email", "password": "Pass@1234",
        })
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestLogin:
    async def test_login_success(self, client: AsyncClient, registered_user: dict):
        resp = await client.post("/api/v1/auth/login-json", json={
            "email": "test@codefount.com",
            "password": "Test@1234",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_login_wrong_password(self, client: AsyncClient, registered_user: dict):
        resp = await client.post("/api/v1/auth/login-json", json={
            "email": "test@codefount.com",
            "password": "WRONG",
        })
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login-json", json={
            "email": "nobody@example.com",
            "password": "whatever",
        })
        assert resp.status_code == 401


@pytest.mark.asyncio
class TestProtectedRoutes:
    async def test_get_me_authenticated(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "test@codefount.com"

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_get_me_bad_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer bad.token"})
        assert resp.status_code == 401

    async def test_refresh_token(self, client: AsyncClient, registered_user: dict):
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": registered_user["refresh_token"]
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_change_password(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post("/api/v1/auth/change-password", json={
            "current_password": "Test@1234",
            "new_password": "NewPass@5678",
        }, headers=auth_headers)
        assert resp.status_code == 204


@pytest.mark.asyncio
class TestPublicRoutes:
    async def test_health_check(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_enquiry_guest(self, client: AsyncClient):
        resp = await client.post("/api/v1/enquiries", json={
            "name": "Visitor",
            "email": "visitor@test.com",
            "message": "I want to know more about Java course",
        })
        assert resp.status_code == 201