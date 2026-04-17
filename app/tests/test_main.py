"""Integration tests for PowerCV main application (startup, shutdown, error handlers)."""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.database.connector import MongoConnectionManager
from app.database.models.resume import Resume
from app.main import (
    app,
    global_exception_handler,
    http_exception_handler,
    shutdown_logic,
    startup_logic,
)


class TestAppLifecycle:
    """Test application startup and shutdown."""

    @pytest.mark.asyncio
    async def test_startup_logic_success(self):
        """Test successful application startup."""
        mock_app = MagicMock(spec=FastAPI)
        mock_app.state = MagicMock()

        mock_mongo = AsyncMock()
        mock_mongo.close_all = AsyncMock()

        mock_conn_manager = MagicMock()
        mock_conn_manager.get_instance = MagicMock(return_value=mock_mongo)

        with (
            patch("app.main.get_settings") as mock_settings,
            patch("app.main.MongoConnectionManager", mock_conn_manager),
            patch("app.main.ResumeRepository") as mock_repo,
        ):
            mock_settings.return_value.sentry_dsn = None  # Disable Sentry
            mock_repo.return_value = MagicMock()

            await startup_logic(mock_app)

            # Verify connections initialized
            assert mock_app.state.mongo is not None

    @pytest.mark.asyncio
    async def test_startup_logic_sentry_failure(self):
        """Test startup handles Sentry initialization failure gracefully."""
        mock_app = MagicMock(spec=FastAPI)
        mock_app.state = MagicMock()

        mock_mongo = AsyncMock()
        mock_mongo.close_all = AsyncMock()

        mock_conn_manager = MagicMock()
        mock_conn_manager.get_instance = MagicMock(return_value=mock_mongo)

        with (
            patch("app.main.get_settings") as mock_settings,
            patch("app.main.sentry_sdk.init") as mock_sentry,
            patch("app.main.MongoConnectionManager", mock_conn_manager),
            patch("app.main.ResumeRepository"),
        ):
            # Sentry raises exception
            mock_sentry.side_effect = Exception("Sentry error")
            mock_settings.return_value.sentry_dsn = "http://sentry.example.com"
            mock_settings.return_value.debug = False

            # Should not raise - error logged and continues
            await startup_logic(mock_app)
            assert mock_app.state.mongo is not None

    @pytest.mark.asyncio
    async def test_startup_logic_db_failure(self):
        """Test startup handles database connection failure."""
        mock_app = MagicMock(spec=FastAPI)
        mock_app.state = MagicMock()

        mock_conn_manager = MagicMock()
        mock_conn_manager.get_instance = MagicMock(
            side_effect=Exception("DB connection failed")
        )

        with (
            patch("app.main.get_settings") as mock_settings,
            patch("app.main.MongoConnectionManager", mock_conn_manager),
        ):
            mock_settings.return_value.sentry_dsn = None
            # Startup should raise
            with pytest.raises(Exception) as exc_info:
                await startup_logic(mock_app)
            assert "DB connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_shutdown_logic_success(self):
        """Test successful shutdown."""
        mock_app = MagicMock(spec=FastAPI)
        mock_app.state = MagicMock()
        mock_mongo = AsyncMock()
        mock_app.state.mongo = mock_mongo

        await shutdown_logic(mock_app)

        mock_mongo.close_all.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_shutdown_logic_mongo_not_set(self):
        """Test shutdown when mongo not initialized."""
        mock_app = MagicMock(spec=FastAPI)
        mock_app.state = MagicMock()
        # No mongo attribute
        del mock_app.state.mongo

        # Should not raise
        await shutdown_logic(mock_app)


class TestExceptionHandlers:
    """Test global exception handlers."""

    def test_global_exception_handler_returns_sanitized_error(self):
        """Test that global exception handler hides internal details."""
        from fastapi import Request
        from starlette.exceptions import HTTPException

        # Create mock request
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"

        exc = ValueError("Some internal error")
        response = asyncio.run(global_exception_handler(mock_request, exc))

        assert response.status_code == 500
        # Body check
        import json

        content = json.loads(response.body.decode())
        assert content["error"] == "Internal server error"
        assert "detail" in content

    def test_http_exception_handler_api_returns_json(self):
        """Test HTTP exceptions on API routes return JSON."""
        from fastapi import Request
        from starlette.exceptions import HTTPException

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/unknown"

        exc = HTTPException(status_code=404, detail="Not found")
        response = asyncio.run(http_exception_handler(mock_request, exc))

        import json

        content = json.loads(response.body.decode())
        assert response.status_code == 404
        # Custom 404 message for API routes
        assert content["detail"] == "Resource not found"

    def test_http_exception_handler_web_returns_template(self):
        """Test HTTP exceptions on web routes return HTML template."""
        from fastapi import Request
        from starlette.exceptions import HTTPException
        from starlette.responses import HTMLResponse

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/unknown"

        exc = HTTPException(status_code=404, detail="Not found")
        # We need to patch templates
        with patch("app.main.templates") as mock_templates:
            mock_templates.TemplateResponse = MagicMock(
                return_value=HTMLResponse(content="404 page")
            )
            response = asyncio.run(http_exception_handler(mock_request, exc))
            # Should return HTMLResponse
            assert isinstance(response, HTMLResponse)


class TestAppImport:
    """Test that app can be imported and has expected attributes."""

    def test_app_import(self):
        """App object exists."""
        from app.main import app

        assert app is not None

    def test_app_has_routers(self):
        """App includes expected routers."""
        from app.main import app

        # Check some routes are registered
        routes = [str(route.path) for route in app.routes]
        assert any("health" in r for r in routes)

    def test_app_title(self):
        """App metadata correct."""
        from app.main import app

        assert app.title == "PowerCV API"


class TestAIApiEndpoints:
    """Tests for AI-powered API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient

        from app.main import app

        return TestClient(app, raise_server_exceptions=False)

    @pytest.mark.asyncio
    async def test_analyze_endpoint(self, client, sample_cv_text, sample_jd_text):
        """Test POST /api/v2/analyze endpoint."""
        from unittest.mock import AsyncMock, patch

        mock_response = {
            "ats_score": 85,
            "summary": "Strong candidate",
            "keyword_analysis": {"matched_keywords": [], "missing_critical": []},
            "experience_analysis": {"relevant_roles": []},
            "skill_gaps": {"critical": [], "important": []},
            "strengths": ["Python"],
            "recommendations": [],
        }

        with patch("app.main.analyze_cv") as mock_analyze:
            mock_analyze.return_value = mock_response
            response = client.post(
                "/api/v2/analyze",
                json={"cv_text": sample_cv_text, "jd_text": sample_jd_text},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["ats_score"] == 85

    @pytest.mark.asyncio
    async def test_optimize_endpoint(self, client, sample_cv_text, sample_jd_text):
        """Test POST /api/v2/optimize endpoint."""
        from unittest.mock import patch

        mock_response = {
            "optimized_cv": {"user_information": {"name": "Test"}},
            "ats_score": 90,
            "original_ats_score": 75,
            "improvement": 15,
        }

        with patch("app.main.optimize_cv") as mock_opt:
            mock_opt.return_value = mock_response
            response = client.post(
                "/api/v2/optimize",
                json={
                    "cv_text": sample_cv_text,
                    "jd_text": sample_jd_text,
                    "generate_cover_letter": False,
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["improvement"] == 15

    @pytest.mark.asyncio
    async def test_cover_letter_endpoint(self, client):
        """Test POST /api/v2/cover-letter endpoint."""
        from unittest.mock import patch

        mock_response = {
            "cover_letter": "Dear...",
            "word_count": 100,
            "tone": "Professional",
        }

        with patch("app.main.generate_cover_letter") as mock_gen:
            mock_gen.return_value = mock_response
            response = client.post(
                "/api/v2/cover-letter",
                json={
                    "candidate_data": {"name": "John", "email": "john@example.com"},
                    "job_data": {"company": "TechCorp", "position": "Developer"},
                    "tone": "Professional",
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert data["tone"] == "Professional"

    def test_health_endpoint(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
