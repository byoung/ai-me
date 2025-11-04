# Testing Guide

## Quick Start

### Prerequisites

1. Set environment variables in `.env`:
   ```bash
   OPENAI_API_KEY=<your-key>
   GROQ_API_KEY=<your-key>
   GITHUB_PERSONAL_ACCESS_TOKEN=<token>  # optional
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

   For E2E tests, install Playwright browsers (one-time):
   ```bash
   uv run playwright install chromium
   ```

## Running Tests Locally

### Default (Unit + Integration)
```bash
# By default, E2E tests are excluded to avoid asyncio conflicts
uv run pytest tests/ -v
```

Runs unit and integration tests.

### Unit Tests Only
```bash
uv run pytest tests/unit/ -v
```

Fast tests with no external dependencies.

### Integration Tests Only
```bash
uv run pytest tests/integration/ -v
```

Async tests that call Groq/OpenAI APIs and test the full agent stack.

### E2E Tests (Run Separately)
```bash
# E2E tests must run separately due to asyncio event loop isolation
uv run pytest tests/e2e/ -v
```

Browser automation test that starts the app in a subprocess as Playwright manages its own event loops. Running E2E with async integration tests causes asyncio conflicts. 

## Running Tests in Docker

The Docker environment has all system dependencies and Playwright browsers pre-installed.

### Unit + Integration Tests (Default)
```bash
# Run the default test service (unit + integration)
docker compose run --rm test
```

### E2E Tests

E2E tests use headless Chromium by default via Playwright, so they can run in Docker:

```bash
# Run E2E tests in Docker (uses headless Chromium)
docker compose run --rm test uv run pytest tests/e2e/ -v
```

## With Code Coverage

```bash
# All tests with coverage report
uv run pytest tests/ --cov=src --cov-report=term-missing -v

# Generate HTML report
uv run pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

## E2E Test Details

**Important**: E2E tests run in a separate pytest session from integration tests to avoid asyncio event loop conflicts. This is industry standard practice.

The E2E test runs a single happy-path scenario:

1. Starts the Gradio app in a subprocess on port 7870
2. Launches a real Chromium browser via Playwright
3. Sends realistic prompts:
   - "Hi" → Greeting response
   - "Do you have python experience?" → Python experience answer
   - "What is the hardest thing you've ever done?" → Challenge story
4. Verifies responses are substantive and error-free

Run locally only:
```bash
uv run pytest tests/e2e/ -v
```

## Troubleshooting

**Port already in use**:
```bash
lsof -ti :7870 | xargs kill -9
```

**Playwright not installed**:
```bash
uv run playwright install chromium
```

**App startup timeout**:
- Check app logs for initialization errors
- Ensure all environment variables are set
- Increase `APP_STARTUP_TIMEOUT` in `tests/e2e/conftest.py` if needed

## Advanced Debugging

### View E2E Test Logs

To see detailed logs from E2E tests (test steps, AI response sizes, etc.):

```bash
uv run pytest tests/e2e/ -v -s --log-cli-level=INFO --headed --browser=chromium
```

This shows:
- When messages are sent to the AI
- Response character counts
- Test assertions as they pass/fail

### Slow Motion Debugging

Watch interactions in slow motion (2-second delays between actions):

```bash
PW_SLOW_MO=2000 uv run pytest tests/e2e/ -v -s --log-cli-level=INFO --headed --browser=chromium
```

### Interactive Debug Mode

Use Playwright Inspector to step through the test:

```bash
PWDEBUG=1 uv run pytest tests/e2e/ -v --headed --browser=chromium
```

This opens the Playwright Inspector where you can pause, step through, and inspect the page.



