"""
OpenTelemetry Instrumentation Setup for Ticket Summarizer - Phase 4

This module provides centralized OpenTelemetry instrumentation configuration
for the ticket-summarizer application. It implements a three-tier instrumentation
strategy to enable comprehensive observability and tracing.

Phase 4: Arize AX Cloud Integration
- Tier 1: LLM Provider Auto-Instrumentation (Google GenAI, Azure OpenAI)
- Tier 2: Business Logic Manual Spans (synthesis, categorization, diagnostics)
- Tier 3: API Auto-Instrumentation (Zendesk HTTP calls)

Architecture Decision: OpenTelemetry (OTEL) with Arize AX Cloud Backend
- Uses arize-otel convenience wrapper for simplified Arize AX integration
- OpenInference instrumentors for LLM-specific semantic conventions
- All traces exported to Arize AX cloud (US region)
"""

import os
import logging
from opentelemetry import trace

import config


def setup_instrumentation():
    """
    Initialize OpenTelemetry instrumentation with Arize AX cloud backend.

    This function sets up:
    1. Arize AX tracer provider with cloud export (via arize.otel.register)
    2. Auto-instrumentation for LLM providers (Tier 1)
    3. Auto-instrumentation for HTTP client (Tier 3)

    Call this ONCE at application startup (in main.py before any LLM/API calls).

    Environment Variables:
        ARIZE_SPACE_ID: Your Arize Space ID (required)
        ARIZE_API_KEY: Your Arize API Key (required)
        ARIZE_PROJECT_NAME: Project name for grouping traces (default: "ticket-analysis")
        ENABLE_TRACING: Set to 'false' to disable tracing (default: 'true')
        ENVIRONMENT: Deployment environment (default: 'local')

    Returns:
        TracerProvider instance if successful, None otherwise

    Example:
        >>> from instrumentation import setup_instrumentation
        >>> setup_instrumentation()  # Call at app startup
        [Instrumentation] ✅ Arize AX instrumentation enabled
          - Project: ticket-analysis
          - Endpoint: Arize US Cloud
    """
    logger = logging.getLogger("ticket_summarizer.instrumentation")

    # Check if tracing is enabled via environment variable
    enable_tracing = os.getenv("ENABLE_TRACING", "true").lower() == "true"

    if not enable_tracing:
        logger.info("Tracing disabled via ENABLE_TRACING environment variable")
        print("[Instrumentation] Tracing disabled via ENABLE_TRACING")
        return None

    # Validate Arize credentials
    if not config.ARIZE_SPACE_ID or not config.ARIZE_API_KEY:
        logger.warning(
            "Arize credentials not configured (ARIZE_SPACE_ID or ARIZE_API_KEY missing). "
            "Skipping instrumentation setup. Application will run without observability."
        )
        print("[Instrumentation] ⚠️  Arize credentials not configured - skipping instrumentation")
        print("[Instrumentation]    Set ARIZE_SPACE_ID and ARIZE_API_KEY in .env to enable tracing")
        return None

    try:
        # ============================================================================
        # STEP 1: Register with Arize AX Cloud
        # ============================================================================
        # arize.otel.register() is a convenience wrapper that:
        # - Creates TracerProvider with service metadata
        # - Configures OTLP exporter to Arize cloud endpoint
        # - Handles authentication with Space ID & API Key
        # - Returns configured TracerProvider for instrumentors
        from arize.otel import register, Endpoint

        logger.info("Initializing Arize AX instrumentation")

        tracer_provider = register(
            space_id=config.ARIZE_SPACE_ID,
            api_key=config.ARIZE_API_KEY,
            project_name=config.ARIZE_PROJECT_NAME,
            endpoint=Endpoint.ARIZE  # US region
        )

        logger.info(f"Arize AX tracer provider registered: project={config.ARIZE_PROJECT_NAME}")

        # ============================================================================
        # STEP 2: Auto-Instrument LLM Providers (Tier 1)
        # ============================================================================
        # OpenInference provides OTEL instrumentors for LLM SDKs
        # These automatically capture LLM calls, token counts, latency, and costs
        #
        # IMPORTANT: Pass tracer_provider to ensure traces go to Arize AX

        # Instrument OpenAI/Azure OpenAI
        try:
            from openinference.instrumentation.openai import OpenAIInstrumentor
            OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
            logger.info("OpenAI/Azure OpenAI auto-instrumented (Tier 1)")
            print("[Instrumentation] ✓ OpenAI/Azure OpenAI auto-instrumented")
        except ImportError as e:
            logger.warning(f"OpenAI instrumentor not available: {e}")
            print(f"[Instrumentation] ⚠️  OpenAI instrumentor not available: {e}")

        # Instrument Google GenAI (new unified SDK)
        try:
            from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
            GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
            logger.info("Google GenAI auto-instrumented (Tier 1)")
            print("[Instrumentation] ✓ Google GenAI (Gemini) auto-instrumented")
        except ImportError as e:
            logger.warning(f"Google GenAI instrumentor not available: {e}")
            print(f"[Instrumentation] ⚠️  Google GenAI instrumentor not available: {e}")
            print("[Instrumentation]    Note: Install with 'pip install openinference-instrumentation-google-genai'")

        # ============================================================================
        # STEP 3: Auto-Instrument HTTP Client (Tier 3)
        # ============================================================================
        # Instrument aiohttp HTTP client to capture Zendesk API calls
        try:
            from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
            AioHttpClientInstrumentor().instrument(tracer_provider=tracer_provider)
            logger.info("Aiohttp HTTP client auto-instrumented (Tier 3)")
            print("[Instrumentation] ✓ Aiohttp HTTP client auto-instrumented")
        except ImportError as e:
            logger.warning(f"Aiohttp instrumentor not available: {e}")
            print(f"[Instrumentation] ⚠️  Aiohttp instrumentor not available: {e}")

        # ============================================================================
        # STEP 4: Success Message
        # ============================================================================
        logger.info("OpenTelemetry instrumentation initialized successfully")
        print("\n[Instrumentation] ✅ Arize AX instrumentation enabled")
        print(f"  - Project: {config.ARIZE_PROJECT_NAME}")
        print(f"  - Endpoint: Arize US Cloud")
        print(f"  - Environment: {os.getenv('ENVIRONMENT', 'local')}")
        print("  - Tier 1 (LLM): Auto-instrumented (OpenAI, Google GenAI)")
        print("  - Tier 2 (Business Logic): Manual spans available (synthesis, categorization, diagnostics)")
        print("  - Tier 3 (Zendesk API): Auto-instrumented (aiohttp)")
        print(f"  - View traces: https://app.arize.com/organizations/{config.ARIZE_SPACE_ID}/spaces\n")

        return tracer_provider

    except ImportError as e:
        # arize-otel package not installed
        logger.error(f"Failed to import Arize OTEL package: {e}")
        print(f"[Instrumentation] ✗ Failed to import arize-otel: {e}")
        print("[Instrumentation]    Install with: pip install arize-otel")
        print("[Instrumentation]    Application will continue without tracing")
        return None

    except Exception as e:
        # If instrumentation setup fails, log the error but don't crash the application
        # This allows the app to continue running without tracing (graceful degradation)
        logger.error(f"Failed to initialize OpenTelemetry instrumentation: {e}")
        print(f"[Instrumentation] ✗ Failed to initialize: {e}")
        print("[Instrumentation]    Application will continue without tracing")
        return None


def get_tracer(name: str):
    """
    Get a tracer instance for creating manual spans (Tier 2).

    Use this function in business logic modules (synthesizer, categorizer, diagnostics)
    to obtain a tracer for creating custom spans.

    Args:
        name: Tracer name (typically __name__ of the calling module)

    Returns:
        Tracer instance

    Example:
        >>> # In synthesizer.py
        >>> from instrumentation import get_tracer
        >>> tracer = get_tracer(__name__)
        >>> with tracer.start_as_current_span("synthesize_ticket") as span:
        ...     span.set_attribute("ticket_id", "12345")
        ...     # ... synthesis logic ...
    """
    return trace.get_tracer(name)
