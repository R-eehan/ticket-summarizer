# AI Observability Platform Evaluation for Azure OpenAI, Anthropic, and OpenAI Direct APIs

## Executive Summary

**For 100K-200K traces/month with direct API implementations, Arize Phoenix (self-hosted) at $100-300/month or Helicone Cloud (free-$40/month) deliver the best value.** If evaluation capabilities are paramount, Langfuse ($89-137/month) or LangSmith ($160-330/month) justify their costs. Phoenix open-source provides full-featured observability without vendor lock-in, while its cloud counterpart (Arize AX Pro at $50-51/month) adds AI-powered debugging through the Alyx Copilot—a game-changing feature unavailable in the self-hosted version. Braintrust offers comparable features at similar pricing but reserves self-hosting for Enterprise customers only.

**The critical distinction across platforms:** Most vendors charge $0-137/month at your scale, making feature differences more important than price. The most significant self-hosted vs cloud gaps involve AI assistants (Arize's Alyx), online evaluations, custom dashboards, and enterprise security features—not core observability capabilities.

## Platform Overview

This evaluation covers **seven major platforms**: three required (Braintrust, Arize/Phoenix, Langfuse) plus four additional market leaders (Helicone, LangSmith, Weights & Biases Weave, Datadog). Each supports Azure OpenAI, Anthropic, and OpenAI through direct API instrumentation without framework dependencies.

---

## 1. Comprehensive Feature Comparison

| Feature | Braintrust | Phoenix (OSS) | Arize AX Cloud | Langfuse OSS | Langfuse Cloud | Helicone | LangSmith | W&B Weave | Datadog |
|---------|-----------|---------------|----------------|--------------|----------------|----------|-----------|-----------|---------|
| **Traces & Spans** | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| **Agent Handoffs** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Sessions | ✅ Threads | ✅ | ✅ |
| **Token/Cost Tracking** | ✅ Auto | ✅ 60+ models | ✅ 60+ models | ✅ Auto | ✅ Auto | ✅ Advanced | ✅ Basic | ✅ Custom | ✅ Detailed |
| **Offline Evaluations** | ✅ Full | ✅ Full | ✅ Full | ✅ SDK-based | ✅ UI + SDK | ✅ Basic | ✅ Best-in-class | ✅ Strong | ✅ Advanced |
| **Online Evaluations** | ✅ | ❌ | ✅ | ✅ | ✅ | ⚠️ Limited | ✅ | ✅ | ✅ |
| **LLM-as-Judge** | ✅ | ✅ | ✅ | ✅ SDK | ✅ UI (v3 EE) + SDK | ⚠️ Via integrations | ✅ Native | ✅ Custom | ✅ Built-in |
| **Experiment Management** | ✅ Playground | ✅ | ✅ | ✅ | ✅ | ✅ A/B testing | ✅ Advanced | ✅ Excellent | ✅ 90-day retention |
| **Dataset Management** | ✅ CSV upload | ✅ | ✅ | ✅ Versioned | ✅ Versioned | ✅ 1 free/unlimited paid | ✅ Best-in-class | ✅ Versioned | ✅ 3-year persist |
| **Human Annotation** | ✅ Queues | ✅ | ✅ | ✅ Queues | ✅ Queues | ✅ Feedback | ✅ Queues | ✅ Feedback | ⚠️ Limited |
| **Custom Dashboards** | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ HQL | ✅ | ✅ Excellent | ✅ Out-of-box |
| **AI Assistant** | ❌ | ❌ | ✅ **Alyx Copilot** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Prompt Management** | ✅ Versioning | ✅ Playground | ✅ Playground | ✅ Git-like | ✅ Git-like | ✅ A/B test | ✅ Playground | ✅ | ⚠️ Basic |
| **Azure OpenAI** | ✅ Via proxy | ✅ Native | ✅ Native | ✅ Drop-in | ✅ Drop-in | ✅ 100+ providers | ✅ Supported | ✅ Auto-patch | ✅ Excellent |
| **Anthropic** | ✅ Wrapper | ✅ Native | ✅ Native | ✅ 3 methods | ✅ 3 methods | ✅ Native | ✅ Auto | ✅ Auto-patch | ✅ Native |
| **OpenAI** | ✅ Wrapper | ✅ Native | ✅ Native | ✅ Drop-in | ✅ Drop-in | ✅ Proxy | ✅ Auto | ✅ Auto-patch | ✅ Deep integration |
| **Instrumentation Ease** | ⭐⭐⭐⭐ (3-4 lines) | ⭐⭐⭐⭐ (2-3 lines) | ⭐⭐⭐⭐ (2-3 lines) | ⭐⭐⭐⭐⭐ (Drop-in) | ⭐⭐⭐⭐⭐ (Drop-in) | ⭐⭐⭐⭐⭐ (1 line proxy) | ⭐⭐⭐ (SDK required) | ⭐⭐⭐⭐ (Auto-patch) | ⭐⭐⭐⭐ (SDK) |
| **OpenTelemetry** | ✅ OTLP endpoint | ✅ Native | ✅ Native | ✅ Compatible | ✅ Compatible | ✅ Compatible | ✅ Backend | ✅ Integration | ✅ Full support |

### Integration Methods by Platform

**Direct API Call Support (No Frameworks Required):**

- **Braintrust**: Wrapper functions (`wrapOpenAI`, `wrapAnthropic`), AI Proxy (OpenAI-compatible), OpenTelemetry, manual SDK
- **Phoenix/Arize**: OpenInference auto-instrumentation (2-3 lines), OpenTelemetry manual spans
- **Langfuse**: Drop-in replacement imports, `@observe()` decorator, OpenTelemetry, manual low-level SDK  
- **Helicone**: Proxy via base URL change (easiest—1 line), optional SDK for advanced features
- **LangSmith**: `@traceable` decorator (requires SDK), OpenTelemetry support
- **W&B Weave**: Auto-patching (`weave.init()`), `@weave.op()` decorator
- **Datadog**: SDK auto-instrumentation (Python/Node.js), API submission for other languages

---

## 2. Self-Hosted vs Cloud: Critical Feature Gaps

### Braintrust

**Self-Hosting:** ❌ **Enterprise Only** (hybrid architecture)

**Source:** https://www.braintrust.dev/docs/guides/self-hosting

**What You Get (Self-Hosted Data Plane):**
- All core observability: traces, spans, LLM calls, evaluations, experiments, datasets
- Prompt playground functionality
- AI Proxy (can self-host separately)
- Full data sovereignty—data never touches Braintrust infrastructure

**What You LOSE (Braintrust-Hosted Control Plane):**
- ❌ **Web UI hosted by Braintrust** (not self-hosted)—browser connects directly to your data plane via CORS
- ❌ **User management interface** remains in Braintrust cloud
- ❌ **Automatic monitoring/alerting**—requires opt-in telemetry sharing
- ❌ **Proactive support**—you manage all infrastructure, longer incident resolution without remote access
- ❌ **Automatic updates**—manual quarterly updates required
- ❌ **Infrastructure complexity**—requires AWS Lambda/K8s, PostgreSQL, Redis, S3, Brainstore license

**Deployment:** Terraform (AWS/Azure/GCP), Kubernetes Helm charts, Docker

**Sources:**  
- https://www.braintrust.dev/pricing  
- https://github.com/braintrustdata/terraform-aws-braintrust-data-plane  
- https://github.com/braintrustdata/braintrust-deployment

---

### Arize Phoenix (Open Source) vs Arize AX (Cloud)

**Self-Hosting:** ✅ **Fully Available** (Apache v2.0 license)

**Source:** https://arize.com/docs/phoenix, https://github.com/Arize-ai/phoenix

**Phoenix Open Source Includes:**
- Full observability platform: traces, spans, agents, multi-modal support
- Cost tracking with 60+ model pricing tables
- Offline evaluations (LLM-as-Judge, code-based, external integrations)
- Experiments, datasets, prompt management
- Human annotation capabilities
- Agent Graph visualization
- OpenInference instrumentation (auto for Azure OpenAI, Anthropic, OpenAI)
- SQLite or PostgreSQL backend
- Unlimited traces, unlimited users, free forever

**Arize AX Cloud Adds (CRITICAL GAPS):**
- ✅ **Alyx AI Copilot**—THE most significant missing feature. 30+ skills including semantic search, anomaly detection, natural language queries, eval builder, prompt optimization, embedding summarization (built on Azure OpenAI for security/compliance)
- ✅ **Online evaluations**—real-time evaluation on production traffic (Phoenix: offline only)
- ✅ **Custom dashboards**—Phoenix has fixed views only
- ✅ **Monitors & alerts**—automated monitoring (Phoenix: none)
- ✅ **Custom metrics**—business-specific metrics (Phoenix: standard metrics only)
- ✅ **Traditional ML/CV observability**—drift, bias, performance (Phoenix: LLM-only)
- ✅ **RBAC**—role-based access control (Phoenix: none)
- ✅ **SSO**—Okta, Azure AD/Entra ID (Phoenix: none)
- ✅ **Compliance**—HIPAA, SOC2, 99.9% SLA (Phoenix: self-managed)
- ✅ **ADB (Arize Database)**—proprietary OLAP for billions of traces, petabyte-scale (Phoenix: SQLite/PostgreSQL)
- ✅ **Dedicated support**—customer success team (Phoenix: community Slack)
- ✅ **Automatic data retention**—Phoenix requires manual SQL cleanup scripts

**Infrastructure for Phoenix Self-Hosting:**
- Docker (simplest: `docker run -p 6006:6006 arizephoenix/phoenix:latest`)
- Kubernetes for scale
- PostgreSQL recommended for production (SQLite for development)
- Persistent volume for database
- Estimated costs: **$100-300/month** (compute $50-150, storage $20-50, PostgreSQL $30-100)

**Sources:**  
- https://arize.com/pricing/  
- https://arize.com/docs/phoenix/learn/resources/faqs/what-is-the-difference-between-phoenix-and-arize  
- https://arize.com/docs/phoenix/self-hosting

---

### Langfuse

**Self-Hosting:** ✅ **Fully Available** (MIT license for OSS, Commercial license for Enterprise features)

**Source:** https://langfuse.com/open-source, https://langfuse.com/pricing-self-host

**Langfuse OSS (MIT) Includes:**
- **ALL core platform features**: traces, spans, generations, sessions, LLM call tracking, token/cost monitoring
- Evaluation tools: LLM-as-a-judge (via custom SDK pipelines), human annotations, custom scores via API/SDK
- Prompt management (version control, playground), datasets, experiments
- Annotation queues, dashboards, multi-modal support
- All APIs, SDKs, integrations (OpenAI, Azure OpenAI, Anthropic)
- OpenTelemetry support, SSO (Google, GitHub, Azure AD, Okta, Auth0, AWS Cognito), RBAC
- Export capabilities
- **Codebase is IDENTICAL across OSS, Enterprise self-host, and Cloud**

**Langfuse Cloud/Enterprise Adds (Missing in OSS):**
- ❌ **SCIM API**—automated user provisioning/deprovisioning (Enterprise security requirement)
- ❌ **Extended audit logging**—enhanced security trails for compliance
- ❌ **Automated data retention policies**—UI-based management (OSS: manual SQL queries on schedule)
- ❌ **Organization Management API (EE)**—programmatic org/project management
- ❌ **UI customization (EE)**—custom branding/theming
- ❌ **Model-based evaluations run within Langfuse UI (v3 commercial license)**—NOTE: All core evaluation tooling via SDK/API is MIT-licensed; OSS users run evals via custom pipelines

**Key Insight:** Langfuse has the **smallest feature gap** between self-hosted OSS and cloud. The differences are primarily enterprise security features, not core observability.

**Infrastructure for Self-Hosting:**
- Docker Compose (testing): 15-30 minutes setup
- Kubernetes/Helm (production): 2-4 hours, requires external PostgreSQL, ClickHouse (16GB+ RAM), Redis/Valkey (4+ CPUs), S3/Blob storage
- Cloud templates: AWS/Azure/GCP Terraform (1-3 hours)
- Estimated costs at 100K-200K traces/month: **$300-800/month** (compute, ClickHouse 32-64GB RAM, Redis 8GB+, S3 variable)

**Sources:**  
- https://langfuse.com/pricing  
- https://langfuse.com/pricing-self-host  
- https://github.com/orgs/langfuse/discussions/3393  
- https://langfuse.com/self-hosting/deployment/kubernetes

---

### Helicone

**Self-Hosting:** ✅ **Fully Available** (Apache v2.0 license)

**Source:** https://github.com/Helicone/helicone, https://docs.helicone.ai

**Feature Parity:** No significant gaps—self-hosted includes all core features. Enterprise features (SOC-2, SSO, custom SLAs) only on Enterprise cloud plan.

**Deployment:** Docker Compose, Kubernetes/Helm charts available

**Source:** https://www.helicone.ai/pricing

---

### LangSmith

**Self-Hosting:** ⚠️ **Enterprise Plan Only** (not available on Developer or Plus plans)

**Source:** https://www.langchain.com/pricing

**Feature Gaps:** Self-hosting heavily restricted; most users must use cloud.

---

### Weights & Biases Weave

**Self-Hosting:** ⚠️ **Available with Deploy Manager** (requires trial license activation)

**Source:** https://wandb.ai/site/pricing

**Feature Gaps:** Requires additional setup and trial license (not fully open-source).

---

### Datadog LLM Observability

**Self-Hosting:** ❌ **Cloud-only** (no self-hosted option)

**Source:** https://www.datadoghq.com/product/llm-observability/

---

## 3. Pricing Comparison: 100K-200K Traces/Month

### Key Pricing Models Explained

- **Braintrust**: Platform fee + processed data (GB) + scores + span retention
- **Arize/Phoenix**: Per-span pricing (cloud) or infrastructure costs (self-hosted)
- **Langfuse**: Units = traces + observations (spans/generations) + scores
- **Helicone**: Per-request pricing with generous free tier
- **LangSmith**: Seat-based + trace volume (base vs extended traces)
- **W&B Weave**: Per-user + data ingestion (GB)
- **Datadog**: Complex enterprise usage-based (bundled with APM/Infrastructure)

**CRITICAL:** One "trace" typically contains 5-10 observations (spans), so 100K traces = ~500K-1M total units depending on complexity.

| Platform | Pricing Model | 100K Traces/Month | 200K Traces/Month | Free Tier | Data Retention | Notes |
|----------|--------------|-------------------|-------------------|-----------|----------------|-------|
| **Braintrust Cloud** | $249/mo + $3/GB data | **$0** (FREE tier: 1M spans) | **$249-349** (Pro tier) | 1M spans/mo, 1GB data | Free: 1 month<br>Pro: Extended | Spans ≠ traces (5-10 spans per trace) |
| **Braintrust Self-Hosted** | Infrastructure only | **N/A** (Enterprise only) | **N/A** (Enterprise only) | N/A | User-controlled | Requires Enterprise license + AWS/Azure resources |
| **Phoenix Self-Hosted** | Infrastructure only | **$100-300** | **$100-300** | Unlimited | User-managed | Compute $50-150 + storage $20-50 + PostgreSQL $30-100 |
| **Arize AX Pro** | $50/mo + $10/million spans | **$50** | **$51** | 25K spans/mo, 1GB, 7 days | Free: 7 days<br>Pro: 15 days<br>Enterprise: Custom | **Best cloud value**—includes Alyx Copilot |
| **Langfuse OSS** | Infrastructure only | **$300-800** | **$300-800** | Unlimited | User-managed SQL | ClickHouse 32-64GB RAM + Redis 8GB+ + S3 |
| **Langfuse Cloud Core** | $49/mo + $8/100K units | **$89** (~600K units) | **$137** (~1.2M units) | 50K units/mo | Free: 30 days<br>Core: 90 days | Units = traces + observations + scores |
| **Langfuse Cloud Pro** | $499/mo + $8/100K units | **$539** | **$587** | 100K units | Unlimited | SOC2, ISO27001, BAA (HIPAA) |
| **Helicone Cloud** | $20/user/mo (includes 100K requests) | **FREE** | **$20-40** | 100K requests/mo | Free: 1 month<br>Pro: 3 months | **Best free tier** |
| **Helicone Self-Hosted** | Infrastructure only | **$50-200** | **$50-200** | Unlimited | User-managed | Docker/K8s deployment |
| **LangSmith Plus** | $39/user/mo + $0.50/1K base traces | **$84 + $39/user**<br>(2 users: $162) | **$134 + $39/user**<br>(2 users: $212) | 5K traces/mo | Base: 14 days<br>Extended: 400 days | Per-user fees add up quickly |
| **W&B Weave Pro** | $60/user/mo (25GB data ingestion) | **$60/user** | **$60/user** | 25GB/mo ingestion | Variable | Assumes ~1-2GB for 100K-200K traces (trace size dependent) |
| **Datadog LLM Observability** | Enterprise usage-based (contact sales) | **$200-500+** (estimated) | **$200-500+** (estimated) | None specific | Configurable | Not transparent; expensive at scale |
| **New Relic AI** | $0.35/GB Standard (free 100GB) | **FREE** | **FREE** | 100GB data/mo | Configurable | Assumes ~1-2GB for traces; general observability platform |

### Cost-Effectiveness Ranking (100K-200K Traces/Month)

1. **Helicone**: $0-40/month ⭐⭐⭐⭐⭐
2. **Arize AX Pro**: $50-51/month ⭐⭐⭐⭐⭐ (includes AI assistant)
3. **Langfuse Cloud Core**: $89-137/month ⭐⭐⭐⭐
4. **Phoenix Self-Hosted**: $100-300/month ⭐⭐⭐⭐ (infrastructure burden)
5. **LangSmith Plus**: $160-330/month ⭐⭐⭐ (for 2-5 users)
6. **Langfuse OSS**: $300-800/month ⭐⭐⭐ (infrastructure costs)
7. **W&B Weave**: $60-300/month ⭐⭐⭐ (per-user pricing)
8. **Datadog**: $200-500+/month ⭐⭐ (enterprise pricing)

**Hidden Costs to Consider:**

- **Self-hosted platforms**: DevOps time (4-20 hours/month maintenance), infrastructure monitoring, security patches, scaling management, backup storage
- **Cloud platforms**: Extended data retention ($3-5/GB/month), additional users, overage fees, score computation for evals
- **LLM API costs for evaluations**: All platforms require paying OpenAI/Anthropic/Azure for LLM-as-a-judge evals (not included in platform pricing)

**Sources:**  
- Braintrust: https://www.braintrust.dev/pricing  
- Arize: https://arize.com/pricing/  
- Langfuse: https://langfuse.com/pricing  
- Helicone: https://www.helicone.ai/pricing  
- LangSmith: https://www.langchain.com/pricing  
- W&B: https://wandb.ai/site/pricing  
- Datadog: https://www.datadoghq.com/pricing/

---

## 4. Technical Considerations

### Setup Complexity & Time to First Value

| Platform | Setup Time | Complexity | Method | First Trace |
|----------|-----------|------------|---------|-------------|
| **Helicone** | \<30 min | ⭐ Easiest | Change base URL (1 line) | \<30 min |
| **Braintrust Cloud** | \<1 hour | ⭐⭐ Easy | Wrapper functions (3-4 lines) | \<1 hour |
| **Phoenix (Docker)** | 15-30 min | ⭐⭐ Easy | Docker run + 2-3 lines code | \<1 hour |
| **Arize AX** | 15-30 min | ⭐⭐ Easy | Auto-instrumentation (2-3 lines) | 15-30 min |
| **Langfuse Cloud** | 5-10 min | ⭐⭐ Easy | Drop-in import replacement | 5-10 min |
| **W&B Weave** | 30 min | ⭐⭐ Easy | `weave.init()` + auto-patch | 30 min |
| **Datadog** | 1-2 hours | ⭐⭐⭐ Moderate | SDK integration + DD agent | 1-2 hours |
| **LangSmith** | 1-2 hours | ⭐⭐⭐ Moderate | SDK + decorator-based | 1-2 hours |
| **Phoenix (K8s Production)** | 2-4 hours | ⭐⭐⭐ Moderate | Helm + external DBs | 4-8 hours |
| **Langfuse Self-Hosted (K8s)** | 2-4 hours | ⭐⭐⭐ Moderate | Helm + ClickHouse/PostgreSQL/Redis | 4-8 hours |
| **Braintrust Self-Hosted** | 1-3 days | ⭐⭐⭐⭐ High | Terraform + DevOps (Enterprise only) | 1-3 days |

### Instrumentation for Direct API Calls (No Frameworks)

**Easiest (Proxy-Based):**
- **Helicone**: Change `base_url` parameter—literally one line

**Very Easy (Drop-in Replacements):**
- **Langfuse**: `from langfuse.openai import openai` (Python) or `observeOpenAI(new OpenAI())` (JS)
- **Braintrust**: `wrapOpenAI()`, `wrapAnthropic()`
- **Phoenix/Arize**: `OpenAIInstrumentor().instrument()`
- **W&B Weave**: `weave.init()` auto-patches OpenAI/Anthropic

**Moderate (Decorator-Based):**
- **Langfuse**: `@observe()` decorator for custom functions
- **LangSmith**: `@traceable` decorator
- **W&B Weave**: `@weave.op()` decorator
- **Braintrust**: `@traced()` decorator

**Advanced (Manual):**
- All platforms support OpenTelemetry for maximum control
- Low-level SDKs available for custom span creation

### Infrastructure Requirements (Self-Hosted)

**Phoenix (Minimal):**
- Docker container (single command)
- SQLite (development) or PostgreSQL (production)
- Persistent volume
- Scale estimate: t3.medium-large AWS equivalent

**Langfuse (Production):**
- 2-4 Web containers (2-4 CPU, 4-8 GB RAM each)
- 2-4 Worker containers (2-4 CPU, 4-8 GB RAM each)
- PostgreSQL (managed recommended)
- ClickHouse (16-32GB+ RAM for analytics)
- Redis/Valkey (4+ CPUs, 8GB+ RAM with cluster mode)
- S3/Blob storage (variable based on payloads)

**Braintrust (Enterprise):**
- AWS Lambda or Kubernetes cluster
- PostgreSQL database
- Redis instance (with sizing guidance)
- S3/blob storage
- NVME disk for Brainstore performance
- VPC configuration
- Brainstore license key from Braintrust

**Helicone:**
- Docker Compose or Kubernetes
- ClickHouse database
- Kafka for event streaming
- S3/blob storage

### Data Retention Policies

| Platform | Free/Basic | Mid-Tier | Premium | Self-Hosted |
|----------|-----------|----------|---------|-------------|
| **Braintrust** | 1 month | Extended | Extended | User-controlled |
| **Arize AX** | 7 days | 15 days | Configurable | N/A |
| **Phoenix** | N/A | N/A | N/A | User-managed (SQLite/PostgreSQL) |
| **Langfuse Cloud** | 30 days | 90 days | Unlimited | N/A |
| **Langfuse OSS** | N/A | N/A | N/A | Manual SQL cleanup |
| **Helicone** | 1 month | 3 months | Forever | User-managed |
| **LangSmith** | 14 days (base) | 400 days (extended) | 400 days | Enterprise only |
| **W&B Weave** | Variable | Variable | Variable | Variable |
| **Datadog** | Configurable | Configurable | Configurable | N/A |

### Maintenance Overhead (Self-Hosted)

**Phoenix**: ⭐⭐ Low-Moderate
- Database backups and scaling
- Version upgrades (manual)
- Infrastructure monitoring
- Estimated: 4-8 hours/month basic, 10-15 hours/month production

**Langfuse OSS**: ⭐⭐⭐ Moderate
- Multi-component management (web, worker, PostgreSQL, ClickHouse, Redis, S3)
- Data retention via manual SQL queries
- Scaling decisions (horizontal: web/worker; vertical: ClickHouse memory)
- Queue metrics monitoring
- Estimated: 8-20 hours/month

**Braintrust**: ⭐⭐⭐⭐ High
- Weekly releases (quarterly updates minimum)
- Complex hybrid architecture (data plane self-hosted, control plane Braintrust-hosted)
- Infrastructure configuration responsibility
- Requires dedicated DevOps resources
- Estimated: 20+ hours/month

**Helicone**: ⭐⭐ Low-Moderate
- Docker/K8s deployment
- ClickHouse and Kafka management
- Estimated: 5-10 hours/month

---

## 5. Pros & Cons Analysis

### Braintrust

**Pros:**
- Fast setup (under 1 hour) with minimal code changes (3-4 lines)
- Comprehensive features: evals, experiments, datasets, human labeling
- Production-proven at scale (Notion, Zapier, Coursera, Airtable)
- Likely **FREE** for 100K traces/month (within 1M span limit)
- Native Azure OpenAI, Anthropic, OpenAI support via wrappers or proxy
- Sub-100ms cached responses through AI Proxy
- Open-source AI Proxy available for self-hosting (MIT license)
- Brainstore database offers sub-second query performance (80x faster than traditional databases)

**Cons:**
- Self-hosting restricted to **Enterprise only** (not available on Free/Pro)
- Hybrid architecture: UI remains Braintrust-hosted even when data plane is self-hosted
- No true open-source option (core platform proprietary)
- Proxy adds network hop (mitigated by caching)
- Requires infrastructure management knowledge for self-hosting
- Manual quarterly updates required for self-hosted deployments

**Best For:** Teams wanting comprehensive features at low cost ($0-349/month), rapid implementation, production-grade performance, with Enterprise budget for self-hosting if needed

**Sources:**  
- https://www.braintrust.dev/  
- https://www.braintrust.dev/pricing  
- https://www.braintrust.dev/docs/guides/self-hosting

---

### Arize Phoenix (Open Source) & Arize AX (Cloud)

**Phoenix Pros:**
- **Fully open-source** (Apache v2.0)—no vendor lock-in
- Unlimited traces and users, free forever
- All core observability features included (traces, evals, experiments, datasets)
- Simple Docker deployment (`docker run` single command)
- Excellent integration with Azure OpenAI, Anthropic, OpenAI via OpenInference auto-instrumentation
- Cost tracking for 60+ models with built-in pricing tables
- Agent Graph visualization for complex workflows
- Community support via Slack
- Infrastructure costs only: **$100-300/month** for 100K-200K traces

**Phoenix Cons:**
- ❌ **No Alyx AI Copilot**—the most significant missing feature vs Arize AX
- No online evaluations (offline only)
- No custom dashboards (fixed views only)
- No automated monitors/alerts
- No RBAC, SSO, or compliance certifications
- Manual data retention management (SQL cleanup scripts)
- Operational overhead (database management, scaling, backups)
- Community support only (no SLA)
- LLM-only observability (no traditional ML/CV support)

**Arize AX Pros:**
- **Alyx AI Copilot** with 30+ skills (semantic search, anomaly detection, natural language queries, eval builder, prompt optimization)—game-changing for debugging
- **Exceptionally affordable**: $50-51/month for 100K-200K traces
- Online evaluations on production traffic
- Custom dashboards for stakeholders
- Automated monitors and alerts
- Enterprise features: RBAC, SSO (Okta, Azure AD), HIPAA/SOC2, 99.9% SLA
- Zero maintenance (managed service)
- Dedicated support team
- 15-minute setup
- Proprietary ADB database for petabyte-scale analytics

**Arize AX Cons:**
- Data hosted by Arize (not self-hosted at Pro tier)
- More expensive than Phoenix self-hosted ($50 vs $0 base, but comparable including infrastructure)
- 15-day retention on Pro (vs unlimited in Phoenix)

**Best For:** 
- **Phoenix**: Budget-conscious teams with DevOps resources, wanting complete data control and no vendor lock-in
- **Arize AX**: Teams valuing productivity (Alyx Copilot), managed services, and **best cloud value at $50-51/month** for the feature set

**Recommendation:** **Start with Arize AX Pro** unless strict data sovereignty requires self-hosting. The $50/month cost is lower than Phoenix infrastructure costs, includes game-changing AI assistance, and eliminates operational burden.

**Sources:**  
- https://arize.com/pricing/  
- https://arize.com/docs/phoenix  
- https://github.com/Arize-ai/phoenix  
- https://arize.com/docs/phoenix/learn/resources/faqs/what-is-the-difference-between-phoenix-and-arize

---

### Langfuse

**OSS Pros:**
- **Fully open-source** (MIT license) with near-complete feature parity to cloud
- All core features: traces, evals (via SDK), prompt management, datasets, human annotations
- OpenTelemetry-based (open standard, reduced vendor lock-in)
- Drop-in replacement for OpenAI/Azure OpenAI (easiest instrumentation)
- `@observe()` decorator for custom direct API code
- Multiple integration methods (3 methods for Anthropic alone)
- Strong documentation and active community
- Identical codebase across OSS, Enterprise, and Cloud

**OSS Cons:**
- Infrastructure costs: **$300-800/month** (higher than Phoenix due to ClickHouse, Redis requirements)
- Complex infrastructure (PostgreSQL, ClickHouse 16GB+ RAM, Redis 4+ CPUs, S3)
- Manual data retention management (SQL queries on schedule)
- No automated LLM-as-a-judge UI in v3 (requires SDK/custom pipelines)
- No SCIM API, extended audit logs, or automated retention policies
- Operational overhead (8-20 hours/month maintenance)

**Cloud Pros:**
- **Fastest setup**: 5-10 minutes to first trace
- Reasonable pricing: **$89-137/month** (Core) for 100K-200K traces
- Unlimited retention on Pro tier ($539-587/month)
- SOC2, ISO27001 reports; BAA available for HIPAA
- No infrastructure management
- Built-in HA, backups, scaling
- UI-based evaluations (v3)
- Automated data retention policies
- In-app support (Core) or dedicated support (Pro)

**Cloud Cons:**
- Higher cost than Arize AX Pro ($89 vs $50) at 100K traces
- No AI assistant (unlike Arize's Alyx)
- Data hosted by Langfuse (EU or US regions)

**Best For:**
- **OSS**: Teams needing data sovereignty with DevOps expertise, willing to accept higher infrastructure costs for complete control
- **Cloud Core**: Teams wanting comprehensive features at reasonable cost ($89-137/month)
- **Cloud Pro**: Organizations requiring unlimited retention and compliance certifications

**Note:** Langfuse has the **smallest feature gap** between self-hosted and cloud among all platforms evaluated. The differences are enterprise security features, not core observability.

**Sources:**  
- https://langfuse.com/pricing  
- https://langfuse.com/open-source  
- https://github.com/langfuse/langfuse  
- https://langfuse.com/self-hosting

---

### Helicone

**Pros:**
- **Best free tier**: 100,000 requests/month free (covers 100K traces completely)
- **Easiest instrumentation**: One-line base URL change—no SDK required
- Lowest cost overall: **$0-40/month** for 100K-200K traces
- Fully self-hostable (Apache v2.0) with no feature gaps
- Supports 100+ LLM providers through unified gateway
- Advanced cost tracking with 20-30% savings through built-in caching
- Only 10-50ms latency overhead (proxy-based but highly optimized)
- Docker and Kubernetes deployment options
- Distributed architecture (Cloudflare Workers, ClickHouse, Kafka) for scale
- HQL (Helicone Query Language) for custom queries

**Cons:**
- Basic evaluation capabilities (not as comprehensive as LangSmith or Langfuse)
- Limited experiment management compared to dedicated platforms
- 1 dataset on free tier (unlimited on paid)
- Community-driven development (smaller team vs enterprise platforms)
- Evaluation features require external integrations (LastMile, Ragas)
- Proxy-based approach may not suit all architectures

**Best For:** Budget-conscious teams prioritizing cost tracking, ease of integration, and rapid deployment over advanced evaluation features

**Sources:**  
- https://www.helicone.ai  
- https://www.helicone.ai/pricing  
- https://github.com/Helicone/helicone

---

### LangSmith

**Pros:**
- **Best-in-class evaluation capabilities**—most comprehensive evals framework
- Advanced experiment tracking and comparison
- First-class dataset support with versioning
- Excellent for LangChain workflows (native integration)
- Pytest/Vitest integration for CI/CD regression testing
- Comprehensive UI with detailed trace drill-down
- Prompt playground for rapid iteration
- 400-day retention for extended traces (when feedback added)

**Cons:**
- **Higher cost**: $160-330/month for 100K-200K traces (2-5 users)
- Per-user pricing adds up quickly ($39/user/month base)
- Automatic upgrade to extended traces ($4.50/1K) when feedback received
- Requires SDK integration (moderate setup complexity)
- Self-hosting **restricted to Enterprise only**
- Base traces only 14-day retention (must pay for extended)
- More involved instrumentation than proxy-based solutions

**Best For:** Teams using LangChain, prioritizing evaluation quality over cost, with budget for $200-400/month and multiple team members

**Sources:**  
- https://www.langchain.com/langsmith  
- https://www.langchain.com/pricing  
- https://docs.smith.langchain.com

---

### Weights & Biases Weave

**Pros:**
- **Excellent experiment tracking**—core strength of W&B platform
- Industry-leading visualizations and dashboards
- Strong evaluation framework (custom scorers, leaderboards)
- Hyperparameter optimization (Sweeps)
- Auto-patching for OpenAI/Anthropic (easy setup)
- Integration with broader ML pipeline (perfect for ML-first teams)
- Academic/nonprofit free Pro license (200GB, 25GB/mo ingestion, 100 seats)
- Version control for models, datasets, code

**Cons:**
- **Per-user pricing**: $60/user/month (costs scale with team size)
- Pricing based on data ingestion (GB), not traces—conversion complexity
- May exceed 25GB/month limit with large traces (embeddings, long prompts)
- Feature-heavy—may be overkill for pure LLM use cases
- Self-hosting requires trial license (not fully open-source)
- Less focused on LLM-specific workflows compared to dedicated platforms

**Best For:** ML-first organizations already using W&B for traditional ML, needing unified experiment tracking across LLMs and traditional models, with multiple users

**Sources:**  
- https://wandb.ai/site/weave  
- https://wandb.ai/site/pricing  
- https://weave-docs.wandb.ai

---

### Datadog LLM Observability

**Pros:**
- **Unified observability**: LLM + infrastructure + applications in single platform
- Excellent Azure integration (60+ Azure services)
- Out-of-the-box dashboards and evaluations (hallucination detection, sentiment analysis)
- Deep integration with existing Datadog APM for full-stack correlation
- Enterprise-grade security and compliance (SOC-2, HIPAA with Data Plus)
- Topical clustering and anomaly detection
- 90-day experiment retention, 3-year dataset persistence
- Best for enterprises already using Datadog

**Cons:**
- **Expensive**: $200-500+/month estimated (potentially much higher)
- Not transparent pricing—requires contacting sales
- Cloud-only (no self-hosting)
- Complex pricing structure tied to broader Datadog platform
- Overkill if not already using Datadog infrastructure monitoring
- Limited human annotation capabilities
- Steep learning curve for Datadog ecosystem

**Best For:** Enterprises with existing Datadog infrastructure, needing unified observability, with budget for $500+/month and requiring deep Azure integration

**Sources:**  
- https://www.datadoghq.com/product/llm-observability/  
- https://docs.datadoghq.com/llm_observability/  
- https://www.datadoghq.com/pricing/

---

## 6. Recommendations by Use Case

### For Your Specific Requirements (100K-200K traces/month, Azure OpenAI + Anthropic + OpenAI, direct APIs)

#### 🥇 Top Recommendation: **Arize AX Pro ($50-51/month)**

**Why:** Best overall value combining comprehensive features, AI-powered debugging (Alyx Copilot), managed service, and exceptional affordability. Lower cost than Phoenix self-hosted infrastructure while eliminating operational burden.

**Implementation Path:**
1. Sign up at arize.com
2. Add 2-3 lines: `OpenAIInstrumentor().instrument()`
3. Start receiving traces in 15-30 minutes
4. Leverage Alyx Copilot for debugging and optimization

---

#### 🥈 Second Choice: **Helicone (Free-$40/month)**

**Why:** Best for extreme budget constraints and fastest integration. 100,000 requests/month free tier covers 100K traces completely. One-line implementation (change base URL).

**Implementation Path:**
1. Sign up at helicone.ai
2. Change `base_url` parameter in API clients
3. Immediate tracing with zero code changes beyond URL

**Trade-off:** Basic evaluation capabilities—consider integrating external eval tools (Ragas, LastMile).

---

#### 🥉 Third Choice: **Langfuse Cloud Core ($89-137/month)**

**Why:** Best for teams prioritizing comprehensive evaluations, prompt management, and data control options. Smallest feature gap between self-hosted and cloud.

**Implementation Path:**
1. Sign up at langfuse.com
2. Use drop-in replacement: `from langfuse.openai import openai`
3. Add `@observe()` decorator for custom code
4. 5-10 minutes to first trace

**Upgrade Path:** Move to Langfuse OSS self-hosted if data sovereignty becomes critical (all features available in MIT license).

---

### Self-Hosting Decision Matrix

**Choose Self-Hosted If:**
- ✅ Strict data residency/sovereignty requirements (on-premises only)
- ✅ Have dedicated DevOps resources (10-20 hours/month maintenance capacity)
- ✅ Want complete control over data retention and infrastructure
- ✅ Prefer open-source to avoid vendor lock-in
- ✅ Can accept operational burden for cost savings or control

**Best Self-Hosted Options:**

1. **Phoenix Open Source** ($100-300/month infrastructure)
   - Simplest self-hosted deployment (single Docker command)
   - All core features included
   - Lowest infrastructure costs
   - Trade-off: No AI assistant, no online evals

2. **Langfuse OSS** ($300-800/month infrastructure)
   - Near-complete feature parity with cloud
   - Most comprehensive self-hosted platform
   - Higher infrastructure costs (ClickHouse, Redis requirements)
   - Trade-off: Complex setup, manual data retention

3. **Helicone Self-Hosted** ($50-200/month infrastructure)
   - Lowest base cost
   - Full feature parity with cloud
   - Apache v2.0 license
   - Trade-off: Basic evaluation capabilities

---

### By Primary Priority

**If Evaluation Quality is #1:** LangSmith ($160-330/month) or Langfuse Cloud Core ($89-137/month)

**If Cost is #1:** Helicone (free-$40/month) or Arize AX Pro ($50-51/month)

**If AI-Assisted Debugging is #1:** Arize AX Pro ($50-51/month)—**only platform with AI assistant**

**If Data Sovereignty is #1:** Phoenix OSS ($100-300/month) or Langfuse OSS ($300-800/month)

**If Ease of Integration is #1:** Helicone (1 line) or Langfuse (drop-in replacement)

**If Full-Stack Observability is #1:** Datadog ($200-500+/month)—if already using Datadog

**If Experiment Tracking is #1:** W&B Weave ($60+/user/month) or LangSmith

---

## 7. Implementation Roadmap

### Recommended Approach

**Phase 1: Proof of Concept (Week 1)**
- Deploy **Arize AX Pro** (15-minute setup, $50/month, 14-day trial)
- Instrument Azure OpenAI, Anthropic, OpenAI direct API calls
- Test Alyx Copilot for debugging
- Validate cost tracking and basic dashboards

**Phase 2: Evaluation (Weeks 2-4)**
- Create datasets from production traces
- Set up offline evaluations
- Test prompt experimentation workflows
- Evaluate if online evaluations add value
- Monitor actual trace volume and costs

**Phase 3: Decision Point (Week 4)**

**If satisfied with Arize AX Pro:** Continue at $50/month scale

**If need more evaluation power:** 
- Add Langfuse Cloud Core ($89-137/month) or switch to LangSmith
- Run side-by-side comparison for 2 weeks

**If data sovereignty required:**
- Deploy Phoenix OSS or Langfuse OSS
- Budget 2-4 hours for production setup
- Plan for ongoing maintenance (4-20 hours/month)

**If extremely budget-constrained:**
- Switch to Helicone (free-$40/month)
- Integrate external eval tools as needed

---

## Conclusion

**The AI observability market offers exceptional value at 100K-200K traces/month scale**, with most platforms costing $0-137/month—a fraction of typical LLM API costs. The decision hinges on priorities: Arize AX Pro delivers unmatched value at $50/month with AI-powered debugging, Helicone offers the best free tier and easiest integration, Langfuse provides the most flexibility between cloud and self-hosted, and LangSmith excels at evaluations for teams with larger budgets.

**The most significant self-hosted vs cloud gap across all platforms is Arize's Alyx AI Copilot**—a 30+ skill AI assistant built on Azure OpenAI that fundamentally changes debugging workflows. No other platform offers comparable AI assistance. Beyond this, feature gaps focus on enterprise security (SCIM, audit logs), operational convenience (automated retention, monitoring), and advanced analytics (custom dashboards)—not core observability capabilities.

**Critical insight:** Phoenix open-source and Langfuse OSS prove that comprehensive LLM observability doesn't require vendor lock-in. Both provide production-ready self-hosted options at $100-800/month infrastructure costs with full feature sets. However, the operational burden (10-20 hours/month) and higher infrastructure costs often make affordable cloud options like Arize AX Pro ($50/month) or Helicone ($0-40/month) more economical when factoring in engineering time.

**Start with Arize AX Pro for immediate value**, then pivot to self-hosted options if data sovereignty becomes critical or evaluate alternatives if specific features (advanced evals, experiment tracking) justify higher costs. The low switching costs in this market—thanks to OpenTelemetry standardization—mean you can experiment with confidence.