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

# Engineering Escalation Custom Field IDs (Phase 5)
# Cross Team field - indicates if ticket was escalated to Engineering
# Values: "cross_team_n/a" (not escalated) or "cross_team_succ" (escalated to SUCC engineering)
CROSS_TEAM_FIELD_ID = 48570811421977

# JIRA Ticket field - contains link to JIRA ticket if escalated
# Only appears in Zendesk UI if Cross Team field = "cross_team_succ"
# Value example: "https://whatfix.atlassian.net/browse/SUCC-36126"
JIRA_TICKET_FIELD_ID = 360024807472

# Root Cause field - support agent's documented root cause (Phase 6 Enhancement)
# Text field, free-form, quality varies by agent. Used to ENRICH (not replace) LLM-inferred root cause
ROOT_CAUSE_FIELD_ID = 360024846991

# ============================================================================
# GEMINI CONFIGURATION
# ============================================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Validate Gemini credentials
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set")

GEMINI_MODEL = "gemini-flash-latest"

# ============================================================================
# AZURE OPENAI CONFIGURATION (Phase 3c)
# ============================================================================

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

# Validate Azure credentials (only if Azure is chosen as provider)
# Validation happens at runtime in llm_provider.py to allow Gemini-only usage
# without requiring Azure credentials

# Default model provider (can be overridden via CLI)
DEFAULT_MODEL_PROVIDER = "gemini"

# ============================================================================
# ARIZE AX CONFIGURATION (Phase 4: Observability)
# ============================================================================

ARIZE_SPACE_ID = os.getenv("ARIZE_SPACE_ID")
ARIZE_API_KEY = os.getenv("ARIZE_API_KEY")
ARIZE_PROJECT_NAME = os.getenv("ARIZE_PROJECT_NAME", "ticket-analysis")

# Note: Instrumentation is optional. If credentials are not provided,
# the application will run without observability tracing.

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
# DIAGNOSTICS ANALYSIS CONFIGURATION (Phase 3b + Phase 6 Triage/Fix Enhancement)
# ============================================================================

# Diagnostics Analysis Prompt Template
DIAGNOSTICS_ANALYSIS_PROMPT = """You are a Whatfix product expert analyzing support tickets to determine if the "Diagnostics" feature could have helped with the issue.

## WHAT IS DIAGNOSTICS?

Diagnostics is a self-serviceable troubleshooting tool within Whatfix Studio that helps authors understand why their content fails and provides actionable guidance for resolution.

---

## CRITICAL: ANTI-HALLUCINATION RULES

**BEFORE WRITING ANY REASONING, YOU MUST FOLLOW THESE RULES:**

1. **ONLY reference information EXPLICITLY present in the synthesis**
   - Do NOT mention "visibility rules" unless synthesis explicitly mentions visibility rules
   - Do NOT mention "CSS selector in display rules" unless synthesis explicitly mentions this
   - Do NOT assume technical details not stated in the ticket

2. **Use EXACT terminology from synthesis**
   - If synthesis says "element not found" → use "element not found"
   - Do NOT translate to "CSS selector failure" unless explicitly stated
   - Do NOT assume "selector added" when synthesis says "selector needed"

3. **When uncertain, default to "maybe" with "not confident"**
   - Better to acknowledge uncertainty than hallucinate certainty
   - If synthesis lacks detail, say "insufficient detail" not make assumptions

4. **CHECK your reasoning against the synthesis**
   - Before outputting, verify EACH claim in your reasoning appears in the input
   - If you cannot quote the synthesis to support a claim, remove that claim

---

## DIAGNOSTICS CAPABILITIES (What It CAN Detect)

**Detection Capabilities (for TRIAGE):**

1. **Element Detection Failures**
   - Property mismatch (HTML properties changed/not found on page)
   - CSS selector not found (selector added in visibility/display rules but not evaluating)
   - Auto-tag condition failures

2. **Rule Evaluation Status**
   - Display rule conditions not met (shows WHICH conditions failed)
   - Visibility rule conditions not met (shows rule evaluation result true/false)
   - Role tags evaluation status

3. **Content Status**
   - **Occurrence exhausted** (widget already shown max times to user)
   - **Precedence conflict** (another widget took priority)
   - **Content stage** (Draft/Ready/Production) - shows which stage content evaluates from

4. **Step Execution**
   - Step completion status (passed/failed)
   - Element-related step failures
   - Flow step sequence issues

5. **User Action Status**
   - User Action evaluation status (found/not found)
   - Linked content display (shows associated content when UA triggers)

**Fix Recommendation Capabilities (what Diagnostics can SUGGEST):**
- "Try reselecting the element" (for element detection failures)
- "Increase occurrence count" (for occurrence exhausted)
- "Check visibility rule conditions" (for rule failures)
- "Contact support for assistance" (when issue is complex)

---

## DIAGNOSTICS LIMITATIONS (What It CANNOT Do)

**Detection Limitations:**
- **Latching issues** (element found but WRONG element)
  → Diagnostics shows "element found" even if it's the WRONG element. Cannot detect incorrect latching.
- **Branching condition failures in Flows**
  → Diagnostics doesn't cover Flow branching logic evaluation
- **WHY automated steps fail** (only THAT they failed)
  → Can show step failed, cannot diagnose application-side reasons
- **Timing issues in rule evaluation**
  → Cannot show rules evaluated "too early" before page loaded

**Fix Recommendation Limitations:**
- **CSS selector construction/generation**
  → Can show selector failed, CANNOT suggest what selector to use
- **CSS selector modification**
  → CANNOT recommend how to fix an incorrect selector
- **Use case implementation guidance**
  → CANNOT help with "how do I achieve X?" questions

---

## YOUR TASK: TRIAGE vs FIX Assessment

You MUST evaluate TWO dimensions SEPARATELY:

### 1. TRIAGE Assessment (Identification)
**Question: "Could Diagnostics help the author UNDERSTAND what's failing?"**

| Scenario | triage_assessment |
|----------|------------------|
| Issue involves visibility/display rule not evaluating | "yes" |
| Issue involves element not being found | "yes" |
| Issue involves step execution failure | "yes" |
| Issue involves occurrence exhausted | "yes" |
| Issue is pure use case implementation (no failure involved) | "no" |
| Issue involves latching (wrong element found) | "maybe" |
| Issue involves branching conditions in flows | "no" |
| Unclear from synthesis | "maybe" |

### 2. FIX Assessment (Resolution)
**Question: "Could Diagnostics RECOMMEND a fix the author can self-service?"**

| Scenario | fix_assessment |
|----------|---------------|
| Fix is "reselect element" | "yes" |
| Fix is "increase occurrence count" | "yes" |
| Fix is "adjust visibility rule logic" | "maybe" |
| Fix is "add/construct CSS selector" | "no" |
| Fix is "modify existing CSS selector" | "no" |
| Fix requires Support intervention | "no" |
| Fix requires Engineering escalation | "no" |

**IMPORTANT:** The overall_assessment will be DERIVED programmatically. Do NOT generate it yourself.

---

## TICKET DATA

**Subject:** {subject}
**Issue Reported (LLM-inferred):** {issue_reported}
**Root Cause (LLM-inferred):** {root_cause}
**Summary:** {summary}
**Resolution:** {resolution}
**Custom Field (was_diagnostics_used):** {custom_field_value}

**Support Agent's Root Cause (from Zendesk field):** {support_root_cause}
_Note: Use this to validate/enrich your analysis. If it differs from LLM-inferred root cause, acknowledge both._

**ESCALATION STATUS:**
- **Escalated to Engineering:** {is_escalated}
- **JIRA Ticket ID:** {jira_ticket_id}

---

## ANALYSIS LOGIC

### Step 1: Was Diagnostics Used?
- Look for explicit mentions of "Diagnostics", "diagnose panel", "diagnostic panel", "rule evaluation status"
- Check custom field value (but verify against synthesis)
- If synthesis confirms usage: "yes"
- If no evidence of usage: "no"
- If unclear: "unknown"

### Step 2: Triage Assessment
- Can Diagnostics help IDENTIFY/DETECT what's failing?
- Match issue type to detection capabilities above
- Consider: Would seeing the diagnostic information help the author understand the problem?

### Step 3: Fix Assessment
- Can Diagnostics RECOMMEND a fix the author can execute themselves?
- If fix is "reselect" or "increase occurrence" → "yes"
- If fix requires selector construction/modification → "no"
- If fix requires support expertise → "no"

### Step 4: Handle Escalation Context
**If is_escalated = True:**
- triage_assessment: Could still be "yes" if Diagnostics could identify the issue
- fix_assessment: Almost always "no" (product bugs need engineering fixes)
- Note in reasoning: "Escalated as product bug - Diagnostics cannot resolve but may have helped identify"

---

## OUTPUT STRUCTURE

Provide your analysis in this EXACT JSON structure:

```json
{{
  "was_diagnostics_used": {{
    "llm_assessment": "yes|no|unknown",
    "confidence": "confident|not confident",
    "reasoning": "Explain based on synthesis evidence"
  }},
  "could_diagnostics_help": {{
    "triage_assessment": "yes|no|maybe",
    "triage_reasoning": "Why Diagnostics could/couldn't help IDENTIFY the issue. Reference specific detection capabilities.",
    "fix_assessment": "yes|no|maybe",
    "fix_reasoning": "Why Diagnostics could/couldn't RECOMMEND a self-service fix. Be explicit about what the fix was.",
    "confidence": "confident|not confident",
    "diagnostics_capability_matched": ["capability 1", "capability 2"] or [],
    "limitation_notes": "Explain specific limitations that apply" or null
  }},
  "metadata": {{
    "ticket_type": "troubleshooting|feature_request|technical_request|unclear"
  }}
}}
```

---

## EXAMPLES

**Example 1: Technical Request - Selector Needed (triage=yes, fix=no)**

Subject: "Flow step not working, need CSS selector"
Summary: Step 7 of flow failing, support added CSS selector to fix
Root Cause: Missing selector for step
Support Root Cause: "Element detection failure - added unique CSS selector"

```json
{{
  "was_diagnostics_used": {{
    "llm_assessment": "no",
    "confidence": "confident",
    "reasoning": "Synthesis shows manual troubleshooting by support team without mention of Diagnostics."
  }},
  "could_diagnostics_help": {{
    "triage_assessment": "yes",
    "triage_reasoning": "Diagnostics would show step 7 failing due to element detection failure, helping author understand WHAT is failing before contacting support.",
    "fix_assessment": "no",
    "fix_reasoning": "The fix required support to construct and add a CSS selector. Diagnostics cannot generate or recommend CSS selectors - it can only show that element detection failed.",
    "confidence": "confident",
    "diagnostics_capability_matched": ["Element detection failures", "Step execution status"],
    "limitation_notes": "Diagnostics cannot construct CSS selectors; this requires technical expertise from support team."
  }},
  "metadata": {{
    "ticket_type": "troubleshooting"
  }}
}}
```

**Example 2: Reselection Fix (triage=yes, fix=yes)**

Subject: "Smart Tip not appearing after page update"
Summary: Element detection failure, resolved by reselecting element
Root Cause: Page DOM changed, original selection invalid
Support Root Cause: "DOM change broke element selection"

```json
{{
  "was_diagnostics_used": {{
    "llm_assessment": "no",
    "confidence": "confident",
    "reasoning": "No mention of Diagnostics in synthesis. Issue resolved through reselection."
  }},
  "could_diagnostics_help": {{
    "triage_assessment": "yes",
    "triage_reasoning": "Diagnostics would show element not found, indicating the original selection is no longer valid.",
    "fix_assessment": "yes",
    "fix_reasoning": "Diagnostics recommends 'try reselecting element' for element detection failures. Author could self-service this fix without support.",
    "confidence": "confident",
    "diagnostics_capability_matched": ["Element detection failures", "Property mismatch detection"],
    "limitation_notes": null
  }},
  "metadata": {{
    "ticket_type": "troubleshooting"
  }}
}}
```

**Example 3: Use Case Implementation (triage=no, fix=no)**

Subject: "Need help creating window variable for user segmentation"
Summary: Support helped configure SOQL query and AC code for variable
Root Cause: Technical implementation request
Support Root Cause: "Customer needed new window variable setup"

```json
{{
  "was_diagnostics_used": {{
    "llm_assessment": "no",
    "confidence": "confident",
    "reasoning": "This was a use case implementation request, not a troubleshooting scenario."
  }},
  "could_diagnostics_help": {{
    "triage_assessment": "no",
    "triage_reasoning": "This is a use case implementation request, not a troubleshooting scenario. No failure to diagnose - the author needed help building something new.",
    "fix_assessment": "no",
    "fix_reasoning": "Diagnostics cannot help with technical implementation tasks like creating window variables or configuring AC code.",
    "confidence": "confident",
    "diagnostics_capability_matched": [],
    "limitation_notes": "Use case implementation requests are outside Diagnostics scope."
  }},
  "metadata": {{
    "ticket_type": "technical_request"
  }}
}}
```

**Example 4: Latching Issue (triage=maybe, fix=no)**

Subject: "User Action tracking wrong element"
Summary: UA latching onto similar element in DOM, support added unique selector
Root Cause: Non-unique DOM structure causing incorrect element match
Support Root Cause: "Element latching to wrong target - added unique CSS selector"

```json
{{
  "was_diagnostics_used": {{
    "llm_assessment": "no",
    "confidence": "confident",
    "reasoning": "No mention of Diagnostics. Issue identified through manual investigation."
  }},
  "could_diagnostics_help": {{
    "triage_assessment": "maybe",
    "triage_reasoning": "Diagnostics would show 'element found' but CANNOT detect if it's the WRONG element. It provides partial visibility - author would see element found successfully, which is misleading for latching issues.",
    "fix_assessment": "no",
    "fix_reasoning": "The fix required adding a unique CSS selector. Diagnostics cannot detect latching issues or recommend unique selectors to fix them.",
    "confidence": "confident",
    "diagnostics_capability_matched": [],
    "limitation_notes": "Diagnostics cannot detect latching issues (wrong element found) - it only shows element found/not found status."
  }},
  "metadata": {{
    "ticket_type": "troubleshooting"
  }}
}}
```

**Example 5: Occurrence Exhausted (triage=yes, fix=yes)**

Subject: "Pop-up not showing after page refresh"
Summary: Pop-up occurrence setting was set to 1, preventing re-display
Root Cause: Occurrence count exhausted
Support Root Cause: "Occurrence limit reached"

```json
{{
  "was_diagnostics_used": {{
    "llm_assessment": "no",
    "confidence": "confident",
    "reasoning": "No mention of Diagnostics. Support identified occurrence setting issue."
  }},
  "could_diagnostics_help": {{
    "triage_assessment": "yes",
    "triage_reasoning": "Diagnostics shows occurrence exhausted status, which would have directly identified that the pop-up already reached its display limit.",
    "fix_assessment": "yes",
    "fix_reasoning": "Diagnostics recommends increasing occurrence count for this issue. Author could self-service by adjusting the occurrence setting.",
    "confidence": "confident",
    "diagnostics_capability_matched": ["Occurrence exhausted detection", "Content status visibility"],
    "limitation_notes": null
  }},
  "metadata": {{
    "ticket_type": "troubleshooting"
  }}
}}
```

---

Focus on accuracy. Only use information from the synthesis. When in doubt, use "maybe" with "not confident"."""
