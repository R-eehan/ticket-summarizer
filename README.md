# Zendesk Ticket Summarizer

A terminal-based application that fetches Zendesk support tickets, uses Google Gemini 2.5 Pro to generate comprehensive summaries, and provides **flexible analysis capabilities** including POD categorization and Diagnostics feature analysis for product insights.

## Features

### Phase 1: Ticket Fetching & Synthesis
- Fetches complete ticket data from Zendesk (subject, description, all comments, custom fields)
- Uses Gemini 2.5 Pro LLM to synthesize:
  - Issue reported (one-liner)
  - Root cause (one-liner)
  - Summary (3-4 line paragraph)
  - Resolution (one-liner)

### Phase 2: POD Categorization
- Automatically categorizes tickets into 13 PODs using LLM-based analysis
- Provides clear reasoning for each categorization decision
- Binary confidence scoring ("confident" vs "not confident") for human review
- Suggests alternative PODs when ambiguous
- Tracks POD distribution and confidence breakdown

### Phase 3b: Diagnostics Analysis (NEW)
- Analyzes if Whatfix's "Diagnostics" feature was used in troubleshooting
- Evaluates if Diagnostics COULD have helped resolve/diagnose the issue
- Reads Zendesk custom field "Was Diagnostic Panel used?" for validation
- Ternary assessment ("yes", "no", "maybe") with confidence scoring
- Identifies missed opportunities for self-service resolution
- Provides detailed reasoning and matched Diagnostics capabilities

### General Features
- **Flexible Analysis Modes**: Choose POD categorization, Diagnostics analysis, or both in parallel
- **Parallel Processing**: Run multiple analyses simultaneously for faster results
- Real-time progress tracking for all phases in terminal
- CSV auto-detection (supports multiple input formats)
- Comprehensive error handling and logging
- IST (Indian Standard Time) timestamp conversion
- Separate JSON output files for different analysis types

## Prerequisites

- Python 3.8 or higher
- Zendesk account with API access (Enterprise plan recommended)
- Google Gemini API key

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd ticket-summarizer
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**

   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your credentials:
   ```env
   ZENDESK_API_KEY=your_zendesk_api_token_here
   ZENDESK_SUBDOMAIN=whatfix
   ZENDESK_EMAIL=avinash.pai@whatfix.com
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

## Usage

### Basic Usage

```bash
python main.py --input <input_csv_path> --analysis-type <pod|diagnostics|both>
```

### Examples

#### POD Categorization Only
```bash
python main.py --input input_tickets_sample.csv --analysis-type pod
```

#### Diagnostics Analysis Only
```bash
python main.py --input diagnostics_support_tickets_q3.csv --analysis-type diagnostics
```

#### Both Analyses in Parallel
```bash
python main.py --input input_tickets_sample.csv --analysis-type both
```

### CLI Parameters

- `--input`: **(Required)** Path to input CSV file containing ticket IDs
- `--analysis-type`: **(Required)** Type of analysis to perform:
  - `pod`: POD categorization only
  - `diagnostics`: Diagnostics feature analysis only
  - `both`: Run both analyses in parallel (generates two separate output files)

### Input CSV Format

The application auto-detects and supports two CSV formats:

**Format 1:** Serial No + Ticket ID
```csv
Serial No,Ticket ID
1,78788
2,78969
3,78985
...
```

**Format 2:** Zendesk Tickets ID (auto-generates serial numbers)
```csv
Zendesk Tickets ID
78788
78969
78985
...
```

The application will automatically detect which format you're using and process accordingly.

### Output

The application generates timestamped JSON files based on the analysis type:

- **POD Mode**: `output_pod_YYYYMMDD_HHMMSS.json`
- **Diagnostics Mode**: `output_diagnostics_YYYYMMDD_HHMMSS.json`
- **Both Mode**: Generates both files above in parallel

#### POD Categorization Output Structure

```json
{
  "metadata": {
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
      "ticket_id": "87239",
      "serial_no": 2,
      "subject": "Smart tip not displaying...",
      "description": "Hi, I added a smart tip...",
      "url": "https://whatfix.zendesk.com/agent/tickets/87239",
      "status": "solved",
      "created_at": "2025-05-01T07:47:00+05:30",
      "updated_at": "2025-05-02T10:15:00+05:30",
      "comments_count": 9,
      "comments": [...],
      "synthesis": {
        "issue_reported": "Smart tip not displaying in preview mode",
        "root_cause": "CSS selector was missing",
        "summary": "Customer reported a smart tip that wouldn't display...",
        "resolution": "Reselected smart tip and added necessary CSS selector"
      },
      "categorization": {
        "primary_pod": "Guidance",
        "reasoning": "The issue involves Smart Tips, which are explicitly a Guidance module feature...",
        "confidence": "confident",
        "confidence_reason": "Clear synthesis match with no ambiguity between PODs",
        "alternative_pods": [],
        "alternative_reasoning": null,
        "metadata": {
          "keywords_matched": ["Smart Tips", "preview mode", "display"],
          "decision_factors": [
            "Direct mention of Smart Tips in synthesis",
            "Resolution involved Guidance module fix"
          ]
        }
      },
      "processing_status": "success"
    }
  ],
  "errors": [...]
}
```

#### Diagnostics Analysis Output Structure

```json
{
  "metadata": {
    "analysis_type": "diagnostics",
    "total_tickets": 10,
    "successfully_processed": 9,
    "failed": 1,
    "diagnostics_breakdown": {
      "was_used": {
        "yes": 2,
        "no": 6,
        "unknown": 1
      },
      "could_help": {
        "yes": 5,
        "no": 3,
        "maybe": 1
      },
      "confidence": {
        "confident": 7,
        "not_confident": 2
      }
    },
    "processed_at": "2025-11-02T14:30:00+05:30",
    "processing_time_seconds": 45.2
  },
  "tickets": [
    {
      "ticket_id": "89618",
      "subject": "Blocker Role Tags Setup",
      "url": "https://whatfix.zendesk.com/agent/tickets/89618",
      "synthesis": {
        "issue_reported": "Blocker appearing for all users instead of targeted roles",
        "root_cause": "Incorrect logic (OR instead of AND) in role tags visibility rules",
        "summary": "...",
        "resolution": "Updated role tags combination to AND"
      },
      "diagnostics_analysis": {
        "was_diagnostics_used": {
          "custom_field_value": "no",
          "llm_assessment": "no",
          "confidence": "confident",
          "reasoning": "Custom field says 'No' and synthesis shows manual troubleshooting..."
        },
        "could_diagnostics_help": {
          "assessment": "yes",
          "confidence": "confident",
          "reasoning": "The issue was a visibility rule logic error (OR vs AND). Diagnostics provides real-time visibility rule evaluation status...",
          "diagnostics_capability_matched": [
            "Visibility rule evaluation status",
            "Rule condition feedback"
          ],
          "limitation_notes": null
        },
        "metadata": {
          "ticket_type": "troubleshooting",
          "analysis_timestamp": "2025-11-02T14:30:15+05:30"
        }
      },
      "processing_status": "success"
    }
  ],
  "errors": []
}
```

## Terminal Output

The application provides rich terminal output with progress tracking for all 3 phases:

```
╔══════════════════════════════════════════════════════════╗
║   Zendesk Ticket Summarizer - Powered by Gemini 2.5 Pro  ║
╚══════════════════════════════════════════════════════════╝

Loading CSV: august_L1_tickets.csv
✓ Found 10 tickets to process

[PHASE 1] Fetching Ticket Data from Zendesk
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10/10 [00:10<00:00, 1.0 tickets/s]
✓ Successfully fetched: 10 tickets

[PHASE 2] Synthesizing with Gemini 2.5 Pro
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10/10 [00:25<00:00, 0.4 tickets/s]
✓ Successfully synthesized: 10 tickets

[PHASE 3] Categorizing into PODs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10/10 [00:20<00:00, 0.5 tickets/s]
✓ Successfully categorized: 10 tickets
   • Confident: 8 tickets
   • Not Confident: 2 tickets

Generating output JSON...

╔════════════════════════ Summary ═════════════════════════╗
║ Total Tickets:            10                             ║
║ Successfully Processed:    8                             ║
║ Failed:                    2                             ║
║ Confidence Breakdown:                                    ║
║   • Confident:             8                             ║
║   • Not Confident:         2                             ║
║ POD Distribution:                                        ║
║   • Guidance:              5                             ║
║   • Hub:                   2                             ║
║   • WFE:                   3                             ║
║ Total Time:             0m 55s                           ║
║ Log File:    logs/app_20250510.log                      ║
╚══════════════════════════════════════════════════════════╝

✓ Output saved: output_20250510.json
```

### Understanding Confidence Scores

- **Confident**: The LLM clearly identified a single POD with strong evidence from the synthesis
- **Not Confident**: The issue is ambiguous between multiple PODs or lacks clear categorization signals

Tickets marked "Not Confident" should be reviewed by a human for accurate categorization.

## Logs

Detailed logs are stored in the `logs/` directory with filenames like `app_20250510.log`. The log files include:

- **Console**: INFO level (progress updates)
- **File**: DEBUG level (full API responses, errors)

Check logs for detailed debugging information if issues occur.

## Configuration

Key configuration options can be modified in `config.py`:

- **Rate Limiting**:
  - `ZENDESK_MAX_CONCURRENT`: Max concurrent Zendesk API calls (default: 10)
  - `GEMINI_MAX_CONCURRENT`: Max concurrent Gemini API calls (default: 5)
  - `MAX_RETRIES`: Number of retry attempts (default: 1)
  - `RETRY_DELAY_SECONDS`: Delay between retries (default: 2)

- **Timeout**:
  - `REQUEST_TIMEOUT_SECONDS`: HTTP request timeout (default: 30)

- **LLM Model**:
  - `GEMINI_MODEL`: Gemini model to use (default: "gemini-2.0-flash-exp")

## Troubleshooting

### Common Issues

1. **"ZENDESK_API_KEY environment variable is not set"**
   - Ensure `.env` file exists and contains valid credentials
   - Check that `.env` is in the same directory as the Python files

2. **Rate Limiting Errors**
   - Reduce `ZENDESK_MAX_CONCURRENT` or `GEMINI_MAX_CONCURRENT` in `config.py`
   - The application automatically retries once on failure

3. **Ticket Not Found**
   - Verify ticket IDs in your CSV are correct
   - Check that you have access to the tickets in Zendesk

4. **Synthesis Parsing Issues**
   - Check logs for raw LLM responses
   - Some tickets may have incomplete synthesis if LLM response format varies

### Debug Mode

For detailed debugging, check the log file in `logs/app_YYYYMMDD.log` which contains:
- Full API requests and responses
- Detailed error messages
- Timing information

## Architecture

The application consists of modular components:

- **main.py**: Orchestrator and CLI interface
- **config.py**: Configuration and constants
- **utils.py**: Utilities (logging, timezone, HTML stripping)
- **fetcher.py**: Zendesk API client with rate limiting
- **synthesizer.py**: Gemini LLM client with response parsing

For detailed architecture documentation, see [plan.md](plan.md).

## Performance

- **Fetch Phase**: ~10 tickets/second (with 10 concurrent connections)
- **Synthesis Phase**: ~3-5 tickets/second (with 5 concurrent LLM calls)
- **100 tickets**: ~2-3 minutes total processing time

Performance may vary based on:
- Zendesk API rate limits
- Gemini API rate limits
- Network latency
- Ticket complexity (comment count)

## Testing

Start with a small sample to validate the setup:

```bash
python main.py input_tickets_sample.csv
```

The sample CSV contains 5 tickets for quick testing.

## Future Enhancements

- Web UI with real-time progress
- Product area categorization using ML
- Database storage for historical data
- Batch processing for thousands of tickets
- Export to CSV, Excel, PDF
- Analytics dashboard

## License

Internal use only - Whatfix

## Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Review [plan.md](plan.md) for architecture details
3. Contact the development team
