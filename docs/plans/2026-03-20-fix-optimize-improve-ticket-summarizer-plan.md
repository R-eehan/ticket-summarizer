---
title: "Fix, Optimize & Improve Ticket Summarizer"
type: fix/feat/refactor
date: 2026-03-20
---

# Fix, Optimize & Improve Ticket Summarizer

## Overview

The Zendesk Ticket Summarizer is currently broken on Azure (the primary provider) and has significant performance/quality improvement opportunities. This plan addresses 23 issues across 4 phases: critical bug fixes, performance optimization for 200-500 ticket runs, LLM output quality improvements via structured outputs and better prompts, and code quality polish.

## Problem Statement

1. **Azure is broken** — `max_tokens` parameter rejected by newer GPT-4o deployments, outdated API version, config crashes without Gemini key
2. **Performance is crippled** — 7-second delay applied to Azure (117 min wasted on 500 tickets), sequential diagnostics processing, semaphore=1 everywhere
3. **Output quality can improve** — fragile regex parsing, no structured outputs, no few-shot examples, no temperature control on Gemini
4. **Code quality debt** — misleading class/exception names, mixed async patterns, broken stats tracking

## Research Summary

Findings from 4 parallel research agents (Azure API, Gemini API, LLM prompt engineering, Python async patterns):

| Topic | Key Finding | Source |
|-------|-------------|--------|
| Azure `max_completion_tokens` | Required for newer GPT-4o deployments. Introduced in API `2024-09-01-preview`. | [Microsoft docs](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle) |
| Azure API version `2024-02-01` | Approaching retirement. Missing: structured outputs, `max_completion_tokens`, batch API. Latest GA: `2024-10-21`. | [Azure API lifecycle](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle) |
| Azure structured outputs | Supported since `2024-08-01-preview`. JSON schema enforcement via `response_format`. | [Azure structured outputs](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs) |
| Azure rate limits (Tier 1) | GPT-4o: 300K TPM, ~300 RPM. Safe concurrency: 5-10 requests. | [Azure quotas](https://learn.microsoft.com/en-us/azure/foundry/openai/quotas-limits) |
| Gemini `gemini-flash-latest` | NOT in current official model list. Use `gemini-2.5-flash` (stable) or `gemini-3.1-flash-lite-preview` (newest). | [Gemini models](https://ai.google.dev/gemini-api/docs/models) |
| Gemini structured outputs | Supported via `response_mime_type: "application/json"` + Pydantic `response_schema` in `google-genai` SDK. | [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output) |
| Gemini 3.1 Flash-Lite free tier | 15 RPM, 1000 RPD, 250K TPM. 4-second delay is safe. | [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) |
| Gemini 2.5 Flash free tier | 10 RPM, 250 RPD. 7-second delay required. | [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) |
| Gemini temperature default | 1.0 (too high for analytical tasks). Should be 0.2 for 2.5 models. Gemini 3.x models should keep 1.0. | [Google prompting strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies) |
| `google-genai` SDK | v1.68.0 is latest (March 2026). Old `google-generativeai` deprecated permanently Nov 30, 2025. | [PyPI](https://pypi.org/project/google-genai/) |
| Regex parsing fragility | Industry consensus: use API-level structured outputs. Regex breaks within days as models drift. | [OpenAI structured outputs](https://openai.com/index/introducing-structured-outputs-in-the-api/) |
| "Lost in the middle" problem | 39% performance drop on multi-turn threads without structural markers. | [arXiv 2505.06120](https://arxiv.org/html/2505.06120v1) |
| Few-shot CoT for classification | Outperforms zero-shot for ambiguous multi-class classification. | [Prompting Guide](https://www.promptingguide.ai/techniques/cot) |
| Anti-hallucination: cite evidence | Requiring LLMs to quote source text reduces hallucination beyond general instructions. | [Lakera guide](https://www.lakera.ai/blog/guide-to-hallucinations-in-large-language-models) |
| `asyncio.to_thread` vs `run_in_executor` | `to_thread` is preferred in Python 3.9+ (propagates contextvars, simpler API). | [Python docs](https://docs.python.org/3/library/asyncio-task.html) |
| `openai` SDK v2.0.0 | Breaking change Sep 2025. Pin to `>=1.42.0,<2.0.0` for stability with `AzureOpenAI()`. | [GitHub releases](https://github.com/openai/openai-python/releases) |

## Technical Approach

### Architecture

The existing modular architecture (fetcher → synthesizer → categorizer/diagnostics → exporter) is sound. Changes are primarily within modules, not to the pipeline structure. Key architectural changes:

1. **Provider-aware configuration** — Rate limiting, concurrency, and delays become provider-specific
2. **Shared rate limiter** — For `both` mode, a single rate limiter per provider prevents doubling request rates
3. **Structured output schemas** — Pydantic models become the source of truth for LLM output shape
4. **Lazy credential validation** — Credentials validated at provider instantiation, not at import time

```
┌──────────────────────────────────────────────────────────────┐
│                    config.py (CHANGED)                        │
│  - Lazy credential validation                                │
│  - Provider-specific rate limiting config                     │
│  - Configurable model names via .env                         │
│  - GEMINI_MODEL from .env (default: gemini-2.5-flash)        │
│  - AZURE_OPENAI_API_VERSION default: 2024-10-21              │
└──────────────────────┬───────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│              llm_provider.py (CHANGED)                        │
│  - max_completion_tokens (Azure)                              │
│  - temperature config (Gemini: 0.2)                           │
│  - Structured output support (response_format / response_schema)│
│  - Provider-specific generate_content() interface             │
│  - Shared rate limiter factory                                │
└──────────┬───────────────────────┬───────────────────────────┘
           │                       │
┌──────────▼──────────┐ ┌─────────▼──────────┐ ┌──────────────┐
│ synthesizer.py      │ │ categorizer.py     │ │ diagnostics  │
│ (CHANGED)           │ │ (CHANGED)          │ │ _analyzer.py │
│ - asyncio.to_thread │ │ - Use factory      │ │ (CHANGED)    │
│ - Provider delays   │ │ - asyncio.to_thread│ │ - gather()   │
│ - Pydantic schemas  │ │ - Pydantic schemas │ │ - Pydantic   │
│ - support_root_cause│ │ - Few-shot examples│ │   schemas    │
└─────────────────────┘ └────────────────────┘ └──────────────┘
```

### Implementation Phases

---

## Phase 1: Fix Azure Blockers (P0 — Get it running)

**Goal:** Make `--model-provider azure` work correctly for all analysis types.

### 1.1 Fix `max_tokens` → `max_completion_tokens`

**File:** `llm_provider.py:133`

```python
# BEFORE (line 133)
max_tokens=2000,

# AFTER
max_completion_tokens=2000,
```

**Why:** Azure's newer GPT-4o deployments reject `max_tokens`. Error: `"Unsupported parameter: 'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead."` This is confirmed by the user's error log and [Azure API documentation](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle).

**Testing:** Run `python main.py --input test_5_tickets.csv --analysis-type diagnostics --model-provider azure`

### 1.2 Update Azure API version

**File:** `config.py:65`

```python
# BEFORE
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

# AFTER
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
```

**File:** `.env.example:13`

```
# BEFORE
AZURE_OPENAI_API_VERSION=2024-02-01

# AFTER
AZURE_OPENAI_API_VERSION=2024-10-21
```

**Why:** `2024-02-01` is approaching retirement and missing structured outputs, `max_completion_tokens`, and batch API. `2024-10-21` is the latest versioned GA. [Source](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle).

### 1.3 Make Gemini API key validation lazy

**File:** `config.py:50-54`

```python
# BEFORE
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set")

# AFTER
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Validation moved to GeminiClient.__init__() in llm_provider.py
# This allows Azure-only usage without requiring Gemini credentials
```

**Why:** `config.py` is imported by every module. The `raise ValueError` at import time blocks all Azure-only runs. `GeminiClient.__init__()` at `llm_provider.py:174` already validates the key — the config-level check is redundant and harmful.

**Decision (SpecFlow Q1):** Remove validation from config.py. GeminiClient constructor already validates. A missing key will fail fast at provider instantiation, which is early enough in the pipeline.

### 1.4 Migrate categorizer to LLMProviderFactory

**File:** `categorizer.py`

Changes:
- Remove `from google import genai` (line 11)
- Add `from llm_provider import LLMProviderFactory`
- Change `__init__` to accept `model_provider` parameter
- Replace `self.client = genai.Client(...)` with `self.llm_client = LLMProviderFactory.get_provider(model_provider)`
- Replace `self.client.models.generate_content(model=self.model_name, contents=prompt)` with `self.llm_client.generate_content(prompt)`

**File:** `main.py:63`

```python
# BEFORE
self.categorizer = TicketCategorizer()

# AFTER
self.categorizer = TicketCategorizer(model_provider=model_provider)
```

**Why:** Categorizer currently bypasses the provider factory and always uses Gemini directly, even when `--model-provider azure` is passed.

### 1.5 Fix stats tracking for Phase 6

**File:** `main.py:438`

```python
# BEFORE
assessment = could_help.get('assessment', '').lower()

# AFTER
assessment = could_help.get('overall_assessment', '').lower()
```

**Why:** Phase 6 renamed the field from `assessment` to `overall_assessment`. The "Could Diagnostics help?" stats always show 0.

### 1.6 Make Gemini model configurable via .env

**File:** `config.py:56`

```python
# BEFORE
GEMINI_MODEL = "gemini-flash-latest"

# AFTER
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
```

**File:** `.env.example`

```
# Gemini Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
# Options: gemini-2.5-flash (stable), gemini-3.1-flash-lite-preview (newest free tier)
```

**Why:** `gemini-flash-latest` is not in the official model list. `gemini-2.5-flash` is stable. Making it configurable allows switching to `gemini-3.1-flash-lite-preview` (1000 RPD, 15 RPM) without code changes.

### 1.7 Fix `both` mode merge — ticket_id-based

**File:** `main.py:943-950`

```python
# BEFORE (index-based, fragile)
for i, ticket in enumerate(categorized_tickets):
    if i < len(diagnostics_tickets):
        diag_ticket = diagnostics_tickets[i]
        if 'diagnostics_analysis' in diag_ticket:
            ticket['diagnostics_analysis'] = diag_ticket['diagnostics_analysis']

# AFTER (ticket_id-based, safe)
diag_by_id = {t.get('ticket_id'): t for t in diagnostics_tickets}
for ticket in categorized_tickets:
    tid = ticket.get('ticket_id')
    diag_ticket = diag_by_id.get(tid)
    if diag_ticket:
        if 'diagnostics_analysis' in diag_ticket:
            ticket['diagnostics_analysis'] = diag_ticket['diagnostics_analysis']
        if 'diagnostics_analysis_status' in diag_ticket:
            ticket['diagnostics_analysis_status'] = diag_ticket['diagnostics_analysis_status']
```

**Decision (SpecFlow Q3):** Include partial results with both analysis fields present (one may be missing). The CSV/JSON output already handles missing fields gracefully.

### 1.8 Fix `both` mode shallow copy bug (NEW — found by SpecFlow)

**File:** `main.py:652-653`

```python
# BEFORE (shallow copy — both files get same analysis_type)
pod_output = output.copy()
diag_output = output.copy()

# AFTER
import copy
pod_output = copy.deepcopy(output)
diag_output = copy.deepcopy(output)
```

**Why:** `output.copy()` is shallow. Both `pod_output["metadata"]` and `diag_output["metadata"]` point to the same dict. Setting `analysis_type` on one overwrites both. Both output files currently get `"analysis_type": "diagnostics"`.

### 1.9 Fix UI to show actual provider

**File:** `main.py:887-889`

```python
# BEFORE
"Powered by Gemini 2.5 Pro"

# AFTER — use model_provider
provider_display = {
    "gemini": f"Gemini ({config.GEMINI_MODEL})",
    "azure": f"Azure OpenAI ({config.AZURE_OPENAI_DEPLOYMENT_NAME})"
}
f"Powered by {provider_display.get(self.model_provider, self.model_provider)}"
```

Also update `main.py:216` synthesis phase header and `main.py:986` argparse description.

### Phase 1 Acceptance Criteria

- [x] `python main.py --input test_5_tickets.csv --analysis-type diagnostics --model-provider azure` completes successfully
- [x] `python main.py --input test_5_tickets.csv --analysis-type pod --model-provider azure` completes (categorizer uses Azure, not Gemini)
- [x] `python main.py --input test_5_tickets.csv --analysis-type both --model-provider azure` completes with correct merge
- [x] Azure-only `.env` (no GEMINI_API_KEY) does not crash on import
- [x] Stats summary shows correct "Could Diagnostics help?" numbers (not all zeros)
- [x] `both` mode JSON output has correct `analysis_type` in both files

---

## Phase 2: Performance Optimization (P1 — 200-500 ticket runs)

**Goal:** Reduce Azure run time from ~60+ minutes to ~15-20 minutes for 500 tickets.

### 2.1 Provider-aware rate limiting config

**File:** `config.py`

```python
# ============================================================================
# RATE LIMITING CONFIGURATION (Provider-specific)
# ============================================================================

# Zendesk
ZENDESK_MAX_CONCURRENT = 10

# Gemini free tier
GEMINI_MAX_CONCURRENT = 1
GEMINI_REQUEST_DELAY = 7  # 10 RPM limit for gemini-2.5-flash
# NOTE: gemini-3.1-flash-lite-preview allows 15 RPM (4s delay).
# Override via .env if using a different model.

# Azure OpenAI
AZURE_MAX_CONCURRENT = int(os.getenv("AZURE_MAX_CONCURRENT", "10"))
AZURE_REQUEST_DELAY = float(os.getenv("AZURE_REQUEST_DELAY", "0"))
```

**Files to update:** `synthesizer.py`, `categorizer.py`, `diagnostics_analyzer.py` — check `self.model_provider` before applying delay.

```python
# In synthesizer.py (and similar in other modules):
if self.model_provider == "gemini" and config.GEMINI_REQUEST_DELAY > 0:
    await asyncio.sleep(config.GEMINI_REQUEST_DELAY)
elif self.model_provider == "azure" and config.AZURE_REQUEST_DELAY > 0:
    await asyncio.sleep(config.AZURE_REQUEST_DELAY)
```

**Decision (SpecFlow Q2):** Keep 7-second delay for `gemini-2.5-flash` (10 RPM limit). For `gemini-3.1-flash-lite-preview` (15 RPM), users can set `GEMINI_REQUEST_DELAY=4` in `.env`. This is safer than auto-detecting model capabilities.

### 2.2 Provider-aware concurrency (semaphore sizing)

Update all modules to use provider-specific semaphore:

```python
# In __init__ of synthesizer, categorizer, diagnostics_analyzer:
if model_provider == "azure":
    self.semaphore = asyncio.Semaphore(config.AZURE_MAX_CONCURRENT)
else:
    self.semaphore = asyncio.Semaphore(config.GEMINI_MAX_CONCURRENT)
```

**Decision (SpecFlow Q4 — Shared rate limiter for `both` mode):** When running `both` mode on Gemini, the categorizer and diagnostics analyzer would each hit Gemini independently, doubling the request rate. Solution: create the semaphore once in `main.py` and pass it to both modules.

```python
# In main.py TicketSummarizer.__init__():
if model_provider == "azure":
    self._llm_semaphore = asyncio.Semaphore(config.AZURE_MAX_CONCURRENT)
else:
    self._llm_semaphore = asyncio.Semaphore(config.GEMINI_MAX_CONCURRENT)

self.synthesizer = GeminiSynthesizer(model_provider=model_provider, semaphore=self._llm_semaphore)
self.categorizer = TicketCategorizer(model_provider=model_provider, semaphore=self._llm_semaphore)
self.diagnostics_analyzer = DiagnosticsAnalyzer(model_provider=model_provider, semaphore=self._llm_semaphore)
```

### 2.3 Refactor diagnostics `analyze_multiple()` to use `asyncio.gather()`

**File:** `diagnostics_analyzer.py:513-579`

Replace sequential `for` loop with gather pattern matching synthesizer and categorizer:

```python
async def analyze_multiple(self, tickets, progress_callback=None):
    tickets_to_analyze = [t for t in tickets if t.get('processing_status') == 'success' and 'synthesis' in t]

    tasks = [self._analyze_with_progress(t, progress_callback) for t in tickets_to_analyze]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    analyzed = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            ticket = tickets_to_analyze[i]
            ticket["diagnostics_analysis_status"] = "failed"
            ticket["diagnostics_analysis_error"] = str(result)
            analyzed.append(ticket)
        else:
            analyzed.append(result)

    # Add back skipped tickets
    skipped = [t for t in tickets if t.get('processing_status') != 'success' or 'synthesis' not in t]
    analyzed.extend(skipped)
    return analyzed
```

### 2.4 Standardize on `asyncio.to_thread()`

**Files:** `synthesizer.py:171-174`, `categorizer.py:296-303`

```python
# BEFORE (synthesizer.py)
loop = asyncio.get_event_loop()
response = await loop.run_in_executor(None, lambda: self.llm_client.generate_content(prompt))

# AFTER
response = await asyncio.to_thread(self.llm_client.generate_content, prompt)
```

**Why:** `asyncio.to_thread()` is the modern pattern (Python 3.9+), propagates `contextvars.Context`, and is simpler. [Python docs](https://docs.python.org/3/library/asyncio-task.html).

### 2.5 Add tenacity retry with exponential backoff

**File:** `requirements.txt` — add `tenacity>=8.2.0`

**File:** `llm_provider.py` — wrap `generate_content` in both providers:

```python
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception_type
from openai import RateLimitError, APITimeoutError, APIConnectionError

@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIConnectionError)),
)
def generate_content(self, prompt):
    # ... existing implementation
```

**Why:** The existing custom retry in `utils.py` catches all exceptions indiscriminately and only retries once. Azure 429s need exponential backoff with `Retry-After` header respect. Non-retryable errors (400, 401) should fail immediately.

**Decision (SpecFlow Q4b):** Differentiate retryable (429, 503, timeout, connection) from non-retryable (400, 401, 404, content filter). Content filter rejections are non-retryable.

### Phase 2 Acceptance Criteria

- [ ] Azure run of 500 tickets completes in <20 minutes (vs current ~60+ minutes)
- [ ] Gemini free tier stays under 10 RPM (7s delay) for `gemini-2.5-flash`
- [ ] `both` mode on Gemini does not double the request rate (shared semaphore)
- [ ] 429 errors from Azure are retried with exponential backoff
- [ ] 400/401 errors fail immediately (no wasteful retries)
- [ ] All modules use `asyncio.to_thread()` consistently

---

## Phase 3: Quality Improvements (P2 — Better LLM outputs)

**Goal:** Improve output quality via structured outputs, better prompts, and proper model configuration.

### 3.1 Structured outputs via Pydantic schemas

Define schemas in a new file `schemas.py`:

```python
# schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class TicketSynthesis(BaseModel):
    issue_reported: str = Field(description="One-liner describing what the customer initially reported or the actual issue identified")
    root_cause: str = Field(description="One-liner describing the underlying technical cause of the issue")
    summary: str = Field(description="3-4 line paragraph capturing the ticket essence, key troubleshooting steps, and how the solution was reached")
    resolution: str = Field(description="One-liner stating how the issue was actually resolved")

class PODEnum(str, Enum):
    WFE = "WFE"
    Guidance = "Guidance"
    CMM = "CMM"
    Hub = "Hub"
    Analytics = "Analytics"
    Insights = "Insights"
    Capture = "Capture"
    Mirror = "Mirror"
    Desktop = "Desktop"
    Mobile = "Mobile"
    Labs = "Labs"
    PlatformServices = "Platform Services"
    UIPlatform = "UI Platform"

class ConfidenceEnum(str, Enum):
    confident = "confident"
    not_confident = "not confident"

class TicketCategorization(BaseModel):
    primary_pod: PODEnum = Field(description="The primary POD this ticket belongs to")
    reasoning: str = Field(description="2-3 sentences explaining why this POD was chosen")
    confidence: ConfidenceEnum
    confidence_reason: str = Field(description="Single sentence explaining confidence level")
    alternative_pods: List[str] = Field(default_factory=list, description="Other PODs this could belong to, or empty list")
    alternative_reasoning: Optional[str] = Field(default=None)

class TriageEnum(str, Enum):
    yes = "yes"
    no = "no"
    maybe = "maybe"

class DiagnosticsUsage(BaseModel):
    llm_assessment: str = Field(description="yes, no, or unknown")
    confidence: ConfidenceEnum
    reasoning: str

class DiagnosticsHelp(BaseModel):
    triage_assessment: TriageEnum
    triage_reasoning: str
    triage_gap_area: Optional[str] = Field(default=None)
    triage_gap_description: Optional[str] = Field(default=None)
    fix_assessment: TriageEnum
    fix_reasoning: str
    fix_gap_area: Optional[str] = Field(default=None)
    fix_gap_description: Optional[str] = Field(default=None)
    confidence: ConfidenceEnum
    diagnostics_capability_matched: List[str] = Field(default_factory=list)
    limitation_notes: Optional[str] = Field(default=None)

class DiagnosticsMetadata(BaseModel):
    ticket_type: str = Field(description="troubleshooting, feature_request, technical_request, or unclear")

class DiagnosticsAnalysis(BaseModel):
    was_diagnostics_used: DiagnosticsUsage
    could_diagnostics_help: DiagnosticsHelp
    metadata: DiagnosticsMetadata
```

**Provider integration:**

Azure (`llm_provider.py`):
```python
response = self.client.chat.completions.create(
    model=self.deployment_name,
    messages=[...],
    max_completion_tokens=2000,
    temperature=0.3,
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": schema_name,
            "strict": True,
            "schema": schema_class.model_json_schema()
        }
    }
)
```

Gemini (`llm_provider.py`):
```python
response = self.client.models.generate_content(
    model=self.model_name,
    contents=prompt,
    config={
        "response_mime_type": "application/json",
        "response_schema": schema_class,
        "temperature": 0.2,
    }
)
```

**Impact:** Eliminates `synthesizer.py:parse_response()` (~70 lines of regex), `categorizer.py:parse_categorization_response()` (~140 lines of regex), and simplifies `diagnostics_analyzer.py:_parse_diagnostics_response()`. POD validation becomes automatic via enum constraint.

**Decision (SpecFlow Q5):** Use native structured outputs for BOTH providers. Azure JSON schema enforcement is rock-solid. Gemini's `response_schema` with Pydantic works on 2.5-flash and 3.x models. Both guarantee schema compliance at generation time.

### 3.2 Add temperature to Gemini

**File:** `llm_provider.py:208` — add config parameter:

```python
response = self.client.models.generate_content(
    model=self.model_name,
    contents=prompt,
    config={
        "temperature": 0.2,  # Lower for analytical tasks on 2.5 models
        # NOTE: For Gemini 3.x models, Google recommends keeping temperature=1.0
    }
)
```

**Why:** Gemini defaults to 1.0 (too high for analytical extraction). Azure is already at 0.3. Research confirms 0.0-0.3 is optimal for factual/analytical tasks on Gemini 2.5. [Google prompting strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies).

### 3.3 Enhance comment thread formatting

**File:** `utils.py:format_comment_thread()`

Add structural markers:

```python
def format_comment_thread(comments):
    total = len(comments)
    formatted = []
    ticket_created = comments[0]["created_at"] if comments else None

    for i, comment in enumerate(comments, 1):
        is_public = comment.get("public", True)
        role = "Agent" if not is_public else ("Customer" if i == 1 else "Agent/Customer")
        day_num = _calculate_day_number(ticket_created, comment["created_at"])

        header = f"[Comment {i}/{total} | {role} | Day {day_num}]"
        formatted.append(f"{header}\n{comment['body']}")

    return "\n\n---\n\n".join(formatted)
```

**Decision (SpecFlow Q7):** Use heuristic for role detection (internal comments = agent, first public comment = customer, subsequent = infer from context). Avoids N additional Zendesk User API calls.

**Why:** The "lost in the middle" research shows 39% performance drop on multi-turn threads without orientation markers. [Source](https://arxiv.org/html/2505.06120v1).

### 3.4 Add few-shot examples to categorization prompt

**File:** `config.py:CATEGORIZATION_PROMPT_TEMPLATE`

Add 2-3 worked examples before the `TICKET SYNTHESIS` section, focusing on ambiguous edge cases:

1. **WFE vs Guidance** — Element detection failure on a Smart Tip (WFE owns elements, Guidance owns content type)
2. **Guidance vs CMM** — Content lifecycle issue affecting a Flow (CMM owns lifecycle, Guidance owns Flow logic)
3. **WFE vs Capture** — User Action not triggering (Capture owns User Actions, WFE owns element detection for UAs)

**Why:** Research shows few-shot CoT outperforms zero-shot for ambiguous multi-class classification. The diagnostics prompt already has 5 examples; categorization has zero. [Source](https://www.promptingguide.ai/techniques/cot).

### 3.5 Strengthen anti-hallucination with evidence citation

**File:** `config.py:DIAGNOSTICS_ANALYSIS_PROMPT` (lines 360-381)

Add to the anti-hallucination rules section:

```
5. **CITE YOUR EVIDENCE**
   - In every reasoning field, explicitly quote the phrase from the synthesis that supports your claim
   - Format: [EVIDENCE: "...quoted text from synthesis..."]
   - If you cannot quote the synthesis to support a claim, DO NOT make that claim
   - This applies to triage_reasoning, fix_reasoning, and was_diagnostics_used reasoning
```

Also add this instruction to the synthesis and categorization prompts (which currently lack anti-hallucination rules).

**Why:** Requiring explicit citation forces grounding and is more effective than general "don't hallucinate" instructions. [Source](https://www.lakera.ai/blog/guide-to-hallucinations-in-large-language-models).

### 3.6 Feed `support_root_cause` into synthesis prompt

**File:** `config.py:LLM_PROMPT_TEMPLATE`

Add after the comment thread section:

```
SUPPORT AGENT'S ROOT CAUSE (from Zendesk custom field):
{support_root_cause}
Note: This is the support agent's documented root cause. Use it to VALIDATE your own analysis.
If your analysis differs from the agent's root cause, acknowledge both and explain the discrepancy.
Do NOT simply parrot this field — form your own assessment based on the comment thread.
```

**File:** `synthesizer.py:format_prompt()` — extract and pass `support_root_cause` from `custom_fields`.

**Decision (SpecFlow Q9):** Frame as validation/enrichment, NOT replacement. Explicit prompt instruction to form independent assessment.

### Phase 3 Acceptance Criteria

- [ ] All 3 modules use Pydantic schemas for LLM output (no regex parsing)
- [ ] Azure and Gemini both enforce JSON schema at generation time
- [ ] Categorization prompt includes 2-3 few-shot examples
- [ ] Diagnostics prompt includes "cite your evidence" rule
- [ ] Comment threads show `[Comment 3/12 | Agent | Day 3]` markers
- [ ] Synthesis prompt receives `support_root_cause` as validation context
- [ ] Gemini uses temperature 0.2 (verified in logs)
- [ ] Output CSV/JSON format is backward compatible (same columns, additive only)

---

## Phase 4: Code Quality Polish (P3)

### 4.1 Rename `GeminiAPIError` → `LLMAPIError`

**Files:** `utils.py:29`, `llm_provider.py:149`, `synthesizer.py:179/202`, `categorizer.py:287/307/336`, `diagnostics_analyzer.py:153`

### 4.2 Rename `GeminiSynthesizer` → `TicketSynthesizer`

**File:** `synthesizer.py:19`, `main.py:29/62`

### 4.3 Pin SDK versions

**File:** `requirements.txt`

```
aiohttp==3.9.1
google-genai>=1.68.0
openai>=1.42.0,<2.0.0
python-dotenv==1.0.0
pytz==2024.1
rich==13.7.0
requests==2.31.0
beautifulsoup4==4.12.3
html2text==2020.1.16
tenacity>=8.2.0
pydantic>=2.8.0
```

Changes: pin `google-genai`, constrain `openai` to v1.x, add `tenacity` and `pydantic`, remove `tqdm`.

### 4.4 Remove unused `tqdm`

**File:** `requirements.txt:6` — remove `tqdm==4.66.1`

Verified: `tqdm` is not imported anywhere in the codebase. Rich replaced it.

### Phase 4 Acceptance Criteria

- [ ] No references to `GeminiAPIError` or `GeminiSynthesizer` in codebase
- [ ] `pip install -r requirements.txt` succeeds
- [ ] No unused imports (`tqdm`, old `google-generativeai`)

---

## Alternative Approaches Considered

| Approach | Why Rejected |
|----------|-------------|
| **Mega-batching** (multiple tickets per LLM call using 1M context) | Quality degrades with "lost in the middle" problem. Error blast radius increases. Pipeline redesign required. |
| **Gemini free tier as primary for 200-500 tickets** | 250-1000 RPD cap insufficient. At 3 calls/ticket, 500 tickets = 1500 calls (exceeds free tier). |
| **Reasoning models (o4-mini) for diagnostics** | Azure deployment may not support it. Deferred to future iteration. |
| **Post-hoc Pydantic validation (vs. native structured outputs)** | Native enforcement is strictly better — prevents malformed output at generation time. Both Azure and Gemini support it. |
| **Custom rate limiter (vs. tenacity + semaphore)** | Over-engineered for current scale. Tenacity is battle-tested and handles 429s natively. |

## Risk Analysis & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Structured outputs change LLM output quality | Medium | Medium | Compare outputs before/after on 50-ticket sample. Keep old regex parsing available behind a flag initially. |
| Azure API version change breaks existing workflows | Low | High | New version `2024-10-21` is backward-compatible with existing chat completions code. |
| Gemini 2.5-flash deprecation (June 17, 2026) | Certain | Medium | Model is configurable via `.env`. Switch to `gemini-3.1-flash-lite-preview` when ready. |
| `openai` SDK pin blocks needed features | Low | Low | Pin range `>=1.42.0,<2.0.0` allows minor updates. Revisit if v1 API migration is needed. |
| Pydantic schema with `default` values rejected by Gemini | Medium | Low | Known issue ([GitHub #699](https://github.com/googleapis/python-genai/issues/699)). Avoid default values in response schemas — use `Optional` instead. |

## Dependencies & Prerequisites

- Azure OpenAI deployment must be accessible and have GPT-4o deployed
- Zendesk API key must be valid
- conda environment `ticket-summarizer` must exist
- Python 3.12+

## Explicit Non-Goals (SpecFlow items deferred)

- **Resumability/checkpointing** (SpecFlow Gap 8.1) — Not this iteration. For now, re-run on failure.
- **Cost estimation / `--dry-run`** (SpecFlow Gap 8.2) — Not this iteration.
- **Token counting / context window truncation** (SpecFlow Gap 8.3) — Not this iteration. Very long tickets may fail; acceptable for now.
- **Internal comment filtering** (SpecFlow Gap 8.4) — Include all comments (they contain critical troubleshooting context). Decision: SpecFlow Q8.
- **Unit tests** (SpecFlow Gap 8.5) — Deferred but strongly recommended as a fast-follow.
- **`--output-dir` flag** (SpecFlow Gap 8.6) — Not this iteration.
- **Quality comparison mode** — Deferred to Phase 5 (future).

## Files Modified

| File | Phase | Changes |
|------|-------|---------|
| `config.py` | 1, 2, 3 | Lazy validation, API version, model name, rate limiting config, prompt improvements |
| `llm_provider.py` | 1, 2, 3 | `max_completion_tokens`, temperature, structured output, tenacity retry |
| `categorizer.py` | 1, 2, 3 | Migrate to factory, `asyncio.to_thread`, Pydantic schema, few-shot prompt |
| `synthesizer.py` | 2, 3 | `asyncio.to_thread`, provider-aware delays, Pydantic schema, `support_root_cause` |
| `diagnostics_analyzer.py` | 2, 3 | `asyncio.gather()`, Pydantic schema |
| `main.py` | 1 | Fix stats, fix merge, fix shallow copy, fix UI text, shared semaphore |
| `utils.py` | 3, 4 | Comment formatting, rename exception |
| `requirements.txt` | 2, 4 | Add tenacity/pydantic, pin versions, remove tqdm |
| `.env.example` | 1 | Updated API version, model name, new config options |
| `schemas.py` | 3 | NEW — Pydantic schemas for all LLM outputs |

## Implementation Order

```
Phase 1 (Day 1) ──→ Phase 2 (Day 2) ──→ Phase 3 (Day 3-4) ──→ Phase 4 (Day 4)
   │                    │                     │                      │
   ├─ 1.3 Lazy config   ├─ 2.1 Rate config    ├─ 3.1 Pydantic       ├─ 4.1 Rename errors
   ├─ 1.1 max_tokens    ├─ 2.2 Semaphores     ├─ 3.2 Temperature    ├─ 4.2 Rename class
   ├─ 1.2 API version   ├─ 2.3 gather()       ├─ 3.3 Comment fmt    ├─ 4.3 Pin SDKs
   ├─ 1.4 Categorizer   ├─ 2.4 to_thread()    ├─ 3.4 Few-shot       └─ 4.4 Remove tqdm
   ├─ 1.5 Stats fix     └─ 2.5 Tenacity       ├─ 3.5 Anti-halluc
   ├─ 1.6 Model name                          └─ 3.6 Root cause
   ├─ 1.7 Merge fix
   ├─ 1.8 Shallow copy
   └─ 1.9 UI text
```

**Critical path:** Phase 1 unblocks Azure usage. Phase 2 makes it practical at scale. Phase 3 improves output quality. Phase 4 is polish. Each phase is independently deployable and testable.

## References & Research

### Internal References
- `docs/architecture_decisions.md` — 14 ADRs covering design decisions
- `docs/implementation_plan.md` — Original phase breakdown

### External References
- [Azure OpenAI API Lifecycle](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle)
- [Azure OpenAI Structured Outputs](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs)
- [Azure OpenAI Quotas & Limits](https://learn.microsoft.com/en-us/azure/foundry/openai/quotas-limits)
- [Gemini Structured Output](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini Models](https://ai.google.dev/gemini-api/docs/models)
- [Gemini Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Gemini Prompting Strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies)
- [OpenAI Structured Outputs](https://openai.com/index/introducing-structured-outputs-in-the-api/)
- [LLMs Get Lost in Multi-Turn Conversation (arXiv)](https://arxiv.org/html/2505.06120v1)
- [Chain-of-Thought Prompting Guide](https://www.promptingguide.ai/techniques/cot)
- [LLM Hallucination Guide (Lakera)](https://www.lakera.ai/blog/guide-to-hallucinations-in-large-language-models)
- [Python asyncio.to_thread docs](https://docs.python.org/3/library/asyncio-task.html)
- [OpenAI Python SDK Releases](https://github.com/openai/openai-python/releases)
- [google-genai PyPI](https://pypi.org/project/google-genai/)
