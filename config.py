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

GEMINI_MODEL = "gemini-flash-latest"

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

# ============================================================================
# POD CATEGORIZATION CONFIGURATION (Phase 2)
# ============================================================================

# List of valid PODs for validation
VALID_PODS = [
    "WFE",
    "Guidance",
    "CMM",
    "Hub",
    "Analytics",
    "Insights",
    "Capture",
    "Mirror",
    "Desktop",
    "Mobile",
    "Labs",
    "Platform Services",
    "UI Platform"
]

# Confidence levels for categorization
CONFIDENCE_LEVELS = ["confident", "not confident"]

# POD Categorization Prompt Template
CATEGORIZATION_PROMPT_TEMPLATE = """You are a Whatfix support ticket categorization expert. Your task is to categorize a support ticket into ONE primary POD based on the ticket's synthesis summary and resolution.

CRITICAL INSTRUCTIONS:
- Base your decision ONLY on the synthesis summary and resolution provided
- DO NOT invent or assume information NOT present in the synthesis
- If the issue is ambiguous between multiple PODs, mark as "not confident"
- DO NOT categorize based on subject/description alone - use the synthesis which captures the full conversation

WHATFIX POD DEFINITIONS:

1. **WFE (Workflow Engine)**
Synthesis summary + resolution represents:
   - Element Detection, CSS selectors, XPath issues
   - Reselection requests
   - Latching problems (widgets, tooltips, smart tips, beacons, user actions, launchers, blockers not anchoring correctly)
   - Smart context issues (page specific context issues, content not being visible on one page or appearing on unexpected pages)
   - Visibility Rules
   - Diagnostics
   - Automation of steps - appearance, logic not working, automated execution not working

2. **Guidance**
Synthesis summary + resolution represents:
   - Flows (step-by-step walkthroughs); issues with building them, building branches, theme related issues, step completion rules, lack of understanding of when & how to use them, tool-tip positioning options & difficulties
   - Smart Tips (contextual tooltips); issues with building them, theme related issues, step completion rules, lack of understanding of when & how to use them, tool-tip positioning options & difficulties
   - Pop-ups (modals/announcements); issues with building them, theme related issues, lack of understanding of how to use, what precedence means, what sequencing means, how to link content, etc
   - Beacons (visual elements to grab attention); issues with building them, theme related issues, step completion rules, lack of understanding of when& how to use them, tool-tip positioning options & difficulties
   - Launchers (persistent buttons); issues with building them, theme related issues, step completion rules, lack of understanding of when& how to use them, tool-tip positioning options & difficulties
   - Triggers (auto-firing content); issues with building them, theme related issues, step completion rules, lack of understanding of when& how to use them, tool-tip positioning options & difficulties
   - Blockers (preventing progress); issues with building them, theme related issues, step completion rules, lack of understanding of when& how to use them, tool-tip positioning options & difficulties
   - Branching (conditional paths); issues with building them, theme related issues, step completion rules, lack of understanding of when& how to use them, tool-tip positioning options & difficulties
   - Multiformat exports

3. **CMM (Content & Metadata Management)**
   - Dashboard/Studio navigation
   - CLM (Content Lifecycle Management)
   - P2P (Push to Production)
   - Tags management
   - Auto Testing
   - Auto Translations
   - Versioning

4. **Hub**
   - DAP on OS (desktop widget)
   - Self Help / Task List
   - Surveys
   - Content Repository integration
   - Content Aggregation
   - QuickRead (AI summaries)
   - Static Content
   - Nudges

5. **Analytics**
   - Product analytics dashboards
   - Trends, funnels, user journeys
   - KPIs, charts, performance tracking

6. **Insights**
   - Ask Whatfix AI (NLP queries)
   - Cohorts
   - Event groups
   - User Journeys
   - Enterprise Insights

7. **Capture**
   - Autocapture (tracking interactions)
   - User Actions (custom events)
   - User Attributes (metadata)
   - User Identification
   - User Unification
   - Reserved Variables

8. **Mirror**
   - Application simulation builder
   - Interactive training replicas

9. **Desktop**
   - Native desktop app support (SAP GUI, Teams, Java apps)

10. **Mobile**
    - iOS/Android deployments

11. **Labs**
    - AI Assistant
    - AC reviewer
    - Intent Recognition
    - Enterprise Search

12. **Platform Services**
    - Integration Hub (Confluence, Workday, Amplitude)

13. **UI Platform**
    - Canary deployments

CATEGORIZATION LOGIC:
1. Read the synthesis summary and resolution CAREFULLY & THOROUGHLY
2. Identify key technical terms, features, or modules mentioned
3. Match these to the POD definitions above
4. If the issue spans multiple PODs, choose the PRIMARY one based on:
   - What was the root cause?
   - What area fixed the issue?
   - Which POD "owns" the main functionality involved?
5. If ambiguous between 2+ PODs, mark confidence as "not confident"

TICKET SYNTHESIS:
Subject: {subject}

Issue Reported: {issue_reported}

Root Cause: {root_cause}

Summary: {summary}

Resolution: {resolution}

CATEGORIZATION OUTPUT:
Provide your categorization in this EXACT format:

**Primary POD:**
[One of: WFE, Guidance, CMM, Hub, Analytics, Insights, Capture, Mirror, Desktop, Mobile, Labs, Platform Services, UI Platform]

**Reasoning:**
[2-3 sentences explaining why this POD was chosen based on the synthesis]

**Confidence:**
[Either "confident" or "not confident"]

**Confidence Reason:**
[Single sentence explaining why this confidence level was assigned]

**Alternative PODs:**
[Comma-separated list of other PODs this could belong to, or "None" if no alternatives]

**Alternative Reasoning:**
[1-2 sentences explaining why alternatives were considered, or "N/A" if no alternatives]"""
