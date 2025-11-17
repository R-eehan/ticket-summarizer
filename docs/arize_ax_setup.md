# Arize AX Observability Setup Guide

**Phase 4: Cloud-Based LLM Observability & Tracing**

This guide walks you through setting up Arize AX cloud observability for the ticket-summarizer application. Arize AX provides comprehensive LLM tracing, monitoring, and analytics without requiring self-hosted infrastructure.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Arize AX Account Setup](#arize-ax-account-setup)
4. [Configuration](#configuration)
5. [Package Installation](#package-installation)
6. [Verification](#verification)
7. [Understanding Traces](#understanding-traces)
8. [Troubleshooting](#troubleshooting)
9. [Advanced Configuration](#advanced-configuration)

---

## Overview

### What is Arize AX?

Arize AX is a cloud-based AI observability platform that provides:
- **LLM Tracing**: Automatic capture of LLM calls, prompts, responses, token usage
- **Performance Monitoring**: Latency tracking, error rates, throughput analysis
- **Cost Tracking**: Token consumption and estimated costs per model
- **Span Visualization**: Hierarchical trace view showing request flow
- **Search & Filtering**: Query traces by ticket ID, model, timeframe, etc.

### Architecture

The ticket-summarizer uses a **three-tier instrumentation strategy**:

#### **Tier 1: LLM Provider Auto-Instrumentation**
- **Google GenAI (Gemini)**: Captures all Gemini API calls automatically
- **Azure OpenAI**: Captures all Azure OpenAI API calls automatically
- **Attributes Captured**: Model name, prompt, response, token counts, latency

#### **Tier 2: Business Logic Manual Spans** *(Future Enhancement)*
- Synthesis span: Ticket summarization process
- Categorization span: POD assignment logic
- Diagnostics span: Diagnostics applicability analysis

#### **Tier 3: API Auto-Instrumentation**
- **Zendesk HTTP Calls**: Captures ticket fetch operations via aiohttp
- **Attributes Captured**: HTTP method, URL, status code, latency

### Data Flow

```
┌─────────────────┐
│   main.py       │  → Calls setup_instrumentation()
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  instrumentation.py                                     │
│  ┌───────────────────────────────────────────────────┐ │
│  │  arize.otel.register()                            │ │
│  │  - Creates TracerProvider                         │ │
│  │  - Configures OTLP exporter to Arize Cloud       │ │
│  │  - Authenticates with Space ID & API Key         │ │
│  └───────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │  OpenAIInstrumentor().instrument()                │ │
│  │  - Auto-instruments Azure OpenAI SDK              │ │
│  └───────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │  GoogleGenAIInstrumentor().instrument()           │ │
│  │  - Auto-instruments Google GenAI SDK (Gemini)     │ │
│  └───────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │  AioHttpClientInstrumentor().instrument()         │ │
│  │  - Auto-instruments aiohttp HTTP client           │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Application Runtime                                    │
│  - LLM calls (Gemini, Azure OpenAI)                    │
│  - HTTP calls (Zendesk API)                            │
│  → Spans automatically created and exported            │
└────────┬────────────────────────────────────────────────┘
         │
         ▼ (OTLP over gRPC)
┌─────────────────────────────────────────────────────────┐
│  Arize AX Cloud (US Region)                            │
│  - Receives spans via OTLP protocol                    │
│  - Stores traces for 30 days (free tier)               │
│  - Provides UI for visualization & analysis            │
└─────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- **Python 3.9 - 3.14** (tested on Python 3.12)
- **Conda environment** named `ticket-summarizer` (recommended)
- **Arize AX account** (free tier available)
- **Active Arize Space** (created during signup)

---

## Arize AX Account Setup

### Step 1: Sign Up for Arize AX

1. Visit [https://arize.com/platform/](https://arize.com/platform/)
2. Click **"Start Free"** or **"Sign Up"**
3. Choose authentication method:
   - Google OAuth
   - GitHub OAuth
   - Email + Password

### Step 2: Create a Space

After signing up, you'll be prompted to create your first **Space**:
- **Space Name**: Enter a name (e.g., "Whatfix Ticket Analysis")
- **Space ID**: Auto-generated unique identifier (you'll need this later)
- **Region**: Select **US** (default) or **EU** based on your location

**Important**: Note down your **Space ID** - you'll need it for configuration.

### Step 3: Retrieve API Key

1. Navigate to **Space Settings** (gear icon in top-right)
2. Go to **API Keys** tab
3. Click **"Generate New API Key"**
4. **Copy the API Key immediately** - it's only shown once!
5. Store it securely (you'll add it to `.env` later)

**Security Note**: Treat your API Key like a password. Never commit it to version control.

### Step 4: Verify Space ID

Your Space ID can be found in:
- **Space Settings** → **General** tab
- **URL** when viewing your space: `https://app.arize.com/organizations/[SPACE_ID]/spaces`

---

## Configuration

### Step 1: Update `.env` File

Add the following to your `.env` file (create from `.env.example` if needed):

```bash
# Arize AX Observability (Phase 4)
ARIZE_SPACE_ID=your-actual-space-id-here
ARIZE_API_KEY=your-actual-api-key-here
ARIZE_PROJECT_NAME=ticket-analysis
```

**Configuration Details**:
- `ARIZE_SPACE_ID`: Your Arize Space unique identifier (from Step 2)
- `ARIZE_API_KEY`: Your API Key (from Step 3)
- `ARIZE_PROJECT_NAME`: Project name for grouping traces (can be customized)

### Step 2: Verify Configuration

```bash
# Ensure .env is loaded
cat .env | grep ARIZE
```

**Expected Output**:
```
ARIZE_SPACE_ID=abc123xyz...
ARIZE_API_KEY=arize_api_key_...
ARIZE_PROJECT_NAME=ticket-analysis
```

---

## Package Installation

### Step 1: Activate Conda Environment

```bash
conda activate ticket-summarizer
```

### Step 2: Install New Packages

```bash
pip install --upgrade \
  google-genai \
  arize-otel \
  openinference-instrumentation-openai \
  openinference-instrumentation-google-genai \
  opentelemetry-instrumentation-aiohttp-client
```

**Package Breakdown**:
- `google-genai`: New unified Google GenAI SDK (replaces deprecated `google-generativeai`)
- `arize-otel`: Arize convenience wrapper for OpenTelemetry
- `openinference-instrumentation-openai`: Auto-instrumentation for Azure OpenAI
- `openinference-instrumentation-google-genai`: Auto-instrumentation for Gemini
- `opentelemetry-instrumentation-aiohttp-client`: Auto-instrumentation for HTTP calls

### Step 3: Verify Installation

```bash
python -c "from arize.otel import register; print('✓ Arize OTEL installed')"
python -c "from google import genai; print('✓ Google GenAI SDK installed')"
python -c "from openinference.instrumentation.openai import OpenAIInstrumentor; print('✓ OpenAI instrumentor installed')"
python -c "from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor; print('✓ Google GenAI instrumentor installed')"
```

**Expected Output**:
```
✓ Arize OTEL installed
✓ Google GenAI SDK installed
✓ OpenAI instrumentor installed
✓ Google GenAI instrumentor installed
```

---

## Verification

### Step 1: Run a Test Ticket

```bash
python main.py \
  --input test_tickets.csv \
  --analysis-type pod \
  --model-provider gemini
```

**Expected Instrumentation Output** (at startup):
```
[Instrumentation] ✅ Arize AX instrumentation enabled
  - Project: ticket-analysis
  - Endpoint: Arize US Cloud
  - Environment: local
  - Tier 1 (LLM): Auto-instrumented (OpenAI, Google GenAI)
  - Tier 2 (Business Logic): Manual spans available (synthesis, categorization, diagnostics)
  - Tier 3 (Zendesk API): Auto-instrumented (aiohttp)
  - View traces: https://app.arize.com/organizations/[YOUR_SPACE_ID]/spaces
```

### Step 2: Check Arize AX Dashboard

1. Open the link from instrumentation output (or go to [https://app.arize.com](https://app.arize.com))
2. Navigate to **Projects** → **ticket-analysis**
3. You should see traces appear within **5-10 seconds**

**What to Look For**:
- **Trace Count**: Should match number of tickets processed
- **Spans**: Each trace should contain multiple spans (LLM calls, HTTP calls)
- **Attributes**: Click a span to see model name, token counts, latency

### Step 3: Inspect a Trace

Click on a trace to view the **Trace Details** page:

**Expected Span Hierarchy**:
```
📊 Root Span: ticket_summarization (if Tier 2 implemented)
  ├─ 🌐 HTTP GET: Zendesk API - Fetch Ticket (Tier 3)
  ├─ 🌐 HTTP GET: Zendesk API - Fetch Comments (Tier 3)
  ├─ 🤖 LLM Call: Google GenAI - Synthesis (Tier 1)
  │   ├─ Attributes: model=gemini-flash-latest, tokens=1234, latency=2.3s
  ├─ 🤖 LLM Call: Google GenAI - Categorization (Tier 1)
  │   ├─ Attributes: model=gemini-flash-latest, tokens=567, latency=1.1s
```

---

## Understanding Traces

### Key Terminology

- **Trace**: A complete request flow from start to finish (e.g., one ticket's processing)
- **Span**: A single operation within a trace (e.g., one LLM call, one HTTP request)
- **Attributes**: Metadata attached to spans (e.g., `ticket_id=12345`, `model=gpt-4o`)
- **Duration**: Time taken for a span to complete (latency)

### Span Attributes (Tier 1 - LLM)

Auto-captured by OpenInference instrumentors:

| Attribute | Example Value | Description |
|-----------|---------------|-------------|
| `llm.model_name` | `gemini-flash-latest` | Model used for generation |
| `llm.input_messages` | `[{"role": "user", "content": "..."}]` | Prompt sent to LLM |
| `llm.output_messages` | `[{"role": "assistant", "content": "..."}]` | LLM response |
| `llm.token_count.prompt` | `1523` | Tokens in prompt |
| `llm.token_count.completion` | `487` | Tokens in response |
| `llm.token_count.total` | `2010` | Total tokens |
| `llm.invocation_parameters` | `{"temperature": 0.3}` | Model parameters |

### Filtering & Search

Use the Arize AX UI to filter traces by:
- **Time Range**: Last 1 hour, 24 hours, 7 days, custom
- **Model**: Filter by `gemini-flash-latest`, `gpt-4o`, etc.
- **Status**: Success, error, timeout
- **Latency**: Slow requests (e.g., >5 seconds)
- **Custom Attributes**: Search by `ticket_id`, `analysis_type`, etc. (Tier 2)

---

## Troubleshooting

### Issue 1: "Arize credentials not configured"

**Symptom**:
```
[Instrumentation] ⚠️  Arize credentials not configured - skipping instrumentation
```

**Solution**:
1. Verify `.env` file exists and contains `ARIZE_SPACE_ID` and `ARIZE_API_KEY`
2. Ensure `.env` is in the project root directory
3. Check that `python-dotenv` is installed: `pip show python-dotenv`
4. Restart the application

### Issue 2: No Traces Appearing in Arize AX

**Symptom**: Instrumentation setup succeeds, but no traces appear in dashboard

**Troubleshooting Steps**:
1. **Check API Key**: Ensure API Key is valid and not expired
2. **Check Space ID**: Verify Space ID matches your Arize Space
3. **Check Network**: Ensure outbound HTTPS (port 443) is allowed
4. **Wait**: Traces can take 5-10 seconds to appear (refresh dashboard)
5. **Check Logs**: Look for errors in terminal output during instrumentation

**Test Network Connectivity**:
```bash
curl -I https://otlp.arize.com/v1/traces
```

### Issue 3: "Google GenAI instrumentor not available"

**Symptom**:
```
[Instrumentation] ⚠️  Google GenAI instrumentor not available: No module named 'openinference.instrumentation.google_genai'
```

**Solution**:
```bash
conda activate ticket-summarizer
pip install openinference-instrumentation-google-genai
```

### Issue 4: Gemini API Calls Not Traced

**Possible Causes**:
1. **Old SDK**: Ensure you're using `google-genai` (new SDK), not `google-generativeai` (old SDK)
2. **Instrumentor Not Called**: Verify `GoogleGenAIInstrumentor().instrument()` runs without errors
3. **Import Order**: Instrumentation must be set up BEFORE importing LLM client

**Verify SDK Version**:
```bash
pip show google-genai  # Should show version
pip show google-generativeai  # Should return "WARNING: Package(s) not found"
```

### Issue 5: High Token Costs

**Symptom**: Token usage is higher than expected in Arize AX dashboard

**Analysis**:
1. Navigate to **Cost Tracking** in Arize AX
2. Filter by model and time range
3. Identify high-cost traces

**Optimization Tips**:
- Use `gemini-flash` instead of `gemini-pro` for cost savings
- Reduce prompt size by summarizing ticket comments
- Switch to Azure OpenAI if free Gemini tier is exhausted

---

## Advanced Configuration

### Disabling Tracing

To run the application without tracing (e.g., for local testing):

```bash
# Option 1: Environment variable
export ENABLE_TRACING=false
python main.py --input tickets.csv --analysis-type pod

# Option 2: Remove Arize credentials from .env
# (Comment out or delete ARIZE_SPACE_ID and ARIZE_API_KEY)
```

### EU Region Support

If your Arize account is in the EU region:

**Edit `instrumentation.py`**:
```python
from arize.otel import register, Endpoint

tracer_provider = register(
    space_id=config.ARIZE_SPACE_ID,
    api_key=config.ARIZE_API_KEY,
    project_name=config.ARIZE_PROJECT_NAME,
    endpoint=Endpoint.ARIZE_EUROPE  # Change from ARIZE to ARIZE_EUROPE
)
```

### Custom Project Names

To organize traces by analysis type or environment:

**Edit `.env`**:
```bash
# Separate projects for different analysis types
ARIZE_PROJECT_NAME=ticket-analysis-pod

# Or by environment
ARIZE_PROJECT_NAME=ticket-analysis-staging
```

### Data Retention

**Arize AX Free Tier**:
- **Trace Retention**: 30 days
- **Trace Limit**: 10,000 traces/month
- **Export**: Not available in free tier

**Upgrading**: Contact Arize sales for extended retention and export capabilities.

---

## Next Steps

1. **Run End-to-End Test**: Process a full CSV of tickets and verify all traces appear
2. **Explore Dashboard**: Familiarize yourself with Arize AX UI features
3. **Set Up Alerts**: Configure alerts for high latency or error rates
4. **Implement Tier 2 Spans**: Add manual spans for business logic (future enhancement)
5. **Cost Monitoring**: Track token usage and optimize model selection

---

## References

- **Arize AX Documentation**: [https://docs.arize.com/arize/ax](https://docs.arize.com/arize/ax)
- **OpenInference Spec**: [https://github.com/Arize-ai/openinference](https://github.com/Arize-ai/openinference)
- **Google GenAI SDK**: [https://github.com/googleapis/python-genai](https://github.com/googleapis/python-genai)
- **OpenTelemetry Python**: [https://opentelemetry.io/docs/languages/python/](https://opentelemetry.io/docs/languages/python/)

---

**Last Updated**: January 2025
**Phase**: Phase 4 - Arize AX Cloud Integration
