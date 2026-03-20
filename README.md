# Zendesk Ticket Summarizer

A terminal-based application that fetches Zendesk support tickets, uses AI (Azure OpenAI GPT-4o or Google Gemini) to generate comprehensive summaries, and provides flexible analysis capabilities including POD categorization and Diagnostics gap analysis for product insights.

## Features

### Ticket Fetching & Synthesis
- Fetches complete ticket data from Zendesk (subject, description, all comments, custom fields)
- Uses LLM to synthesize:
  - Issue reported (one-liner)
  - Root cause (one-liner, cross-validated against support agent's root cause)
  - Summary (3-4 line paragraph with key turning points)
  - Resolution (one-liner)
- **Structured outputs** via Pydantic schemas — JSON enforced at generation time (no fragile regex)
- Comment threads formatted with structural markers `[Comment 3/12 | Agent | Day 3]`

### POD Categorization
- Categorizes tickets into 13 PODs using LLM-based analysis
- 3 few-shot worked examples for ambiguous edge cases (WFE vs Guidance, etc.)
- Binary confidence scoring ("confident" vs "not confident")
- Suggests alternative PODs when ambiguous

### Diagnostics Gap Analysis
- Analyzes if Whatfix's "Diagnostics" feature was used in troubleshooting
- Evaluates if Diagnostics COULD have helped: split into **Triage** (identification) and **Fix** (resolution)
- Gap area taxonomy with 11 triage + 10 fix predefined categories
- Anti-hallucination rules with **evidence citation** requirement
- Ternary assessment ("yes", "no", "maybe") with confidence scoring

### Multi-Model LLM Support
- **Azure OpenAI GPT-4o** (primary, enterprise) — 10 concurrent requests, no delays
- **Google Gemini** (secondary, free tier) — configurable model via `.env`
- Provider-aware rate limiting and concurrency
- Shared rate limiter prevents doubling request rate in "both" analysis mode
- Native structured outputs on both providers

## Prerequisites

- Python 3.12+
- Zendesk account with API access
- **At least one** LLM provider:
  - **Azure OpenAI** (recommended for 200+ tickets)
  - **Google Gemini API key** (free tier, good for small samples)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/R-eehan/ticket-summarizer.git
   cd ticket-summarizer
   ```

2. **Set up conda environment:**
   ```bash
   conda create -n ticket-summarizer python=3.12 -y
   conda activate ticket-summarizer
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your credentials:

   **Required (Zendesk):**
   ```env
   ZENDESK_API_KEY=your_zendesk_api_token
   ZENDESK_SUBDOMAIN=whatfix
   ZENDESK_EMAIL=your_email@whatfix.com
   ```

   **Azure OpenAI (recommended):**
   ```env
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_KEY=your_azure_api_key
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
   AZURE_OPENAI_API_VERSION=2024-10-21
   ```

   **Gemini (optional, for quality comparison):**
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   GEMINI_MODEL=gemini-2.5-flash
   # Options: gemini-2.5-flash (stable), gemini-3.1-flash-lite-preview (newest free tier)
   ```

   **Note:** You can run Azure-only without setting `GEMINI_API_KEY`.

## Usage

```bash
python main.py --input <csv_path> --analysis-type <pod|diagnostics|both> [--model-provider <gemini|azure>]
```

### Examples

```bash
# Diagnostics analysis with Azure (recommended for bulk)
python main.py --input tickets.csv --analysis-type diagnostics --model-provider azure

# POD categorization with Azure
python main.py --input tickets.csv --analysis-type pod --model-provider azure

# Both analyses in parallel
python main.py --input tickets.csv --analysis-type both --model-provider azure

# Small sample with Gemini (free tier, quality comparison)
python main.py --input test_5_tickets.csv --analysis-type diagnostics --model-provider gemini
```

### CLI Parameters

| Parameter | Required | Options | Description |
|-----------|----------|---------|-------------|
| `--input` | Yes | File path | CSV with ticket IDs |
| `--analysis-type` | Yes | `pod`, `diagnostics`, `both` | Analysis mode |
| `--model-provider` | No | `gemini` (default), `azure` | LLM provider |

### Provider Comparison

| Factor | Azure OpenAI (Recommended) | Gemini Free Tier |
|--------|---------------------------|------------------|
| **Concurrency** | 10 concurrent (configurable) | 1 sequential |
| **Speed** | ~15-20 min for 500 tickets | ~60+ min for 500 tickets |
| **Rate Limits** | 300+ RPM (Tier 1) | 10-15 RPM |
| **Daily Limit** | Unlimited (pay-per-use) | 250-1000 RPD |
| **Best For** | Production runs (200-500 tickets) | Quality comparison (30-50 tickets) |
| **Cost** | Enterprise pricing | Free |

### Input CSV Format

Two formats auto-detected:

```csv
# Format 1: Serial No + Ticket ID
Serial No,Ticket ID
1,78788
2,78969

# Format 2: Zendesk Tickets ID only
Zendesk Tickets ID
78788
78969
```

### Output

Generates timestamped JSON + CSV files:

- **POD Mode**: `output_pod_YYYYMMDD_HHMMSS.json` + `.csv`
- **Diagnostics Mode**: `output_diagnostics_YYYYMMDD_HHMMSS.json` + `.csv`
- **Both Mode**: Both file pairs generated in parallel

CSV is designed for Excel pivot table analysis. JSON contains full structured data.

## Configuration

Key settings in `config.py` and `.env`:

| Setting | Default | Description |
|---------|---------|-------------|
| `AZURE_MAX_CONCURRENT` | 10 | Concurrent Azure API calls |
| `AZURE_REQUEST_DELAY` | 0 | Seconds between Azure calls |
| `GEMINI_MAX_CONCURRENT` | 1 | Concurrent Gemini API calls |
| `GEMINI_REQUEST_DELAY` | 7 | Seconds between Gemini calls (10 RPM limit) |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model identifier |
| `AZURE_OPENAI_API_VERSION` | `2024-10-21` | Azure API version |
| `ZENDESK_MAX_CONCURRENT` | 10 | Concurrent Zendesk API calls |

All rate limiting settings are overridable via `.env`.

## Architecture

```
main.py                  CLI orchestrator, shared semaphore
  |
config.py                Configuration, prompts, rate limits
schemas.py               Pydantic schemas for structured LLM outputs
  |
llm_provider.py          Factory pattern: Azure + Gemini providers
  |                      Native structured outputs on both
  |
fetcher.py               Zendesk API client (async, 10 concurrent)
synthesizer.py           Ticket synthesis (structured output)
categorizer.py           POD categorization (structured output, few-shot)
diagnostics_analyzer.py  Diagnostics gap analysis (structured output)
csv_exporter.py          CSV export for pivot tables
utils.py                 Logging, HTML stripping, validation
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| `max_tokens unsupported` | Update `.env`: `AZURE_OPENAI_API_VERSION=2024-10-21` |
| `ZENDESK_API_KEY not set` | Add credentials to `.env` |
| `AZURE_OPENAI_ENDPOINT not set` | Add all 4 Azure vars to `.env` |
| Rate limiting (429) | Use Azure for bulk; reduce concurrency in `.env` |
| Ticket not found | Verify ticket IDs exist and you have Zendesk access |

Check `logs/app_YYYYMMDD.log` for detailed debug info.

## License

Internal use only - Whatfix
