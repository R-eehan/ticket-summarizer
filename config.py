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

# Zendesk Custom Field IDs
DIAGNOSTICS_CUSTOM_FIELD_ID = 41001255923353  # "Was Diagnostic Panel used?" field

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
GEMINI_MAX_CONCURRENT = 1    # Sequential for free tier (10 req/min limit)

# Request delay configuration
GEMINI_REQUEST_DELAY = 7     # Seconds between Gemini API calls (keeps under 10/min)

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

# ============================================================================
# DIAGNOSTICS ANALYSIS CONFIGURATION (Phase 3b)
# ============================================================================

# Diagnostics Analysis Prompt Template
DIAGNOSTICS_ANALYSIS_PROMPT = """You are a Whatfix product expert analyzing support tickets to determine if the "Diagnostics" feature could have helped resolve or identify the issue.

## WHAT IS DIAGNOSTICS?

Diagnostics is a self-serviceable troubleshooting tool available within Whatfix Studio AND as a standalone entity that helps authors understand why their content fails and provides actionable guidance for resolution.

**Diagnostics Capabilities:**
1. Real-time event-based step execution feedback
2. Visibility into the "why" of a step failure
3. Visibility into rule evaluation status for old AND advanced visibility rules
4. Available within Studio (one-stop-shop for authoring + testing)
5. Available as a standalone entity that can be spun up on specific user machines via a keyboard shortcut. This helps address issues where everything works on the author's machine but doesn't work on a specific end user's machine. Can help catch user specific issues

**What Diagnostics CAN Help With:**
- Visibility rule failures (conditions not met, incorrect logic like OR vs AND)
- Property mismatch (HTML properties don't match webpage elements)
- Element detection failures
- CSS selector failures - selectors added as part of the Visibility Rules OR Display Rules OR Element Precision rules failing during runtime
- Step execution failures
- Rule evaluation issues
- Content not displaying due to targeting/visibility issues
- Role tags not evaluating to true or false based on conditions applied

**What Diagnostics CANNOT Help With:**
- CSS selector construction/generation (technical request requiring support)
- Feature requests for new product capabilities
- Application-side bugs (not Whatfix-related)
- Data migration or bulk operations
- Integration setup (Confluence, Workday, etc.)
- Performance optimization requests
- Custom code implementation
- Product knowledge questions such as:
  - How do I create a flow/beacon/smart tip/blocker/launcher
  - Branching related questions
  - Pop-up sequencing
  - Content movement from & across stages such as Draft/Ready/Production
  - Deployment/delivery related questions

## YOUR TASK

Analyze the ticket synthesis and determine:
1. **Was Diagnostics used?** (by customer OR support team)
2. **Could Diagnostics have helped?** (to diagnose OR resolve the issue)

## CRITICAL INSTRUCTIONS

- Base your analysis ONLY on the synthesis summary, resolution, and custom field provided
- DO NOT invent or assume information not present in the ticket
- The custom field "was_diagnostics_used" may be unreliable (often "No" or "NA" even when it was used)
- If the issue is a **technical request** (e.g., "help me create a CSS selector"), classify as "no" for "could_diagnostics_help"
- If the issue is ambiguous or lacks detail, use "maybe" and mark confidence as "not confident"

## TICKET DATA

**Subject:** {subject}
**Issue Reported:** {issue_reported}
**Root Cause:** {root_cause}
**Summary:** {summary}
**Resolution:** {resolution}
**Custom Field (was_diagnostics_used):** {custom_field_value}

## ANALYSIS LOGIC

### Step 1: Was Diagnostics Used?
- Read the synthesis summary and resolution carefully
- Look for explicit mentions of "Diagnostics", "diagnose panel", "diagnostic panel", "rule evaluation", "visibility status", "step failure", "CSS selector failure"
- Check the custom field value (but don't trust it blindly - verify against synthesis)
- If synthesis confirms usage: "yes"
- If synthesis contradicts custom field or shows alternative debugging (console, manual): "no"
- If unclear: "unknown"

### Step 2: Could Diagnostics Have Helped?
- Identify the issue type:
  - **Troubleshooting issue?** (content not working, rules failing, elements not found) → Likely "yes" or "maybe"
  - **Technical request?** (help create selector, configure integration) → Likely "no"
  - **Feature request?** (new capability request) → "no"
  - **Product knowledge question?** (knowledge or how to questions) → "no"

- Match issue to Diagnostics capabilities:
  - Visibility rule failures → "yes" (Diagnostics shows rule evaluation)
  - Property mismatch → "yes" (Diagnostics shows property errors)
  - Element not found → "yes" (Diagnostics shows targeting issues)
  - CSS selector not working → "yes" (Diagnostics shows CSS failures)
  - CSS selector construction → "no" (Diagnostics doesn't generate selectors)
  - Generic "content not working" → "maybe" (need more context)

- Confidence:
  - "confident" if clear match or clear non-match
  - "not confident" if ambiguous, generic, or insufficient detail

### Step 3: Output Structure

Provide your analysis in the following exact JSON structure:

```json
{{
  "was_diagnostics_used": {{
    "llm_assessment": "yes|no|unknown",
    "confidence": "confident|not confident",
    "reasoning": "Explain why you classified this way, referencing synthesis and custom field"
  }},
  "could_diagnostics_help": {{
    "assessment": "yes|no|maybe",
    "confidence": "confident|not confident",
    "reasoning": "Explain why Diagnostics could/couldn't help. Be specific about which Diagnostics capability applies or why it doesn't apply. If custom field says 'No' but Diagnostics could have helped, explicitly mention this gap.",
    "diagnostics_capability_matched": ["capability 1", "capability 2"] or [],
    "limitation_notes": "Explain limitations if 'no' or 'maybe'" or null
  }},
  "metadata": {{
    "ticket_type": "troubleshooting|feature_request|technical_request|unclear"
  }}
}}
```

## EXAMPLES

**Example 1: Ticket 89618**
Subject: Conversation with Ramesh Rengarajan : Blocker Role Tags Setup
Issue: Blocker appearing for all users instead of targeted roles
Root Cause: Incorrect logic (OR instead of AND) in role tags visibility rules
Resolution: Updated role tags combination to AND, blocker appeared to targeted audience
Custom Field: "No"

**Analysis:**
```json
{{
  "was_diagnostics_used": {{
    "llm_assessment": "no",
    "confidence": "confident",
    "reasoning": "Custom field says 'No' and synthesis shows manual troubleshooting without mention of Diagnostics tool usage."
  }},
  "could_diagnostics_help": {{
    "assessment": "yes",
    "confidence": "confident",
    "reasoning": "The issue was a visibility rule logic error (OR vs AND). Diagnostics provides real-time visibility rule evaluation status, which would have shown that the rule was evaluating incorrectly and highlighted the logic discrepancy. The author could have identified and fixed this themselves without raising a ticket. The custom field shows Diagnostics was NOT used, representing a missed opportunity for self-service resolution.",
    "diagnostics_capability_matched": [
      "Visibility rule evaluation status",
      "Rule condition feedback"
    ],
    "limitation_notes": null
  }},
  "metadata": {{
    "ticket_type": "troubleshooting"
  }}
}}
```

**Example 2: Ticket 88591**
Subject: Flow Name: DO NOT DEAL - Integrity (Auto Case Creation for DQ team)
Issue: Author needed specific CSS selectors for Flow steps
Root Cause: Technical request for selector construction
Resolution: Whatfix support team constructed and added selectors
Custom Field: "No"

**Analysis:**
```json
{{
  "was_diagnostics_used": {{
    "llm_assessment": "no",
    "confidence": "confident",
    "reasoning": "Synthesis shows this was a technical request for support to generate selectors, not a troubleshooting scenario where Diagnostics would be used."
  }},
  "could_diagnostics_help": {{
    "assessment": "no",
    "confidence": "confident",
    "reasoning": "This was a CSS selector construction request, which is a technical task best handled by Whatfix support. Diagnostics does not generate or construct CSS selectors - it only diagnoses issues with existing content. The ticket type is a 'technical request', not a troubleshooting issue, making Diagnostics irrelevant here.",
    "diagnostics_capability_matched": [],
    "limitation_notes": "Diagnostics cannot generate or construct CSS selectors; this requires technical expertise from support team."
  }},
  "metadata": {{
    "ticket_type": "technical_request"
  }}
}}
```

Focus on accuracy and avoid hallucination. Only use information from the synthesis."""
