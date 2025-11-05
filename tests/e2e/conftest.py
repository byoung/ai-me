"""End-to-end test configuration and fixtures.

Manages Gradio app server lifecycle and browser fixtures for E2E tests.
"""

import logging
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Iterator

import pytest

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
SRC_DIR = PROJECT_ROOT / "src"
APP_HOST = "127.0.0.1"
APP_PORT = 7870
APP_URL = f"http://{APP_HOST}:{APP_PORT}"
APP_STARTUP_TIMEOUT = 300
APP_SHUTDOWN_TIMEOUT = 10


def _port_is_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a port is accepting connections."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.debug(f"Port check failed for {host}:{port}: {e}")
        return False


class AppServer:
    """Manages the Gradio app server lifecycle."""

    def __init__(self):
        self.process = None

    def start(self) -> None:
        """Start the app server and wait for port 7870 to be listening."""
        logger.info(f"Starting app server on {APP_URL}...")

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["GRADIO_SERVER_PORT"] = str(APP_PORT)
        env["GRADIO_SERVER_NAME"] = APP_HOST  # Bind to 127.0.0.1 specifically

        # Verify required environment variables are present
        if "GROQ_API_KEY" not in env or not env["GROQ_API_KEY"]:
            logger.error("GROQ_API_KEY is not set - app will fail to start")
            raise EnvironmentError("GROQ_API_KEY environment variable is required")
        
        # Verify GITHUB_PERSONAL_ACCESS_TOKEN for loading GitHub repos
        if "GITHUB_PERSONAL_ACCESS_TOKEN" not in env or not env["GITHUB_PERSONAL_ACCESS_TOKEN"]:
            logger.error("GITHUB_PERSONAL_ACCESS_TOKEN is not set - app will fail to load documents")
            raise EnvironmentError("GITHUB_PERSONAL_ACCESS_TOKEN environment variable is required")
        
        # Configure GITHUB_REPOS for E2E tests if not already set
        # These repos are required for the agent to have knowledge to answer questions
        if "GITHUB_REPOS" not in env or not env["GITHUB_REPOS"]:
            env["GITHUB_REPOS"] = "byoung/me,byoung/ai-me"
            logger.info(f"Setting GITHUB_REPOS for E2E tests: {env['GITHUB_REPOS']}")

        try:
            self.process = subprocess.Popen(
                [sys.executable, str(SRC_DIR / "app.py")],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(PROJECT_ROOT),
                env=env,
            )

            # Print startup output to console for debugging
            startup_lines = []
            def log_output():
                if self.process and self.process.stdout:
                    for line in self.process.stdout:
                        line_stripped = line.rstrip()
                        startup_lines.append(line_stripped)
                        print(f"[APP] {line_stripped}")
                        # Signal ready when port appears in output
                        if "7870" in line or "Running on" in line:
                            logger.info(f"Port detection: {line_stripped}")

            threading.Thread(target=log_output, daemon=True).start()

            # Wait for port to actually be listening
            start_time = time.time()
            while time.time() - start_time < APP_STARTUP_TIMEOUT:
                if _port_is_open(APP_HOST, APP_PORT):
                    logger.info(f"✓ App server started on {APP_URL}")
                    return
                time.sleep(0.5)

            # Timeout occurred - show what we captured
            logger.error(f"Timeout waiting for port {APP_PORT} after {APP_STARTUP_TIMEOUT}s")
            logger.error(f"Last 10 startup lines: {startup_lines[-10:]}")
            if self.process:
                logger.error(f"Process returncode: {self.process.returncode}")
            raise TimeoutError(
                f"Port {APP_PORT} did not open within {APP_STARTUP_TIMEOUT}s"
            )

        except Exception as e:
            logger.error(f"Failed to start app server: {e}")
            self._cleanup()
            raise

    def _cleanup(self) -> None:
        """Terminate the subprocess."""
        if not self.process:
            return
        try:
            self.process.terminate()
            self.process.wait(timeout=APP_SHUTDOWN_TIMEOUT)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        finally:
            self.process = None

    def stop(self) -> None:
        """Stop the app server."""
        if not self.process:
            return
        logger.info("Stopping app server...")
        self._cleanup()
        logger.info("✓ App server stopped")


@pytest.fixture(scope="session")
def app_server() -> Iterator[str]:
    """Start the app server for the test session, yield URL to tests.
    
    Skips E2E tests if GROQ_API_KEY is not available (graceful degradation for CI).
    """
    # Check for required environment variable
    if not os.environ.get("GROQ_API_KEY"):
        pytest.skip(
            "GROQ_API_KEY not set - skipping E2E tests (normal in CI without API keys)",
            allow_module_level=True
        )
    
    server = AppServer()
    server.start()
    time.sleep(1)  # Let it fully settle
    yield APP_URL
    server.stop()


@pytest.fixture(scope="session")
def browser_context_args(app_server):
    """Configure browser context for E2E tests."""
    return {
        "base_url": app_server,
        "ignore_https_errors": True,
    }
