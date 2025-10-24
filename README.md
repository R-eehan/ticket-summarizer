# Zendesk Ticket Summarizer

A terminal-based application that fetches Zendesk support tickets and uses Google Gemini 2.5 Pro to generate comprehensive summaries for product area attribution.

## Features

- Fetches complete ticket data from Zendesk (subject, description, all comments)
- Uses Gemini 2.5 Pro LLM to synthesize:
  - Issue reported (one-liner)
  - Root cause (one-liner)
  - Summary (3-4 line paragraph)
  - Resolution (one-liner)
- Parallel processing with rate limiting for optimal performance
- Real-time progress tracking in terminal
- Comprehensive error handling and logging
- IST (Indian Standard Time) timestamp conversion
- JSON output optimized for future web application integration

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
python main.py <input_csv_path>
```

### Example

```bash
python main.py input_tickets_sample.csv
```

### Input CSV Format

Your CSV file must contain two columns with headers:

```csv
Serial No,Ticket ID
1,78788
2,78969
3,78985
...
```

- **Serial No**: Sequential number for each ticket
- **Ticket ID**: Zendesk ticket ID (numeric)

### Output

The application generates a timestamped JSON file (e.g., `output_20250510.json`) with the following structure:

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
      "subject": "Smart tip not displaying...",
      "description": "Hi, I added a smart tip...",
      "url": "https://whatfix.zendesk.com/agent/tickets/78788",
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
      "processing_status": "success"
    }
  ],
  "errors": [...]
}
```

## Terminal Output

The application provides rich terminal output with progress tracking:

```
╔══════════════════════════════════════════════════════════╗
║   Zendesk Ticket Summarizer - Powered by Gemini 2.5 Pro  ║
╚══════════════════════════════════════════════════════════╝

Loading CSV: input_tickets.csv
✓ Found 5 tickets to process

[PHASE 1] Fetching Ticket Data from Zendesk
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 5/5 [00:05<00:00, 1.0 tickets/s]
✓ Successfully fetched: 5 tickets

[PHASE 2] Synthesizing with Gemini 2.5 Pro
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 5/5 [00:15<00:00, 0.3 tickets/s]
✓ Successfully synthesized: 5 tickets

Generating output JSON...

╔════════════════════════ Summary ═════════════════════════╗
║ Total Tickets:             5                             ║
║ Successfully Processed:    5                             ║
║ Failed:                    0                             ║
║ Total Time:             0m 23s                           ║
║ Log File:    logs/app_20250510.log                      ║
╚══════════════════════════════════════════════════════════╝

✓ Output saved: output_20250510.json
```

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
