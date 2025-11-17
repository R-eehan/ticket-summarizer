# Phase 4: LLM Observability & Experimentation Instrumentation Plan

> **Document Purpose**: This plan guides the implementation of observability tracing, monitoring, and experimentation capabilities for the ticket-summarizer application. It covers instrumentation architecture, platform selection, implementation steps, and future scalability considerations.

---

## Table of Contents

- [Goals & Business Objectives](#goals--business-objectives)
- [Platform Selection](#platform-selection)
- [Architecture Decision: OpenTelemetry Approach](#architecture-decision-opentelemetry-approach)
- [Instrumentation Strategy](#instrumentation-strategy)
- [Dynamic Execution Model Considerations](#dynamic-execution-model-considerations)
- [Implementation Roadmap](#implementation-roadmap)
- [Platform Setup Guide](#platform-setup-guide)
- [Code Instrumentation Examples](#code-instrumentation-examples)
- [Data Privacy & Security](#data-privacy--security)
- [Platform Comparison Framework](#platform-comparison-framework)
- [Future Platform Additions](#future-platform-additions)
- [Provider Flexibility Guide](#provider-flexibility-guide)
- [Testing & Validation](#testing--validation)
- [Success Criteria](#success-criteria)

---

## Goals & Business Objectives

### Primary Goal

Instrument the entire ticket-summarizer application for **LLM + function call observability & monitoring** to enable:
1. Full trace visualization of application execution
2. Data flow into observability platforms (Arize Phoenix, Langfuse OSS)
3. Experimentation on output datasets to validate:
   - Synthesis summarization quality
   - POD categorization accuracy
   - Diagnostics analysis correctness
4. Error analysis without constant codebase modification

### Business Objectives

This activity serves a **dual purpose**:

#### 1. Set Up Logging & Tracing (Internal Benefit)

**Immediate Value**:
- Visualize complete execution traces (API calls → LLM calls → analysis results)
- Track latency, token costs, and error rates across all phases
- Identify bottlenecks and failure patterns in production

**Long-Term Value**:
- Run experiments directly in observability platforms (no code changes)
- Compare LLM provider performance (Gemini vs Azure OpenAI vs future Anthropic)
- Evaluate prompt variations without modifying codebase
- Build ground truth datasets for quality benchmarking

#### 2. Demonstrate Observability Tooling (Organizational Benefit)

**Goal**: Compare self-hosted vs cloud-based observability platforms to inform organization-wide tooling decisions

**Key Questions to Answer**:
1. **Setup Cost**: How complex is self-hosted deployment vs cloud signup?
2. **Feature Parity**: Do self-hosted versions lose critical features?
3. **Developer Experience**: Which platform is easier to integrate and use?
4. **Cost Model**: What are the tradeoffs between free self-hosted and paid cloud?
5. **Scalability**: Can self-hosted platforms handle production workloads?

**Platforms Under Evaluation**:
- **Phase 4 (Initial)**: Arize Phoenix OSS, Langfuse OSS (self-hosted)
- **Phase 4b (Future)**: Braintrust, Opik, LangSmith (cloud-based comparison)

---

## Platform Selection

### Initial Focus: Self-Hosted OSS Platforms

**Selected Platforms for Phase 4**:
1. **Arize Phoenix OSS** (self-hosted)
2. **Langfuse OSS** (self-hosted)

**Rationale**:
- **Cost**: Free, no vendor lock-in
- **Data Privacy**: All data stays local (critical for sensitive Zendesk tickets)
- **Control**: Full control over deployment, retention, and customization
- **Organizational Demo**: Showcase self-hosted ease-of-setup for security-conscious teams

### Why NOT Cloud-Based (Initially)?

- **Data Residency**: Zendesk tickets may contain customer PII/sensitive data
- **Cost Unknowns**: Want to evaluate self-hosted first before committing to cloud pricing
- **Feature Baseline**: Establish self-hosted baseline before comparing cloud features

**Future Iteration**: Add Braintrust, Opik, LangSmith in Phase 4b for cloud vs self-hosted comparison

---

## Architecture Decision: OpenTelemetry Approach

### Decision Summary

**Instrumentation Standard**: OpenTelemetry (OTEL) with OpenInference conventions

**Export Strategy**: Dual-export to both Phoenix and Langfuse simultaneously (or sequentially via config)

**Rationale**: See [ADR-001: OpenTelemetry vs Abstraction Layer](./architecture_decisions.md#adr-001-opentelemetry-vs-abstraction-layer) for full reasoning

### Why OpenTelemetry (vs Abstraction Layer)?

#### ✅ Pros of OpenTelemetry Approach

1. **Instrument Once, Export Everywhere**
   - Single instrumentation codebase
   - Both Phoenix and Langfuse consume OTLP (OpenTelemetry Protocol) traces
   - Future platforms (Braintrust, Opik, LangSmith) support OTLP with minimal config changes

2. **Auto-Instrumentation**
   - Leverage existing OTEL instrumentors:
     - `openinference-instrumentation-openai` for Azure OpenAI
     - `openinference-instrumentation-google-generativeai` for Gemini
     - Future: `openinference-instrumentation-anthropic` for Claude (zero code changes)
   - Token counts, latency, costs captured automatically
   - No manual span creation for LLM calls

3. **True Vendor Neutrality**
   - Industry standard (CNCF project)
   - Phoenix uses OpenInference natively (OTEL-based)
   - Langfuse consumes OTLP on `/api/public/otel` endpoint
   - Not tied to any single platform

4. **Provider Flexibility**
   - Adding new LLM providers (e.g., Anthropic Claude) is trivial:
     - Install `openinference-instrumentation-anthropic`
     - Traces automatically flow to all platforms
     - **Zero code changes** in synthesizer/analyzer modules

#### ❌ Cons of OpenTelemetry (and Mitigations)

1. **Learning Curve**
   - OTEL concepts (spans, context propagation, exporters) can be complex
   - **Mitigation**: This document provides detailed examples specific to ticket-summarizer

2. **Platform-Specific Features Harder to Access**
   - Langfuse sessions, Phoenix experiments not directly accessible via OTEL
   - **Mitigation**: Use platform SDKs ONLY for experimentation/evaluation (Phase 4b)
   - Tracing = OTEL, Evals = Native SDKs

3. **Debugging OTLP Export Failures**
   - OTLP export failures can be opaque
   - **Mitigation**: Start with Phoenix (simpler single-container), then add Langfuse

#### 🚫 Why NOT Abstraction Layer?

**Abstraction Layer** = Custom wrapper class (e.g., `ObservabilityClient`) with platform-specific implementations

**Cons (with examples from ticket-summarizer codebase)**:

1. **Code Duplication**
   - Need to implement instrumentation twice (once for Phoenix, once for Langfuse)
   - Example: In `synthesizer.py:synthesize_tickets()`, would need:
     - `phoenix_client.trace()` decorator
     - `langfuse.observe()` decorator
   - Maintenance burden: Every new function = 2+ implementations

2. **Inconsistent Traces**
   - Risk of different metadata across platforms
   - Example: If you add `ticket_id` attribute to Phoenix spans but forget Langfuse, comparison becomes invalid
   - Defeats goal of comparing platforms on equal footing

3. **Provider-Specific Pain**
   - Each LLM provider needs 2+ integrations
   - Current: `llm_provider.py` supports Gemini + Azure OpenAI
   - Abstraction layer means:
     - `PhoenixGeminiInstrumentor` + `LangfuseGeminiInstrumentor`
     - `PhoenixAzureInstrumentor` + `LangfuseAzureInstrumentor`
   - Adding Anthropic = 2+ more implementations

4. **Scaling Issues**
   - Future: 5 platforms × 3 providers × 4 phases = **60+ instrumentation points** to maintain
   - Abstraction layer becomes unmaintainable

**Conclusion**: OpenTelemetry provides better scalability, vendor neutrality, and maintainability for this use case.

---

## Instrumentation Strategy

### Three-Tier Instrumentation Architecture

**Goal**: Capture traces at multiple granularities for comprehensive observability

```
┌──────────────────────────────────────────────────────────────────┐
│                     Tier 1: LLM Provider Level                    │
│                    (llm_provider.py - FACTORY)                    │
│                                                                    │
│  Method: Auto-instrumentation via OpenInference                   │
│  Coverage: All LLM calls across all providers (Gemini, Azure)     │
│  Implementation:                                                  │
│    - openinference-instrumentation-openai (Azure OpenAI)         │
│    - openinference-instrumentation-google-generativeai (Gemini)  │
│  Captured Automatically:                                          │
│    - Model name, token counts, latency, costs                    │
│    - Prompts, responses, errors                                  │
│    - Provider-specific metadata                                  │
└──────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│              Tier 2: Business Logic / Analyzer Level              │
│      (synthesizer.py, categorizer.py, diagnostics_analyzer.py)   │
│                                                                    │
│  Method: Manual OTEL spans with custom attributes                │
│  Coverage: Business operations (synthesis, categorization, diag)  │
│  Implementation:                                                  │
│    - opentelemetry.trace.get_tracer(__name__)                    │
│    - @tracer.start_as_current_span() decorator                   │
│  Captured Manually:                                               │
│    - Phase name, ticket_id, batch_size                           │
│    - POD category, diagnostics assessment                        │
│    - Confidence scores, reasoning metadata                       │
└──────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Tier 3: API / Network Level                    │
│                         (fetcher.py)                              │
│                                                                    │
│  Method: Auto-instrumentation via OTEL HTTP instrumentor         │
│  Coverage: All HTTP calls to Zendesk API                         │
│  Implementation:                                                  │
│    - opentelemetry.instrumentation.requests.RequestsInstrumentor │
│       OR                                                          │
│    - opentelemetry.instrumentation.aiohttp.AioHttpClientInstr... │
│  Captured Automatically:                                          │
│    - HTTP method, URL, status code, latency                      │
│    - API errors, rate limit responses (429)                      │
└──────────────────────────────────────────────────────────────────┘
```

### Span Hierarchy Example

#### Scenario 1: `--analysis-type pod` (POD Categorization Only)

```
[Trace: Process Tickets] (analysis_type=pod, model_provider=gemini, tickets=10)
├─ [Phase 1: Fetch Tickets from Zendesk] (ticket_count=10)
│  ├─ [HTTP GET /api/v2/tickets/78788] (status=200, latency=0.3s)
│  ├─ [HTTP GET /api/v2/tickets/78788/comments] (status=200, latency=0.2s)
│  ├─ [HTTP GET /api/v2/tickets/78969] (status=200, latency=0.25s)
│  └─ ... (8 more tickets)
│
├─ [Phase 2: Synthesis] (ticket_count=10, batch_size=10)
│  ├─ [synthesize_ticket] (ticket_id=78788)
│  │  └─ [LLM Call - Gemini Pro] (model=gemini-pro, tokens=1500, latency=2.1s, cost=$0.002)
│  ├─ [synthesize_ticket] (ticket_id=78969)
│  │  └─ [LLM Call - Gemini Pro] (model=gemini-pro, tokens=1450, latency=1.9s, cost=$0.002)
│  └─ ... (8 more)
│
└─ [Phase 3a: POD Categorization] (ticket_count=10)
   ├─ [categorize_ticket] (ticket_id=78788)
   │  └─ [LLM Call - Gemini Pro] (model=gemini-pro, tokens=800, latency=1.5s)
   │     └─ [Result: primary_pod=Guidance, confidence=confident]
   ├─ [categorize_ticket] (ticket_id=78969)
   │  └─ [LLM Call - Gemini Pro] (model=gemini-pro, tokens=750, latency=1.4s)
   │     └─ [Result: primary_pod=WFE, confidence=not_confident]
   └─ ... (8 more)
```

#### Scenario 2: `--analysis-type diagnostics` (Diagnostics Analysis Only)

```
[Trace: Process Tickets] (analysis_type=diagnostics, model_provider=azure, tickets=10)
├─ [Phase 1: Fetch Tickets from Zendesk] (ticket_count=10, custom_fields=true)
│  └─ ... (same as above)
│
├─ [Phase 2: Synthesis] (ticket_count=10)
│  ├─ [synthesize_ticket] (ticket_id=89618)
│  │  └─ [LLM Call - Azure OpenAI GPT-4o] (model=gpt-4o, tokens=1600, latency=0.8s, cost=$0.004)
│  └─ ... (9 more)
│
└─ [Phase 3b: Diagnostics Analysis] (ticket_count=10)
   ├─ [analyze_diagnostics] (ticket_id=89618, custom_field=diagnostic_no)
   │  └─ [LLM Call - Azure OpenAI GPT-4o] (model=gpt-4o, tokens=1200, latency=0.7s)
   │     └─ [Result: was_used=no, could_help=yes, confidence=confident]
   └─ ... (9 more)
```

#### Scenario 3: `--analysis-type both` (Parallel Execution)

```
[Trace: Process Tickets] (analysis_type=both, model_provider=azure, tickets=10)
├─ [Phase 1: Fetch Tickets] (ticket_count=10)
├─ [Phase 2: Synthesis] (ticket_count=10)
├─ [Phase 3a: POD Categorization] (ticket_count=10) ← CONCURRENT
└─ [Phase 3b: Diagnostics Analysis] (ticket_count=10) ← CONCURRENT
```

**CRITICAL NOTE**: Spans for Phase 3a and 3b are created **concurrently** when `--analysis-type both`. OpenTelemetry context propagation must handle this correctly (see [Dynamic Execution Model](#dynamic-execution-model-considerations)).

### Instrumentation Coverage

| Component | Phase | Tier | Instrumentation Method | Metadata Captured |
|-----------|-------|------|------------------------|-------------------|
| **fetcher.py** | Phase 1 | Tier 3 | Auto (OTEL HTTP) | URL, status, latency, errors |
| **synthesizer.py** | Phase 2 | Tier 1 + 2 | Auto (OpenInference) + Manual | Model, tokens, cost + ticket_id, batch_size |
| **categorizer.py** | Phase 3a | Tier 1 + 2 | Auto (OpenInference) + Manual | Model, tokens + POD, confidence, reasoning |
| **diagnostics_analyzer.py** | Phase 3b | Tier 1 + 2 | Auto (OpenInference) + Manual | Model, tokens + assessment, custom_field |
| **llm_provider.py** | All | Tier 1 | Auto (OpenInference) | Provider name, model, latency, errors |
| **main.py** | Root | Tier 2 | Manual (root span) | analysis_type, model_provider, ticket_count |

---

## Dynamic Execution Model Considerations

### CLI Branching and Span Creation

**Critical Constraint**: The application has **conditional execution** based on `--analysis-type` CLI parameter ([main.py:822-859](../main.py#L822-L859))

**Execution Flows**:
1. `--analysis-type pod` → Only runs Phase 3a (POD Categorization)
2. `--analysis-type diagnostics` → Only runs Phase 3b (Diagnostics Analysis)
3. `--analysis-type both` → Runs **BOTH in parallel** (lines 837-847: `asyncio.gather()`)

### Instrumentation Requirements

#### 1. Dynamic Span Creation

**Rule**: Don't create Phase 3a spans if user runs `--analysis-type diagnostics`

**Implementation**:
```python
# In main.py orchestrator
with tracer.start_as_current_span("Process Tickets") as root_span:
    root_span.set_attribute("analysis_type", args.analysis_type)
    root_span.set_attribute("model_provider", args.model_provider)
    root_span.set_attribute("ticket_count", len(ticket_ids))

    # Phase 1 & 2: Always run
    await fetch_phase(...)
    await synthesis_phase(...)

    # Phase 3: Conditional based on analysis_type
    if args.analysis_type == "pod":
        # Only create POD categorization spans
        await categorization_phase(...)
    elif args.analysis_type == "diagnostics":
        # Only create Diagnostics analysis spans
        await diagnostics_phase(...)
    elif args.analysis_type == "both":
        # Create BOTH span trees concurrently
        await asyncio.gather(
            categorization_phase(...),
            diagnostics_phase(...)
        )
```

#### 2. Parallel Context Propagation

**Challenge**: When `--analysis-type both`, Phase 3a and 3b run concurrently via `asyncio.gather()` ([main.py:845-847](../main.py#L845-L847))

**OpenTelemetry Requirement**: Each concurrent task must maintain its own span context

**Solution**:
```python
# OpenTelemetry automatically propagates context to asyncio tasks
# Both tasks will correctly parent their spans under the root "Process Tickets" span

# Example in categorization_phase:
async def categorization_phase(tickets):
    with tracer.start_as_current_span("Phase 3a: POD Categorization") as span:
        span.set_attribute("phase", "categorization")
        # ... categorization logic ...

# Example in diagnostics_phase:
async def diagnostics_phase(tickets):
    with tracer.start_as_current_span("Phase 3b: Diagnostics Analysis") as span:
        span.set_attribute("phase", "diagnostics")
        # ... diagnostics logic ...

# When run concurrently, both spans are siblings under root span
```

#### 3. Conditional Attributes on Root Span

**Best Practice**: Add `analysis_type` attribute to root trace span for filtering in Phoenix/Langfuse

```python
root_span.set_attribute("analysis_type", args.analysis_type)
```

**Benefit**: Can filter traces in UI by analysis type:
- Show only `analysis_type=pod` traces
- Compare latency for `diagnostics` vs `both`

---

## Implementation Roadmap

### Phase 4a: Initial Setup (Week 1)

**Goal**: Get Phoenix running locally with basic tracing

**Tasks**:
1. ✅ **Research & Documentation** (COMPLETED - this document)
2. ⏳ **Phoenix Setup**:
   - Pull Phoenix Docker image
   - Run locally on `localhost:6006`
   - Validate UI loads
3. ⏳ **Basic OTEL Integration**:
   - Install `opentelemetry-api`, `opentelemetry-sdk`
   - Install `opentelemetry-exporter-otlp`
   - Configure OTLP exporter to `http://localhost:4317` (Phoenix gRPC)
4. ⏳ **Root Span Test**:
   - Add root span in `main.py:run()`
   - Run with `--input test_5_tickets.csv --analysis-type pod`
   - Validate trace appears in Phoenix UI

**Success Criteria**:
- Phoenix UI accessible at `localhost:6006`
- Root trace visible with `analysis_type` and `ticket_count` attributes

### Phase 4b: Tier 1 Auto-Instrumentation (Week 1-2)

**Goal**: Automatically capture all LLM calls

**Tasks**:
1. ⏳ **Install OpenInference Instrumentors**:
   - `pip install openinference-instrumentation-openai`
   - `pip install openinference-instrumentation-google-generativeai`
2. ⏳ **Instrument LLM Providers** (in `main.py` or `llm_provider.py`):
   ```python
   from openinference.instrumentation.openai import OpenAIInstrumentor
   from openinference.instrumentation.google_generativeai import GoogleGenerativeAIInstrumentor

   # At application startup (before any LLM calls)
   OpenAIInstrumentor().instrument()  # Covers Azure OpenAI
   GoogleGenerativeAIInstrumentor().instrument()  # Covers Gemini
   ```
3. ⏳ **Test LLM Tracing**:
   - Run synthesis with Gemini: `--model-provider gemini`
   - Run synthesis with Azure: `--model-provider azure`
   - Validate both show up in Phoenix with token counts, latency

**Success Criteria**:
- LLM calls appear as child spans under synthesis/categorization/diagnostics
- Token counts, model name, latency visible in Phoenix
- Both Gemini and Azure calls traced correctly

### Phase 4c: Tier 2 Business Logic Spans (Week 2)

**Goal**: Add manual spans for business operations

**Tasks**:
1. ⏳ **Instrument Main Phases** (in `main.py`):
   - Add span for `fetch_phase()` with `ticket_count` attribute
   - Add span for `synthesis_phase()` with `ticket_count`, `batch_size`
   - Add conditional spans for `categorization_phase()` and `diagnostics_phase()`
2. ⏳ **Instrument Synthesizer** (in `synthesizer.py`):
   - Add span per ticket in `synthesize_ticket()`
   - Add attributes: `ticket_id`, `serial_no`
   - Add result attributes: `synthesis_success` (boolean)
3. ⏳ **Instrument Categorizer** (in `categorizer.py`):
   - Add span per ticket in `categorize_ticket()`
   - Add attributes: `ticket_id`, `primary_pod`, `confidence`
4. ⏳ **Instrument Diagnostics Analyzer** (in `diagnostics_analyzer.py`):
   - Add span per ticket in `analyze_ticket()`
   - Add attributes: `ticket_id`, `was_used`, `could_help`, `confidence`

**Success Criteria**:
- Complete span hierarchy visible in Phoenix (Fetch → Synthesis → Analysis)
- Can filter traces by `ticket_id`, `primary_pod`, `diagnostics_assessment`
- Latency breakdown shows which phase is slowest

### Phase 4d: Tier 3 API Tracing (Week 2-3)

**Goal**: Capture Zendesk API calls

**Tasks**:
1. ⏳ **Install HTTP Instrumentor**:
   - `pip install opentelemetry-instrumentation-aiohttp`
   - (fetcher.py uses `aiohttp` for async HTTP)
2. ⏳ **Instrument at Startup** (in `main.py`):
   ```python
   from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor

   AioHttpClientInstrumentor().instrument()
   ```
3. ⏳ **Test Zendesk API Tracing**:
   - Run fetch phase
   - Validate HTTP calls appear in Phoenix
   - Check for 429 (rate limit) or 404 (not found) errors

**Success Criteria**:
- Zendesk API calls appear as spans under `fetch_phase`
- HTTP status codes, URLs visible
- API failures easily identifiable in traces

### Phase 4e: Langfuse Integration (Week 3)

**Goal**: Add Langfuse as second observability platform

**Tasks**:
1. ⏳ **Langfuse Docker Setup**:
   - Create `docker-compose.yml` with PostgreSQL + ClickHouse + Redis
   - Set `TELEMETRY_ENABLED=false` in environment
   - Start Langfuse locally on `localhost:3000`
2. ⏳ **Add Second OTLP Exporter**:
   - Configure OTLP HTTP exporter to `http://localhost:3000/api/public/otel`
   - Keep Phoenix exporter active (dual-export)
3. ⏳ **Test Dual-Export**:
   - Run full workflow with `--analysis-type both`
   - Validate traces appear in BOTH Phoenix and Langfuse
   - Compare UI experiences

**Success Criteria**:
- Same trace data visible in both Phoenix AND Langfuse
- Can compare dashboards side-by-side
- No performance degradation from dual-export

### Phase 4f: Comparison & Documentation (Week 3-4)

**Goal**: Evaluate platforms and document findings

**Tasks**:
1. ⏳ **Run Comparison Tests**:
   - Process 50 tickets with `--analysis-type both`
   - Compare Phoenix vs Langfuse on:
     - Setup complexity
     - UI/UX for trace exploration
     - Filtering & search capabilities
     - Latency dashboards
     - Cost estimation features
2. ⏳ **Document Findings**:
   - Update [Platform Comparison Framework](#platform-comparison-framework) section
   - Screenshot key UI differences
   - Note feature gaps in self-hosted vs cloud
3. ⏳ **Cleanup & Optimize**:
   - Remove debug logging
   - Optimize span attribute verbosity
   - Add instrumentation toggle (env var to disable)

**Success Criteria**:
- Comprehensive comparison table filled out
- Clear recommendation for organization (self-hosted vs cloud)
- Instrumentation code is production-ready

---

## Platform Setup Guide

### Arize Phoenix OSS - Local Setup

**Infrastructure**: Docker (single container)

#### Quick Start (5 minutes)

```bash
# 1. Pull latest Phoenix image
docker pull arizephoenix/phoenix:latest

# 2. Run Phoenix (SQLite storage)
docker run -d \
  --name phoenix \
  -p 6006:6006 \
  -p 4317:4317 \
  -v phoenix_data:/mnt/data \
  -e PHOENIX_WORKING_DIR=/mnt/data \
  arizephoenix/phoenix:latest

# 3. Verify Phoenix is running
curl http://localhost:6006
# Expected: Phoenix UI HTML

# 4. Access Phoenix UI
# Open browser: http://localhost:6006
```

#### Port Mapping

- `6006`: Phoenix web UI (HTTP) + OTLP HTTP collector
- `4317`: OTLP gRPC collector (for traces)

#### Data Persistence

**Development** (SQLite):
```bash
# Data stored in Docker volume 'phoenix_data'
docker volume inspect phoenix_data
```

**Production** (PostgreSQL):
```yaml
# docker-compose.yml
services:
  phoenix:
    image: arizephoenix/phoenix:latest
    ports:
      - "6006:6006"
      - "4317:4317"
    environment:
      - PHOENIX_SQL_DATABASE_URL=postgresql://user:password@postgres:5432/phoenix
    depends_on:
      - postgres

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=phoenix
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

#### OTLP Exporter Configuration (Python)

```python
# In main.py or dedicated instrumentation module

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# Create resource with service name
resource = Resource(attributes={
    "service.name": "ticket-summarizer",
    "deployment.environment": "local"
})

# Initialize tracer provider
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer_provider = trace.get_tracer_provider()

# Configure OTLP exporter for Phoenix
otlp_exporter = OTLPSpanExporter(
    endpoint="http://localhost:4317",  # Phoenix gRPC endpoint
    insecure=True  # Local dev only, use TLS in production
)

# Add batch span processor
tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

# Get tracer for use in application
tracer = trace.get_tracer("ticket_summarizer")
```

#### Privacy & Telemetry

**Data Storage**: All trace data stored locally in SQLite (dev) or PostgreSQL (prod)

**Telemetry**: No evidence of phone-home behavior in Phoenix OSS (validated via research)

**Network Isolation**: Can run fully offline after Docker image pull

---

### Langfuse OSS - Local Setup

**Infrastructure**: Docker Compose (4-5 containers)

#### Architecture Components

- **Langfuse Web**: Web UI (port 3000)
- **Langfuse Worker**: Background job processing
- **PostgreSQL**: Transactional data storage (port 5432)
- **ClickHouse**: OLAP database for traces/observations (port 8123)
- **Redis/Valkey**: Queue & cache (port 6379)
- **S3/Local Blob**: Event persistence (optional for local dev)

#### Docker Compose Setup (30 minutes)

**Step 1: Create `docker-compose.langfuse.yml`**

```yaml
version: '3.8'

services:
  langfuse-web:
    image: langfuse/langfuse:latest
    container_name: langfuse-web
    ports:
      - "3000:3000"
    environment:
      # Database
      - DATABASE_URL=postgresql://langfuse:langfuse_password@postgres:5432/langfuse
      # ClickHouse
      - CLICKHOUSE_URL=http://clickhouse:8123
      - CLICKHOUSE_USER=default
      - CLICKHOUSE_PASSWORD=clickhouse_password
      # Redis
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      # CRITICAL: Disable telemetry for privacy
      - TELEMETRY_ENABLED=false
      # Authentication (change in production)
      - NEXTAUTH_SECRET=change_this_secret_in_production
      - NEXTAUTH_URL=http://localhost:3000
      - SALT=change_this_salt_in_production
    depends_on:
      - postgres
      - clickhouse
      - redis
    restart: unless-stopped

  langfuse-worker:
    image: langfuse/langfuse:latest
    container_name: langfuse-worker
    command: worker
    environment:
      - DATABASE_URL=postgresql://langfuse:langfuse_password@postgres:5432/langfuse
      - CLICKHOUSE_URL=http://clickhouse:8123
      - CLICKHOUSE_USER=default
      - CLICKHOUSE_PASSWORD=clickhouse_password
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - TELEMETRY_ENABLED=false
    depends_on:
      - postgres
      - clickhouse
      - redis
    restart: unless-stopped

  postgres:
    image: postgres:14
    container_name: langfuse-postgres
    environment:
      - POSTGRES_DB=langfuse
      - POSTGRES_USER=langfuse
      - POSTGRES_PASSWORD=langfuse_password
    volumes:
      - langfuse_postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  clickhouse:
    image: clickhouse/clickhouse-server:latest
    container_name: langfuse-clickhouse
    environment:
      - CLICKHOUSE_DB=langfuse
      - CLICKHOUSE_USER=default
      - CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1
      - CLICKHOUSE_PASSWORD=clickhouse_password
    volumes:
      - langfuse_clickhouse_data:/var/lib/clickhouse
    ports:
      - "8123:8123"
      - "9000:9000"
    restart: unless-stopped

  redis:
    image: redis:7
    container_name: langfuse-redis
    ports:
      - "6379:6379"
    restart: unless-stopped

volumes:
  langfuse_postgres_data:
  langfuse_clickhouse_data:
```

**Step 2: Start Langfuse**

```bash
# Start all containers
docker-compose -f docker-compose.langfuse.yml up -d

# Check logs
docker-compose -f docker-compose.langfuse.yml logs -f langfuse-web

# Wait for "Server started on port 3000" message
```

**Step 3: Create Langfuse Account**

1. Open browser: `http://localhost:3000`
2. Click "Sign Up"
3. Create account (local, no email verification)
4. Create new project: "ticket-summarizer"
5. Copy API keys from project settings:
   - Public Key: `pk-lf-...`
   - Secret Key: `sk-lf-...`

**Step 4: Configure Environment Variables**

```bash
# Add to .env file
LANGFUSE_BASE_URL=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key-here
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key-here
```

#### OTLP Exporter Configuration (Python)

```python
# In main.py or dedicated instrumentation module

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPHTTPExporter

# Langfuse OTLP HTTP endpoint (available in v3.22.0+)
langfuse_exporter = OTLPHTTPExporter(
    endpoint="http://localhost:3000/api/public/otel",  # Langfuse OTLP HTTP
    headers={
        "Authorization": f"Bearer {LANGFUSE_SECRET_KEY}"  # From .env
    }
)

# Add to tracer provider
tracer_provider.add_span_processor(BatchSpanProcessor(langfuse_exporter))
```

#### Privacy & Telemetry

**CRITICAL**: By default, Langfuse sends **aggregated usage analytics** to PostHog (Langfuse's analytics provider)

**What's Sent** (if `TELEMETRY_ENABLED=true`):
- Feature usage stats (e.g., "X traces logged today")
- **NOT sent**: Actual traces, prompts, responses, customer data

**Privacy Guarantee**: Setting `TELEMETRY_ENABLED=false` in `docker-compose.yml` completely disables telemetry

**Validation**:
```bash
# Check environment variable is set
docker exec langfuse-web env | grep TELEMETRY_ENABLED
# Expected: TELEMETRY_ENABLED=false

# Confirm no outbound PostHog requests
docker exec langfuse-web cat /app/.next/server/app/api/telemetry.js
# Should show early return if TELEMETRY_ENABLED=false
```

**Air-Gapped Deployment**: Can run Langfuse without internet after initial Docker image pull

**Data Storage**:
- Traces: ClickHouse (`langfuse_clickhouse_data` volume)
- Metadata: PostgreSQL (`langfuse_postgres_data` volume)
- Events: Optional S3/local blob storage (not required for basic setup)

---

## Code Instrumentation Examples

### Example 1: Root Span in main.py

```python
# main.py - orchestrator

import asyncio
from opentelemetry import trace

# Get tracer (initialized at startup)
tracer = trace.get_tracer("ticket_summarizer")

class TicketSummarizer:
    async def run(self, csv_path: str):
        """
        Main workflow execution with root tracing span.
        """
        # Create root span for entire process
        with tracer.start_as_current_span("Process Tickets") as root_span:
            # Add attributes for filtering/grouping in UI
            root_span.set_attribute("analysis_type", self.analysis_type)
            root_span.set_attribute("model_provider", self.model_provider)
            root_span.set_attribute("csv_path", csv_path)

            # Load CSV and add ticket count
            ticket_ids = self.load_csv(csv_path)
            root_span.set_attribute("ticket_count", len(ticket_ids))

            # Phase 1: Fetch (auto-instrumented HTTP calls)
            fetched_tickets = await self.fetch_phase(ticket_ids)
            root_span.add_event("Phase 1 Complete", {
                "tickets_fetched": len(fetched_tickets)
            })

            # Phase 2: Synthesis (auto-instrumented LLM calls)
            synthesized_tickets = await self.synthesis_phase(fetched_tickets)
            root_span.add_event("Phase 2 Complete", {
                "tickets_synthesized": len(synthesized_tickets)
            })

            # Phase 3: Conditional based on analysis_type
            if self.analysis_type == "pod":
                processed_tickets = await self.categorization_phase(synthesized_tickets)
            elif self.analysis_type == "diagnostics":
                processed_tickets = await self.diagnostics_phase(synthesized_tickets)
            elif self.analysis_type == "both":
                # Parallel execution - OTEL handles context propagation
                cat_tickets, diag_tickets = await asyncio.gather(
                    self.categorization_phase(synthesized_tickets),
                    self.diagnostics_phase(synthesized_tickets)
                )
                # Merge results
                processed_tickets = self._merge_results(cat_tickets, diag_tickets)

            root_span.add_event("Phase 3 Complete")
            root_span.set_attribute("processing_status", "success")

            return processed_tickets
```

### Example 2: Phase-Level Span in synthesizer.py

```python
# synthesizer.py - business logic

from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class GeminiSynthesizer:
    async def synthesize_multiple(self, tickets, progress_callback):
        """
        Synthesize multiple tickets with tracing.
        """
        # Create span for entire synthesis phase
        with tracer.start_as_current_span("Phase 2: Synthesis") as phase_span:
            phase_span.set_attribute("phase", "synthesis")
            phase_span.set_attribute("ticket_count", len(tickets))
            phase_span.set_attribute("batch_size", len(tickets))

            results = []

            # Process each ticket (each will create child span)
            for ticket in tickets:
                try:
                    result = await self.synthesize_ticket(ticket)
                    results.append(result)
                    progress_callback(ticket['ticket_id'], result, success=True)
                except Exception as e:
                    # Log error to span
                    phase_span.record_exception(e)
                    phase_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))

                    result = {**ticket, "processing_status": "failed", "error": str(e)}
                    results.append(result)
                    progress_callback(ticket['ticket_id'], result, success=False)

            phase_span.set_attribute("success_count", sum(1 for r in results if r.get('processing_status') == 'success'))
            phase_span.set_attribute("failed_count", sum(1 for r in results if r.get('processing_status') == 'failed'))

            return results

    async def synthesize_ticket(self, ticket_data):
        """
        Synthesize a single ticket with per-ticket span.
        """
        ticket_id = ticket_data.get('ticket_id', 'unknown')

        # Create span for this ticket's synthesis
        with tracer.start_as_current_span("synthesize_ticket") as span:
            span.set_attribute("ticket_id", ticket_id)
            span.set_attribute("serial_no", ticket_data.get('serial_no'))
            span.set_attribute("comment_count", len(ticket_data.get('comments', [])))

            # Format prompt
            prompt = self.format_prompt(ticket_data)
            span.set_attribute("prompt_length", len(prompt))

            # LLM call (auto-instrumented by OpenInference)
            # This will create a child span automatically
            response = await self.llm_client.generate_content(prompt)

            # Parse response
            synthesis = self.parse_response(response.text)

            # Add result attributes
            span.set_attribute("synthesis_success", True)
            span.set_attribute("issue_reported", synthesis.get('issue_reported', '')[:100])  # Truncate

            ticket_data['synthesis'] = synthesis
            ticket_data['processing_status'] = 'success'

            return ticket_data
```

### Example 3: Auto-Instrumentation Setup

```python
# instrumentation.py - centralized instrumentation setup

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GRPCExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPExporter
from opentelemetry.sdk.resources import Resource

# OpenInference instrumentors
from openinference.instrumentation.openai import OpenAIInstrumentor
from openinference.instrumentation.google_generativeai import GoogleGenerativeAIInstrumentor

# HTTP instrumentor for Zendesk API
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor

import os


def setup_instrumentation():
    """
    Initialize OpenTelemetry instrumentation for ticket-summarizer.

    Call this ONCE at application startup (in main.py before any LLM/API calls).
    """
    # 1. Create resource with service metadata
    resource = Resource(attributes={
        "service.name": "ticket-summarizer",
        "service.version": "1.0.0",  # Update per release
        "deployment.environment": os.getenv("ENVIRONMENT", "local")
    })

    # 2. Initialize tracer provider
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer_provider = trace.get_tracer_provider()

    # 3. Configure Phoenix exporter (gRPC)
    phoenix_exporter = GRPCExporter(
        endpoint=os.getenv("PHOENIX_OTLP_ENDPOINT", "http://localhost:4317"),
        insecure=True  # Local dev only, use TLS in production
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(phoenix_exporter))

    # 4. Configure Langfuse exporter (HTTP) - optional, comment out if not using
    if os.getenv("LANGFUSE_SECRET_KEY"):
        langfuse_exporter = HTTPExporter(
            endpoint=os.getenv("LANGFUSE_OTLP_ENDPOINT", "http://localhost:3000/api/public/otel"),
            headers={
                "Authorization": f"Bearer {os.getenv('LANGFUSE_SECRET_KEY')}"
            }
        )
        tracer_provider.add_span_processor(BatchSpanProcessor(langfuse_exporter))

    # 5. Auto-instrument LLM providers (Tier 1)
    OpenAIInstrumentor().instrument()  # Covers Azure OpenAI
    GoogleGenerativeAIInstrumentor().instrument()  # Covers Gemini

    # 6. Auto-instrument HTTP client (Tier 3)
    AioHttpClientInstrumentor().instrument()  # Covers Zendesk API calls (fetcher.py)

    print("[Instrumentation] OpenTelemetry initialized successfully")
    print(f"  - Phoenix endpoint: {os.getenv('PHOENIX_OTLP_ENDPOINT', 'http://localhost:4317')}")
    if os.getenv("LANGFUSE_SECRET_KEY"):
        print(f"  - Langfuse endpoint: {os.getenv('LANGFUSE_OTLP_ENDPOINT', 'http://localhost:3000/api/public/otel')}")


# Call this in main.py before instantiating TicketSummarizer
if __name__ == "__main__":
    # Import at top of main.py
    from instrumentation import setup_instrumentation

    # Initialize instrumentation FIRST
    setup_instrumentation()

    # Then run application
    summarizer = TicketSummarizer(...)
    asyncio.run(summarizer.run(csv_path))
```

### Example 4: Conditional Span Creation (Diagnostics Analyzer)

```python
# diagnostics_analyzer.py - conditional analysis

from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class DiagnosticsAnalyzer:
    async def analyze_multiple(self, tickets, progress_callback):
        """
        Analyze multiple tickets for diagnostics applicability.

        NOTE: This function is ONLY called if --analysis-type is "diagnostics" or "both".
        Spans are created conditionally based on user input.
        """
        # This span will NOT exist if user runs --analysis-type pod
        with tracer.start_as_current_span("Phase 3b: Diagnostics Analysis") as phase_span:
            phase_span.set_attribute("phase", "diagnostics")
            phase_span.set_attribute("ticket_count", len(tickets))

            # Filter tickets with synthesis data
            tickets_to_analyze = [
                t for t in tickets
                if t.get('processing_status') == 'success' and 'synthesis' in t
            ]

            phase_span.set_attribute("valid_ticket_count", len(tickets_to_analyze))

            results = []
            for ticket in tickets_to_analyze:
                result = await self.analyze_ticket(ticket)
                results.append(result)
                progress_callback(ticket['ticket_id'], result)

            # Add aggregated metrics to span
            was_used_counts = {"yes": 0, "no": 0, "unknown": 0}
            could_help_counts = {"yes": 0, "no": 0, "maybe": 0}

            for r in results:
                if r.get('diagnostics_analysis_status') == 'success':
                    diag = r.get('diagnostics_analysis', {})
                    was_used = diag.get('was_diagnostics_used', {}).get('llm_assessment', 'unknown').lower()
                    could_help = diag.get('could_diagnostics_help', {}).get('assessment', 'unknown').lower()

                    if was_used in was_used_counts:
                        was_used_counts[was_used] += 1
                    if could_help in could_help_counts:
                        could_help_counts[could_help] += 1

            # Store aggregates as span attributes
            for key, value in was_used_counts.items():
                phase_span.set_attribute(f"was_used.{key}", value)
            for key, value in could_help_counts.items():
                phase_span.set_attribute(f"could_help.{key}", value)

            return results
```

---

## Data Privacy & Security

### Privacy Guarantees for Self-Hosted Deployments

#### Arize Phoenix OSS

**✅ Fully Private**:
- All trace data stored **locally** in SQLite (dev) or PostgreSQL (prod)
- No telemetry or phone-home behavior detected (validated via research)
- Can run **fully offline** after Docker image pull
- No account creation or cloud connection required

**Network Isolation**:
```bash
# Run Phoenix in isolated Docker network (optional paranoia mode)
docker network create phoenix-isolated

docker run -d \
  --name phoenix \
  --network phoenix-isolated \
  -p 6006:6006 \
  -p 4317:4317 \
  arizephoenix/phoenix:latest

# Phoenix cannot make outbound requests
```

#### Langfuse OSS

**⚠️ Default Telemetry (Can Be Disabled)**:
- By default, Langfuse sends **aggregated usage analytics** to PostHog
  - **Sent**: Feature usage stats (e.g., "X traces logged today")
  - **NOT sent**: Actual traces, prompts, responses, customer data
- **CRITICAL**: Set `TELEMETRY_ENABLED=false` to fully disable (see [Langfuse Setup](#langfuse-oss---local-setup))

**✅ After Disabling Telemetry**:
- All trace data stored **locally** in PostgreSQL + ClickHouse
- Event persistence in local blob storage (or S3 if configured)
- Can run **air-gapped** after Docker image pull
- No external dependencies except initial Docker registry

**Validation**:
```bash
# Confirm telemetry is disabled
docker exec langfuse-web env | grep TELEMETRY_ENABLED
# Expected: TELEMETRY_ENABLED=false

# Check for outbound network requests (should be empty)
docker exec langfuse-web netstat -an | grep ESTABLISHED
# Expected: Only internal container IPs (postgres, clickhouse, redis)
```

### Sensitive Data Considerations

**Data in Traces**:
- Zendesk tickets may contain **customer PII** (names, emails, phone numbers)
- Synthesis summaries may reveal **internal product issues**
- LLM prompts may include **proprietary troubleshooting workflows**

**Mitigation Strategies**:

1. **Field Filtering** (optional, if needed):
   ```python
   # Add to instrumentation.py if PII filtering required
   from opentelemetry.sdk.trace import SpanProcessor

   class PIIFilterProcessor(SpanProcessor):
       def on_start(self, span, parent_context):
           pass

       def on_end(self, span):
           # Remove sensitive attributes before export
           if span.attributes:
               # Example: Remove customer email from attributes
               if 'customer_email' in span.attributes:
                   span.attributes['customer_email'] = '[REDACTED]'

   # Add to tracer provider
   tracer_provider.add_span_processor(PIIFilterProcessor())
   ```

2. **Local-Only Deployment**:
   - Keep Phoenix/Langfuse on local machine (not shared servers)
   - Use VPN if accessing from remote locations
   - Encrypt Docker volumes at rest (optional)

3. **Access Control**:
   - Phoenix: No authentication by default (local dev only)
   - Langfuse: Requires account creation (local, no email verification)
   - Production: Add reverse proxy (Nginx) with basic auth if needed

---

## Platform Comparison Framework

### Evaluation Criteria

Use this framework to compare Phoenix vs Langfuse (and future platforms) after Phase 4 implementation.

| Criterion | Weight | Phoenix OSS | Langfuse OSS | Notes |
|-----------|--------|-------------|--------------|-------|
| **Setup Complexity** | High | ⭐⭐⭐⭐⭐ (5/5) | ⭐⭐⭐ (3/5) | Phoenix: 5 min (1 container). Langfuse: 30 min (5 containers) |
| **Infrastructure Overhead** | High | ⭐⭐⭐⭐⭐ (5/5) | ⭐⭐ (2/5) | Phoenix: ~500MB disk. Langfuse: ~5GB disk + 4 services |
| **Trace Visualization** | High | [TBD after testing] | [TBD after testing] | Compare UI for exploring nested spans, filtering |
| **Filtering & Search** | Medium | [TBD] | [TBD] | Can you filter by ticket_id, POD, confidence? |
| **Latency Dashboards** | Medium | [TBD] | [TBD] | Built-in charts for LLM latency, token cost? |
| **Cost Estimation** | Medium | [TBD] | [TBD] | Automatic token cost calculation per trace? |
| **Experimentation** | Low | [TBD] | [TBD] | Can you A/B test prompts without code changes? |
| **Online Evaluations** | Low | [TBD] | [TBD] | Support for LLM-as-a-judge evals in UI? |
| **Documentation Quality** | Medium | [TBD] | [TBD] | Clarity of setup docs, troubleshooting guides |
| **Community Support** | Low | [TBD] | [TBD] | GitHub issues response time, Discord activity |

**Fill out TBD fields during Phase 4f testing**

### Setup Complexity Comparison (Pre-Filled)

| Aspect | Phoenix | Langfuse |
|--------|---------|----------|
| **Docker Containers** | 1 (all-in-one) | 4-5 (web, worker, PostgreSQL, ClickHouse, Redis) |
| **Setup Time** | 5 minutes (pull + run) | 30-60 minutes (docker-compose + config) |
| **Disk Space** | ~500MB (SQLite) | ~5GB (PostgreSQL + ClickHouse) |
| **Ports** | 2 (6006 UI, 4317 OTLP) | 5+ (3000 UI, 5432 Postgres, 8123 ClickHouse, 6379 Redis, OTLP) |
| **Persistence** | Volume mount (simple) | Multiple volumes (complex) |
| **Maintenance** | Low (single container) | Medium (multi-service orchestration) |

**Verdict**: Phoenix is **significantly easier** to set up for self-hosting (important for organizational demo).

### Feature Parity: Self-Hosted vs Cloud (Research Findings)

**Phoenix OSS**:
- **Self-Hosted**: Full feature set (no cloud version yet)
- **Limitations**: No built-in auth, no multi-user collaboration (single-user tool)

**Langfuse OSS vs Cloud**:
- **Self-Hosted Loses**:
  - Advanced analytics (cohort analysis, funnel tracking)
  - Multi-workspace collaboration
  - SSO/SAML authentication
  - Managed infrastructure (uptime SLA)
- **Self-Hosted Keeps**:
  - Core tracing & observability
  - Prompt management
  - Manual evaluations
  - API access

**Key Finding**: For **initial observability** (Phase 4 goal), self-hosted versions are **sufficient**. Advanced features (SSO, collaboration) matter more for organization-wide rollout.

---

## Future Platform Additions

### Phase 4b: Cloud Platform Evaluation (Future)

**Goal**: Compare self-hosted (Phoenix, Langfuse) vs cloud-based (Braintrust, Opik, LangSmith)

**Platforms to Add**:
1. **Braintrust** (cloud, paid)
2. **Opik** (cloud/self-hosted hybrid)
3. **LangSmith** (cloud, LangChain ecosystem)

**Implementation Approach**:
- Same OpenTelemetry instrumentation (no code changes)
- Add cloud OTLP exporters in `instrumentation.py`:
  ```python
  # Example: Add Braintrust exporter
  braintrust_exporter = HTTPExporter(
      endpoint="https://api.braintrust.ai/v1/traces",
      headers={"Authorization": f"Bearer {BRAINTRUST_API_KEY}"}
  )
  tracer_provider.add_span_processor(BatchSpanProcessor(braintrust_exporter))
  ```

**Comparison Criteria** (same as [Platform Comparison Framework](#platform-comparison-framework)):
- Setup complexity (cloud signup vs self-hosted deployment)
- Feature richness (evaluations, experiments, collaboration)
- Cost model (free tier limits, pricing per 1M tokens)
- Data residency constraints (where do traces live?)

**Expected Outcome**: Clear recommendation for organization:
- Use self-hosted for sensitive data / cost-sensitive teams
- Use cloud for feature-rich experimentation / fast iteration

### Adding New Platforms: Step-by-Step

**Step 1: Research OTLP Endpoint**

Check platform documentation:
- Does it support OTLP? (Most modern platforms do)
- What's the endpoint URL? (e.g., `https://api.platform.com/v1/otel`)
- What authentication is required? (API key, bearer token?)

**Step 2: Add Exporter in `instrumentation.py`**

```python
# Example: Adding a new platform "ExampleAI"
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPExporter

exampleai_exporter = HTTPExporter(
    endpoint=os.getenv("EXAMPLEAI_OTLP_ENDPOINT", "https://api.exampleai.com/v1/otel"),
    headers={
        "Authorization": f"Bearer {os.getenv('EXAMPLEAI_API_KEY')}",
        "Content-Type": "application/json"
    }
)

tracer_provider.add_span_processor(BatchSpanProcessor(exampleai_exporter))
```

**Step 3: Add Environment Variables**

```env
# .env
EXAMPLEAI_API_KEY=your_api_key_here
EXAMPLEAI_OTLP_ENDPOINT=https://api.exampleai.com/v1/otel
```

**Step 4: Test**

```bash
# Run full workflow
python main.py --input test_5_tickets.csv --analysis-type both --model-provider azure

# Check ExampleAI dashboard for traces
# Validate all spans, attributes, and events appear correctly
```

**Step 5: Document Findings**

Update [Platform Comparison Framework](#platform-comparison-framework) with:
- Setup complexity score
- Feature observations
- Cost estimates
- UI/UX notes

---

## Provider Flexibility Guide

### Current LLM Providers

**Supported** (Phase 3c):
- Google Gemini (via `google-generativeai` SDK)
- Azure OpenAI GPT-4o (via `openai` SDK)

**Auto-Instrumented** (Phase 4):
- ✅ Gemini: `openinference-instrumentation-google-generativeai`
- ✅ Azure OpenAI: `openinference-instrumentation-openai`

### Adding a New Provider: Anthropic Claude Example

**Scenario**: Organization wants to evaluate Anthropic Claude 3.5 Sonnet as third LLM provider

**Step 1: Add Provider to Factory** ([llm_provider.py](../llm_provider.py))

```python
# llm_provider.py

from anthropic import Anthropic

class AnthropicClient:
    """Wrapper for Anthropic Claude API"""

    def __init__(self):
        self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.model = "claude-3-5-sonnet-20250101"

    def generate_content(self, prompt: str):
        """
        Generate content using Claude.

        Returns unified LLMResponse object.
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )

        # Wrap in unified response object
        return LLMResponse(text=response.content[0].text)


class LLMProviderFactory:
    """Factory for creating LLM provider clients"""

    @staticmethod
    def get_provider(provider: str = "gemini"):
        if provider == "gemini":
            return GeminiClient()
        elif provider == "azure":
            return AzureOpenAIClient()
        elif provider == "anthropic":  # NEW
            return AnthropicClient()
        else:
            raise ValueError(f"Unknown provider: {provider}")
```

**Step 2: Add Configuration** ([config.py](../config.py))

```python
# config.py

# Anthropic Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
```

**Step 3: Update CLI** ([main.py](../main.py))

```python
# main.py

parser.add_argument(
    "--model-provider",
    choices=["gemini", "azure", "anthropic"],  # Add "anthropic"
    default="gemini",
    help="LLM provider to use: 'gemini', 'azure', or 'anthropic'"
)
```

**Step 4: Install OpenInference Instrumentor**

```bash
# Install Anthropic SDK
pip install anthropic

# Install OpenInference instrumentor for Anthropic
pip install openinference-instrumentation-anthropic
```

**Step 5: Add Auto-Instrumentation** ([instrumentation.py](instrumentation_plan.md#example-3-auto-instrumentation-setup))

```python
# instrumentation.py

from openinference.instrumentation.anthropic import AnthropicInstrumentor

def setup_instrumentation():
    # ... existing setup ...

    # Auto-instrument Anthropic (NEW)
    AnthropicInstrumentor().instrument()

    print("[Instrumentation] Anthropic auto-instrumented")
```

**Step 6: Test**

```bash
# Add API key to .env
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" >> .env

# Run with Anthropic provider
python main.py --input test_5_tickets.csv --analysis-type diagnostics --model-provider anthropic

# Validate:
# 1. Synthesis completes successfully
# 2. Phoenix shows "claude-3-5-sonnet" in LLM call spans
# 3. Token counts, latency captured correctly
```

**CRITICAL**: Zero code changes in `synthesizer.py`, `categorizer.py`, or `diagnostics_analyzer.py`!

All those modules use `LLMProviderFactory.get_provider()`, which now supports Anthropic. OpenInference auto-instrumentation handles tracing.

### Provider Comparison Matrix

After adding Anthropic, you can compare all 3 providers using Phoenix/Langfuse dashboards:

| Metric | Gemini Pro | Azure OpenAI GPT-4o | Anthropic Claude 3.5 Sonnet |
|--------|------------|---------------------|------------------------------|
| **Avg Latency (synthesis)** | [TBD] | [TBD] | [TBD] |
| **Avg Tokens (synthesis)** | [TBD] | [TBD] | [TBD] |
| **Cost per 1K Tickets** | [TBD] | [TBD] | [TBD] |
| **Error Rate** | [TBD] | [TBD] | [TBD] |
| **POD Accuracy** | [TBD] | [TBD] | [TBD] |
| **Diagnostics F1 Score** | [TBD] | [TBD] | [TBD] |

**How to Gather Data**:
1. Run same 100-ticket dataset with all 3 providers:
   ```bash
   python main.py --input tickets_100.csv --analysis-type both --model-provider gemini
   python main.py --input tickets_100.csv --analysis-type both --model-provider azure
   python main.py --input tickets_100.csv --analysis-type both --model-provider anthropic
   ```

2. Export traces from Phoenix/Langfuse as CSV

3. Analyze:
   - Latency: Avg span duration for `synthesize_ticket`
   - Tokens: Avg `llm.token_count.total` attribute
   - Cost: Calculate based on provider pricing (tokens × price)
   - Error Rate: Count `span.status.code = ERROR`
   - Accuracy: Manual review or LLM-as-a-judge eval (Phase 4b)

---

## Testing & Validation

### Test Plan

#### Test 1: Basic Tracing (Phoenix Only)

**Goal**: Validate root span and phase spans appear in Phoenix

**Steps**:
1. Start Phoenix: `docker run -d -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest`
2. Run small dataset: `python main.py --input test_5_tickets.csv --analysis-type pod --model-provider gemini`
3. Open Phoenix UI: `http://localhost:6006`
4. Verify:
   - ✅ Root trace "Process Tickets" visible
   - ✅ Attributes: `analysis_type=pod`, `ticket_count=5`
   - ✅ Child spans: Phase 1, Phase 2, Phase 3a
   - ✅ LLM calls under synthesis/categorization

**Expected Trace Structure**:
```
Process Tickets (8.5s)
├─ Phase 1: Fetch Tickets (2.1s)
│  └─ HTTP GET /api/v2/tickets/... (×5)
├─ Phase 2: Synthesis (4.2s)
│  ├─ synthesize_ticket (ticket_id=78788)
│  │  └─ LLM Call - Gemini (1.9s, 1500 tokens)
│  └─ ... (4 more)
└─ Phase 3a: POD Categorization (2.2s)
   ├─ categorize_ticket (ticket_id=78788)
   │  └─ LLM Call - Gemini (1.5s, 800 tokens)
   └─ ... (4 more)
```

#### Test 2: Dual-Export (Phoenix + Langfuse)

**Goal**: Validate same traces appear in both platforms

**Steps**:
1. Start Langfuse: `docker-compose -f docker-compose.langfuse.yml up -d`
2. Configure dual-export in `instrumentation.py` (both Phoenix and Langfuse exporters)
3. Run: `python main.py --input test_10_tickets.csv --analysis-type diagnostics --model-provider azure`
4. Check Phoenix UI: `http://localhost:6006`
5. Check Langfuse UI: `http://localhost:3000`
6. Verify:
   - ✅ Same trace ID in both platforms
   - ✅ Same span hierarchy
   - ✅ Same attributes (ticket_id, model, tokens)

#### Test 3: Parallel Execution Tracing

**Goal**: Validate concurrent Phase 3a + 3b spans when `--analysis-type both`

**Steps**:
1. Run: `python main.py --input test_10_tickets.csv --analysis-type both --model-provider azure`
2. Open Phoenix trace view
3. Verify:
   - ✅ Phase 3a and 3b are **siblings** (not parent-child)
   - ✅ Both start at approximately same time (parallel execution)
   - ✅ Both complete before root span closes
   - ✅ No missing spans or context loss

**Expected Timeline** (Phoenix Gantt chart):
```
[Phase 1] ████████░░░░░░░░░░░░░░░░░░░░░░░░░░ (0-2s)
[Phase 2] ░░░░░░░░██████████░░░░░░░░░░░░░░░░ (2-6s)
[Phase 3a] ░░░░░░░░░░░░░░░░██████░░░░░░░░░░░ (6-9s) ← Parallel
[Phase 3b] ░░░░░░░░░░░░░░░░██████░░░░░░░░░░░ (6-9s) ← Parallel
```

#### Test 4: Error Tracing

**Goal**: Validate errors appear in traces

**Steps**:
1. Create CSV with invalid ticket ID (e.g., `99999999`)
2. Run: `python main.py --input test_invalid.csv --analysis-type pod`
3. Open Phoenix trace view
4. Verify:
   - ✅ Span for failed ticket has `status.code = ERROR`
   - ✅ Exception message visible in span events
   - ✅ Stack trace captured (if applicable)
   - ✅ Failed ticket doesn't break entire trace

#### Test 5: Provider Flexibility

**Goal**: Validate instrumentation works for both Gemini and Azure

**Steps**:
1. Run Gemini: `python main.py --input test_5_tickets.csv --analysis-type diagnostics --model-provider gemini`
2. Run Azure: `python main.py --input test_5_tickets.csv --analysis-type diagnostics --model-provider azure`
3. Compare traces in Phoenix:
   - ✅ Gemini shows `model=gemini-pro`
   - ✅ Azure shows `model=gpt-4o`
   - ✅ Both capture token counts correctly
   - ✅ Latency difference visible (Gemini slower due to free tier)

---

## Success Criteria

### Phase 4 Overall Success Criteria

#### Functional Requirements

1. ✅ **Instrumentation Coverage**
   - All phases (1, 2, 3a, 3b) instrumented with spans
   - LLM calls automatically traced (Gemini and Azure)
   - Zendesk API calls automatically traced
   - Root span contains analysis_type, model_provider, ticket_count

2. ✅ **Platform Integration**
   - Phoenix OSS running locally, traces visible in UI
   - Langfuse OSS running locally, traces visible in UI
   - Dual-export to both platforms working simultaneously
   - No data loss or missing spans

3. ✅ **Dynamic Execution Support**
   - Conditional span creation based on `--analysis-type`
   - Parallel execution (`--analysis-type both`) traced correctly
   - No context loss or orphaned spans

4. ✅ **Provider Flexibility**
   - Both Gemini and Azure OpenAI traced identically
   - Can add new provider (e.g., Anthropic) with zero code changes in analyzers
   - OpenInference auto-instrumentation works for all providers

#### Performance Requirements

1. ✅ **Minimal Overhead**
   - Tracing adds <5% latency overhead to total runtime
   - No rate limit errors from dual-export
   - Batch span processing doesn't block main thread

2. ✅ **Scalability**
   - Can process 100-ticket dataset without memory issues
   - Phoenix/Langfuse handle concurrent trace ingestion (asyncio.gather)

#### Quality Requirements

1. ✅ **Code Quality**
   - Instrumentation code is modular (separate `instrumentation.py`)
   - Can enable/disable tracing via environment variable
   - No breaking changes to existing functionality
   - Comprehensive inline comments

2. ✅ **Documentation**
   - This plan document complete and accurate
   - Platform setup guides tested and validated
   - Architecture decisions documented in ADRs
   - Code examples are copy-paste ready

3. ✅ **Organizational Demo Value**
   - Clear comparison: Phoenix (5 min setup) vs Langfuse (30 min setup)
   - Feature parity analysis documented
   - Self-hosted vs cloud tradeoffs articulated
   - Recommendation for organization provided

### Phase 4b Success Criteria (Future)

**Goal**: Demonstrate cloud platforms vs self-hosted

**Requirements**:
1. Add Braintrust, Opik, or LangSmith (at least 1 cloud platform)
2. Compare on same [Platform Comparison Framework](#platform-comparison-framework)
3. Document:
   - Setup ease (cloud signup vs self-hosted deployment)
   - Feature richness (evals, experiments, collaboration)
   - Cost model (free tier vs paid)
   - Data residency constraints
4. Clear recommendation: When to use self-hosted vs cloud

---

## Notes & Best Practices

### Instrumentation Best Practices

1. **Start Small**: Begin with root span + LLM auto-instrumentation before adding manual spans
2. **Attribute Naming**: Use semantic conventions:
   - `ticket_id` not `ticket_ID` (lowercase)
   - `model` not `llm_model` (concise)
   - `phase` values: `"synthesis"`, `"categorization"`, `"diagnostics"` (lowercase)
3. **Avoid Over-Instrumentation**: Don't create spans for trivial operations (< 10ms)
4. **Truncate Large Attributes**: Prompts/responses can be >10K chars, truncate to first 500 chars
5. **Use Events for Milestones**: Use `span.add_event("Phase 1 Complete")` for key checkpoints

### Debugging Instrumentation

**Problem**: Traces not appearing in Phoenix

**Checklist**:
1. Is Phoenix running? `curl http://localhost:6006`
2. Is OTLP exporter configured correctly? Check `endpoint="http://localhost:4317"`
3. Are spans being created? Add print statements: `print(f"Span created: {span.name}")`
4. Is BatchSpanProcessor flushing? Call `tracer_provider.force_flush()` before app exit
5. Check Phoenix logs: `docker logs phoenix`

**Problem**: Spans appear in Phoenix but not Langfuse

**Checklist**:
1. Is Langfuse running? `curl http://localhost:3000`
2. Is OTLP HTTP endpoint correct? `http://localhost:3000/api/public/otel`
3. Is `LANGFUSE_SECRET_KEY` set in Authorization header?
4. Check Langfuse logs: `docker logs langfuse-web`
5. Verify Langfuse version >= 3.22.0 (OTLP support)

### Performance Optimization

**Span Sampling** (if overhead is an issue):
```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# Sample 50% of traces (for high-volume production)
sampler = TraceIdRatioBased(0.5)
tracer_provider = TracerProvider(sampler=sampler, resource=resource)
```

**Async Batch Export**:
```python
# Already using BatchSpanProcessor (asynchronous)
# Spans are batched and exported in background thread
# No blocking of main application thread
```

---

## Appendix

### Research Summary

**Phoenix OSS**:
- Setup: Single Docker container (`arizephoenix/phoenix:latest`)
- Ports: 6006 (UI + OTLP HTTP), 4317 (OTLP gRPC)
- Storage: SQLite (dev) or PostgreSQL (prod)
- Telemetry: None detected (fully private)
- OTLP: Native support (gRPC and HTTP)

**Langfuse OSS**:
- Setup: Docker Compose (web, worker, PostgreSQL, ClickHouse, Redis)
- Ports: 3000 (UI), 5432 (Postgres), 8123 (ClickHouse), 6379 (Redis)
- Storage: PostgreSQL (metadata) + ClickHouse (traces) + S3/blob (events)
- Telemetry: Default ON (aggregated stats to PostHog), can disable via `TELEMETRY_ENABLED=false`
- OTLP: HTTP endpoint at `/api/public/otel` (v3.22.0+)

**OpenTelemetry Instrumentation**:
- OpenAI: `openinference-instrumentation-openai` (covers Azure OpenAI)
- Gemini: `openinference-instrumentation-google-generativeai`
- Anthropic: `openinference-instrumentation-anthropic` (for future use)
- HTTP: `opentelemetry-instrumentation-aiohttp-client` (for Zendesk API)

**Key Insight**: Both Phoenix and Langfuse consume OTLP, so **single instrumentation codebase** works for both (and all future platforms).

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-09
**Author**: Phase 4 Planning Team
**Next Review**: After Phase 4a completion (Week 1)
