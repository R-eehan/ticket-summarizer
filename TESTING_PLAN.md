# Phase 4: Arize AX Observability Testing Plan

This document outlines the step-by-step testing plan for validating Phase 4 instrumentation with Arize AX cloud observability.

**Goal**: Verify that all three tiers of instrumentation are working correctly and traces are visible in Arize AX dashboard.

---

## Prerequisites

Before running tests, ensure you have:

1. ✅ **Active conda environment**: `ticket-summarizer`
2. ✅ **Arize AX account**: Free account created at [https://arize.com](https://arize.com)
3. ✅ **Arize credentials configured**: `.env` file with `ARIZE_SPACE_ID` and `ARIZE_API_KEY`
4. ✅ **Test data available**: Small CSV file with 2-5 test tickets

---

## Phase 4: Arize AX Setup & Testing

### Step 1: Activate Conda Environment

**Action**: Activate the `ticket-summarizer` conda environment.

```bash
conda activate ticket-summarizer
```

**Verification**:
```bash
# Verify you're in the correct environment
conda env list | grep '*'
```

**Expected Output**:
```
ticket-summarizer       * /Users/.../anaconda3/envs/ticket-summarizer
```

---

### Step 2: Install Dependencies

**Action**: Install all Phase 4 dependencies including new Google GenAI SDK and Arize packages.

```bash
# Install/upgrade all required packages
pip install --upgrade \
  google-genai \
  arize-otel \
  openinference-instrumentation-openai \
  openinference-instrumentation-google-genai \
  opentelemetry-instrumentation-aiohttp-client
```

**Expected Output**:
- All packages install successfully without version conflicts
- **Key packages to verify**:
  - `google-genai` (new unified SDK - replaces `google-generativeai`)
  - `arize-otel` (Arize convenience wrapper)
  - `openinference-instrumentation-openai`
  - `openinference-instrumentation-google-genai`
  - `opentelemetry-instrumentation-aiohttp-client`

**Verification**:
```bash
# Check installed packages
pip show google-genai
pip show arize-otel
pip list | grep openinference
```

**Expected Output**:
```
Name: google-genai
Version: 0.x.x

Name: arize-otel
Version: 0.x.x

openinference-instrumentation-google-genai  0.1.x
openinference-instrumentation-openai        0.1.x
```

**⚠️ Important**: Verify `google-generativeai` (old SDK) is **NOT** installed:
```bash
pip show google-generativeai
```

**Expected Output**: `WARNING: Package(s) not found: google-generativeai`

---

### Step 3: Configure Arize Credentials

**Action**: Update your `.env` file with Arize AX credentials.

**File**: `.env`

```env
# Arize AX Observability (Phase 4)
ARIZE_SPACE_ID=your-actual-space-id-here
ARIZE_API_KEY=your-actual-api-key-here
ARIZE_PROJECT_NAME=ticket-analysis
```

**How to Get Credentials**:
1. Log in to [Arize AX](https://app.arize.com)
2. Navigate to **Space Settings** (gear icon)
3. Go to **API Keys** tab
4. Copy **Space ID** and **API Key**

**Verification**:
```bash
# Ensure .env has Arize credentials
cat .env | grep ARIZE
```

**Expected Output**:
```
ARIZE_SPACE_ID=abc123xyz...
ARIZE_API_KEY=arize_api_key_...
ARIZE_PROJECT_NAME=ticket-analysis
```

---

### Step 4: Verify Instrumentation Setup

**Action**: Test that instrumentation initializes correctly.

```bash
# Test import and configuration
python -c "
import config
from instrumentation import setup_instrumentation
print(f'Space ID configured: {bool(config.ARIZE_SPACE_ID)}')
print(f'API Key configured: {bool(config.ARIZE_API_KEY)}')
print(f'Project Name: {config.ARIZE_PROJECT_NAME}')
tracer_provider = setup_instrumentation()
print(f'Instrumentation setup: {tracer_provider is not None}')
"
```

**Expected Output**:
```
Space ID configured: True
API Key configured: True
Project Name: ticket-analysis

[Instrumentation] ✅ Arize AX instrumentation enabled
  - Project: ticket-analysis
  - Endpoint: Arize US Cloud
  - Environment: local
  - Tier 1 (LLM): Auto-instrumented (OpenAI, Google GenAI)
  - Tier 2 (Business Logic): Manual spans available (synthesis, categorization, diagnostics)
  - Tier 3 (Zendesk API): Auto-instrumented (aiohttp)
  - View traces: https://app.arize.com/organizations/[YOUR_SPACE_ID]/spaces

Instrumentation setup: True
```

**✅ Success Indicators**:
- All three instrumentors load without errors
- Arize tracer provider registered successfully
- No import errors or warnings

**❌ Failure Scenarios**:
| Symptom | Cause | Solution |
|---------|-------|----------|
| `Arize credentials not configured` | Missing `.env` variables | Add `ARIZE_SPACE_ID` and `ARIZE_API_KEY` to `.env` |
| `Failed to import arize-otel` | Package not installed | `pip install arize-otel` |
| `Google GenAI instrumentor not available` | Package not installed | `pip install openinference-instrumentation-google-genai` |

---

### Step 5: Test Ticket Processing (Gemini Provider)

**Action**: Run the application with Gemini provider and verify traces appear in Arize AX.

#### 5a. Prepare Test Data

Create a small test CSV with 2-3 tickets:

**File**: `test_tickets.csv`
```csv
Serial No, Ticket ID
1, 91682
2, 91123
3, 90567
```

#### 5b. Run POD Analysis with Gemini

```bash
python main.py \
  --input test_tickets.csv \
  --analysis-type pod \
  --model-provider gemini
```

**Expected Output** (Instrumentation startup):
```
[Instrumentation] ✅ Arize AX instrumentation enabled
  - Project: ticket-analysis
  - Endpoint: Arize US Cloud
  ...

[Phase 1] Fetching ticket data...
[Phase 2] Synthesizing tickets...
[Phase 3a] Categorizing tickets into PODs...
...
```

**Verification**:
- Application completes successfully
- No instrumentation errors in output
- Tickets are processed normally

#### 5c. Verify Traces in Arize AX Dashboard

1. **Open Arize Dashboard**: Navigate to [https://app.arize.com](https://app.arize.com)
2. **Select Project**: Click **Projects** → **ticket-analysis**
3. **View Traces**: You should see traces appear within 5-10 seconds

**What to Look For**:

| Metric | Expected Value | Description |
|--------|----------------|-------------|
| **Trace Count** | 6-9 traces | 3 tickets × 2-3 LLM calls each (synthesis + categorization) |
| **Time Range** | Last 5 minutes | Traces should appear with recent timestamps |
| **Status** | All success (green) | No errors or failures |

#### 5d. Inspect a Trace

Click on any trace to view **Trace Details**:

**Expected Span Hierarchy** (for one ticket):
```
🌐 HTTP GET: Zendesk API - Fetch Ticket
  └─ Attributes: http.method=GET, http.status_code=200, duration=~500ms

🌐 HTTP GET: Zendesk API - Fetch Comments
  └─ Attributes: http.method=GET, http.status_code=200, duration=~300ms

🤖 LLM Call: Google GenAI - Synthesis
  └─ Attributes:
     - llm.model_name = gemini-flash-latest
     - llm.token_count.prompt = ~1500-2000
     - llm.token_count.completion = ~400-600
     - llm.token_count.total = ~2000-2500
     - duration = ~2-4 seconds

🤖 LLM Call: Google GenAI - Categorization
  └─ Attributes:
     - llm.model_name = gemini-flash-latest
     - llm.token_count.prompt = ~3000-4000
     - llm.token_count.completion = ~200-300
     - duration = ~1-2 seconds
```

**✅ Success Criteria**:
- All spans present (HTTP calls + LLM calls)
- Token counts are non-zero
- Latency is reasonable (<10s per LLM call)
- Model name is correct (`gemini-flash-latest`)

---

### Step 6: Test Diagnostics Analysis (Gemini Provider)

**Action**: Test diagnostics analysis workflow.

```bash
python main.py \
  --input test_tickets.csv \
  --analysis-type diagnostics \
  --model-provider gemini
```

**Expected Traces**:
- Similar to Step 5, but with different LLM prompt/response content
- **Trace Count**: 3 traces (1 per ticket)
- **Spans per Trace**: HTTP fetch + synthesis + diagnostics analysis

**Verification**:
1. Check Arize dashboard for new traces
2. Filter by **Time Range**: Last 5 minutes
3. Verify diagnostics analysis spans appear

---

### Step 7: Test Both Analyses (Gemini Provider)

**Action**: Test running both POD and Diagnostics analysis in parallel.

```bash
python main.py \
  --input test_tickets.csv \
  --analysis-type both \
  --model-provider gemini
```

**Expected Traces**:
- **Trace Count**: 6-9 traces
- **Spans per Trace**: HTTP fetch + synthesis + categorization + diagnostics (parallel)

**Verification**:
1. Arize dashboard shows increased trace volume
2. Both categorization and diagnostics spans appear in traces

---

### Step 8: Test Azure OpenAI Provider

**Action**: Switch to Azure OpenAI provider and verify instrumentation.

**Prerequisites**:
- Azure OpenAI credentials configured in `.env`:
  ```env
  AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
  AZURE_OPENAI_API_KEY=your_azure_api_key
  AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
  AZURE_OPENAI_API_VERSION=2024-02-01
  ```

**Command**:
```bash
python main.py \
  --input test_tickets.csv \
  --analysis-type pod \
  --model-provider azure
```

**Expected Traces in Arize**:
- Similar structure to Gemini, but with different model name
- **Model Attribute**: `llm.model_name = gpt-4o` (or your deployment name)
- **Token Counts**: Different from Gemini (GPT-4o uses more tokens)

**Verification**:
1. Check Arize dashboard
2. Filter by **Model**: `gpt-4o`
3. Verify Azure OpenAI spans appear

---

### Step 9: Validate HTTP Client Instrumentation (Tier 3)

**Action**: Verify that Zendesk API calls are traced.

**Expected Span Attributes** (for HTTP calls):

| Attribute | Example Value | Description |
|-----------|---------------|-------------|
| `http.method` | `GET` | HTTP request method |
| `http.url` | `https://whatfix.zendesk.com/api/v2/tickets/91682.json` | Full request URL |
| `http.status_code` | `200` | HTTP response status |
| `http.request.header.user_agent` | `aiohttp/3.9.1` | Client user agent |
| `duration` | `~500ms` | Request latency |

**Verification**:
1. In Arize AX, click on any trace
2. Look for HTTP GET spans (should appear before LLM spans)
3. Expand span to view attributes

**✅ Success Criteria**:
- HTTP spans exist for Zendesk ticket and comment fetches
- Status codes are 200 (success)
- URLs contain `zendesk.com/api/v2/`

---

### Step 10: Cost & Performance Analysis

**Action**: Use Arize AX to analyze token usage and latency.

#### 10a. Token Usage Analysis

1. Navigate to Arize **Projects** → **ticket-analysis**
2. View **Metrics** or **Cost Tracking** (if available)
3. Check total tokens consumed

**Expected Results**:
- **Gemini (per ticket)**:
  - Synthesis: ~2000-2500 tokens
  - Categorization: ~3500-4500 tokens
  - **Total per ticket**: ~6000-7000 tokens
- **Azure OpenAI (per ticket)**: Higher (GPT-4o is more verbose)

#### 10b. Latency Analysis

1. Sort traces by **Duration** (descending)
2. Identify slowest operations

**Expected Results**:
- **Gemini LLM calls**: 1-4 seconds per call
- **Azure OpenAI LLM calls**: 2-6 seconds per call (typically slower)
- **Zendesk HTTP calls**: <1 second

---

## Troubleshooting

### Issue 1: No Traces Appearing in Arize

**Symptoms**:
- Application runs successfully
- Instrumentation setup prints success message
- But no traces appear in Arize AX dashboard

**Troubleshooting Steps**:

1. **Wait 10 seconds and refresh**: Traces can take 5-10 seconds to appear

2. **Check credentials**:
   ```bash
   python -c "import config; print(f'Space ID: {config.ARIZE_SPACE_ID[:10]}...'); print(f'API Key: {config.ARIZE_API_KEY[:20]}...')"
   ```

3. **Test network connectivity**:
   ```bash
   curl -I https://otlp.arize.com/v1/traces
   ```
   Expected: `HTTP/2 405` (endpoint exists, POST required)

4. **Check for errors in application output**:
   - Look for `[Instrumentation] ✗ Failed to initialize`
   - Check for import errors or connection failures

5. **Verify project name**:
   - Ensure you're looking at the correct project (`ticket-analysis`)
   - Try filtering by time range: Last 1 hour

### Issue 2: Gemini Traces Missing (but Azure works)

**Symptoms**:
- Azure OpenAI traces appear
- Gemini traces do not appear

**Possible Causes**:
1. **Old SDK still installed**:
   ```bash
   pip uninstall google-generativeai
   pip install google-genai
   ```

2. **Instrumentor not loaded**:
   - Check instrumentation output for `Google GenAI instrumentor not available`
   - Install: `pip install openinference-instrumentation-google-genai`

3. **Import order issue**:
   - Verify `setup_instrumentation()` is called BEFORE LLM client initialization

### Issue 3: HTTP Spans Missing

**Symptoms**:
- LLM traces appear
- HTTP/Zendesk API traces do not appear

**Possible Causes**:
1. **aiohttp instrumentor not installed**:
   ```bash
   pip install opentelemetry-instrumentation-aiohttp-client
   ```

2. **Instrumentor not called**:
   - Verify instrumentation output shows `Aiohttp HTTP client auto-instrumented`

### Issue 4: High Token Usage / Cost

**Symptoms**:
- Gemini free tier exhausted quickly
- High token counts in Arize dashboard

**Solutions**:
1. **Switch to Azure OpenAI** (if enterprise license available)
2. **Reduce prompt size**: Summarize ticket comments before sending to LLM
3. **Use smaller model**: `gemini-flash` instead of `gemini-pro`

---

## Test Scenarios Checklist

Use this checklist to ensure comprehensive testing:

### Basic Functionality
- [ ] Instrumentation setup completes without errors
- [ ] Application runs successfully with tracing enabled
- [ ] Traces appear in Arize AX dashboard within 10 seconds

### Provider Testing (Gemini)
- [ ] POD analysis generates traces
- [ ] Diagnostics analysis generates traces
- [ ] Both analyses generate traces (parallel execution)
- [ ] Token counts are captured correctly
- [ ] Model name is `gemini-flash-latest`

### Provider Testing (Azure OpenAI)
- [ ] POD analysis with Azure generates traces
- [ ] Model name is `gpt-4o` (or deployment name)
- [ ] Token counts differ from Gemini (typically higher)

### Tier Validation
- [ ] **Tier 1 (LLM)**: Gemini spans appear with attributes
- [ ] **Tier 1 (LLM)**: Azure OpenAI spans appear with attributes
- [ ] **Tier 3 (HTTP)**: Zendesk API spans appear with status codes

### Edge Cases
- [ ] Empty credentials (`.env` missing) → Application runs without tracing
- [ ] Invalid credentials → Application runs without tracing (graceful degradation)
- [ ] Network issues → Application continues processing (async export)

### Performance
- [ ] Latency analysis: LLM calls < 10 seconds
- [ ] Token usage analysis: Reasonable consumption
- [ ] No application slowdown due to instrumentation

---

## Next Steps After Testing

Once all tests pass:

1. **Update Documentation**: Mark testing complete in project plan
2. **Production Deployment**: Consider upgrading Arize AX tier for extended retention
3. **Set Up Alerts**: Configure alerts in Arize for high latency or error rates
4. **Implement Tier 2**: Add manual business logic spans (future enhancement)
5. **Cost Monitoring**: Track token usage trends over time

---

**Last Updated**: January 2025 (Phase 4: Arize AX Migration)
