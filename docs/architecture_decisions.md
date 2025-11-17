# Architecture Decision Records (ADRs)

> **Purpose**: This document captures all major architectural decisions made during the development of the ticket-summarizer application, with detailed reasoning, alternatives considered, and consequences. Each decision is documented for future reference to help engineers and product managers understand the "why" behind technical choices.

---

## Table of Contents

- [ADR-001: OpenTelemetry vs Abstraction Layer for Observability](#adr-001-opentelemetry-vs-abstraction-layer-for-observability)
- [ADR-002: Phoenix + Langfuse OSS Selection for Initial Evaluation](#adr-002-phoenix--langfuse-oss-selection-for-initial-evaluation)
- [ADR-003: Three-Tier Instrumentation Strategy](#adr-003-three-tier-instrumentation-strategy)
- [ADR-004: Local-First Deployment Approach](#adr-004-local-first-deployment-approach)
- [ADR-005: Dynamic Execution Model with CLI Branching](#adr-005-dynamic-execution-model-with-cli-branching)
- [ADR-006: Factory Pattern for LLM Provider Abstraction (Phase 3c)](#adr-006-factory-pattern-for-llm-provider-abstraction-phase-3c)
- [ADR-007: No Automatic Fallback Between LLM Providers](#adr-007-no-automatic-fallback-between-llm-providers)
- [ADR-008: Binary Confidence Scoring for POD Categorization](#adr-008-binary-confidence-scoring-for-pod-categorization)
- [ADR-009: Ternary Assessment for Diagnostics Analysis](#adr-009-ternary-assessment-for-diagnostics-analysis)
- [ADR-010: Separate Output Files for Different Analysis Types](#adr-010-separate-output-files-for-different-analysis-types)
- [ADR-011: JIRA URL as Source of Truth for Escalation](#adr-011-jira-url-as-source-of-truth-for-escalation)
- [ADR-012: Escalation Signal in Diagnostics Analysis Only](#adr-012-escalation-signal-in-diagnostics-analysis-only)
- [ADR-013: Separate CSV Files Per Analysis Type](#adr-013-separate-csv-files-per-analysis-type)

---

## ADR-001: OpenTelemetry vs Abstraction Layer for Observability

**Status**: Accepted (Phase 4)

**Decision Date**: 2025-11-09

**Context**:

For Phase 4 (Observability & Instrumentation), we need to instrument the application to send traces to multiple observability platforms (Arize Phoenix, Langfuse OSS, and potentially Braintrust, Opik, LangSmith in the future). Two approaches were considered:

1. **OpenTelemetry (OTEL) Approach**: Use industry-standard OpenTelemetry for instrumentation, export traces via OTLP (OpenTelemetry Protocol) to all platforms
2. **Abstraction Layer Approach**: Create custom wrapper class (e.g., `ObservabilityClient`) with platform-specific implementations (Phoenix client, Langfuse client, etc.)

**Decision**:

We chose **OpenTelemetry (OTEL) with OpenInference conventions** as the instrumentation standard.

**Rationale**:

### Pros of OpenTelemetry Approach

#### 1. Instrument Once, Export Everywhere
- Single instrumentation codebase
- Both Phoenix and Langfuse consume OTLP (OpenTelemetry Protocol) natively
- Future platforms (Braintrust, Opik, LangSmith) all support OTLP with minimal configuration changes
- **Example**: Adding Braintrust requires only adding an OTLP exporter, zero code changes in application logic

#### 2. Auto-Instrumentation Leverage
- Existing OTEL instrumentors available for all LLM providers:
  - `openinference-instrumentation-openai` for Azure OpenAI (automatically captures token counts, latency, costs)
  - `openinference-instrumentation-google-generativeai` for Gemini
  - `openinference-instrumentation-anthropic` for future Claude integration
- HTTP instrumentor for Zendesk API calls: `opentelemetry-instrumentation-aiohttp-client`
- **No manual span creation required for LLM calls** - all metadata captured automatically

#### 3. True Vendor Neutrality
- Industry standard (CNCF graduated project)
- Not tied to any single observability platform
- Phoenix uses OpenInference (OTEL-based) natively
- Langfuse consumes OTLP on `/api/public/otel` endpoint
- Protects against vendor lock-in

#### 4. Provider Flexibility (Critical for Multi-Model Support)
- Adding new LLM providers (e.g., Anthropic Claude) is trivial:
  - Install `openinference-instrumentation-anthropic`
  - Traces automatically flow to **all** platforms (Phoenix, Langfuse, Braintrust, etc.)
  - **Zero code changes** in `synthesizer.py`, `categorizer.py`, or `diagnostics_analyzer.py`
- Current architecture ([llm_provider.py](../llm_provider.py)) supports Gemini and Azure OpenAI
- All consumers use `LLMProviderFactory.get_provider()` which is instrumentation-agnostic

**Example from Codebase**:
```python
# In synthesizer.py - NO instrumentation code needed
class GeminiSynthesizer:
    def __init__(self, model_provider: str = "gemini"):
        # Get provider from factory (Gemini, Azure, or future Anthropic)
        self.llm_client = LLMProviderFactory.get_provider(provider=model_provider)

    async def synthesize_ticket(self, ticket_data):
        # This LLM call is auto-instrumented by OpenInference
        response = await self.llm_client.generate_content(prompt)
        # Token counts, latency, costs automatically captured in trace
```

If we add Anthropic:
1. Install `openinference-instrumentation-anthropic`
2. Add `AnthropicClient` to factory
3. **DONE** - all traces automatically flow to Phoenix, Langfuse, etc.

### Cons of OpenTelemetry (and Mitigations)

#### 1. Learning Curve
- **Con**: OTEL concepts (spans, context propagation, exporters) can be complex for engineers unfamiliar with observability
- **Mitigation**: [instrumentation_plan.md](./instrumentation_plan.md) provides detailed, copy-paste-ready examples specific to ticket-summarizer
- **Mitigation**: Centralize OTEL setup in single `instrumentation.py` module - rest of codebase is instrumentation-agnostic

#### 2. Platform-Specific Features Harder to Access
- **Con**: Langfuse sessions, Phoenix experiments not directly accessible via OTEL
- **Mitigation**: Use platform SDKs ONLY for experimentation/evaluation (Phase 4b), not for tracing
  - **Tracing** = OpenTelemetry (vendor-neutral)
  - **Evaluations** = Native platform SDKs (when needed)

#### 3. Debugging OTLP Export Failures
- **Con**: OTLP export failures can be opaque (e.g., "connection refused" without clear platform identification)
- **Mitigation**: Start with Phoenix (simpler single-container setup) to validate OTEL works, then add Langfuse
- **Mitigation**: Add explicit logging in `instrumentation.py` for each exporter initialization

### Why NOT Abstraction Layer?

#### Cons of Abstraction Layer (with Codebase Examples)

##### 1. Code Duplication
**Problem**: Need to implement instrumentation twice (once for Phoenix, once for Langfuse)

**Example from Codebase**:
```python
# synthesizer.py - with abstraction layer (BAD)
class GeminiSynthesizer:
    def __init__(self, observability_platform: str = "phoenix"):
        if observability_platform == "phoenix":
            self.obs_client = PhoenixClient()
        elif observability_platform == "langfuse":
            self.obs_client = LangfuseClient()

    async def synthesize_tickets(self, tickets):
        # Manually create trace for Phoenix
        with self.obs_client.trace(name="synthesis"):
            for ticket in tickets:
                # Manually create span for each ticket
                with self.obs_client.span(name="synthesize_ticket", attributes={"ticket_id": ticket.id}):
                    response = await self.llm_client.generate_content(...)
```

**Maintenance Burden**:
- Every new function requiring tracing = 2+ implementations (Phoenix + Langfuse + future platforms)
- Example: Adding `batch_size` attribute:
  - Update `PhoenixClient.span()` to accept `batch_size`
  - Update `LangfuseClient.span()` to accept `batch_size`
  - Update all call sites (synthesizer, categorizer, diagnostics)
  - Risk of inconsistency if forgotten in one platform

##### 2. Inconsistent Traces Across Platforms
**Problem**: Risk of different metadata across platforms, defeating comparison goal

**Example**:
```python
# In synthesizer.py - easy to forget attribute in one platform
with phoenix_client.span("synthesize") as span:
    span.set_attribute("ticket_id", ticket_id)
    span.set_attribute("batch_size", batch_size)  # Added here

with langfuse_client.span("synthesize") as span:
    span.set_attribute("ticket_id", ticket_id)
    # Forgot to add batch_size! Now Phoenix and Langfuse traces differ
```

**Consequence**: Can't reliably compare platforms if they have different data

##### 3. Provider-Specific Pain (Scales Poorly)
**Current State**: `llm_provider.py` supports 2 providers (Gemini, Azure OpenAI)

**Abstraction Layer Scaling**:
- 2 providers × 2 platforms = **4 implementations**
  - `PhoenixGeminiInstrumentor`
  - `PhoenixAzureInstrumentor`
  - `LangfuseGeminiInstrumentor`
  - `LangfuseAzureInstrumentor`

**Future State** (with Anthropic + Braintrust + Opik):
- 3 providers × 5 platforms = **15 implementations**
- Adding a new provider (e.g., OpenAI direct API) = 5 more implementations

**OpenTelemetry Scaling**:
- Install `openinference-instrumentation-{provider}` → **1 implementation**
- Works with all platforms automatically

##### 4. Maintenance Nightmare Example
**Scenario**: Add `primary_pod` attribute to categorization spans

**Abstraction Layer**:
```python
# Update PhoenixClient
class PhoenixClient:
    def categorize_span(self, ticket_id, primary_pod):  # Add primary_pod param
        span.set_attribute("ticket_id", ticket_id)
        span.set_attribute("primary_pod", primary_pod)  # NEW

# Update LangfuseClient
class LangfuseClient:
    def categorize_span(self, ticket_id, primary_pod):  # Add primary_pod param
        span.set_attribute("ticket_id", ticket_id)
        span.set_attribute("primary_pod", primary_pod)  # NEW

# Update BraintrustClient (future)
# Update OpikClient (future)
# Update LangSmithClient (future)

# Update all call sites
# categorizer.py
with obs_client.categorize_span(ticket_id, primary_pod):  # Update call
    ...
```

**OpenTelemetry**:
```python
# Update call site ONLY (single location)
# categorizer.py
with tracer.start_as_current_span("categorize_ticket") as span:
    span.set_attribute("ticket_id", ticket_id)
    span.set_attribute("primary_pod", primary_pod)  # NEW - automatically exported to all platforms
```

**Verdict**: Abstraction layer becomes unmaintainable at scale (5 platforms × 3 providers × 4 analysis phases = **60+ instrumentation points**)

**Consequences**:

### Positive Consequences
1. ✅ **Scalability**: Can add unlimited platforms and providers with minimal code changes
2. ✅ **Consistency**: All platforms receive identical trace data, enabling fair comparison
3. ✅ **Community Support**: OpenTelemetry is CNCF standard with massive ecosystem
4. ✅ **Future-Proof**: Industry moving toward OTEL as de facto standard

### Negative Consequences
1. ⚠️ **Learning Investment**: Engineers need to learn OTEL concepts (one-time cost)
2. ⚠️ **Platform-Specific Features**: Requires platform SDKs for advanced features (mitigated by separating tracing from evals)

**Alternatives Considered**:

1. **Abstraction Layer** (rejected - see cons above)
2. **Multi-Instrumentation** (instrument with both Phoenix SDK AND Langfuse SDK simultaneously)
   - **Rejected because**: Performance overhead (every span created twice), code complexity, doesn't scale beyond 2 platforms
3. **Platform-Specific Only** (use Phoenix SDK only, no Langfuse)
   - **Rejected because**: Goal is to compare multiple platforms, vendor lock-in

**References**:
- OpenTelemetry Tracing Specification: https://opentelemetry.io/docs/specs/otel/trace/
- OpenInference (OTEL for LLMs): https://github.com/Arize-ai/openinference
- Phoenix OTLP Support: https://arize.com/docs/phoenix (uses OTLP natively)
- Langfuse OTLP Support: https://langfuse.com/docs/integrations/opentelemetry (v3.22.0+)

---

## ADR-002: Phoenix + Langfuse OSS Selection for Initial Evaluation

**Status**: Accepted (Phase 4)

**Decision Date**: 2025-11-09

**Context**:

For Phase 4 initial implementation, we need to select 2 observability platforms to:
1. Set up logging & tracing for application monitoring
2. Demonstrate self-hosted vs cloud-based observability tools to the organization
3. Compare setup cost, feature parity, and developer experience

Options considered: Arize Phoenix OSS, Langfuse OSS, Braintrust, Opik, LangSmith, OpenLIT, others

**Decision**:

Start with **Arize Phoenix OSS** and **Langfuse OSS** (both self-hosted).

**Rationale**:

### Why Self-Hosted First?

#### 1. Data Privacy (Critical for Sensitive Zendesk Tickets)
- Zendesk tickets may contain **customer PII** (names, emails, support issues)
- Synthesis summaries may reveal **internal product issues**
- Self-hosted = all data stays local (no transmission to external cloud)
- **Organizational Requirement**: Security-conscious teams prefer self-hosted for initial evaluation

#### 2. Cost Predictability
- Self-hosted = free (only infrastructure costs)
- Cloud platforms have opaque pricing (per trace, per user, per 1M tokens)
- Want to establish baseline value before committing to cloud spend

#### 3. Control & Customization
- Full control over deployment, retention policies, backup strategies
- Can modify source code if needed (both are open-source)
- No vendor quota limits or rate restrictions

### Why Phoenix OSS?

#### 1. Simplicity (Organizational Demo Value)
**Setup Complexity**: Single Docker container
```bash
docker run -d -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest
# Ready in 5 minutes
```

**Infrastructure**: Minimal
- 1 container (all-in-one)
- ~500MB disk space (SQLite storage)
- 2 ports (6006 UI, 4317 OTLP gRPC)

**Best for**: Demonstrating "self-hosted can be easy" to organization

#### 2. OpenTelemetry Native
- Built on OpenInference (OTEL-based)
- No SDK required for basic tracing (just OTLP exporter)
- All OTEL instrumentors work out-of-the-box

#### 3. Developer-Focused
- Strong evaluation capabilities (though self-hosted lacks some advanced features)
- Lightweight, fast UI for trace exploration
- No account creation required (local-only)

### Why Langfuse OSS?

#### 1. Feature-Rich (Comparison Baseline)
**Capabilities** (even in self-hosted mode):
- Prompt management
- Manual evaluations
- Session tracking
- Rich analytics (POD distribution, diagnostics breakdown)

**Best for**: Demonstrating feature parity gap (self-hosted vs cloud) to organization

#### 2. Production-Grade Architecture
**Infrastructure**: Multi-service
- PostgreSQL (transactional data)
- ClickHouse (OLAP for traces)
- Redis (queue/cache)
- Web + Worker containers

**Best for**: Evaluating operational overhead of complex self-hosted deployments

#### 3. Cloud Version Available (Future Comparison)
- Can compare Langfuse OSS (self-hosted) vs Langfuse Cloud in Phase 4b
- Same platform, different deployment models
- Direct apples-to-apples feature comparison

### Why NOT Cloud Platforms (Initially)?

#### Braintrust
- ❌ Cloud-only (no self-hosted option) → can't demonstrate self-hosting
- ❌ Pricing unclear for bulk analysis (1M+ tokens)
- ✅ Excellent experimentation features (but overkill for Phase 4a)

#### Opik
- ❌ Less mature (newer project, smaller community)
- ✅ Hybrid self-hosted/cloud model (interesting for Phase 4b)

#### LangSmith
- ❌ Cloud-only (no self-hosted) → can't demonstrate self-hosting
- ❌ LangChain ecosystem bias (we use direct LLM SDKs)
- ✅ Excellent debugging features (but tied to LangChain)

### Platform Comparison Matrix (Rationale)

| Criterion | Phoenix OSS | Langfuse OSS | Braintrust | LangSmith | Decision |
|-----------|-------------|--------------|------------|-----------|----------|
| **Self-Hosted** | ✅ Yes (easy) | ✅ Yes (complex) | ❌ No | ❌ No | Phoenix + Langfuse |
| **Data Privacy** | ✅ Fully local | ✅ Local (with telemetry disabled) | ❌ Cloud-only | ❌ Cloud-only | Phoenix + Langfuse |
| **Setup Complexity** | ⭐⭐⭐⭐⭐ 5 min | ⭐⭐⭐ 30 min | ⭐⭐⭐⭐ 10 min (cloud signup) | ⭐⭐⭐⭐ 10 min | Good contrast for demo |
| **OTLP Support** | ✅ Native | ✅ Yes (v3.22+) | ✅ Yes | ✅ Yes | All equal |
| **Cost** | Free | Free | Paid (unclear) | Paid | Phoenix + Langfuse |
| **Org Demo Value** | ✅ "Easy self-host" | ✅ "Complex self-host" | ✅ "Easy cloud" | ❌ LangChain bias | 2 extremes of self-hosting |

**Key Insight**: Phoenix (simple) + Langfuse (complex) show **two ends of self-hosted spectrum**, giving organization full picture

**Consequences**:

### Positive Consequences
1. ✅ **Data Privacy Guaranteed**: All traces stay local (critical for org approval)
2. ✅ **Cost Control**: $0 platform cost (only local Docker infrastructure)
3. ✅ **Clear Organizational Demo**: Can show "self-hosted is easy (Phoenix)" vs "self-hosted is complex (Langfuse)" vs future "cloud is feature-rich (Braintrust)"
4. ✅ **OpenTelemetry Validation**: Both support OTLP → validates ADR-001 decision

### Negative Consequences
1. ⚠️ **Missing Cloud Features**: Self-hosted Langfuse lacks SSO, advanced analytics, multi-workspace collaboration
   - **Mitigation**: Document feature gaps, plan Phase 4b for cloud comparison
2. ⚠️ **Operational Overhead**: Langfuse requires managing 5 Docker containers (PostgreSQL, ClickHouse, Redis, Web, Worker)
   - **Mitigation**: Use docker-compose for orchestration, document operational complexity in plan
3. ⚠️ **Not Industry-Leading**: Neither Phoenix nor Langfuse are market leaders (LangSmith, Braintrust have more traction)
   - **Mitigation**: This is Phase 4a (initial), add market leaders in Phase 4b

**Alternatives Considered**:

1. **Phoenix OSS + Braintrust Cloud** (rejected)
   - **Pro**: Compare self-hosted vs cloud directly
   - **Con**: Data privacy concern (Zendesk tickets to Braintrust cloud)
   - **Con**: Can't demonstrate self-hosted feature parity

2. **Langfuse OSS Only** (rejected)
   - **Pro**: Simpler demo (one platform)
   - **Con**: Doesn't show simplicity spectrum (Phoenix is much easier)
   - **Con**: Goal is to compare platforms, need at least 2

3. **OpenLIT + Langfuse OSS** (rejected)
   - **Pro**: Both self-hosted OSS
   - **Con**: OpenLIT less mature, smaller community
   - **Con**: Phoenix has better OTEL documentation

**Future Evolution** (Phase 4b):
- Add Braintrust (cloud, feature-rich experimentation)
- Add LangSmith (cloud, LangChain ecosystem) OR Opik (hybrid)
- Compare self-hosted (Phoenix/Langfuse) vs cloud (Braintrust/LangSmith) on:
  - Setup cost
  - Feature richness
  - Data residency constraints
  - Pricing models

**References**:
- Phoenix OSS: https://github.com/Arize-ai/phoenix
- Langfuse OSS: https://github.com/langfuse/langfuse
- Langfuse Self-Hosting Docs: https://langfuse.com/docs/deployment/self-host

---

## ADR-003: Three-Tier Instrumentation Strategy

**Status**: Accepted (Phase 4)

**Decision Date**: 2025-11-09

**Context**:

Need to determine **where** in the application to add instrumentation (spans) for observability. Possible approaches:
1. Instrument only LLM calls (Tier 1 only)
2. Instrument only business logic (Tier 2 only)
3. Instrument everything (Tier 1 + Tier 2 + Tier 3)

**Decision**:

Implement a **Three-Tier Instrumentation Strategy**:
- **Tier 1**: LLM Provider Level (auto-instrumentation)
- **Tier 2**: Business Logic / Analyzer Level (manual spans)
- **Tier 3**: API / Network Level (auto-instrumentation)

**Rationale**:

### Why Three Tiers?

#### Goal: Comprehensive Observability Across All Phases

**User Requirement** (from conversation):
> "I think ALL phases should be instrumented. Considering we're looking at the FULL application functioning, I believe it is important to capture ALL the events, including simple API calls - what if the API call fails? This failure directly impacts my LLM calls & JSON structure processing."

**Example Failure Cascade**:
```
[Phase 1: Zendesk API] HTTP 429 Rate Limit Error
    ↓
[Phase 2: Synthesis] Receives 0 tickets → Empty array passed to LLM
    ↓
[Phase 3a: Categorization] LLM confusion → Hallucinated POD names
    ↓
[Output] Garbage results
```

**Without Tier 3 (API tracing)**: Would only see "categorization failed" with no context
**With Tier 3**: See root cause: Zendesk API rate limit → 0 tickets fetched → cascading failure

### Tier 1: LLM Provider Level (Auto-Instrumentation)

**Instrumentation Location**: [llm_provider.py](../llm_provider.py) - factory level

**Method**: OpenInference auto-instrumentors

**Coverage**: All LLM calls across all providers (Gemini, Azure OpenAI, future Anthropic)

**Implementation**:
```python
# In instrumentation.py (startup)
from openinference.instrumentation.openai import OpenAIInstrumentor
from openinference.instrumentation.google_generativeai import GoogleGenerativeAIInstrumentor

OpenAIInstrumentor().instrument()  # Covers Azure OpenAI
GoogleGenerativeAIInstrumentor().instrument()  # Covers Gemini
```

**Captured Automatically**:
- Model name (`gemini-pro`, `gpt-4o`)
- Token counts (prompt, completion, total)
- Latency (time to first token, total duration)
- Costs (if provider SDK exposes it)
- Prompts (full text, can be truncated)
- Responses (full text, can be truncated)
- Errors (API failures, quota exceeded, etc.)

**Why Auto-Instrumentation?**:
- **Zero code changes** in synthesizer/categorizer/diagnostics
- **Provider-agnostic**: Adding Anthropic = install instrumentor, done
- **Consistent metadata**: All providers captured identically

**Example from Codebase**:
```python
# synthesizer.py - NO instrumentation code
async def synthesize_ticket(self, ticket_data):
    # This LLM call is auto-instrumented
    response = await self.llm_client.generate_content(prompt)
    # Token counts, latency automatically captured in Phoenix/Langfuse
```

### Tier 2: Business Logic / Analyzer Level (Manual Spans)

**Instrumentation Location**:
- [synthesizer.py](../synthesizer.py) - synthesis operations
- [categorizer.py](../categorizer.py) - POD categorization
- [diagnostics_analyzer.py](../diagnostics_analyzer.py) - diagnostics analysis
- [main.py](../main.py) - orchestrator (root span, phase spans)

**Method**: Manual OpenTelemetry spans with custom attributes

**Coverage**: Business operations (synthesis, categorization, diagnostics) + domain metadata

**Implementation**:
```python
# In synthesizer.py
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def synthesize_tickets(self, tickets):
    with tracer.start_as_current_span("Phase 2: Synthesis") as span:
        span.set_attribute("phase", "synthesis")
        span.set_attribute("ticket_count", len(tickets))
        span.set_attribute("batch_size", len(tickets))

        for ticket in tickets:
            with tracer.start_as_current_span("synthesize_ticket") as ticket_span:
                ticket_span.set_attribute("ticket_id", ticket['ticket_id'])
                ticket_span.set_attribute("serial_no", ticket['serial_no'])
                # ... synthesis logic (LLM call auto-instrumented by Tier 1) ...
```

**Captured Manually**:
- Phase name (`synthesis`, `categorization`, `diagnostics`)
- Ticket metadata (`ticket_id`, `serial_no`, `batch_size`)
- POD category (`primary_pod`, `confidence`)
- Diagnostics assessment (`was_used`, `could_help`, `confidence`)
- Ticket priority, custom fields, etc.

**Why Manual Spans?**:
- **Domain-specific metadata**: OTEL auto-instrumentors don't know about tickets, PODs, diagnostics
- **Error analysis**: Can filter traces by `primary_pod=WFE` or `diagnostics_could_help=yes`
- **Business metrics**: Track POD distribution, diagnostics hit rate, etc.

**Example Use Case**:
```
Query in Phoenix UI:
  "Show me all traces where primary_pod='WFE' AND confidence='not_confident'"

Result:
  15 traces → all WFE categorizations that need human review
```

### Tier 3: API / Network Level (Auto-Instrumentation)

**Instrumentation Location**: [fetcher.py](../fetcher.py) - Zendesk API calls

**Method**: OpenTelemetry HTTP client instrumentor

**Coverage**: All HTTP calls to Zendesk API

**Implementation**:
```python
# In instrumentation.py (startup)
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor

AioHttpClientInstrumentor().instrument()  # Covers all aiohttp HTTP calls
```

**Captured Automatically**:
- HTTP method (`GET`, `POST`)
- URL (`https://whatfix.zendesk.com/api/v2/tickets/78788`)
- Status code (`200`, `404`, `429`)
- Latency (request duration)
- Errors (network failures, timeouts)

**Why Tier 3?**:
- **Failure Diagnosis**: Zendesk API failures cascade to LLM errors
  - Example: 429 Rate Limit → 0 tickets → empty synthesis → bad categorization
- **Performance Bottlenecks**: Is Phase 1 (fetch) slower than Phase 2 (synthesis)?
- **Retry Analysis**: How often do retries happen? Are they successful?

**Example Failure Trace**:
```
[Trace: Process Tickets] (FAILED)
├─ [Phase 1: Fetch Tickets] (ticket_count=10)
│  ├─ [HTTP GET /api/v2/tickets/78788] (200 OK, 0.3s)
│  ├─ [HTTP GET /api/v2/tickets/78969] (429 Rate Limited, 0.1s) ← FAILURE
│  ├─ [HTTP GET /api/v2/tickets/78969] (RETRY: 429 Rate Limited, 0.1s) ← RETRY FAILED
│  └─ ... (8 more tickets)
├─ [Phase 2: Synthesis] (ticket_count=9) ← Only 9 tickets (1 failed fetch)
└─ [Phase 3a: Categorization] (ticket_count=9)
```

**Root cause visible**: Zendesk rate limit → missing ticket → downstream issues

### Span Hierarchy (All Tiers Together)

**Example Trace** (`--analysis-type pod`, 5 tickets):
```
[Tier 2] [ROOT] Process Tickets (analysis_type=pod, model_provider=gemini, tickets=5) - 8.5s
    │
    ├─ [Tier 2] Phase 1: Fetch Tickets (ticket_count=5) - 2.1s
    │  ├─ [Tier 3] HTTP GET /api/v2/tickets/78788 (200, 0.3s)
    │  ├─ [Tier 3] HTTP GET /api/v2/tickets/78788/comments (200, 0.2s)
    │  ├─ [Tier 3] HTTP GET /api/v2/tickets/78969 (200, 0.25s)
    │  └─ ... (more HTTP calls)
    │
    ├─ [Tier 2] Phase 2: Synthesis (ticket_count=5, batch_size=5) - 4.2s
    │  ├─ [Tier 2] synthesize_ticket (ticket_id=78788, serial_no=1)
    │  │  └─ [Tier 1] LLM Call - Gemini Pro (model=gemini-pro, tokens=1500, cost=$0.002) - 1.9s
    │  ├─ [Tier 2] synthesize_ticket (ticket_id=78969, serial_no=2)
    │  │  └─ [Tier 1] LLM Call - Gemini Pro (model=gemini-pro, tokens=1450, cost=$0.002) - 1.8s
    │  └─ ... (3 more tickets)
    │
    └─ [Tier 2] Phase 3a: POD Categorization (ticket_count=5) - 2.2s
       ├─ [Tier 2] categorize_ticket (ticket_id=78788, primary_pod=Guidance, confidence=confident)
       │  └─ [Tier 1] LLM Call - Gemini Pro (model=gemini-pro, tokens=800, cost=$0.001) - 1.5s
       ├─ [Tier 2] categorize_ticket (ticket_id=78969, primary_pod=WFE, confidence=not_confident)
       │  └─ [Tier 1] LLM Call - Gemini Pro (model=gemini-pro, tokens=750, cost=$0.001) - 1.4s
       └─ ... (3 more tickets)
```

**Observations**:
- **Tier 3** shows Zendesk API is fast (0.2-0.3s per call)
- **Tier 1** shows Gemini LLM is slow (1.5-1.9s per call) ← bottleneck
- **Tier 2** shows Phase 2 (synthesis) is slowest (4.2s) ← optimization target
- Can filter by `primary_pod` or `confidence` for error analysis

**Consequences**:

### Positive Consequences
1. ✅ **Complete Visibility**: Can trace failure root causes from API → LLM → business logic
2. ✅ **Granular Analysis**: Can analyze each tier independently (API latency vs LLM latency vs business logic)
3. ✅ **Error Correlation**: See how API failures cascade to LLM errors
4. ✅ **Performance Optimization**: Identify bottlenecks at each tier

### Negative Consequences
1. ⚠️ **Instrumentation Overhead**: More spans = more data storage, more export bandwidth
   - **Mitigation**: Use batch span processing (async export), sample high-volume traces if needed
2. ⚠️ **Code Complexity**: Manual spans (Tier 2) add code to business logic
   - **Mitigation**: Centralize span creation logic, use context managers (`with tracer.start_as_current_span()`)

**Alternatives Considered**:

1. **Tier 1 Only** (LLM auto-instrumentation)
   - **Rejected**: Can't diagnose API failures, no business context (ticket_id, POD)
2. **Tier 2 Only** (Manual business logic spans)
   - **Rejected**: Lose auto-instrumentation benefits (LLM token counts, HTTP status codes)
3. **Tier 1 + Tier 2** (No API tracing)
   - **Rejected**: User explicitly requested API tracing for failure diagnosis

---

## ADR-004: Local-First Deployment Approach

**Status**: Accepted (Phase 4)

**Decision Date**: 2025-11-09

**Context**:

Need to decide deployment model for observability platforms (Phoenix, Langfuse):
1. Local deployment (Docker on Mac)
2. Cloud VM deployment (AWS EC2, GCP Compute Engine)
3. Managed cloud services (Langfuse Cloud, future Braintrust)

**Decision**:

Start with **local deployment** (Docker on Mac) for Phase 4a.

**Rationale**:

### Goal Alignment

**User Requirement**:
> "To START off with, I just need to showcase this on my LOCAL Mac. The goal is to showcase how easy or difficult it is from a developer stand point as well as from a feature parity/loss stand point."

**Organizational Demo Objective**: Compare self-hosted developer experience vs cloud

### Why Local Deployment?

#### 1. Developer Experience Evaluation
- **Target Audience**: Developers in organization evaluating observability tools
- **Key Question**: "How hard is it to run this on my laptop?"
- **Local = Best Case**: If local is too complex, cloud won't help
- **Demonstration Value**:
  - Phoenix: "5-minute setup, one Docker command" → showcase ease
  - Langfuse: "30-minute setup, multi-container orchestration" → showcase complexity

#### 2. Zero Infrastructure Cost
- No cloud VM provisioning
- No network egress charges
- No managed service fees
- **Budget-Friendly**: Organization can evaluate at $0 cost

#### 3. Iteration Speed
- Restart containers in seconds (no cloud deploy wait)
- Modify docker-compose locally, test immediately
- No VPN/SSH overhead
- **Fast Experimentation**: Can test different configurations quickly

#### 4. Data Privacy (No Network Transmission)
- All data stays on local machine
- No accidental data exfiltration to cloud
- No need for VPN or network isolation
- **Security-Conscious**: Sensitive Zendesk tickets never leave laptop

### Setup Complexity Showcase

**Phoenix (Local)**:
```bash
# 1 command, 5 minutes
docker run -d -p 6006:6006 -p 4317:4317 arizephoenix/phoenix:latest
```

**Langfuse (Local)**:
```bash
# docker-compose.yml setup, 30 minutes
# 5 services: web, worker, postgres, clickhouse, redis
# Requires PostgreSQL schema setup, ClickHouse initialization
docker-compose -f docker-compose.langfuse.yml up -d
```

**Cloud VM** (hypothetical):
```bash
# Provision VM (10 min)
# Configure security groups (5 min)
# Install Docker (5 min)
# Same docker run/docker-compose commands (5-30 min)
# Configure DNS (optional, 10 min)
# Total: 35-60 minutes
```

**Verdict**: Local is simpler → best for showcasing "developer experience"

### Minimal Basic Setup

**User Requirement**:
> "I need the MINIMAL, basic set up required to have my data be visualized in the tools I've mentioned."

**Local Deployment Delivers**:
- Phoenix: SQLite storage (no PostgreSQL setup)
- Langfuse: docker-compose handles all dependencies
- No TLS certificates, no reverse proxy, no DNS
- Access via `localhost` (no network complexity)

**Consequences**:

### Positive Consequences
1. ✅ **Fast Setup**: Phoenix in 5 minutes, Langfuse in 30 minutes
2. ✅ **Zero Cost**: No cloud infrastructure charges
3. ✅ **Data Privacy**: All data on local machine
4. ✅ **Iteration Speed**: Restart/reconfigure in seconds
5. ✅ **Organizational Demo**: Clear baseline for "self-hosted developer experience"

### Negative Consequences
1. ⚠️ **Not Production-Grade**: Local setup lacks HA, backups, monitoring
   - **Mitigation**: Document production deployment in separate section (future)
2. ⚠️ **Single-User**: Can't share dashboard with team
   - **Mitigation**: This is expected for Phase 4a (local demo)
3. ⚠️ **Limited Scale**: SQLite (Phoenix) won't handle 1M+ traces
   - **Mitigation**: Phase 4a processes <1000 tickets, sufficient for demo

**Alternatives Considered**:

1. **Cloud VM Deployment** (AWS EC2)
   - **Rejected**: Slower setup, incurs cost, overkill for Phase 4a demo
   - **Future**: Document cloud deployment for production in separate guide
2. **Langfuse Cloud** (managed service)
   - **Rejected**: Can't demonstrate self-hosted ease-of-setup
   - **Future**: Add in Phase 4b for cloud comparison

**Future Evolution**:

**Phase 4b** (Cloud Comparison):
- Keep local Phoenix (baseline)
- Add Braintrust Cloud (cloud ease-of-setup comparison)
- Compare:
  - Local Phoenix (5 min, $0, local data)
  - Braintrust Cloud (10 min signup, paid, cloud data)
- Document production deployment guide (cloud VMs, Kubernetes)

---

## ADR-005: Dynamic Execution Model with CLI Branching

**Status**: Accepted (Phase 3b & Phase 4)

**Decision Date**: 2025-11-09

**Context**:

The application has **conditional execution** based on `--analysis-type` CLI parameter ([main.py:822-859](../main.py#L822-L859)):

**Execution Flows**:
1. `--analysis-type pod` → Only runs Phase 3a (POD Categorization)
2. `--analysis-type diagnostics` → Only runs Phase 3b (Diagnostics Analysis)
3. `--analysis-type both` → Runs **BOTH in parallel** (lines 837-847: `asyncio.gather()`)

**Problem**: Instrumentation must handle dynamic phase execution without breaking or creating orphaned spans.

**Decision**:

Implement **conditional span creation** based on `analysis_type`, with OpenTelemetry context propagation for parallel execution.

**Rationale**:

### Critical Constraint from Codebase

**User Clarification**:
> "In your SPAN hierarchy example, you have Phase 3a & Phase 3b. However, PLEASE REMEMBER/NOTE THAT these phases are NOT sequential. They are ON-DEMAND & CAN BE SPECIFIED BY the user using the application via a CLI parameter. YOU NEED TO ENSURE that the span hierarchy ADJUSTS & doesn't BREAK."

**Example Failure (Naive Instrumentation)**:
```python
# BAD: Always creates Phase 3a and 3b spans
async def run(self, csv_path):
    with tracer.start_as_current_span("Process Tickets"):
        await fetch_phase()
        await synthesis_phase()

        # BUG: Always creates Phase 3a span, even if --analysis-type diagnostics
        with tracer.start_as_current_span("Phase 3a: Categorization"):
            if self.analysis_type in ["pod", "both"]:
                await categorization_phase()  # Only runs if pod/both
            # Span exists even if categorization didn't run!

        # BUG: Always creates Phase 3b span, even if --analysis-type pod
        with tracer.start_as_current_span("Phase 3b: Diagnostics"):
            if self.analysis_type in ["diagnostics", "both"]:
                await diagnostics_phase()  # Only runs if diagnostics/both
            # Span exists even if diagnostics didn't run!
```

**Problem**: Empty spans for phases that didn't execute → misleading traces

### Solution: Conditional Span Creation

**Correct Implementation**:
```python
# GOOD: Conditionally create spans based on analysis_type
async def run(self, csv_path):
    with tracer.start_as_current_span("Process Tickets") as root_span:
        # Add analysis_type attribute for filtering
        root_span.set_attribute("analysis_type", self.analysis_type)

        # Phase 1 & 2: Always run
        await fetch_phase(...)
        await synthesis_phase(...)

        # Phase 3: Conditional based on analysis_type
        if self.analysis_type == "pod":
            # Only create Phase 3a span
            await categorization_phase(...)

        elif self.analysis_type == "diagnostics":
            # Only create Phase 3b span
            await diagnostics_phase(...)

        elif self.analysis_type == "both":
            # Create BOTH spans concurrently
            await asyncio.gather(
                categorization_phase(...),  # Creates Phase 3a span
                diagnostics_phase(...)      # Creates Phase 3b span
            )

# In categorization_phase (only called if analysis_type="pod" or "both")
async def categorization_phase(self, tickets):
    # This span is ONLY created if this function is called
    with tracer.start_as_current_span("Phase 3a: POD Categorization") as span:
        span.set_attribute("phase", "categorization")
        # ... categorization logic ...

# In diagnostics_phase (only called if analysis_type="diagnostics" or "both")
async def diagnostics_phase(self, tickets):
    # This span is ONLY created if this function is called
    with tracer.start_as_current_span("Phase 3b: Diagnostics Analysis") as span:
        span.set_attribute("phase", "diagnostics")
        # ... diagnostics logic ...
```

**Result**: Span hierarchy matches actual execution

### Span Hierarchy Examples (All Scenarios)

#### Scenario 1: `--analysis-type pod`
```
[Process Tickets] (analysis_type=pod)
├─ [Phase 1: Fetch]
├─ [Phase 2: Synthesis]
└─ [Phase 3a: POD Categorization]  ← Only Phase 3a span
```

#### Scenario 2: `--analysis-type diagnostics`
```
[Process Tickets] (analysis_type=diagnostics)
├─ [Phase 1: Fetch]
├─ [Phase 2: Synthesis]
└─ [Phase 3b: Diagnostics Analysis]  ← Only Phase 3b span
```

#### Scenario 3: `--analysis-type both` (PARALLEL)
```
[Process Tickets] (analysis_type=both)
├─ [Phase 1: Fetch]
├─ [Phase 2: Synthesis]
├─ [Phase 3a: POD Categorization]  ← CONCURRENT
└─ [Phase 3b: Diagnostics Analysis]  ← CONCURRENT
```

**Timeline (Gantt chart for Scenario 3)**:
```
Time:      0s      2s      6s      9s
           ├───────┼───────┼───────┤
Phase 1:   ████████
Phase 2:           ██████████
Phase 3a:                   ██████ ← Parallel
Phase 3b:                   ██████ ← Parallel
```

### Parallel Context Propagation (OpenTelemetry)

**Challenge**: When `--analysis-type both`, Phase 3a and 3b run concurrently via `asyncio.gather()` ([main.py:845-847](../main.py#L845-L847))

**OpenTelemetry Guarantee**: Async context propagation

**How It Works**:
```python
# In main.py
async def run(self):
    with tracer.start_as_current_span("Process Tickets") as root_span:
        # ... Phase 1 & 2 ...

        # Create concurrent tasks
        pod_task = asyncio.create_task(self.categorization_phase(tickets))
        diag_task = asyncio.create_task(self.diagnostics_phase(tickets))

        # Wait for both (asyncio.gather)
        categorized, analyzed = await asyncio.gather(pod_task, diag_task)

# OpenTelemetry automatically:
# 1. Propagates root span context to both tasks
# 2. Creates Phase 3a and Phase 3b as sibling spans under root
# 3. Handles concurrent span completion
```

**No Manual Context Passing Required**: OpenTelemetry SDK handles asyncio context propagation automatically

### Filtering Traces by Analysis Type

**Use Case**: In Phoenix/Langfuse, filter traces by analysis type

**Query Examples**:
- `analysis_type = "pod"` → Show only POD categorization traces
- `analysis_type = "diagnostics"` → Show only diagnostics traces
- `analysis_type = "both"` → Show traces with both analyses

**Implementation**: Root span attribute
```python
root_span.set_attribute("analysis_type", self.analysis_type)
```

**Consequences**:

### Positive Consequences
1. ✅ **Accurate Traces**: Span hierarchy matches actual execution (no empty spans)
2. ✅ **Parallel Support**: OpenTelemetry handles concurrent execution correctly
3. ✅ **Filterable**: Can query traces by `analysis_type` for targeted analysis
4. ✅ **Non-Breaking**: Instrumentation respects existing CLI branching logic

### Negative Consequences
1. ⚠️ **Conditional Complexity**: Instrumentation code mirrors branching logic
   - **Mitigation**: Keep instrumentation close to business logic (same file)
2. ⚠️ **Testing Overhead**: Must test all 3 execution paths (`pod`, `diagnostics`, `both`)
   - **Mitigation**: Automated tests for each `analysis_type` scenario

**Alternatives Considered**:

1. **Always Create All Spans** (rejected)
   - **Con**: Empty spans for phases that didn't run
   - **Con**: Misleading traces (looks like Phase 3a ran when it didn't)
2. **Single Combined Phase 3 Span** (rejected)
   - **Con**: Can't distinguish POD vs diagnostics latency
   - **Con**: Loses granularity for performance analysis

---

## ADR-006: Factory Pattern for LLM Provider Abstraction (Phase 3c)

**Status**: Accepted (Phase 3c)

**Decision Date**: 2025-11-03

**Context**:

Phase 3c added multi-model LLM support (Gemini + Azure OpenAI). Need architecture to:
1. Abstract provider selection (Gemini vs Azure)
2. Support future providers (Anthropic Claude, OpenAI direct)
3. Maintain backward compatibility (default to Gemini)

**Decision**:

Use **Factory Pattern** with unified `LLMResponse` interface.

**Rationale**:

See ADR-001 for observability instrumentation benefits. This ADR focuses on LLM provider abstraction benefits.

### Why Factory Pattern?

**Code Structure** ([llm_provider.py](../llm_provider.py)):
```python
class LLMProviderFactory:
    @staticmethod
    def get_provider(provider: str = "gemini"):
        if provider == "gemini":
            return GeminiClient()
        elif provider == "azure":
            return AzureOpenAIClient()
        else:
            raise ValueError(f"Unknown provider: {provider}")

# Usage in synthesizer.py
class GeminiSynthesizer:
    def __init__(self, model_provider: str = "gemini"):
        self.llm_client = LLMProviderFactory.get_provider(provider=model_provider)

    async def synthesize_ticket(self, ticket_data):
        response = await self.llm_client.generate_content(prompt)  # Unified interface
```

**Benefits**:
1. **Centralized Provider Selection**: All provider logic in one place
2. **Unified Interface**: All providers implement `generate_content()` → return `LLMResponse` with `.text` property
3. **Backward Compatible**: Default `provider="gemini"` maintains existing behavior
4. **Easy Testing**: Can mock factory to return test provider

**Alternatives Considered**:

1. **Strategy Pattern** (runtime provider swapping)
   - **Rejected**: No use case for switching providers mid-execution
2. **Direct Instantiation** (no abstraction)
   - **Rejected**: Tight coupling, hard to test

**References**: See [Phase 3c in implementation_plan.md](./implementation_plan.md#phase-3c-multi-model-llm-support)

---

## ADR-007: No Automatic Fallback Between LLM Providers

**Status**: Accepted (Phase 3c)

**Decision Date**: 2025-11-03

**Context**:

When Azure OpenAI fails (API error, quota exceeded), should the application:
1. Automatically fall back to Gemini free tier?
2. Retry Azure, then fail hard?

**Decision**:

**Retry Azure on failure, then fail hard** (no fallback to Gemini).

**Rationale**:

**User Requirement**:
> "When the data is large, falling back to Gemini which is a free tier API will give me half baked results. Fail hard, I can choose to re-run when I want."

### Why Fail Hard?

#### 1. Data Integrity
- Gemini free tier unreliable for large datasets (rate limits, inconsistent quality)
- Falling back mid-run creates **mixed results**: Some tickets analyzed by Azure, others by Gemini
- User can't trust output quality if provider switched silently

#### 2. Explicit User Control
- User chose `--model-provider azure` for a reason (cost, quality, SLA)
- Silent fallback violates user intent
- Better to fail loudly than produce inconsistent results

#### 3. Easier Debugging
- Clear failure point: "Azure quota exceeded"
- User knows exact cause, can increase quota or switch to Gemini manually
- Silent fallback hides root cause

### Implementation

```python
# llm_provider.py - Azure client
class AzureOpenAIClient:
    def generate_content(self, prompt: str):
        try:
            response = self.client.chat.completions.create(...)
            return LLMResponse(text=response.choices[0].message.content)
        except Exception as e:
            # Retry once (built into SDK)
            # If still fails, raise exception (no fallback)
            raise GeminiAPIError(f"Azure OpenAI API call failed: {e}")
```

**User Workflow**:
```bash
# Run with Azure
python main.py --input tickets_1000.csv --analysis-type both --model-provider azure

# If Azure quota exceeded:
# ERROR: Azure OpenAI API call failed: QuotaExceeded

# User manually switches to Gemini
python main.py --input tickets_1000.csv --analysis-type both --model-provider gemini
```

**Consequences**:
- ✅ **Data Integrity**: No mixed-provider results
- ✅ **User Control**: Explicit provider choice honored
- ⚠️ **No Resilience**: Azure failure stops entire run
  - **Mitigation**: User can re-run with different provider

**Alternatives Considered**:

1. **Automatic Fallback to Gemini** (rejected)
   - **Con**: Mixed results, violates user intent
2. **Fallback Only for Paid Gemini** (future consideration)
   - **Pro**: If paid Gemini API available, fallback is acceptable
   - **Status**: Not implemented in Phase 3c, revisit in Phase 4

**References**: See [Phase 3c in implementation_plan.md](./implementation_plan.md#adr-007-no-automatic-fallback-between-llm-providers)

---

## ADR-008: Binary Confidence Scoring for POD Categorization

**Status**: Accepted (Phase 2)

**Decision Date**: 2025-05-10

**Context**:

For POD categorization, need confidence scoring to flag ambiguous cases for human review. Options:
1. Binary: "confident" or "not confident"
2. 3-level: "high", "medium", "low"
3. Numeric: 0.0 to 1.0 (e.g., 0.85)

**Decision**:

Use **binary confidence scoring** ("confident" vs "not confident").

**Rationale**:

### Why Binary?

#### 1. Actionability
- Clear decision: Review ticket or don't review
- No ambiguity: "medium confidence" → should I review or not?
- **User Workflow**:
  - `confident` → Trust LLM, no review
  - `not confident` → Human review required

#### 2. Simplicity (LLM Prompt Design)
- Easier for LLM to decide binary vs 3-way split
- Less prompt engineering to explain "high vs medium vs low"
- Reduces LLM hallucination risk

#### 3. Avoids Middle-Ground Trap
- "Medium confidence" often becomes dumping ground
- Binary forces LLM to commit: "Am I sure or not?"

**Consequences**:
- ✅ **Clear Workflow**: Review or don't review
- ✅ **Simpler Prompt**: LLM decision is binary
- ⚠️ **Loss of Granularity**: Can't distinguish "slightly confident" vs "very confident"
  - **Mitigation**: Add `confidence_reason` field for nuance

**Alternatives Considered**:

1. **3-level** (rejected): "Medium" becomes ambiguous
2. **Numeric** (rejected): Over-engineered, LLM struggles with precise scores

**References**: See [Phase 2 in implementation_plan.md](./implementation_plan.md#adr-008-binary-confidence-scoring-for-pod-categorization)

---

## ADR-009: Ternary Assessment for Diagnostics Analysis

**Status**: Accepted (Phase 3b)

**Decision Date**: 2025-11-02

**Context**:

For diagnostics "Could Diagnostics help?" assessment, need classification. Options:
1. Binary: "yes" or "no"
2. Ternary: "yes", "no", "maybe"

**Decision**:

Use **ternary classification** ("yes", "no", "maybe").

**Rationale**:

### Why Ternary (vs Binary for POD)?

**Key Difference**: Diagnostics assessment has inherent ambiguity

#### Examples of "Maybe" Cases:
- **Ticket**: "Flow not working, customer reported click issue"
  - **Could Diagnostics help?**: Maybe
  - **Reasoning**: If click failure is due to CSS selector → yes. If due to application bug → no. Insufficient information in ticket.

- **Ticket**: "Smart Tip displaying inconsistently"
  - **Could Diagnostics help?**: Maybe
  - **Reasoning**: Diagnostics can check visibility rules, but "inconsistent" might be timing issue outside Diagnostics scope.

**Binary Scoring Would Force**:
- LLM to guess "yes" or "no" → hallucination
- Or default to "not confident" → loses signal

**Ternary Scoring Allows**:
- LLM to express uncertainty: "maybe" + "not confident" = clear flag for manual review
- More accurate than forced binary choice

**Consequences**:
- ✅ **Accurate Assessment**: LLM can express genuine uncertainty
- ✅ **Better Signal**: "yes" means definite, "maybe" means possible, "no" means impossible
- ⚠️ **More Complex Workflow**: 3 buckets instead of 2
  - **Mitigation**: "maybe" + "not confident" → human review

**Alternatives Considered**:

1. **Binary** (rejected): Forces LLM to guess, reduces accuracy
2. **4-level** ("yes", "probably", "probably not", "no") (rejected): Over-engineered

**References**: See [Phase 3b in implementation_plan.md](./implementation_plan.md#adr-009-ternary-assessment-for-diagnostics-analysis)

---

## ADR-010: Separate Output Files for Different Analysis Types

**Status**: Accepted (Phase 3b)

**Decision Date**: 2025-11-02

**Context**:

When `--analysis-type both` (run POD + Diagnostics in parallel), how to structure output?
1. Single JSON with both analyses
2. Separate JSON files (one for POD, one for Diagnostics)

**Decision**:

Generate **two separate output files** when `--analysis-type both`:
- `output_pod_YYYYMMDD_HHMMSS.json` (POD categorization)
- `output_diagnostics_YYYYMMDD_HHMMSS.json` (Diagnostics analysis)

**Rationale**:

### Why Separate Files?

#### 1. Different Stakeholders
- **POD categorization**: Product managers, support categorization teams
- **Diagnostics analysis**: Diagnostics feature team, product analytics
- Different audiences need different data → separate files easier to consume

#### 2. Different Metadata Needs
- **POD**: `pod_distribution`, `confidence_breakdown`
- **Diagnostics**: `was_used`, `could_help`, `diagnostics_confidence`
- Combining into single metadata structure is awkward

#### 3. Clearer Separation of Concerns
- Each file has single, focused purpose
- Easier to parse, validate, archive

**Implementation** ([main.py](../main.py)):
```python
if self.analysis_type == "both":
    # Generate two files
    pod_filename = f"output_pod_{timestamp}.json"
    diag_filename = f"output_diagnostics_{timestamp}.json"

    # Each file has analysis_type-specific metadata
    pod_output["metadata"]["analysis_type"] = "pod"
    diag_output["metadata"]["analysis_type"] = "diagnostics"
```

**Consequences**:
- ✅ **Clear Stakeholder Separation**: POD team gets POD file, Diagnostics team gets Diagnostics file
- ✅ **Simpler Metadata**: Each file has focused metadata structure
- ⚠️ **File Proliferation**: 2 files instead of 1
  - **Mitigation**: Clear naming convention makes pairing obvious

**Alternatives Considered**:

1. **Single Combined File** (rejected): Awkward metadata structure, mixed stakeholder needs
2. **Single File with Two Top-Level Keys** (`{"pod_analysis": {...}, "diagnostics_analysis": {...}}`) (rejected): Still mixed stakeholder needs

**References**: See [Phase 3b in implementation_plan.md](./implementation_plan.md#adr-010-separate-output-files-for-different-analysis-types)

---

## ADR-011: JIRA URL as Source of Truth for Escalation

**Status**: Accepted (Phase 5)

**Decision Date**: 2025-11-17

**Context**:

For Phase 5 (Engineering Escalation tracking), we need to determine whether a Zendesk ticket was escalated to Engineering. Two custom fields are available:
1. **Cross Team field** (ID: 48570811421977) - Values: "cross_team_n/a" or "cross_team_succ"
2. **JIRA Ticket URL field** (ID: 360024807472) - Contains link to JIRA ticket

**Problem**: Which field should be the source of truth for escalation status?

**Scenario**: Support agent creates JIRA ticket and pastes URL in Zendesk, but forgets to update Cross Team field from "N/A" to "SUCC"

**Decision**:

Use **JIRA Ticket URL field as the source of truth** for escalation status.

**Rationale**:

### Why JIRA URL Over Cross Team Field?

#### 1. Concrete Evidence of Escalation
- JIRA URL = physical link to escalation ticket (verifiable, clickable)
- Cross Team field = just an indicator (can be out of sync)
- If JIRA URL exists → escalation definitely happened
- If Cross Team says "SUCC" but no URL → ambiguous (was it actually escalated?)

#### 2. Handles Support Agent Forgetfulness
**Common Workflow**:
1. Support agent identifies product bug
2. Creates JIRA ticket in Engineering backlog
3. Copies JIRA URL to Zendesk custom field
4. **Forgets to update Cross Team field from "N/A" to "SUCC"**

**With Cross Team as source of truth**:
- `is_escalated = False` (incorrect - ticket WAS escalated)
- Analytics miss this escalation

**With JIRA URL as source of truth**:
- `is_escalated = True` (correct - JIRA URL proves escalation)
- Analytics capture all escalations

#### 3. Data Consistency Logic

**Implementation**:
```python
def determine_escalation_status(cross_team_value, jira_url):
    # JIRA URL is source of truth
    is_escalated = bool(jira_url and jira_url.strip() != "")

    return {
        "is_escalated": is_escalated,
        "cross_team_status": normalize_cross_team_field(cross_team_value),  # Keep for reference
        "jira_ticket_url": jira_url,
        "jira_ticket_id": extract_jira_ticket_id(jira_url)
    }
```

**Edge Cases Handled**:
- JIRA URL exists, Cross Team = "N/A" → **is_escalated = True** (trust URL)
- JIRA URL empty, Cross Team = "SUCC" → **is_escalated = False** (no physical evidence)
- Both empty → **is_escalated = False** (no escalation)
- Both populated → **is_escalated = True** (both agree)

**Consequences**:

### Positive Consequences
1. ✅ **Captures All Escalations**: Doesn't miss escalations due to forgot ten field updates
2. ✅ **Verifiable**: JIRA URL can be clicked to verify escalation actually exists
3. ✅ **Human Error Tolerance**: Handles support agent workflow mistakes gracefully

### Negative Consequences
1. ⚠️ **Relies on URL Field Accuracy**: If support agent pastes wrong URL, escalation data is incorrect
   - **Mitigation**: JIRA ticket ID extracted from URL can be verified manually if needed
2. ⚠️ **Cross Team Field Becomes Secondary**: Cross Team field is stored but not used for is_escalated
   - **Mitigation**: Still include `cross_team_status` in output for manual review/reconciliation

**Alternatives Considered**:

1. **Cross Team Field as Source of Truth** (rejected)
   - **Con**: Support agents forget to update it
   - **Con**: More likely to be out of sync than URL field

2. **Both Fields Must Agree** (rejected)
   - **Con**: Too strict - would miss valid escalations due to field sync issues
   - **Con**: More false negatives

3. **Either Field Can Indicate Escalation** (rejected)
   - **Con**: Too loose - could have false positives (Cross Team = "SUCC" but no actual JIRA ticket)

**References**:
- [Phase 5 in implementation_plan.md](./implementation_plan.md#phase-5-engineering-escalation--csv-export)
- [utils.py:determine_escalation_status()](../utils.py)

---

## ADR-012: Escalation Signal in Diagnostics Analysis Only

**Status**: Accepted (Phase 5)

**Decision Date**: 2025-11-17

**Context**:

Phase 5 adds escalation status tracking. Need to determine which LLM analysis phases should receive escalation status as input:
- **Synthesis** (Phase 2): Distills ticket content into issue/root_cause/summary/resolution
- **POD Categorization** (Phase 2): Assigns ticket to product domain (WFE, Guidance, etc.)
- **Diagnostics Analysis** (Phase 3b): Assesses if Diagnostics feature was used / could have helped

**Decision**:

Include escalation status **ONLY in Diagnostics Analysis prompt**, NOT in Synthesis or Categorization.

**Rationale**:

### Why NOT in Synthesis?

**Synthesis = Pure Content Distillation**

**Principle**: Synthesis should objectively summarize ticket content without external metadata

**Reasoning**:
- Escalation status is **metadata ABOUT the ticket**, not content FROM the ticket
- If ticket was escalated, the **comments already mention it**:
  - "Logged with engineering team for investigation"
  - "Identified as product bug, created JIRA ticket SUCC-36126"
  - "Waiting for engineering fix"
- Including escalation could **bias synthesis** to overemphasize severity vs actual content

**Example**:
- Ticket escalated but synthesis should still objectively describe what happened
- Synthesis should capture "escalated to engineering" by reading comments, not from metadata injection

**Verdict**: Keep synthesis metadata-free ✅

### Why NOT in Categorization?

**Categorization = Technical Domain Assignment**

**Principle**: POD categorization is about **which team owns the functionality**, not **severity or escalation status**

**Reasoning**:
- A bug in WFE is still **WFE**, whether escalated or not
- A bug in Guidance is still **Guidance**, whether escalated or not
- Escalation doesn't change **which POD owns the technical domain**
- Synthesis (issue_reported, root_cause, resolution) **already contains enough signal** about the technical area

**Example**:
- Ticket: "Smart Tip not displaying on specific page, escalated to Engineering (JIRA: SUCC-36126)"
- **Without escalation signal**: LLM categorizes as **Guidance** (Smart Tip = Guidance functionality)
- **With escalation signal**: LLM still categorizes as **Guidance** (escalation doesn't change ownership)
- **Conclusion**: Escalation adds no value to categorization

**Verdict**: Keep categorization domain-focused ✅

### Why YES in Diagnostics Analysis?

**Diagnostics Analysis = Self-Serviceability Assessment**

**Principle**: Escalated tickets = product bugs that **CANNOT be self-serviced**, regardless of symptom similarity

**Critical Insight** (from user):
> "If a ticket was escalated to Engineering, that means there is a GENUINE bug in the product. Diagnostics analysis should REFLECT this nuance, don't you think?"

**Reasoning**:

#### 1. Prevents False Positives

**Scenario**: Ticket escalated with visibility rule failure symptom

**WITHOUT Escalation Signal**:
```
LLM Analysis:
- Symptom: "Visibility rule not evaluating correctly"
- LLM Assessment: "Yes, Diagnostics could help - shows rule evaluation status"
- PROBLEM: This is a PRODUCT BUG in the rule engine, Diagnostics cannot fix it!
```

**WITH Escalation Signal**:
```
LLM Analysis:
- Symptom: "Visibility rule not evaluating correctly"
- Escalation: True (JIRA: SUCC-36126)
- LLM Assessment: "No - escalated as product bug. Diagnostics can diagnose but cannot fix engine-level defects."
- CORRECT: Diagnostics cannot resolve product bugs requiring code changes
```

#### 2. Distinguishes Self-Serviceable vs Product Defects

**Key Distinction**:
- **Self-Serviceable Issue**: Authoring error (wrong selector, incorrect rule logic) → Diagnostics helps
- **Product Bug**: Engine-level defect (rule evaluator broken, renderer bug) → Diagnostics useless

**Escalation = Strong Signal** that issue is product-level, not authoring-level

#### 3. Real Example from Codebase

**Ticket 90346** (from conversation):
- Subject: "No Tooltip on smart tip showing again"
- Issue: Smart Tip tooltip icon not appearing after element selection
- Resolution: "Escalated to Engineering as known product bug affecting Bullhorn integration (JIRA: SUCC-36126)"

**WITHOUT Escalation Signal**:
- LLM might say: "Diagnostics could help - check element targeting"
- **Incorrect**: This is a rendering engine bug, not targeting issue

**WITH Escalation Signal**:
- LLM says: "No - escalated as product bug (JIRA: SUCC-36126). Diagnostics cannot fix renderer defects."
- **Correct**: Acknowledges product-level nature

### Updated Diagnostics Prompt (Phase 5)

**Added Section**:
```python
## TICKET DATA

**ESCALATION STATUS:**
- **Escalated to Engineering:** {is_escalated}
- **JIRA Ticket ID:** {jira_ticket_id}

## CRITICAL: Escalation Context

**If this ticket was escalated to Engineering (is_escalated = True):**

This indicates a **GENUINE PRODUCT BUG** requiring code-level fixes.

**Analysis Guidelines:**
1. **Default Assessment:** `could_diagnostics_help` = "no"
   - Reasoning: "Escalated to Engineering as product bug (JIRA: {jira_ticket_id}). Diagnostics cannot resolve product-level defects."

2. **Exception:** If synthesis shows Diagnostics was used to IDENTIFY the bug → "maybe"
   - Reasoning: "Diagnostics helped diagnose but could not resolve (JIRA: {jira_ticket_id})."
```

**Consequences**:

### Positive Consequences
1. ✅ **Accurate Diagnostics Assessment**: No false positives for product bugs
2. ✅ **CSV Column Correlation**: Strong correlation between `is_escalated=TRUE` and `could_diagnostics_help=no`
3. ✅ **Business Insights**: Can calculate:
   - "X% of escalated tickets could NOT have been solved with Diagnostics" (validates Diagnostics scope)
   - "Y% of non-escalated troubleshooting tickets could have used Diagnostics" (missed self-service opportunities)

### Negative Consequences
1. ⚠️ **Prompt Complexity**: Diagnostics prompt becomes longer (added escalation logic)
   - **Mitigation**: Complexity is necessary for accuracy, well-documented in prompt
2. ⚠️ **Dependence on Escalation Field Accuracy**: If escalation field is wrong, diagnostics assessment is wrong
   - **Mitigation**: ADR-011 (JIRA URL as source of truth) minimizes field inaccuracy

**Alternatives Considered**:

1. **Include Escalation in All Phases** (rejected)
   - **Con**: Synthesis becomes biased, categorization unchanged by escalation
   - **Con**: Only diagnostics benefits from escalation signal

2. **Exclude Escalation from All Phases** (rejected)
   - **Con**: Diagnostics produces false positives on product bugs
   - **Con**: User explicitly requested escalation signal in diagnostics

3. **Create Separate "Escalation Analysis" Phase** (rejected)
   - **Con**: Over-engineered, escalation is just one input to diagnostics
   - **Con**: Adds unnecessary complexity

**References**:
- [Phase 5 in implementation_plan.md](./implementation_plan.md#phase-5-engineering-escalation--csv-export)
- [config.py:DIAGNOSTICS_ANALYSIS_PROMPT](../config.py)

---

## ADR-013: Separate CSV Files Per Analysis Type

**Status**: Accepted (Phase 5)

**Decision Date**: 2025-11-17

**Context**:

Phase 5 adds CSV export for Google Sheets analysis. Need to decide CSV output structure:
1. **Single CSV with all columns** (POD + Diagnostics + Escalation)
2. **Separate CSVs per analysis type** (POD CSV, Diagnostics CSV)

**User Requirement**:
> "For both categorizer & diagnostics analysis outputs, I need a clean CSV version that is exported after each run. The CSV columns should reflect the individual ticket IDs and the corresponding analysis done."

**Decision**:

Generate **separate CSV files per analysis type**:
- POD Categorization: `output_pod_YYYYMMDD_HHMMSS.csv`
- Diagnostics Analysis: `output_diagnostics_YYYYMMDD_HHMMSS.csv`

**Rationale**:

### Why Separate CSVs?

#### 1. Different Stakeholders

**POD Categorization CSV**:
- **Audience**: Product managers, support categorization teams
- **Use Case**: Verify POD assignments, review low-confidence tickets
- **Key Columns**: `primary_pod`, `categorization_reasoning`, `confidence`, `alternative_pods`

**Diagnostics Analysis CSV**:
- **Audience**: Diagnostics feature team, product analytics
- **Use Case**: Track Diagnostics usage, identify missed self-service opportunities
- **Key Columns**: `was_diagnostics_used_llm_assessment`, `could_diagnostics_help_assessment`, `diagnostics_capabilities_matched`

**Benefit**: Each team gets focused CSV with only relevant columns

#### 2. Different Column Structures

**POD CSV**: 21 columns
- Ticket metadata, escalation, synthesis, **categorization-specific** (primary_pod, reasoning, alternatives)

**Diagnostics CSV**: 26 columns
- Ticket metadata, escalation, synthesis, **diagnostics-specific** (was_used, could_help, capabilities, ticket_type)

**Combined CSV**: 37+ columns
- **Problem**: Too wide, hard to navigate in Google Sheets
- **Problem**: Many empty/NA columns depending on analysis type run

#### 3. Google Sheets Usability

**Separate CSVs**:
- POD CSV: 21 columns → fits in spreadsheet viewport
- Diagnostics CSV: 26 columns → fits in spreadsheet viewport
- Easy to scan, filter, sort

**Combined CSV**:
- 37+ columns → requires horizontal scrolling
- Cluttered with NA values in columns not relevant to analysis type
- Harder to share with stakeholders (too much noise)

#### 4. Mirrors JSON Output Structure

**Existing Pattern** (Phase 3b):
- POD analysis: `output_pod_YYYYMMDD_HHMMSS.json`
- Diagnostics analysis: `output_diagnostics_YYYYMMDD_HHMMSS.json`
- Separate files already established

**Consistency**: CSV structure mirrors JSON structure

### Implementation

```python
# csv_exporter.py
class CSVExporter:
    def export_pod_categorization(self, tickets, output_path):
        fieldnames = [
            "ticket_id", "serial_no", "url", "subject", "status",
            "created_at", "comments_count",
            # Escalation columns
            "is_escalated", "jira_ticket_id", "jira_ticket_url",
            # Synthesis columns
            "issue_reported", "root_cause", "summary", "resolution",
            # POD categorization columns
            "primary_pod", "categorization_reasoning", "confidence",
            "alternative_pods", "alternative_reasoning",
            "processing_status", "error"
        ]
        # ... write CSV ...

    def export_diagnostics_analysis(self, tickets, output_path):
        fieldnames = [
            "ticket_id", "serial_no", "url", "subject", "status",
            "created_at", "comments_count",
            # Escalation columns
            "is_escalated", "jira_ticket_id", "jira_ticket_url",
            # Synthesis columns
            "issue_reported", "root_cause", "summary", "resolution",
            # Diagnostics analysis columns
            "was_diagnostics_used_custom_field",
            "was_diagnostics_used_llm_assessment",
            "could_diagnostics_help_assessment",
            "diagnostics_capabilities_matched",
            "ticket_type",
            "processing_status", "error"
        ]
        # ... write CSV ...
```

**File Naming**:
- `output_pod_20251117_143246.csv`
- `output_diagnostics_20251117_162748.csv`
- Timestamp makes pairing obvious if needed

**Consequences**:

### Positive Consequences
1. ✅ **Clear Stakeholder Separation**: POD team gets POD CSV, Diagnostics team gets Diagnostics CSV
2. ✅ **Google Sheets Friendly**: Each CSV fits in viewport, easy to navigate
3. ✅ **Simpler Column Structure**: No NA/empty columns for irrelevant analysis
4. ✅ **Consistent with JSON Pattern**: Mirrors existing separate JSON files

### Negative Consequences
1. ⚠️ **File Proliferation**: 2 CSV files instead of 1 when `--analysis-type both`
   - **Mitigation**: Clear naming convention makes pairing obvious
   - **Mitigation**: User requested separate CSVs per analysis type
2. ⚠️ **Duplicate Columns**: Escalation and synthesis columns repeated in both CSVs
   - **Mitigation**: Necessary for each CSV to be self-contained (stakeholders don't need to join files)

**Alternatives Considered**:

1. **Single Combined CSV** (rejected)
   - **Con**: 37+ columns too wide for Google Sheets
   - **Con**: Many NA columns depending on analysis type
   - **Con**: Mixed stakeholder needs

2. **Single CSV with Conditional Columns** (rejected)
   - **Con**: Complex schema (some rows have POD columns, others have Diagnostics)
   - **Con**: Google Sheets pivot tables harder to configure

3. **Three CSVs** (Shared, POD-specific, Diagnostics-specific) (rejected)
   - **Con**: Over-engineered, stakeholders would need to join files
   - **Con**: User requested "clean CSV version", not multi-file joins

**References**:
- [Phase 5 in implementation_plan.md](./implementation_plan.md#csv-export-specification)
- [csv_exporter.py](../csv_exporter.py) (to be implemented)
- [ADR-010: Separate Output Files for Different Analysis Types](#adr-010-separate-output-files-for-different-analysis-types) (JSON precedent)

---

## Document Maintenance

**How to Add a New ADR**:

1. Copy template:
   ```markdown
   ## ADR-XXX: [Decision Title]

   **Status**: Proposed | Accepted | Deprecated

   **Decision Date**: YYYY-MM-DD

   **Context**: [What's the situation? What problem are we solving?]

   **Decision**: [What did we decide?]

   **Rationale**: [Why did we make this decision?]

   **Consequences**: [What are the pros and cons?]

   **Alternatives Considered**: [What else did we think about and why did we reject it?]

   **References**: [Links to docs, code, or related ADRs]
   ```

2. Add to Table of Contents
3. Link from related documents (implementation_plan.md, instrumentation_plan.md)

**When to Create an ADR**:
- Major architectural decisions (e.g., OTEL vs abstraction layer)
- Tradeoffs with long-term consequences (e.g., fail hard vs fallback)
- Deviations from industry norms (e.g., binary vs 3-level scoring)
- Decisions that will be questioned later (e.g., why separate output files?)

**When NOT to Create an ADR**:
- Implementation details (e.g., variable names)
- Temporary workarounds (e.g., debug logging)
- Reversible choices (e.g., batch size for synthesis)

---

**Document Version**: 1.1.0
**Last Updated**: 2025-11-17 (Phase 5 ADRs added)
**Next Review**: After Phase 5 completion
