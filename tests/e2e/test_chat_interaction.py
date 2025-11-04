"""End-to-end tests for the AI-Me chatbot interface.

Tests the complete user interaction flow with the Gradio chat interface.
Uses sync Playwright to drive a real Chromium browser against the running app.
"""

import logging
import time

import pytest
from playwright.sync_api import Page

logger = logging.getLogger(__name__)


class ChatBotHelper:
    """Helper class for interacting with the Gradio chat interface."""

    def __init__(self, page: Page):
        self.page = page
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def load_page(self, url: str, timeout: int = 120000) -> None:
        """Navigate to the app and wait for the chat interface to load."""
        self.logger.info(f"Loading app at {url}...")
        self.page.goto(url, wait_until="load", timeout=timeout)

        # Wait for heading to indicate page has loaded
        try:
            self.page.locator("h1").first.wait_for(state="visible", timeout=10000)
            self.logger.info("✓ App loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load app: {e}")
            raise

    def send_message(self, message: str, timeout: int = 60000) -> str:
        """Send a chat message and wait for a response from the AI agent."""
        self.logger.info(f"Sending: {message}")

        # Find and fill the input field
        input_field = self.page.locator("textarea, input[type='text']").first
        input_field.wait_for(state="visible", timeout=10000)
        input_field.fill(message)

        # Press Enter to send
        input_field.press("Enter")

        # Wait for response from AI agent
        self.logger.debug("Waiting for AI response...")
        start_time = time.time()
        response_timeout_sec = timeout / 1000
        last_response_text = ""
        stable_count = 0
        
        # Generic selector for bot response bubbles in Gradio chatbot
        # This matches all message rows with the bot-row class
        bot_response_selector = ".message-row.bubble.bot-row"
        
        # Wait for text to stop changing (indicates AI has finished responding)
        while time.time() - start_time < response_timeout_sec:
            try:
                # Get all bot responses
                response_elements = self.page.locator(bot_response_selector)
                if response_elements.count() > 0:
                    # Get the last (most recent) bot response
                    last_element = response_elements.last
                    response_text = last_element.inner_text()
                    
                    # Check if text is stable (no new content for 2 consecutive checks)
                    if response_text == last_response_text:
                        stable_count += 1
                        if stable_count >= 2:
                            # Text has stabilized, we have a complete response
                            if len(response_text) > len(message) * 2:  # Substantial response
                                self.logger.info(f"✓ Got AI response ({len(response_text)} chars) {response_text}")
                                return response_text
                    else:
                        stable_count = 0
                    
                    last_response_text = response_text
            except Exception as e:
                self.logger.debug(f"Error checking page: {e}")
                pass
            
            time.sleep(1.0)  # Check every 1 second for stability

        raise TimeoutError(f"No response received within {timeout}ms")


class TestChatbotInteraction:
    """Test suite for the AI-Me chatbot interface."""

    @pytest.fixture
    def chat(self, page: Page) -> ChatBotHelper:
        """Provide a ChatBotHelper instance for each test."""
        return ChatBotHelper(page)

    def test_happy_path_conversation(self, chat: ChatBotHelper, app_server: str):
        """Happy path: Load app, send realistic prompts, verify responses."""
        # Load the app
        chat.load_page(app_server, timeout=120000)
        
        # Start with a greeting
        resp1 = chat.send_message("Hi", timeout=60000)
        assert resp1 and len(resp1) > 10, "Should get greeting response"
        assert "error" not in resp1.lower(), "Greeting should not contain error text"
        logger.info("✓ Greeting response received")

        # Ask about experience
        resp2 = chat.send_message("Do you have python experience?", timeout=60000)
        assert resp2 and len(resp2) > 20, "Should answer about Python experience"
        assert "error" not in resp2.lower(), "Experience response should not contain error text"
        logger.info("✓ Experience question answered")

        # Ask about challenges
        resp3 = chat.send_message("What is the hardest thing you've ever done?", timeout=60000)
        assert resp3 and len(resp3) > 20, "Should answer about challenges"
        assert "error" not in resp3.lower(), "Response should not contain error text"
        logger.info("✓ Challenge question answered")

        logger.info("✓ Happy path test passed")
