import asyncio
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from app import main
from app.database import get_db


def asgi_request(method, path, headers=None):
    """Call the FastAPI ASGI app directly, without a live server or httpx."""
    request_headers = [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in (headers or {}).items()
    ]
    messages = []
    request_sent = False

    async def receive():
        nonlocal request_sent
        if request_sent:
            return {"type": "http.disconnect"}
        request_sent = True
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": request_headers,
        "server": ("testserver", 80),
        "client": ("testclient", 12345),
    }
    asyncio.run(main.app(scope, receive, send))
    start = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return start["status"], dict(start["headers"]), body


class DeploymentHttpTests(unittest.TestCase):
    def test_health_is_available_without_database_or_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(main, "engine", None):
                status, _, body = asgi_request("GET", "/health")

        self.assertEqual(status, 200)
        self.assertEqual(body, b'{"status":"ok"}')

    def test_database_health_reports_unconfigured_database(self):
        with patch.object(main, "engine", None):
            status, _, body = asgi_request("GET", "/health/db")

        self.assertEqual(status, 503)
        self.assertEqual(body, b'{"detail":"Database is not configured."}')

    def test_protected_cve_lookup_rejects_missing_and_incorrect_keys(self):
        with patch.dict(os.environ, {"BREACHX_API_KEY": "test-deployment-key"}):
            missing_status, _, _ = asgi_request("GET", "/cve/CVE-2025-1234")
            incorrect_status, _, _ = asgi_request(
                "GET", "/cve/CVE-2025-1234", {"X-API-Key": "incorrect"}
            )

        self.assertEqual(missing_status, 401)
        self.assertEqual(incorrect_status, 401)

    def test_protected_cve_lookup_proceeds_with_correct_key(self):
        with patch.dict(os.environ, {"BREACHX_API_KEY": "test-deployment-key"}):
            with patch.object(main, "get_cve", return_value=None) as get_cve:
                status, _, _ = asgi_request(
                    "GET",
                    "/cve/CVE-2025-1234",
                    {"X-API-Key": "test-deployment-key"},
                )

        self.assertEqual(status, 404)
        get_cve.assert_called_once_with("CVE-2025-1234")

    def test_assets_read_remains_unauthenticated_and_returns_existing_shape(self):
        main.app.dependency_overrides[get_db] = lambda: object()
        try:
            with patch.dict(os.environ, {}, clear=True):
                with patch.object(main, "list_assets", return_value=[]):
                    status, _, body = asgi_request("GET", "/assets")
        finally:
            main.app.dependency_overrides.pop(get_db, None)

        self.assertEqual(status, 200)
        self.assertEqual(body, b"[]")

    def test_configured_cors_origin_is_allowed(self):
        origin = main.cors_origins[0]
        status, headers, _ = asgi_request(
            "OPTIONS",
            "/assets",
            {
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(status, 200)
        self.assertEqual(headers.get(b"access-control-allow-origin"), origin.encode())

    def test_wildcard_cors_origin_is_rejected(self):
        backend_dir = Path(__file__).resolve().parents[1]
        environment = os.environ.copy()
        environment["CORS_ORIGINS"] = "*"
        result = subprocess.run(
            [sys.executable, "-c", "import app.main"],
            cwd=backend_dir,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("wildcard origins are not supported", result.stderr)

    def test_nvd_api_key_is_sent_only_to_nvd_from_backend(self):
        from app.services import nvd_client

        response = unittest.mock.Mock()
        response.json.return_value = {"vulnerabilities": [], "totalResults": 0}
        with patch.dict(os.environ, {"NVD_API_KEY": "test-nvd-key"}):
            with patch.object(nvd_client.requests, "get", return_value=response) as get:
                nvd_client.fetch_cve("CVE-2025-1234")

        sent_headers = get.call_args.kwargs["headers"]
        self.assertTrue(sent_headers.get("apiKey") == "test-nvd-key")

        frontend_root = Path(__file__).resolve().parents[2] / "frontend"
        frontend_files = [
            *frontend_root.joinpath("src").rglob("*"),
            frontend_root / ".env.example",
        ]
        source_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in frontend_files
            if path.is_file()
        )
        self.assertNotIn("NVD_API_KEY", source_text)


if __name__ == "__main__":
    unittest.main()
