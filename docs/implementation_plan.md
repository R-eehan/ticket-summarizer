# Zendesk Ticket Summarizer - Implementation Plan (Phases 1-3c)

> **Note**: This document contains the historical implementation details for Phases 1 through 3c. For observability and instrumentation (Phase 4), see [instrumentation_plan.md](./instrumentation_plan.md). For architectural decisions and reasoning, see [architecture_decisions.md](./architecture_decisions.md).

---

## Table of Contents

- [Phase 1: Core Implementation](#phase-1-core-implementation)
  - [Overview](#overview)
  - [Problem Statement](#problem-statement)
  - [Solution](#solution)
  - [Technical Architecture](#technical-architecture)
  - [Module Specifications](#module-specifications)
  - [Output JSON Structure](#output-json-structure)
  - [Technical Decisions](#technical-decisions)
- [Phase 2: POD Categorization](#phase-2-pod-categorization)
  - [Overview](#overview-1)
  - [Problem Statement - Phase 2](#problem-statement---phase-2)
  - [Technical Architecture - Phase 2](#technical-architecture---phase-2)
  - [Module Specifications - Phase 2](#module-specifications---phase-2)
  - [Enhanced Output JSON Structure](#enhanced-output-json-structure)
  - [Technical Decisions - Phase 2](#technical-decisions---phase-2)
- [Phase 3b: Diagnostics Analysis](#phase-3b-diagnostics-analysis)
  - [Overview](#overview-2)
  - [Problem Statement](#problem-statement-1)
  - [Solution](#solution-1)
  - [Updated Architecture - Branching Design](#updated-architecture---branching-design)
  - [Module Updates - Phase 3b](#module-updates---phase-3b)
  - [Output Files - Phase 3b](#output-files---phase-3b)
  - [Key Design Decisions - Phase 3b](#key-design-decisions---phase-3b)
- [Phase 3c: Multi-Model LLM Support](#phase-3c-multi-model-llm-support)
  - [Overview](#overview-3)
  - [Problem Statement - Phase 3c](#problem-statement---phase-3c)
  - [Technical Architecture - Phase 3c](#technical-architecture---phase-3c)
  - [Technical Decisions - Phase 3c](#technical-decisions---phase-3c)
  - [Configuration Requirements](#configuration-requirements---phase-3c)

---

## Phase 1: Core Implementation

### Overview

A terminal-based application that fetches Zendesk tickets, retrieves all comments, and uses Google Gemini 2.5 Pro to synthesize comprehensive summaries for product area attribution.

### Problem Statement

Current ticket categorization solution only examines subject, description, and custom fields, missing crucial context from comment threads. This leads to:
- Incorrect product area attribution
- Missed nuances in issue resolution
- Incomplete understanding of actual vs. reported issues

### Solution

Build a CLI tool that:
1. Takes CSV input with ticket IDs
2. Fetches complete ticket data (subject, description, ALL comments)
3. Uses LLM to synthesize: issue reported, root cause, summary, resolution
4. Outputs structured JSON for future web application integration

### Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (main.py)                    │
│  - CLI interface, progress tracking, final JSON generation   │
└──────────────┬────────────────────────────┬──────────────────┘
               │                            │
     ┌─────────▼─────────┐       ┌─────────▼──────────┐
     │  ZENDESK FETCHER  │       │  GEMINI SYNTHESIZER │
     │   (fetcher.py)    │       │   (synthesizer.py)  │
     │                   │       │                     │
     │ - Fetch tickets   │       │ - LLM synthesis     │
     │ - Fetch comments  │       │ - Prompt formatting │
     │ - Rate limiting   │       │ - Response parsing  │
     │ - Retry logic     │       │ - Retry logic       │
     └───────────────────┘       └─────────────────────┘
               │                            │
     ┌─────────▼────────────────────────────▼──────────┐
     │          UTILITIES (utils.py)                   │
     │  - IST conversion, logging, error handling      │
     └─────────────────────────────────────────────────┘
```

### File Structure

```
ticket-summarizer/
├── plan.md                 # Original plan (now deprecated - see docs/)
├── docs/                   # NEW: Modular documentation
│   ├── implementation_plan.md      # This file
│   ├── instrumentation_plan.md    # Phase 4 observability
│   └── architecture_decisions.md  # ADRs
├── README.md               # Setup & usage instructions
├── requirements.txt        # Python dependencies
├── .gitignore             # Git ignore patterns
├── .env.example           # Environment variable template
├── main.py                # Entry point & orchestrator
├── config.py              # Configuration & constants
├── utils.py               # Utilities (logging, timezone, etc.)
├── fetcher.py             # Zendesk API client
├── synthesizer.py         # Gemini LLM client (Phase 1)
├── categorizer.py         # POD categorization (Phase 2)
├── diagnostics_analyzer.py # Diagnostics analysis (Phase 3b)
├── llm_provider.py        # LLM provider factory (Phase 3c)
├── logs/                  # Application logs (auto-created)
│   └── app_YYYYMMDD.log
└── input_tickets.csv      # User-provided input (example)
```

### Module Specifications

#### 1. config.py - Configuration Constants

**Purpose**: Central configuration management

**Contents**:
- Zendesk credentials (subdomain, email, API token from env)
- Gemini API key (from env)
- Azure OpenAI credentials (Phase 3c)
- Rate limiting configuration:
  - Zendesk: 10 concurrent requests
  - Gemini: 5 concurrent requests
  - Retry: 1 attempt with 2-second delay
- LLM prompt templates (synthesis, categorization, diagnostics)
- Logging configuration

#### 2. utils.py - Utilities

**Purpose**: Shared utility functions

**Functions**:
- `convert_to_ist(utc_timestamp)`: Convert UTC to IST (UTC+5:30)
- `setup_logger(name)`: Configure structured logging
- `strip_html(text)`: Remove HTML/markdown from text
- `retry_on_failure(func, retries=1)`: Retry decorator with exponential backoff
- `normalize_diagnostics_field(value)`: Normalize Zendesk custom field (Phase 3b)
- `validate_diagnostics_assessment(assessment)`: Validate assessment values (Phase 3b)

**Custom Exceptions**:
- `ZendeskAPIError`: Zendesk API failures
- `GeminiAPIError`: Gemini API failures
- `TicketNotFoundError`: Ticket doesn't exist

#### 3. fetcher.py - Zendesk Data Fetcher

**Purpose**: Fetch ticket data from Zendesk API

**Class**: `ZendeskFetcher`

**Methods**:
- `fetch_ticket(ticket_id)`: Fetch single ticket metadata
- `fetch_comments(ticket_id)`: Fetch all comments for a ticket
- `fetch_ticket_complete(ticket_id)`: Fetch ticket + all comments (combined)
- `fetch_multiple_tickets(ticket_ids, progress_callback)`: Parallel fetch with progress
- `_parse_custom_fields(ticket_data)`: Extract custom fields (Phase 3b)

**Features**:
- Rate limiting using `asyncio.Semaphore` (max 10 concurrent)
- Retry logic (1 retry on failure with 2s delay)
- Progress callbacks for real-time updates
- Comprehensive error handling and logging
- Basic auth with email/token format
- Custom field extraction for diagnostics (Phase 3b)

**API Endpoints**:
- `GET /api/v2/tickets/{ticket_id}` - Fetch ticket
- `GET /api/v2/tickets/{ticket_id}/comments` - Fetch comments

#### 4. synthesizer.py - Gemini LLM Synthesizer

**Purpose**: Use Gemini 2.5 Pro (or Azure OpenAI GPT-4o) to analyze and synthesize ticket data

**Class**: `GeminiSynthesizer`

**Methods**:
- `synthesize_ticket(ticket_data)`: Generate synthesis from ticket data
- `format_prompt(ticket_data)`: Format data into LLM prompt
- `parse_response(llm_response)`: Parse LLM response into structured data
- `synthesize_multiple(tickets, progress_callback)`: Parallel synthesis with progress

**Features**:
- Rate limiting (max 5 concurrent requests)
- Retry logic (1 retry on failure)
- Robust response parsing with fallbacks
- Token usage tracking
- HTML/markdown stripping from comments
- Multi-model support (Gemini/Azure) via factory pattern (Phase 3c)

**LLM Prompt Template**:

```
You are an expert support ticket analyst. Your task is to analyze a Zendesk support ticket including its subject, description, and ALL comments exchanged between the customer and support agents.

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

Focus on accuracy and technical precision. Extract information only from the provided data.
```

#### 5. categorizer.py - POD Categorizer (Phase 2)

**Purpose**: Categorize synthesized tickets into PODs using LLM-based judgment

**Class**: `TicketCategorizer`

**Methods**:
- `categorize_ticket(ticket_data)`: Categorize a single synthesized ticket
- `format_categorization_prompt(ticket_data)`: Format synthesis into categorization prompt
- `parse_categorization_response(response_text)`: Parse LLM response into structured data
- `categorize_multiple(tickets, progress_callback)`: Batch categorization with progress

**Features**:
- Rate limiting (max 5 concurrent Gemini calls)
- Retry logic (1 retry on failure)
- POD validation against predefined list
- Confidence scoring (binary: "confident" or "not confident")
- Alternative POD suggestions when ambiguous
- Comprehensive inline comments for code clarity

**Categorization Output Structure**:
```python
{
    "primary_pod": "Guidance",
    "reasoning": "Based on synthesis, issue involves Smart Tips not displaying...",
    "confidence": "confident",
    "confidence_reason": "Clear synthesis match with no ambiguity between PODs",
    "alternative_pods": ["WFE"],  # Or [] if none
    "alternative_reasoning": "Could also be WFE due to element detection...",  # Or null
    "metadata": {
        "keywords_matched": ["Smart Tips", "preview mode", "display"],
        "decision_factors": [
            "Direct mention of Smart Tips in synthesis",
            "Clear product functionality issue",
            "Resolution involved product fix"
        ]
    }
}
```

**POD Definitions**:

13 PODs based on Whatfix product structure:

1. **WFE (Workflow Engine)** - Element detection, CSS selectors, reselection, latching, visibility rules
2. **Guidance** - Flows, Smart Tips, Pop-ups, Beacons, Launchers, Triggers, Blockers
3. **CMM (Content & Metadata Management)** - Dashboard, CLM, P2P, Tags, Auto Testing
4. **Hub** - DAP on OS, Self Help, Task List, Surveys, Content Repository
5. **Analytics** - Dashboards, trends, funnels, KPIs, performance tracking
6. **Insights** - Ask Whatfix AI, Cohorts, Event groups, User Journeys
7. **Capture** - Autocapture, User Actions, User Attributes, User Identification
8. **Mirror** - Application simulation, interactive training replicas
9. **Desktop** - Native desktop app support (SAP GUI, Teams, Java)
10. **Mobile** - iOS/Android deployments
11. **Labs** - AI Assistant, AC reviewer, Intent Recognition, Enterprise Search
12. **Platform Services** - Integration Hub (Confluence, Workday, Amplitude)
13. **UI Platform** - Canary deployments

#### 6. diagnostics_analyzer.py - Diagnostics Analyzer (Phase 3b)

**Purpose**: Analyze tickets for Diagnostics feature applicability

**Class**: `DiagnosticsAnalyzer`

**Key Methods**:
- `analyze_ticket(ticket_data)`: Analyze single ticket
- `format_diagnostics_prompt(...)`: Format prompt with ticket synthesis
- `parse_diagnostics_response(response_text)`: Parse LLM JSON response
- `validate_analysis_structure(analysis_data)`: Validate response structure
- `analyze_multiple(tickets, progress_callback)`: Batch analysis with progress

**Output Structure**:
```json
{
  "was_diagnostics_used": {
    "custom_field_value": "no",
    "llm_assessment": "no",
    "confidence": "confident",
    "reasoning": "..."
  },
  "could_diagnostics_help": {
    "assessment": "yes",
    "confidence": "confident",
    "reasoning": "...",
    "diagnostics_capability_matched": ["Visibility rule evaluation"],
    "limitation_notes": null
  },
  "metadata": {
    "ticket_type": "troubleshooting",
    "analysis_timestamp": "2025-11-02T14:30:15+05:30"
  }
}
```

#### 7. llm_provider.py - LLM Provider Factory (Phase 3c)

**Purpose**: Abstract LLM provider selection (Gemini vs Azure OpenAI)

**Classes**:
- `LLMProviderFactory`: Provider selection logic
- `GeminiClient`: Wrapper for Google Gemini API
- `AzureOpenAIClient`: Wrapper for Azure OpenAI API
- `LLMResponse`: Unified response object (normalizes `.text` property)

**Factory Pattern**:
```python
from llm_provider import LLMProviderFactory

# Get provider based on configuration
llm_client = LLMProviderFactory.get_provider(provider="azure")

# Use provider (same interface for both)
response = llm_client.generate_content(prompt)
print(response.text)  # Unified interface
```

#### 8. main.py - Orchestrator & CLI

**Purpose**: Main entry point, orchestrates entire workflow

**Workflow**:
1. Parse CLI arguments (`--input`, `--analysis-type`, `--model-provider`)
2. Load CSV (auto-detect format: Serial No/Ticket ID or Zendesk Tickets ID)
3. Initialize fetcher, synthesizer, categorizer, diagnostics analyzer
4. **PHASE 1**: Fetch all tickets in parallel (with custom fields)
   - Display real-time progress for each ticket
   - Track success/failure
5. **PHASE 2**: Synthesize fetched tickets in parallel
   - Display real-time progress for each ticket
   - Track success/failure
6. **PHASE 3**: Branch based on `--analysis-type`:
   - `pod`: Run POD categorization only
   - `diagnostics`: Run diagnostics analysis only
   - `both`: Run POD + diagnostics in parallel (using `asyncio.gather()`)
7. Generate final JSON with IST timestamps
8. Save to `output_{analysis_type}_YYYYMMDD_HHMMSS.json`
9. Display summary statistics

**CLI Interface**:
```bash
# POD categorization with Gemini (default)
python main.py --input tickets.csv --analysis-type pod

# POD categorization with Azure OpenAI
python main.py --input tickets.csv --analysis-type pod --model-provider azure

# Diagnostics analysis with Gemini
python main.py --input tickets.csv --analysis-type diagnostics

# Diagnostics analysis with Azure OpenAI
python main.py --input tickets.csv --analysis-type diagnostics --model-provider azure

# Both analyses in parallel with Azure OpenAI
python main.py --input tickets.csv --analysis-type both --model-provider azure
```

**CLI Parameters**:
- `--input <csv_path>` (required): Path to input CSV file
- `--analysis-type {pod,diagnostics,both}` (required): Type of analysis to perform
- `--model-provider {gemini,azure}` (optional, default: gemini): LLM provider to use

### Output JSON Structure

**For POD Categorization (`--analysis-type pod`)**:
```json
{
  "metadata": {
    "analysis_type": "pod",
    "total_tickets": 10,
    "successfully_processed": 8,
    "synthesis_failed": 1,
    "categorization_failed": 1,
    "failed": 2,
    "confidence_breakdown": {
      "confident": 6,
      "not_confident": 2
    },
    "pod_distribution": {
      "WFE": 3,
      "Guidance": 4,
      "Hub": 1
    },
    "processed_at": "2025-05-10T14:32:30+05:30",
    "processing_time_seconds": 45.2
  },
  "tickets": [
    {
      "ticket_id": "78788",
      "serial_no": 1,
      "subject": "Offline Message from Katherine Miranda Hudson...",
      "description": "Hi, I added a smart tip but cannot get it to display...",
      "url": "https://whatfix.zendesk.com/agent/tickets/78788",
      "status": "solved",
      "created_at": "2025-05-01T07:47:00+05:30",
      "updated_at": "2025-05-02T10:15:00+05:30",
      "comments_count": 9,
      "comments": [...],
      "synthesis": {
        "issue_reported": "Smart tip not displaying in preview mode despite correct configuration",
        "root_cause": "CSS selector was missing, causing element targeting failure",
        "summary": "Customer reported a smart tip that wouldn't display in preview mode...",
        "resolution": "Reselected smart tip and added necessary CSS selector to fix element targeting"
      },
      "categorization": {
        "primary_pod": "Guidance",
        "reasoning": "Based on synthesis, the issue involves Smart Tips...",
        "confidence": "confident",
        "confidence_reason": "Clear synthesis match with no ambiguity",
        "alternative_pods": [],
        "alternative_reasoning": null,
        "metadata": {
          "keywords_matched": ["Smart Tips", "preview mode"],
          "decision_factors": [...]
        }
      },
      "processing_status": "success"
    }
  ],
  "errors": []
}
```

**For Diagnostics Analysis (`--analysis-type diagnostics`)**:
```json
{
  "metadata": {
    "analysis_type": "diagnostics",
    "total_tickets": 10,
    "successfully_processed": 9,
    "synthesis_failed": 0,
    "diagnostics_analysis_failed": 1,
    "failed": 1,
    "diagnostics_breakdown": {
      "was_used": {"yes": 2, "no": 6, "unknown": 1},
      "could_help": {"yes": 5, "no": 3, "maybe": 1},
      "confidence": {"confident": 7, "not_confident": 2}
    },
    "processed_at": "2025-11-02T14:30:00+05:30",
    "processing_time_seconds": 45.2
  },
  "tickets": [
    {
      "ticket_id": "89618",
      "subject": "Blocker Role Tags Setup",
      "synthesis": {...},
      "diagnostics_analysis": {
        "was_diagnostics_used": {...},
        "could_diagnostics_help": {...},
        "metadata": {...}
      },
      "processing_status": "success"
    }
  ],
  "errors": []
}
```

**For Both Analyses (`--analysis-type both`)**:
- Two separate files generated:
  - `output_pod_YYYYMMDD_HHMMSS.json` (POD categorization)
  - `output_diagnostics_YYYYMMDD_HHMMSS.json` (Diagnostics analysis)
- Both contain combined metadata

### Input Format

**CSV Structure - Format 1** (Phase 1 format):
```csv
Serial No,Ticket ID
1,78788
2,78969
3,78985
```

**CSV Structure - Format 2** (Auto-generates serial numbers):
```csv
Zendesk Tickets ID
78788
78969
78985
```

**Auto-Detection Logic**:
- Read CSV headers
- If "Serial No" + "Ticket ID" columns exist → Format 1
- If "Zendesk Tickets ID" column exists → Format 2 (auto-generate serial numbers)
- Otherwise → Error with clear message

### Environment Configuration

**File**: `.env`

```env
# Zendesk Configuration
ZENDESK_API_KEY=your_zendesk_api_token_here
ZENDESK_SUBDOMAIN=whatfix
ZENDESK_EMAIL=your_email@whatfix.com

# Gemini Configuration (for Gemini provider)
GEMINI_API_KEY=your_gemini_api_key_here

# Azure OpenAI Configuration (for Azure provider)
AZURE_OPENAI_ENDPOINT=https://openai-for-product.openai.azure.com/
AZURE_OPENAI_API_KEY=your_azure_key_here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-01
```

### Dependencies

**File**: `requirements.txt`

```
aiohttp==3.9.1
google-generativeai==0.3.2
python-dotenv==1.0.0
pytz==2024.1
tqdm==4.66.1
rich==13.7.0
requests==2.31.0
beautifulsoup4==4.12.3
html2text==2020.1.16
openai>=2.7.1  # Phase 3c: Azure OpenAI support
```

### Technical Decisions

#### 1. Parallelization Strategy

- **Two-Phase Approach**: Separate fetch and synthesis phases for cleaner progress tracking
- **Fetch Phase**: 10 concurrent Zendesk API calls (conservative for Enterprise plan)
- **Synthesis Phase**: 5 concurrent Gemini API calls (respecting API limits)
- **Rejected Pipeline Approach**: Would make progress tracking complex

#### 2. IST Timezone Handling

All timestamps converted from UTC to IST (UTC+5:30):
```python
import pytz
from datetime import datetime

def convert_to_ist(utc_timestamp):
    ist = pytz.timezone('Asia/Kolkata')
    return utc_timestamp.astimezone(ist).isoformat()
```

#### 3. Rate Limiting

- `asyncio.Semaphore` for concurrent request limiting
- `aiohttp` for async HTTP requests (faster than `requests`)
- Built-in delays between retries

#### 4. Retry Logic

- One retry per failed request
- 2-second exponential backoff
- Both attempts logged for debugging

#### 5. Error Handling

- Ticket-level failures don't stop entire process
- All errors logged with full context
- Failed tickets tracked separately in output JSON
- Custom exception classes for clarity

#### 6. Logging

- **Console**: INFO level (progress updates)
- **File**: DEBUG level (full API responses, errors)
- **Format**: `[YYYY-MM-DD HH:MM:SS IST] [LEVEL] [Module] Message`
- **Location**: `logs/app_YYYYMMDD.log`

#### 7. Comment Processing

- Fetch ALL comments (including internal notes)
- Strip HTML/markdown before sending to LLM (cleaner text)
- Preserve all metadata (author, timestamp, public/private)

---

## Phase 2: POD Categorization

### Overview

Phase 2 extends the ticket summarizer to automatically categorize support tickets into PODs (Product Organizational Domains) based on the synthesis summary generated in Phase 1. This addresses the core problem of incorrect categorization due to missing comment thread context.

### Problem Statement - Phase 2

**Current State (Phase 1):**
- Tickets are fetched and synthesized successfully
- Synthesis captures complete context from comment threads
- No automatic categorization into product areas

**Problem:**
- Existing keyword-based bucketing uses only subject, description, and custom fields
- Comment thread context is ignored, leading to miscategorization
- Example: Tickets 87239 and 87249 incorrectly categorized as WFE instead of Guidance

**Phase 2 Goal:**
- Automatically categorize tickets into PODs using synthesis context
- Provide reasoning and confidence scoring for each categorization
- Enable human review of ambiguous cases ("not confident" tickets)

### Technical Architecture - Phase 2

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (main.py)                    │
│         CLI, progress tracking, JSON generation              │
└──────┬──────────────────┬──────────────────┬─────────────────┘
       │                  │                  │
   ┌───▼────┐      ┌──────▼──────┐   ┌──────▼──────────┐
   │FETCHER │      │SYNTHESIZER  │   │  CATEGORIZER    │
   │        │      │             │   │ (categorizer.py)│
   │Phase 1 │      │  Phase 2    │   │    Phase 3      │
   └────────┘      └─────────────┘   └─────────────────┘
                                              │
                                     - POD assignment
                                     - Reasoning
                                     - Confidence scoring
                                     - Alternative PODs
```

### Module Specifications - Phase 2

See **categorizer.py** in [Module Specifications](#module-specifications) section above.

### Enhanced Output JSON Structure

See **Output JSON Structure** section above for complete POD categorization output format.

### Technical Decisions - Phase 2

#### 1. Categorization Architecture

**Decision**: Separate `categorizer.py` module (not integrated into `synthesizer.py`)

**Rationale**:
- **Separation of Concerns**: Synthesis and categorization are distinct operations
- **Modularity**: Can test/improve categorization independently
- **Reusability**: Can categorize pre-synthesized tickets without re-running synthesis
- **Consistency**: Mirrors existing architecture (fetcher.py, synthesizer.py)

#### 2. Confidence Scoring System

**Decision**: Binary scoring ("confident" vs "not confident") instead of 3-level

**Rationale**:
- **Actionability**: Clear decision - review or don't review
- **Simplicity**: Easier for LLM to decide binary vs 3-way split
- **Human Review**: "not confident" tickets escalated to humans
- **Avoids Ambiguity**: No middle ground that might delay action

#### 3. LLM Prompt Design

**Decision**: Condensed POD guide embedded in prompt (not RAG/semantic search)

**Rationale**:
- **Simplicity**: No additional vector DB infrastructure
- **Consistency**: Same POD definitions for every categorization
- **Cost-Effective**: Fits within Gemini token limits
- **Deterministic**: Repeatable results for same synthesis

#### 4. Alternative PODs Handling

**Decision**: Empty array `[]` when no alternatives, null for alternative_reasoning

**Rationale**:
- **JSON Compatibility**: Empty array is valid JSON, cleaner than null
- **Frontend-Friendly**: Easy to check `.length === 0` in JavaScript
- **Null for Reasoning**: Clearly indicates "not applicable" vs empty string

#### 5. Knowledge Base Injection

**Decision**: Embed full POD definitions in every prompt

**Rationale**:
- **No Hallucination**: LLM has explicit definitions, can't invent PODs
- **Context-Aware**: LLM sees full picture for each decision
- **No External Dependencies**: Self-contained, no database needed

---

## Phase 3b: Diagnostics Analysis

### Overview

Phase 3b introduces an independent analysis capability that evaluates whether Whatfix's **Diagnostics** feature was used or could have helped resolve/diagnose reported issues in support tickets.

This feature runs **independently** or **in parallel** with POD categorization, allowing users to choose:
- POD categorization only (`--analysis-type pod`)
- Diagnostics analysis only (`--analysis-type diagnostics`)
- Both analyses in parallel (`--analysis-type both`)

### Problem Statement

> "Product team needs to understand if Diagnostics feature is being utilized effectively and identify missed opportunities where Diagnostics could have prevented support tickets or enabled self-service resolution."

**Current Challenges**:
- Zendesk custom field "Was Diagnostic Panel used?" is often unreliable (incomplete, NA, or inaccurate)
- No systematic way to assess if Diagnostics COULD have helped (even when not used)
- Manual ticket review is time-consuming and doesn't scale
- Difficult to quantify Diagnostics' impact on support cost reduction

### Solution

Build an **LLM-powered Diagnostics analyzer** that:
1. Reads Zendesk custom field "Was Diagnostic Panel used?" (ID: 41001255923353)
2. Analyzes ticket synthesis to determine if Diagnostics was ACTUALLY used
3. Evaluates if Diagnostics COULD have helped resolve/diagnose the issue
4. Provides ternary assessment ("yes", "no", "maybe") with confidence scoring
5. Outputs structured JSON with reasoning for Product Manager review

### Updated Architecture - Branching Design

```
┌──────────────────────────────────────────────────────────────────┐
│                  ORCHESTRATOR (main.py)                           │
│      CLI, --analysis-type parameter, progress, JSON generation    │
└──────┬──────────────────┬──────────────────┬─────────────────────┘
       │                  │                  │
   ┌───▼────┐      ┌──────▼──────┐   ┌──────▼──────────────────────┐
   │FETCHER │      │SYNTHESIZER  │   │   ANALYSIS BRANCH           │
   │        │      │             │   │  (based on user input)      │
   │Phase 1 │      │  Phase 2    │   │                             │
   │        │      │             │   │  ┌─────────────────┐        │
   │+ custom│      │             │   │  │ POD Categorizer │        │
   │ fields │      │             │   │  │ (categorizer.py)│        │
   └────────┘      └─────────────┘   │  └─────────────────┘        │
                                     │          OR                  │
                                     │  ┌─────────────────┐        │
                                     │  │ Diagnostics     │        │
                                     │  │ Analyzer (NEW)  │        │
                                     │  │ (diagnostics_   │        │
                                     │  │  analyzer.py)   │        │
                                     │  └─────────────────┘        │
                                     │         OR                   │
                                     │  ┌─────────────────┐        │
                                     │  │  BOTH (PARALLEL)│        │
                                     │  │  POD + Diag     │        │
                                     │  └─────────────────┘        │
                                     └─────────────────────────────┘
```

### Module Updates - Phase 3b

See **diagnostics_analyzer.py** in [Module Specifications](#module-specifications) section above.

### Output Files - Phase 3b

See **Output JSON Structure** section above for diagnostics analysis output format.

#### When `--analysis-type both`: Two Separate Files

- `output_pod_YYYYMMDD_HHMMSS.json` (POD categorization)
- `output_diagnostics_YYYYMMDD_HHMMSS.json` (Diagnostics analysis)

Both files generated in parallel with combined metadata.

### Key Design Decisions - Phase 3b

#### 1. Independent Branching Architecture

- POD categorization and Diagnostics analysis are independent
- Users choose which analysis to run via `--analysis-type`
- "both" mode runs analyses in parallel using `asyncio.gather()`

#### 2. Custom Field Handling

- Custom field fetched with ticket data (no extra API calls)
- Normalized to prevent LLM confusion ("Yes"/"yes"/"YES" → "Yes")
- Used as input to LLM but not blindly trusted (LLM validates against synthesis)

#### 3. Ternary Classification

- "Could Diagnostics help?" uses "yes"/"no"/"maybe" instead of binary
- Allows LLM to express uncertainty for ambiguous cases
- "maybe" + "not confident" = clear signal for manual review

#### 4. Separate Output Files

- Different analysis types have different metadata needs
- Easier to consume independently for different stakeholders
- Clear separation of concerns

#### 5. LLM Prompt Validation Gate

- Diagnostics prompt reviewed and approved by Product Manager (Reehan)
- Includes explicit capabilities/limitations to reduce hallucination
- Two concrete examples anchor the LLM's decision-making

---

## Phase 3c: Multi-Model LLM Support

### Overview

Phase 3c introduces support for multiple LLM providers, allowing the application to switch between:
1. **Google Gemini** (free tier, rate-limited)
2. **Azure OpenAI GPT-4o** (enterprise deployment, higher limits)

This enables cost optimization and prevents API limit exhaustion during large-scale analysis.

### Problem Statement - Phase 3c

**Current Challenges:**
- Single LLM dependency (Gemini free tier only)
- Hitting free-tier rate limits (10 requests/min) during bulk analysis
- No fallback or alternative when Gemini quota is exhausted
- Gemini free tier unreliable for production-scale workloads

**Business Impact:**
- Cannot process large ticket batches (>100 tickets) without multi-hour delays
- Gemini free tier lacks SLA guarantees
- Organization has unused Azure OpenAI capacity (enterprise deployment)

**Solution Requirement:**
- Support Azure OpenAI GPT-4o as alternative LLM provider
- Allow runtime selection between providers via CLI
- Maintain backward compatibility with existing Gemini-based code
- No automatic fallback (fail hard to prevent half-baked results)

### Technical Architecture - Phase 3c

#### Factory Pattern Implementation

```
┌──────────────────────────────────────────────────────────────┐
│                   LLMProviderFactory                         │
│  Centralized provider selection and instantiation            │
└──────────┬──────────────────┬────────────────────────────────┘
           │                  │
    ┌──────▼─────────┐  ┌────▼──────────────┐
    │ GeminiClient   │  │ AzureOpenAIClient │
    │ (free tier)    │  │ (enterprise)      │
    └────────────────┘  └───────────────────┘
           │                  │
           │                  │
    Both implement: generate_content(prompt) → LLMResponse

┌──────────────────────────────────────────────────────────────┐
│                       Consumers                               │
│  GeminiSynthesizer, DiagnosticsAnalyzer                      │
│  Use factory to get provider, agnostic to implementation     │
└──────────────────────────────────────────────────────────────┘
```

See **llm_provider.py** in [Module Specifications](#module-specifications) section above.

### Technical Decisions - Phase 3c

#### 1. Factory Pattern Architecture

**Decision:** Use Factory Pattern instead of Strategy Pattern

**Rationale:**
- **Simplicity:** Factory centralizes provider creation logic
- **No runtime switching:** Once initialized, provider doesn't change during execution
- **Cleaner initialization:** Consumers (synthesizer, analyzer) don't need to know provider details
- **Easier testing:** Can mock factory to return test providers

**Alternative Considered:** Strategy Pattern with runtime provider swapping
- **Rejected because:** No use case for switching providers mid-execution
- Adds unnecessary complexity for zero benefit

#### 2. No Automatic Fallback

**Decision:** Retry Azure on failure, then fail hard (no fallback to Gemini)

**Rationale:**
- **Data integrity:** Gemini free tier may give incomplete results on large datasets
- **Explicit user control:** User should decide which provider to use for each run
- **Avoid mixed results:** Falling back mid-run creates inconsistent output
- **Easier debugging:** Clear failure point instead of silent degradation

**User's explicit requirement:**
> "When the data is large, falling back to Gemini which is a free tier API will give me half baked results. Fail hard, I can choose to re-run when I want."

#### 3. Global Model Provider Selection

**Decision:** Single `--model-provider` applies to ALL analysis phases (synthesis + diagnostics + POD)

**Rationale:**
- **Simplicity:** Easier CLI interface, fewer parameters to track
- **Consistency:** Same LLM for entire run ensures consistent analysis quality
- **Cost tracking:** Clear which provider was used for billing purposes
- **User requirement:** User requested CLI parameter, not per-phase selection

#### 4. Azure OpenAI Configuration

**Decision:** Use modern `openai` Python SDK (v2.7.1+) with `AzureOpenAI` class

**Rationale:**
- **Official recommendation:** Microsoft's latest Azure OpenAI docs recommend this approach
- **Deprecation:** Old `openai.api_type = "azure"` config is deprecated in v1.0+
- **Active maintenance:** v2.x is actively maintained, v0.28.1 is EOL
- **Better error handling:** Modern SDK has improved error messages and retry logic

**Implementation Details:**
```python
from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2024-02-01"  # Latest stable version
)

response = client.chat.completions.create(
    model=AZURE_OPENAI_DEPLOYMENT_NAME,  # Deployment name, not model name
    messages=[...],
    temperature=0.3,  # Lower for factual analysis
    max_tokens=2000
)
```

#### 5. Backward Compatibility

**Decision:** Default `model_provider="gemini"` for all components

**Rationale:**
- **No breaking changes:** Existing code works without modification
- **Gradual migration:** Users can test Azure without rewriting code
- **Safe rollback:** If Azure has issues, revert by removing `--model-provider` flag

#### 6. Custom Field Bug Fix

**Decision:** Fix `normalize_diagnostics_field()` to correctly interpret Zendesk enum values

**Problem:**
- Zendesk stores values as `"diagnostic_yes"` and `"diagnostic_no"` (enum IDs)
- Old code checked for `"yes"` and `"no"` → found nothing → marked as `"unknown"`

**Fix:**
```python
# BEFORE (incorrect)
if normalized in ["yes", "y", "true", "1"]:
    return "yes"

# AFTER (correct)
if normalized == "diagnostic_yes":
    return "Yes"  # Note: Capital "Y" for display consistency
elif normalized == "diagnostic_no":
    return "No"
else:
    return "Not Applicable"  # Changed from "unknown"
```

### Configuration Requirements - Phase 3c

#### Environment Variables (`.env`)

**Required for Gemini (existing):**
```env
GEMINI_API_KEY=your_gemini_key_here
```

**Required for Azure OpenAI (new):**
```env
AZURE_OPENAI_ENDPOINT=https://openai-for-product.openai.azure.com/
AZURE_OPENAI_API_KEY=your_azure_key_here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-01
```

**Best Practice:** Keep BOTH sets of credentials in `.env`
- Application validates credentials only for chosen provider at runtime
- Allows easy switching without editing `.env` each time

---

## Future Enhancements

Based on Phases 1-3c foundation:

### Phase 4: Observability & Instrumentation

See [instrumentation_plan.md](./instrumentation_plan.md) for complete Phase 4 details:
- LLM tracing & monitoring (Arize Phoenix, Langfuse OSS)
- Cost & latency tracking
- Experimentation platform integration
- Evaluation pipelines

### Phase 5: Web UI

Based on Phase 2 & 3b JSON output structure:

1. **Review Interface**: Display synthesis + categorization/diagnostics for human review
2. **Confidence Filtering**: Filter tickets by confidence level
3. **POD Dashboard**: Visualize ticket distribution across PODs
4. **Diagnostics Dashboard**: Visualize missed Diagnostics opportunities
5. **Recategorization**: Allow manual POD/Diagnostics override with audit trail
6. **Bulk Actions**: Approve/reject multiple analyses at once
7. **Export**: Download filtered/reviewed tickets as CSV/Excel
8. **Impact Analysis**: Calculate support cost savings from Diagnostics self-service

---

## Notes

- Zendesk account: Enterprise (assumed)
- Zendesk subdomain: `whatfix`
- Authentication: Email/token format (`email/token`)
- All timestamps in IST (Indian Standard Time)
- Output format optimized for future web app integration
- Terminal-based for MVP, no fancy UI yet
- Comprehensive inline comments for code maintainability
- Modular architecture allows future analysis types to be added easily

---

**Last Updated:** 2025-11-09 (Phase 3c completed)

**Next Steps:** See [instrumentation_plan.md](./instrumentation_plan.md) for Phase 4 observability implementation.
