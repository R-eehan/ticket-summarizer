"""
LLM Provider Abstraction Layer for Zendesk Ticket Summarizer.

This module implements a factory pattern to support multiple LLM providers:
- Google Gemini (free tier)
- Azure OpenAI GPT-4o (enterprise)

Phase 3c: Multi-Model Support
Rationale: Allows switching between LLM providers without changing business logic,
enabling cost optimization and avoiding free-tier API limits.
"""

import logging
import asyncio
from typing import Dict, Any
from openai import AzureOpenAI

from google import genai

import config
import utils


# ============================================================================
# RESPONSE WRAPPER CLASS (for consistency between providers)
# ============================================================================

class LLMResponse:
    """
    Unified response object that works across both Gemini and Azure OpenAI.

    Gemini returns response.text directly.
    Azure OpenAI returns response.choices[0].message.content.

    This wrapper normalizes both to provide a consistent .text property.
    """

    def __init__(self, text: str, raw_response: Any = None):
        """
        Initialize LLM response wrapper.

        Args:
            text: The generated text from the LLM
            raw_response: The raw response object (for debugging/logging)
        """
        self.text = text
        self._raw_response = raw_response


# ============================================================================
# AZURE OPENAI CLIENT WRAPPER
# ============================================================================

class AzureOpenAIClient:
    """
    Wrapper for Azure OpenAI API that matches Gemini's interface.

    Uses the modern openai Python SDK (v2.7.1+) with AzureOpenAI class.
    Implements the same generate_content() method as Gemini for seamless switching.
    """

    def __init__(self):
        """
        Initialize Azure OpenAI client with credentials from config.

        Raises:
            ValueError: If Azure credentials are missing or invalid
        """
        self.logger = logging.getLogger("ticket_summarizer.llm_provider")

        # Validate Azure credentials
        if not config.AZURE_OPENAI_ENDPOINT:
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT environment variable is not set. "
                "Please add it to your .env file."
            )
        if not config.AZURE_OPENAI_API_KEY:
            raise ValueError(
                "AZURE_OPENAI_API_KEY environment variable is not set. "
                "Please add it to your .env file."
            )
        if not config.AZURE_OPENAI_DEPLOYMENT_NAME:
            raise ValueError(
                "AZURE_OPENAI_DEPLOYMENT_NAME environment variable is not set. "
                "Please add it to your .env file."
            )

        self.logger.info("Initializing Azure OpenAI client")

        # Initialize Azure OpenAI client using modern SDK
        self.client = AzureOpenAI(
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_API_KEY,
            api_version=config.AZURE_OPENAI_API_VERSION
        )

        self.deployment_name = config.AZURE_OPENAI_DEPLOYMENT_NAME
        self.logger.info(f"Azure OpenAI client initialized with deployment: {self.deployment_name}")

    def generate_content(self, prompt: str) -> LLMResponse:
        """
        Generate content using Azure OpenAI (synchronous).

        Matches Gemini's generate_content() interface for seamless switching.
        Uses chat completions API with system + user message pattern.

        Args:
            prompt: The prompt text to send to the LLM

        Returns:
            LLMResponse object with .text property containing generated content

        Raises:
            utils.GeminiAPIError: Renamed to match existing error handling (actually Azure error)
        """
        try:
            self.logger.debug(f"Calling Azure OpenAI with deployment: {self.deployment_name}")

            # Call Azure OpenAI chat completions API
            response = self.client.chat.completions.create(
                model=self.deployment_name,  # This is the deployment name, not model name
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert support ticket analyst. Provide accurate, structured analysis based only on the provided ticket data."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent, factual responses
                max_tokens=2000,  # Sufficient for ticket analysis
                top_p=0.95
            )

            # Extract text from response
            generated_text = response.choices[0].message.content

            self.logger.debug(f"Azure OpenAI response received: {len(generated_text)} characters")

            # Return wrapped response with consistent interface
            return LLMResponse(text=generated_text, raw_response=response)

        except Exception as e:
            self.logger.error(f"Azure OpenAI API call failed: {e}")
            # Use GeminiAPIError for consistency with existing error handling
            # (Will rename to LLMAPIError in future refactoring)
            raise utils.GeminiAPIError(f"Azure OpenAI API call failed: {e}")


# ============================================================================
# GEMINI CLIENT WRAPPER (for consistency)
# ============================================================================

class GeminiClient:
    """
    Wrapper for Google Gemini API using the new unified google-genai SDK.

    Migrated from deprecated google-generativeai to google-genai SDK (Phase 4).
    Maintains backward-compatible interface for seamless integration.
    """

    def __init__(self):
        """
        Initialize Gemini client with API key from config.

        Raises:
            ValueError: If Gemini API key is missing
        """
        self.logger = logging.getLogger("ticket_summarizer.llm_provider")

        # Validate Gemini credentials
        if not config.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please add it to your .env file."
            )

        self.logger.info("Initializing Gemini client with new google-genai SDK")

        # Initialize new unified Google GenAI client
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model_name = config.GEMINI_MODEL

        self.logger.info(f"Gemini client initialized with model: {self.model_name}")

    def generate_content(self, prompt: str) -> Any:
        """
        Generate content using Gemini (synchronous).

        Uses the new google-genai SDK client.models.generate_content() API.
        Returns response object with .text property for backward compatibility.

        Args:
            prompt: The prompt text to send to the LLM

        Returns:
            Gemini response object with .text property

        Raises:
            utils.GeminiAPIError: If API call fails
        """
        try:
            self.logger.debug(f"Calling Gemini with model: {self.model_name}")

            # Call new Google GenAI SDK (returns response with .text property)
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )

            self.logger.debug(f"Gemini response received: {len(response.text)} characters")

            return response

        except Exception as e:
            self.logger.error(f"Gemini API call failed: {e}")
            raise utils.GeminiAPIError(f"Gemini API call failed: {e}")


# ============================================================================
# LLM PROVIDER FACTORY
# ============================================================================

class LLMProviderFactory:
    """
    Factory for creating LLM provider instances.

    Central point for provider selection logic. Supports:
    - "gemini": Google Gemini (free tier, default)
    - "azure": Azure OpenAI GPT-4o (enterprise)

    Usage:
        provider = LLMProviderFactory.get_provider("azure")
        response = provider.generate_content("Analyze this ticket...")
        print(response.text)
    """

    @staticmethod
    def get_provider(provider_name: str = "gemini"):
        """
        Get LLM provider instance based on name.

        Args:
            provider_name: Provider name ("gemini" or "azure")

        Returns:
            Configured LLM client (GeminiClient or AzureOpenAIClient)

        Raises:
            ValueError: If provider_name is invalid or credentials are missing

        Example:
            >>> provider = LLMProviderFactory.get_provider("azure")
            >>> response = provider.generate_content("Hello")
            >>> print(response.text)
        """
        logger = logging.getLogger("ticket_summarizer.llm_provider")

        provider_name_lower = provider_name.lower().strip()

        if provider_name_lower == "gemini":
            logger.info("Creating Gemini LLM provider")
            return GeminiClient()

        elif provider_name_lower == "azure":
            logger.info("Creating Azure OpenAI LLM provider")
            return AzureOpenAIClient()

        else:
            raise ValueError(
                f"Invalid model provider: '{provider_name}'. "
                f"Supported providers: 'gemini', 'azure'"
            )

    @staticmethod
    def validate_provider_credentials(provider_name: str) -> bool:
        """
        Validate that credentials exist for the specified provider.

        Does NOT validate that credentials are correct (only that they exist).
        Actual validation happens when creating the client.

        Args:
            provider_name: Provider name ("gemini" or "azure")

        Returns:
            True if credentials exist, False otherwise
        """
        provider_name_lower = provider_name.lower().strip()

        if provider_name_lower == "gemini":
            return bool(config.GEMINI_API_KEY)

        elif provider_name_lower == "azure":
            return bool(
                config.AZURE_OPENAI_ENDPOINT and
                config.AZURE_OPENAI_API_KEY and
                config.AZURE_OPENAI_DEPLOYMENT_NAME
            )

        return False
