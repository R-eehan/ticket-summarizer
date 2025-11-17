# Zendesk Ticket Summarizer

A terminal-based application that fetches Zendesk support tickets, uses AI (Google Gemini or Azure OpenAI GPT-4o) to generate comprehensive summaries, and provides **flexible analysis capabilities** including POD categorization and Diagnostics feature analysis for product insights.

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

### Phase 3b: Diagnostics Analysis
- Analyzes if Whatfix's "Diagnostics" feature was used in troubleshooting
- Evaluates if Diagnostics COULD have helped resolve/diagnose the issue
- Reads Zendesk custom field "Was Diagnostic Panel used?" for validation
- Ternary assessment ("yes", "no", "maybe") with confidence scoring
- Identifies missed opportunities for self-service resolution
- Provides detailed reasoning and matched Diagnostics capabilities

### Phase 3c: Multi-Model LLM Support
- **Choose Your AI Provider**: Switch between Google Gemini (free tier) or Azure OpenAI GPT-4o (enterprise)
- **Cost Optimization**: Use Azure to avoid free-tier rate limits for bulk processing
- **No Performance Degradation**: Azure processes faster without artificial delays
- **Backward Compatible**: Defaults to Gemini, existing workflows unchanged
- **Simple CLI Flag**: `--model-provider azure` or `--model-provider gemini`
- Same analysis quality across both providers (identical prompts, consistent outputs)

### Phase 4: Arize AX Observability (NEW)
- **LLM Tracing**: Automatic capture of all Gemini and Azure OpenAI API calls with token usage, latency, and costs
- **Cloud-Based**: No self-hosted infrastructure required - traces sent to Arize AX cloud
- **Performance Monitoring**: Track request latency, error rates, and throughput in real-time
- **Search & Analysis**: Filter traces by ticket ID, model, timeframe, or custom attributes
- **Optional**: Application runs normally without tracing if credentials not configured
- **Three-Tier Instrumentation**: LLM auto-instrumentation, HTTP client tracing, business logic spans (future)
- See [docs/arize_ax_setup.md](docs/arize_ax_setup.md) for setup instructions

### General Features
- **Flexible Analysis Modes**: Choose POD categorization, Diagnostics analysis, or both in parallel
- **Flexible LLM Provider**: Choose between Gemini (free) or Azure OpenAI (enterprise)
- **Parallel Processing**: Run multiple analyses simultaneously for faster results
- Real-time progress tracking for all phases in terminal
- CSV auto-detection (supports multiple input formats)
- Comprehensive error handling and logging
- IST (Indian Standard Time) timestamp conversion
- Separate JSON output files for different analysis types

## Prerequisites

- Python 3.9 - 3.14 (tested on Python 3.12)
- Zendesk account with API access (Enterprise plan recommended)
- **At least one** of the following LLM providers:
  - **Google Gemini API key** (free tier, default)
  - **Azure OpenAI access** (enterprise, faster for bulk processing)
- **Optional**: Arize AX account for LLM observability and tracing (free tier available at [arize.com](https://arize.com))

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

   **Required (Zendesk):**
   ```env
   ZENDESK_API_KEY=your_zendesk_api_token_here
   ZENDESK_SUBDOMAIN=whatfix
   ZENDESK_EMAIL=avinash.pai@whatfix.com
   ```

   **Required for Gemini (default LLM):**
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

   **Optional - Azure OpenAI (enterprise LLM):**
   ```env
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_KEY=your_azure_api_key_here
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
   AZURE_OPENAI_API_VERSION=2024-02-01
   ```

   **Note:** You need **at least one** LLM provider configured (Gemini OR Azure). Both can be configured for easy switching.

## Usage

### Basic Usage

```bash
python main.py --input <input_csv_path> --analysis-type <pod|diagnostics|both> [--model-provider <gemini|azure>]
```

### Examples

#### Using Default Provider (Gemini)

```bash
# POD Categorization with Gemini (default)
python main.py --input input_tickets_sample.csv --analysis-type pod

# Diagnostics Analysis with Gemini
python main.py --input diagnostics_support_tickets_q3.csv --analysis-type diagnostics

# Both Analyses with Gemini
python main.py --input input_tickets_sample.csv --analysis-type both
```

#### Using Azure OpenAI (Faster for Bulk Processing)

```bash
# POD Categorization with Azure OpenAI
python main.py --input input_tickets_sample.csv --analysis-type pod --model-provider azure

# Diagnostics Analysis with Azure OpenAI
python main.py --input diagnostics_support_tickets_q3.csv --analysis-type diagnostics --model-provider azure

# Both Analyses with Azure OpenAI
python main.py --input input_tickets_sample.csv --analysis-type both --model-provider azure
```

### CLI Parameters

- `--input`: **(Required)** Path to input CSV file containing ticket IDs
- `--analysis-type`: **(Required)** Type of analysis to perform:
  - `pod`: POD categorization only
  - `diagnostics`: Diagnostics feature analysis only
  - `both`: Run both analyses in parallel (generates two separate output files)
- `--model-provider`: **(Optional)** LLM provider to use:
  - `gemini`: Google Gemini (default, free tier)
  - `azure`: Azure OpenAI GPT-4o (enterprise, faster, no rate limits)

### Choosing Between Gemini vs Azure OpenAI

| Factor | Gemini (Default) | Azure OpenAI |
|--------|------------------|--------------|
| **Cost** | Free tier | Enterprise pricing |
| **Speed** | Slower (7s delays between requests) | Faster (no artificial delays) |
| **Rate Limits** | 10 requests/min (free tier) | Higher limits (deployment-specific) |
| **Best For** | Small datasets (<50 tickets) | Bulk processing (100+ tickets) |
| **Setup** | API key only | Endpoint + API key + deployment name |
| **Quality** | Excellent | Comparable (same prompts used) |

**Recommendation:** Use Gemini for quick tests, Azure for production bulk analysis.

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
  - `GEMINI_MAX_CONCURRENT`: Max concurrent LLM API calls (default: 5)
  - `MAX_RETRIES`: Number of retry attempts (default: 1)
  - `RETRY_DELAY_SECONDS`: Delay between retries (default: 2)

- **Timeout**:
  - `REQUEST_TIMEOUT_SECONDS`: HTTP request timeout (default: 30)

- **LLM Models**:
  - `GEMINI_MODEL`: Gemini model to use (default: "gemini-flash-latest")
  - `DEFAULT_MODEL_PROVIDER`: Default provider (default: "gemini")

- **Azure OpenAI** (configured via `.env`):
  - `AZURE_OPENAI_ENDPOINT`: Your Azure resource endpoint
  - `AZURE_OPENAI_API_KEY`: Your Azure API key
  - `AZURE_OPENAI_DEPLOYMENT_NAME`: Your GPT-4o deployment name
  - `AZURE_OPENAI_API_VERSION`: API version (default: "2024-02-01")

- **Arize AX Observability** (Phase 4 - optional, configured via `.env`):
  - `ARIZE_SPACE_ID`: Your Arize Space ID (from Space Settings)
  - `ARIZE_API_KEY`: Your Arize API Key (from Space Settings → API Keys)
  - `ARIZE_PROJECT_NAME`: Project name for grouping traces (default: "ticket-analysis")
  - `ENABLE_TRACING`: Set to "false" to disable tracing (default: "true")
  - See [docs/arize_ax_setup.md](docs/arize_ax_setup.md) for detailed setup instructions

## Troubleshooting

### Common Issues

1. **"ZENDESK_API_KEY environment variable is not set"**
   - Ensure `.env` file exists and contains valid credentials
   - Check that `.env` is in the same directory as the Python files

2. **"GEMINI_API_KEY environment variable is not set"** (when using Gemini)
   - Add `GEMINI_API_KEY=your_key` to `.env`
   - Or use `--model-provider azure` if you have Azure configured

3. **"AZURE_OPENAI_ENDPOINT environment variable is not set"** (when using Azure)
   - Add all 4 Azure variables to `.env`: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT_NAME`, `AZURE_OPENAI_API_VERSION`
   - Verify endpoint URL format: `https://your-resource.openai.azure.com/`
   - Verify deployment name matches your Azure OpenAI deployment

4. **Rate Limiting Errors**
   - **Gemini**: Free tier limited to 10 req/min → Use `--model-provider azure` for bulk processing
   - **Zendesk**: Reduce `ZENDESK_MAX_CONCURRENT` in `config.py`
   - The application automatically retries once on failure

5. **Ticket Not Found**
   - Verify ticket IDs in your CSV are correct
   - Check that you have access to the tickets in Zendesk

6. **Synthesis Parsing Issues**
   - Check logs for raw LLM responses
   - Some tickets may have incomplete synthesis if LLM response format varies

7. **Azure OpenAI Errors**
   - **"ResourceNotFound"**: Check deployment name is correct (not model name)
   - **"InvalidApiKey"**: Verify Azure API key in `.env`
   - **"Unauthorized"**: Check API key permissions in Azure portal

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
- **synthesizer.py**: LLM client with response parsing (supports both providers)
- **diagnostics_analyzer.py**: Diagnostics analysis module (supports both providers)
- **categorizer.py**: POD categorization module
- **llm_provider.py**: LLM provider abstraction layer (factory pattern for Gemini/Azure)

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
