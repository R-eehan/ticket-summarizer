"""
Configuration module for Zendesk Ticket Summarizer.
Loads environment variables and defines constants for the application.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# ZENDESK CONFIGURATION
# ============================================================================

ZENDESK_SUBDOMAIN = os.getenv("ZENDESK_SUBDOMAIN", "whatfix")
ZENDESK_EMAIL = os.getenv("ZENDESK_EMAIL", "avinash.pai@whatfix.com")
ZENDESK_API_KEY = os.getenv("ZENDESK_API_KEY")

# Validate Zendesk credentials
if not ZENDESK_API_KEY:
    raise ValueError("ZENDESK_API_KEY environment variable is not set")

# Zendesk API endpoints
ZENDESK_BASE_URL = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2"
ZENDESK_TICKET_URL = f"{ZENDESK_BASE_URL}/tickets/{{ticket_id}}.json"
ZENDESK_COMMENTS_URL = f"{ZENDESK_BASE_URL}/tickets/{{ticket_id}}/comments.json"

# ============================================================================
# GEMINI CONFIGURATION
# ============================================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Validate Gemini credentials
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set")

GEMINI_MODEL = "gemini-2.0-flash-exp"

# ============================================================================
# RATE LIMITING CONFIGURATION
# ============================================================================

# Maximum concurrent requests
ZENDESK_MAX_CONCURRENT = 10  # Conservative for Enterprise plan
GEMINI_MAX_CONCURRENT = 5    # Respect Gemini API limits

# Retry configuration
MAX_RETRIES = 1              # One retry attempt
RETRY_DELAY_SECONDS = 2      # Delay between retries

# Timeout configuration
REQUEST_TIMEOUT_SECONDS = 30

# ============================================================================
# LLM PROMPT TEMPLATE
# ============================================================================

LLM_PROMPT_TEMPLATE = """You are an expert support ticket analyst. Your task is to analyze a Zendesk support ticket including its subject, description, and ALL comments exchanged between the customer and support agents.

CRITICAL INSTRUCTIONS:
- You MUST read and analyze EVERY single comment in the ticket thread thoroughly
- Pay close attention to the evolution of the conversation to understand the ACTUAL issue, not just the initial report
- The issue initially reported may differ from the actual problem discovered during troubleshooting
- The resolution should reflect what ACTUALLY fixed the problem, not just what was attempted

TICKET DATA:
Subject: {subject}

Description: {description}

COMPLETE COMMENT THREAD:
{all_comments}

ANALYSIS REQUIREMENTS:
Provide your analysis in the following exact structure:

**Issue Reported:**
[One-liner describing what the customer initially reported or the actual issue identified]

**Root Cause:**
[One-liner describing the underlying technical cause of the issue]

**Summary:**
[3-4 line paragraph that captures the essence of the entire ticket, including key troubleshooting steps, turning points in the investigation, and how the solution was reached]

**Resolution:**
[One-liner that clearly states how the issue was actually resolved]

Focus on accuracy and technical precision. Extract information only from the provided data."""

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOG_DIR = "logs"
LOG_LEVEL_CONSOLE = "INFO"
LOG_LEVEL_FILE = "DEBUG"
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ============================================================================
# TIMEZONE CONFIGURATION
# ============================================================================

TIMEZONE_IST = "Asia/Kolkata"

# ============================================================================
# OUTPUT CONFIGURATION
# ============================================================================

OUTPUT_FILENAME_PREFIX = "output_"
OUTPUT_DATE_FORMAT = "%Y%m%d"  # Format: output_20250510.json
