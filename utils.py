"""
Utility functions for Zendesk Ticket Summarizer.
Includes logging, timezone conversion, HTML stripping, and retry logic.
"""

import os
import logging
import pytz
import html2text
from datetime import datetime
from functools import wraps
from typing import Optional
from bs4 import BeautifulSoup
import time
import asyncio

import config


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class ZendeskAPIError(Exception):
    """Raised when Zendesk API calls fail."""
    pass


class GeminiAPIError(Exception):
    """Raised when Gemini API calls fail."""
    pass


class TicketNotFoundError(Exception):
    """Raised when a ticket doesn't exist."""
    pass


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logger(name: str = "ticket_summarizer") -> logging.Logger:
    """
    Set up structured logging with both console and file handlers.

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists(config.LOG_DIR):
        os.makedirs(config.LOG_DIR)

    # Generate log filename with current date
    log_filename = f"app_{datetime.now().strftime('%Y%m%d')}.log"
    log_filepath = os.path.join(config.LOG_DIR, log_filename)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatters
    formatter = logging.Formatter(
        config.LOG_FORMAT,
        datefmt=config.LOG_DATE_FORMAT
    )

    # Console handler (INFO level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, config.LOG_LEVEL_CONSOLE))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (DEBUG level)
    file_handler = logging.FileHandler(log_filepath)
    file_handler.setLevel(getattr(logging, config.LOG_LEVEL_FILE))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# ============================================================================
# TIMEZONE CONVERSION
# ============================================================================

def convert_to_ist(utc_timestamp: str) -> str:
    """
    Convert UTC timestamp to IST (Indian Standard Time).

    Args:
        utc_timestamp: UTC timestamp string (ISO 8601 format)

    Returns:
        IST timestamp string in ISO 8601 format
    """
    try:
        # Parse the UTC timestamp
        if isinstance(utc_timestamp, str):
            # Handle various ISO 8601 formats
            dt_utc = datetime.fromisoformat(utc_timestamp.replace('Z', '+00:00'))
        else:
            dt_utc = utc_timestamp

        # Ensure it's timezone-aware (UTC)
        if dt_utc.tzinfo is None:
            dt_utc = pytz.utc.localize(dt_utc)

        # Convert to IST
        ist_tz = pytz.timezone(config.TIMEZONE_IST)
        dt_ist = dt_utc.astimezone(ist_tz)

        return dt_ist.isoformat()
    except Exception as e:
        logger = logging.getLogger("ticket_summarizer")
        logger.warning(f"Failed to convert timestamp '{utc_timestamp}' to IST: {e}")
        return utc_timestamp  # Return original if conversion fails


def get_current_ist_timestamp() -> str:
    """
    Get current timestamp in IST.

    Returns:
        Current IST timestamp in ISO 8601 format
    """
    ist_tz = pytz.timezone(config.TIMEZONE_IST)
    now_ist = datetime.now(ist_tz)
    return now_ist.isoformat()


# ============================================================================
# HTML/MARKDOWN STRIPPING
# ============================================================================

def strip_html(text: Optional[str]) -> str:
    """
    Strip HTML and markdown from text, returning clean plain text.

    Args:
        text: Raw text that may contain HTML or markdown

    Returns:
        Clean plain text
    """
    if not text:
        return ""

    try:
        # First, use BeautifulSoup to remove HTML tags
        soup = BeautifulSoup(text, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Use html2text to convert any remaining markdown
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.ignore_emphasis = False
        h.body_width = 0  # Don't wrap lines

        # Clean up excessive whitespace
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        lines = [line for line in lines if line]  # Remove empty lines

        return '\n'.join(lines)
    except Exception as e:
        logger = logging.getLogger("ticket_summarizer")
        logger.warning(f"Failed to strip HTML from text: {e}")
        return text  # Return original if stripping fails


# ============================================================================
# RETRY LOGIC
# ============================================================================

def retry_on_failure(max_retries: int = config.MAX_RETRIES,
                    delay: float = config.RETRY_DELAY_SECONDS):
    """
    Decorator to retry a function on failure with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds

    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = logging.getLogger("ticket_summarizer")
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )

            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = logging.getLogger("ticket_summarizer")
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )

            raise last_exception

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# FORMATTING UTILITIES
# ============================================================================

def format_comment_thread(comments: list) -> str:
    """
    Format comment thread into a readable string for LLM processing.

    Args:
        comments: List of comment dictionaries

    Returns:
        Formatted comment thread string
    """
    if not comments:
        return "No comments available."

    formatted_comments = []
    for i, comment in enumerate(comments, 1):
        author = comment.get('author_name', 'Unknown')
        created_at = comment.get('created_at', 'Unknown')
        body = strip_html(comment.get('body', ''))
        visibility = "Public" if comment.get('public', True) else "Internal"

        comment_str = f"""
Comment #{i} ({visibility})
Author: {author}
Time: {created_at}
---
{body}
---
"""
        formatted_comments.append(comment_str.strip())

    return "\n\n".join(formatted_comments)


def generate_output_filename() -> str:
    """
    Generate output filename with current date.

    Returns:
        Output filename (e.g., output_20250510.json)
    """
    date_str = datetime.now().strftime(config.OUTPUT_DATE_FORMAT)
    return f"{config.OUTPUT_FILENAME_PREFIX}{date_str}.json"


# ============================================================================
# CATEGORIZATION VALIDATION UTILITIES (Phase 2)
# ============================================================================

def validate_pod(pod_name: str) -> bool:
    """
    Validate POD name against the list of valid PODs.

    Used by categorizer to ensure LLM doesn't hallucinate POD names.
    Performs case-insensitive matching for robustness.

    Args:
        pod_name: POD name to validate (e.g., "Guidance", "WFE")

    Returns:
        True if POD name is valid, False otherwise

    Example:
        >>> validate_pod("Guidance")
        True
        >>> validate_pod("Invalid POD")
        False
        >>> validate_pod("guidance")  # Case insensitive
        True
    """
    if not pod_name:
        return False

    # Case-insensitive check against valid PODs list
    # Normalize both the input and the list for comparison
    pod_name_normalized = pod_name.strip()

    # Check exact match first (most common case)
    if pod_name_normalized in config.VALID_PODS:
        return True

    # Check case-insensitive match
    pod_name_lower = pod_name_normalized.lower()
    valid_pods_lower = [p.lower() for p in config.VALID_PODS]

    return pod_name_lower in valid_pods_lower


def validate_confidence(confidence: str) -> bool:
    """
    Validate confidence level against allowed values.

    Ensures LLM response contains valid confidence level.
    Only two levels allowed: "confident" or "not confident"

    Args:
        confidence: Confidence level string from LLM

    Returns:
        True if confidence is valid, False otherwise

    Example:
        >>> validate_confidence("confident")
        True
        >>> validate_confidence("not confident")
        True
        >>> validate_confidence("very confident")
        False
    """
    if not confidence:
        return False

    # Case-insensitive check against valid confidence levels
    confidence_normalized = confidence.strip().lower()
    valid_levels_lower = [c.lower() for c in config.CONFIDENCE_LEVELS]

    return confidence_normalized in valid_levels_lower


# ============================================================================
# DIAGNOSTICS ANALYSIS UTILITIES (Phase 3b)
# ============================================================================

def normalize_diagnostics_field(raw_value: Optional[str]) -> str:
    """
    Normalize the raw custom field value for "Was Diagnostic Panel used?"

    The Zendesk custom field (ID: 41001255923353) stores values as enum IDs:
    - "diagnostic_yes": Diagnostics was used → maps to "Yes"
    - "diagnostic_no": Diagnostics was NOT used → maps to "No"
    - Any other value (null, empty, NA, etc.) → maps to "Not Applicable"

    IMPORTANT: This is a Zendesk enum field, NOT a free-text field.
    The values are stored as enum IDs (diagnostic_yes/diagnostic_no), not display strings.

    Args:
        raw_value: Raw value from Zendesk custom field (can be str, None, or empty)

    Returns:
        Normalized value: "Yes", "No", or "Not Applicable"

    Example:
        >>> normalize_diagnostics_field("diagnostic_yes")
        'Yes'
        >>> normalize_diagnostics_field("diagnostic_no")
        'No'
        >>> normalize_diagnostics_field("N/A")
        'Not Applicable'
        >>> normalize_diagnostics_field(None)
        'Not Applicable'
        >>> normalize_diagnostics_field("")
        'Not Applicable'
    """
    if not raw_value:
        return "Not Applicable"

    # Strip whitespace and convert to lowercase for comparison
    normalized = str(raw_value).strip().lower()

    if not normalized:
        return "Not Applicable"

    # Map Zendesk enum IDs to display values
    if normalized == "diagnostic_yes":
        return "Yes"
    elif normalized == "diagnostic_no":
        return "No"
    else:
        # For any other value (NA, null, unknown, etc.), return "Not Applicable"
        # Log a debug message (not warning) since "NA" and empty values are expected
        logger = logging.getLogger("ticket_summarizer")
        logger.debug(
            f"Diagnostics custom field value '{raw_value}' is not 'diagnostic_yes' or 'diagnostic_no'. "
            f"Marking as 'Not Applicable'."
        )
        return "Not Applicable"


def validate_diagnostics_assessment(assessment: str) -> bool:
    """
    Validate diagnostics assessment value against allowed values.

    For "could_diagnostics_help", only three values are allowed:
    - "yes": Diagnostics could have helped
    - "no": Diagnostics could NOT have helped
    - "maybe": Unclear or ambiguous

    Args:
        assessment: Assessment value from LLM

    Returns:
        True if assessment is valid, False otherwise

    Example:
        >>> validate_diagnostics_assessment("yes")
        True
        >>> validate_diagnostics_assessment("no")
        True
        >>> validate_diagnostics_assessment("maybe")
        True
        >>> validate_diagnostics_assessment("probably")
        False
    """
    if not assessment:
        return False

    # Case-insensitive check against valid assessment values
    assessment_normalized = assessment.strip().lower()
    valid_assessments = ["yes", "no", "maybe"]

    return assessment_normalized in valid_assessments


def validate_diagnostics_usage(usage: str) -> bool:
    """
    Validate diagnostics usage value against allowed values.

    For "was_diagnostics_used", only three values are allowed:
    - "yes": Diagnostics was used
    - "no": Diagnostics was NOT used
    - "unknown": Cannot determine from ticket synthesis

    Args:
        usage: Usage value from LLM

    Returns:
        True if usage is valid, False otherwise

    Example:
        >>> validate_diagnostics_usage("yes")
        True
        >>> validate_diagnostics_usage("unknown")
        True
        >>> validate_diagnostics_usage("maybe")
        False
    """
    if not usage:
        return False

    # Case-insensitive check against valid usage values
    usage_normalized = usage.strip().lower()
    valid_usages = ["yes", "no", "unknown"]

    return usage_normalized in valid_usages
