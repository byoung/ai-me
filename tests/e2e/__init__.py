"""End-to-end tests for the AI-Me application.

Tests the complete application stack including:
- Gradio server startup and web interface
- Browser-based user interactions
- Chat interface and message handling
- Live code coverage collection

These tests run the full app.py server in a background thread while
driving browser automation via Playwright. Coverage is collected
across all interactions.
"""
