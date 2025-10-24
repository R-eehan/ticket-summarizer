# Zendesk Ticket Summarizer - Implementation Plan

## Overview

A terminal-based application that fetches Zendesk tickets, retrieves all comments, and uses Google Gemini 2.5 Pro to synthesize comprehensive summaries for product area attribution.

## Problem Statement

Current ticket categorization solution only examines subject, description, and custom fields, missing crucial context from comment threads. This leads to:
- Incorrect product area attribution
- Missed nuances in issue resolution
- Incomplete understanding of actual vs. reported issues

## Solution

Build a CLI tool that:
1. Takes CSV input with ticket IDs
2. Fetches complete ticket data (subject, description, ALL comments)
3. Uses LLM to synthesize: issue reported, root cause, summary, resolution
4. Outputs structured JSON for future web application integration

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (main.py)                    │
│  - CLI interface, progress tracking, final JSON generation   │
└──────────────────┬────────────────────────────┬──────────────┘
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

## File Structure

```
ticket-summarizer/
├── plan.md                 # This file
├── README.md               # Setup & usage instructions
├── requirements.txt        # Python dependencies
├── .gitignore             # Git ignore patterns
├── .env.example           # Environment variable template
├── main.py                # Entry point & orchestrator
├── config.py              # Configuration & constants
├── utils.py               # Utilities (logging, timezone, etc.)
├── fetcher.py             # Zendesk API client
├── synthesizer.py         # Gemini LLM client
├── logs/                  # Application logs (auto-created)
│   └── app_YYYYMMDD.log
└── input_tickets.csv      # User-provided input (example)
```

## Module Specifications

### 1. config.py - Configuration Constants

**Purpose**: Central configuration management

**Contents**:
- Zendesk credentials (subdomain, email, API token from env)
- Gemini API key (from env)
- Rate limiting configuration:
  - Zendesk: 10 concurrent requests
  - Gemini: 5 concurrent requests
  - Retry: 1 attempt with 2-second delay
- LLM prompt template
- Logging configuration

### 2. utils.py - Utilities

**Purpose**: Shared utility functions

**Functions**:
- `convert_to_ist(utc_timestamp)`: Convert UTC to IST (UTC+5:30)
- `setup_logger(name)`: Configure structured logging
- `strip_html(text)`: Remove HTML/markdown from text
- `retry_on_failure(func, retries=1)`: Retry decorator with exponential backoff

**Custom Exceptions**:
- `ZendeskAPIError`: Zendesk API failures
- `GeminiAPIError`: Gemini API failures
- `TicketNotFoundError`: Ticket doesn't exist

### 3. fetcher.py - Zendesk Data Fetcher

**Purpose**: Fetch ticket data from Zendesk API

**Class**: `ZendeskFetcher`

**Methods**:
- `fetch_ticket(ticket_id)`: Fetch single ticket metadata
- `fetch_comments(ticket_id)`: Fetch all comments for a ticket
- `fetch_ticket_complete(ticket_id)`: Fetch ticket + all comments (combined)
- `fetch_multiple_tickets(ticket_ids, progress_callback)`: Parallel fetch with progress

**Features**:
- Rate limiting using `asyncio.Semaphore` (max 10 concurrent)
- Retry logic (1 retry on failure with 2s delay)
- Progress callbacks for real-time updates
- Comprehensive error handling and logging
- Basic auth with email/token format

**API Endpoints**:
- `GET /api/v2/tickets/{ticket_id}` - Fetch ticket
- `GET /api/v2/tickets/{ticket_id}/comments` - Fetch comments

### 4. synthesizer.py - Gemini LLM Synthesizer

**Purpose**: Use Gemini 2.5 Pro to analyze and synthesize ticket data

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

### 5. main.py - Orchestrator & CLI

**Purpose**: Main entry point, orchestrates entire workflow

**Workflow**:
1. Parse CLI arguments (input CSV path)
2. Load CSV (Serial No, Ticket ID)
3. Initialize fetcher & synthesizer
4. **PHASE 1**: Fetch all tickets in parallel
   - Display real-time progress for each ticket
   - Track success/failure
5. **PHASE 2**: Synthesize fetched tickets in parallel
   - Display real-time progress for each ticket
   - Track success/failure
6. Generate final JSON with IST timestamps
7. Save to `output_YYYYMMDD.json`
8. Display summary statistics

**CLI Interface**:
```bash
python main.py <input_csv_path>
```

**Terminal Output Example**:
```
╔══════════════════════════════════════════════════════════╗
║   Zendesk Ticket Summarizer - Powered by Gemini 2.5 Pro  ║
╚══════════════════════════════════════════════════════════╝

[2025-05-10 14:30:15 IST] Loading CSV: input_tickets.csv
[2025-05-10 14:30:15 IST] Found 100 tickets to process

[PHASE 1] Fetching Ticket Data from Zendesk
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100/100 [00:45<00:00, 2.2 tickets/s]
✓ Successfully fetched: 98 tickets
✗ Failed: 2 tickets (IDs: 12345, 67890)

[PHASE 2] Synthesizing with Gemini 2.5 Pro
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 98/98 [01:30<00:00, 1.1 tickets/s]
✓ Successfully synthesized: 96 tickets
✗ Failed: 2 tickets (IDs: 11111, 22222)

[2025-05-10 14:32:30 IST] Generating output JSON...
[2025-05-10 14:32:31 IST] ✓ Output saved: output_20250510.json

╔══════════════════════ SUMMARY ═══════════════════════════╗
║ Total Tickets:           100                             ║
║ Successfully Processed:   96                             ║
║ Failed:                    4                             ║
║ Total Time:             2m 16s                           ║
║ Log File:    logs/app_20250510.log                      ║
╚══════════════════════════════════════════════════════════╝
```

## Output JSON Structure

```json
{
  "metadata": {
    "total_tickets": 100,
    "successfully_processed": 96,
    "failed": 4,
    "processed_at": "2025-05-10T14:32:30+05:30",
    "processing_time_seconds": 136.5
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
      "comments": [
        {
          "id": "46402347403033",
          "author_id": "123456789",
          "author_name": "Katherine Hudson",
          "created_at": "2025-05-01T07:47:00+05:30",
          "body": "Hi, I added a smart tip but cannot get it to display...",
          "public": true
        }
      ],
      "synthesis": {
        "issue_reported": "Smart tip not displaying in preview mode despite correct configuration",
        "root_cause": "CSS selector was missing, causing element targeting failure",
        "summary": "Customer reported a smart tip that wouldn't display in preview mode despite multiple attempts at configuration. Support engineer investigated and discovered the CSS selector was not properly configured for the dynamic element. After reselecting the smart tip and adding the necessary CSS selector, the smart tip began working as expected. Customer confirmed resolution in production environment.",
        "resolution": "Reselected smart tip and added necessary CSS selector to fix element targeting"
      },
      "processing_status": "success"
    },
    {
      "ticket_id": "78789",
      "serial_no": 2,
      "processing_status": "failed",
      "error": "Ticket not found - may have been deleted"
    }
  ],
  "errors": [
    {
      "ticket_id": "78789",
      "serial_no": 2,
      "error_type": "TicketNotFoundError",
      "message": "HTTP 404: Ticket not found"
    }
  ]
}
```

## Input Format

**CSV Structure** (`input_tickets.csv`):
```csv
Serial No,Ticket ID
1,78788
2,78969
3,78985
...
```

## Environment Configuration

**File**: `.env`

```env
ZENDESK_API_KEY=your_zendesk_api_token_here
GEMINI_API_KEY=your_gemini_api_key_here
ZENDESK_SUBDOMAIN=whatfix
ZENDESK_EMAIL=avinash.pai@whatfix.com
```

## Dependencies

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
```

## Technical Decisions

### 1. Parallelization Strategy

- **Two-Phase Approach**: Separate fetch and synthesis phases for cleaner progress tracking
- **Fetch Phase**: 10 concurrent Zendesk API calls (conservative for Enterprise plan)
- **Synthesis Phase**: 5 concurrent Gemini API calls (respecting API limits)
- **Rejected Pipeline Approach**: Would make progress tracking complex

### 2. IST Timezone Handling

All timestamps converted from UTC to IST (UTC+5:30):
```python
import pytz
from datetime import datetime

def convert_to_ist(utc_timestamp):
    ist = pytz.timezone('Asia/Kolkata')
    return utc_timestamp.astimezone(ist).isoformat()
```

### 3. Rate Limiting

- `asyncio.Semaphore` for concurrent request limiting
- `aiohttp` for async HTTP requests (faster than `requests`)
- Built-in delays between retries

### 4. Retry Logic

- One retry per failed request
- 2-second exponential backoff
- Both attempts logged for debugging

### 5. Error Handling

- Ticket-level failures don't stop entire process
- All errors logged with full context
- Failed tickets tracked separately in output JSON
- Custom exception classes for clarity

### 6. Logging

- **Console**: INFO level (progress updates)
- **File**: DEBUG level (full API responses, errors)
- **Format**: `[YYYY-MM-DD HH:MM:SS IST] [LEVEL] [Module] Message`
- **Location**: `logs/app_YYYYMMDD.log`

### 7. Comment Processing

- Fetch ALL comments (including internal notes)
- Strip HTML/markdown before sending to LLM (cleaner text)
- Preserve all metadata (author, timestamp, public/private)

## Testing Strategy

1. **Phase 1**: Test with 5 tickets
2. **Phase 2**: Validate JSON output structure
3. **Phase 3**: Test with 10 tickets
4. **Phase 4**: Test with 25 tickets
5. **Phase 5**: Test with 50 tickets
6. **Phase 6**: Full test with 100 tickets
7. Monitor logs for rate limiting and errors throughout

## Potential Challenges & Mitigations

| Challenge | Mitigation |
|-----------|------------|
| Zendesk rate limits hit | Conservative concurrency (10), built-in delays |
| Gemini API failures | Retry logic, detailed error logging |
| Large comment threads | No pagination limit, fetch all comments |
| Network timeouts | 30-second timeout per request, retry once |
| Memory issues (100 tickets) | Process in memory (adequate for 100 tickets) |
| HTML in comments | Strip HTML/markdown using BeautifulSoup |
| Malformed LLM responses | Robust parsing with fallbacks, detailed logging |

## Implementation Checklist

- [ ] Create project structure
- [ ] Initialize git repository
- [ ] Create requirements.txt
- [ ] Create .env.example
- [ ] Implement config.py
- [ ] Implement utils.py
- [ ] Implement fetcher.py
- [ ] Implement synthesizer.py
- [ ] Implement main.py
- [ ] Create sample input CSV
- [ ] Create README.md
- [ ] Test with 5 tickets
- [ ] Test with full dataset

## Future Enhancements (Post-MVP)

1. **Web UI**: Flask/FastAPI backend + React frontend
2. **Product Area Attribution**: ML model to categorize tickets
3. **Database**: PostgreSQL for ticket history
4. **Batch Processing**: Handle thousands of tickets
5. **Real-time Updates**: WebSocket for live progress
6. **Analytics Dashboard**: Visualize trends and patterns
7. **Export Options**: CSV, Excel, PDF reports
8. **Caching**: Cache ticket data to avoid re-fetching

## Notes

- Zendesk account: Enterprise (assumed)
- Zendesk subdomain: `whatfix`
- Authentication: Email/token format (`email/token`)
- All timestamps in IST (Indian Standard Time)
- Output format optimized for future web app integration
- Terminal-based for MVP, no fancy UI yet
